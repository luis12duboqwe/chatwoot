#!/usr/bin/env python3
"""Opt-in finite Groq shadow evaluation with fictional buyers; NEVER send chats.

Seven fixed fictional cases. No personal records, inventory, orders, payments,
Chatwoot writes or customer messages. Aggregate JSON status only.
"""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path

from configurar_clave_groq import stored_key
from groq_pilot import PilotError,prepare,suggest
from suggestion_guard import guarded_draft
from variant_preference import expected_selection
from quality_auditor import _atomic_json

DATA=Path(__file__).resolve().parent/"quality"
REPORT=DATA/"groq-sales-shadow-evaluation.json"
CASES=[
 {"id":"change-capacity-color","message":"Ahora prefiero el iPhone 15 Pro de 256 GB azul",
  "context":{"model":"iPhone 15 Pro","storage_gb":"128","color_options":"negro"},
  "must_human":False},
 {"id":"preferred-vs-compared","message":"Prefiero el azul de 256GB, pero ¿cuánto cuesta el negro de 128GB?",
  "context":{"model":"iPhone 15 Pro","storage_gb":"128","color_options":"negro"},
  "must_human":True},
 {"id":"conditional-fallback","message":"Si no hay 512GB negro, mejor 256GB azul",
  "context":{"model":"iPhone 15 Pro","storage_gb":"512","color_options":"negro"},
  "must_human":True},
 {"id":"ambiguity-options","message":"Quiero 128GB negro o 256GB azul, ¿cuál me conviene?",
  "context":{"model":"iPhone 15 Pro"},"must_human":True},
 {"id":"warranty-bundle","message":"¿Qué garantía incluye y qué accesorios trae el Samsung S24 Ultra?",
  "context":{"model":"Samsung S24 Ultra","storage_gb":"256"},"must_human":True},
 {"id":"delivery-eta","message":"¿Cuánto tarda el envío para Choloma?",
  "context":{"model":"iPhone 14 Pro Max","city":"Choloma"},"must_human":True},
 {"id":"new-intent","message":"Busco un iPhone 14 Pro Max de 256GB en negro",
  "context":{},"must_human":False}
]

def evaluate(api=suggest,key_provider=stored_key):
 results=[]
 if os.getenv("SOFTMOBILE_AI_ENABLED")!="true":
  raise RuntimeError("Explicit synthetic Groq evaluation flag missing")
 key=key_provider()
 if not key:raise RuntimeError("No key")
 for case in CASES:
  clean=prepare({"conversation_id":3,"message":case["message"],"context":case["context"]})
  expected=expected_selection(case["message"])
  row={"id":case["id"],"api_ok":False,"safe":False,"expected_matched":False,
       "human_handoff":False,"blocked_claim":False}
  try:
   response=api(clean,key)
   candidate,blocked=guarded_draft(response)
   match=(expected["storage_gb"] is None or response["storage_gb"]==expected["storage_gb"])
   if expected["color"] is not None:
    match=match and expected["color"] in [str(x).lower() for x in response["color_options"]]
   handoff=(candidate["human_review"] is True or not case["must_human"])
   row.update({"api_ok":True,"safe":True,
     "expected_matched":bool(match),"human_handoff":bool(handoff),
     "blocked_claim":bool(blocked)})
  except (PilotError,RuntimeError,ValueError,TypeError) as exc:
   # Fixed error categories only; never log provider payloads or user data.
   desc=str(exc).lower()
   row["rejection_category"]=("capacity_mismatch" if "capacidad" in desc else
       "color_mismatch" if "color distinto" in desc else
       "invalid_response_or_provider" if isinstance(exc,PilotError) else
       "unavailable")
  results.append(row)
 return {"evaluated_at":datetime.now(timezone.utc).isoformat(),
    "fictional_cases":len(CASES),
    "valid_structured":sum(x["api_ok"] for x in results),
    "preferred_variant_match":sum(x["expected_matched"] for x in results),
    "safe_handoff":sum(x["human_handoff"] for x in results),
    "claim_blocks":sum(x["blocked_claim"] for x in results),
    "results":results,"real_messages_sent":0,"pilot_code_modified":False,
    "all_passed":all(x["api_ok"] and x["safe"] and x["expected_matched"] and x["human_handoff"] for x in results)}

def main():
 p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
 g.add_argument("--run",action="store_true");g.add_argument("--status",action="store_true")
 args=p.parse_args()
 if args.status:
  print(json.dumps(json.loads(REPORT.read_text()) if REPORT.exists() else {"status":"not_run"}))
  return
 result=evaluate()
 DATA.mkdir(parents=True,exist_ok=True,mode=0o700)
 _atomic_json(REPORT,result)
 print(json.dumps(result,ensure_ascii=False))
if __name__=="__main__":main()
