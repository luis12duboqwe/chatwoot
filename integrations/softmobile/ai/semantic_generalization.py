#!/usr/bin/env python3
"""Safer family-level coverage derived from a previously validated learned rule.

Only a fixed, human-reviewed Ruby pattern may cover new paraphrases; Groq
cannot author executable code, Ruby patterns, prices, or business policies.
This candidate is STAGED INERT, never deployed by this program.
"""
import base64,hashlib,json,os,re,subprocess,tempfile
from pathlib import Path
import autonomous_learning as learn
import patch_proposer as pp
from quality_auditor import _load,_atomic_json

DIR=Path(__file__).resolve().parent/"quality"
STAGE=DIR/"semantic-generalization-candidates"
REPORT=DIR/"semantic-generalization-review.json"
NAME="extra_accessory"
SEMANTIC_REPLY="Todavía no puedo confirmarte el precio de la funda u otro accesorio ni ofrecerlo gratis; un asesor debe comprobar si la regalía aplica a ese equipo y cuánto costaría incluirlo."
SIGN="      # SM_GENERALIZED_EXTRA_ACCESSORY_BEGIN"
END="      # SM_GENERALIZED_EXTRA_ACCESSORY_END"
# Static pattern authored as source by engineer, not generated from client/Groq.
# Buyer must mention accessory + price/inclusion, and not involve after-sales, PII,
# payments, defects, financial commitments, other exceptions.
RUBY_RULE=r'''      # SM_GENERALIZED_EXTRA_ACCESSORY_BEGIN
      if t.match?(/\b(?:funda|forro|estuche|protector|vidrio templado|cargador|accesorios?)\b/) &&
         t.match?(/\b(?:precio|cuanto|cuesta|costo|vale|agregar|anadir|incluir|incluida|incluido|adicional|aparte|pagarla|pagarlo)\b/) &&
         !t.match?(/\b(?:reclamo|reclamar|devolucion|reembolso|garantia|dano|danado|defecto|falla|fallo|roto|quebrado|cambio por garantia|mi compra|ya compre|ya pague|pin|cvv|otp|clave|contrasena|banco|tarjeta|transferencia|deposito|reparacion|reparar|pedido|paquete|original|autentico|autentica|genuino|genuina|certificado|certificada)\b/) &&
         t.length<=155
        return {reply:"Todavía no puedo confirmarte el precio de la funda u otro accesorio ni ofrecerlo gratis; un asesor debe comprobar si la regalía aplica a ese equipo y cuánto costaría incluirlo.",
                note:"CONSULTA DE ACCESORIO: verificar unidad y precio; no ofrecer regalos ni prometer accesorios.",
                needs_human:true,intent: :learned_handoff,tag:"sm_semantic_accessory"}
      end
      # SM_GENERALIZED_EXTRA_ACCESSORY_END
'''
# Distinct cases; negative tests must NEVER change. No payment instructions.
POSITIVE=[
 "Quiero agregar una funda de silicona, ¿cuánto cuesta?",
 "¿Cuánto sale añadir un protector para el celular?",
 "¿Me pueden incluir un cargador en el precio?",
 "¿Qué costo tiene una funda adicional?",
 "¿La funda está incluida en el precio del iPhone?",
 "¿Cuánto vale agregar un estuche?",
 "¿Se puede incluir un vidrio templado y cuánto cuesta?",
 "¿Cuánto cuesta el forro si lo llevo junto con el equipo?",
 "¿Puedo agregar accesorios al precio?",
 "¿La funda viene incluida o se paga aparte?"
]
NEGATIVE=[
 "¿Cuánto cuesta el iPhone 15 Pro de 256 GB?",
 "¿Qué garantía tienen los equipos?",
 "¿El cargador incluido es original?",
 "Ya compré mi celular y la funda está dañada, quiero reclamar.",
 "¿Cuánto cuesta reparar mi cargador que falló?",
 "¿Dónde está mi pedido con la funda?",
 "¿Cuál es el PIN de mi tarjeta?",
 "¿Puedo pagar con transferencia?",
 "Quiero un reembolso por la funda rota.",
 "¿Cuánto tarda el envío para Choloma?",
 "Busco Samsung S24 Ultra negro de 256GB.",
 "¿La funda es compatible con iPhone 15 Pro?",
 "¿Puedo cambiar de color el iPhone?",
 "¿Puedo hacer un depósito por mi paquete?",
 "Tengo un reclamo de garantía de un cargador."
]

def build(source,pack):
 learn.validate_pack(pack)
 if not any(rule["family"]==NAME for rule in pack["rules"]):
  raise ValueError("Missing corroborated learning family")
 if source.count(learn.BEG)!=1 or source.count(learn.END)!=1:
  raise ValueError("Missing verified learned code anchors")
 if source.count(SIGN) or source.count(END):
  raise ValueError("Generalization already installed")
 if any(source.count(x)!=1 for x in learn.PILOT):
  raise ValueError("Pilot guard missing")
 return source.replace(learn.END,RUBY_RULE+learn.END,1)

def inspect(source,cases,runner=subprocess.run):
 """All samples in ONE disposable no-network Ruby interpreter."""
 from sandbox_review import IMAGE
 if source.count("\nif ENV['SM_MODE']=='test'\n")!=1:
  raise ValueError("Missing Ruby test boundary")
 core=source.split("\nif ENV['SM_MODE']=='test'\n",1)[0]
 raw=base64.b64encode(json.dumps(cases,ensure_ascii=False).encode()).decode()
 code=("require 'base64'\n"+core+f"""
cases=JSON.parse(Base64.strict_decode64('{raw}'))
raise 'bad number of cases' if cases.length>40
results=cases.map do |msg|
 ctx=SoftMobileSales.context_from([msg])
 decision=SoftMobileSales.plan(msg,ctx,[],nil)
 {{reply:decision[:reply].to_s,tag:decision[:tag].to_s,
   human:!!decision[:needs_human]}}
end
puts 'SM_SEMANTIC_INSPECT='+JSON.generate(results)
""")
 cmd=["docker","run","-i","--rm","--pull","never","--network","none",
      "--read-only","--cap-drop","ALL","--security-opt","no-new-privileges",
      "--pids-limit","48","--memory","200m","--cpus","0.5",
      "--user","65534:65534","--tmpfs","/tmp:rw,noexec,nosuid,size=8m",
      "--env","HOME=/tmp","--entrypoint","ruby",IMAGE,"-"]
 p=runner(cmd,input=code,text=True,capture_output=True,timeout=65)
 if p.returncode:raise RuntimeError("Sandbox Ruby execution failed")
 rows=[json.loads(x.split("SM_SEMANTIC_INSPECT=",1)[1])
       for x in p.stdout.splitlines() if x.startswith("SM_SEMANTIC_INSPECT=")]
 if len(rows)!=1 or len(rows[0])!=len(cases):raise RuntimeError("Bad isolated sample output")
 return rows[0]

def gates(original,candidate,inspect_fn=inspect,regression=None,syntax=None):
 checks={"status":"rejected","positive":len(POSITIVE),"negative":len(NEGATIVE),
         "no_customer_messages":True,"pilot_only":True}
 syntax=syntax or pp.syntax_only
 if not syntax(candidate):
  checks["reason"]="ruby_syntax_failed";return checks
 old=inspect_fn(original,POSITIVE+NEGATIVE)
 new=inspect_fn(candidate,POSITIVE+NEGATIVE)
 desired=SEMANTIC_REPLY
 changed_improved=0
 for b,a in zip(old[:len(POSITIVE)],new[:len(POSITIVE)]):
  if a["reply"]!=desired or a["human"] is not True or a["tag"]!="sm_semantic_accessory":
   checks["reason"]="positive_fails";return checks
  if b["reply"]!=a["reply"]:changed_improved+=1
 if any(a!=b for a,b in zip(old[len(POSITIVE):],new[len(POSITIVE):])):
  checks["reason"]="negative_regression";return checks
 checks["improved_examples"]=changed_improved
 if changed_improved<6:
  checks["reason"]="not_enough_new_coverage";return checks
 if regression is None:
  from isolated_gate import gates as regress
  regression=regress
 total=regression(candidate)
 checks["ruby_regressions"]=total
 checks["status"]="verified_in_sandbox" if total.get("status")=="passed" and total.get("total",0)>=117 else "ruby_regression_failed"
 return checks

def review():
 pack=learn.validate_pack(_load(learn.STORE,learn.empty_pack()))
 original=learn.BOT.read_text()
 candidate=build(original,pack)
 result=gates(original,candidate)
 result["at"]=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
 result["original_sha256"]=hashlib.sha256(original.encode()).hexdigest()
 result["candidate_sha256"]=hashlib.sha256(candidate.encode()).hexdigest()
 result["deployed"]=False
 if result["status"]=="verified_in_sandbox":
  STAGE.mkdir(mode=0o700,parents=True,exist_ok=True)
  file=STAGE/("semantic-"+result["candidate_sha256"][:18]+".rb")
  fd,temp=tempfile.mkstemp(dir=STAGE,prefix=".semantic-")
  try:
   with os.fdopen(fd,"w") as out:out.write(candidate);out.flush();os.fsync(out.fileno())
   os.chmod(temp,0o600);os.replace(temp,file)
  finally:
   if os.path.exists(temp):os.unlink(temp)
  result["stage_file"]=file.name
 _atomic_json(REPORT,result)
 return result

if __name__=="__main__":
 print(json.dumps(review(),ensure_ascii=False))
