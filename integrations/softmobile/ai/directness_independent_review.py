#!/usr/bin/env python3
"""Independent reviewer for a static pilot-accessory clarification.

Only a *fresh* Groq verdict of no error on an isolated fictional dialogue,
plus exact pinned candidate/source hashes, can unblock the bundled promoter.
Provider limits or inconclusive verdicts never grant approval. No clients.
"""
import argparse,fcntl,json,os,sys
from datetime import datetime,timezone
from pathlib import Path

import autonomous_learning as learner
import accessory_directness as accessory
import combined_pilot_promotion as bundle
import synthetic_lab as lab
from configurar_clave_groq import stored_key
from interactive_lab import validate_grader_observation
from quality_auditor import _load,_atomic_json
from provider_cooldown import state_at

REPORT=bundle.QA/"directness-independent-review.json"
QUESTION="Me preocupa que el precio no incluya la funda, ¿puedo agregarla sin costo adicional?"
HISTORY=["Busco un celular que me guste",QUESTION]
MIN_REPLY_MARKERS=("no puedo incluirte","sin costo","asesor","regalía","precio")

def review(judge=lab.api_json,key=None):
 now=datetime.now(timezone.utc).isoformat()
 out={"at":now,"status":"review_pending",
      "revision":bundle.REVISION,"candidate_sha256":None,
      "judge_error":None,"provider_calls_reserved":0,
      "public_messages_sent":0,"real_stock_modified":False}
 staged=_load(bundle.REVIEW,{})
 if staged.get("status")!="verified_staged" or staged.get("revision")!=bundle.REVISION:
  out["status"]="candidate_not_preverified";return out
 if staged.get("baseline_sha256")!=bundle.digest(learner.BOT.read_text()):
  out["status"]="source_changed";return out
 try:
  candidate=bundle.prepare(learner.BOT.read_text(),
    learner.validate_pack(_load(learner.STORE,learner.empty_pack())))
 except (ValueError,TypeError,RuntimeError,KeyError):
  out["status"]="fixed_candidate_build_rejected";return out
 if bundle.digest(candidate)!=staged.get("candidate_sha256"):
  out["status"]="staged_source_changed";return out
 out["candidate_sha256"]=bundle.digest(candidate)
 try:
  result=learner.trace_output(candidate,HISTORY)
 except (RuntimeError,ValueError,TypeError):
  out["status"]="candidate_replay_failed";return out
 answer=result.get("reply","")
 if (answer!=accessory.REPLY or result.get("needs_human") is not True
     or result.get("tag")!="sm_learned_dialogue"
     or not all(m in answer.casefold() for m in MIN_REPLY_MARKERS)):
  out["status"]="objective_criteria_failed";return out
 if state_at()>0:
  out["status"]="groq_provider_cooldown";return out
 if not key:key=stored_key()
 if not key:
  out["status"]="missing_groq_key";return out
 state=_load(lab.STATE,lab.previous_state())
 try:
  lab.reserve(state)
  out["provider_calls_reserved"]=1
  raw=judge(key,lab.JUDGE_SYSTEM,json.dumps(
      {"category":"questions",
       "dialogue":[{"buyer":HISTORY[0],"bot":"Entendido, ¿qué modelo buscás?"},
                   {"buyer":QUESTION,"bot":answer}],
       "testing_mode":"fictional_independent_commercial_quality_review"},
       ensure_ascii=False),lab.JUDGE_SCHEMA,"accessory_directness_independent")
  grade=validate_grader_observation(raw)
  out["judge_error"]=grade["error"]
  out["judge_category"]=grade["category"]
  out["judge_reason"]=grade["reason"][:230]
  out["status"]="independent_ai_flagged_needs_review" if grade["error"] else "independent_ai_approved"
 except (RuntimeError,ValueError,TypeError,OSError):
  out["status"]="provider_or_grade_unavailable"
 finally:
  _atomic_json(lab.STATE,state)
 return out

def run(judge=lab.api_json,key=None):
 bundle.QA.mkdir(parents=True,exist_ok=True,mode=0o700)
 with open(lab.LOCK,"a+") as lock:
  os.fchmod(lock.fileno(),0o600)
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  data=review(judge,key)
  _atomic_json(REPORT,data)
  return data

def main():
 p=argparse.ArgumentParser()
 a=p.add_mutually_exclusive_group(required=True)
 a.add_argument("--run",action="store_true")
 a.add_argument("--status",action="store_true")
 args=p.parse_args()
 if args.status:
  print(json.dumps(_load(REPORT,{"status":"not_run"}),ensure_ascii=False))
  return 0
 if os.environ.get("SOFTMOBILE_DIRECTNESS_AI_REVIEW_ENABLED")!="true":
  print("review_disabled");return 2
 prior=_load(REPORT,{})
 if prior.get("status")=="independent_ai_approved" and prior.get("candidate_sha256"):
  if bundle.independent_quality_approved(prior["candidate_sha256"]):
   print("independent_ai_approval_still_fresh");return 0
 try:
  result=run()
  print(json.dumps(result,ensure_ascii=False))
  return 0 if result["status"] in (
       "independent_ai_approved","independent_ai_flagged_needs_review",
       "groq_provider_cooldown","provider_or_grade_unavailable",
       "candidate_not_preverified") else 2
 except BlockingIOError:
  print("synthetic_lab_busy");return 0
 except (OSError,ValueError,TypeError,RuntimeError):
  print("review_failed_closed");return 2
if __name__=="__main__":sys.exit(main())
