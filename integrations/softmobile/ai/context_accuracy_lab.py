#!/usr/bin/env python3
"""Isolated preference-memory QA from synthetic customer dialogues."""
import argparse,json
from pathlib import Path
from datetime import datetime,timezone
import offline_issue_replay as replay
from quality_auditor import _load,_atomic_json
from synthetic_lab import normalize

ROOT=Path(__file__).resolve().parent
REPORT=ROOT/"quality"/"context-accuracy-report.json"
CASES=[
 ("color-black-to-blue",["Quiero cambiar el color del celular que pedí. Estaba en negro, ¿puedo cambiarlo a azul?"],"azul"),
 ("color-explicit-blue",["Quisiera cambiar el color de negro a azul marino."],"azul"),
 ("color-green-to-white",["Quiero cambiar el color de verde a blanco."],"blanco"),
 ("capacity-64-vs-128",["Me interesa iPhone 15 de 128GB","Prefiero el 64GB, pero quisiera saber si la pantalla es igual a la del 128."],"64gb"),
 ("capacity-256-vs-128",["Quiero iPhone 15 de 128GB","Mejor quiero 256GB en lugar de 128GB."],"256gb"),
 ("capacity-128-not-256",["Busco iPhone 15 de 256GB","Prefiero el 128GB, no el 256GB."],"128gb"),
 ("capacity-simple-256",["Busco iPhone 15","256GB"],"256gb"),
 ("color-simple-blue",["Busco iPhone 15","Color azul"],"azul"),
]

def evaluate(source=None,runner=replay.isolated_replay):
 cases=[{"id":item[0],"scenario":{"category":"changes","messages":(["Hola","Busco un iPhone 15"]+item[1])[-3:]}} for item in CASES]
 results=runner(cases,source=source)
 if len(results)!=len(CASES):raise RuntimeError("Incomplete replay")
 expected={row[0]:row[2] for row in CASES}
 rows=[]
 for result in results:
  name=result["id"]
  if name not in expected:raise RuntimeError("Unrecognized scenario")
  turns=result["turns"]
  if not turns:raise RuntimeError("Empty transcript")
  answer=normalize(turns[-1]["bot"])
  passed=normalize(expected[name]) in answer
  rows.append({"id":name,"passed":passed,"expected_choice":expected[name]})
 return {"at":datetime.now(timezone.utc).isoformat(),
     "environment":"FICTIONAL_NO_NETWORK","total":len(rows),
     "passed":sum(row["passed"] for row in rows),
     "failed":len(rows)-sum(row["passed"] for row in rows),
     "failure_examples":[row for row in rows if not row["passed"]],
     "api_calls":0,"public_messages_sent":0,"deployed":False}

def main():
 a=argparse.ArgumentParser()
 g=a.add_mutually_exclusive_group(required=True)
 g.add_argument("--run",action="store_true")
 g.add_argument("--status",action="store_true")
 args=a.parse_args()
 result=evaluate() if args.run else _load(REPORT,{"status":"not_run"})
 if args.run:_atomic_json(REPORT,result)
 print(json.dumps(result,ensure_ascii=False))
if __name__=="__main__":main()
