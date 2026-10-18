#!/usr/bin/env python3
"""Reviewer-authored second candidate; never install bot changes directly."""
import json
import patch_proposer as p
import sandbox_review as sandbox
import synthetic_lab as lab
from quality_auditor import _load,_atomic_json

REPLACEMENT=(
 "        choices=color_options(variant_str)\n"
 "        if choices.any?\n"
 "          data[:color_options]=choices\n"
 "          selection=choices.first\n"
 "          if choices.length>1 && nt.match?(/\\bsi no\\b/)\n"
 "            tail=nt.split(/\\b(?:mejor|prefiero|me gustaria|puedo cambiar a|puedo ver|puedo comprar|me sirve)\\b/).last\n"
 "            selection=color_options(tail).first if tail && tail!=nt\n"
 "            selection=choices.last if nt.scan(/\\bsi no hay\\b/).length>1\n"
 "          end\n"
 "          data[:color]=selection\n"
 "        end\n")

def main():
 issue=p.pick_issue(_load(lab.ISSUES,[]))
 if not issue:raise ValueError("No matching fictitious client bug")
 original=p.BOT.read_text(encoding="utf8")
 proposal={"search":p.COLOR_ANCHOR,"replace":REPLACEMENT,
   "reason":"Reviewer-authored candidate that interprets an explicit alternative only after a conditional 'si no', avoiding changes when the buyer simply compares two colors.",
   "regression_example":"Cliente dice si no hay 512GB negro, mejor 256GB azul. No confundir con prefiero negro pero cuánto cuesta azul."}
 candidate=p.validate_patch(original,proposal)
 if not p.syntax_only(candidate):raise ValueError("Invalid Ruby syntax")
 result=sandbox.compare(original,candidate)
 print("SANDBOX_REVIEW",json.dumps(result,ensure_ascii=False))
 if result["status"]!="behavior_passed":
  print("REJECTED, NO REVIEW DIFF SAVED")
  return 2
 saved=p.stage(original,candidate,proposal,issue)
 saved["status"]="isolated_behavior_passed_human_review_required"
 saved["ruby_source_was_model_generated"]=False
 saved["isolated_behavior"]=result
 saved["live_bot_modified"]=False
 saved["behavior_executed_only_in_network_disabled_container"]=True
 _atomic_json(p.STAGE/(saved["proposal_id"]+".json"),saved)
 print("STAGED",saved["proposal_id"])
 return 0
if __name__=="__main__":raise SystemExit(main())
