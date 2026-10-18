#!/usr/bin/env python3
"""Single safe pilot-only bundled promotion for two *fixed* proven corrections.

Bundles a static finance-parser fix and a fixed human-handoff accessory
pattern into one pilot deployment, avoiding racing two daily promotors.

No arbitrary model-generated code, stock, payments, broader customer routing,
or unlimited deployment. Promotion needs exact source hash, persisted
pre-verification, independent full regression suites, trusted backup,
atomic rollback on unexpected post-deployment behavior, and the one/day cap.
"""
import argparse
from datetime import datetime,timezone
import fcntl,hashlib,json,os,sys
from pathlib import Path
import tempfile

from quality_auditor import _load,_atomic_json
import autonomous_learning as learner
import semantic_generalization as semantic
import conversion_candidate_review as finance
import conversion_training_lab as sales
import financing_holdout
import inventory_quality_lab as inventory
import synthetic_lab as lab
import auto_improver as fixer
import accessory_directness as direct
import learned_retest as retest

ROOT=Path(__file__).resolve().parent
QA=ROOT/"quality"
STAGING=QA/"combined-pilot-candidates"
REVIEW=QA/"combined-pilot-review.json"
STATUS=QA/"combined-pilot-promotion-status.json"
REVISION="bundle-static-semantic-financing-directness-20261018-v2"
DAILY_CAP=1
EXPECTED_BASE="4dc2814ddb5d3a03c31add202cb004f6369a77b154f2fa5141d5dfb3220ef106"
KNOWN_SEM_SHA="f988868718e2d13d1107839809b5342618d6f025caa0750811d14f2b443ae02f"
KNOWN_FIN_SHA="972b74f1e4a9126059fb273117178f131a7299e5f24b03c15451d7df5734755e"

def digest(s):
 return hashlib.sha256(s.encode()).hexdigest()

def prepare(source,pack):
 learner.validate_pack(pack)
 if digest(source)!=EXPECTED_BASE:
  raise ValueError("Pilot source changed: bundle requires independent restaging")
 # No model-generated Ruby allowed: this is two fixed literal replacements.
 sem=semantic.build(source,pack)
 fin=finance.create_candidate(source)
 combined=direct.append(finance.create_candidate(sem))
 if digest(sem)!=KNOWN_SEM_SHA or digest(fin)!=KNOWN_FIN_SHA:
  raise ValueError("Proven independent candidate SHA mismatch")
 if source.count("PILOT_CONVERSATION_ID = 3")!=1 or source.count("INBOX_ID = 2")!=1:
  raise ValueError("Pilot guard not present")
 if (combined.count(semantic.RUBY_RULE)!=1 or combined.count(finance.NEW)!=1
     or combined.count(direct.CODE)!=1):
  raise ValueError("Bundled transformations differ")
 if combined.count(finance.OLD)>0:raise ValueError("Unfixed finance parser")
 if learner.compile_source(combined,pack)!=combined:
  raise ValueError("Bundled code incompatible with autonomous learning compiler")
 return combined

def evidence(source,combined):
 before,_=sales.run(source=source,persist=False)
 after,_=sales.run(source=combined,persist=False)
 if not finance.admissible(before,after):
  return {"status":"sales_regressions","before":before["passed"],"after":after["passed"]}
 # Explicitly replay the previously AI-flagged exact buyer question and
 # inspect the candidate's customer-facing answer. A canned safe fallback
 # is not sufficient unless it mentions the possibility of free inclusion.
 specific=[
  "Busco un celular que me guste",
  "Me preocupa que el precio no incluya la funda, ¿puedo agregarla sin costo adicional?"
 ]
 exact=learner.trace_output(combined,specific)
 if (exact.get("reply")!=direct.REPLY or exact.get("needs_human") is not True
     or exact.get("tag")!="sm_learned_dialogue"
     or "sin costo" not in exact["reply"].lower()
     or "no puedo incluirte" not in exact["reply"].lower()):
  return {"status":"accessory_directness_failed"}
 hold_old=financing_holdout.verify(source=source)
 hold_new=financing_holdout.verify(source=combined)
 if hold_new["total"]!=48 or hold_new["passed"]!=48 or hold_new["passed"]<hold_old["passed"]:
  return {"status":"holdout_regressions","old":hold_old["passed"],"new":hold_new["passed"]}
 # This also enforces 10/10 positive semantic, 14/14 negatives, and full 117 Ruby.
 sem=semantic.gates(source,combined)
 if sem.get("status")!="verified_in_sandbox":
  return {"status":"semantic_or_ruby_regression","semantic":sem}
 base=inventory.evaluate(source=source)
 cand=inventory.evaluate(source=combined)
 if (base["scenario_count"]!=108 or cand["scenario_count"]!=108
     or cand["failed"]>base["failed"] or cand["safety_violations"]):
  return {"status":"inventory_regressions",
          "base_failures":base["failed"],"new_failures":cand["failed"],
          "unsafe_claims":cand["safety_violations"]}
 return {"status":"gates_passed","sales_before":before["passed"],"sales_after":after["passed"],
         "total_sales":after["scenarios"],
         "financing_before":before["by_family"]["financing"]["passed"],
         "financing_after":after["by_family"]["financing"]["passed"],
         "holdout_before":hold_old["passed"],"holdout_after":hold_new["passed"],
         "holdout_total":hold_new["total"],
         "semantic_positive":sem["positive"],"semantic_negative":sem["negative"],
         "direct_accessory_answer_verification":True,
         "ruby_regressions":sem["ruby_regressions"]["total"],
         "stock_scenarios":cand["scenario_count"],"stock_before":base["passed"],
         "stock_after":cand["passed"],"unsafe_claims":cand["safety_violations"]}

def stage(source,combined,checks):
 if checks.get("status")!="gates_passed":raise ValueError("Cannot stage failing candidate")
 STAGING.mkdir(parents=True,exist_ok=True,mode=0o700)
 digest_candidate=digest(combined)
 path=STAGING/("combined-"+digest_candidate[:18]+".rb")
 fd,temp=tempfile.mkstemp(dir=STAGING,prefix=".combined-")
 try:
  with os.fdopen(fd,"w") as f:
   f.write(combined);f.flush();os.fsync(f.fileno())
  os.chmod(temp,0o600)
  os.replace(temp,path)
 finally:
  if os.path.exists(temp):os.unlink(temp)
 result={"at":datetime.now(timezone.utc).isoformat(),"status":"verified_staged",
   "revision":REVISION,"baseline_sha256":digest(source),
   "candidate_sha256":digest_candidate,"stage_file":path.name,
   "gates":checks,"pilot_only":True,"promoted":False,
   "arbitrary_llm_code_executed":False,"public_messages_sent":0}
 _atomic_json(REVIEW,result)
 return result

def review():
 source=learner.BOT.read_text()
 pack=learner.validate_pack(_load(learner.STORE,learner.empty_pack()))
 combined=prepare(source,pack)
 checks=evidence(source,combined)
 if checks.get("status")!="gates_passed":
  outcome={"at":datetime.now(timezone.utc).isoformat(),
           "status":"not_approved","evidence":checks,"promoted":False}
  _atomic_json(REVIEW,outcome)
  return outcome
 return stage(source,combined,checks)

def deployed_today(day):
 history=_load(learner.HISTORY,[])
 if not isinstance(history,list):raise ValueError("History corrupted")
 return sum(isinstance(h,dict) and h.get("day")==day and h.get("promoted") is True
            for h in history)

def restore_before_going_live(previous,candidate):
 """If independent post-deploy checks fail, revert via backup atomically."""
 import subprocess
 from auto_improver import TIMER,SERVICE
 if learner.BOT.read_text()!=candidate:
  raise RuntimeError("Source changed concurrently, cannot blindly roll back")
 subprocess.run(["systemctl","stop",TIMER],check=True)
 try:
  r=subprocess.run(["systemctl","is-active",SERVICE],capture_output=True,text=True)
  if r.stdout.strip()=="active":
   raise RuntimeError("Bot service busy; stop and manually recover from backup")
  if learner.BOT.read_text()!=candidate:
   raise RuntimeError("Source modified since promotion; manual intervention required")
  mode=learner.BOT.stat().st_mode&0o777
  fd,temp=tempfile.mkstemp(dir=learner.BOT.parent,prefix=".bundled-rollback-")
  try:
   with os.fdopen(fd,"wb") as f:
    f.write(previous.encode());f.flush();os.fsync(f.fileno())
   os.chmod(temp,mode);os.replace(temp,learner.BOT)
  finally:
   if os.path.exists(temp):os.unlink(temp)
 finally:
  subprocess.run(["systemctl","start",TIMER],check=True)

def independent_quality_approved(candidate):
 """Quality alert from Groq must be resolved on the EXACT staged version."""
 path=QA/"directness-independent-review.json"
 observed=_load(path,{})
 if not isinstance(observed,dict):return False
 if observed.get("status")!="independent_ai_approved":return False
 if observed.get("candidate_sha256")!=digest(candidate):return False
 if observed.get("revision")!=REVISION:return False
 if observed.get("judge_error") is not False:return False
 try:
  timestamp=datetime.fromisoformat(observed["at"])
  if timestamp.tzinfo is None:return False
  age=(datetime.now(timezone.utc)-timestamp.astimezone(timezone.utc)).total_seconds()
  return 0<=age<=86400
 except (ValueError,TypeError,KeyError):
  return False

def promote(installer=fixer.deploy,validator=evidence):
 day=datetime.now(timezone.utc).date().isoformat()
 now=datetime.now(timezone.utc).isoformat()
 if deployed_today(day)>=DAILY_CAP:
  return {"at":now,"status":"daily_deployment_cap","promoted":False}
 current=learner.BOT.read_text()
 if semantic.SIGN in current and finance.NEW in current:
  return {"at":now,"status":"already_installed","promoted":False}
 record=_load(REVIEW,{})
 if (record.get("status")!="verified_staged" or record.get("revision")!=REVISION
     or record.get("baseline_sha256")!=digest(current)
     or not record.get("stage_file")):
  return {"at":now,"status":"review_or_source_mismatch","promoted":False}
 pack=learner.validate_pack(_load(learner.STORE,learner.empty_pack()))
 expected=prepare(current,pack)
 stored=STAGING/record["stage_file"]
 if (not stored.is_file() or stored.read_text()!=expected
     or digest(expected)!=record.get("candidate_sha256")):
  return {"at":now,"status":"staged_candidate_tampered","promoted":False}
 if not independent_quality_approved(expected):
  return {"at":now,"status":"independent_ai_quality_pending","promoted":False}
 tests=validator(current,expected)
 if tests.get("status")!="gates_passed":
  return {"at":now,"status":"independent_gates_failed","evidence":tests,"promoted":False}
 if learner.BOT.read_text()!=current:
  return {"at":now,"status":"concurrent_bot_change","promoted":False}
 result=installer(expected)
 if result.get("status")!="deployed":
  return {"at":now,"status":"safe_deployment_rejected","promoted":False}
 # The normal deploy() performed the full 117 Ruby suite after replacing the file.
 # Repeat INDEPENDENT sales and stock gate; revert on post-deploy failure.
 try:
  if learner.BOT.read_text()!=expected:
   raise RuntimeError("Post-deploy source drift")
  post=validator(current,learner.BOT.read_text())
  if post.get("status")!="gates_passed":
   raise RuntimeError("Post-deploy differential failure")
 except BaseException:
  restore_before_going_live(current,expected)
  return {"at":now,"status":"postdeploy_failed_rolled_back","promoted":False,
          "backup":result.get("backup_name")}
 row={"at":now,"day":day,"status":"pilot_deployed_pending_retest",
      "promoted":True,"pilot_only":True,
      "previous_sha256":digest(current),"new_sha256":digest(expected),
      "backup":result.get("backup_name"),"validation":tests,
      "public_messages_sent_during_tests":0}
 history=_load(learner.HISTORY,[])
 _atomic_json(learner.HISTORY,(history+[row])[-100:])
 return row

def run(promote_enabled=False):
 QA.mkdir(mode=0o700,parents=True,exist_ok=True)
 # Same three locks and order as the existing autolearner/semantic promoter.
 with open(learner.LOCK,"a+") as learning:
  os.fchmod(learning.fileno(),0o600)
  fcntl.flock(learning,fcntl.LOCK_EX|fcntl.LOCK_NB)
  with open(fixer.LOCK,"a+") as fix:
   os.fchmod(fix.fileno(),0o600)
   fcntl.flock(fix,fcntl.LOCK_EX|fcntl.LOCK_NB)
   with open(lab.LOCK,"a+") as synthetic:
    os.fchmod(synthetic.fileno(),0o600)
    fcntl.flock(synthetic,fcntl.LOCK_EX|fcntl.LOCK_NB)
    result=promote() if promote_enabled else review()
    _atomic_json(STATUS,result)
    return result

def main():
 p=argparse.ArgumentParser()
 group=p.add_mutually_exclusive_group(required=True)
 group.add_argument("--stage",action="store_true")
 group.add_argument("--run",action="store_true")
 group.add_argument("--status",action="store_true")
 args=p.parse_args()
 if args.status:
  print(json.dumps(_load(STATUS,{"status":"not_started"}),ensure_ascii=False));return 0
 if args.run and os.environ.get("SOFTMOBILE_BUNDLED_PILOT_ENABLED")!="true":
  print("disabled");return 2
 try:
  result=run(promote_enabled=args.run)
  print(json.dumps(result,ensure_ascii=False))
  if args.run and result["status"] in ("daily_deployment_cap","already_installed","pilot_deployed_pending_retest","review_or_source_mismatch"):
   return 0
  return 0 if args.stage and result.get("status")=="verified_staged" else 2
 except BlockingIOError:print("other_learning_lab_busy");return 0
 except (OSError,ValueError,RuntimeError,TypeError,KeyError) as exc:
  print("bundled_promotion_failed_closed:"+type(exc).__name__);return 2
if __name__=="__main__":sys.exit(main())
