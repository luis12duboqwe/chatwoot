#!/usr/bin/env python3
"""Previously unseen finance phrases, independent of 72 training dialogs.

Catches numeric installment counts spuriously recognized as Samsung A models.
All requests are fictional and no prices are quoted or payments are taken.
"""
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path
import inventory_training_lab as lab
from inventory_quality_lab import grouped
from training_inventory import SimulationInventory,normalize as norm
from quality_auditor import _atomic_json,_load

ROOT=Path(__file__).resolve().parent
REPORT=ROOT/"quality"/"financing-holdout-report.json"
TEMPLATES=("¿Cuánto pago a 18 meses?","¿Lo puedo sacar a 24 cuotas?",
           "¿Y a 36 pagos mensuales?","¿Cuál sería la cuota a 10 plazos?")

def scenarios():
 cases=[]
 for n,r in enumerate(SimulationInventory().catalog()):
  for j,template in enumerate(TEMPLATES):
   cases.append({"id":f"holdout-{n:02d}-{j:02d}",
    "messages":[f"Me interesa {r['model']} {r['capacity_gb']} GB {r['color']}",template],
    "expected":"not_found",
    "truth":{"model":r["model"],"capacity_gb":r["capacity_gb"],"color":r["color"]}})
 return cases

def verify(source=None):
 cases=scenarios()
 result=[]
 for chunk in grouped(cases,25):
  passed=lab.parse_with_real_ruby([{k:x[k] for k in ("id","messages","expected")} for x in chunk],source=source)
  if len(chunk)!=len(passed):raise RuntimeError("Holdout output incomplete")
  for expected,observed in zip(chunk,passed):
   if expected["id"]!=observed["id"]:raise RuntimeError("Holdout Ruby mismatch")
   o=observed["steps"][-1];truth=expected["truth"]
   correct=(norm(o.get("model"))==norm(truth["model"])
            and lab.strict_capacity(o.get("capacity"))==truth["capacity_gb"]
            and norm(o.get("color"))==norm(truth["color"]))
   result.append({"id":expected["id"],"pass":bool(correct),
     "misread_as_other_model":o.get("model") if not correct else None})
 return {"at":datetime.now(timezone.utc).isoformat(),
  "type":"previously_unseen_installment_phrases",
  "environment":"OFFLINE_TRAINING_ONLY",
  "total":len(result),"passed":sum(x["pass"] for x in result),
  "failed_ids":[x["id"] for x in result if not x["pass"]][:20],
  "source_sha256":sha256((lab.BOT.read_text() if source is None else source).encode()).hexdigest(),
  "public_messages_sent":0,"real_inventory_modified":False}

def main():
 import argparse
 p=argparse.ArgumentParser()
 g=p.add_mutually_exclusive_group(required=True)
 g.add_argument("--run",action="store_true")
 g.add_argument("--status",action="store_true")
 args=p.parse_args()
 if args.status:print(json.dumps(_load(REPORT,{"status":"not_run"}),ensure_ascii=False));return 0
 x=verify()
 _atomic_json(REPORT,x)
 print(json.dumps(x,ensure_ascii=False))
 return 0
if __name__=="__main__":
 raise SystemExit(main())
