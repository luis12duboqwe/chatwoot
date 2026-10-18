#!/usr/bin/env python3
"""Reviewer-authored fallback proposal; never execute or install Ruby."""
import json
from pathlib import Path
import patch_proposer as p
import synthetic_lab as lab
from quality_auditor import _atomic_json,_load

def main():
 issue=p.pick_issue(_load(lab.ISSUES,[]))
 if not issue:raise ValueError("No matching fictional buyer dialogue")
 src=p.BOT.read_text(encoding="utf8")
 replacement=(
  "        choices=color_options(variant_str)\n"
  "        if choices.any?\n"
  "          data[:color_options]=choices\n"
  "          is_fallback=choices.length>1 && nt.match?(/\\b(?:si no hay|si no tienen|si no|mejor|prefiero)\\b/)\n"
  "          data[:color]=is_fallback ? choices.last : choices.first\n"
  "        end\n")
 proposal={"search":p.COLOR_ANCHOR,"replace":replacement,
 "reason":"Propuesta determinística para revisión: al mencionar una alternativa descartada seguida de otra preferida, evitar seleccionar el primer color de la frase.",
 "regression_example":"Si no hay 512GB negro, mejor 256GB azul. Si no hay 256GB azul, preferir 128GB rojo. Comparar con la selección anterior."}
 candidate=p.validate_patch(src,proposal)
 if not p.syntax_only(candidate):raise ValueError("Invalid Ruby syntax")
 report=p.stage(src,candidate,proposal,issue)
 report["status"]="trusted_fallback_source_pending_human_review"
 report["ruby_source_was_model_generated"]=False
 report["behavior_not_executed"]=True
 _atomic_json(p.STAGE/(report["proposal_id"]+".json"),report)
 _atomic_json(p.SUMMARY,{"status":report["status"],"proposal_id":report["proposal_id"],"pilot_unchanged":True})
 print(json.dumps({"status":report["status"],"issue_id":issue["id"],"proposal_id":report["proposal_id"],
 "syntax_only_passed":True,"model_code_executed":False},ensure_ascii=False))
if __name__=="__main__":main()