#!/usr/bin/env python3
"""Adversarial five-turn sales conversations against the private Groq pilot.

This evaluation cannot publish messages, mutate Chatwoot, retrieve stock,
accept payments or install patches. All buyer utterances are fictional.
Persist only fixed per-turn flags and aggregate counters, not replies.
"""
import argparse
from datetime import datetime,timezone
import json
import os
import time
import fcntl
from pathlib import Path
import re
import unicodedata
from urllib.error import HTTPError,URLError

from configurar_clave_groq import stored_key
from groq_pilot import PilotError,prepare,suggest
from journey_memory import history_snapshot
from variant_preference import expected_selection
from suggestion_guard import guarded_draft
from quality_auditor import _atomic_json,_load
from sales_quality_gate import assess
import synthetic_lab as lab

MAX_CALLS=20
from groq_usage_policy import request_cap
MAX_REAL_RUNS_PER_DAY=request_cap(2)
STATE=Path(__file__).resolve().parent/".objections-run-state.json"
LOCK=Path(__file__).resolve().parent/".objections-run.lock"
REPORT=Path(__file__).resolve().parent/"quality"/"groq-objections-evaluation.json"
TOPICS={
 "product":("iphone","samsung","modelo","opcion","equipo","telefono"),
 "budget":("presupuesto","precio","alternativa","opcion","barato"),
 "discount":("descuento","precio","promocion","presupuesto"),
 "payment":("cuota","financiamiento","banco","tarjeta","pago"),
 "warranty":("garantia","cobertura","defecto","unidad"),
 "condition":("estado","nuevo","usado","revisar","probar"),
 "shipping":("entrega","envio","retiro","retirar","transport"),
 "inspection":("probar","revisar","estado","condicion"),
 "trade_in":("parte de pago","canje","valoracion","recibir"),
 "closing":("compra","disponibilidad","confirmar","asesor","retirar","entrega"),
 "comparison":("comparar","diferencia","opciones","alternativas","precio"),
}
JOURNEYS=[
 {"id":"budget-discount-inspection-close","turns":[
  ("Busco iPhone 15 Pro de 256GB negro","product",False),
  ("Mi presupuesto es limitado, ¿tienen otra opción más barata?","budget",True),
  ("Si pago en efectivo, ¿me hacen descuento?","discount",True),
  ("¿Es nuevo o usado? ¿Puedo revisarlo?","condition",True),
  ("Quiero comprarlo, ¿puedo retirarlo en Plaza Numa?","closing",True),
 ]},
 {"id":"finance-price-objection-warranty-close","turns":[
  ("Estoy viendo el Samsung S24 Ultra 256GB negro","product",False),
  ("¿Puedo pagarlo con tarjeta en 12 cuotas?","payment",True),
  ("En otro negocio lo vi más barato, ¿me mejoran el precio?","discount",True),
  ("¿Qué garantía tiene si falla la batería?","warranty",True),
  ("Quiero llevármelo hoy, ¿me lo apartan?","closing",True),
 ]},
 {"id":"color-change-compare-delivery-close","turns":[
  ("Busco iPhone 14 Pro Max de 128GB negro","product",False),
  ("No quiero negro, mejor 256GB blanco","product",False),
  ("¿Y el negro de 128GB cuesta lo mismo?","comparison",True),
  ("¿Cuánto tarda el envío para Choloma?","shipping",True),
  ("Si me lo pueden entregar esta semana, lo compro, ¿me confirmás?","closing",True),
 ]},
 {"id":"trade-in-coverage-inspection-pay","turns":[
  ("Busco un iPhone 15 de 128GB azul","product",False),
  ("¿Reciben mi celular como parte de pago?","trade_in",True),
  ("¿Qué pasa si viene sin cargador, tiene garantía?","warranty",True),
  ("¿Lo puedo probar antes de pagar?","inspection",True),
  ("Estoy listo para comprar, ¿dónde pago?","payment",True),
 ]},
]
def fold(text):
 return "".join(c for c in unicodedata.normalize("NFKD",text.lower())
       if not unicodedata.combining(c))
def topic_matches(reply,topic):
 norm=fold(reply)
 return any(fold(x) in norm for x in TOPICS[topic])
def effective_handoff(reply,review):
 return not review or (reply.get("human_review") is True)
def failure_category(exc):
 if isinstance(exc,SharedBudgetExceeded):return "shared_daily_budget_exhausted"
 cause=getattr(exc,"__cause__",None)
 if isinstance(cause,HTTPError):
  if cause.code==429:return "provider_rate_limited"
  if cause.code>=500:return "provider_server_error"
  return "provider_http_error"
 if isinstance(cause,(URLError,TimeoutError)):return "provider_network_error"
 if isinstance(exc,PilotError):
  content=str(exc).lower()
  if any(word in content for word in ("distinta","cambi[oó]","diferente","preferida","elegida")):
   return "preference_validation_rejected"
  return "structured_response_rejected"
 return "local_validation_error"

class SharedBudgetExceeded(RuntimeError):
 pass

def reserve_shared_call():
 """Count this evaluation against the same UTC budget as other Groq labs."""
 with open(lab.LOCK,"a+",encoding="utf8") as lock:
  os.fchmod(lock.fileno(),0o600)
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  current=_load(lab.STATE,lab.previous_state())
  try:lab.reserve(current)
  except RuntimeError as exc:raise SharedBudgetExceeded("Daily shared Groq budget exhausted") from exc

def execute(api=suggest,key_provider=stored_key,pacing_seconds=0,budget_hook=None):
 if os.getenv("SOFTMOBILE_AI_ENABLED")!="true":
  raise RuntimeError("Synthetic evaluation must be explicitly enabled")
 key=key_provider()
 if not key:raise RuntimeError("Missing Groq key")
 rows=[];api_calls=0;provider_aborted=False
 for case in JOURNEYS:
  prior=[]
  for step,(buyer,topic,must_human) in enumerate(case["turns"],1):
   if api_calls>=MAX_CALLS:raise RuntimeError("Maximum 20 Groq requests reached")
   prior_context=history_snapshot(prior[-4:])
   cleaned=prepare({"conversation_id":3,"message":buyer,"context":prior_context})
   state=history_snapshot((prior+[buyer])[-4:])
   pref=expected_selection(buyer)
   row={"id":case["id"],"turn":step,"topic":topic,
      "valid":False,"memory_ok":False,"human_ok":False,
      "topical":False,"actionable":False,"specific":False,"meaningful":False,
      "claims_blocked":False}
   if provider_aborted:
    row["reason"]="not_run_provider_unavailable"
    rows.append(row)
    prior.append(buyer)
    continue
   try:
    if api_calls and pacing_seconds>0:time.sleep(pacing_seconds)
    if budget_hook is not None:budget_hook()
    api_calls+=1
    proposed=api(cleaned,key)
    draft,blocked=guarded_draft(proposed,cleaned)
    want_model=state.get("model")
    got_model=proposed.get("model")
    models_ok=(not want_model or
       (isinstance(got_model,str) and fold(got_model)==fold(want_model)))
    wanted_capacity=state.get("storage_gb")
    cap_ok=not wanted_capacity or proposed.get("storage_gb")==wanted_capacity
    wanted_color=state.get("color_options")
    col_ok=not wanted_color or wanted_color in [
      str(x).casefold() for x in proposed.get("color_options",[])]
    # No invented chosen variant for an unresolved two-option comparison
    if pref["ambiguous"]:
     col_ok=col_ok and draft["human_review"] is True
    response=draft["suggested_reply"]
    rubric=assess(response,topic)
    row.update({"valid":True,"memory_ok":bool(models_ok and cap_ok and col_ok),
       "human_ok":bool(effective_handoff(draft,must_human)),
       "topical":bool(rubric["relevant"]),
       "actionable":bool(rubric["actionable"]),
       "specific":bool(rubric["specific"]),
       "meaningful":bool(rubric["meaningful"]),
       "claims_blocked":bool(blocked)})
   except (PilotError,ValueError,RuntimeError,TypeError) as exc:
    row["reason"]=failure_category(exc)
    if row["reason"] in {"provider_rate_limited","provider_server_error","provider_network_error","shared_daily_budget_exhausted"}:
     provider_aborted=True
   rows.append(row)
   prior.append(buyer)
 ok=lambda r: r["valid"] and r["memory_ok"] and r["human_ok"] and r["topical"] and r["actionable"] and r["specific"] and r["meaningful"]
 return {"evaluated_at":datetime.now(timezone.utc).isoformat(),
  "fictional_journeys":len(JOURNEYS),"turns":len(rows),
  "api_calls":api_calls,"all_checks_passed":sum(ok(r) for r in rows),
  "valid_responses":sum(r["valid"] for r in rows),
  "memory_errors":sum(r["valid"] and not r["memory_ok"] for r in rows),
  "missing_human_handoffs":sum(r["valid"] and not r["human_ok"] for r in rows),
  "off_topic":sum(r["valid"] and not r["topical"] for r in rows),
  "unhelpful_or_bulk":sum(r["valid"] and not (r["actionable"] and r["specific"] and r["meaningful"]) for r in rows),
  "invalid_responses":sum((not r["valid"]) and r.get("reason")!="not_run_provider_unavailable" for r in rows),
  "provider_aborted":provider_aborted,
  "not_run_provider":sum(r.get("reason")=="not_run_provider_unavailable" for r in rows),
  "failure_categories":{k:sum(x.get("reason")==k for x in rows)
      for k in sorted({x.get("reason") for x in rows if x.get("reason")})},
  "claims_blocked":sum(r["claims_blocked"] for r in rows),
  "results":rows,"public_messages_sent":0,
  "real_inventory_queried":False,"real_orders_created":0,
  "pilot_bot_modified":False,"all_passed":all(map(ok,rows))}
def reserve_real_run():
 today=datetime.now(timezone.utc).date().isoformat()
 previous=json.loads(STATE.read_text()) if STATE.exists() else {}
 prior_runs=previous.get("runs",0) if previous.get("day")==today else 0
 if not isinstance(prior_runs,int) or prior_runs<0 or prior_runs>=MAX_REAL_RUNS_PER_DAY:
  raise RuntimeError("Daily synthetic test run limit reached")
 _atomic_json(STATE,{"day":today,"runs":prior_runs+1})
 return prior_runs+1

def main():
 parser=argparse.ArgumentParser()
 g=parser.add_mutually_exclusive_group(required=True)
 g.add_argument("--run",action="store_true")
 g.add_argument("--status",action="store_true")
 args=parser.parse_args()
 if args.status:
  print(json.dumps(json.loads(REPORT.read_text()) if REPORT.exists() else {"status":"not_run"}))
  return
 with open(LOCK,"a+",encoding="utf8") as lock:
  os.fchmod(lock.fileno(),0o600)
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  reserve_real_run()
  result=execute(pacing_seconds=2.0,budget_hook=reserve_shared_call)
 REPORT.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
 _atomic_json(REPORT,result)
 print(json.dumps(result,ensure_ascii=False))
if __name__=="__main__":main()
