#!/usr/bin/env python3
"""Reproducible, privacy-preserving prioritization of fictional lab findings.

This is a READ-ONLY analysis of the source issue store. AI-only diagnosis is
not counted as a proven defect. The report never modifies issue statuses.
"""
from collections import Counter,defaultdict
from datetime import datetime,timezone
import hashlib
import json
import re
from pathlib import Path

import synthetic_lab as lab
from quality_auditor import _load,_atomic_json

ROOT=Path(__file__).resolve().parent
ISSUES=ROOT/"quality"/"synthetic-lab-issues.json"
REPORT=ROOT/"quality"/"issue-triage-report.json"
VALID_STATUSES={"synthetic_unverified","fix_deployed_pending_synthetic_retest",
                "retested_ai_clear_pending_deterministic_review","discarded_invalid_scenario"}
CONFIRMED_FLAGS={"payment_choice_repeat","color_change_ignored","exact_repeat","stock_no_next_step"}

def bucket(issue):
 if not isinstance(issue,dict):return "malformed"
 if issue.get("status") not in VALID_STATUSES:return "other_status"
 if issue.get("status")=="discarded_invalid_scenario":return "discarded"
 try:
  scenario=lab.validate_cases({"scenarios":[issue["scenario"]]})[0]
 except (KeyError,ValueError,TypeError):return "invalid_replay_evidence"
 rows=issue.get("evidence",[])
 if not isinstance(rows,list) or len(rows)!=len(scenario["messages"]):
  return "invalid_replay_evidence"
 if any(not isinstance(row,dict) or row.get("buyer")!=msg for msg,row in zip(scenario["messages"],rows)):
  return "invalid_replay_evidence"
 if issue.get("status")=="fix_deployed_pending_synthetic_retest":return "deployed_needs_retest"
 if issue.get("status")=="retested_ai_clear_pending_deterministic_review":return "cleared_ai_needs_deterministic_review"
 flags=issue.get("static_flags",[])
 if not isinstance(flags,list):return "invalid_replay_evidence"
 flag=any(x in CONFIRMED_FLAGS for x in flags)
 grade=issue.get("grade")
 ai=bool(isinstance(grade,dict) and grade.get("error") is True)
 if flag and ai:return "convergent_signals_pending_replay"
 if flag:return "deterministic_signal_pending_replay"
 if ai:return "ai_only_unverified"
 return "not_enough_evidence"

def fingerprint(issue):
 """Dedup only same normalized synthetic turns and category, never client PII."""
 scenario=issue.get("scenario") if isinstance(issue,dict) else None
 if not isinstance(scenario,dict):return None
 try:clean=lab.validate_cases({"scenarios":[scenario]})[0]
 except (ValueError,TypeError):return None
 payload={"category":clean["category"],"messages":[re.sub(r"\s+"," ",x.casefold()).strip()
                                                     for x in clean["messages"]]}
 return hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:18]

def summarize(issues):
 if not isinstance(issues,list):raise ValueError("Expected issue array")
 buckets=Counter()
 topics=defaultdict(Counter)
 ids=set()
 unique_fingerprints=set()
 duplicates=0
 for issue in issues:
  result=bucket(issue)
  buckets[result]+=1
  category=issue.get("category","unknown") if isinstance(issue,dict) else "unknown"
  if not isinstance(category,str) or len(category)>50:category="unknown"
  topics[category][result]+=1
  fp=fingerprint(issue)
  if fp:
   if fp in unique_fingerprints:duplicates+=1
   unique_fingerprints.add(fp)
  if isinstance(issue,dict) and isinstance(issue.get("id"),str):ids.add(issue["id"])
 priority={"convergent_signals_pending_replay":0,"deterministic_signal_pending_replay":1,
           "deployed_needs_retest":2,"ai_only_unverified":3,"cleared_ai_needs_deterministic_review":4}
 shortlist=sorted((x for x in issues if isinstance(x,dict) and bucket(x) in priority),
  key=lambda x:(priority[bucket(x)],x.get("at","")),reverse=False)[:12]
 return {
  "at":datetime.now(timezone.utc).isoformat(),"total_records":len(issues),
  "distinct_issue_ids":len(ids),"duplicate_conversation_fingerprints":duplicates,
  "bucket_counts":dict(sorted(buckets.items())),"by_topic":{k:dict(v) for k,v in sorted(topics.items())},
  "priority_ids":[{"id":x.get("id"),"category":x.get("category"),"class":bucket(x)}
                  for x in shortlist],
  "promoted_or_proven_by_ai_alone":0,
  "note":"Synthetic issues are suspicions, not proven real customer defects; prioritize independent isolated replay."}

def run():
 report=summarize(_load(ISSUES,[]))
 _atomic_json(REPORT,report)
 return report

if __name__=="__main__":
 print(json.dumps(run(),ensure_ascii=False))
