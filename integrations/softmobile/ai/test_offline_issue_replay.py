import copy,json,unittest
from unittest.mock import patch
import offline_issue_replay as f

SCENARIO={"category":"questions","messages":["Busco un iPhone 14 Pro Max",
  "¿Y la funda?","¿Cuánto más costaría?"]}
ISSUE={"id":"case-test-0001","status":"synthetic_unverified","category":"questions",
       "scenario":SCENARIO,
       "evidence":[{"buyer":s,"bot":"Un asesor debe verificar las condiciones"}
         for s in SCENARIO["messages"]],
       "grade":{"error":True},
       "static_flags":["exact_repeat"]}

class OfflineReplayTests(unittest.TestCase):
 def test_ruby_runner_explicitly_disables_network_and_mounts(self):
  row={"id":"case-test-0001","scenario":SCENARIO}
  class Result:
   returncode=0
   stdout=f.MARK+json.dumps([{"id":"case-test-0001","category":"questions",
      "turns":[{"buyer":s,"bot":"Un asesor debe verificar las condiciones"}
         for s in SCENARIO["messages"]]}])
   stderr=""
  calls=[]
  def runner(argv,**kwargs):
   calls.append((argv,kwargs))
   return Result()
  output=f.isolated_replay([row],source="module SoftMobileSales;end",runner=runner)
  self.assertEqual(len(output),1)
  cmd,kwargs=calls[0]
  self.assertIn("--network",cmd)
  self.assertEqual(cmd[cmd.index("--network")+1],"none")
  self.assertIn("--read-only",cmd)
  self.assertNotIn("-v",cmd)
  self.assertNotIn("--mount",cmd)
  self.assertEqual(kwargs["timeout"],70)
 def test_static_only_flags_are_not_proven_customer_errors(self):
  current=copy.deepcopy(ISSUE)
  replay={"id":current["id"],"category":"questions",
     "turns":[{"buyer":s,"bot":"Un asesor debe verificar las condiciones"}
             for s in SCENARIO["messages"]]}
  with patch.object(f.lab,"static_flags",return_value=["exact_repeat"]):
   item=f.classify_replay(current,replay)
  self.assertEqual(item["outcome"],"previous_flags_reproduced")
  self.assertNotIn("confirmed_customer_bug",item)
 def test_ai_only_is_still_unverified_when_no_flags(self):
  issue=copy.deepcopy(ISSUE);issue["static_flags"]=[]
  rows={"id":issue["id"],"category":"questions","turns":[
     {"buyer":s,"bot":"Un asesor debe verificar"} for s in SCENARIO["messages"]]}
  with patch.object(f.lab,"static_flags",return_value=[]):
   out=f.classify_replay(issue,rows)
  self.assertEqual(out["outcome"],"ai_only_still_unverified")
 def test_summary_without_automatic_code_promotion(self):
  def stub(rows,source=None):
   return [{"id":x["id"],"category":"questions","turns":[{"buyer":s,"bot":"A revisar"}
      for s in x["scenario"]["messages"]]} for x in rows]
  with patch.object(f.lab,"static_flags",return_value=[]):
   r=f.assess(issues=[copy.deepcopy(ISSUE)],runner=stub)
  self.assertEqual(r["api_calls"],0)
  self.assertEqual(r["public_messages_sent"],0)
  self.assertFalse(r["real_inventory_changed"])
  self.assertTrue(r["no_auto_promotion"])
  self.assertEqual(r["replayed"],1)
 def test_candidate_diff_catches_new_flags_not_real_incidents(self):
  row={"id":"one","new_flags":["exact_repeat"]}
  base={"results":[row]}
  future={"results":[{"id":"one","new_flags":["exact_repeat","payment_choice_repeat"]}]}
  diff=f.compare(base,future)
  self.assertEqual(diff["new_flags_in_candidate"],1)
  self.assertTrue(diff["candidate_requires_review"])
  self.assertIn("hypotheses",diff["note"])
 def test_count_mismatch_is_fail_closed(self):
  with patch.object(f.lab,"static_flags",return_value=[]):
   with self.assertRaises(RuntimeError):
    f.assess(issues=[copy.deepcopy(ISSUE)],runner=lambda *args,**kwargs:[])
 def test_untrusted_scenario_is_not_executed(self):
  bogus=copy.deepcopy(ISSUE)
  bogus["scenario"]["messages"][0]="Me llamo Pedro y mi teléfono es 9999"
  result=f.assess(issues=[bogus],runner=lambda *args,**kwargs:[])
  self.assertEqual(result["replayed"],0)
if __name__=="__main__":unittest.main()
