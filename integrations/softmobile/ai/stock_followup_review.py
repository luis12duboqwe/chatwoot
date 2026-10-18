#!/usr/bin/env python3
"""Review-only static Ruby correction for vague inventory responses.

Every proposed improvement is staged. This module never changes live Ruby,
public routing, stock, prices, messaging, or deployment limits.
"""
from datetime import datetime,timezone
from pathlib import Path
from hashlib import sha256
import json
import autonomous_learning as learning
from quality_auditor import _atomic_json,_load
import offline_issue_replay as replay
import conversion_training_lab as sales
import financing_holdout as financing
import inventory_quality_lab as stock
import context_accuracy_lab as context
from isolated_gate import gates as ruby_gates

ROOT=Path(__file__).resolve().parent
REPORT=ROOT/"quality"/"stock-followup-review.json"
STAGED=ROOT/"quality"/"stock-followup-candidates"
EXPECTED_LIVE="970ac57ef00ba068d5319ec8b865dbaa597192e21a1ea1f16d9ca5273bf13d7a"
BEFORE="""          response="Aún no tengo confirmada la existencia del #{device}#{cap ? ' de '+cap : ''}#{col ? ' en '+col.downcase : ''}#{place ? ' para '+place : ''}. Un asesor debe comprobar la unidad con el proveedor antes de confirmarte disponibilidad."

          human_note="STOCK Y COLOR PENDIENTES:"""
AFTER="""          if !cap && !col
            response="Podemos consultar por el #{device}. Todavía no tengo existencias confirmadas. ¿De cuántos GB y en qué color lo buscás?"
          elsif !cap
            response="Anoté que buscás el #{device} en #{col.downcase}. ¿De cuántos GB lo preferís? Primero debemos confirmar disponibilidad."
          elsif !col
            response="Perfecto, revisamos el #{device} de #{cap}. ¿Qué color preferís? Todavía hay que confirmar la existencia de esa versión."
          else
            response="Aún no tengo confirmada la existencia del #{device}#{cap ? ' de '+cap : ''}#{col ? ' en '+col.downcase : ''}#{place ? ' para '+place : ''}. Un asesor debe comprobar la unidad con el proveedor antes de confirmarte disponibilidad."
          end

          human_note="STOCK Y COLOR PENDIENTES:"""

TESTS=[
 ("generic",["Hola","Buenas","Tienen 14 pro Max?"],["de cuantos gb","en que color"]),
 ("short",["Hola","Buenas","Tiene 14 Pro Max?"],["capacidad"]),
 ("storage_present",["Hola","Buenas","¿Tienen el iPhone 14 Pro Max de 256GB?"],["que color"]),
 ("color_present",["Hola","Buenas","¿Tienen el iPhone 14 Pro Max azul?"],["de cuantos gb"]),
 ("full_variant",["Hola","Buenas","¿Tienen iPhone 14 Pro Max 256GB azul?"],["asesor","confirmada"]),
]

def build(source):
 if sha256(source.encode()).hexdigest()!=EXPECTED_LIVE:
  raise ValueError("Expected installed V4 source unchanged")
 if source.count(BEFORE)!=1:raise ValueError("Missing exact stock reply anchor")
 return source.replace(BEFORE,AFTER,1)

def smoke(source):
 requested=[{"id":label,"scenario":{"category":"questions","messages":msgs}}
            for label,msgs,_ in TESTS]
 rows=replay.isolated_replay(requested,source=source)
 if len(rows)!=len(TESTS):raise RuntimeError("Scenario mismatch")
 outcomes=[]
 for (label,msgs,required),output in zip(TESTS,rows):
  if label!=output["id"]:raise RuntimeError("Scenario identity mismatch")
  text=replay.lab.normalize(output["turns"][-1]["bot"])
  safe=not any(token in text for token in ("disponible hoy","si tenemos en stock",
   "el precio es","te lo reservo","reservado para vos"))
  outcomes.append({"case":label,"reply":output["turns"][-1]["bot"],
   "passed":all(word in text for word in required) and safe})
 return {"passed":sum(x["passed"] for x in outcomes),"total":len(outcomes),
         "cases":outcomes,"public_messages_sent":0}

def run():
 source=learning.BOT.read_text()
 candidate=build(source)
 checked=smoke(candidate)
 report={"at":datetime.now(timezone.utc).isoformat(),
         "status":"not_validated","baseline_sha256":EXPECTED_LIVE,
         "candidate_sha256":sha256(candidate.encode()).hexdigest(),
         "dialogue":checked,"promoted":False,"pilot_only":True}
 if checked["passed"]!=checked["total"]:
  report["status"]="buyer_reply_gate_failed"
 else:
  ruby=ruby_gates(candidate)
  before,_=sales.run(source=source,persist=False)
  after,_=sales.run(source=candidate,persist=False)
  loan=financing.verify(source=candidate)
  choices=context.evaluate(source=candidate)
  reference=stock.evaluate(source=source)
  inventory=stock.evaluate(source=candidate)
  differences=replay.compare(replay.assess(source=source),replay.assess(source=candidate))
  report["regressions"]={"ruby":ruby.get("total"),"ruby_status":ruby.get("status"),
    "sales_before":before["passed"],"sales_after":after["passed"],
    "financing":loan["passed"],"context":choices["passed"],
    "stock_before":reference["passed"],"stock_after":inventory["passed"],
    "unsafe_stock_claims":inventory["safety_violations"],"historical":differences}
  if (ruby.get("status")=="passed" and ruby.get("total",0)>=117
      and after["passed"]>=before["passed"]==72
      and loan["passed"]==loan["total"]==48
      and choices["passed"]==choices["total"]==8
      and inventory["failed"]<=reference["failed"]
      and not inventory["safety_violations"]
      and not differences["new_flags_in_candidate"]):
   STAGED.mkdir(parents=True,exist_ok=True,mode=0o700)
   filename="stock-followup-"+report["candidate_sha256"][:18]+".rb"
   dest=STAGED/filename;dest.write_text(candidate);dest.chmod(0o600)
   report["stage_file"]=filename
   report["status"]="validated_review_only"
  else:
   report["status"]="regression_gate_failed"
 _atomic_json(REPORT,report)
 return report

if __name__=="__main__":
 result=run()
 print(json.dumps({k:v for k,v in result.items() if k!="dialogue"},ensure_ascii=False))
