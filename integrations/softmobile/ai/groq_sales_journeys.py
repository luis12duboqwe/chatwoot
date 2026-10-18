#!/usr/bin/env python3
"""Three-turn fictional sales journey evaluation for the private Groq copilot.

Never sends public Chatwoot/WhatsApp messages. Each API request only includes
the current fictitious customer question and the derived preference snapshot
of up to four previous fictitious messages. No invented stock or price checks.
"""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path

from configurar_clave_groq import stored_key
from groq_pilot import PilotError,prepare,suggest
from journey_memory import history_snapshot
from variant_preference import expected_selection
from suggestion_guard import guarded_draft
from quality_auditor import _atomic_json

DATA=Path(__file__).resolve().parent/"quality"
REPORT=DATA/"groq-sales-journeys-report.json"
MAX_API_CALLS=12
JOURNEYS=[
 {"id":"choose-then-ship","turns":[
  {"buyer":"Busco iPhone 15 Pro de 512 GB negro","review":False},
  {"buyer":"Si no hay 512GB negro, mejor 256GB azul","review":True},
  {"buyer":"¿Lo puedo retirar en Choloma?","review":True}]},
 {"id":"compare-without-changing-choice","turns":[
  {"buyer":"Quiero Samsung S24 Ultra 256GB negro","review":False},
  {"buyer":"¿Cuánto cuesta el de 128GB azul? Prefiero seguir con el negro de 256GB","review":True},
  {"buyer":"¿Qué garantía tiene y qué accesorios incluye?","review":True}]},
 {"id":"change-mind-and-purchase","turns":[
  {"buyer":"Busco iPhone 14 Pro Max de 128GB negro","review":False},
  {"buyer":"Mejor el de 256GB blanco","review":False},
  {"buyer":"¿Puedo probarlo antes de pagar?","review":True}]},
 {"id":"compare-then-decide","turns":[
  {"buyer":"¿Qué me conviene, iPhone 15 de 128GB negro o 256GB azul?","review":True},
  {"buyer":"Prefiero el de 128GB rojo","review":False},
  {"buyer":"¿Cuánto tarda el envío para San Pedro Sula?","review":True}]},
]

def _canonical_model(m):
 if not isinstance(m,str):return ""
 return " ".join(m.casefold().split())

def execute(api=suggest,key_provider=stored_key):
 if os.getenv("SOFTMOBILE_AI_ENABLED")!="true":
  raise RuntimeError("Explicit synthetic evaluation flag required")
 key=key_provider()
 if not key:raise RuntimeError("Groq key missing")
 rows=[]
 calls=0
 for journey in JOURNEYS:
  previous=[]
  for number,step in enumerate(journey["turns"],1):
   if calls>=MAX_API_CALLS:raise RuntimeError("12-call synthetic hard cap exceeded")
   snapshot=history_snapshot(previous[-4:])
   current=step["buyer"]
   clean=prepare({"conversation_id":3,"message":current,"context":snapshot})
   expected=history_snapshot((previous+[current])[-4:])
   pref=expected_selection(current)
   row={"journey":journey["id"],"turn":number,
        "model_match":False,"variant_match":False,"review_correct":False,
        "safe_draft":False,"provider_valid":False,"blocked_claim":False,
        "sanitized_memory_fields":sorted(snapshot)}
   try:
    calls+=1
    output=api(clean,key)
    draft,blocked=guarded_draft(output,clean)
    match_model=(not expected.get("model") or _canonical_model(output.get("model"))==
        _canonical_model(expected["model"]))
    match_storage=(not expected.get("storage_gb") or
        output.get("storage_gb")==expected["storage_gb"])
    match_color=(not expected.get("color_options") or
        expected["color_options"] in [str(x).casefold() for x in output.get("color_options",[])])
    if pref["ambiguous"]:
     # No model may silently assert a selected color when the buyer
     # explicitly offered multiple incompatible options.
     match_color=not output.get("color_options") or draft.get("human_review") is True
    row.update({"provider_valid":True,"model_match":bool(match_model),
     "variant_match":bool(match_storage and match_color),
     "review_correct":bool(not step["review"] or draft["human_review"]),
     "safe_draft":True,"blocked_claim":bool(blocked)})
   except (PilotError,ValueError,RuntimeError,TypeError):
    row["failure"]="rejected_response_or_provider"
   rows.append(row)
   previous.append(current)
 successful=sum(x["provider_valid"] and x["model_match"] and x["variant_match"]
         and x["review_correct"] and x["safe_draft"] for x in rows)
 return {"evaluated_at":datetime.now(timezone.utc).isoformat(),
  "journeys":len(JOURNEYS),"turns":len(rows),
  "api_calls":calls,"validated_turns":successful,
  "invalid_responses":sum(not x["provider_valid"] for x in rows),
  "memory_mismatches":sum(x["provider_valid"] and
    not (x["model_match"] and x["variant_match"]) for x in rows),
  "unsafe_claims_blocked":sum(x["blocked_claim"] for x in rows),
  "results":rows,"all_passed":successful==len(rows),
  "public_messages_sent":0,"real_inventory_queried":False,
  "pilot_code_modified":False,
  "public_auto_reply_enabled":False}

def main():
 p=argparse.ArgumentParser()
 g=p.add_mutually_exclusive_group(required=True)
 g.add_argument("--run",action="store_true")
 g.add_argument("--status",action="store_true")
 args=p.parse_args()
 if args.status:
  print(json.dumps(json.loads(REPORT.read_text()) if REPORT.exists() else {"status":"not_run"}))
  return
 report=execute()
 DATA.mkdir(parents=True,exist_ok=True,mode=0o700)
 _atomic_json(REPORT,report)
 print(json.dumps(report,ensure_ascii=False))
if __name__=="__main__":main()
