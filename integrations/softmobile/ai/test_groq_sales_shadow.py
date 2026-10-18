#!/usr/bin/env python3
"""Portable offline assertions for finite Groq shadow evaluation."""
import unittest
from unittest.mock import patch
import groq_sales_shadow as shadow
from variant_preference import expected_selection

class ShadowEvaluationTests(unittest.TestCase):
 def test_exactly_seven_nonidentifiable_fictional_cases(self):
  self.assertEqual(len(shadow.CASES),7)
  self.assertEqual(len({x["id"] for x in shadow.CASES}),7)
  for c in shadow.CASES:
   self.assertTrue(c["message"])
   self.assertEqual(set(c),{"id","message","context","must_human"})
   self.assertNotIn("password",repr(c).lower())
 def test_valid_mock_api_never_writes_to_customer(self):
  def mock_suggest(clean,key):
   pref=expected_selection(clean["message"])
   return {"intent":"consulta","model":"iPhone 15 Pro",
    "storage_gb":pref["storage_gb"],
    "color_options":[pref["color"]] if pref["color"] else [],
    "city":None,"pickup_location":None,
    "human_review":True,
    "suggested_reply":"Un asesor puede confirmar las condiciones antes de comprar."}
  with patch.dict(shadow.os.environ,{"SOFTMOBILE_AI_ENABLED":"true"}):
   r=shadow.evaluate(api=mock_suggest,key_provider=lambda:"fake-key")
  self.assertTrue(r["all_passed"])
  self.assertEqual(r["valid_structured"],7)
  self.assertEqual(r["preferred_variant_match"],7)
  self.assertEqual(r["real_messages_sent"],0)
  self.assertEqual(r["pilot_code_modified"],False)
 def test_failure_is_not_misclassified_as_success(self):
  def simulated_failure(clean,key):
   raise shadow.PilotError("No hay sugerencia IA válida")
  with patch.dict(shadow.os.environ,{"SOFTMOBILE_AI_ENABLED":"true"}):
   result=shadow.evaluate(api=simulated_failure,key_provider=lambda:"fake-key")
  self.assertFalse(result["all_passed"])
  self.assertEqual(result["valid_structured"],0)
  self.assertEqual(len(result["results"]),7)
  self.assertEqual({x["rejection_category"] for x in result["results"]},
                   {"invalid_response_or_provider"})
 def test_disabled_flag_rejects_without_invoking_api(self):
  called=[]
  with patch.dict(shadow.os.environ,{"SOFTMOBILE_AI_ENABLED":"false"}):
   with self.assertRaises(RuntimeError):
    shadow.evaluate(api=lambda *x:called.append(1),key_provider=lambda:"fake-key")
  self.assertEqual(called,[])
 def test_human_handoff_required_for_commercial_sensitive_cases(self):
  def unsafe_draft(clean,key):
   p=expected_selection(clean["message"])
   return {"intent":"consulta","model":"iPhone 15",
    "storage_gb":p["storage_gb"],
    "color_options":[p["color"]] if p["color"] else [],
    "human_review":False,"suggested_reply":"¿Querés comparar ambos modelos?"}
  with patch.dict(shadow.os.environ,{"SOFTMOBILE_AI_ENABLED":"true"}):
   result=shadow.evaluate(api=unsafe_draft,key_provider=lambda:"fake")
  self.assertFalse(result["all_passed"])
  self.assertTrue(any(x["api_ok"] and not x["human_handoff"] for x in result["results"]))
if __name__=="__main__":unittest.main()
