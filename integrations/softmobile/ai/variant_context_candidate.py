#!/usr/bin/env python3
"""Review-only contextual preference fix based on V3, without deployment."""
import hashlib,json
from pathlib import Path
from quality_auditor import _load,_atomic_json
import context_accuracy_lab as memory
import offline_issue_replay as replay

ROOT=Path(__file__).resolve().parent
QA=ROOT/"quality"
REPORT=QA/"variant-context-review.json"
STAGE=QA/"variant-context-candidates"
V3_SHA="d58682904e798606ede7dca3815fee8044f00f5efa87eb2f86220b3cfa520772"

CAP_OLD="    def capacity(s)\n      t = normalize(s)\n"
CAP_NEW="""    def capacity(s)
      t = normalize(s)
      explicit=t.match(/\\b(?:prefiero|me quedo con|elijo|mejor quiero|quiero mejor)\\s+(?:el |la |de |con )?(32|64|128|256|512)\\s*(?:gb|gigas?)\\b/)
      return "#{explicit[1]}GB" if explicit
"""
COL_OLD="""        if choices.any?
          data[:color_options]=choices
          data[:color]=choices.first
        end"""
COL_NEW="""        if choices.any?
          data[:color_options]=choices
          # Explicit old-to-new color corrections outrank mentioned old finishes.
          changed=nt.match?(/\\b(?:cambiar|cambiarlo|cambio|cambie|pasar)\\b/) &&
                  nt.match?(/\\b(?:a|por)\\s+(?:color )?(?:negro|negra|blanco|blanca|azul|verde|rojo|morado|morada|dorado|dorada|plata|titanio|titanium)\\b/)
          data[:color]=(changed && choices.length>1 && !nt.match?(/\\b(?:o|ambos|cualquiera|en vez de)\\b/)) ? choices.last : choices.first
        end"""

def build(source):
 if not isinstance(source,str) or source.count(CAP_OLD)!=1 or source.count(COL_OLD)!=1:
  raise ValueError("Unexpected baseline source; cannot patch")
 return source.replace(CAP_OLD,CAP_NEW,1).replace(COL_OLD,COL_NEW,1)

def run():
 stage=_load(QA/"combined-pilot-review.json",{})
 if stage.get("status")!="verified_staged" or stage.get("candidate_sha256")!=V3_SHA:
  raise ValueError("Expected V3 evidence unavailable")
 p=QA/"combined-pilot-candidates"/stage["stage_file"]
 source=p.read_text()
 if hashlib.sha256(source.encode()).hexdigest()!=V3_SHA:
  raise ValueError("V3 bytes differ")
 candidate=build(source)
 base=memory.evaluate(source=source)
 result=memory.evaluate(source=candidate)
 out={"status":"not_approved","at":result["at"],
      "base_sha256":V3_SHA,"candidate_sha256":hashlib.sha256(candidate.encode()).hexdigest(),
      "context_before":base,"context_after":result,"review_only":True,
      "deployed":False,"independent_ai_approval":False,"public_messages_sent":0}
 if result["passed"]<=base["passed"]:
  out["reason"]="context_not_improved"
 else:
  STAGE.mkdir(parents=True,exist_ok=True,mode=0o700)
  filename="context-"+out["candidate_sha256"][:18]+".rb"
  path=STAGE/filename
  path.write_text(candidate);path.chmod(0o600)
  out["stage_file"]=filename
  out["status"]="needs_full_regression"
 _atomic_json(REPORT,out)
 return out

if __name__=="__main__":
 print(json.dumps(run(),ensure_ascii=False))
