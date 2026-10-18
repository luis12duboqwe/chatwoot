#!/usr/bin/env python3
"""Independent full regression gate for the review-only context candidate."""
import hashlib,json
from pathlib import Path
from quality_auditor import _load,_atomic_json
import variant_context_candidate as variant
import context_accuracy_lab as context
import offline_issue_replay as replay
import conversion_training_lab as sales
import inventory_quality_lab as stock
import financing_holdout as finance
from isolated_gate import gates as ruby

QA=Path(__file__).resolve().parent/"quality"
OUT=QA/"variant-context-full-review.json"

def validate():
 v=_load(variant.REPORT,{})
 b=_load(QA/"combined-pilot-review.json",{})
 if v.get("status")!="needs_full_regression" or b.get("status")!="verified_staged":
  raise ValueError("Missing safe staged source")
 old=(QA/"combined-pilot-candidates"/b["stage_file"]).read_text()
 current=(variant.STAGE/v["stage_file"]).read_text()
 if hashlib.sha256(current.encode()).hexdigest()!=v.get("candidate_sha256"):
  raise ValueError("Candidate file altered")
 if current!=variant.build(old):
  raise ValueError("Candidate differs from fixed source patch")
 check=ruby(current)
 base_stock=stock.evaluate(source=old)
 new_stock=stock.evaluate(source=current)
 before,_=sales.run(source=old,persist=False)
 after,_=sales.run(source=current,persist=False)
 hold=finance.verify(source=current)
 mem=context.evaluate(source=current)
 diff=replay.compare(replay.assess(source=old),replay.assess(source=current))
 status=(check.get("status")=="passed" and check.get("total",0)>=117 and
         new_stock["failed"]<=base_stock["failed"] and new_stock["safety_violations"]==0 and
         after["passed"]>=before["passed"] and after["unverified_promises"]==0 and
         hold["passed"]==hold["total"]==48 and
         mem["passed"]==mem["total"]==8 and diff["new_flags_in_candidate"]==0)
 result={"status":"review_ready_needs_independent_ai" if status else "rejected_after_regressions",
   "base_sha256":v["base_sha256"],"candidate_sha256":v["candidate_sha256"],
   "ruby_regressions":check.get("total"),"stock":new_stock["passed"],
   "sales_before":before["passed"],"sales_after":after["passed"],
   "financing":hold["passed"],"context_choices":mem["passed"],
   "historical_diff":diff,"independent_ai_approved":False,
   "pilot_deployed":False,"public_messages_sent":0,"real_inventory_modified":False}
 _atomic_json(OUT,result)
 return result

if __name__=="__main__":
 v=validate()
 print(json.dumps(v,ensure_ascii=False))
