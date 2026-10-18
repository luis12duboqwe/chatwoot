#!/usr/bin/env python3
"""Fully isolated exercise: current sales Ruby PARSER + fictitious inventory.

No Chatwoot, WAHA, webhook, network, database or real SKU is accessed. The
training quote adapter exists exclusively in Python and is never imported
by the public sales script. All outputs visibly label SIMULATION.
"""
import argparse
import base64
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

from quality_auditor import _atomic_json
from training_inventory import SimulationInventory,CATALOG_VERSION,LABEL
from isolated_gate import SEPARATOR
from sandbox_review import IMAGE

BOT=Path("/opt/softmobile-waha-test/sales-bot-v2.rb")
ROOT=Path(__file__).resolve().parent
REPORT=ROOT/"quality"/"training-inventory-report.json"
MARK="SM_TRAINING_INVENTORY_PARSER="
SCENARIOS=[
 {"id":"available-iphone","messages":["Busco iPhone 14 Pro Max de 256 GB negro","¿Lo tienen disponible?"],"expected":"in_stock"},
 {"id":"soldout-gold","messages":["Quiero iPhone 14 Pro Max de 256 GB dorado","¿Tienen existencia?"],"expected":"out_of_stock"},
 {"id":"samsung-price","messages":["Busco Samsung S24 Ultra de 256 GB azul","¿Cuál es el precio?"],"expected":"in_stock"},
 {"id":"iphone13-price","messages":["Busco iPhone 13 de 128 GB blanco","¿Cuánto cuesta?"],"expected":"in_stock"},
 {"id":"iphone15-stock","messages":["Quiero un iPhone 15 de 128 GB azul","¿Tienen disponible?"],"expected":"in_stock"},
 {"id":"samsung-soldout","messages":["Quiero Samsung S24 Ultra 256 GB negro","¿Lo tienen?"],"expected":"out_of_stock"},
 {"id":"missing-color","messages":["Quiero iPhone 14 Pro Max de 256 GB","¿Qué precio tiene?"],"expected":"missing_variant"},
 {"id":"color-change","messages":["Busco iPhone 14 Pro Max de 256 GB negro","Mejor en dorado","¿Tenés?"],"expected":"out_of_stock"},
 {"id":"capacity-change","messages":["Busco iPhone 15 128 GB azul","Mejor el de 256 GB negro","¿Hay?"],"expected":"in_stock"},
 {"id":"iphone12-price","messages":["Quiero iPhone 12 de 128 GB rojo","¿Cuánto sale?"],"expected":"in_stock"},
 {"id":"iphone13-soldout","messages":["Quiero iPhone 13 de 128 GB negro","¿Hay disponible?"],"expected":"out_of_stock"}
]

def validate_scenarios(scenarios):
 if not isinstance(scenarios,list) or not 1<=len(scenarios)<=30:raise ValueError("Invalid scenario length")
 seen=set()
 for s in scenarios:
  if not isinstance(s,dict) or set(s)!={"id","messages","expected"}:
   raise ValueError("Invalid scenario record")
  if not isinstance(s["id"],str) or not re.fullmatch(r"[a-z0-9-]{3,40}",s["id"]) or s["id"] in seen:
   raise ValueError("Invalid scenario ID")
  seen.add(s["id"])
  if s["expected"] not in ("in_stock","out_of_stock","missing_variant","not_found"):
   raise ValueError("Invalid scenario expectation")
  if not isinstance(s["messages"],list) or not 1<=len(s["messages"])<=5:
   raise ValueError("Invalid messages")
  for m in s["messages"]:
   if not isinstance(m,str) or not 3<=len(m)<=145:
    raise ValueError("Invalid buyer utterance")
   if re.search(r"https?://|@|\b(?:cvv|pin|otp|contrase[nñ]a|rtn)\b|\+?504\d{8}",m,re.I):
    raise ValueError("Sensitive or external content in fictional scenario")
 return scenarios

def parse_with_real_ruby(scenarios,source=None,runner=subprocess.run):
 """Use current Ruby context/intent logic in a no-network ephemeral container."""
 validate_scenarios(scenarios)
 source_text=BOT.read_text() if source is None else source
 if source_text.count(SEPARATOR)!=1:raise ValueError("Ruby test boundary missing")
 core=source_text.split(SEPARATOR,1)[0]
 serial=base64.b64encode(json.dumps(scenarios,ensure_ascii=False).encode()).decode()
 ruby="require 'json'\nrequire 'base64'\n"+core+f"""
records=JSON.parse(Base64.strict_decode64('{serial}'))
raise 'bad records' unless records.length<=30
result=records.map do |row|
 h=[]
 steps=row.fetch('messages').map do |m|
  h << m
  c=SoftMobileSales.context_from(h)
  p=SoftMobileSales.plan(m,c,[],nil)
  {{model:SoftMobileSales.model_name(c[:model]),
    capacity:c[:capacity],color:c[:color],
    intent:SoftMobileSales.intent(m).to_s,baseline:p[:reply].to_s[0,240]}}
 end
 {{id:row.fetch('id'),steps:steps}}
end
puts '{MARK}'+JSON.generate(result)
"""
 cmd=["docker","run","--rm","-i","--pull","never","--network","none",
      "--read-only","--cap-drop","ALL","--security-opt","no-new-privileges",
      "--pids-limit","48","--memory","200m","--cpus","0.5",
      "--user","65534:65534","--tmpfs","/tmp:rw,noexec,nosuid,size=8m",
      "--env","HOME=/tmp","--entrypoint","ruby",IMAGE,"-"]
 try:
  p=runner(cmd,input=ruby,text=True,capture_output=True,timeout=70)
 except (OSError,subprocess.TimeoutExpired) as exc:
  raise RuntimeError("Offline parser unavailable") from exc
 if p.returncode:raise RuntimeError("Isolated Ruby parsing failed")
 rows=[json.loads(line[len(MARK):]) for line in p.stdout.splitlines() if line.startswith(MARK)]
 if len(rows)!=1 or len(rows[0])!=len(scenarios):
  raise RuntimeError("Unexpected Ruby scenario results")
 return rows[0]

def strict_capacity(value):
 if not value:return None
 m=re.fullmatch(r"(\d{2,4})\s*GB",str(value).strip(),re.I)
 return int(m.group(1)) if m else None

def simulated_response(context,inventory):
 """Fictional quote; never a client-facing production answer."""
 model=context.get("model")
 capacity=strict_capacity(context.get("capacity"))
 color=context.get("color")
 if not model or capacity is None or not color:
  return {"status":"missing_variant","reply":LABEL+" | Falta confirmar modelo, capacidad o color antes de cotizar.","sku":None}
 result=inventory.quote(model,capacity,color)
 if result.status=="in_stock":
  r=result.record
  reply=(f"{LABEL} | {r['model']} {r['capacity_gb']}GB {r['color']}: "
          f"{r['units']} unidad(es) ficticias, precio simulado L {r['price_lps']:,}.")
  return {"status":"in_stock","reply":reply,"sku":r["sku"],"units":r["units"],"price_lps":r["price_lps"]}
 if result.status=="out_of_stock":
  options=", ".join(f"{r['capacity_gb']}GB {r['color']}" for r in result.alternatives) or "sin alternativas simuladas"
  return {"status":"out_of_stock","reply":LABEL+" | Variante agotada en el inventario ficticio; alternativas: "+options+".",
          "sku":result.record["sku"] if result.record else None}
 return {"status":"not_found","reply":LABEL+" | No existe esa combinación en el inventario ficticio.","sku":None}

def checkout_regressions():
 """In-memory operations for hold, cancel, sale, price update, exhaustion."""
 inv=SimulationInventory()
 sku="SIM-S23U-256-BLK"
 original=inv.quote("Samsung S23 Ultra",256,"Negro")
 token=inv.hold(sku,1)
 held=inv.quote("Samsung S23 Ultra",256,"Negro")
 restored=inv.release(token)
 again=inv.quote("Samsung S23 Ultra",256,"Negro")
 new_hold=inv.hold(sku,1)
 receipt=inv.checkout(new_hold)
 emptied=inv.quote("Samsung S23 Ultra",256,"Negro")
 replay=inv.checkout(new_hold)
 refused=inv.hold(sku,1)
 before=inv.quote("iPhone 13",128,"Blanco").record["price_lps"]
 inv.reprice("SIM-IPH13-128-WHT",before+250)
 after=inv.quote("iPhone 13",128,"Blanco").record["price_lps"]
 # Parallel BUYERS operate only on the isolated in-memory fixture.
 many=SimulationInventory()
 def buyer(_):
  key=many.hold("SIM-IPH14PM-256-BLK",1)
  if key:many.checkout(key)
  return key
 with ThreadPoolExecutor(max_workers=16) as pool:
  successes=[x for x in pool.map(buyer,range(32)) if x]
 no_oversell=(len(successes)==3
              and many.quote("iPhone 14 Pro Max",256,"Negro").status=="out_of_stock")
 held_price=SimulationInventory()
 ticket=held_price.hold("SIM-IPH15-128-BLU",1)
 old_cost=16500
 held_price.reprice("SIM-IPH15-128-BLU",old_cost+200)
 receipt=held_price.checkout(ticket)
 settled_price=bool(receipt and receipt["total_lps"]==old_cost)
 return {
  "hold_and_release":bool(token and restored and original.status=="in_stock"
                          and held.status=="out_of_stock" and again.status=="in_stock"),
  "checkout_decrements_once":bool(receipt and receipt["status"]=="simulated_only"
                                  and emptied.status=="out_of_stock" and replay is None and refused is None),
  "price_change_only_in_memory":after==before+250,
  "no_payment_or_customer_data":set(receipt)=={"status","sku","total_lps"},
  "parallel_buyers_no_oversell":no_oversell,
  "held_price_immutable":settled_price,
  "simulated_events":len(inv.events())
 }

def run(scenarios=None,inventory=None,source=None,runner=subprocess.run):
 selected=validate_scenarios(SCENARIOS if scenarios is None else scenarios)
 inv=inventory or SimulationInventory()
 ruby=parse_with_real_ruby(selected,source=source,runner=runner)
 checks=[]
 for s,parsed in zip(selected,ruby):
  if parsed.get("id")!=s["id"] or len(parsed.get("steps",[]))!=len(s["messages"]):
   raise RuntimeError("Ruby trace mismatch")
  last=parsed["steps"][-1]
  mock=simulated_response(last,inv)
  checks.append({"id":s["id"],"expected":s["expected"],"observed":mock["status"],
     "passed":s["expected"]==mock["status"],
     "parsed_model":last.get("model"),"parsed_capacity":last.get("capacity"),
     "parsed_color":last.get("color"),"reply":mock["reply"],
     "baseline_requires_verification":bool(re.search(r"confirmar|verificar|disponib",last.get("baseline",""),re.I))})
 commerce=checkout_regressions()
 return {"at":datetime.now(timezone.utc).isoformat(),
   "environment":"OFFLINE_TRAINING_ONLY","fixture":CATALOG_VERSION,
   "inventory":{"variants":len(inv.catalog()),"available_units":sum(x["units"] for x in inv.catalog()),"all_synthetic":True},
   "sales_journeys":len(checks),"passed_journeys":sum(x["passed"] for x in checks),
   "failed_journeys":[x["id"] for x in checks if not x["passed"]],
   "stock_operations":commerce,
   "public_customer_messages":0,"real_orders":0,"real_stock_modified":False,
   "network_allowed":False,"public_bot_source_modified":False,
   "bot_source_sha256":hashlib.sha256(BOT.read_bytes()).hexdigest() if source is None else None,
   "checks":checks}

def main():
 p=argparse.ArgumentParser()
 mode=p.add_mutually_exclusive_group(required=True)
 mode.add_argument("--run",action="store_true")
 mode.add_argument("--status",action="store_true")
 args=p.parse_args()
 if args.status:
  from quality_auditor import _load
  print(json.dumps(_load(REPORT,{"status":"not_run"}),ensure_ascii=False));return 0
 report=run()
 _atomic_json(REPORT,report)
 # Only fail CI when a simulated sales journey breaks or business invariants fail.
 print(json.dumps(report,ensure_ascii=False))
 return 0 if report["passed_journeys"]==report["sales_journeys"] and all(
  v is True for k,v in report["stock_operations"].items() if k!="simulated_events") else 1

if __name__=="__main__":sys.exit(main())
