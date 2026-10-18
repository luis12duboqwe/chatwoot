#!/usr/bin/env python3
"""Verify the *installed* SoftMobile bot inside Chatwoot, read-only.

No public or private Chatwoot messages are created. The code's test branch
exits before DB/message code. This file cannot deploy or override daily caps.
"""
import argparse,hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
from quality_auditor import _load,_atomic_json
import combined_pilot_promotion as combined
import autonomous_learning as learner
import conversion_training_lab as sales
import financing_holdout as financing
import context_accuracy_lab as memory
import inventory_quality_lab as inventory
import offline_issue_replay as replay
import auto_improver as fixer

RESULT=combined.QA/"postdeploy-pilot-smoke.json"

def review(source=None):
 now=datetime.now(timezone.utc).isoformat()
 published=learner.BOT.read_text() if source is None else source
 sha=hashlib.sha256(published.encode()).hexdigest()
 expected=combined.KNOWN_V4_SHA
 outcome={"at":now,"status":"not_installed","actual_sha256":sha,
          "expected_sha256":expected,"pilot_only":True,
          "public_messages_sent":0,"real_inventory_changed":False,
          "payments_taken":0,"real_client_journey_verified":False}
 if sha!=expected:return outcome
 if not (published.count("PILOT_CONVERSATION_ID = 3")==1
         and published.count("INBOX_ID = 2")==1):
  outcome["status"]="pilot_scope_failed";return outcome
 hist=_load(learner.HISTORY,[])
 installed=[r for r in hist if isinstance(r,dict) and r.get("promoted") is True
            and r.get("new_sha256")==expected]
 if not installed:
  outcome["status"]="promotion_history_missing";return outcome
 if not combined.chatwoot_runtime_smoke(published):
  outcome["status"]="live_chatwoot_rails_smoke_failed";return outcome
 sold,_=sales.run(source=published,persist=False)
 credit=financing.verify(source=published)
 preference=memory.evaluate(source=published)
 stock=inventory.evaluate(source=published)
 outcome["sales_tested"]=sold.get("scenarios")
 outcome["sales_passed"]=sold.get("passed")
 outcome["financing_tested"]=credit.get("total")
 outcome["financing_passed"]=credit.get("passed")
 outcome["context_tested"]=preference.get("total")
 outcome["context_passed"]=preference.get("passed")
 outcome["inventory_tested"]=stock.get("scenario_count")
 outcome["inventory_passed"]=stock.get("passed")
 outcome["unsafe_promises"]=stock.get("safety_violations")
 if not (sold.get("scenarios")==sold.get("passed")==72 and
         credit.get("total")==credit.get("passed")==48 and
         preference.get("total")==preference.get("passed")==8 and
         stock.get("scenario_count")==stock.get("passed")==108
         and stock.get("safety_violations")==0):
  outcome["status"]="postdeploy_offline_regression";return outcome
 baseline_path=fixer.BACKUPS/installed[-1].get("backup","")
 if baseline_path.is_file():
  baseline=baseline_path.read_text()
  staged=_load(combined.REVIEW,{})
  if combined.digest(baseline)==staged.get("baseline_sha256"):
   old=replay.assess(source=baseline)
   new=replay.assess(source=published)
   diff=replay.compare(old,new)
   outcome["historical_cases"]=diff["cases_compared"]
   outcome["new_historical_flags"]=diff["new_flags_in_candidate"]
   if diff["new_flags_in_candidate"]:
    outcome["status"]="historical_replay_regression";return outcome
 outcome["status"]="installed_and_chatwoot_smoke_passed"
 return outcome

def main():
 p=argparse.ArgumentParser()
 g=p.add_mutually_exclusive_group(required=True)
 g.add_argument("--run",action="store_true")
 g.add_argument("--status",action="store_true")
 args=p.parse_args()
 if args.status:
  print(json.dumps(_load(RESULT,{"status":"not_checked"}),ensure_ascii=False));return 0
 try:
  result=review()
  _atomic_json(RESULT,result)
  print(json.dumps(result,ensure_ascii=False))
  return 0 if result["status"] in ("installed_and_chatwoot_smoke_passed","not_installed") else 2
 except (ValueError,TypeError,RuntimeError,OSError,KeyError):
  fail={"at":datetime.now(timezone.utc).isoformat(),
        "status":"postinstall_verification_failed_closed",
        "public_messages_sent":0}
  _atomic_json(RESULT,fail)
  print(json.dumps(fail));return 2
if __name__=="__main__":sys.exit(main())
