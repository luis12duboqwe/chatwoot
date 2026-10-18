#!/usr/bin/env python3
"""Targeted comparative dialogues in no-network disposable Ruby container."""
from pathlib import Path
import base64
import json
import re
import subprocess
import hashlib
import sys
from datetime import datetime,timezone

import isolated_gate as gate
import sandbox_review as sb
import prepare_conversation_quality as quality
from quality_auditor import _atomic_json

MARKER="SM_SALES_DIALOGUE_RESULTS="
SCENARIOS=[
 {"id":"mix-first","history":["Busco un iPhone 15 Pro negro 128GB"],
  "buyer":"¿Qué garantía tienen y qué accesorios vienen incluidos? Además, ¿el celular es nuevo o usado?",
  "target":"bundle_warranty_accessories","words":["garantía","accesorios","nueva"]},
 {"id":"mix-followup","history":["Busco el iPhone 15 Pro negro 128GB","¿Qué garantía tiene y qué accesorios trae?"],
  "buyer":"¿Podés darme un detalle de la garantía y los accesorios? Si es nuevo quiero cargador y funda",
  "target":"bundle_warranty_accessories","words":["garantía","accesorios","nueva"]},
 {"id":"mix-bundle","history":["Quiero el Samsung S24 Ultra 256GB"],
  "buyer":"¿Cuánta garantía trae y qué cargador o funda viene incluido?",
  "target":"bundle_warranty_accessories","words":["garantía","accesorios"]},
 {"id":"eta-first","history":["Busco un iPhone 15 128GB negro"],
  "buyer":"¿En qué plazo entregan el móvil una vez que lo pago?",
  "target":"shipping_eta","words":["entrega","plazo"]},
 {"id":"eta-first-new","history":["Quiero un Samsung S24 Ultra de 256GB"],
  "buyer":"Quiero saber cuándo recibiré mi nuevo celular, ¿cuál es el tiempo estimado de entrega?",
  "target":"shipping_eta","words":["entrega","plazo"]},
 {"id":"eta-order","history":["Compré un iPhone 15 Pro hace unos días"],
  "buyer":"¿Cuándo llegará mi pedido?",
  "target":"order_delivery_status","words":["pedido","guía"]},
 {"id":"eta-variant","history":["Quiero cambiar el color del iPhone 15 a negro","El negro viene con 128GB"],
  "buyer":"¿Qué tiempo tardaría el cambio?",
  "target":"variant_change_eta","words":["variante","plazo"]},
 {"id":"negative-warranty","history":["Busco iPhone 15 Pro negro 128GB"],
  "buyer":"¿Cuánto dura la garantía estándar?",
  "target":None},
 {"id":"negative-accessories","history":["Busco iPhone 15 Pro negro 128GB"],
  "buyer":"¿Qué accesorios trae el teléfono?",
  "target":None},
 {"id":"negative-photo","history":["Busco iPhone 15 Pro 128GB negro"],
  "buyer":"¿Tienen fotos reales?",
  "target":None},
 {"id":"negative-stock","history":["Busco iPhone 15 Pro 128GB negro"],
  "buyer":"¿Tienen disponible el iPhone 15 Pro de 128GB negro?",
  "target":None},
 {"id":"negative-finance","history":["Busco iPhone 15 Pro negro 128GB"],
  "buyer":"¿Aceptan tarjetas a 3 meses sin intereses?",
  "target":None},
 {"id":"negative-complaint","history":["Compré un iPhone 15 hace un mes"],
  "buyer":"Mi equipo se dañó y quiero reclamar garantía.",
  "target":None},
 {"id":"negative-tracking","history":["Compré un iPhone 15 hace una semana"],
  "buyer":"¿Cómo puedo rastrear mi paquete?",
  "target":None},
 {"id":"negative-repair","history":["Busco reparación de iPhone"],
  "buyer":"¿Cuánto tardan en cambiar una pantalla?",
  "target":None},
 {"id":"negative-shipping-damage","history":["Compré un iPhone 15"],
  "buyer":"¿Qué pasa si el envío llega dañado?",
  "target":None}
]
def sandbox_answers(source,runner=subprocess.run):
 if source.count("\nif ENV['SM_MODE']=='test'\n")!=1:raise ValueError("Bot source has invalid test boundary")
 core=source.split("\nif ENV['SM_MODE']=='test'\n",1)[0]
 request=[{"id":x["id"],"messages":x["history"],"buyer":x["buyer"]} for x in SCENARIOS]
 encoded=base64.b64encode(json.dumps(request,ensure_ascii=False).encode()).decode()
 script="require 'base64'\n"+core+f"""
data=JSON.parse(Base64.strict_decode64('{encoded}'))
result=data.map do |row|
  ctx=SoftMobileSales.context_from(row.fetch('messages')+[row.fetch('buyer')])
  a=SoftMobileSales.plan(row.fetch('buyer'),ctx,[],nil)
  {{id:row.fetch('id'),intent:a[:intent].to_s,reply:a[:reply].to_s,
    needs_human:!!a[:needs_human]}}
end
puts '{MARKER}'+JSON.generate(result)
"""
 cmd=["docker","run","-i","--rm","--pull","never","--network","none",
      "--read-only","--cap-drop","ALL","--security-opt","no-new-privileges",
      "--pids-limit","48","--memory","200m","--cpus","0.5","--user","65534:65534",
      "--tmpfs","/tmp:rw,noexec,nosuid,size=8m","--env","HOME=/tmp",
      "--entrypoint","ruby",sb.IMAGE,"-"]
 p=runner(cmd,input=script,text=True,capture_output=True,timeout=60)
 if p.returncode:raise RuntimeError("Sandbox error "+p.stderr[-200:])
 lines=[l[len(MARKER):] for l in p.stdout.splitlines() if l.startswith(MARKER)]
 if len(lines)!=1:raise RuntimeError("Missing sandbox result")
 return {x["id"]:x for x in json.loads(lines[0])}
def compare(original,candidate):
 before=sandbox_answers(original);after=sandbox_answers(candidate)
 fixes=[];regressions=[];failures=[];unchanged_negatives=[]
 for case in SCENARIOS:
  key=case["id"];old=before[key];new=after[key]
  if case["target"]:
   valid=(new["intent"]==case["target"] and new["needs_human"] and
      all(word.lower() in new["reply"].lower() for word in case["words"]) and
      not re.search(r"\b(?:en|dentro de)\s+\d+\s*(?:horas|dias|días)\b",new["reply"],re.I))
   was_correct=old["intent"]==case["target"]
   if valid and not was_correct:fixes.append(key)
   elif not valid:failures.append(key)
  else:
   # Only these explicit intents may change. All other historic intents
   # and reply text must remain bit-for-bit identical.
   if old!=new:regressions.append(key)
   else:unchanged_negatives.append(key)
 return {"status":"review_ready" if len(fixes)>=5 and not regressions and not failures else "rejected",
   "total":len(SCENARIOS),"targeted_fixed":fixes,"unmet_targets":failures,
   "regressions":regressions,"unchanged_non_targets":len(unchanged_negatives),
   "candidate_not_deployed":True,"public_messages_sent":0}
if __name__=="__main__":
 from pathlib import Path
 live=quality.LIVE.read_text()
 staged=(quality.STAGE/"sales-bot-composite-sales-stage.rb").read_text()
 comparison=compare(live,staged)
 suite=gate.gates(staged) if comparison["status"]=="review_ready" else {"status":"skipped"}
 output={"at":datetime.now(timezone.utc).isoformat(),"comparison":comparison,
  "ruby_gate":suite,"base_sha256":hashlib.sha256(live.encode()).hexdigest(),
  "candidate_sha256":hashlib.sha256(staged.encode()).hexdigest(),
  "approved_for_production":False}
 dest=quality.STAGE/"conversation-quality-review-report.json"
 _atomic_json(dest,output)
 print(json.dumps(output,ensure_ascii=False))
 sys.exit(0 if comparison["status"]=="review_ready" and suite.get("status")=="passed" else 2)
