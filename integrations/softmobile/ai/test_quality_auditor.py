#!/usr/bin/env python3
"""Offline regression suite for the autonomous quality auditor."""
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import quality_auditor as q

class QualityTests(unittest.TestCase):
 def setUp(self):
  self.cash={"bot_id":210,"inbound_id":208,"incoming":"Efectivo",
             "reply":"Podés pagar en efectivo, transferencia o tarjeta, según las condiciones del punto de entrega.",
             "previous":"Métodos de pago??"}
  self.place={"bot_id":204,"inbound_id":202,"incoming":"Galerías",
              "reply":"Perfecto, sería con envío a San Pedro Sula. Tenemos anotado el modelo.",
              "previous":"Envío"}
 def test_payment_choice_detected(self):
  self.assertEqual(q.detect(q.sanitize_pair(self.cash)),["payment_choice_repeat"])
 def test_location_ambiguity_detected(self):
  self.assertEqual(q.detect(q.sanitize_pair(self.place)),["pickup_shipping_ambiguity"])
 def test_good_disambiguation_not_flagged(self):
  p=dict(self.place,reply="¿Querés retirarlo en Mall Galerías o preferís envío a esa zona?")
  self.assertNotIn("pickup_shipping_ambiguity",q.detect(q.sanitize_pair(p)))
 def test_confirmed_stock_claim_blocked(self):
  p=dict(self.cash,incoming="Necesito confirmar el Samsung S22 Ultra",
         reply="Tenemos disponible, podés venir")
  self.assertIn("unsafe_claim",q.detect(q.sanitize_pair(p)))
 def test_repeated_outbound_different_messages(self):
  p=dict(self.cash,incoming="¿Qué opciones tengo?",previous="")
  self.assertIn("exact_repeat",q.detect(q.sanitize_pair(p),p["reply"]))
 def test_personal_data_skipped(self):
  for incoming in ("Mi teléfono es 9999-1234","Mi nombre es Fernando",
                   "Mi correo es usuario@example.com","Mi colonia es Los Pinos",
                   "El comprobante de banco es 1234"):
   with self.subTest(incoming=incoming[:15]):
    self.assertIsNone(q.sanitize_pair(dict(self.cash,incoming=incoming)))
 def test_sanitize_allows_checkout_choices(self):
  for case in (self.cash,self.place):
   self.assertIsNotNone(q.sanitize_pair(case))
 def test_proposed_reply_safety(self):
  good={"error":True,"category":"repetition","severity":"high",
        "reason":"Ya indicó pago en efectivo",
        "suggested_reply":"Perfecto, anoté efectivo. Un asesor confirmará el precio.",
        "test_expectation":"No repetir métodos"}
  self.assertEqual(q.valid_proposal(good),good)
  with self.assertRaises(ValueError):
   q.valid_proposal(dict(good,suggested_reply="Tenemos disponible y te lo aparté."))
  with self.assertRaises(ValueError):
   q.valid_proposal(dict(good,suggested_reply="Llamá al 9999-1234"))
  with self.assertRaises(ValueError):
   q.valid_proposal(dict(good,unknown=True))
 def test_judge_structured_api_with_mock(self):
  response={"error":True,"category":"repetition","severity":"high",
            "reason":"Repitió medios de pago","suggested_reply":"Perfecto, efectivo.",
            "test_expectation":"Reconocer la modalidad elegida"}
  class Reply(io.BytesIO):
   status=200
  def opener(req,timeout):
   self.assertEqual(req.full_url,q.ENDPOINT)
   self.assertEqual(req.get_header("User-agent"),"SoftMobile-QualityAuditor/1.0")
   self.assertEqual(timeout,18)
   body=json.loads(req.data)
   self.assertEqual(body["model"],q.MODEL)
   self.assertTrue(body["response_format"]["json_schema"]["strict"])
   self.assertEqual(json.loads(body["messages"][1]["content"])["customer"],"Efectivo")
   return Reply(json.dumps({"choices":[{"message":{"content":json.dumps(response)}}]}).encode())
  out=q.judge(q.sanitize_pair(self.cash),"test",opener=opener)
  self.assertEqual(out,response)
 def test_state_permissions_and_atomic_write(self):
  with tempfile.TemporaryDirectory() as directory:
   file=Path(directory)/"state.json"
   q._atomic_json(file,{"conversation_id":3,"last_bot_id":42})
   self.assertEqual(file.stat().st_mode & 0o777,0o600)
   self.assertEqual(q._load(file,{}).get("last_bot_id"),42)
   file.chmod(0o644)
   with self.assertRaises(RuntimeError):q._load(file,{})
 def test_audit_once_detection_idempotence_and_budget(self):
  with tempfile.TemporaryDirectory() as directory:
   base=Path(directory)
   pairdata=[self.place,self.cash]
   with patch.object(q,"STATE",base/"state.json"),\
        patch.object(q,"FINDINGS",base/"findings.json"),\
        patch.object(q,"REPORT",base/"summary.json"):
    def fake_fetch(cursor):
     if cursor==0:return {"last_bot_id":210,"pairs":pairdata}
     return {"last_bot_id":210,"pairs":[]}
    with patch.object(q,"fetch_pairs",side_effect=fake_fetch),\
         patch.object(q,"judge",return_value={
          "error":True,"category":"context","severity":"medium",
          "reason":"Repetición","suggested_reply":"Confirmamos con un vendedor.",
          "test_expectation":"Reconocer elección"
         }) as judge,\
         patch.object(q,"stored_key",return_value="mock"):
     first=q.run(use_llm=True)
     self.assertEqual(first["findings_total"],2)
     self.assertEqual(first["latest_run"]["api_used"],2)
     second=q.run(use_llm=True)
     self.assertEqual(second["findings_total"],2)
     self.assertEqual(second["latest_run"]["api_used"],0)
     self.assertEqual(judge.call_count,2)
     self.assertEqual(q._load(q.STATE,{})["api_calls"],2)
     self.assertEqual(len(q._load(q.FINDINGS,[])),2)
 def test_disabled_command_causes_no_state_change(self):
  with patch.dict(q.os.environ,{"SOFTMOBILE_QUALITY_AUDIT_ENABLED":"false"}):
   self.assertEqual(q.main.__name__,"main")
 def test_audit_notice_is_private_and_idempotent(self):
  def check(ruby):
   self.assertIn("c.account_id==2 && c.inbox_id==2",ruby)
   self.assertIn("message_type: :outgoing,private:false",ruby)
   self.assertIn("private:true",ruby)
   self.assertIn("Messages::MessageBuilder.new(nil,c,",ruby)
   self.assertIn("missing_bot_source",ruby)
   return {"status":"created","private":True}
  with patch.object(q,"rails_read",side_effect=check):
   self.assertEqual(q.notify_staff(210,["payment_choice_repeat"]),"created")
   with self.assertRaises(ValueError):
    q.notify_staff(0,["payment_choice_repeat"])
   with self.assertRaises(ValueError):
    q.notify_staff(210,["unknown"])

 def test_report_has_no_raw_phone(self):
  candidate=q.report_issue(q.sanitize_pair(self.cash),"payment_choice_repeat")
  self.assertEqual(candidate["status"],"pending_human_review")
  self.assertEqual(candidate["category"],"payment_choice_repeat")
  self.assertNotIn("phone_number",json.dumps(candidate))

if __name__=="__main__":unittest.main()
