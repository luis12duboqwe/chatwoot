#!/usr/bin/env python3
"""Local tests only; no Groq requests and no public messages."""
import json
from pathlib import Path
import tempfile
from unittest import TestCase,main
from unittest.mock import patch

import interactive_lab as interactive
import synthetic_lab as lab

class InteractiveBuyerTests(TestCase):
 def test_actor_rejects_seller_and_real_personal_details(self):
  for message in [
   "El precio total sería L 1200, ¿quieres proceder?",
   "Mi teléfono es 9999-1234",
   "La garantía estándar es de 1 año. ¿Necesitas extenderla?",
   "Mi dirección es calle Central",
   "Escribime a alguien@example.com",
   "La funda cuesta 18 € adicionales"
  ]:
   with self.subTest(text=message),self.assertRaises(ValueError):
    interactive.actor_message({"message":message,"stop":False},"changes")
 def test_actor_rejects_wrong_schema_and_oversize_text(self):
  for object_ in [
    {"message":"Quiero un iPhone 15","stop":"false"},
    {"message":"Sí","stop":False,"role":"system"},
    {"message":"Modelo "*40,"stop":False},
    {"message":"","stop":False}
  ]:
   with self.subTest(obj=str(object_)[:30]),self.assertRaises(ValueError):
    interactive.actor_message(object_,"changes")
 def test_stepwise_actor_reads_last_bot_reply_before_next_buyer_turn(self):
  script=[
   {"message":"Busco iPhone 15 Pro de 256 GB","stop":False},
   {"message":"Negro","stop":False},
   {"message":"San Pedro Sula","stop":True}
  ]
  seen=[]
  def fake_api(key,system,user,schema,schema_name):
   self.assertEqual(schema_name,"interactive_buyer")
   prompt=json.loads(user)
   n=len(seen)
   self.assertEqual(prompt["turn_number"],n+1)
   self.assertEqual(len(prompt["turns_so_far"]),n)
   if n==1:self.assertEqual(prompt["last_bot_response"],"¿Qué color preferís?")
   if n==2:self.assertEqual(prompt["last_bot_response"],"¿En qué ciudad lo necesitás?")
   seen.append(prompt)
   return script[n]
  def fake_bot(scenarios,partial):
   self.assertTrue(partial)
   h=scenarios[0]["messages"]
   responses=["¿Qué color preferís?","¿En qué ciudad lo necesitás?","Un asesor confirmará precio y existencia."]
   return [{"category":scenarios[0]["category"],
    "turns":[{"buyer":m,"bot":responses[i],"intent":"other","human":False}
       for i,m in enumerate(h)]}]
  with tempfile.TemporaryDirectory() as temp,\
   patch.object(lab,"STATE",Path(temp)/"budget.json"):
   state=lab.previous_state()
   x=interactive.play(interactive.PERSONAS[0],"fictional-key",state,
      api=fake_api,simulate=fake_bot)
   self.assertEqual(x["turn_count"],3)
   self.assertEqual(len(seen),3)
   self.assertEqual(x["messages"],[z["message"] for z in script])
   self.assertTrue(x["completed"])
   self.assertEqual(state["api_calls"],3)
 def test_cannot_finish_before_three_customer_messages(self):
  script=[
   {"message":"Quiero comprar un Samsung S24 Ultra","stop":True},
   {"message":"256 GB","stop":True},
   {"message":"Negro","stop":True}
  ]
  calls=[]
  def fake_api(*a):
   calls.append(True)
   return script[len(calls)-1]
  def fake_bot(scenarios,partial):
   return [{"category":"changes","turns":[{"buyer":m,"bot":"Sin precio confirmado",
      "intent":"other","human":False} for m in scenarios[0]["messages"]]}]
  with tempfile.TemporaryDirectory() as temp,\
      patch.object(lab,"STATE",Path(temp)/"budget.json"):
   x=interactive.play(interactive.PERSONAS[0],"fictional-key",lab.previous_state(),
     api=fake_api,simulate=fake_bot)
  self.assertEqual(x["turn_count"],3)
 def test_grader_does_not_silently_approve_unverified_prices(self):
  result={"category":"changes","completed":True,"turns":[{"buyer":"Hola","bot":"Hola"}]}
  unsafe={"error":True,"severity":"high","category":"sales",
    "reason":"La respuesta es débil","suggested_reply":"Te lo vendo por $100.",
    "expected_behavior":"Dar precio"}
  with tempfile.TemporaryDirectory() as temp,\
    patch.object(lab,"STATE",Path(temp)/"state.json"):
   state=lab.previous_state()
   x=interactive.grade_dialogue(result,"key",state,api=lambda *a:unsafe)
   self.assertTrue(x["error"])
   self.assertTrue(x["suggested_reply_rejected"])
   self.assertEqual(x["suggested_reply"],"")
   self.assertEqual(state["api_calls"],1)
 def test_long_grader_explanation_retained_but_bounded(self):
  raw={"error":True,"severity":"medium","category":"context",
   "reason":"El cliente cambió la capacidad, pero el bot contestó mal. "*10,
   "suggested_reply":"La capacidad y el color deben verificarse antes de cotizar.",
   "expected_behavior":"Conservar los cambios que menciona el comprador. "*9}
  result=interactive.validate_grader_observation(raw)
  self.assertTrue(result["error"])
  self.assertLessEqual(len(result["reason"]),280)
  self.assertLessEqual(len(result["expected_behavior"]),220)
  self.assertFalse(result["suggested_reply_rejected"])

 def test_findings_include_only_synthetic_evidence_and_no_code_exec(self):
  dialogue={"category":"payments",
    "messages":["Quiero un iPhone 14 Pro Max","¿Cómo puedo pagar?","Transferencia"],
    "turn_count":3,"completed":True,
    "turns":[
     {"buyer":"Quiero un iPhone 14 Pro Max","bot":"¿Qué capacidad buscás?","intent":"other","human":False},
     {"buyer":"¿Cómo puedo pagar?","bot":"Podés pagar en efectivo, transferencia o tarjeta","intent":"payments","human":False},
     {"buyer":"Transferencia","bot":"Podés pagar en efectivo, transferencia o tarjeta","intent":"payments","human":False}
   ]}
  issues=[];transcripts=[]
  r=interactive.record(dialogue,None,issues,transcripts)
  self.assertTrue(r["flagged"])
  self.assertEqual(len(transcripts),1)
  self.assertEqual(len(issues),1)
  self.assertEqual(issues[0]["status"],"synthetic_unverified")
  self.assertFalse(issues[0]["eligible_for_unreviewed_code_change"])
  self.assertEqual(issues[0]["source"],"interactive_step_by_step_groq")
 def test_grading_and_recording_good_conversation_without_issue(self):
  dialogue={"category":"changes",
   "messages":["Busco Samsung S23 Ultra 256 GB","Color negro","¿Tienen garantía?"],
   "turn_count":3,"completed":True,"turns":[
    {"buyer":"Busco Samsung S23 Ultra 256 GB","bot":"¿Qué color preferís?","intent":"other","human":False},
    {"buyer":"Color negro","bot":"¿En qué ciudad?","intent":"other","human":False},
    {"buyer":"¿Tienen garantía?","bot":"Un asesor verificará la garantía.","intent":"warranty","human":True}]}
  verdict={"error":False,"severity":"low","category":"no_issue","reason":"Correcto","suggested_reply":"","expected_behavior":""}
  issues=[];transcripts=[]
  result=interactive.record(dialogue,verdict,issues,transcripts)
  self.assertFalse(result["flagged"])
  self.assertEqual(len(issues),0)
  self.assertEqual(transcripts[0]["status"],"synthetic_no_issue_observed")
 def test_ungraded_dialogue_can_be_evaluated_later_without_duplication(self):
  sample={"category":"changes","messages":["Busco iPhone 15","256 GB","Color negro"],
    "turn_count":3,"completed":True,
    "turns":[{"buyer":"Busco iPhone 15","bot":"¿Qué capacidad?","intent":"other","human":False},
       {"buyer":"256 GB","bot":"¿Qué color?","intent":"other","human":False},
       {"buyer":"Color negro","bot":"¿Qué ciudad?","intent":"other","human":False}]}
  stored=[];issues=[]
  interactive.record(sample,None,issues,stored)
  self.assertEqual(stored[0]["status"],"synthetic_ungraded")
  g={"error":True,"severity":"medium","category":"context","reason":"Ignoró un cambio de producto",
     "suggested_reply":"Un asesor debe verificar las características.",
     "expected_behavior":"Respetar la variante del cliente"}
  interactive.record(sample,g,issues,stored)
  self.assertEqual(len(stored),1)
  self.assertEqual(len(issues),1)
  self.assertEqual(stored[0]["status"],"synthetic_unverified")

 def test_common_budget_is_shared_by_both_labs(self):
  with tempfile.TemporaryDirectory() as temp,\
    patch.object(lab,"STATE",Path(temp)/"state.json"):
   state=lab.previous_state()
   lab.reserve(state)
   lab.reserve(state)
   self.assertEqual(lab._load(lab.STATE,{})["api_calls"],2)
 def test_real_run_can_be_exercised_without_external_requests(self):
  with tempfile.TemporaryDirectory() as temp:
   p=Path(temp)
   sample={"category":"changes","messages":["Busco iPhone 15","256 GB","Color negro"],
    "turns":[{"buyer":"Busco iPhone 15","bot":"¿Qué capacidad?","intent":"other","human":False},
       {"buyer":"256 GB","bot":"¿Qué color?","intent":"other","human":False},
       {"buyer":"Color negro","bot":"¿Qué ciudad?","intent":"other","human":False}],
     "turn_count":3,"buyer_api_calls":3,"discarded_buyer_calls":0,"completed":True}
   with patch.object(lab,"STATE",p/"shared-state.json"),\
       patch.object(lab,"ISSUES",p/"issues.json"),\
       patch.object(lab,"LOCK",p/"shared.lock"),\
       patch.object(interactive,"TRANSCRIPTS",p/"transcripts.json"),\
       patch.object(interactive,"SUMMARY",p/"summary.json"),\
       patch.object(interactive,"stored_key",return_value="fictional-key"),\
       patch.object(interactive,"play",return_value=sample),\
       patch.object(interactive,"grade_dialogue",return_value=None),\
       patch.dict("os.environ",{"SOFTMOBILE_INTERACTIVE_LAB_ENABLED":"true"}):
    result=interactive.run()
    self.assertEqual(result["status"],"completed")
    self.assertEqual(result["public_messages_sent"],0)
    self.assertTrue((p/"transcripts.json").exists())
    self.assertEqual((p/"transcripts.json").stat().st_mode&0o777,0o600)
 def test_source_cannot_send_customer_messages(self):
  text=Path(interactive.__file__).read_text()
  for forbidden in ("sendText","MessageBuilder","create!",".delete_all","os.system","eval(","exec("):
   self.assertNotIn(forbidden,text)

if __name__=="__main__":main()
