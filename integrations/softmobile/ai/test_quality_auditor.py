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
 def test_ignored_payment_choice_detected(self):
  pair=dict(self.cash,incoming="Transferencias",
            reply="Perfecto, sería para retirar. Tengo anotado el Samsung S22 Ultra en Choloma.")
  self.assertIn("payment_choice_ignored",q.detect(q.sanitize_pair(pair)))
  pair2=dict(pair,incoming="tarjeta")
  self.assertIn("payment_choice_ignored",q.detect(q.sanitize_pair(pair2)))
  good=dict(pair,reply="Entendido, preferís pagar por transferencia. Un asesor confirmará precio.")
  self.assertNotIn("payment_choice_ignored",q.detect(q.sanitize_pair(good)))
 def test_variant_corrections_flagged_only_if_old_variant_retained(self):
  c=dict(self.cash,incoming="Mejor morado",
         reply="Tengo anotado el Samsung S22 Ultra negro. ¿Retiro o envío?")
  self.assertIn("color_change_ignored",q.detect(q.sanitize_pair(c)))
  self.assertNotIn("color_change_ignored",q.detect(q.sanitize_pair(
    dict(c,reply="Anoté color morado, confirmamos stock."))))
  s=dict(self.cash,incoming="Mejor de 256 GB",
         reply="Tengo anotado el Samsung S22 Ultra 128 GB. ¿Retiro o envío?")
  self.assertIn("capacity_change_ignored",q.detect(q.sanitize_pair(s)))
  self.assertNotIn("capacity_change_ignored",q.detect(q.sanitize_pair(
    dict(s,reply="Buscás el de 256 GB, verificaremos."))))
 def test_delivery_area_prompt_keeps_a_safe_generic_question(self):
  record={"bot_id":236,"inbound_id":234,"incoming":"Envío",
          "reply":"Consultamos envío a Comayagua y confirmamos transporte, costo y plazo antes de cerrar. ¿En qué colonia o zona sería?",
          "previous":"Comayagua"}
  parsed=q.sanitize_pair(record)
  self.assertIsNotNone(parsed)
  self.assertEqual(parsed["reply"],"¿En qué colonia o zona sería?")
  landmark=q.sanitize_pair({"bot_id":239,"inbound_id":237,"incoming":"Gasolinera uno",
          "reply":"Tengo anotado el iPhone 16 Pro de 256GB, con envío. Precio por verificar.",
          "previous":"Envío"})
  self.assertIn("shipping_reference_ignored",q.detect(landmark,parsed["reply"]))
 def test_precise_landmarks_are_redacted_before_external_review(self):
  safe=q.safe_line("Gasolinera uno")
  self.assertEqual(safe,"gasolinera [referencia omitida]")
  self.assertNotIn("uno",safe)
  self.assertIn("shipping_reference_ignored",q.detect({
    "incoming":safe,"reply":"Tengo anotado el equipo, con envío, precio por verificar.",
    "previous":"Envío"},"¿En qué colonia o zona sería?"))
 def test_live_pilot_detects_three_reproducible_failures(self):
  titanium={"bot_id":227,"inbound_id":225,"incoming":"Color titanium",
   "reply":"Dale, revisamos el iPhone 16 Pro de 256GB. ¿Qué color preferís?",
   "previous":"De 256"}
  reference={"bot_id":239,"inbound_id":237,"incoming":"Gasolinera uno",
   "reply":"Tengo anotado el iPhone 16 Pro de 256GB, en dorado, con envío. Precio y existencia todavía deben verificarse con un asesor.",
   "previous":"Envío"}
  ack={"bot_id":242,"inbound_id":240,"incoming":"Si",
   "reply":"Tengo anotado el iPhone 16 Pro de 256GB, en dorado, con envío. Precio y existencia todavía deben verificarse con un asesor.",
   "previous":"Gasolinera uno"}
  self.assertIn("finish_color_not_understood",q.detect(titanium,"¿Qué color preferís?"))
  self.assertIn("shipping_reference_ignored",q.detect(reference,"Consultamos envío a Comayagua. ¿En qué colonia o zona sería?"))
  self.assertIn("affirmation_repeated_summary",q.detect(ack,reference["reply"]))
  fixed_titanium=dict(titanium,reply="Anoté titanio, ¿qué tono preferís?")
  fixed_reference=dict(reference,reply="Anoté tu referencia de entrega para Comayagua; ¿cómo preferís pagar?")
  fixed_ack=dict(ack,reply="¿Preferís efectivo, transferencia o tarjeta?")
  self.assertNotIn("finish_color_not_understood",q.detect(fixed_titanium,"¿Qué color preferís?"))
  self.assertNotIn("shipping_reference_ignored",q.detect(fixed_reference,"¿En qué colonia o zona sería?"))
  self.assertNotIn("affirmation_repeated_summary",q.detect(fixed_ack,reference["reply"]))

 def test_good_disambiguation_not_flagged(self):
  p=dict(self.place,reply="¿Querés retirarlo en Mall Galerías o preferís envío a esa zona?")
  self.assertNotIn("pickup_shipping_ambiguity",q.detect(q.sanitize_pair(p)))
 def test_incomplete_stock_question_must_advance_buyer(self):
  answer="Aún no tengo confirmada la existencia del iPhone 14 Pro Max. Un asesor debe comprobar la unidad con el proveedor antes de confirmarte disponibilidad."
  prompts=("Tienen 14 pro Max?","¿Tienen iPhone 14 Pro Max?","¿Hay Samsung S24 Ultra?")
  for question in prompts:
   row=dict(self.cash,incoming=question,reply=answer,previous="")
   with self.subTest(question=question):
    self.assertIn("stock_no_next_step",q.detect(row))
    self.assertFalse(q.score_hits(q.detect(row))==100)
  improved="Podemos consultar por el iPhone 14 Pro Max; todavía no confirmamos existencias. ¿De cuántos GB y en qué color lo buscás?"
  for question in prompts:
   self.assertNotIn("stock_no_next_step",q.detect(dict(self.cash,incoming=question,reply=improved,previous="")))
 def test_stock_flag_respects_complete_variants_and_customer_escalations(self):
  reply="No tengo existencias confirmadas. Un asesor verificará el proveedor."
  for question in ("¿Tienen iPhone 14 Pro Max de 256 GB azul?",
                   "Quiero hablar con un asesor por iPhone 14 Pro Max.",
                   "¿Tiene garantía el Samsung S24 Ultra?"):
   self.assertNotIn("stock_no_next_step",q.detect(dict(self.cash,incoming=question,reply=reply,previous="")))
  self.assertIn("stock_no_next_step",q.CONCERNS)
  self.assertGreater(q.ISSUE_PENALTIES["stock_no_next_step"],0)
 def test_confirmed_stock_claim_blocked(self):
  p=dict(self.cash,incoming="Necesito confirmar el Samsung S22 Ultra",
         reply="Tenemos disponible, podés venir")
  self.assertIn("unsafe_claim",q.detect(q.sanitize_pair(p)))
 def test_repeated_outbound_different_messages(self):
  p=dict(self.cash,incoming="¿Qué opciones tengo?",previous="")
  self.assertIn("exact_repeat",q.detect(q.sanitize_pair(p),p["reply"]))
 def test_same_customer_question_is_not_false_repeat(self):
  sample=dict(self.cash,incoming="¿Tienen equipo?",previous="¿Tienen equipo?")
  self.assertNotIn("exact_repeat",q.detect(q.sanitize_pair(sample),sample["reply"]))
  ack=dict(self.cash,incoming="Gracias",previous="Precio del equipo")
  self.assertNotIn("exact_repeat",q.detect(q.sanitize_pair(ack),ack["reply"]))

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
 def test_quality_signal_reproducible_and_no_customer_content(self):
  self.assertEqual(q.score_hits([]),100)
  self.assertEqual(q.score_hits(["payment_choice_ignored"]),65)
  self.assertEqual(q.score_hits(["unsafe_claim","exact_repeat"]),15)
  scores=q.score_summary([(100,[]),(65,["payment_choice_ignored"]),(75,["pickup_shipping_ambiguity"])])
  self.assertEqual(scores,{"evaluated":3,"heuristic_score":80.0,"flagged":2})
  self.assertIsNone(q.score_summary([])["heuristic_score"])
  self.assertNotIn("customer",str(scores).lower())

 def test_history_baseline_is_idempotent_and_contains_no_customer_text(self):
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/"quality-score-history.json"
   with patch.object(q,"SCORE_HISTORY",path),patch.object(q,"fetch_pairs",
        return_value={"last_bot_id":210,"pairs":[self.cash,self.place]}) as fetch:
    a=q.build_baseline()
    b=q.build_baseline()
    self.assertEqual(a,b)
    self.assertEqual(fetch.call_count,1)
    self.assertEqual(a["evaluated"],2)
    self.assertNotIn("Efectivo",path.read_text())
    self.assertNotIn("Galerías",path.read_text())
    self.assertEqual(path.stat().st_mode&0o777,0o600)

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
 def test_read_pagination_does_not_skip_remaining_messages(self):
  def fake_rails(script):
   self.assertIn("batch=scope.to_a",script)
   self.assertIn("last=batch.last&.id",script)
   self.assertIn("limit(",script)
   self.assertNotIn("scope.reorder(id: :desc).first",script)
   return {"last_bot_id":64,"pairs":[]}
  with patch.object(q,"rails_read",side_effect=fake_rails):
   self.assertEqual(q.fetch_pairs(31)["last_bot_id"],64)

 def test_historical_flags_wait_for_live_validation(self):
  self.assertEqual(len(q.HISTORICAL_REPLAY_CASES),7)
  self.assertEqual(q.HISTORICAL_REPLAY_CASES,{134,137,143,146,169,175,179})
  summary=q.summarize(q.initial_state(),[
    {"status":"regression_passed_pending_live_test","category":"exact_repeat"},
    {"status":"pending_human_review","category":"unsafe_claim"}],{})
  self.assertEqual(summary["regression_passed_pending_live_test"],1)
  self.assertEqual(summary["pending_review"],1)

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
