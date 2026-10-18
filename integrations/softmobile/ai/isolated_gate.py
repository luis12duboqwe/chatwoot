#!/usr/bin/env python3
"""Run *all* fixed Ruby regressions inside a disposable no-network container."""
import json
import re
import subprocess
from pathlib import Path
import sandbox_review as sb
import auto_improver as fixer

SEPARATOR="\nif ENV['SM_MODE']=='test'\n"
SUITES=[
 ("engine",None,r"BOT_TEST_CASES=(\d+) PASS=(\d+) FAIL=0"),
 ("regression",fixer.REGRESSION,r"SOFTMOBILE_QA_REGRESSION=(\d+)/(\d+) PASS"),
 ("historical",fixer.HISTORICAL,r"HISTORICAL_REPLAY_TOTAL=(\d+) PASS=(\d+) FAIL=0"),
 ("journeys",fixer.JOURNEYS,r"SM_JOURNEYS_TOTAL=(\d+) PASS=(\d+) FAIL=0"),
 ("pilot",fixer.LIVE_JOURNEY,r"SM_LIVE_JOURNEY_TOTAL=(\d+) PASS=(\d+) FAIL=0"),
 ("payment",fixer.SYNTHETIC_PAYMENT,r"SM_AUTOFIX_PAYMENT_MENU_TOTAL=(\d+) PASS=(\d+) FAIL=0"),
 ("future",fixer.FUTURE,r"SM_FUTURE_SCENARIOS_TOTAL=(\d+) PASS=(\d+) FAIL=0"),
]

def gates(candidate,runner=subprocess.run):
 if candidate.count(SEPARATOR)!=1:raise ValueError("missing bot test boundary")
 core,engine=candidate.split(SEPARATOR,1)
 # The production catalog is HTTP-backed. These behavior tests intentionally
 # test dialogue with NO authorized inventory; suppress catalog network reads.
 offline_catalog="\nmodule SoftMobileSales\n  def self.catalog; []; end\nend\n"
 checks={}
 for name,file,pattern in SUITES:
  if file is None:
   script="require 'base64'\n"+core+offline_catalog+SEPARATOR+engine
  else:
   script="require 'base64'\n"+core+offline_catalog+"\n"+Path(file).read_text(encoding="utf8")
  cmd=["docker","run","-i","--rm","--pull","never","--network","none",
       "--read-only","--cap-drop","ALL","--security-opt","no-new-privileges",
       "--pids-limit","48","--memory","200m","--cpus","0.5",
       "--user","65534:65534","--tmpfs","/tmp:rw,noexec,nosuid,size=8m",
       "--env","HOME=/tmp"]
  if name=="engine":cmd+=["--env","SM_MODE=test"]
  cmd+=["--entrypoint","ruby",sb.IMAGE,"-"]
  try:res=runner(cmd,input=script,text=True,capture_output=True,timeout=60)
  except (OSError,subprocess.TimeoutExpired):
   return {"status":"sandbox_timeout","suite":name,"tests":checks}
  m=re.search(pattern,res.stdout)
  if res.returncode or m is None or m.group(1)!=m.group(2):
   return {"status":"sandbox_regression_failed","suite":name,
     "last_output":(res.stderr or res.stdout)[-260:],"tests":checks}
  checks[name]=int(m.group(1))
 return {"status":"passed","tests":checks,"total":sum(checks.values())}

if __name__=="__main__":
 import patch_proposer as pp
 import review_fallback_v2 as review
 original=pp.BOT.read_text()
 candidate=pp.validate_patch(original,{"search":pp.COLOR_ANCHOR,
    "replace":review.REPLACEMENT,"reason":"review","regression_example":"buyer changes color"})
 print("RESULT",json.dumps(gates(candidate),ensure_ascii=False))
