#!/usr/bin/env python3
"""Pilot-only bounded self-improvement from audited conversation defects.

Only finite reviewed playbooks, not LLM-generated arbitrary code.
Applies to Chatwoot conversation #3 ONLY. Tests; backup; atomic replace; rollback.
"""
import base64
from datetime import datetime,timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

from quality_auditor import _load,_atomic_json,FINDINGS,STATE,REPORT,summarize,normalize

LIVE=Path("/opt/softmobile-waha-test/sales-bot-v2.rb")
ROOT=Path("/opt/softmobile-waha-test/laboratorio-ia")
DATA=ROOT/"quality"
HISTORY=DATA/"autofix-history.json"
PACK=DATA/"auto-policy-rules.json"
REGRESSION=DATA/"test_quality_flows.rb"
HISTORICAL=DATA/"test_historical_replay.rb"
BACKUPS=Path("/opt/softmobile-waha-test/quality-backups")
LOCK=DATA/"autofix.lock"
TIMER="softmobile-waha-catalog-notes.timer"
SERVICE="softmobile-waha-catalog-notes.service"
BEG="  # SM_AUTO_POLICY_BEGIN"
END="  # SM_AUTO_POLICY_END"
HOOK_BEG="      # SM_AUTO_POLICY_HOOK_BEGIN"
HOOK_END="      # SM_AUTO_POLICY_HOOK_END"
DAILY_CAP=2
ALLOWED_REPLIES={
 "transferencias": "Entendido, preferís pagar por transferencia. Un asesor confirmará precio y disponibilidad y luego te dará los datos oficiales de cobro.",
 "transferencia": "Entendido, preferís pagar por transferencia. Un asesor confirmará precio y disponibilidad y luego te dará los datos oficiales de cobro.",
 "tarjeta": "Perfecto, preferís pagar con tarjeta. El asesor verificará el precio y las condiciones disponibles antes de coordinar.",
 "en efectivo": "Perfecto, anoté pago en efectivo. Un asesor confirmará precio y disponibilidad antes de coordinar."
}
CONFIRM_SAFE=re.compile(
 r"(?:est[aá] disponible|tenemos existencias|te lo reserv[eé]|te lo apart[eé]|"
 r"ya se aprob[oó]|pago confirmado|env[ií]o confirmado|precio final es|"
 r"l\.?\s*\d{3,}|\b(?:c[oó]digo|contrase[nñ]a|pin|cvv)\b)",re.I
)
DECLARATIONS=r'''  # SM_AUTO_POLICY_BEGIN
  SM_AUTO_POLICY_PACK = JSON.parse(Base64.strict_decode64("PACK_BASE64")).freeze
  # SM_AUTO_POLICY_END

  # Sandboxed business rule pack: literal normalized text + fixed context gate.
  # No Ruby or regex from AI or from untrusted conversation data is evaluated.
  def self.sm_auto_policy(raw,intent,previous_bot)
    return nil unless [:payments].include?(intent)
    chosen=normalize(raw)
    prev=previous_bot.to_s
    SM_AUTO_POLICY_PACK.each do |rule|
      next unless chosen==rule.fetch("when")
      next unless intent.to_s==rule.fetch("intent")
      gate=rule.fetch("previous_gate")
      valid=gate=="checkout" && prev.match?(/(?:ser[ií]a para retirar|ser[ií]a con env[ií]o|tengo anotado|confirmar disponibilidad)/i)
      next unless valid
      return {reply:rule.fetch("reply"),note:"AUTOMEJORA PILOTO: verificar modalidad y precio final con asesor.",needs_human:true,intent: :payments,tag:'sm_autofix'}
    end
    nil
  end
'''
HOOK=r'''      # SM_AUTO_POLICY_HOOK_BEGIN
      # Only a narrow, safely-tested improvement for an exact follow-up.
      if (sm_policy=SoftMobileSales.sm_auto_policy(raw,intent_type,previous_bot))
        return sm_policy
      end
      # SM_AUTO_POLICY_HOOK_END
'''

def default_pack():
 return {"version":1,"pilot_conversation_id":3,"rules":[]}

def _safe_rule(rule):
 if not isinstance(rule,dict) or set(rule)!={"when","intent","previous_gate","reply"}:
  raise ValueError("Unexpected rule fields")
 if rule["when"] not in ALLOWED_REPLIES or rule["intent"]!="payments" or rule["previous_gate"]!="checkout":
  raise ValueError("Unsupported or out-of-scope rule")
 if rule["reply"]!=ALLOWED_REPLIES[rule["when"]] or CONFIRM_SAFE.search(rule["reply"]):
  raise ValueError("Unsafe or unverified text")
 return rule

def valid_pack(pack):
 if not isinstance(pack,dict) or pack.get("version")!=1 or pack.get("pilot_conversation_id")!=3:
  raise ValueError("Out-of-scope pack")
 if not isinstance(pack.get("rules"),list) or len(pack["rules"])>8:
  raise ValueError("Invalid pack")
 seen=set()
 for rule in pack["rules"]:
  _safe_rule(rule)
  if rule["when"] in seen:raise ValueError("Duplicate rule")
  seen.add(rule["when"])
 return pack

def embedded_source(src,pack):
 valid_pack(pack)
 if "PILOT_CONVERSATION_ID = 3" not in src or "INBOX_ID = 2" not in src:
  raise RuntimeError("Not an authorized pilot script")
 if "AUTO_REPLY_LIMIT = 1" not in src:
  raise RuntimeError("Public response safety guard altered")
 if "if ENV['SM_MODE']=='test'" not in src:
  raise RuntimeError("Test mode absent")
 b64=base64.b64encode(json.dumps(pack["rules"],ensure_ascii=False,separators=(",",":")).encode()).decode()
 const=DECLARATIONS.replace("PACK_BASE64",b64)
 if BEG in src:
  prefix,rest=src.split(BEG,1)
  if rest.count(END)!=1:raise RuntimeError("Ambiguous policy delimiters")
  anchor="  class << self\n"
  if rest.count(anchor)!=1:raise RuntimeError("Missing original class anchor")
  _,suffix=rest.split(anchor,1)
  src=prefix+const+"\n"+anchor+suffix
 else:
  anchor="  class << self\n"
  if src.count(anchor)!=1:raise RuntimeError("Policy placement anchor missing")
  src=src.replace(anchor,const+"\n"+anchor,1)
 if HOOK_BEG not in src:
  anchor="      if ambiguous_model_choice?(raw) && [:stock,:price,:other,:comparison].include?(intent_type)"
  if src.count(anchor)!=1:raise RuntimeError("Hook anchor missing")
  src=src.replace(anchor,HOOK+"\n"+anchor,1)
 if src.count(BEG)!=1 or src.count(END)!=1 or src.count(HOOK_BEG)!=1:
  raise RuntimeError("Malformed policy code anchors")
 return src

def discover(findings,pack):
 seen={r["when"] for r in pack["rules"]}
 learned=[]
 for case in sorted(findings,key=lambda d:d.get("bot_message_id",0),reverse=True):
  if case.get("status") not in ("pending_human_review","fix_deployed_pending_live_test"):continue
  if case.get("category")!="exact_repeat":continue
  msg=normalize(case.get("customer_sample",""))
  old=normalize(case.get("bot_sample",""))
  if msg not in ALLOWED_REPLIES or msg in seen:continue
  if "seria para retirar" not in old and "seria con envio" not in old and "tengo anotado" not in old:
   continue
  learned.append({"when":msg,"intent":"payments","previous_gate":"checkout","reply":ALLOWED_REPLIES[msg]})
  seen.add(msg)
 return learned

def cmd_run(cmd,stdin=None,timeout=70,env=None):
 return subprocess.run(cmd,input=stdin,text=True,capture_output=True,timeout=timeout,env=env)

def gates(candidate):
 if re.search(r"(?m)^\s*(?:system|eval|exec|class_eval)\b",candidate):
  return {"status":"disallowed_code"}
 separator="\nif ENV['SM_MODE']=='test'\n"
 if separator not in candidate:return {"status":"missing_test_entry"}
 suites=[
  (["docker","exec","-i","-e","SM_MODE=test","softmobile-chatwoot-rails-1","sh","-lc",
    "RAILS_ENV=production bundle exec rails runner -"],candidate,r"BOT_TEST_CASES=(\d+) PASS=(\d+) FAIL=0"),
  (["docker","exec","-i","softmobile-chatwoot-rails-1","sh","-lc",
    "RAILS_ENV=production bundle exec rails runner -"],
    candidate.split(separator)[0]+"\n"+REGRESSION.read_text(),r"SOFTMOBILE_QA_REGRESSION=(\d+)/(\d+) PASS"),
  (["docker","exec","-i","softmobile-chatwoot-rails-1","sh","-lc",
    "RAILS_ENV=production bundle exec rails runner -"],
    candidate.split(separator)[0]+"\n"+HISTORICAL.read_text(),r"HISTORICAL_REPLAY_TOTAL=(\d+) PASS=(\d+) FAIL=0"),
 ]
 checks=[]
 for cmd,code,rx in suites:
  try:r=cmd_run(cmd,stdin=code)
  except (OSError,subprocess.TimeoutExpired):return {"status":"timeout"}
  m=re.search(rx,r.stdout)
  if r.returncode!=0 or not m or m.group(1)!=m.group(2):
   return {"status":"regression_failed"}
  checks.append(int(m.group(1)))
 return {"status":"passed","baseline":checks[0],"regressions":checks[1],"historical_replays":checks[2]}

def scenario_check(src,rule):
 sep="\nif ENV['SM_MODE']=='test'\n"
 test=r'''
inven=[]
ctx=SoftMobileSales.context_from(['Busco el iPhone 15 Pro de 128 negro','Choloma','Retirarlo'])
prev='Perfecto, sería para retirar. Tengo anotado el iPhone 15 Pro de 128GB, en negro, para Choloma. Primero hay que confirmar disponibilidad, precio y punto de retiro.'
r=SoftMobileSales.plan('RULE_TRIGGER',ctx,inven,prev)
raise 'autofix_not_selected' unless r[:tag]=='sm_autofix'
raise 'wrong_reply' unless r[:reply]=='EXPECTED_REPLY'
raise 'unsafe' if r[:reply].match?(/precio final es|tenemos disponible|te lo reservé/i)
raise 'missing_human' unless r[:needs_human]
other=SoftMobileSales.plan('¿Ya pagué por transferencia?',ctx,inven,prev)
raise 'security_bypass' if other[:tag]=='sm_autofix'
puts 'AUTOFIX_SCENARIO_PASS'
'''.replace("RULE_TRIGGER",rule["when"]).replace("EXPECTED_REPLY",rule["reply"])
 r=cmd_run(["docker","exec","-i","softmobile-chatwoot-rails-1","sh","-lc",
      "RAILS_ENV=production bundle exec rails runner -"],src.split(sep)[0]+"\n"+test)
 return r.returncode==0 and "AUTOFIX_SCENARIO_PASS" in r.stdout

def deploy(candidate):
 BACKUPS.mkdir(mode=0o700,parents=True,exist_ok=True)
 stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
 backup=BACKUPS/("sales-bot.autofix."+stamp+".bak")
 current=LIVE.read_bytes()
 oldmode=LIVE.stat().st_mode&0o777
 subprocess.run(["systemctl","stop",TIMER],check=True)
 try:
  for _ in range(30):
   r=subprocess.run(["systemctl","is-active",SERVICE],capture_output=True,text=True)
   if r.stdout.strip()!="active":break
   time.sleep(1)
  else:raise RuntimeError("Bot service busy")
  if current!=LIVE.read_bytes():raise RuntimeError("Concurrent source modification")
  backup.write_bytes(current);backup.chmod(0o600)
  fd,tmp=tempfile.mkstemp(prefix=".sm-autofix-",dir=LIVE.parent)
  try:
   with os.fdopen(fd,"wb") as f:
    f.write(candidate.encode());f.flush();os.fsync(f.fileno())
   os.chmod(tmp,oldmode);os.replace(tmp,LIVE)
  finally:
   if os.path.exists(tmp):os.unlink(tmp)
  if gates(candidate)["status"]!="passed":
   LIVE.write_bytes(current)
   os.chmod(LIVE,oldmode)
   raise RuntimeError("Rollback after post-deploy tests failed")
  return {"status":"deployed","backup_name":backup.name}
 finally:
  subprocess.run(["systemctl","start",TIMER],check=True)

def main():
 import argparse
 p=argparse.ArgumentParser()
 p.add_argument("--run",action="store_true")
 p.add_argument("--dry-run",action="store_true")
 p.add_argument("--status",action="store_true")
 args=p.parse_args()
 if sum([args.run,args.dry_run,args.status])!=1:p.error("Specify exactly one mode")
 if args.status:
  data=_load(HISTORY,[])
  print(json.dumps({"attempts":len(data),"last":data[-1] if data else {}},ensure_ascii=False))
  return 0
 if args.run and os.getenv("SOFTMOBILE_AUTOFIX_ENABLED")!="true":
  print("disabled")
  return 2
 DATA.mkdir(mode=0o700,parents=True,exist_ok=True)
 with open(LOCK,"a+",encoding="utf8") as lock:
  os.fchmod(lock.fileno(),0o600)
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  findings=_load(FINDINGS,[])
  history=_load(HISTORY,[])
  day=datetime.now(timezone.utc).date().isoformat()
  if sum(x.get("day")==day and x.get("status")=="deployed" for x in history)>=DAILY_CAP:
   print("daily_deployment_cap")
   return 0
  current=valid_pack(_load(PACK,default_pack()))
  candidates=discover(findings,current)
  if not candidates:
   print("no_supported_new_rule")
   return 0
  rule=candidates[0]
  next_pack={**current,"rules":current["rules"]+[rule]}
  candidate=embedded_source(LIVE.read_text(),next_pack)
  result={"day":day,"scenario":rule["when"],"source_rule":"bounded_catalog",
          "time":datetime.now(timezone.utc).isoformat()}
  status=gates(candidate)
  result["gate"]=status
  if status["status"]=="passed" and scenario_check(candidate,rule):
   if args.run:
    result.update(deploy(candidate))
    _atomic_json(PACK,next_pack)
    for finding in findings:
     if normalize(finding.get("customer_sample",""))==rule["when"] and finding.get("category")=="exact_repeat":
      finding["status"]="fix_deployed_pending_live_test"
      finding["resolution_note"]="Autofix de patrón acotado: requiere validación con conversación nueva."
    _atomic_json(FINDINGS,findings)
    st=_load(STATE,{})
    report=summarize(st,findings,{"autofix":result,"regression_gate":status})
    _atomic_json(REPORT,report)
   else:result["status"]="dry_run_passed"
  else:result["status"]="rejected_by_tests"
  if args.run:
   history.append(result)
   _atomic_json(HISTORY,history[-100:])
  print(json.dumps(result,ensure_ascii=False))
 return 0

if __name__=="__main__":
 try:sys.exit(main())
 except (RuntimeError,ValueError,OSError,subprocess.CalledProcessError) as exc:
  print("autofix_safe_failure:",type(exc).__name__)
  sys.exit(2)
