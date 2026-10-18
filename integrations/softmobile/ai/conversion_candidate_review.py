#!/usr/bin/env python3
"""Fixed, review-only fix for a clear financing/model ambiguity.

No Groq-proposed Ruby, no deployment. Any model/context source drift fails
closed. Approving the review is separate from the pilot's deployment quotas.
"""
import hashlib,json,os,tempfile
from datetime import datetime,timezone
from pathlib import Path
from quality_auditor import _atomic_json,_load
from isolated_gate import gates as ruby_gates
from inventory_quality_lab import evaluate as stock_gate
import conversion_training_lab as sales
import patch_proposer
import financing_holdout

ROOT=Path(__file__).resolve().parent
REVIEW=ROOT/"quality"/"financing-model-review.json"
STAGE=ROOT/"quality"/"conversion-candidates"
# Whitelisted static source replacement, not arbitrary model-generated code.
OLD=r'if (m = t.match(/\b(?:samsung\s+|galaxy\s+)?a\s*(\d{2})(?:\s+(5g|4g))?\b/))'
NEW=r'if (m = t.match(/\b(?:samsung\s+|galaxy\s+)?a\s*(\d{2})(?!\s*(?:meses?|cuotas?|pagos?|plazos?|mensualidades)\b)(?:\s+(5g|4g))?\b/))'

def create_candidate(source):
 if not isinstance(source,str) or source.count(OLD)!=1 or source.count(NEW):
  raise ValueError("Untrusted Ruby source or new regex already present")
 if source.count("PILOT_CONVERSATION_ID = 3")!=1 or source.count("AUTO_REPLY_LIMIT = 1")!=1:
  raise ValueError("Pilot identity drift")
 candidate=source.replace(OLD,NEW,1)
 if len(candidate)<5000 or not candidate.endswith(source[-100:]):
  raise ValueError("Unexpected Ruby source patch result")
 return candidate

def admissible(before,after):
 if before["scenarios"]!=72 or after["scenarios"]!=72:return False
 if after["passed"]<=before["passed"]:return False
 if after["failed"]>before["failed"]:return False
 if after["unverified_promises"]!=0:return False
 # Require fixing the 12 financing issues without sacrificing other families.
 return (after["by_family"]["financing"]["passed"]==12
         and all(after["by_family"][k]["passed"]>=before["by_family"][k]["passed"]
                 for k in sales.FAMILIES))

def evaluate():
 source=sales.lab.BOT.read_text()
 proposed=create_candidate(source)
 before,_=sales.run(source=source,persist=False)
 after,_=sales.run(source=proposed,persist=False)
 assessment={"at":datetime.now(timezone.utc).isoformat(),
  "status":"rejected","review_only":True,"deployed":False,
  "public_messages_sent":0,"real_inventory_modified":False,
  "baseline_sha256":hashlib.sha256(source.encode()).hexdigest(),
  "candidate_sha256":hashlib.sha256(proposed.encode()).hexdigest(),
  "baseline_sales":before["passed"],
  "candidate_sales":after["passed"],
  "sales_total":after["scenarios"],
  "baseline_financing":before["by_family"]["financing"]["passed"],
  "candidate_financing":after["by_family"]["financing"]["passed"],
  "unsafe_claims":after["unverified_promises"]}
 if not admissible(before,after):
  assessment["reason"]="sales_candidate_not_better"
 elif not patch_proposer.syntax_only(proposed):
  assessment["reason"]="ruby_syntax_failed"
 else:
  regressions=ruby_gates(proposed)
  assessment["ruby_regressions"]=regressions
  if regressions.get("status")!="passed" or regressions.get("total",0)<117:
   assessment["reason"]="ruby_regressions_failed"
  else:
   base_stock=stock_gate(source=source)
   new_stock=stock_gate(source=proposed)
   assessment["inventory_gate"]={"baseline_failures":base_stock["failed"],
     "candidate_failures":new_stock["failed"],
     "tested":new_stock["scenario_count"],
     "unsafe_claims":new_stock["safety_violations"]}
   if (new_stock["scenario_count"]<108 or
       new_stock["failed"]>base_stock["failed"] or
       new_stock["safety_violations"]!=0):
    assessment["reason"]="inventory_regression_detected"
   else:
    unseen_base=financing_holdout.verify(source=source)
    unseen_candidate=financing_holdout.verify(source=proposed)
    assessment["unseen_financing"]={
      "total":unseen_candidate["total"],"baseline_passed":unseen_base["passed"],
      "candidate_passed":unseen_candidate["passed"]}
    if (unseen_candidate["total"]!=48 or
        unseen_candidate["passed"]!=48 or
        unseen_candidate["passed"]<unseen_base["passed"]):
     assessment["reason"]="unseen_financing_regression"
    else:
     STAGE.mkdir(mode=0o700,parents=True,exist_ok=True)
     path=STAGE/("financing-"+assessment["candidate_sha256"][:18]+".rb")
     fd,temp=tempfile.mkstemp(dir=STAGE,prefix=".review-")
     try:
      with os.fdopen(fd,"w") as f:
       f.write(proposed);f.flush();os.fsync(f.fileno())
      os.chmod(temp,0o600);os.replace(temp,path)
     finally:
      if os.path.exists(temp):os.unlink(temp)
     assessment["status"]="review_ready_not_deployed"
     assessment["stage_file"]=path.name
 _atomic_json(REVIEW,assessment)
 return assessment

def main():
 import argparse
 p=argparse.ArgumentParser()
 g=p.add_mutually_exclusive_group(required=True)
 g.add_argument("--run",action="store_true")
 g.add_argument("--status",action="store_true")
 args=p.parse_args()
 if args.status:print(json.dumps(_load(REVIEW,{"status":"not_run"}),ensure_ascii=False));return 0
 a=evaluate()
 print(json.dumps(a,ensure_ascii=False))
 return 0 if a["status"]=="review_ready_not_deployed" else 1
if __name__=="__main__":
 raise SystemExit(main())
