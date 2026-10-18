#!/usr/bin/env python3
"""Human-facing sales lead notes: deterministic, private and no customer PII."""
import unittest
from lead_handoff import lead_facts,private_lead_summary
import chatwoot_ai_bridge as bridge

class LeadHandoffTests(unittest.TestCase):
 def test_complete_phone_choice_and_handoff(self):
  clean={"message":"¿Cuánto tarda el envío para Choloma?",
    "context":{"model":"iPhone 15 Pro","storage_gb":"256","color_options":"azul"}}
  self.assertEqual(lead_facts(clean),{"model":"iPhone 15 Pro",
    "storage_gb":256,"color":"azul","city":"Choloma"})
  note=private_lead_summary(clean)
  for val in ("iPhone 15 Pro","256 GB","azul","Choloma","Confirmar destino"):
   self.assertIn(val,note)
  self.assertNotIn("entrega confirmada",note.lower())
 def test_comparison_cannot_change_selected_phone(self):
  clean={"message":"¿Y el negro de 128GB cuesta lo mismo?",
    "context":{"model":"iPhone 15 Pro","storage_gb":"256","color_options":"azul"}}
  self.assertEqual(lead_facts(clean),{"model":"iPhone 15 Pro",
    "storage_gb":256,"color":"azul"})
 def test_change_mind_updates_variant(self):
  clean={"message":"No quiero negro, mejor 256GB azul",
    "context":{"model":"iPhone 15 Pro","storage_gb":"128","color_options":"negro"}}
  self.assertEqual(lead_facts(clean),{"model":"iPhone 15 Pro",
    "storage_gb":256,"color":"azul"})
 def test_explicit_rejection_without_replacement_clears_color(self):
  clean={"message":"No quiero azul",
    "context":{"model":"iPhone 15 Pro","storage_gb":"256","color_options":"azul"}}
  self.assertNotIn("color",lead_facts(clean))
 def test_ambiguous_two_variants_are_not_declared_chosen(self):
  clean={"message":"¿128GB negro o 256GB azul?",
    "context":{"model":"iPhone 15 Pro","storage_gb":"128","color_options":"negro"}}
  result=lead_facts(clean)
  self.assertNotIn("storage_gb",result)
  self.assertNotIn("color",result)
  self.assertEqual(result["model"],"iPhone 15 Pro")
 def test_unknown_field_and_provider_authored_claim_are_not_copied(self):
  clean={"message":"Quiero el Samsung S24 Ultra 256GB gris",
    "context":{"model":"Inventado AI phone STOLEN PII", "storage_gb":"999",
      "color_options":"cromo","city":"Pueblo inventado",
      "address":"Calle Central #10","phone":"9999-1234","price":199}}
  note=private_lead_summary(clean)
  self.assertIn("Samsung S24 Ultra",note)
  for bad in ("Inventado","STOLEN","9999","Calle Central","199",
     "Pueblo inventado","cromo"):
   self.assertNotIn(bad,note)
 def test_model_and_city_are_whitelisted(self):
  clean={"message":"¿Aceptan cuota?",
    "context":{"model":"iPhone 15 Pro\nError: token","city":"Zona Desconocida",
      "storage_gb":12,"color_options":"dorado\npaga"}}
  self.assertEqual(lead_facts(clean),{})
 def test_pending_action_is_specific_but_not_committed(self):
  examples=[
   ("¿Puedo financiarlo?", "Confirmar medios de pago"),
   ("¿Qué garantía tiene?", "Confirmar estado"),
   ("¿Me hacen descuento?", "Confirmar precio"),
   ("Lo compro ahora", "Verificar existencia"),
   ("¿Reciben mi equipo como parte de pago?", "Confirmar si existe canje"),
  ]
  for message,expected in examples:
   with self.subTest(message=message):
    note=private_lead_summary({"message":message,"context":{}})
    self.assertIn(expected,note)
 def test_note_is_private_only_and_bounded(self):
  clean={"message":"Quiero el iPhone 15 Pro 256GB negro, ¿cuánto cuesta?",
     "context":{"model":"iPhone 15 Pro","storage_gb":256,"color_options":"negro"}}
  result=bridge.format_note("13",
    {"suggested_reply":"Un asesor deberá confirmar condiciones.", "human_review":True},clean)
  self.assertIn("[SMAI:13]",result)
  self.assertIn("SUGERENCIA INTERNA",result)
  self.assertIn("Ficha comercial:",result)
  self.assertIn("Revisión humana: SÍ",result)
  self.assertLess(len(result),1500)
  self.assertNotIn("precio confirmado",result.lower())
 def test_empty_context_and_broken_types_fail_closed(self):
  self.assertEqual(lead_facts(None),{})
  self.assertIn("pendientes de confirmar",private_lead_summary({}))
  clean={"message":12,"context":"evil"}
  self.assertEqual(lead_facts(clean),{})
 def test_simple_mock_groq_bridge_note_contains_commercial_summary(self):
  result=bridge.format_note("14",{"suggested_reply":"Un asesor puede confirmar",
       "human_review":True},
      {"message":"¿Puedo retirar en Choloma?",
       "context":{"model":"iPhone 15 Pro","storage_gb":"256","color_options":"azul"}})
  self.assertIn("Modelo: iPhone 15 Pro",result)
  self.assertIn("Ciudad: Choloma",result)
  self.assertNotIn("datos bancarios enviados",result)

if __name__=="__main__":unittest.main()
