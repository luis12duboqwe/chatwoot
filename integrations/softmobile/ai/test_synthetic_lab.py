#!/usr/bin/env python3
import json
import tempfile
from datetime import datetime,timezone
from pathlib import Path
from unittest import TestCase,main
from unittest.mock import patch

import synthetic_lab as lab

class LaboratoryTests(TestCase):
 def setUp(self):
  self.scenarios=lab.DEFAULT_CASES
  self.correct={"error":True,"severity":"medium","category":"context",
    "reason":"Ignoró el cambio de memoria al tercer turno",
    "suggested_reply":"Perfecto, tomo nota de los 256 GB. Un asesor verificará precio y existencia.",
    "expected_behavior":"No repetir las opciones anteriores y respetar los 256 GB"}

 def test_synthetic_schema_accepts_safe_customer_inputs(self):
  self.assertEqual(lab.validate_cases({"scenarios":self.scenarios}),self.scenarios)
 def test_role_confused_customer_messages_rejected(self):
  invalid=[
    "Sí, el negro está disponible. ¿Quieres cambiarlo ahora?",
    "El precio total sería 1,200,000 lempiras. ¿Quieres proceder con la compra?",
    "El envío estándar suele tardar entre 5 y 7 días hábiles. ¿Prefieres exprés?",
    "La garantía estándar es de 1 año. ¿Necesitas extenderla?",
    "La funda cuesta 15 € adicionales."
  ]
  for message in invalid:
   with self.subTest(message=message[:22]),self.assertRaises(ValueError):
    lab.validate_cases({"scenarios":[{"category":"checkout","messages":[
       "Busco iPhone 15 Pro",message,"Gracias"]}]})
  clean={"category":"questions","messages":["Quisiera saber si ofrecen garantía",
       "¿Qué sucede si tiene una falla?","¿Puedo retirarlo en tienda?"]}
  x,y,z=lab.select_valid_scenarios({"scenarios":[{"category":"checkout","messages":[
       "¿Qué tal?","El envío estándar suele tardar 4 días. ¿Prefieres exprés?","Claro"]},clean]})
  self.assertEqual(y,1)
  self.assertEqual(z,1)
  self.assertEqual(len(x),4)
  self.assertEqual(x[0],clean)
 def test_curated_availability_probe_cannot_be_crowded_out_by_groq(self):
  generated=[{"category":"questions","messages":["Busco un Samsung A54",f"Duda numero {i}","¿Y su precio?"]}
             for i in range(4)]
  selected,accepted,_=lab.select_valid_scenarios({"scenarios":generated})
  self.assertEqual(len(selected),lab.MAX_BATCH)
  self.assertEqual(accepted,lab.MAX_BATCH-1)
  self.assertIn(lab.DEFAULT_CASES[0],selected)
  self.assertIn("¿Tienen iPhone 16 Pro?",lab.DEFAULT_CASES[0]["messages"])
 def test_live_legacy_stock_dead_end_is_flagged_in_synthetic_dialogue(self):
  dialogue={"category":"questions","turns":[
   {"buyer":"Hola","bot":"¿Qué celular buscás?"},
   {"buyer":"¿Tienen iPhone 14 Pro Max?","bot":"Aún no tengo la existencia confirmada. Un asesor debe revisar con el proveedor."},
   {"buyer":"Me interesa","bot":"¿De cuántos GB y color lo buscás?"}]}
  self.assertIn("stock_no_next_step",lab.static_flags(dialogue))
 def test_offline_static_detection_survives_provider_cooldown_and_is_persisted(self):
  import copy
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp)
   turns=[{"buyer":x,"bot":"Un asesor verificará la existencia.","intent":"stock","human":True}
          for x in lab.DEFAULT_CASES[0]["messages"]]
   def runner(scenarios):
    return [{"category":case["category"],"turns":(
      turns if case==lab.DEFAULT_CASES[0] else
      [{"buyer":m,"bot":"¿Qué color y capacidad buscás?","intent":"other","human":False}
       for m in case["messages"]])} for case in scenarios]
   with patch.dict("os.environ",{"SOFTMOBILE_LAB_AI_ENABLED":"true"}),\
        patch.object(lab,"STATE",root/"state.json"),\
        patch.object(lab,"ISSUES",root/"issues.json"),\
        patch.object(lab,"SUMMARY",root/"summary.json"),\
        patch.object(lab,"LOCK",root/"lock"),\
        patch.object(lab,"state_at",return_value=120),\
        patch.object(lab,"simulate",side_effect=runner),\
        patch.object(lab,"api_json",side_effect=AssertionError("Must not call Groq")):
    result=lab.run(use_ai=True)
    stored=lab._load(lab.ISSUES,[])
   self.assertEqual(result["mode"],"curated_deterministic_provider_unavailable")
   self.assertEqual(result["simulated"],4)
   self.assertEqual(result["public_messages_sent"],0)
   self.assertTrue(any("stock_no_next_step" in x.get("static_flags",[]) for x in stored))
   self.assertTrue(all(x.get("grade") is None for x in stored))
 def test_unverified_price_suggestion_rejected(self):
  for msg in ("El envío cuesta 15 € adicionales.",
      "El precio total sería 1,200,000 lempiras.", "La garantía se extiende por 2 años."):
   with self.subTest(msg=msg),self.assertRaises(ValueError):
    lab.validate_grade(dict(self.correct,suggested_reply=msg))
 def test_no_private_data_permitted_in_synthetic_messages(self):
  samples=["Mi tarjeta 4111111111111111","Me llamo Luis y quiero un iPhone",
    "Mi teléfono es 9999-1234","Escríbeme a prueba@example.com",
    "En colonia Las Palmas, calle 4","https://external.test"]
  for s in samples:
   with self.subTest(message=s):
    test=dict(self.scenarios[0],messages=[s,"Quiero pagar en efectivo","Mejor no"])
    with self.assertRaises(ValueError):lab.validate_cases({"scenarios":[test]})
 def test_script_like_text_does_not_escape_runner(self):
  # The runner only receives base64 JSON, with no eval(user data).
  source=Path(tempfile.gettempdir())/"softmobile-fixture-lab.rb"
  source.write_text("""module SoftMobileSales
 def self.context_from(messages); {}; end
 def self.plan(message,context,catalog,last); {reply:'Bot',intent: :other,needs_human:false}; end
end
if ENV['SM_MODE']=='test'
  puts 'test'
end
""")
  dialogues=[{"category":"objections","messages":["Aún quieres revisar?",
     "Una expresión con comillas ' y comando touch /tmp/hack",
     "Sí"]}]
  def runner(cmd,**kwargs):
   body=kwargs["input"]
   self.assertIn("Base64.strict_decode64",body)
   self.assertNotIn("eval(",body)
   self.assertNotIn("touch /tmp/hack",body)
   obj=[{"category":"objections","turns":[{"buyer":m,"bot":"Bot","intent":"other","human":False} for m in dialogues[0]["messages"]]}]
   class Resp:
    returncode=0
    stdout="INFO\n"+lab.MARK+json.dumps(obj)+"\n"
   return Resp()
  try:self.assertEqual(len(lab.simulate(dialogues,runner=runner,source=source)),1)
  finally:source.unlink(missing_ok=True)
 def test_grade_rejects_commercial_promise(self):
  self.assertEqual(lab.validate_grade(self.correct),self.correct)
  for msg in ("Tenemos disponible el Samsung","Pago confirmado, vení a retirarlo",
    "Mi dirección exacta es colonia las Palmas","Te lo reservé"):
   with self.subTest(msg=msg),self.assertRaises(ValueError):
    lab.validate_grade(dict(self.correct,suggested_reply=msg))
 def test_grade_requires_real_reason_and_expectation(self):
  with self.assertRaises(ValueError):lab.validate_grade(dict(self.correct,expected_behavior=""))
  with self.assertRaises(ValueError):lab.validate_grade(dict(self.correct,category="no_issue"))
  no_issue={"error":False,"severity":"low","category":"no_issue",
    "reason":"Pide los datos adecuados","suggested_reply":"","expected_behavior":""}
  self.assertFalse(lab.validate_grade(no_issue)["error"])
 def test_generate_schema_is_strict_no_tools(self):
  calls=[]
  class Resp:
   status=200
   def read(self,n):
    return json.dumps({"choices":[{"message":{"content":json.dumps({"scenarios":self_data})}}]}).encode()
   def __enter__(self):return self
   def __exit__(self,*args):return False
  self_data=self.scenarios
  def opener(req,timeout):
   self.assertEqual(req.get_method(),"POST")
   self.assertEqual(req.get_header("User-agent"),"SoftMobile-Synthetic-QualityLab/1.0")
   self.assertEqual(timeout,25)
   payload=json.loads(req.data)
   self.assertEqual(payload["response_format"]["json_schema"]["strict"],True)
   self.assertIn("Synthetic",req.get_header("User-agent"))
   calls.append(req)
   return Resp()
  out=lab.api_json("mock",lab.GENERATOR_SYSTEM,"test",lab.CASE_SCHEMA,"synth_cases",opener=opener)
  self.assertEqual(out["scenarios"],self.scenarios)
  self.assertEqual(len(calls),1)
 def test_budget_counter_atomic_does_not_leak_secrets(self):
  with tempfile.TemporaryDirectory() as temp:
   with patch.object(lab,"STATE",Path(temp)/"state.json"):
    state=lab.previous_state()
    lab.reserve(state)
    stored=lab._load(lab.STATE,{})
    self.assertEqual(stored["api_calls"],1)
    self.assertEqual(lab.STATE.stat().st_mode&0o777,0o600)
    self.assertNotIn("Authorization",lab.STATE.read_text())
    state["api_calls"]=lab.MAX_DAILY
    with self.assertRaises(RuntimeError):lab.reserve(state)
 def test_static_quality_signal_can_flag_simulated_repetition(self):
  simulation={"category":"payments","turns":[
    {"buyer":"Efectivo","bot":"Podés pagar en efectivo, transferencia o tarjeta, según las condiciones del punto de entrega."},
    {"buyer":"Transferencia","bot":"Podés pagar en efectivo, transferencia o tarjeta, según las condiciones del punto de entrega."}
  ]}
  self.assertIn("payment_choice_repeat",lab.static_flags(simulation))
 def test_retest_replays_and_regrades_without_deploying(self):
  issue={"id":"candidate-1","status":"fix_deployed_pending_synthetic_retest",
   "category":"questions","scenario":self.scenarios[0],
   "evidence":[{"bot":"Antes: repetir pregunta de color"}]}
  grade={"error":False,"severity":"low","category":"no_issue",
         "reason":"La consulta ahora se interpreta correctamente",
         "suggested_reply":"","expected_behavior":""}
  replay={"category":"questions","turns":[
    {"buyer":m,"bot":("¿Qué capacidad y color buscás?" if "¿Tienen iPhone" in m else "Ahora: respuesta adecuada"),"intent":"other","human":False}
    for m in self.scenarios[0]["messages"]]}
  state=lab.previous_state()
  with tempfile.TemporaryDirectory() as temp:
   with patch.object(lab,"STATE",Path(temp)/"state.json"),\
        patch.object(lab,"simulate",return_value=[replay]),\
        patch.object(lab,"api_json",return_value=grade) as ai:
    result=lab.retest_open_issues([issue],"mock",state,max_cases=1)
    self.assertEqual(result,{"checked":1,"improved_ai_only":1,"still_suspicious":0})
    self.assertEqual(issue["status"],"retested_ai_clear_pending_deterministic_review")
    self.assertEqual(issue["retest"]["changed_turns"],1)
    self.assertEqual(state["api_calls"],1)
    ai.assert_called_once()
 def test_retest_cannot_mark_new_issue_clear_from_bad_or_missing_grade(self):
  issue={"id":"candidate-2","status":"synthetic_unverified","category":"changes",
   "scenario":self.scenarios[0],"evidence":[{"bot":"old reply"}]}
  replay={"category":"changes","turns":[
    {"buyer":m,"bot":"new reply","intent":"other","human":False}
    for m in self.scenarios[0]["messages"]]}
  state=lab.previous_state()
  with tempfile.TemporaryDirectory() as temp:
   with patch.object(lab,"STATE",Path(temp)/"state.json"),\
        patch.object(lab,"simulate",return_value=[replay]),\
        patch.object(lab,"api_json",side_effect=RuntimeError("unavailable")):
    result=lab.retest_open_issues([issue],"mock",state,max_cases=1)
    self.assertEqual(result["still_suspicious"],1)
    self.assertEqual(issue["status"],"synthetic_unverified")
    self.assertIsNone(issue["retest"]["ai_error"])
 def test_no_user_contact_needed(self):
  self.assertEqual(lab.BOT.name,"sales-bot-v2.rb")
  self.assertIn("quality",str(lab.ISSUES))
  self.assertEqual(lab.MAX_BATCH,4)
 def test_observe_only_without_production_writes(self):
  src=Path(lab.__file__).read_text()
  for sensitive in ("Messages::MessageBuilder","create!",".delete_all","sendText","os.system","exec("):
   self.assertNotIn(sensitive,src)

if __name__=="__main__":main()
