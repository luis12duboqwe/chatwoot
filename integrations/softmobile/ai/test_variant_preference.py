#!/usr/bin/env python3
"""Real consumer-phrase unit tests; simulated inputs only, no Groq requests."""
import unittest
import groq_pilot as pilot
from variant_preference import expected_selection

class VariantPreferenceTests(unittest.TestCase):
 def test_clear_preference_beats_later_comparison(self):
  cases=[
   ("Prefiero el azul, pero ¿cuánto cuesta el negro?",None,"azul"),
   ("Prefiero el de 256 GB azul, ¿cuánto cuesta el de 128 GB negro?",256,"azul"),
   ("Si no hay 512GB negro, mejor 256GB azul",256,"azul"),
   ("Ahora prefiero el de 128GB rojo",128,"rojo"),
   ("No quiero negro, prefiero azul",None,"azul"),
   ("Prefiero blanco, pero ¿qué tal el dorado?",None,"blanco"),
   ("Busco 256GB morado en Choloma",256,"morado"),
   ("Me quedo con el de 512GB gris, no el azul",512,"gris"),
   ("Antes pregunté por negro, mejor el verde",None,"verde"),
  ]
  for raw,gb,color in cases:
   with self.subTest(raw=raw):
    p=expected_selection(raw)
    self.assertFalse(p["ambiguous"])
    self.assertEqual(p["storage_gb"],gb)
    self.assertEqual(p["color"],color)
 def test_ambiguous_comparisons_do_not_force_final_mention(self):
  cases=[
   "Quiero 256 GB azul o 128 GB negro",
   "¿Cuál me conviene, 256GB azul o 128GB negro?",
   "¿Negro o azul?",
   "No quiero negro",
   "¿Hay 128GB o 256GB?",
  ]
  for raw in cases:
   with self.subTest(raw=raw):
    p=expected_selection(raw)
    self.assertTrue(p["ambiguous"])
    self.assertIsNone(p["color"])
    self.assertIsNone(p["storage_gb"])
 def test_validation_accepts_primary_preference_not_last_mentioned(self):
  clean=pilot.prepare({"conversation_id":3,"message":
   "Prefiero el de 256 GB azul, ¿cuánto cuesta el de 128 GB negro?",
   "context":{"model":"iPhone 15 Pro","storage_gb":128,"color_options":"negro"}})
  answer={"intent":"consulta","model":"iPhone 15 Pro","storage_gb":256,
      "color_options":["azul"],"city":None,"pickup_location":None,
      "human_review":False,
      "suggested_reply":"Un asesor puede confirmar condiciones antes de comprar."}
  result=pilot.validate(dict(answer),clean)
  self.assertEqual(result["storage_gb"],256)
  self.assertEqual(result["color_options"],["azul"])
  self.assertTrue(result["human_review"]) # price question
  with self.assertRaises(pilot.PilotError):
   pilot.validate(dict(answer,storage_gb=128),clean)
  with self.assertRaises(pilot.PilotError):
   pilot.validate(dict(answer,color_options=["negro"]),clean)
 def test_conditional_latest_explicit_selection_cannot_be_stale(self):
  clean=pilot.prepare({"conversation_id":3,"message":
    "Si no tienen 512 GB negro, mejor 256 GB azul",
    "context":{"storage_gb":512,"color_options":["negro"]}})
  prototype={"intent":"compra","model":"iPhone 15 Pro","storage_gb":256,
    "color_options":["azul"],"city":None,"pickup_location":None,
    "human_review":True,
    "suggested_reply":"Un asesor verificará la opción azul antes de la compra."}
  self.assertEqual(pilot.validate(dict(prototype),clean)["storage_gb"],256)
  with self.assertRaises(pilot.PilotError):
   pilot.validate(dict(prototype,storage_gb=512),clean)
 def test_multi_variant_request_requires_human_review(self):
  clean=pilot.prepare({"conversation_id":3,
   "message":"Quiero 128 GB negro o 256 GB azul, ¿cuál recomiendas?"})
  ans={"intent":"consulta","model":"iPhone 15","storage_gb":128,
       "color_options":["negro"],"city":None,"pickup_location":None,
       "human_review":False,
       "suggested_reply":"¿Querés comparar ambos modelos primero?"}
  self.assertTrue(pilot.validate(ans,clean)["human_review"])
 def test_pickup_and_inspection_always_need_human_review(self):
  for question in ("¿Lo puedo retirar en Choloma?",
                   "¿Puedo probarlo antes de pagar?",
                   "¿Cuándo recibo mi equipo?",
                   "¿Tienen entrega a San Pedro Sula?"):
   with self.subTest(question=question):
    clean=pilot.prepare({"conversation_id":3,"message":question,
      "context":{"model":"iPhone 15 Pro","storage_gb":"256","color_options":"azul"}})
    draft={"intent":"consulta","model":"iPhone 15 Pro","storage_gb":256,
      "color_options":["azul"],"city":None,"pickup_location":None,
      "human_review":False,
      "suggested_reply":"Un asesor puede confirmar las condiciones."}
    self.assertTrue(pilot.validate(draft,clean)["human_review"])
 def test_comparison_question_is_not_selected_variant(self):
  clean=pilot.prepare({"conversation_id":3,
    "message":"¿Y el negro de 128GB cuesta lo mismo?",
    "context":{"model":"iPhone 14 Pro Max","storage_gb":256,"color_options":"blanco"}})
  import json
  data=json.loads(pilot.payload(clean)["messages"][1]["content"])
  self.assertTrue(data["comparison_only"])
  self.assertEqual(data["selected_preference"]["storage_gb"],None)
  self.assertEqual(data["selected_preference"]["color"],None)
  base={"intent":"consulta","model":"iPhone 14 Pro Max","storage_gb":256,
    "color_options":["blanco"],"city":None,"pickup_location":None,
    "human_review":True,"suggested_reply":"Un asesor revisará la comparación."}
  self.assertEqual(pilot.validate(dict(base),clean)["storage_gb"],256)
  with self.assertRaises(pilot.PilotError):
   pilot.validate(dict(base,storage_gb=128,color_options=["negro"]),clean)
 def test_condition_question_needs_human_but_generic_review_can_be_safe(self):
  clean=pilot.prepare({"conversation_id":3,"message":"¿Es nuevo o usado? ¿Puedo revisarlo?"})
  base={"intent":"consulta","model":None,"storage_gb":None,
    "color_options":[],"city":None,"pickup_location":None,
    "human_review":False,"suggested_reply":"Un asesor puede confirmar el estado del equipo."}
  self.assertTrue(pilot.validate(base,clean)["human_review"])
 def test_sensitive_credentials_not_an_ai_output(self):
  clean=pilot.prepare({"conversation_id":3,"message":"Quiero una opción de 128 GB negro"})
  ans={"intent":"consulta","model":"iPhone 15","storage_gb":128,
       "color_options":["negro"],"city":None,"pickup_location":None,
       "human_review":False,"suggested_reply":"¿Te parece revisar las opciones con un asesor?"}
  self.assertFalse(pilot.validate(ans,clean)["human_review"])

if __name__=="__main__":unittest.main()
