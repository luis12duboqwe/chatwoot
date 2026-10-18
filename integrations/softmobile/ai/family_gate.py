#!/usr/bin/env python3
"""Mandatory isolated behavioral gate for SoftMobile bounded fix families.

No production Rails runner, bot subprocess, HTTP, DB or WhatsApp calls.
The candidate source is evaluated in an ephemeral Docker container with
no network, no mounts, read-only root, non-root UID and restricted resources.
"""
import base64
import json
from pathlib import Path
import subprocess
import re
import sandbox_review as sb

SEP="\nif ENV['SM_MODE']=='test'\n"
PERMITTED_FAMILIES=frozenset(("advisor_eta","tracking_followup","prepurchase_inspection","optional_coverage"))
FIXTURES=[
 ("inspection-before-buy","prepurchase_inspection",
    "¿Puedo probar el teléfono antes de comprarlo?",True,["probar","asesor"]),
 ("inspection-before-payment","prepurchase_inspection",
    "¿Puedo revisarlo antes de pagar?",True,["probar","asesor"]),
 ("inspection-samsung","prepurchase_inspection",
    "¿Se puede probar el Samsung S24 antes de pagar?",True,["probar","asesor"]),
 ("optional-insurance","optional_coverage",
    "¿Puedo solicitar un seguro adicional para la pantalla?",True,["confirmado","asesor"]),
 ("optional-warranty","optional_coverage",
    "¿Tienen opción de garantía extendida?",True,["confirmado","asesor"]),
 ("optional-drop","optional_coverage",
    "¿Trae protección para caídas?",True,["confirmado","asesor"]),
 ("optional-extend","optional_coverage",
    "¿Es posible ampliar la garantía?",True,["confirmado","asesor"]),
 ("standard-warranty","none",
    "¿Cuánto dura la garantía estándar de este celular?",False,[]),
 ("already-damaged","none",
    "Ya compré el equipo y se dañó la pantalla; quiero reclamar",False,[]),
 ("request-repair","none",
    "¿Pueden reparar la pantalla del iPhone 15?",False,[]),
 ("photo-request","none",
    "¿Tienen fotos reales del Samsung S24?",False,[]),
 ("price-confirmation","none",
    "¿Cuánto cuesta el iPhone 15 Pro?",False,[]),
 ("stock-confirmation","none",
    "¿Tienen disponible iPhone 15 Pro 256GB negro?",False,[]),
 ("location-inquiry","none",
    "¿Dónde puedo ver el teléfono en tienda?",False,[]),
 ("warranty-repair","none",
    "Mi celular no funciona, necesito aplicar la garantía",False,[])
]
def script_for(source):
 if source.count(SEP)!=1:raise ValueError("Unrecognized bot executable boundary")
 core=source.split(SEP,1)[0]
 rows=[{"id":name,"message":msg,"family":family,"expected":positive,
        "terms":terms} for name,family,msg,positive,terms in FIXTURES]
 data=base64.b64encode(json.dumps(rows,ensure_ascii=False).encode()).decode()
 return "require 'base64'\n"+core+"\n"+f"""
rows=JSON.parse(Base64.strict_decode64('{data}'))
bot=SoftMobileSales
out=rows.map do |r|
  msg=r.fetch('message')
  ctx=bot.context_from(['Busco iPhone 15 Pro de 256GB negro',msg])
  answer=bot.plan(msg,ctx,[],nil)
  {{id:r['id'],intent:answer[:intent].to_s,tag:answer[:tag],
    reply:answer[:reply].to_s,needs_human:!!answer[:needs_human]}}
end
puts 'SM_FAMILY_ISOLATED='+JSON.generate(out)
"""
def run(source,selected,runner=subprocess.run):
 selected=set(selected)
 if not selected<=PERMITTED_FAMILIES:raise ValueError("Not pre-reviewed family")
 payload=script_for(source)
 cmd=["docker","run","-i","--rm","--pull","never","--network","none",
     "--read-only","--cap-drop","ALL","--security-opt","no-new-privileges",
     "--pids-limit","48","--memory","200m","--cpus","0.5",
     "--user","65534:65534","--tmpfs","/tmp:rw,noexec,nosuid,size=8m",
     "--env","HOME=/tmp","--entrypoint","ruby",sb.IMAGE,"-"]
 try:r=runner(cmd,input=payload,text=True,capture_output=True,timeout=60)
 except (OSError,subprocess.TimeoutExpired):return {"status":"timeout"}
 if r.returncode:return {"status":"ruby_failure","output":(r.stderr or "")[-260:]}
 marker="SM_FAMILY_ISOLATED="
 outputs=[line[len(marker):] for line in r.stdout.splitlines() if line.startswith(marker)]
 if len(outputs)!=1:return {"status":"missing_output"}
 try:records=json.loads(outputs[0])
 except (ValueError,TypeError):return {"status":"invalid_output"}
 if not isinstance(records,list) or len(records)!=len(FIXTURES):return {"status":"wrong_result_count"}
 evidence=[]
 for (name,family,_,positive,terms),res in zip(FIXTURES,records):
  if res.get("id")!=name:return {"status":"wrong_result_order"}
  active=family in selected
  target=positive and active
  if target:
   valid=(res.get("intent")==family and res.get("needs_human") is True and
          all(term.casefold() in res.get("reply","").casefold() for term in terms) and
          not re.search(r"(?:garantiza(?:mos|do)?|está aprobado|incluido sin costo|te aseguramos)",res.get("reply",""),re.I))
  else:
   valid=res.get("intent") not in selected
  evidence.append({"id":name,"passed":bool(valid),"positive":target})
 return {"status":"passed" if all(x["passed"] for x in evidence) else "rejected_incorrect_or_regression",
         "total":len(FIXTURES),"passed":sum(x["passed"] for x in evidence),
         "failed":[x["id"] for x in evidence if not x["passed"]],
         "isolated":True,"public_messages_sent":0}

if __name__=="__main__":
 import repair_lab as rl
 import auto_improver as auto
 selected=list(rl.FAMILIES)
 candidate=rl.compile_candidate(auto.LIVE.read_text(),selected)
 print(json.dumps(run(candidate,selected),ensure_ascii=False))
