import unittest
from unittest.mock import Mock
import semantic_generalization as s
class SemanticTests(unittest.TestCase):
 def test_requires_existing_reviewed_family(self):
  with self.assertRaises(ValueError):s.build("unrelated",{"version":1,"pilot_conversation_id":3,"rules":[]})
 def test_no_model_code_or_unverified_price(self):
  self.assertIn("needs_human:true",s.RUBY_RULE)
  self.assertNotIn("1000",s.RUBY_RULE)
  self.assertNotIn("eval(",s.RUBY_RULE)
  self.assertNotIn("system(",s.RUBY_RULE)
 def test_gate_fails_on_negative_regression(self):
  raw=[{"reply":"not safe","tag":"normal","human":False} for i in s.POSITIVE+s.NEGATIVE]
  response=[{"reply":s.learn.FAMILIES[s.NAME]["reply"],"tag":"sm_semantic_accessory","human":True}
            for p in s.POSITIVE]+[{"reply":"bad","tag":"changed","human":True} for p in s.NEGATIVE]
  runner=Mock(side_effect=[raw,response])
  outcome=s.gates("old","candidate",inspect_fn=runner,syntax=lambda x:True,
                  regression=lambda x:{"status":"passed","total":117})
  self.assertEqual(outcome["status"],"rejected")
  self.assertEqual(outcome["reason"],"negative_regression")
 def test_requires_six_real_improvements(self):
  row={"reply":s.learn.FAMILIES[s.NAME]["reply"],"tag":"sm_semantic_accessory","human":True}
  allsame=[row for x in s.POSITIVE+s.NEGATIVE]
  outcome=s.gates("old","new",inspect_fn=Mock(side_effect=[allsame,allsame]),
      syntax=lambda x:True,regression=lambda x:{"status":"passed","total":117})
  self.assertEqual(outcome["reason"],"not_enough_new_coverage")
if __name__=="__main__":unittest.main()
