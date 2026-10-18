#!/usr/bin/env python3
"""Safely finish independent AI judgments on already simulated fictional chats.

Does NOT regenerate buyer messages, send public messages, alter real stock,
execute suggested text, or deploy code. A failed Groq call leaves the case
pending with temporary backoff. Only validated synthetic transcripts qualify.
"""
import argparse,fcntl,hashlib,json,os,sys
from datetime import datetime,timezone,timedelta
from pathlib import Path

import synthetic_lab as lab
import interactive_lab as interactive
from configurar_clave_groq import stored_key
from provider_cooldown import state_at
from quality_auditor import _load,_atomic_json

ROOT=Path(__file__).resolve().parent
REPORT=ROOT/"quality"/"deferred-grading-report.json"
MAX_PER_RUN=2
MAX_REPLY_LENGTH=520
RETRY_MINUTES=30

def eligible(row,now=None):
 now=now or datetime.now(timezone.utc)
 if not isinstance(row,dict) or row.get("source")!="interactive_step_by_step_groq":
  return False
 if row.get("grade") is not None:return False
 if row.get("status") not in ("synthetic_ungraded","synthetic_unverified"):
  return False
 retry=row.get("next_grading_after")
 if retry:
  if not isinstance(retry,str):return False
  try:
   at=datetime.fromisoformat(retry)
   if at.tzinfo is None or at.astimezone(timezone.utc)>now:return False
  except (ValueError,TypeError):return False
 try:
  scenario=lab.validate_cases({"scenarios":[row["scenario"]]})[0]
  digest=hashlib.sha256(json.dumps(scenario,ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:18]
  if row.get("id")!=digest:return False
  turns=row["evidence"]
  if not isinstance(turns,list) or len(turns)!=len(scenario["messages"]):
   return False
  for turn,msg in zip(turns,scenario["messages"]):
   if not isinstance(turn,dict) or turn.get("buyer")!=msg:return False
   if not isinstance(turn.get("bot"),str) or len(turn["bot"])>MAX_REPLY_LENGTH:return False
  return True
 except (ValueError,KeyError,TypeError):
  return False

def backlog(rows):
 if not isinstance(rows,list):raise ValueError("Malformed transcript store")
 return sum(isinstance(x,dict) and x.get("source")=="interactive_step_by_step_groq"
            and x.get("grade") is None for x in rows)

def evaluate(rows,issues,state,api=lab.api_json,key=None,now=None):
 now=now or datetime.now(timezone.utc)
 if not isinstance(rows,list) or not isinstance(issues,list) or not isinstance(state,dict):
  raise ValueError("Corrupt grading stores")
 output={"at":now.isoformat(),"status":"no_due_items","considered":0,
   "approved_no_issue":0,"flagged_for_review":0,"provider_unavailable":0,
   "invalid_or_delayed":0,"api_calls_reserved":0,"left_ungraded":0,
   "public_messages_sent":0,"production_inventory_touched":False,
   "code_deployments":0}
 source=[x for x in rows if isinstance(x,dict) and x.get("source")=="interactive_step_by_step_groq"
         and x.get("grade") is None]
 chosen=[x for x in source if eligible(x,now)][:MAX_PER_RUN]
 output["invalid_or_delayed"]=len(source)-len([x for x in source if eligible(x,now)])
 if not chosen:
  output["left_ungraded"]=backlog(rows)
  return output
 if state_at(now)>0:
  output["status"]="provider_cooldown"
  output["left_ungraded"]=backlog(rows)
  return output
 if not key:key=stored_key()
 if not key:
  output["status"]="missing_api_key"
  output["left_ungraded"]=backlog(rows)
  return output
 for row in chosen:
  if state_at(now)>0:break
  output["considered"]+=1
  # Reserve FIRST using the same shared, provider-aware Groq budget.
  lab.reserve(state)
  output["api_calls_reserved"]+=1
  try:
   obj=api(key,lab.JUDGE_SYSTEM,json.dumps({
      "category":row["category"],"dialogue":row["evidence"],
      "testing_mode":"previously_ungraded_fictional_conversation"},
      ensure_ascii=False)[:7500],lab.JUDGE_SCHEMA,"deferred_independent_grade")
   grade=interactive.validate_grader_observation(obj)
   row["grade"]=grade
   row["graded_at"]=now.isoformat()
   row.pop("next_grading_after",None)
   row["status"]="synthetic_unverified" if grade["error"] or row.get("static_flags") else "synthetic_no_issue_observed"
   if grade["error"]:
    output["flagged_for_review"]+=1
    match=next((x for x in issues if isinstance(x,dict) and x.get("id")==row["id"]),None)
    if match is None:
     issues.append({k:row[k] for k in ("id","at","source","category","scenario","evidence","grade","static_flags","status")})
     issues[-1]["eligible_for_unreviewed_code_change"]=False
    elif match.get("grade") is None:
     match["grade"]=grade
   else:
    output["approved_no_issue"]+=1
  except (RuntimeError,ValueError,TypeError,OSError):
   output["provider_unavailable"]+=1
   count=min(4,int(row.get("grading_retries",0))+1)
   row["grading_retries"]=count
   row["next_grading_after"]=(now+timedelta(minutes=RETRY_MINUTES*(2**(count-1)))).isoformat()
 output["left_ungraded"]=backlog(rows)
 output["status"]="completed" if not output["provider_unavailable"] else "partial_provider_failure"
 return output

def run(api=lab.api_json,key=None):
 with open(lab.LOCK,"a+") as lock:
  os.fchmod(lock.fileno(),0o600)
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  rows=_load(interactive.TRANSCRIPTS,[])
  issues=_load(lab.ISSUES,[])
  state=_load(lab.STATE,lab.previous_state())
  result=evaluate(rows,issues,state,api,key)
  _atomic_json(interactive.TRANSCRIPTS,rows[-interactive.MAX_STORED:])
  _atomic_json(lab.ISSUES,issues[-lab.MAX_ISSUES:])
  _atomic_json(lab.STATE,state)
  _atomic_json(REPORT,result)
  return result

def main():
 p=argparse.ArgumentParser()
 mode=p.add_mutually_exclusive_group(required=True)
 mode.add_argument("--run",action="store_true")
 mode.add_argument("--status",action="store_true")
 a=p.parse_args()
 if a.status:
  print(json.dumps(_load(REPORT,{"status":"not_run"}),ensure_ascii=False));return 0
 if os.environ.get("SOFTMOBILE_DEFERRED_GRADING_ENABLED")!="true":
  print("grading_disabled");return 2
 try:
  r=run()
  print(json.dumps(r,ensure_ascii=False))
  return 0
 except BlockingIOError:
  print("synthetic_lab_busy");return 0
 except (RuntimeError,ValueError,TypeError,OSError,KeyError):
  print("deferred_grading_failed_closed");return 2
if __name__=="__main__":sys.exit(main())
