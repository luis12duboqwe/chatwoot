#!/usr/bin/env python3
"""Safely promote a *previously staged and verified* fixed family pattern.

Never consumes model-authored Ruby, respects the learned-policy daily cap,
checks source drift, replays negative cases, and uses existing backup+rollback.
This operator-enabled systemd job applies only to restricted pilot #3.
"""
from datetime import datetime,timezone
import argparse,fcntl,hashlib,json,os,sys
from pathlib import Path

import autonomous_learning as learn
import semantic_generalization as sem
import synthetic_lab as lab
import promotion_budget
import auto_improver as fixer
from quality_auditor import _load,_atomic_json

REPORT=sem.DIR/"semantic-promotion-summary.json"
MAX_DAILY_PROMOTIONS=1

def daily_count(rows,day):
 if not isinstance(rows,list):raise ValueError("Invalid promotion log")
 return sum(isinstance(x,dict) and x.get("day")==day and x.get("promoted") is True
            for x in rows)

def assess(allow_deploy=False,validator=sem.gates,installer=fixer.deploy):
 day=datetime.now(timezone.utc).date().isoformat()
 hist=_load(learn.HISTORY,[])
 if daily_count(hist,day)>=MAX_DAILY_PROMOTIONS or promotion_budget.exhausted(day):
  return {"status":"daily_deployment_cap","promoted":False}
 pack=learn.validate_pack(_load(learn.STORE,learn.empty_pack()))
 source=learn.BOT.read_text()
 if sem.SIGN in source:
  # Evidence of already installed semantic policy. Never redeploy it.
  if source.count(sem.RUBY_RULE)!=1:
   return {"status":"installed_source_drift","promoted":False}
  return {"status":"already_installed","promoted":False}
 previous=_load(sem.REPORT,{})
 if previous.get("status")!="verified_in_sandbox":
  return {"status":"no_preverified_candidate","promoted":False}
 source_sha=hashlib.sha256(source.encode()).hexdigest()
 if source_sha!=previous.get("original_sha256"):
  return {"status":"source_changed_restaging_required","promoted":False}
 candidate=sem.build(source,pack)
 candidate_sha=hashlib.sha256(candidate.encode()).hexdigest()
 if candidate_sha!=previous.get("candidate_sha256"):
  return {"status":"candidate_changed_restaging_required","promoted":False}
 stage=sem.STAGE/previous.get("stage_file","")
 if not stage.is_file() or stage.read_text()!=candidate:
  return {"status":"candidate_missing_or_modified","promoted":False}
 checks=validator(source,candidate)
 if checks.get("status")!="verified_in_sandbox":
  return {"status":"regression_rejected","validation":checks,"promoted":False}
 # Independent stock/variant stress suite must not regress when Ruby changes.
 # Only fictitious records and no-network ephemeral Ruby processes are used.
 import inventory_quality_lab as stock_quality
 before_quality=stock_quality.evaluate(source=source)
 after_quality=stock_quality.evaluate(source=candidate)
 checks["simulated_inventory_gate"]={
  "scenarios":after_quality["scenario_count"],
  "baseline_failures":before_quality["failed"],
  "candidate_failures":after_quality["failed"],
  "unsafe_claims":after_quality["safety_violations"]}
 if (after_quality["scenario_count"]<100 or
     after_quality["failed"]>before_quality["failed"] or
     after_quality["safety_violations"]!=0):
  return {"status":"mock_inventory_regression_rejected","validation":checks,"promoted":False}
 result={"status":"verified_not_deployed","day":day,
         "source_sha256":source_sha,"candidate_sha256":candidate_sha,
         "validation":checks,"promoted":False,"pilot_only":True}
 if not allow_deploy:return result
 if source!=learn.BOT.read_text():
  result["status"]="concurrent_source_change";return result
 installed=installer(candidate)
 if installed.get("status")=="deployed" and learn.BOT.read_text()==candidate:
  result.update({"status":"pilot_deployed_pending_retest","promoted":True,
                 "backup":installed.get("backup_name")})
 else:
  result["status"]="deployment_unverified"
 return result

def run(deploy=False):
 sem.DIR.mkdir(parents=True,exist_ok=True,mode=0o700)
 with open(learn.LOCK,"a+") as learned:
  os.fchmod(learned.fileno(),0o600)
  fcntl.flock(learned,fcntl.LOCK_EX|fcntl.LOCK_NB)
  with open(fixer.LOCK,"a+") as fix:
   os.fchmod(fix.fileno(),0o600)
   fcntl.flock(fix,fcntl.LOCK_EX|fcntl.LOCK_NB)
   with open(lab.LOCK,"a+") as l:
    os.fchmod(l.fileno(),0o600)
    fcntl.flock(l,fcntl.LOCK_EX|fcntl.LOCK_NB)
    result=assess(allow_deploy=deploy)
    record={"at":datetime.now(timezone.utc).isoformat(),
            "day":datetime.now(timezone.utc).date().isoformat(),**result}
    if deploy and record.get("promoted") is True:
     history=_load(learn.HISTORY,[])
     _atomic_json(learn.HISTORY,(history+[record])[-100:])
    _atomic_json(REPORT,record)
    return record

def main():
 p=argparse.ArgumentParser()
 g=p.add_mutually_exclusive_group(required=True)
 g.add_argument("--run",action="store_true")
 g.add_argument("--dry-run",action="store_true")
 g.add_argument("--status",action="store_true")
 a=p.parse_args()
 if a.status:
  print(json.dumps(_load(REPORT,{"status":"not_run"}),ensure_ascii=False));return 0
 if a.run and os.getenv("SOFTMOBILE_SEMANTIC_PROMOTION_ENABLED")!="true":
  print("semantic_promotion_not_enabled");return 2
 try:
  print(json.dumps(run(deploy=a.run),ensure_ascii=False));return 0
 except BlockingIOError:print("semantic_promotion_other_lab_busy");return 0
 except (OSError,TypeError,ValueError,RuntimeError,KeyError):
  print("semantic_promotion_rejected_safely");return 2

if __name__=="__main__":sys.exit(main())
