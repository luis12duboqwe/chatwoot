#!/usr/bin/env python3
"""Independent offline oracle vs live Ruby parser using fully fictional inventory.

No AI output or customer data authorizes an automated production change.
One immutable set of deterministic fixtures probes normal/short/long dialogs,
variant transitions, sold-out colors and missing variants. Failing cases go
to a review-only queue with short digests and no customer identifiers.
"""
from datetime import datetime,timezone
from itertools import islice
import hashlib
import json
import os
from pathlib import Path
import random
import re

import inventory_training_lab as trainer
from training_inventory import SimulationInventory, normalize as norm
from quality_auditor import _atomic_json,_load

ROOT=Path(__file__).resolve().parent
REPORT=ROOT/"quality"/"training-inventory-quality-report.json"
ISSUES=ROOT/"quality"/"training-inventory-review-issues.json"
SEED=12018
MAX_STORED=120

def scenarios():
 items=SimulationInventory().catalog()
 rng=random.Random(SEED)
 results=[]
 # Observe Ruby parsing as a separate test subject, never derive expected
 # model/storage/color from its own output.
 for i,record in enumerate(items):
  model=record["model"]; gb=record["capacity_gb"]; col=record["color"]
  variants=[
   ([f"Busco {model} de {gb} GB {col}"],"single"),
   ([f"¿Tienen {model} {gb}GB en {col}?"],"natural-availability"),
   ([f"Quiero un {model}",f"El de {gb} GB",f"En color {col}"],"followup"),
   ([f"Me interesa el {model} {gb} GB en azul",f"Mejor en {col}"],"correct-color"),
   ([f"{model} {gb}GB {col}","¿Cuál es el precio?"],"price-context"),
   ([f"{model} {gb} GB {col}","¿Está disponible?"],"stock-context")
  ]
  for j,(msgs,kind) in enumerate(variants):
   results.append({"id":f"m{i:02d}-t{j:02d}","messages":msgs,"expected":"variant",
      "truth":{"model":model,"capacity_gb":gb,"color":col},"kind":kind})
 # Pairwise model switches are important because color and storage must reset.
 choices=list(enumerate(items));rng.shuffle(choices)
 for i,(idx,item) in enumerate(choices):
  previous=items[(idx+5)%len(items)]
  if previous["model"]==item["model"]:previous=items[(idx+7)%len(items)]
  msg=[f"Busco {previous['model']} {previous['capacity_gb']} GB {previous['color']}",
       f"Ahora quiero {item['model']} {item['capacity_gb']} GB {item['color']}"]
  results.append({"id":f"switch-{i:02d}","messages":msg,"expected":"variant",
     "truth":{"model":item["model"],"capacity_gb":item["capacity_gb"],"color":item["color"]},
     "kind":"model-switch"})
 # Missing a shade must NOT commit fake availability; missing capacities
 # must NOT silently substitute 256GB if the user asked for 512GB.
 for idx,item in enumerate(items):
  results.append({"id":f"missing-color-{idx:02d}",
      "messages":[f"Quiero {item['model']} de {item['capacity_gb']} GB",
         "¿Qué precio tiene?"],"expected":"incomplete",
      "truth":{"model":item["model"],"capacity_gb":item["capacity_gb"],"color":None},
      "kind":"missing-color"})
  results.append({"id":f"unlisted-capacity-{idx:02d}",
      "messages":[f"Busco {item['model']} de 512 GB {item['color']}","¿Hay disponible?"],
      "expected":"absent-variant",
      "truth":{"model":item["model"],"capacity_gb":512,"color":item["color"]},
      "kind":"unlisted-capacity"})
  # Full label changes after the initial sale inquiry must not reuse the
  # previous model/variant if user clearly switches devices.
 return results

def grouped(seq,size=25):
 seq=iter(seq)
 while True:
  page=list(islice(seq,size))
  if not page:break
  yield page

def trace_eval(entry,row,inventory):
 steps=row["steps"]
 final=steps[-1]
 model=final.get("model")
 size=trainer.strict_capacity(final.get("capacity"))
 col=final.get("color")
 target=entry["truth"]
 # Never mark a malformed Ruby model parse as an actual stock guarantee.
 parsed=(norm(model)==norm(target["model"])
         and size==target["capacity_gb"]
         and norm(col)==norm(target["color"]))
 quote=trainer.simulated_response(final,inventory)
 if entry["expected"]=="variant":
  passed=parsed and quote["status"] in ("in_stock","out_of_stock")
 elif entry["expected"]=="incomplete":
  passed=(norm(model)==norm(target["model"]) and size==target["capacity_gb"]
          and not col and quote["status"]=="missing_variant")
 elif entry["expected"]=="absent-variant":
  passed=parsed and quote["status"]=="not_found"
 else:raise ValueError("Unexpected independent expectation")
 # Baseline must not pretend a fake quote is actual stock.
 baseline=final.get("baseline") or ""
 unsafe=bool(re.search(
   r"\b(?:lo tengo disponible|tenemos disponible|pago confirmado|ya esta reservado|ya esta apartado)\b|"
   r"\b(?:precio definitivo|precio final)\s*(?:es|:)?\s*L\s*\d",
   baseline,re.I))
 return {"id":entry["id"],"kind":entry["kind"],"passed":bool(passed and not unsafe),
         "parser_match":parsed,"observed":quote["status"],"unsafe_public_claim":unsafe,
         "expected":entry["expected"],
         "ruby_model":model,"ruby_capacity":final.get("capacity"),"ruby_color":col}

def evaluate(parser=trainer.parse_with_real_ruby,source=None):
 items=SimulationInventory()
 tasks=scenarios()
 results=[]
 for block in grouped(tasks,25):
  rows=[{"id":x["id"],"messages":x["messages"],"expected":"not_found"} for x in block]
  traces=parser(rows,source=source)
  if len(traces)!=len(block):raise RuntimeError("Parser count differs from oracle scenarios")
  for entry,row in zip(block,traces):
   if row.get("id")!=entry["id"] or len(row.get("steps",[]))!=len(entry["messages"]):
    raise RuntimeError("Ruby runner returned untrusted order or malformed steps")
   results.append(trace_eval(entry,row,items))
 failed=[r for r in results if not r["passed"]]
 counts={}
 for item in results:
  item_type=item["kind"]
  if item_type not in counts:counts[item_type]={"pass":0,"fail":0}
  counts[item_type]["pass" if item["passed"] else "fail"]+=1
 safety_violations=sum(x["unsafe_public_claim"] for x in results)
 report={"at":datetime.now(timezone.utc).isoformat(),
  "environment":"OFFLINE_TRAINING_ONLY",
  "scenario_count":len(tasks),"passed":len(tasks)-len(failed),
  "failed":len(failed),"safety_violations":safety_violations,
  "pass_rate":round((len(tasks)-len(failed))/len(tasks),4),
  "per_family":counts,"training_only":True,"production_messages_sent":0,
  "production_stock_changed":False,
  "public_ruby_sha256":hashlib.sha256(trainer.BOT.read_bytes()).hexdigest(),
  "first_failures":failed[:18]}
 return report

def run(parser=trainer.parse_with_real_ruby,source=None):
 report=evaluate(parser=parser,source=source)
 failed=report["first_failures"]
 # Issue queue independent of the real sales-bot auto-promoter.
 history=_load(ISSUES,[])
 if not isinstance(history,list):raise ValueError("Untrusted training review history")
 previous={entry.get("id") for entry in history if isinstance(entry,dict)}
 for item in failed:
  if item["id"] in previous:continue
  issue={"id":item["id"],"first_seen":report["at"],"status":"training_review_only",
         "environment":"OFFLINE_TRAINING_ONLY","kind":item["kind"],
         "reason":"Oracle disagrees with the Ruby interpretation of a fictitious buyer.",
         "may_deploy_automatically":False,"details":item}
  history.append(issue)
 _atomic_json(ISSUES,history[-MAX_STORED:])
 _atomic_json(REPORT,report)
 return report

def main():
 import argparse
 p=argparse.ArgumentParser()
 a=p.add_mutually_exclusive_group(required=True)
 a.add_argument("--run",action="store_true")
 a.add_argument("--status",action="store_true")
 o=p.parse_args()
 if o.status:print(json.dumps(_load(REPORT,{"status":"not_run"}),ensure_ascii=False));return 0
 report=run()
 print(json.dumps({k:v for k,v in report.items() if k!="first_failures"},ensure_ascii=False))
 # Quality failures go to review, not an automated Ruby install.
 return 0 if report["safety_violations"]==0 else 1
if __name__=="__main__":
 raise SystemExit(main())
