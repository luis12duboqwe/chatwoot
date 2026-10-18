#!/usr/bin/env python3
"""Offline checks proving Ruby review cannot escape isolated execution gates."""
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

import sandbox_review as s
import isolated_gate as gate
import patch_proposer as proposer

class SandboxReviewTests(unittest.TestCase):
 def test_runner_security_options(self):
  calls=[]
  def fake_runner(argv,**opts):
   calls.append((argv,opts))
   class Result:returncode=0
   r=Result()
   r.stdout=s.MARKER+'[{"id":"sample","capacity":"256GB","color":"Azul"}]\n'
   r.stderr=""
   return r
  scenario=[("sample",["Busco iPhone 15 256GB azul"],"256GB","Azul")]
  response=s.isolated_run("module SoftMobileSales;end\nif ENV['SM_MODE']=='test'\n",scenario,runner=fake_runner)
  self.assertEqual(len(response),1)
  argv,opts=calls[0]
  for token in ("--network","none","--read-only","--cap-drop","ALL",
    "--security-opt","no-new-privileges","--pids-limit","--memory",
    "--cpus","--user","65534:65534","--pull","never"):
   self.assertIn(token,argv)
  self.assertNotIn("--volume",argv)
  self.assertNotIn("-v",argv)
  self.assertNotIn("--privileged",argv)
  self.assertIn("--rm",argv)
  self.assertIn("-i",argv)
  self.assertIn("require 'base64'",opts["input"])
 def test_missing_or_malformed_output_blocks_proposal(self):
  class Response:returncode=0;stdout="";stderr=""
  with self.assertRaises(RuntimeError):
   s.isolated_run("module SoftMobileSales;end\nif ENV['SM_MODE']=='test'\n",
    s.SCENARIOS[:1],runner=lambda *a,**k:Response())
 def test_compares_complete_customer_cases_in_both_versions(self):
  names=[c[0] for c in s.SCENARIOS]
  def rows(kind):
   x=[{"id":name,"capacity":cap,"color":color}
      for name,_,cap,color in s.SCENARIOS]
   if kind=="base":x[0]["color"]="Azul"
   return x
  with patch.object(s,"isolated_run",side_effect=[rows("base"),rows("better")]):
   report=s.compare("base","better")
  self.assertEqual(report["status"],"behavior_passed")
  self.assertEqual(report["regressed"],[])
  self.assertIn("initial-model",report["fixed"])
  with patch.object(s,"isolated_run",side_effect=[rows("better"),rows("base")]):
   report=s.compare("base","worse")
  self.assertEqual(report["status"],"rejected_regression_or_no_improvement")
  self.assertIn("initial-model",report["regressed"])
 def test_rejects_unexpected_diff_paths(self):
  base="PILOT_CONVERSATION_ID = 3\n"+proposer.START+("      data[:color]=nil\n"*18)+proposer.STOP+"\n"
  malformed=[
   "--- a/../../etc/password\n+++ b/sales-bot-v2.rb\n@@ -1 +1 @@\n-a\n+b\n",
   "--- a/sales-bot-v2.rb\n+++ b/sales-bot-v2.rb\n@@ -1 +1 @@\n-a\n+b\n@@ -3 +3 @@\n-c\n+d\n",
   "--- a/sales-bot-v2.rb\n+++ b/sales-bot-v2.rb\n@@ -1 +1 @@\n-a\n+b\n+require 'socket'\n"
  ]
  for diff in malformed:
   with self.subTest(diff=diff[:28]),self.assertRaises(ValueError):
    s.parse_diff(diff,base)
 def test_production_scripts_cannot_be_in_isolated_payload(self):
  with self.assertRaises(ValueError):
   s.prepare_script("module SoftMobileSales; Message.where(:id => 3);end\nif ENV['SM_MODE']=='test'\n",
      s.SCENARIOS[:1])
 def test_isolated_full_gate_never_uses_active_container_exec(self):
  observed=[]
  class Resp:
   returncode=0
   stderr=""
   stdout=("BOT_TEST_CASES=57 PASS=57 FAIL=0\n"
    "SOFTMOBILE_QA_REGRESSION=5/5 PASS\n"
    "HISTORICAL_REPLAY_TOTAL=7 PASS=7 FAIL=0\n"
    "SM_JOURNEYS_TOTAL=20 PASS=20 FAIL=0\n"
    "SM_LIVE_JOURNEY_TOTAL=11 PASS=11 FAIL=0\n"
    "SM_AUTOFIX_PAYMENT_MENU_TOTAL=2 PASS=2 FAIL=0\n"
    "SM_FUTURE_SCENARIOS_TOTAL=15 PASS=15 FAIL=0\n")
  def runner(cmd,**kwargs):
   observed.append(cmd)
   self.assertEqual(cmd[0:2],["docker","run"])
   self.assertIn("--network",cmd)
   self.assertIn("none",cmd)
   self.assertNotIn("softmobile-chatwoot-rails-1",cmd)
   self.assertIn("--read-only",cmd)
   return Resp()
  sample="module SoftMobileSales;end\n"+gate.SEPARATOR+"  puts 'test'\n"
  result=gate.gates(sample,runner=runner)
  self.assertEqual(result["status"],"passed")
  self.assertEqual(result["total"],117)
  self.assertEqual(len(observed),7)
 def test_gate_failure_is_not_promotable(self):
  class Failed:
   returncode=1
   stderr="No internet allowed"
   stdout=""
  sample="module SoftMobileSales;end\n"+gate.SEPARATOR+"  puts 'test'\n"
  r=gate.gates(sample,runner=lambda *a,**kw:Failed())
  self.assertEqual(r["status"],"sandbox_regression_failed")
  self.assertEqual(r["suite"],"engine")

if __name__=="__main__":unittest.main()
