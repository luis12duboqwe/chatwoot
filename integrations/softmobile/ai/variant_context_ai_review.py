#!/usr/bin/env python3
"""Independent Groq second opinion for two corrected synthetic buyer preferences.

Review-only; a positive verdict never deploys or approves payments.
"""
import json,fcntl
from pathlib import Path
from datetime import datetime,timezone
from quality_auditor import _load,_atomic_json
from configurar_clave_groq import stored_key
from interactive_lab import validate_grader_observation
from provider_cooldown import state_at
import synthetic_lab as lab
import offline_issue_replay as replay
import variant_context_candidate as patch

QA=Path(__file__).resolve().parent/"quality"
REPORT=QA/"variant-context-ai-review.json"
REVIEWED=("color-black-to-blue","capacity-64-vs-128")

def evaluate(api=lab.api_json,key=None):
 approved=_load(QA/"variant-context-full-review.json",{})
 result={"at":datetime.now(timezone.utc).isoformat(),
  "candidate_sha256":approved.get("candidate_sha256"),
  "status":"unavailable","ai_approved":False,"ai_calls":0,
  "public_messages_sent":0,"deployed":False,"judgments":[]}
 if approved.get("status")!="review_ready_needs_independent_ai":
  result["status"]="candidate_not_fully_validated";return result
 stage=_load(patch.REPORT,{})
 if stage.get("candidate_sha256")!=result["candidate_sha256"]:
  result["status"]="candidate_hash_mismatch";return result
 if not isinstance(stage.get("stage_file"),str):
  result["status"]="candidate_path_missing";return result
 path=patch.STAGE/stage["stage_file"]
 if not path.is_file():
  result["status"]="candidate_file_missing";return result
 source=path.read_text()
 import hashlib
 if hashlib.sha256(source.encode()).hexdigest()!=result["candidate_sha256"]:
  result["status"]="candidate_source_tampered";return result
 prior=_load(REPORT,{})
 if prior.get("candidate_sha256")==result["candidate_sha256"]:
  for item in prior.get("judgments",[]):
   if not isinstance(item,dict) or item.get("case") not in REVIEWED:
    continue
   try:
    when=datetime.fromisoformat(item.get("reviewed_at",prior.get("at","")))
    seconds=(datetime.now(timezone.utc)-when.astimezone(timezone.utc)).total_seconds()
    if when.tzinfo and 0<=seconds<=86400 and isinstance(item.get("error"),bool):
     result["judgments"].append(dict(item,reviewed_at=when.isoformat()))
   except (TypeError,ValueError):pass
 if any(row["error"] for row in result["judgments"]):
  result["status"]="ai_flagged_needs_revision";return result
 if len({row["case"] for row in result["judgments"]})==len(REVIEWED):
  result["status"]="ai_approved_for_review";result["ai_approved"]=True;return result
 if state_at()>0:
  result["status"]="provider_cooldown";return result
 if not key:key=stored_key()
 if not key:
  result["status"]="missing_key";return result
 selected=[row for row in __import__("context_accuracy_lab").CASES if row[0] in REVIEWED]
 state=_load(lab.STATE,lab.previous_state())
 for case_id,messages,expected in selected:
  if any(row["case"]==case_id for row in result["judgments"]):continue
  fixture={"id":case_id,"scenario":{"category":"changes",
            "messages":(["Hola","Busco un iPhone 15"]+messages)[-3:]}}
  rows=replay.isolated_replay([fixture],source=source)
  if len(rows)!=1:raise RuntimeError("No replay")
  lab.reserve(state)
  result["ai_calls"]+=1
  try:
   raw=api(key,lab.JUDGE_SYSTEM,json.dumps({
      "category":"changes","dialogue":rows[0]["turns"],
      "testing_mode":"fictional_context_fix_independent_review"},
      ensure_ascii=False),lab.JUDGE_SCHEMA,"context_preference_quality")
   grade=validate_grader_observation(raw)
   result["judgments"].append({"case":case_id,"error":grade["error"],
    "reason":grade["reason"][:220],"reviewed_at":datetime.now(timezone.utc).isoformat()})
  except (RuntimeError,TypeError,ValueError,OSError):
   result["status"]="provider_or_grade_unavailable";return result
  finally:
   _atomic_json(lab.STATE,state)
 result["ai_approved"]=len(result["judgments"])==2 and all(not v["error"] for v in result["judgments"])
 result["status"]="ai_approved_for_review" if result["ai_approved"] else "ai_flagged_needs_revision"
 return result

def run():
 with open(lab.LOCK,"a+") as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  previous=_load(REPORT,{})
  stage=_load(QA/"variant-context-full-review.json",{})
  if (previous.get("status")=="ai_approved_for_review"
      and previous.get("candidate_sha256")==stage.get("candidate_sha256")
      and stage.get("status")=="review_ready_needs_independent_ai"):
   try:
    at=datetime.fromisoformat(previous["at"])
    if at.tzinfo and 0<=(datetime.now(timezone.utc)-at.astimezone(timezone.utc)).total_seconds()<=86400:
     return previous
   except (KeyError,ValueError,TypeError):
    pass
  result=evaluate()
  _atomic_json(REPORT,result)
  return result

if __name__=="__main__":
 print(json.dumps(run(),ensure_ascii=False))
