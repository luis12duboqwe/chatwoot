import unittest
from sales_quality_gate import assess
from suggestion_guard import _buyer_topic,_topic_fallback,guarded_draft,_misses_secondary_intent

class ComplexBuyerIntentTests(unittest.TestCase):
 CASES=(
  ("Compré un iPhone 15 y el cargador falló, ¿tiene garantía?","warranty"),
  ("Mi equipo se dañó y quiero reclamar garantía.","warranty"),
  ("¿Cuándo llega mi pedido? ¿Tienen número de guía?","shipping"),
  ("¿Qué garantía tiene, incluye cargador y es nuevo o usado?","warranty"),
  ("¿Cuál es el precio y cuánto pago en cuotas?","payment"),
 )
 def test_preserves_customer_intent(self):
  for msg,topic in self.CASES:
   with self.subTest(msg=msg):
    self.assertEqual(_buyer_topic({"message":msg}),topic)
    reply=_topic_fallback({"message":msg})
    qa=assess(reply,topic)
    self.assertTrue(all(qa[k] for k in ("relevant","actionable","specific","meaningful")),qa)
    self.assertFalse(_misses_secondary_intent(reply,{"message":msg}))
 def test_detects_incomplete_replies(self):
  cases=[
   ("¿Qué garantía tiene, incluye cargador y es nuevo o usado?","Un asesor confirma la garantía."),
   ("¿Cuál es el precio y cuánto pago en cuotas?","El precio debe confirmarlo un asesor."),
   ("¿Cuándo llega mi pedido?","Un asesor puede verificar el transporte."),
   ("Compré un iPhone 15 y falló el cargador, ¿tiene garantía?","Antes de concretar la compra, un asesor confirma la garantía.")
  ]
  for msg,partial in cases:
   with self.subTest(msg=msg):
    out,blocked=guarded_draft({"suggested_reply":partial,"human_review":False},{"message":msg})
    self.assertTrue(blocked)
    self.assertTrue(out["human_review"])
    self.assertFalse(_misses_secondary_intent(out["suggested_reply"],{"message":msg}))
 def test_safe_replies_survive(self):
  for msg,_ in self.CASES:
   with self.subTest(msg=msg):
    reply=_topic_fallback({"message":msg})
    out,blocked=guarded_draft({"suggested_reply":reply,"human_review":True},{"message":msg})
    self.assertFalse(blocked)
    self.assertEqual(out["suggested_reply"],reply)
 def test_price_promises_are_blocked(self):
  for msg,_ in self.CASES:
   with self.subTest(msg=msg):
    out,blocked=guarded_draft(
     {"suggested_reply":"Te lo reservo y la cuota es L 900","human_review":False},{"message":msg})
    self.assertTrue(blocked)
    self.assertTrue(out["human_review"])
    self.assertNotIn("900",out["suggested_reply"])
if __name__=="__main__":unittest.main()
