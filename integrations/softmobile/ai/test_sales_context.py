#!/usr/bin/env python3
"""Offline, no PII and no Groq network calls."""
import unittest
import sales_context as ctx
import suggestion_guard as guard

class ContextTests(unittest.TestCase):
 def test_keeps_only_commercial_preferences(self):
  result=ctx.preference_snapshot([
   "Busco iPhone 15 Pro de 128GB negro",
   "Ahora el de 256 GB azul",
   "Lo quiero para retirar en Choloma"])
  self.assertEqual(result,{"model":"iPhone 15 Pro",
   "storage_gb":256,"color_options":"azul","city":"Choloma"})
 def test_mixed_phone_discussion_does_not_choose_first_unrelated_device(self):
  d=ctx.preference_snapshot(["Tengo iPhone 12 negro, quiero Samsung S24 Ultra azul"])
  self.assertNotIn("model",d)
  self.assertNotIn("color_options",d)
 def test_never_forward_address_payment_phone_credentials_or_long_message(self):
  texts=[
   "Mi correo es compras@ejemplo.com, quiero 256 GB",
   "Llamame al 9999-1234 para el azul",
   "Mi cuenta bancaria es 7000000000000000000",
   "Estoy en la colonia Las Acacias, quiero iPhone 15",
   "Prefiero pagar por transferencia, iPhone 15 negro",
   "Mi clave bancaria es 1234, Samsung S24 Ultra",
   "a"*450,
  ]
  self.assertEqual(ctx.preference_snapshot(texts[:4]),{})
  for txt in texts:
   self.assertIsNone(ctx.safe_previous(txt))
 def test_too_many_prior_messages_fails_closed(self):
  self.assertEqual(ctx.preference_snapshot(["iPhone 15 256GB"]*5),{})
 def test_ambiguous_color_and_capacity_are_not_assumed(self):
  d=ctx.preference_snapshot(["¿iPhone 15 negro o azul, 128GB o 256GB?"])
  self.assertEqual(d,{"model":"iPhone 15"})
 def test_known_cities_only(self):
  d=ctx.preference_snapshot(["Busco Samsung S22 Ultra 256 GB en Ciudad Central"])
  self.assertNotIn("city",d)

class SuggestionGuardTests(unittest.TestCase):
 def test_blocks_unconfirmed_hard_claims(self):
  examples=[
   "Sí, tenemos disponible el iPhone 15.",
   "Te lo reservé para mañana.",
   "Incluye funda y cargador.",
   "El precio es L 12,000.",
   "Te llega en 2 días.",
   "Compárteme el número de tarjeta.",
   "Ya quedó reservado para vos.",
   "El seguro de pantalla tiene cobertura incluida.",
   "Está disponible en tienda.",
   "Viene con cargador.",
   "Te lo aparto.",
   "Tenemos en existencia el equipo.",
   "Entrega inmediata garantizada."
  ]
  for text in examples:
   with self.subTest(text=text):
    sanitized,was_guarded=guard.guarded_draft(
      {"suggested_reply":text,"human_review":False})
    self.assertTrue(was_guarded)
    self.assertTrue(sanitized["human_review"])
    self.assertEqual(sanitized["suggested_reply"],guard.FALLBACK)
 def test_preserves_safe_questions(self):
  row={"suggested_reply":"¿Querés consultar el iPhone 15 Pro de 256 GB en azul con un asesor?",
       "human_review":True}
  result,changed=guard.guarded_draft(row)
  self.assertFalse(changed)
  self.assertEqual(result,row)
 def test_reject_invalid_shape(self):
  with self.assertRaises(ValueError):guard.guarded_draft({"human_review":True})

if __name__=="__main__":unittest.main()
