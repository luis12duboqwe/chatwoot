#!/usr/bin/env python3
"""Boundary and routing tests for verified commercial response families."""
import unittest
from unittest.mock import patch
import repair_lab as repair
import family_gate as gate
import synthetic_lab as synthetic
import json

class SafeCommercialFamiliesTests(unittest.TestCase):
 def test_four_reviewed_families(self):
  self.assertEqual(len(repair.FAMILIES),4)
  self.assertEqual(set(repair.FAMILIES),set(repair.SAFE_REPLIES))
  self.assertEqual(set(repair.FAMILIES),set(repair.EXPECTED))
  self.assertEqual(set(repair.FAMILIES),set(repair.SIGNATURES))
  self.assertTrue(set(repair.FAMILIES)<=gate.PERMITTED_FAMILIES)
 def test_prepurchase_issue_selector_recognizes_real_lab_finding(self):
  issues=synthetic._load(synthetic.ISSUES,[])
  record=next(x for x in issues if x["id"]=="db278a3db2956d4a69")
  chosen=repair.eligible([record],["advisor_eta"])
  self.assertIsNotNone(chosen)
  self.assertEqual(chosen[2],["prepurchase_inspection"])
 def test_optional_coverage_selector_recognizes_real_lab_finding(self):
  issues=synthetic._load(synthetic.ISSUES,[])
  record=next(x for x in issues if x["id"]=="186c39b4bbd27bd73e")
  chosen=repair.eligible([record],["advisor_eta","prepurchase_inspection"])
  self.assertIsNotNone(chosen)
  self.assertEqual(chosen[2],["optional_coverage"])
 def test_unverified_source_never_promoted(self):
  issues=synthetic._load(synthetic.ISSUES,[])
  issue=next(x for x in issues if x["id"]=="db278a3db2956d4a69")
  other=dict(issue,status="synthetic_no_issue_observed")
  self.assertIsNone(repair.eligible([other],["advisor_eta"]))
 def test_selector_source_is_literal_not_ai_authored(self):
  for family in ("prepurchase_inspection","optional_coverage"):
   txt=repair.SAFE_REPLIES[family]
   self.assertNotIn("eval(",txt)
   self.assertNotIn("system(",txt)
   self.assertNotIn("Process.",txt)
   self.assertNotIn("ENV[",txt)
   self.assertNotIn("send(",txt)
   self.assertIn("needs_human:true",txt)
   self.assertTrue(all(token.lower() in txt.lower() for token in ("asesor","confirm")))
 def test_compile_embeds_all_and_rejects_unknown_family(self):
  src=repair.fixer.LIVE.read_text()
  new=repair.compile_candidate(src,list(repair.FAMILIES))
  self.assertEqual(new.count(repair.BEG),1)
  for family in repair.FAMILIES:
   expected="tracking" if family=="tracking_followup" else family
   self.assertIn("intent: :"+expected,new)
  with self.assertRaises(ValueError):repair.compile_candidate(src,["brand_new_ruby"])
 def test_safe_sandbox_never_mounts_production(self):
  response={"status":"passed","total":len(gate.FIXTURES),"passed":len(gate.FIXTURES)}
  seen=[]
  def dummy(cmd,**opts):
   seen.append(cmd)
   class R:returncode=0;stderr=""
   obj=R()
   actual=[]
   for name,category,msg,is_positive,terms in gate.FIXTURES:
    if category in ("prepurchase_inspection","optional_coverage") and is_positive:
     actual.append({"id":name,"intent":category,"reply":"asesor confirmado probar confirmado","needs_human":True})
    else:actual.append({"id":name,"intent":"other","reply":"respuesta","needs_human":False})
   obj.stdout="SM_FAMILY_ISOLATED="+json.dumps(actual)
   return obj
  source=repair.compile_candidate(repair.fixer.LIVE.read_text(),list(repair.FAMILIES))
  result=gate.run(source,list(repair.FAMILIES),runner=dummy)
  self.assertEqual(result["status"],"passed")
  self.assertEqual(len(seen),1)
  cmd=seen[0]
  self.assertIn("--network",cmd)
  self.assertIn("none",cmd)
  self.assertIn("--read-only",cmd)
  self.assertIn("--cap-drop",cmd)
  self.assertNotIn("-v",cmd)
  self.assertNotIn("softmobile-chatwoot-rails-1",cmd)
 def test_missing_handoff_rejected(self):
  def dummy(cmd,**opts):
   class R:returncode=0;stderr=""
   obj=R()
   data=[{"id":name,"intent":cat if positive else "other",
       "needs_human":False,"reply":"asesor confirmado probar confirmado"} for name,cat,_,positive,_ in gate.FIXTURES]
   obj.stdout="SM_FAMILY_ISOLATED="+json.dumps(data)
   return obj
  result=gate.run(repair.fixer.LIVE.read_text(),list(repair.FAMILIES),runner=dummy)
  self.assertEqual(result["status"],"rejected_incorrect_or_regression")
  self.assertGreater(len(result["failed"]),0)
 def test_unknown_family_never_executes(self):
  with self.assertRaises(ValueError):
   gate.run(repair.fixer.LIVE.read_text(),["credit_approval"],runner=lambda *x,**y:None)
 def test_business_expectations_dont_promise_stock_or_payment(self):
  for family in ("prepurchase_inspection","optional_coverage"):
   txt=repair.SAFE_REPLIES[family].lower()
   for promise in ("reembolso garantizado","disponible para llevar","te lo reservé","cobertura incluida"):
    self.assertNotIn(promise,txt)

if __name__=="__main__":unittest.main()
