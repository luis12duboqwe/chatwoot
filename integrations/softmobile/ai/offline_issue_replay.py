#!/usr/bin/env python3
"""Fast no-network replay of previously stored, *fictional* quality flags.

No Groq calls, public messages, Chatwoot/WAHA writes, production inventory,
or direct deploys. The result says "still has a deterministic flag", NOT
"proven business defect". LLM-only suspicion must remain unverified.
"""
import argparse,base64,hashlib,json,subprocess
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path

import synthetic_lab as lab
import issue_triage as triage
from inventory_quality_lab import grouped
from sandbox_review import IMAGE
from quality_auditor import _load,_atomic_json

ROOT=Path(__file__).resolve().parent
RESULT=ROOT/"quality"/"offline-issue-replay-report.json"
MAX_ITEMS=250
MAX_BATCH=20
MARK="SM_OFFLINE_REPLAY="
VALID_CLASSES={"convergent_signals_pending_replay","deterministic_signal_pending_replay",
 "ai_only_unverified","deployed_needs_retest","cleared_ai_needs_deterministic_review",
 "not_enough_evidence"}
BASELINE_FIELDS={"id","classification","old_flags","new_flags","outcome","bot_reply_changes"}

def isolated_replay(items,source=None,runner=subprocess.run):
 """Execute the exact Ruby response planner in a disposable NO NETWORK runner."""
 if not isinstance(items,list) or not 1<=len(items)<=MAX_BATCH:
  raise ValueError("Invalid offline replay batch")
 for item in items:
  if set(item)!={"id","scenario"} or not isinstance(item["id"],str):
   raise ValueError("Unexpected source fields")
  lab.validate_cases({"scenarios":[item["scenario"]]})
 live=lab.BOT.read_text() if source is None else source
 core=live.split("\nif ENV['SM_MODE']=='test'\n",1)[0]
 serial=base64.b64encode(json.dumps(items,ensure_ascii=False).encode()).decode()
 script="require 'json'\nrequire 'base64'\n"+core+f"""
rows=JSON.parse(Base64.strict_decode64('{serial}'))
raise 'too many rows' if rows.length>{MAX_BATCH}
results=rows.map do |row|
  history=[]
  prev=nil
  turns=row.fetch('scenario').fetch('messages').map do |msg|
    history << msg
    decision=SoftMobileSales.plan(msg,SoftMobileSales.context_from(history),[],prev)
    reply=decision[:reply].to_s[0,520]
    prev=reply unless reply.empty?
    {{buyer:msg,bot:reply,intent:decision[:intent].to_s,human:!!decision[:needs_human]}}
  end
  {{id:row.fetch('id'),category:row.fetch('scenario').fetch('category'),turns:turns}}
end
puts '{MARK}'+JSON.generate(results)
"""
 cmd=["docker","run","--rm","-i","--pull","never","--network","none","--read-only",
     "--cap-drop","ALL","--security-opt","no-new-privileges","--pids-limit","48",
     "--memory","200m","--cpus","0.5","--user","65534:65534",
     "--tmpfs","/tmp:rw,noexec,nosuid,size=8m","--env","HOME=/tmp",
     "--entrypoint","ruby",IMAGE,"-"]
 try:
  p=runner(cmd,input=script,text=True,capture_output=True,timeout=70)
 except (OSError,subprocess.TimeoutExpired) as exc:
  raise RuntimeError("Isolated Ruby replay failed") from exc
 if p.returncode:
  raise RuntimeError("Isolated Ruby planner failed")
 lines=[json.loads(x[len(MARK):]) for x in p.stdout.splitlines() if x.startswith(MARK)]
 if len(lines)!=1 or len(lines[0])!=len(items):
  raise RuntimeError("Isolated Ruby replay count mismatch")
 return lines[0]

def classify_replay(issue,replayed):
 old=issue.get("static_flags") or []
 fresh=lab.static_flags(replayed)
 old_set=set(old)
 fresh_set=set(fresh)
 if not old_set and not fresh_set:
  state="ai_only_still_unverified"
 elif old_set and old_set.isdisjoint(fresh_set):
  state="previous_flags_no_longer_present"
 elif old_set.intersection(fresh_set):
  state="previous_flags_reproduced"
 else:
  state="new_deterministic_flags"
 evidence=issue.get("evidence") or []
 rows=replayed["turns"]
 return {"id":issue["id"],"classification":triage.bucket(issue),
         "old_flags":sorted(old_set),"new_flags":sorted(fresh_set),
         "outcome":state,"bot_reply_changes":sum(
          str(x.get("bot"))!=str(y.get("bot"))
          for x,y in zip(evidence,rows))}

def assess(issues=None,source=None,runner=isolated_replay):
 all_issues=issues if issues is not None else _load(triage.ISSUES,[])
 if not isinstance(all_issues,list):raise ValueError("Unexpected issues JSON")
 selected=[]
 skipped=Counter()
 for issue in all_issues:
  kind=triage.bucket(issue)
  if kind not in VALID_CLASSES:
   skipped[kind]+=1;continue
  if len(selected)>=MAX_ITEMS:
   skipped["over_max_items"]+=1;continue
  try:clean=lab.validate_cases({"scenarios":[issue["scenario"]]})[0]
  except (ValueError,TypeError,KeyError):
   skipped["invalid_scenario"]+=1;continue
  if not isinstance(issue.get("id"),str) or not isinstance(issue.get("evidence"),list):
   skipped["invalid_evidence"]+=1;continue
  selected.append((issue,clean))
 records=[]
 for page in grouped(selected,MAX_BATCH):
  chosen=[{"id":row[0]["id"],"scenario":row[1]} for row in page]
  observed=runner(chosen,source=source)
  if len(observed)!=len(page):raise RuntimeError("Batch mismatch")
  for (original,scenario),row in zip(page,observed):
   if row.get("id")!=original["id"] or len(row.get("turns",[]))!=len(scenario["messages"]):
    raise RuntimeError("Mismatched Ruby replay")
   records.append(classify_replay(original,row))
 outcomes=Counter(x["outcome"] for x in records)
 return {"at":datetime.now(timezone.utc).isoformat(),
  "environment":"NO_NETWORK_SYNTHETIC_ONLY","replayed":len(records),
  "total_seen":len(all_issues),"skipped":dict(skipped),
  "outcomes":dict(outcomes),"per_class":dict(Counter(x["classification"] for x in records)),
  "ruby_sha256":hashlib.sha256((source if source is not None else lab.BOT.read_text()).encode()).hexdigest(),
  "api_calls":0,"public_messages_sent":0,"real_inventory_changed":False,
  "no_auto_promotion":True,
  "examples":[x for x in records if x["outcome"] in ("previous_flags_reproduced","new_deterministic_flags")][:25],
  "results":records}

def compare(current,candidate):
 """Deterministic deltas, not proof of real-world defects."""
 a={x["id"]:x for x in current.get("results",[])}
 b={x["id"]:x for x in candidate.get("results",[])}
 if set(a)!=set(b):raise ValueError("Cannot compare different fictional case sets")
 added=[];removed=[];changed=[]
 for case_id in sorted(a):
  before=set(a[case_id]["new_flags"]);after=set(b[case_id]["new_flags"])
  if after-before:added.append({"id":case_id,"flags":sorted(after-before)})
  if before-after:removed.append({"id":case_id,"flags":sorted(before-after)})
  if after!=before:changed.append(case_id)
 return {"cases_compared":len(a),"new_flags_in_candidate":len(added),
         "cleared_flags_in_candidate":len(removed),"changed_cases":len(changed),
         "new_flag_details":added[:30],"cleared_flag_details":removed[:30],
         "candidate_requires_review":bool(added),
         "note":"Static quality signals are hypotheses; not independently verified bugs."}

def run(compare_staged=True):
 r=assess()
 if compare_staged:
  review=_load(ROOT/"quality"/"combined-pilot-review.json",{})
  if review.get("status")=="verified_staged" and isinstance(review.get("stage_file"),str):
   from pathlib import Path
   stage=ROOT/"quality"/"combined-pilot-candidates"/review["stage_file"]
   if stage.is_file():
    source=stage.read_text()
    sha=hashlib.sha256(source.encode()).hexdigest()
    if sha==review.get("candidate_sha256"):
     candidate=assess(source=source)
     r["candidate_sha256"]=sha
     r["differential"]=compare(r,candidate)
 _atomic_json(RESULT,r)
 return r

def main():
 p=argparse.ArgumentParser()
 a=p.add_mutually_exclusive_group(required=True)
 a.add_argument("--run",action="store_true")
 a.add_argument("--status",action="store_true")
 v=p.parse_args()
 if v.status:
  print(json.dumps(_load(RESULT,{"status":"not_run"}),ensure_ascii=False));return 0
 r=run()
 print(json.dumps({k:v for k,v in r.items() if k not in ("examples","results")},ensure_ascii=False))
 return 0

if __name__=="__main__":raise SystemExit(main())
