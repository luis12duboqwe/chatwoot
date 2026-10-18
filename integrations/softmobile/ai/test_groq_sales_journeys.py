#!/usr/bin/env python3
"""Reproducible tests: no API calls, no real customer chats."""
import os
import unittest
from unittest.mock import patch
import journey_memory as memory
import groq_sales_journeys as lab
from variant_preference import expected_selection

class JourneyMemoryTests(unittest.TestCase):
 def test_explicit_fallback_survives_delivery_question(self):
  self.assertEqual(memory.history_snapshot([
   "Busco iPhone 15 Pro 512GB negro",
   "Si no hay 512GB negro, mejor 256GB azul",
   "¿Lo puedo retirar en Choloma?"]),
   {"model":"iPhone 15 Pro","storage_gb":256,"color_options":"azul","city":"Choloma"})
 def test_price_comparison_does_not_overwrite_chosen_variant(self):
  self.assertEqual(memory.history_snapshot([
   "Quiero Samsung S24 Ultra 256GB negro",
   "¿Cuánto cuesta el de 128GB azul?",
   "¿Qué garantía tiene?"]),
   {"model":"Samsung S24 Ultra","storage_gb":256,"color_options":"negro"})
 def test_explicit_change_updates_correct_field_only(self):
  self.assertEqual(memory.history_snapshot([
   "Busco iPhone 14 Pro Max 128GB negro","Mejor el blanco",
   "¿Qué garantía tiene?"]),
   {"model":"iPhone 14 Pro Max","storage_gb":128,"color_options":"blanco"})
 def test_buyer_ambiguous_variant_clears_selected_fields(self):
  self.assertEqual(memory.history_snapshot([
   "Busco iPhone 15 Pro 128GB negro",
   "Quiero 128GB negro o 256GB azul"]),{"model":"iPhone 15 Pro"})
 def test_private_data_not_part_of_context(self):
  self.assertEqual(memory.history_snapshot([
   "iPhone 15 Pro 256GB negro",
   "Mi número es 9999-0000 y dirección colonia Centro, ¿ya llegó?"
  ]),{"model":"iPhone 15 Pro","storage_gb":256,"color_options":"negro"})
 def test_rejects_unbounded_history(self):
  self.assertEqual(memory.history_snapshot(["iPhone 15 Pro 128GB negro"]*5),{})
 def test_rejected_color_not_stored_as_desired(self):
  self.assertEqual(memory.history_snapshot([
   "iPhone 15 Pro 256GB negro",
   "No quiero negro"]),
   {"model":"iPhone 15 Pro","storage_gb":256})
 def test_negative_then_affirmative_color_update(self):
  self.assertEqual(memory.history_snapshot([
   "Busco iPhone 15 Pro 128GB negro","No quiero negro, mejor azul",
   "¿Puedo pasar a Choloma?"]),
   {"model":"iPhone 15 Pro","storage_gb":128,"color_options":"azul",
    "city":"Choloma"})
 def test_comparison_question_must_not_erase_selected_color(self):
  self.assertEqual(memory.history_snapshot([
   "Quiero iPhone 15 Pro 128GB negro","¿Y el azul cuesta lo mismo?",
   "¿Cuándo puedo comprar?"]),
   {"model":"iPhone 15 Pro","storage_gb":128,"color_options":"negro"})
 def test_rejected_only_color_is_unselected(self):
  self.assertEqual(memory.history_snapshot(["Quiero 256GB azul","No quiero azul"]),
                   {"storage_gb":256})
 def test_no_history_sent_to_api(self):
  messages=["Busco iPhone 15 Pro 256GB negro","Mejor azul"]
  data=memory.history_snapshot(messages)
  self.assertEqual(set(data),{"model","storage_gb","color_options"})
  self.assertFalse(any(isinstance(x,list) for x in data.values()))

class JourneyShadowTests(unittest.TestCase):
 def test_four_journeys_twelve_turns(self):
  self.assertEqual(len(lab.JOURNEYS),4)
  self.assertEqual(sum(len(x["turns"]) for x in lab.JOURNEYS),lab.MAX_API_CALLS)
  self.assertEqual(len({x["id"] for x in lab.JOURNEYS}),4)
 def test_mock_all_valid_when_matches_context(self):
  prompts=[]
  def api(clean,key):
   prompts.append(clean)
   latest=expected_selection(clean["message"])
   old=memory.history_snapshot([])
   old.update(clean["context"])
   full=dict(old)
   if latest["storage_gb"] is not None:full["storage_gb"]=latest["storage_gb"]
   if latest["color"] is not None:full["color_options"]=latest["color"]
   # test selected model in question; use simple deterministic detector
   import sales_context
   new_model=sales_context.preference_snapshot([clean["message"]]).get("model")
   if new_model:full["model"]=new_model
   return {"intent":"consulta","model":full.get("model"),
    "storage_gb":int(full["storage_gb"]) if full.get("storage_gb") else None,
    "color_options":[full["color_options"]] if full.get("color_options") else [],
    "city":full.get("city"),"pickup_location":None,"human_review":True,
    "suggested_reply":"Un asesor verificará las condiciones antes de comprar."}
  with patch.dict(os.environ,{"SOFTMOBILE_AI_ENABLED":"true"}):
   result=lab.execute(api=api,key_provider=lambda:"fictional-key")
  self.assertEqual(result["api_calls"],12)
  self.assertEqual(result["public_messages_sent"],0)
  self.assertFalse(result["public_auto_reply_enabled"])
  self.assertEqual(len(prompts),12)
  for p in prompts:
   self.assertNotIn("history",p)
   self.assertFalse(any(isinstance(v,list) for v in p["context"].values()))
 def test_provider_failure_not_counted_as_pass(self):
  def api(*args):
   raise lab.PilotError("No valid data")
  with patch.dict(os.environ,{"SOFTMOBILE_AI_ENABLED":"true"}):
   result=lab.execute(api=api,key_provider=lambda:"fictional-key")
  self.assertFalse(result["all_passed"])
  self.assertEqual(result["invalid_responses"],12)
  self.assertEqual(result["validated_turns"],0)
 def test_disabled_mode_never_calls_provider(self):
  calls=[]
  with patch.dict(os.environ,{"SOFTMOBILE_AI_ENABLED":"false"}):
   with self.assertRaises(RuntimeError):
    lab.execute(api=lambda *a:calls.append(True),key_provider=lambda:"fictional-key")
  self.assertEqual(calls,[])
if __name__=="__main__":unittest.main()
