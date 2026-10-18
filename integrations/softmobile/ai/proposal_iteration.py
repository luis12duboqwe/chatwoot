#!/usr/bin/env python3
"""Bounded iterative feedback for inert Groq Ruby proposals.

Each new attempt sees validation outcomes only, never credentials or real
customers. The model cannot approve, install or publish a patch.
"""
import hashlib
import json
from datetime import datetime,timezone
import synthetic_lab as lab

MAX_PER_CYCLE=2
GENERIC_ADVICE={
 "static_rejected":"JSON patch failed method boundary, line cap, or allowlist checks. Replace only the exact supplied block with Ruby syntax.",
 "syntax_rejected":"Ruby syntax validation failed. Return correctly balanced Ruby if/end blocks and preserve line endings.",
 "behavior_rejected":"Thirty deterministic Ruby conversations showed no net improvement or new regressions. Distinguish chosen from rejected/comparison variants.",
 "stress_rejected":"The patch regressed at least one of 150 independent color/capacity variants. Preserve previously correct results.",
 "regression_rejected":"The full commercial Ruby suite failed. Preserve all behavior outside the color-selection purpose.",
 "duplicate_candidate":"Your patch exactly repeats a rejected prior attempt. Produce different effective logic."
}

def feedback_message(states):
 if not isinstance(states,list):raise ValueError("Invalid retry states")
 return [{"attempt":i+1,"outcome":status,"advice":GENERIC_ADVICE[status]}
   for i,status in enumerate(states) if status in GENERIC_ADVICE][-MAX_PER_CYCLE:]

def attempt_sequence(issue,source,method,api,key,state,prior_attempts=0,
                     max_attempts=MAX_PER_CYCLE,checks=None):
 """Return safe result and attempt metadata; injected checks are only for offline tests."""
 import patch_proposer as pp
 if checks is None:
  from sandbox_review import compare
  from sandbox_stress import analyze
  from isolated_gate import gates
  checks={"syntax":pp.syntax_only,"compare":compare,"stress":analyze,
   "gates":gates,"stage":pp.stage}
 if not (1<=max_attempts<=MAX_PER_CYCLE):raise ValueError("Invalid attempt ceiling")
 if not key:return {"status":"api_unavailable","attempts":[]}
 failed=[];records=[];seen=set()
 outcome={"status":"no_candidate_passed_validation","issue_id":issue["id"]}
 for idx in range(max_attempts):
  is_today=state.get("day")==datetime.now(timezone.utc).date().isoformat()
  if prior_attempts+len(records)>=pp.MAX_DAILY or (is_today and state.get("api_calls",0)>=lab.MAX_DAILY):
   outcome={"status":"shared_daily_cap","issue_id":issue["id"]}
   break
  prompt={"fictional_dialogue":[{"buyer":x.get("buyer","")[:155],
      "bot":x.get("bot","")[:230]} for x in issue["evidence"]],
    "source_method":method,"replace_only_this_exact_block":pp.COLOR_ANCHOR,
    "previous_rejection_feedback":feedback_message(failed),
    "request":"Supply a minimal text replacement of this Ruby block. Never change payments, price, stock or safety scope."}
  lab.reserve(state)
  try:
   proposal=api(key,pp.SYSTEM,json.dumps(prompt,ensure_ascii=False)[:8500],
      pp.SCHEMA,"ruby_patch_proposal")
  except (RuntimeError,ValueError,TypeError):
   records.append({"outcome":"api_unavailable","proposal_hash":None})
   outcome={"status":"api_unavailable","issue_id":issue["id"]}
   break
  record={"outcome":None,"proposal_hash":None}
  try:
   if not isinstance(proposal,dict) or set(proposal)!=set(pp.SCHEMA["required"]):
    raise ValueError("Invalid schema")
   if method.count(pp.COLOR_ANCHOR)!=1:raise ValueError("Trusted anchor drift")
   accepted=dict(proposal,search=pp.COLOR_ANCHOR)
   candidate=pp.validate_patch(source,accepted)
   digest=hashlib.sha256(candidate.encode()).hexdigest()[:16]
   record["proposal_hash"]=digest
   if digest in seen:record["outcome"]="duplicate_candidate"
   else:
    seen.add(digest)
    if not checks["syntax"](candidate):record["outcome"]="syntax_rejected"
    else:
     behavior=checks["compare"](source,candidate)
     if behavior.get("status")!="behavior_passed":record["outcome"]="behavior_rejected"
     else:
      stress=checks["stress"](source,candidate)
      if stress.get("status")!="stress_passed":record["outcome"]="stress_rejected"
      else:
       regression=checks["gates"](candidate)
       if regression.get("status")!="passed":record["outcome"]="regression_rejected"
       else:
        artifact=checks["stage"](source,candidate,accepted,issue)
        artifact.update({"status":"isolated_behavior_passed_human_review_required",
          "sandbox_behavior":behavior,"sandbox_independent_stress":stress,
          "sandbox_ruby_suite":regression,"model_code_executed":True,
          "model_code_execution_environment":"isolated network-disabled disposable container only",
          "automatic_deployment_allowed":False,"independent_human_review_required":True})
        pp._atomic_json(pp.STAGE/(artifact["proposal_id"]+".json"),artifact)
        outcome={"status":"review_ready_not_deployed","issue_id":issue["id"],
          "proposal_id":artifact["proposal_id"],"passed_ruby":regression["total"],
          "automatic_deployment_allowed":False}
        record["outcome"]="review_ready_not_deployed"
  except (ValueError,TypeError):
   record["outcome"]="static_rejected"
  records.append(record)
  if record["outcome"]=="review_ready_not_deployed":break
  failed.append(record["outcome"])
 outcome["attempts"]=[{"attempt":i+1,**x} for i,x in enumerate(records)]
 outcome["api_calls_reserved"]=len(records)
 outcome["bot_modified"]=False
 return outcome
