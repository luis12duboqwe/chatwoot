#!/usr/bin/env python3
"""Portable offline tests: no live VPS files, real customer data, or credentials."""
import json
import unittest
from unittest.mock import patch

import repair_lab as repair
import family_gate as gate

class SafeCommercialFamiliesTests(unittest.TestCase):
 def setUp(self):
  self.stub=(
   "module SoftMobileSales\n"
   "  INBOX_ID = 2\n"
   "  PILOT_CONVERSATION_ID = 3\n"
   "  AUTO_REPLY_LIMIT = 1\n"
   "  def self.plan(raw,ctx,items,prev=nil)\n"
   "      # SM_AUTO_POLICY_HOOK_END\n"
   "    end\n"
   "end\n"
   "\nif ENV['SM_MODE']=='test'\n"
  )
 def sample(self,category,messages,answers):
  return {"id":"acfc20a1c3eeabb337","at":"2026-10-18T00:00:00Z",
    "category":category,"source":"groq_generated","status":"synthetic_unverified",
    "scenario":{"category":category,"messages":messages},
    "evidence":[{"buyer":m,"bot":b} for m,b in zip(messages,answers)]}
 def test_all_preapproved_categories_have_fixed_source_and_expected_terms(self):
  self.assertEqual(len(repair.FAMILIES),4)
  for lookup in (repair.SAFE_REPLIES,repair.EXPECTED,repair.SIGNATURES):
   self.assertEqual(set(repair.FAMILIES),set(lookup))
  self.assertTrue(set(repair.FAMILIES)<=gate.PERMITTED_FAMILIES)
 def test_inspection_selector_with_fictional_three_turn_fixture(self):
  issue=self.sample("objections",[
   "Me interesa el iPhone 15 Pro",
   "¿Tienen alguna promoción?",
   "¿Puedo probar el teléfono antes de comprarlo?"],
   ["¿De cuántos GB lo buscás?","Las promociones deben confirmarse.",
    "¿Qué capacidad buscás?"])
  choice=repair.eligible([issue],["advisor_eta"])
  self.assertIsNotNone(choice)
  self.assertEqual(choice[2],["prepurchase_inspection"])
 def test_optional_coverage_selector_with_fictional_three_turn_fixture(self):
  issue=self.sample("questions",[
   "Me interesa el iPhone 15 Pro",
   "¿Cuánto dura la garantía?",
   "¿Puedo solicitar un seguro adicional para la pantalla?"],
   ["¿Qué capacidad buscás?","Un asesor confirmará el plazo.",
    "¿En qué ciudad lo necesitás?"])
  choice=repair.eligible([issue],["advisor_eta","prepurchase_inspection"])
  self.assertIsNotNone(choice)
  self.assertEqual(choice[2],["optional_coverage"])
 def test_reviewer_does_not_promote_unverified_status(self):
  issue=self.sample("objections",["¿Qué modelo?", "iPhone 15",
       "¿Puedo probar el teléfono antes de comprarlo?"],
       ["¿Qué equipo buscás?","¿Qué capacidad?","¿De cuántos GB?"])
  issue["status"]="discarded_invalid_scenario"
  self.assertIsNone(repair.eligible([issue],["advisor_eta"]))
 def test_preapproved_source_is_literal_not_ai_code(self):
  for family in ("prepurchase_inspection","optional_coverage"):
   txt=repair.SAFE_REPLIES[family]
   for bad in ("eval(", "system(", "Process.", "ENV[", "send(", "File."):
    self.assertNotIn(bad,txt)
   self.assertIn("needs_human:true",txt)
   self.assertIn("asesor",txt)
 def test_compiler_embeds_all_families_and_rejects_unknown(self):
  source=repair.compile_candidate(self.stub,list(repair.FAMILIES))
  self.assertEqual(source.count(repair.BEG),1)
  self.assertEqual(source.count(repair.END),1)
  for family in repair.FAMILIES:
   expected="tracking" if family=="tracking_followup" else family
   self.assertIn("intent: :"+expected,source)
  with self.assertRaises(ValueError):
   repair.compile_candidate(self.stub,["unknown_dynamic_ruby"])
 def test_isolation_flags_and_no_prod_container(self):
  called=[]
  def runner(cmd,**kw):
   called.append(cmd)
   class Result:returncode=0;stderr=""
   out=Result()
   records=[]
   for name,family,msg,pos,terms in gate.FIXTURES:
    is_target=family in ("prepurchase_inspection","optional_coverage") and pos
    records.append({"id":name,
      "intent":family if is_target else "other",
      "reply":"asesor confirmado probar confirmado" if is_target else "revisión normal",
      "needs_human":is_target})
   out.stdout="SM_FAMILY_ISOLATED="+json.dumps(records)+"\n"
   return out
  compiled=repair.compile_candidate(self.stub,list(repair.FAMILIES))
  result=gate.run(compiled,list(repair.FAMILIES),runner=runner)
  self.assertEqual(result["status"],"passed")
  self.assertEqual(len(called),1)
  argv=called[0]
  for flag in ("--network","none","--read-only","--cap-drop","--user","65534:65534"):
   self.assertIn(flag,argv)
  self.assertNotIn("softmobile-chatwoot-rails-1",argv)
  self.assertNotIn("-v",argv)
 def test_missing_human_handoff_rejected(self):
  def runner(cmd,**kw):
   class Result:returncode=0;stderr=""
   r=Result()
   records=[{"id":name,"intent":family if positive else "other",
      "needs_human":False,"reply":"asesor confirmado probar confirmado"}
     for name,family,msg,positive,terms in gate.FIXTURES]
   r.stdout="SM_FAMILY_ISOLATED="+json.dumps(records)
   return r
  candidate=repair.compile_candidate(self.stub,list(repair.FAMILIES))
  result=gate.run(candidate,list(repair.FAMILIES),runner=runner)
  self.assertEqual(result["status"],"rejected_incorrect_or_regression")
  self.assertGreater(len(result["failed"]),0)
 def test_unknown_family_is_blocked_before_execution(self):
  with self.assertRaises(ValueError):
   gate.run(self.stub,["credit_approval"],runner=lambda *a,**kw:None)
 def test_fixed_replies_never_guarantee_insurance_or_stock(self):
  for family in ("prepurchase_inspection","optional_coverage"):
   txt=repair.SAFE_REPLIES[family].lower()
   for unsafe in ("reembolso garantizado","te lo reservé","cobertura incluida",
    "seguro activado","tu compra está confirmada"):
    self.assertNotIn(unsafe,txt)

if __name__=="__main__":unittest.main()
