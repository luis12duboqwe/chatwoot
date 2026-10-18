#!/usr/bin/env python3
"""Independent deterministic stress set for color/capacity parsing changes."""
import hashlib
import itertools
import json
import random
from pathlib import Path
import sandbox_review as sandbox
import patch_proposer as proposer
from quality_auditor import _atomic_json

COLORS=["negro","blanco","azul","rojo","dorado","verde","morado"]
CAPACITIES=["128GB","256GB","512GB"]

def generate(seed=20261018):
 rng=random.Random(seed)
 distinct=[x for x in itertools.permutations(COLORS,3)]
 rng.shuffle(distinct)
 cases=[]
 for i,(first,second,third) in enumerate(distinct[:30]):
  old,new=rng.sample(CAPACITIES,2)
  family="iPhone 15" if i%2==0 else "Samsung S24 Ultra"
  base="Busco el "+family+" de "+old
  specs=[
    (f"Si no hay {old} {first}, mejor {new} {second}",new,second),
    (f"Prefiero {first}, pero ¿cuánto cuesta el {second}?",old,first),
    (f"Si no hay {first}, prefiero {second}; ¿cuánto vale el {third}?",old,second),
    (f"Si no hay {first}, mejor {second}; si no hay {second}, {third}",old,third),
    (f"Prefiero {first} o {second}",old,first)
  ]
  for j,(follow,cap,color) in enumerate(specs):
   cases.append((f"stress-{i:02d}-{j}",[base,follow],cap,color.title()))
 return cases

def analyze(original,candidate):
 cases=generate()
 before=sandbox.isolated_run(original,cases)
 after=sandbox.isolated_run(candidate,cases)
 old={r["id"]:r for r in before}
 new={r["id"]:r for r in after}
 labels={name:(cap,color) for name,_,cap,color in cases}
 regress=[];fixed=[];still_bad=[]
 for key,expect in labels.items():
  p=old[key];q=new[key]
  okay_before=(p["capacity"],p["color"])==expect
  okay_after=(q["capacity"],q["color"])==expect
  if okay_before and not okay_after:regress.append(key)
  if not okay_before and okay_after:fixed.append(key)
  if not okay_after:still_bad.append(key)
 return {"scenarios":len(cases),"baseline_pass":len(cases)-len([x for x in labels if (old[x]["capacity"],old[x]["color"])!=labels[x]]),
   "candidate_pass":len(cases)-len(still_bad),"fixed":len(fixed),"regressions":regress,
   "still_incorrect":still_bad[:15],
   "status":"stress_passed" if not regress and fixed else "stress_failed",
   "live_bot_modified":False}

if __name__=="__main__":
 import sys
 if len(sys.argv)!=2:raise SystemExit("Provide a staged .diff path")
 original=proposer.BOT.read_text()
 diff=Path(sys.argv[1]).resolve()
 if proposer.STAGE.resolve() not in diff.parents or diff.suffix!=".diff":
  raise SystemExit("Invalid staged diff")
 candidate=sandbox.parse_diff(diff.read_text(),original)
 result=analyze(original,candidate)
 print(json.dumps(result,ensure_ascii=False))
 if result["status"]!="stress_passed":raise SystemExit(2)
