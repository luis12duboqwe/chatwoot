#!/usr/bin/env python3
"""Isolated behavior tests for review-only Ruby patches.

Strict boundary: code under review runs ONLY in an ephemeral Docker container
without networking, filesystem mounts, writable rootfs, root identity, Linux
capabilities or access to Rails/Chatwoot credentials. No production Rails
runner, no host Ruby, no public WhatsApp traffic.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime,timezone

import patch_proposer as pp
from quality_auditor import _atomic_json

IMAGE="chatwoot/chatwoot:v4.18.0-ce"
REPORT_DIR=pp.DATA/"proposal-evaluations"
MARKER="SM_ISOLATED_CONTEXT_RESULTS="
SAFE_MARKERS=("'SM_MODE'","'test'")
RUN_LIMIT=60
SCENARIOS=[
 ("initial-model",["Busco un iPhone 15 de 128GB negro"],"128GB","Negro"),
 ("change-simple",["Busco iPhone 15 128 GB negro","Mejor el de 256GB azul"],"256GB","Azul"),
 ("fallback-first",["Busco iPhone 15 de 512GB negro","Si no hay 512GB negro, mejor 256GB azul"],"256GB","Azul"),
 ("fallback-second",["Busco iPhone 15 de 512GB negro","Si no hay 512GB negro, mejor 256GB azul","Si no hay 256GB azul, mejor 128GB rojo"],"128GB","Rojo"),
 ("buyer-real-1",["Hola, iPhone 15 de 128GB negro","Si no tienen 128GB negro, ¿puedo ver 256GB azul?"],"256GB","Azul"),
 ("buyer-real-2",["Quiero un iPhone 15 de 256GB azul","¿Y si no hay 256GB azul, puedo comprar 128GB rojo?"],"128GB","Rojo"),
 ("prefer-color-then-ask",["Busco iPhone 15 128GB","Prefiero negro, pero cuánto cuesta el azul"],"128GB","Negro"),
 ("prefer-color-and-photo",["Busco iPhone 15 de 128GB","Prefiero el azul; ¿tenés fotos del negro?"],"128GB","Azul"),
 ("prefer-first-or-second",["Busco iPhone 15 128GB","Prefiero negro o azul"],"128GB","Negro"),
 ("prefer-first-and-second",["Busco iPhone 15 256GB","Prefiero el negro y también miro el azul"],"256GB","Negro"),
 ("prefer-first-else-second",["Busco iPhone 15 256GB","Prefiero negro, si no hay negro me sirve azul"],"256GB","Azul"),
 ("prefer-blue-compare-black",["Busco iPhone 15 128GB","Prefiero azul, pero ¿qué precio tiene el negro?"],"128GB","Azul"),
 ("black-primary-blue-question",["Busco iPhone 15 256GB","Prefiero el negro; ¿el azul también viene de 256GB?"],"256GB","Negro"),
 ("two-model-compare",["Tengo iPhone 12 128GB negro, quiero Samsung S24 Ultra 256GB azul"],"256GB","Azul"),
 ("sequential-colors",["Busco Samsung S24 256GB negro","Mejor blanco","Ahora verde"],"256GB","Verde"),
 ("single-blue",["Busco Samsung S24 Ultra 256GB azul"],"256GB","Azul"),
 ("no-blue-black",["Busco iPhone 15 256GB","No quiero azul, prefiero negro"],"256GB","Negro"),
 ("generic-titanium",["iPhone 16 Pro 256GB titanio"],"256GB","Titanio"),
 ("gold",["iPhone 15 Pro 128GB dorado"],"128GB","Dorado"),
 ("no-color-choice",["Quiero iPhone 15 Pro 256GB"],"256GB",None),
 ("no-storage-choice",["Quiero iPhone 15 Pro negro"],None,"Negro"),
 ("change-capacity-no-color",["Busco iPhone 15 128GB negro","Mejor de 256GB"],"256GB","Negro"),
 ("capacity-alternative",["Busco iPhone 15 128GB negro","Si no hay 128GB, mejor 256GB"],"256GB","Negro"),
 ("alternative-and-budget",["Busco Samsung S24 de 128GB negro","Mejor el de 256GB azul"],"256GB","Azul"),
 ("city-kept",["Busco iPhone 15 de 128GB negro en Choloma","Mejor el de 256GB azul"],"256GB","Azul"),
 ("color-single-preferred",["Quiero iPhone 15 de 256GB en rojo"],"256GB","Rojo"),
 ("more-than-two-colors",["Busco iPhone 15 256GB","Si no hay azul, prefiero rojo, si no hay rojo, negro"],"256GB","Negro"),
 ("start-with-one-end-another",["Quiero iPhone 15 de 128GB","Mejor el de 512GB negro"],"512GB","Negro"),
 ("change-model-clear",["Busco iPhone 15 128GB negro","Mejor Samsung S24 Ultra 256GB azul"],"256GB","Azul"),
 ("conditional-blue-red-price",["Busco iPhone 15 256GB negro","Si no hay negro prefiero azul, ¿cuánto vale el rojo?"],"256GB","Azul")
]

def parse_diff(diff,original):
 if not isinstance(diff,str) or len(diff)>4500 or diff.count("@@")!=2:
  raise ValueError("Unexpected one-hunk diff")
 lines=diff.splitlines(keepends=True)
 if len(lines)<6 or lines[0]!="--- a/sales-bot-v2.rb\n" or lines[1]!="+++ b/sales-bot-v2.rb\n":
  raise ValueError("Unexpected patch headers")
 m=re.fullmatch(r"@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@.*\n",lines[2])
 if not m:raise ValueError("Malformed single hunk")
 old=[];new=[]
 for line in lines[3:]:
  if line.startswith("@@") or line.startswith("\\") or not line or line[0] not in ("+","-"," "):
   raise ValueError("Unsafe diff syntax")
  if line[0] in ("-"," "):old.append(line[1:])
  if line[0] in ("+"," "):new.append(line[1:])
 original_context="".join(old)
 replacement_context="".join(new)
 if not original_context or original_context==replacement_context:
  raise ValueError("Diff has no changes")
 _prefix,method,_suffix=pp.method_area(original)
 if method.count(original_context)!=1:raise ValueError("Diff not applicable in review method")
 proposal={"search":original_context,"replace":replacement_context,
   "reason":"Review only", "regression_example":"synthetic scenario"}
 # Diff context may be > original 8 line limit; enforce actual changed block instead.
 if len(old)>14 or len(new)>17:raise ValueError("Oversized hunk")
 if pp.DANGEROUS.search(replacement_context):raise ValueError("Forbidden code")
 candidate=original.replace(original_context,replacement_context,1)
 before,window,after=pp.method_area(candidate)
 if before!=pp.method_area(original)[0] or after!=pp.method_area(original)[2]:
  raise ValueError("Diff left method scope")
 if not pp.syntax_only(candidate):raise ValueError("Ruby syntax invalid")
 return candidate

def prepare_script(source,scenarios):
 if source.count("\nif ENV['SM_MODE']=='test'\n")!=1:
  raise ValueError("Missing test boundary")
 ruby=source.split("\nif ENV['SM_MODE']=='test'\n",1)[0]
 if "Message.where(" in ruby or "Conversation.find(" in ruby:
  raise ValueError("Chatwoot DB source must not run")
 cases=[{"id":name,"messages":messages} for name,messages,*_ in scenarios]
 payload=base64.b64encode(json.dumps(cases,ensure_ascii=False).encode()).decode()
 return "require 'base64'\n"+ruby+"\n"+f"""
rows=JSON.parse(Base64.strict_decode64('{payload}'))
results=rows.map do |row|
  c=SoftMobileSales.context_from(row.fetch('messages'))
  {{id:row.fetch('id'),capacity:c[:capacity],color:c[:color],
    model:c[:model],city:c[:city]}}
end
puts '{MARKER}'+JSON.generate(results)
"""

def isolated_run(source,scenarios,runner=subprocess.run):
 src=prepare_script(source,scenarios)
 cmd=["docker","run","-i","--rm","--pull","never","--network","none",
      "--read-only","--cap-drop","ALL","--security-opt","no-new-privileges",
      "--pids-limit","48","--memory","200m","--cpus","0.5",
      "--user","65534:65534","--tmpfs","/tmp:rw,noexec,nosuid,size=8m",
      "--env","HOME=/tmp","--entrypoint","ruby",IMAGE,"-"]
 try:
  p=runner(cmd,input=src,text=True,capture_output=True,timeout=RUN_LIMIT)
 except (OSError,subprocess.TimeoutExpired) as e:
  raise RuntimeError("Sandbox runner unavailable") from e
 if p.returncode:
  raise RuntimeError("Sandbox Ruby evaluation failed")
 match=[line[len(MARKER):] for line in p.stdout.splitlines() if line.startswith(MARKER)]
 if len(match)!=1:raise RuntimeError("Sandbox output missing")
 result=json.loads(match[0])
 if not isinstance(result,list) or len(result)!=len(scenarios):
  raise RuntimeError("Incomplete sandbox result")
 return result

def grade(actual):
 # Full protocol includes exact desired capacity/color. Any candidate regression
 # is a rejection even when the original variant also had errors.
 expected={name:{"capacity":cap,"color":color} for name,_,cap,color in SCENARIOS}
 return {item["id"]:{key:item.get(key)==value for key,value in expected[item["id"]].items()}
         for item in actual}

def compare(original,candidate,runner=subprocess.run):
 old=isolated_run(original,SCENARIOS,runner)
 new=isolated_run(candidate,SCENARIOS,runner)
 by_old={r["id"]:r for r in old}
 by_new={r["id"]:r for r in new}
 old_marks=grade(old);new_marks=grade(new)
 old_score=sum(all(v.values()) for v in old_marks.values())
 new_score=sum(all(v.values()) for v in new_marks.values())
 regress=[];fixes=[];both_incorrect=[]
 for name in old_marks:
  before=all(old_marks[name].values())
  after=all(new_marks[name].values())
  if before and not after:regress.append(name)
  elif not before and after:fixes.append(name)
  elif not before and not after:both_incorrect.append(name)
 diffs=[name for name in by_old if (by_old[name]["color"],by_old[name]["capacity"])!=(by_new[name]["color"],by_new[name]["capacity"])]
 return {"scenarios":len(SCENARIOS),"baseline_pass":old_score,
    "candidate_pass":new_score,"fixed":fixes,"regressed":regress,
    "both_incorrect":both_incorrect,"changed":diffs,
    "status":"behavior_passed" if fixes and not regress and new_score>old_score else "rejected_regression_or_no_improvement",
    "live_bot_modified":False,"client_messages_sent":0}

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--proposal",required=True)
 args=ap.parse_args()
 diff_path=Path(args.proposal).resolve()
 if pp.STAGE.resolve() not in diff_path.parents or diff_path.suffix!=".diff":
  raise SystemExit("Source path must be a locally staged inert patch")
 orig=pp.BOT.read_text()
 try:
  candidate=parse_diff(diff_path.read_text(),orig)
  result=compare(orig,candidate)
 except (ValueError,RuntimeError) as e:
  result={"status":"blocked_before_or_during_sandbox","reason":str(e)[:180],
          "live_bot_modified":False,"client_messages_sent":0}
 if result.get("status")=="behavior_passed":
  from sandbox_stress import analyze
  stress=analyze(orig,candidate)
  result["independent_stress"]=stress
  if stress.get("status")!="stress_passed":
   result["status"]="rejected_independent_stress"
  else:
   from isolated_gate import gates
   checks=gates(candidate)
   result["ruby_regression_gate"]=checks
   result["status"]="review_ready" if checks.get("status")=="passed" else "rejected_ruby_regression"
 result.update({"at":datetime.now(timezone.utc).isoformat(),
   "proposal_file":diff_path.name,"base_sha256":hashlib.sha256(orig.encode()).hexdigest()})
 REPORT_DIR.mkdir(parents=True,exist_ok=True,mode=0o700)
 _atomic_json(REPORT_DIR/(diff_path.stem+".json"),result)
 print(json.dumps(result,ensure_ascii=False))
 return 0 if result["status"]=="review_ready" else 2

if __name__=="__main__":
 sys.exit(main())
