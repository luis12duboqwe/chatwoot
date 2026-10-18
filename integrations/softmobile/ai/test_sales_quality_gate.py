#!/usr/bin/env python3
"""Offline tests for strict relevance and anti-keyword-stuffing gate."""
import unittest
from sales_quality_gate import assess

class SalesQualityGateTests(unittest.TestCase):
 def test_rejects_keyword_stuffing_even_if_every_topic_word_matches(self):
  spam=("Asesor: comparar opciones y modelos, precio y presupuesto, descuento y promoción, "
        "cuota, financiación, banco, garantía, estado y revisión, entrega y retiro, "
        "parte de pago, valoración, compra disponible a confirmar.")
  for topic in ("payment","warranty","closing","trade_in","budget"):
   with self.subTest(topic=topic):
    r=assess(spam,topic)
    self.assertTrue(r["relevant"])
    self.assertFalse(r["specific"])
 def test_genuine_specific_safe_payment_answer(self):
  text=("Un asesor debe confirmar los bancos participantes, las cuotas y los requisitos "
        "de financiamiento para esta unidad. No compartás datos de tarjeta aquí.")
  r=assess(text,"payment")
  self.assertTrue(all(r[k] for k in ("relevant","actionable","specific","meaningful")))
 def test_generic_one_liner_cannot_pass_for_tradein(self):
  for text in ("Un asesor lo revisará.","Un asesor verá opciones.","No sé."):
   r=assess(text,"trade_in")
   self.assertFalse(r["relevant"] and r["actionable"] and r["specific"] and r["meaningful"])
 def test_vague_agent_filler_is_not_a_sale_next_step(self):
  r=assess("Un asesor revisará las condiciones del equipo.","product")
  self.assertTrue(r["relevant"])
  self.assertFalse(r["specific"])
 def test_tradein_answer_must_mention_commercial_topic(self):
  text=("Un asesor debe confirmar si existe la opción de recibir tu celular como parte "
        "de pago, su valoración y las condiciones antes de concretar nada.")
  r=assess(text,"trade_in")
  self.assertTrue(all(r[k] for k in ("relevant","actionable","specific","meaningful")))
 def test_shipping_delivery_requires_relevant_terms(self):
  warranty=("Un asesor puede confirmar las condiciones de garantía y la batería "
            "antes de proceder con la consulta sobre el equipo.")
  self.assertFalse(assess(warranty,"shipping")["relevant"])
 def test_unknown_topic_or_bad_values_fail(self):
  for reply,topic in ((None,"payment"),("Un asesor debe verificar","unknown"),("", "payment")):
   self.assertFalse(assess(reply,topic)["meaningful"])
 def test_excessively_long_draft_rejected(self):
  text="Un asesor puede confirmar el precio y las cuotas. "+"Consulta comercial. "*20
  self.assertFalse(assess(text,"payment")["specific"])

if __name__=="__main__":unittest.main()
