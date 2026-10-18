import unittest
import conversion_candidate_review as r

class FinancingPatchTests(unittest.TestCase):
 def test_no_arbitrary_patch_when_anchor_missing(self):
  with self.assertRaises(ValueError):r.create_candidate("arbitrary code")
 def test_only_one_fully_scoped_model_rule_may_change(self):
  mock=("PILOT_CONVERSATION_ID = 3\nAUTO_REPLY_LIMIT = 1\n"
        +r.OLD+"\n"+"# no-op\n"*1100)
  target=r.create_candidate(mock)
  self.assertEqual(target.count(r.NEW),1)
  self.assertNotIn(r.OLD,target)
  self.assertEqual(target.replace(r.NEW,r.OLD,1),mock)
 def test_duplicate_or_repeated_applying_is_rejected(self):
  mock=("PILOT_CONVERSATION_ID = 3\nAUTO_REPLY_LIMIT = 1\n"
        +r.OLD+"\n"+"# no-op\n"*1100)
  with self.assertRaises(ValueError):r.create_candidate(mock+r.OLD)
  with self.assertRaises(ValueError):r.create_candidate(r.create_candidate(mock))
 def test_unseen_holdout_is_required_before_staging(self):
  import inspect
  code=inspect.getsource(r.evaluate)
  self.assertIn('unseen_financing_regression',code)
  self.assertIn('financing_holdout.verify',code)
 def test_gates_require_real_improvement_and_safe_financing(self):
  from conversion_training_lab import FAMILIES
  before={"scenarios":72,"passed":60,"failed":12,
          "by_family":{x:{"passed":0 if x=="financing" else 12} for x in FAMILIES}}
  after={"scenarios":72,"passed":72,"failed":0,"unverified_promises":0,
         "by_family":{x:{"passed":12} for x in FAMILIES}}
  self.assertTrue(r.admissible(before,after))
  after["unverified_promises"]=1
  self.assertFalse(r.admissible(before,after))
  after["unverified_promises"]=0
  after["by_family"]["negotiation"]["passed"]=11
  self.assertFalse(r.admissible(before,after))
if __name__=="__main__":unittest.main()
