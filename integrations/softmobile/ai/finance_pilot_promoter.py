#!/usr/bin/env python3
"""Fallback pilot-only promotion of an objectively tested static parser fix.

Runs AFTER combined bundle has first choice. The common learned-deployment
history enforces one update per UTC day; never broadens Chatwoot scope.
No model code/price/stock and no public network in tests.
"""
from datetime import datetime,timezone
import argparse,fcntl,json,os,sys
import autonomous_learning as learner
import combined_pilot_promotion as bundled
import conversion_candidate_review as finance
import conversion_training_lab as sales
import financing_holdout
import inventory_quality_lab as stock
from isolated_gate import gates as ruby_gates
from quality_auditor import _load,_atomic_json
import auto_improver as fixer
import synthetic_lab as lab

ROOT=bundled.QA
REPORT=ROOT/"financing-fallback-promotion.json"
EXPECTED_BASE=bundled.EXPECTED_BASE
KNOWN_FIN_SHA=bundled.KNOWN_FIN_SHA

def fixed_candidate(source):
 if bundled.digest(source)!=EXPECTED_BASE:
  raise ValueError("Not the reviewed pilot source")
 result=finance.create_candidate(source)
 if bundled.digest(result)!=KNOWN_FIN_SHA:
  raise ValueError("Non-reviewed finance fix")
 pack=learner.validate_pack(_load(learner.STORE,learner.empty_pack()))
 if learner.compile_source(result,pack)!=result:
  raise ValueError("Autolearner incompatible with finance candidate")
 return result

def validate(source,candidate):
 before,_=sales.run(source=source,persist=False)
 after,_=sales.run(source=candidate,persist=False)
 if not finance.admissible(before,after):
  return {"status":"sales_regression"}
 old=financing_holdout.verify(source=source)
 new=financing_holdout.verify(source=candidate)
 if new["total"]!=48 or new["passed"]!=48 or new["passed"]<old["passed"]:
  return {"status":"holdout_regression"}
 rub=ruby_gates(candidate)
 if rub.get("status")!="passed" or rub.get("total",0)<117:
  return {"status":"ruby_regression"}
 old_inv=stock.evaluate(source=source)
 new_inv=stock.evaluate(source=candidate)
 if new_inv["scenario_count"]!=108 or new_inv["failed"]>old_inv["failed"] or new_inv["safety_violations"]:
  return {"status":"inventory_regression"}
 return {"status":"verified",
         "sales_before":before["passed"],"sales_after":after["passed"],
         "holdout_before":old["passed"],"holdout_after":new["passed"],
         "ruby_tests":rub["total"],"stock_tests":new_inv["scenario_count"],
         "stock_failures":new_inv["failed"],"unsafe_claims":new_inv["safety_violations"]}

def promote(installer=fixer.deploy,validator=validate):
 now=datetime.now(timezone.utc).isoformat()
 day=datetime.now(timezone.utc).date().isoformat()
 if bundled.deployed_today(day)>=1:
  return {"at":now,"status":"daily_deployment_cap","promoted":False}
 source=learner.BOT.read_text()
 if bundled.digest(source)==KNOWN_FIN_SHA:
  return {"at":now,"status":"already_installed","promoted":False}
 if bundled.digest(source)!=EXPECTED_BASE:
  return {"at":now,"status":"source_changed","promoted":False}
 staged=_load(finance.REVIEW,{})
 if (staged.get("status")!="review_ready_not_deployed"
    or staged.get("baseline_sha256")!=EXPECTED_BASE
    or staged.get("candidate_sha256")!=KNOWN_FIN_SHA):
  return {"at":now,"status":"finance_review_not_preverified","promoted":False}
 proposed=fixed_candidate(source)
 name=staged.get("stage_file","")
 if (not name or name!=("financing-"+KNOWN_FIN_SHA[:18]+".rb")
     or not (finance.STAGE/name).is_file()
     or (finance.STAGE/name).read_text()!=proposed):
  return {"at":now,"status":"source_or_stage_tampered","promoted":False}
 checks=validator(source,proposed)
 if checks.get("status")!="verified":
  return {"at":now,"status":"finance_regression_rejected","promoted":False,"checks":checks}
 if learner.BOT.read_text()!=source:
  return {"at":now,"status":"source_changed_during_checks","promoted":False}
 deployed=installer(proposed)
 if deployed.get("status")!="deployed":
  return {"at":now,"status":"deploy_rejected","promoted":False}
 try:
  if learner.BOT.read_text()!=proposed:raise RuntimeError("Post-install source changed")
  post=validator(source,learner.BOT.read_text())
  if post.get("status")!="verified":raise RuntimeError("Post-install regression")
 except BaseException:
  bundled.restore_before_going_live(source,proposed)
  return {"at":now,"status":"rolled_back_after_failed_gate","promoted":False,
          "backup":deployed.get("backup_name")}
 result={"at":now,"day":day,"status":"financing_pilot_deployed_pending_retest",
         "promoted":True,"pilot_only":True,
         "previous_sha256":EXPECTED_BASE,
         "new_sha256":KNOWN_FIN_SHA,
         "backup":deployed.get("backup_name"),
         "checks":checks,"public_messages_sent_during_tests":0}
 history=_load(learner.HISTORY,[])
 _atomic_json(learner.HISTORY,(history+[result])[-100:])
 return result

def run():
 ROOT.mkdir(parents=True,exist_ok=True,mode=0o700)
 with open(learner.LOCK,"a+") as learning:
  fcntl.flock(learning,fcntl.LOCK_EX|fcntl.LOCK_NB)
  with open(fixer.LOCK,"a+") as fixing:
   fcntl.flock(fixing,fcntl.LOCK_EX|fcntl.LOCK_NB)
   with open(lab.LOCK,"a+") as synthetic:
    fcntl.flock(synthetic,fcntl.LOCK_EX|fcntl.LOCK_NB)
    result=promote()
    _atomic_json(REPORT,result)
    return result

def main():
 p=argparse.ArgumentParser()
 m=p.add_mutually_exclusive_group(required=True)
 m.add_argument("--run",action="store_true")
 m.add_argument("--status",action="store_true")
 args=p.parse_args()
 if args.status:
  print(json.dumps(_load(REPORT,{"status":"not_run"}),ensure_ascii=False));return 0
 if os.environ.get("SOFTMOBILE_FINANCE_FALLBACK_ENABLED")!="true":
  print("finance_promotion_disabled");return 2
 try:
  out=run()
  print(json.dumps(out,ensure_ascii=False))
  return 0 if out.get("status") in ("daily_deployment_cap","already_installed",
    "financing_pilot_deployed_pending_retest","source_changed",
    "finance_review_not_preverified") else 2
 except BlockingIOError:
  print("other_training_process_busy");return 0
 except (RuntimeError,ValueError,OSError,KeyError,TypeError):
  print("safe_finance_promotion_rejected");return 2
if __name__=="__main__":sys.exit(main())
