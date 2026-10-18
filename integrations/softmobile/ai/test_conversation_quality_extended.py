#!/usr/bin/env python3
"""Additional buyer-language adversarial tests, independent from the initial 16.

All messages fictional. No real Chatwoot activity, inventory, or API calls.
"""
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import evaluate_conversation_quality as qa
import prepare_conversation_quality as p

EXTRA=[
("mixed-1","¿Incluye cargador o estuche y cuánto tiempo tiene de garantía?","bundle_warranty_accessories"),
("mixed-2","¿Cuál es la garantía del celular y cuáles regalías trae?","bundle_warranty_accessories"),
("mixed-3","Me interesa el Samsung S24, ¿incluye funda y garantía?","bundle_warranty_accessories"),
("mixed-4","¿Trae audífonos y tiene garantía?","bundle_warranty_accessories"),
("ship-1","¿Cuánto tiempo tarda en entregar el teléfono?","shipping_eta"),
("ship-2","¿Cuánto tardaría el envío para Choloma?","shipping_eta"),
("ship-3","¿Para cuándo está estimada la entrega del iPhone?","shipping_eta"),
("ship-4","¿Cuántos días demora llegar a Tegucigalpa?",None),
("order-1","¿Cuándo recibiré mi pedido?","order_delivery_status"),
("order-2","¿Qué pasa con mi paquete, cuándo lo recibiré?",None),
("order-3","¿En cuánto tiempo llega mi pedido ya pagado?","order_delivery_status"),
("change-1","¿Cuánto tardaría el cambio de 128 a 256 GB?","variant_change_eta"),
("change-2","¿En qué plazo me cambian el color a azul?","variant_change_eta"),
("change-3","¿Qué tiempo tardaría en cambiar el modelo al 14 Pro?","variant_change_eta"),
("safe-1","Compré un celular y el cargador falló ¿qué garantía tiene?",None),
("safe-2","¿La garantía incluye accesorios de la caja que fallan?",None),
("safe-3","¿El celular tiene garantía cuando se moja?",None),
("safe-4","¿Tienen funda y otro regalo para el iPhone?",None),
("safe-5","¿Cómo funciona la garantía extendida?",None),
("safe-6","Tengo problemas con mi pedido y quiero cancelarlo",None),
("safe-7","¿La pantalla tiene rayas? ¿Qué garantía cubre eso?",None),
("safe-8","¿En cuánto tiempo tardan en reparar el puerto de carga?",None),
("safe-9","¿Me mandan el número de guía para rastrear el envío?",None),
("safe-10","¿Cuánto cuesta el transporte a Tegucigalpa?",None),
("safe-11","¿Puedo recoger mañana en Mall Galerías?",None),
("safe-12","¿Aceptan cambios por defecto al mes de comprar?",None),
]
def extra_cases():
 return [{"id":key,"history":["Busco un iPhone 15 Pro negro 128GB"],
   "buyer":msg,"target":intent,
   "words":["asesor"] if intent else []} for key,msg,intent in EXTRA]

def evaluate():
 old_cases=qa.SCENARIOS
 try:
  qa.SCENARIOS=old_cases+extra_cases()
  old=p.LIVE.read_text()
  new=(p.STAGE/"sales-bot-composite-sales-stage.rb").read_text()
  report=qa.compare(old,new)
  report["source_hash"]=hashlib.sha256(old.encode()).hexdigest()
  report["candidate_hash"]=hashlib.sha256(new.encode()).hexdigest()
  report["existing_pilot_unchanged"]=True
  return report
 finally:
  qa.SCENARIOS=old_cases

class ConversationCandidateUnitTests(unittest.TestCase):
 def test_extra_case_groups_are_balanced_and_unique(self):
  cases=extra_cases()
  self.assertEqual(len(cases),26)
  self.assertEqual(len({x["id"] for x in cases}),26)
  self.assertTrue(sum(x["target"] is None for x in cases)>=10)
  self.assertTrue(sum(x["target"] is not None for x in cases)>=10)
 def test_review_policy_has_no_deploy_code_or_customer_output(self):
  src=Path(p.__file__).read_text()
  self.assertNotIn("MessageBuilder",src)
  self.assertNotIn("sendText",src)
  self.assertNotIn("fixer.deploy(",src)
  self.assertIn("needs_human:true",p.BLOCK)
  self.assertNotIn("te garantizamos",p.BLOCK.lower())
 def test_target_and_negative_fixtures_independent_of_private_vps(self):
  for x in extra_cases():
   self.assertNotIn("+504",x["buyer"])
   self.assertNotIn("@",x["buyer"])
   self.assertNotIn("411111",x["buyer"])
  self.assertFalse(any(x["id"] in {y["id"] for y in qa.SCENARIOS} for x in extra_cases()))

if __name__=="__main__":
 import argparse
 parser=argparse.ArgumentParser()
 parser.add_argument("--integration",action="store_true")
 args=parser.parse_args()
 if args.integration:
  result=evaluate()
  print(json.dumps(result,ensure_ascii=False))
  sys.exit(0 if result["status"]=="review_ready" and result["total"]==42 and len(result["unmet_targets"])==0 and not result["regressions"] else 2)
 unittest.main(argv=[sys.argv[0]])
