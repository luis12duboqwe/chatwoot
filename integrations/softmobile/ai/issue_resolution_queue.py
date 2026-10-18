#!/usr/bin/env python3
"""Compact actionable triage for synthetic replay hypotheses.

An issue is not a confirmed customer bug. Reproduced static signals remain
unverified until tested with a distinct oracle or explicitly reviewed. The
queue cannot edit Ruby, send messages or mark any finding 'resolved'.
"""
import argparse,json
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
import issue_triage as triage
from quality_auditor import _load,_atomic_json

QA=Path(__file__).resolve().parent/"quality"
OUT=QA/"issue-resolution-queue.json"
REVIEWABLE={"previous_flags_reproduced","new_deterministic_flags"}

def build(issues,replay):
 if not isinstance(issues,list) or not isinstance(replay,dict):
  raise ValueError("Bad quality stores")
 results=replay.get("results",[])
 if not isinstance(results,list):raise ValueError("Corrupt replay report")
 by_id={x["id"]:x for x in results if isinstance(x,dict) and isinstance(x.get("id"),str)}
 groups=defaultdict(list)
 confirmed=0
 for issue in issues:
  category=triage.bucket(issue)
  if category not in ("convergent_signals_pending_replay",
                      "deterministic_signal_pending_replay",
                      "deployed_needs_retest"):continue
  result=by_id.get(issue.get("id"))
  if not result or result.get("outcome") not in REVIEWABLE:continue
  flags=result.get("new_flags",[])
  if not isinstance(flags,list) or not flags:continue
  ai=issue.get("grade",{})
  corroborated=bool(isinstance(ai,dict) and ai.get("error") is True)
  rank=0 if corroborated else 1
  for flag in sorted(set(flags)):
   if not isinstance(flag,str) or len(flag)>48:continue
   groups[(rank,issue.get("category","unknown"),flag)].append(issue["id"])
  confirmed+=1
 clusters=[{"category":category,"signal":signal,
            "corroborated_by_ai":rank==0,
            "synthetic_examples":len(ids),
            "ids":sorted(set(ids))[:5],
            "status":"needs_independent_review",
            "autonomous_code_promotion_authorized":False}
           for (rank,category,signal),ids in groups.items()]
 clusters.sort(key=lambda x:(not x["corroborated_by_ai"],-x["synthetic_examples"],
                              x["category"],x["signal"]))
 return {"at":datetime.now(timezone.utc).isoformat(),
         "status":"quality_triage_only","stored_hypotheses":len(issues),
         "replay_cases":len(results),"reviewable_replayed_hypotheses":confirmed,
         "unreviewed_clusters":len(clusters),"clusters":clusters[:50],
         "real_customer_defects_proven":0,"public_messages_sent":0,
         "auto_deployments":0,"requires_confirmation":True}

def run():
 out=build(_load(triage.ISSUES,[]),_load(QA/"offline-issue-replay-report.json",{}))
 _atomic_json(OUT,out);return out

def main():
 p=argparse.ArgumentParser()
 group=p.add_mutually_exclusive_group(required=True)
 group.add_argument("--run",action="store_true")
 group.add_argument("--status",action="store_true")
 args=p.parse_args()
 out=run() if args.run else _load(OUT,{"status":"not_run"})
 print(json.dumps({k:v for k,v in out.items() if k!="clusters"},ensure_ascii=False))
if __name__=="__main__":main()
