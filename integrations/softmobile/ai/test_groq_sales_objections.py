#!/usr/bin/env python3
"""Offline tests for the 20-turn private sales/objection evaluation."""
import os
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

import groq_sales_objections as lab
from journey_memory import history_snapshot
from variant_preference import expected_selection
from groq_pilot import PilotError
from suggestion_guard import guarded_draft

class ObjectionsTests(unittest.TestCase):
 def test_four_journeys_exactly_twenty_fictional_turns(self):
  self.assertEqual(len(lab.JOURNEYS),4)
  self.assertEqual(sum(len(x["turns"]) for x in lab.JOURNEYS),lab.MAX_CALLS)
  self.assertEqual({x["id"] for x in lab.JOURNEYS},
   {"budget-discount-inspection-close","finance-price-objection-warranty-close",
    "color-change-compare-delivery-close","trade-in-coverage-inspection-pay"})
 def test_successful_mock_preserves_context_with_no_chatwoot_actions(self):
  seen=[]
  def fake_api(clean,key):
   seen.append(clean)
   context=clean["context"]
   choice=expected_selection(clean["message"])
   import groq_pilot
   if groq_pilot._comparison_only(clean):
    choice={"storage_gb":None,"color":None,"ambiguous":False}
   new=history_snapshot([clean["message"]])
   return {"intent":"consulta","model":new.get("model",context.get("model")),
    "storage_gb":choice["storage_gb"] or context.get("storage_gb"),
    "color_options":[choice["color"] or context.get("color_options")]
       if choice["color"] or context.get("color_options") else [],
    "human_review":True,"city":None,"pickup_location":None,
    "suggested_reply":"Asesor: comparar opciones y modelos, precio y presupuesto, descuento y promoción, cuota, financiación, banco, garantía, estado y revisión, entrega y retiro, parte de pago, valoración, compra disponible a confirmar."}
  with patch.dict(os.environ,{"SOFTMOBILE_AI_ENABLED":"true"}):
   result=lab.execute(api=fake_api,key_provider=lambda:"fictitious-key")
  self.assertEqual(result["api_calls"],20)
  self.assertEqual(result["public_messages_sent"],0)
  self.assertFalse(result["pilot_bot_modified"])
  self.assertEqual(result["real_orders_created"],0)
  self.assertEqual(len(seen),20)
  for clean in seen:
   self.assertNotIn("history",clean)
   self.assertFalse(any(isinstance(x,list) for x in clean["context"].values()))
 def test_rate_limit_bails_out_and_does_not_spend_eighteen_more_calls(self):
  calls=[]
  def api(*a):
   calls.append(True)
   if len(calls)==2:
    try:raise HTTPError("https://provider.invalid",429,"quota exceeded",{},None)
    except HTTPError as e:raise PilotError("Provider unavailable") from e
   raise PilotError("invalid")
  with patch.dict(os.environ,{"SOFTMOBILE_AI_ENABLED":"true"}):
   result=lab.execute(api=api,key_provider=lambda:"fictitious-key")
  self.assertTrue(result["provider_aborted"])
  self.assertEqual(len(calls),2)
  self.assertEqual(result["api_calls"],2)
  self.assertEqual(result["not_run_provider"],18)
  self.assertEqual(result["failure_categories"]["provider_rate_limited"],1)
  self.assertEqual(result["public_messages_sent"],0)
 def test_parser_only_local_failures_can_continue(self):
  def api(*a):raise PilotError("Invalid response")
  with patch.dict(os.environ,{"SOFTMOBILE_AI_ENABLED":"true"}):
   result=lab.execute(api=api,key_provider=lambda:"fictitious-key")
  self.assertEqual(result["api_calls"],20)
  self.assertFalse(result["provider_aborted"])
  self.assertEqual(result["invalid_responses"],20)
 def test_synthetic_guard_topic_is_not_generic_warranty_reply(self):
  clean={"message":"¿Reciben mi celular como parte de pago?","context":{"model":"iPhone 15"}}
  draft,blocked=guarded_draft({"suggested_reply":"Un asesor lo revisará.","human_review":True},clean)
  self.assertTrue(blocked)
  self.assertIn("parte de pago",draft["suggested_reply"])
 def test_guarded_discount_does_not_invent_prices(self):
  clean={"message":"¿Me hacen descuento en efectivo?","context":{}}
  draft,blocked=guarded_draft({"suggested_reply":"El precio final es L 10,000","human_review":False},clean)
  self.assertTrue(blocked)
  self.assertIn("precio",draft["suggested_reply"])
  self.assertNotIn("10,000",draft["suggested_reply"])
  self.assertTrue(draft["human_review"])
 def test_daily_real_execution_limit_is_persisted(self):
  import tempfile
  from pathlib import Path
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as temp:
   with patch.object(lab,"STATE",Path(temp)/"quota.json"):
    self.assertEqual(lab.reserve_real_run(),1)
    self.assertEqual(lab.reserve_real_run(),2)
    with self.assertRaises(RuntimeError):
     lab.reserve_real_run()
 def test_commercial_mismatch_classification_does_not_expose_prompt(self):
  self.assertEqual(lab.failure_category(PilotError(
      "La IA cambió la capacidad elegida al comparar precios.")),
      "preference_validation_rejected")
 def test_strict_quality_gate_rejects_keyword_spam(self):
  before=lambda *a:"Asesor: comparar opciones y modelos, precio y presupuesto, descuento y promoción, cuota, financiación, banco, garantía, estado y revisión, entrega y retiro, parte de pago, valoración, compra disponible a confirmar."
  from sales_quality_gate import assess
  self.assertFalse(assess(before(),"payment")["specific"])
  self.assertFalse(assess(before(),"warranty")["specific"])
 def test_shared_budget_counts_calls_and_enforces_utc_limit(self):
  import tempfile
  from pathlib import Path
  with tempfile.TemporaryDirectory() as root:
   root=Path(root)
   with patch.object(lab.lab,"STATE",root/"shared.json"),patch.object(lab.lab,"LOCK",root/"shared.lock"):
    for _ in range(2):lab.reserve_shared_call()
    import json
    self.assertEqual(json.loads((root/"shared.json").read_text())["api_calls"],2)
    with patch.object(lab.lab,"MAX_DAILY",2):
     with self.assertRaises(lab.SharedBudgetExceeded):
      lab.reserve_shared_call()
 def test_budget_unavailable_never_calls_groq(self):
  calls=[]
  def quota():raise lab.SharedBudgetExceeded("Shared daily cap")
  with patch.dict(os.environ,{"SOFTMOBILE_AI_ENABLED":"true"}):
   result=lab.execute(api=lambda *a:calls.append(1),key_provider=lambda:"fixture",budget_hook=quota)
  self.assertEqual(calls,[])
  self.assertEqual(result["api_calls"],0)
  self.assertEqual(result["failure_categories"]["shared_daily_budget_exhausted"],1)
  self.assertEqual(result["not_run_provider"],19)
 def test_disabled_mode_cannot_access_provider(self):
  touched=[]
  with patch.dict(os.environ,{"SOFTMOBILE_AI_ENABLED":"false"}):
   with self.assertRaises(RuntimeError):
    lab.execute(api=lambda *x:touched.append(1),key_provider=lambda:"key")
  self.assertEqual(touched,[])

if __name__=="__main__":unittest.main()
