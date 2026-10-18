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

if __name__=="__main__":unittest.main()
