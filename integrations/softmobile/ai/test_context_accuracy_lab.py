import unittest
from unittest.mock import Mock,patch
import context_accuracy_lab as c
import variant_context_candidate as v
import variant_context_ai_review as ai

class NewContextTests(unittest.TestCase):
 def test_all_examples_are_unique_and_fictional(self):
  self.assertEqual(len(c.CASES),8)
  self.assertEqual(len({x[0] for x in c.CASES}),8)
  self.assertTrue(all("@" not in str(x) for x in c.CASES))
 def test_correct_choice_is_measured_independently_of_ruby(self):
  def fake(rows,source=None):
   return [{"id":row["id"],"turns":[{"bot":next(x[2] for x in c.CASES if x[0]==row["id"])}]}
           for row in rows]
  r=c.evaluate(source="simulated Ruby",runner=fake)
  self.assertEqual(r["passed"],8)
  self.assertFalse(r["deployed"])
  self.assertEqual(r["api_calls"],0)
 def test_wrong_context_is_reported_not_accepted(self):
  def fake(rows,source=None):
   return [{"id":row["id"],"turns":[{"bot":"Un asesor debe verificar los datos."}]}
           for row in rows]
  r=c.evaluate(source="simulated Ruby",runner=fake)
  self.assertEqual(r["passed"],0)
 def test_review_patch_must_have_exact_anchors(self):
  with self.assertRaises(ValueError):v.build("untrusted text")
 def test_provider_cooldown_does_not_bypass_independent_grade(self):
  fixture={"status":"review_ready_needs_independent_ai",
            "candidate_sha256":"fake"}
  with patch.object(ai,"_load",return_value=fixture),patch.object(ai,"state_at",return_value=2),patch.object(ai,"stored_key") as key:
   r=ai.evaluate()
   self.assertNotEqual(r["status"],"ai_approved_for_review")
   self.assertFalse(r["ai_approved"])
   key.assert_not_called()

 def test_reuse_one_good_groq_verdict_without_second_call(self):
  import hashlib,json,tempfile
  from pathlib import Path
  from datetime import datetime,timezone
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);source="fictional Ruby only"
   sha=hashlib.sha256(source.encode()).hexdigest()
   (root/"candidate.rb").write_text(source)
   now=datetime.now(timezone.utc).isoformat()
   existing={"candidate_sha256":sha,"status":"provider_or_grade_unavailable",
     "at":now,"judgments":[{"case":"color-black-to-blue",
       "error":False,"reason":"Correcto","reviewed_at":now}]}
   full={"status":"review_ready_needs_independent_ai","candidate_sha256":sha}
   stage={"candidate_sha256":sha,"stage_file":"candidate.rb"}
   def load(file,default=None):
    if file==ai.REPORT:return existing
    if file==ai.QA/"variant-context-full-review.json":return full
    if file==ai.patch.REPORT:return stage
    if file==ai.lab.STATE:return ai.lab.previous_state()
    return default
   answer={"error":False,"severity":"low","category":"no_issue",
      "reason":"Se atendió la preferencia","suggested_reply":"","expected_behavior":""}
   observed=[]
   def api(*args):
    observed.append(args);return answer
   fake=lambda rows,source=None:[{"id":rows[0]["id"],
      "turns":[{"buyer":v,"bot":"El cliente prefiere 64GB"} for v in rows[0]["scenario"]["messages"]]}]
   with patch.object(ai,"QA",root),patch.object(ai,"REPORT",root/"prior.json"),\
      patch.object(ai.patch,"STAGE",root),patch.object(ai.patch,"REPORT",root/"stage.json"),\
      patch.object(ai,"_load",side_effect=load),patch.object(ai,"state_at",return_value=0),\
      patch.object(ai.replay,"isolated_replay",side_effect=fake),\
      patch.object(ai.lab,"STATE",root/"budget.json"):
    result=ai.evaluate(api=api,key="fake")
   self.assertTrue(result["ai_approved"])
   self.assertEqual(result["status"],"ai_approved_for_review")
   self.assertEqual(result["ai_calls"],1)
   self.assertEqual(len(observed),1)

if __name__=="__main__":unittest.main()
