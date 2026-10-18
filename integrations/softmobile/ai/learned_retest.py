#!/usr/bin/env python3
"""Independent recurring audit of *deployed* pilot learning.

The AI judge never gets to deploy/approve code. It only records a second opinion
after deterministic checks with a no-network disposable Ruby container.
"""
import argparse
from datetime import datetime,timezone
import fcntl
import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError

import autonomous_learning as learner
import synthetic_lab as lab
from configurar_clave_groq import stored_key
from quality_auditor import _load,_atomic_json

DATA=Path(__file__).resolve().parent/"quality"
REPORT=DATA/"learned-dialogue-retest.json"
MAX_AI_JUDGMENTS=2

def failure_category(exc):
 """Safe, non-sensitive error classification for independent AI retests."""
 cause=getattr(exc,"__cause__",None)
 if isinstance(cause,HTTPError):
  return "provider_rate_limited" if cause.code==429 else "provider_http_error"
 if isinstance(exc,ValueError):return "judge_validation_rejected"
 if isinstance(exc,RuntimeError):
  return "provider_or_response_unavailable"
 return "local_evaluation_unavailable"

def report_status(report,use_ai):
 if report["deterministic_failed"]:return "needs_review"
 if report["checked"]==0:return "no_learned_rules"
 if not use_ai:return "deterministic_only_passed"
 if report["ai_flagged"]:return "ai_flagged_needs_review"
 if report["ai_confirmed"]<report["checked"]:return "deterministic_passed_ai_pending"
 return "deterministic_and_ai_passed"

def collect_rules(pack,issues):
 """Only complete synthetic evidence with the exact buyer utterance qualifies."""
 learner.validate_pack(pack)
 if not isinstance(issues,list):raise ValueError("Invalid issue store")
 results=[]
 for rule in pack["rules"]:
  issue=next((item for item in issues
              if isinstance(item,dict) and item.get("id")==rule["source_issue"]),None)
  if not issue:
   results.append((rule,None,"missing_original_issue"));continue
  try:
   scenario=lab.validate_cases({"scenarios":[issue["scenario"]]})[0]
   index=next(i for i,msg in enumerate(scenario["messages"])
              if learner.normalized(msg)==rule["trigger"])
   results.append((rule,scenario["messages"][:index+1],None))
  except (ValueError,KeyError,IndexError,StopIteration,TypeError):
   results.append((rule,None,"invalid_synthetic_evidence"))
 return results

def check_one(source,rule,messages,simulate=learner.trace_output):
 """Deterministic gates do not depend on any subjective judge score."""
 if not messages:return {"status":"no_replay_evidence"}
 try:
  result=simulate(source,messages)
 except (ValueError,RuntimeError,TypeError):
  return {"status":"isolated_replay_failed"}
 definition=learner.FAMILIES[rule["family"]]
 reply=result.get("reply","")
 if not isinstance(reply,str):reply=""
 from accessory_directness import expected_reply
 direct=expected_reply(source,rule)
 required_reply=direct if direct is not None else definition["reply"]
 safe=(result.get("tag")=="sm_learned_dialogue"
       and result.get("needs_human") is True
       and all(learner.normalized(x) in learner.normalized(reply)
               for x in definition["markers"])
       and reply==required_reply)
 return {"status":"deterministic_passed" if safe else "deterministic_failed",
         "pilot_only":True,
         "human_review":result.get("needs_human") is True,
         "tag":result.get("tag","")[:60]}

def evaluate(use_ai=False,judge=lab.api_json,simulate=learner.trace_output):
 source=learner.BOT.read_text()
 pack=learner.validate_pack(_load(learner.STORE,learner.empty_pack()))
 issues=_load(lab.ISSUES,[])
 report={"at":datetime.now(timezone.utc).isoformat(),
  "checked":0,"deterministic_passed":0,"deterministic_failed":0,
  "ai_calls_reserved":0,"ai_confirmed":0,"ai_flagged":0,
  "pilot_only":True,"real_customers_contacted":0,
  "public_messages_sent":0,"outcomes":[]}
 # Catches drift in an existing installed policy block before any AI access.
 if learner.compile_source(source,pack)!=source:
  report.update({"status":"source_policy_drift","deterministic_failed":len(pack["rules"])})
  return report
 for rule,messages,issue_error in collect_rules(pack,issues):
  row={"family":rule["family"],"source_issue":rule["source_issue"]}
  if issue_error:
   row["status"]=issue_error
  else:
   check=check_one(source,rule,messages,simulate=simulate)
   row.update(check)
  report["checked"]+=1
  if row["status"]=="deterministic_passed":
   report["deterministic_passed"]+=1
   if use_ai and report["ai_calls_reserved"]<MAX_AI_JUDGMENTS:
    state=_load(lab.STATE,lab.previous_state())
    try:
     key=stored_key()
     if key:
      # One short fictional buyer/bot pair; never full user history.
      reply=simulate(source,messages)["reply"]
      lab.reserve(state)
      report["ai_calls_reserved"]+=1
      obj=judge(key,lab.JUDGE_SYSTEM,json.dumps(
       {"category":"questions","dialogue":[{"buyer":messages[-1],
           "bot":reply}],"testing_mode":"learned_policy_independent_review"},
       ensure_ascii=False)[:2400],lab.JUDGE_SCHEMA,"learned_rule_retest")
      from interactive_lab import validate_grader_observation
      grade=validate_grader_observation(obj)
      row["judge_error"]=grade["error"]
      row["judge_reason"]=grade["reason"][:160]
      if grade["error"]:report["ai_flagged"]+=1
      else:report["ai_confirmed"]+=1
     else:row["judge_status"]="missing_provider_key"
    except (RuntimeError,ValueError,TypeError,OSError) as exc:
     row["judge_status"]=failure_category(exc)
    finally:
     _atomic_json(lab.STATE,state)
  else:report["deterministic_failed"]+=1
  report["outcomes"].append(row)
 report["status"]=report_status(report,use_ai)
 return report

def run(use_ai=False):
 DATA.mkdir(parents=True,exist_ok=True,mode=0o700)
 with open(lab.LOCK,"a+") as lock:
  os.fchmod(lock.fileno(),0o600)
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  result=evaluate(use_ai=use_ai)
  _atomic_json(REPORT,result)
  return result

def main():
 p=argparse.ArgumentParser()
 a=p.add_mutually_exclusive_group(required=True)
 a.add_argument("--run",action="store_true")
 a.add_argument("--offline",action="store_true")
 a.add_argument("--status",action="store_true")
 args=p.parse_args()
 if args.status:
  print(json.dumps(_load(REPORT,{"status":"not_run"}),ensure_ascii=False));return 0
 if args.run and os.environ.get("SOFTMOBILE_LEARNED_RETEST_ENABLED")!="true":
  print("learned_retest_not_enabled");return 2
 try:
  res=run(use_ai=args.run)
  print(json.dumps(res,ensure_ascii=False));return 0
 except BlockingIOError:
  print("learned_retest_skipped_busy");return 0
 except (OSError,ValueError,RuntimeError,TypeError,KeyError):
  print("learned_retest_failed_safely");return 2
if __name__=="__main__":sys.exit(main())
