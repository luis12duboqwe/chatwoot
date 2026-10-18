#!/usr/bin/env python3
"""All retry tests are offline; no model requests or Docker required."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import patch_proposer as p
import proposal_iteration as it
import synthetic_lab as s

class ProposalIterationTests(unittest.TestCase):
 def setUp(self):
  self.issue={
   "id":"6080c2a5b31ef5b2a9","status":"synthetic_unverified",
   "source":"interactive_step_by_step_groq","category":"changes",
   "evidence":[{"buyer":"Si no hay 512GB negro, prefiero 256GB azul",
      "bot":"Revisaré 512GB negro"}]}
  self.source=("PILOT_CONVERSATION_ID = 3\nAUTO_REPLY_LIMIT = 1\n"+
     p.START+("      # safe context filler\n"*27)+p.COLOR_ANCHOR+
     "      data\n    end\n\n"+p.STOP+"\n")
  self.method=p.method_area(self.source)[1]
  self.p_good={"search":"no matter what","replace":
      p.COLOR_ANCHOR.replace("data[:color]=choices.first","data[:color]=choices.last"),
      "reason":"Prefer alternative after conditional request",
      "regression_example":"Si no hay negro, mejor azul"}
  self.p_bad={"search":"arbitrary",
      "replace":"      eval('unsafe')\n",
      "reason":"Unsafe","regression_example":"Buyer preference"}

 def checks(self,mode="success"):
  calls=[]
  def syntax(candidate):
   calls.append("syntax");return mode!="syntax"
  def compare(original,candidate):
   calls.append("compare");return {"status":"behavior_passed" if mode!="behavior" else "rejected_regression_or_no_improvement"}
  def stress(original,candidate):
   calls.append("stress");return {"status":"stress_passed" if mode!="stress" else "stress_failed"}
  def gates(candidate):
   calls.append("gates");return {"status":"passed" if mode!="gate" else "sandbox_regression_failed","total":117}
  return {"syntax":syntax,"compare":compare,"stress":stress,"gates":gates,"stage":p.stage},calls

 def test_retry_uses_validation_feedback_then_stages_only_passed_candidate(self):
  with tempfile.TemporaryDirectory() as tmp,\
      patch.object(s,"STATE",Path(tmp)/"state.json"),\
      patch.object(p,"STAGE",Path(tmp)/"staged"):
   state=s.previous_state();calls=[];received=[]
   def fakeapi(key,system,prompt,schema,task):
    parsed=json.loads(prompt);received.append(parsed)
    return self.p_bad if len(received)==1 else self.p_good
   checks,gates=self.checks()
   result=it.attempt_sequence(self.issue,self.source,self.method,fakeapi,"fictional-key",state,checks=checks)
   self.assertEqual(result["status"],"review_ready_not_deployed")
   self.assertEqual([v["outcome"] for v in result["attempts"]],
       ["static_rejected","review_ready_not_deployed"])
   self.assertEqual(received[0]["previous_rejection_feedback"],[])
   self.assertEqual(received[1]["previous_rejection_feedback"][0]["outcome"],"static_rejected")
   self.assertEqual(gates,["syntax","compare","stress","gates"])
   self.assertEqual(state["api_calls"],2)
   report=json.loads((Path(tmp)/"staged"/(result["proposal_id"]+".json")).read_text())
   self.assertFalse(report["automatic_deployment_allowed"])
   self.assertTrue(report["independent_human_review_required"])
   self.assertEqual((Path(tmp)/"staged"/(result["proposal_id"]+".json")).stat().st_mode&0o777,0o600)
   self.assertEqual(result["bot_modified"],False)

 def test_failing_gate_blocks_all_staging_and_provides_feedback(self):
  for mode,status in [("syntax","syntax_rejected"),("behavior","behavior_rejected"),
      ("stress","stress_rejected"),("gate","regression_rejected")]:
   with self.subTest(mode=mode),tempfile.TemporaryDirectory() as tmp,\
      patch.object(s,"STATE",Path(tmp)/"state.json"),\
      patch.object(p,"STAGE",Path(tmp)/"staged"):
    state=s.previous_state();checks,calls=self.checks(mode=mode)
    sent=[]
    def actor(*args):
     sent.append(json.loads(args[2]));return self.p_good
    out=it.attempt_sequence(self.issue,self.source,self.method,actor,
         "test",state,checks=checks)
    self.assertEqual(out["status"],"no_candidate_passed_validation")
    self.assertEqual(out["attempts"][0]["outcome"],status)
    self.assertEqual(out["attempts"][1]["outcome"],"duplicate_candidate")
    self.assertFalse((Path(tmp)/"staged").exists())
    self.assertEqual(sent[1]["previous_rejection_feedback"][0]["outcome"],status)

 def test_daily_limit_and_missing_key_fail_closed(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(s,"STATE",Path(tmp)/"state.json"):
   state=s.previous_state()
   self.assertEqual(it.attempt_sequence(self.issue,self.source,self.method,lambda *a:None,
      None,state)["status"],"api_unavailable")
   called=[]
   r=it.attempt_sequence(self.issue,self.source,self.method,
      lambda *a:called.append(True), "dummy",state,prior_attempts=p.MAX_DAILY)
   self.assertEqual(r["status"],"shared_daily_cap")
   self.assertEqual(called,[])
   self.assertEqual(state["api_calls"],0)

 def test_api_failure_aborts_without_extra_retries(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(s,"STATE",Path(tmp)/"state.json"):
   calls=[]
   def actor(*a):
    calls.append(True);raise RuntimeError("Provider unavailable")
   state=s.previous_state()
   r=it.attempt_sequence(self.issue,self.source,self.method,actor,"key",state)
   self.assertEqual(r["status"],"api_unavailable")
   self.assertEqual(len(calls),1)
   self.assertEqual(state["api_calls"],1)

 def test_does_not_accept_unbounded_attempts(self):
  with self.assertRaises(ValueError):
   it.attempt_sequence(self.issue,self.source,self.method,lambda *a:None,
       "key",s.previous_state(),max_attempts=3)

 def test_feedback_is_bounded_and_has_no_user_submitted_error_string(self):
  self.assertEqual(len(it.feedback_message(["static_rejected"]*15)),2)
  self.assertEqual(it.feedback_message(["new_random_status"]),[])
  payload=json.dumps(it.feedback_message(["syntax_rejected"]))
  self.assertNotIn("API_KEY",payload)
  self.assertNotIn("stacktrace",payload)
  self.assertNotIn("/opt/softmobile",payload)

 def test_active_bot_is_not_a_possible_retry_action(self):
  src=Path(it.__file__).read_text()
  self.assertNotIn("Messages::MessageBuilder",src)
  self.assertNotIn("rails runner",src)
  self.assertNotIn("fixer.deploy(",src)
  self.assertNotIn("LIVE.write_text",src)
  self.assertNotIn("eval(",src)
  self.assertNotIn("exec(",src)

if __name__=="__main__":unittest.main()
