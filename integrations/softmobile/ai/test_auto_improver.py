#!/usr/bin/env python3
"""Fully offline safety tests for the bounded autonomous pilot self-improver."""
import unittest
from unittest.mock import patch
from pathlib import Path
import auto_improver as a

class AutoImproverTests(unittest.TestCase):
 def setUp(self):
  self.rule={"when":"transferencias","intent":"payments",
             "previous_gate":"checkout","reply":a.ALLOWED_REPLIES["transferencias"]}
  self.pack={"version":1,"pilot_conversation_id":3,"rules":[self.rule]}
 def test_authorized_rule(self):
  self.assertEqual(a.valid_pack(self.pack),self.pack)
 def test_rules_reject_arbitrary_model_code(self):
  for bad in (dict(self.rule,reply="eval('system')"),
              dict(self.rule,when="tarjeta bancaria"),
              dict(self.rule,intent="payment_verification"),
              dict(self.rule,previous_gate="any"),
              dict(self.rule,reply="Tenemos stock disponible"),
              dict(self.rule,unexpected="yes")):
   with self.subTest(bad=str(bad)[:40]),self.assertRaises(ValueError):
    a.valid_pack(dict(self.pack,rules=[bad]))
 def test_cannot_apply_outside_pilot(self):
  for p in (dict(self.pack,pilot_conversation_id=4),dict(self.pack,version=2),
            dict(self.pack,rules=[self.rule,self.rule])):
   with self.assertRaises(ValueError):a.valid_pack(p)
 def test_source_gates_are_required(self):
  source=a.LIVE.read_text()
  self.assertIn("PILOT_CONVERSATION_ID = 3",source)
  changed=source.replace("PILOT_CONVERSATION_ID = 3","PILOT_CONVERSATION_ID = 5")
  with self.assertRaises(RuntimeError):a.embedded_source(changed,self.pack)
 def test_deterministic_source(self):
  source=a.LIVE.read_text()
  p=a.embedded_source(source,self.pack)
  self.assertEqual(p,a.embedded_source(p,self.pack))
  self.assertEqual(p.count(a.BEG),1)
  self.assertEqual(p.count(a.HOOK_BEG),1)
  self.assertIn("sm_auto_policy(raw,intent_type,previous_bot)",p)
  self.assertIn('gate=="checkout"',p)
 def test_filters_review_findings(self):
  sample={"bot_message_id":184,"status":"pending_human_review",
          "category":"exact_repeat","customer_sample":"Transferencias",
          "bot_sample":"Perfecto, sería para retirar. Tengo anotado el iPhone 15 Pro"}
  self.assertEqual(a.discover([sample],a.default_pack()),[self.rule])
  self.assertEqual(a.discover([sample],self.pack),[])
  self.assertEqual(a.discover([dict(sample,category="unsafe_claim")],a.default_pack()),[])
  self.assertEqual(a.discover([dict(sample,bot_sample="Una respuesta distinta")],a.default_pack()),[])
 def test_safety_pattern_always_checks_outputs(self):
  self.assertIsNotNone(a.CONFIRM_SAFE.search("precio final es L20000"))
  self.assertIsNotNone(a.CONFIRM_SAFE.search("te lo reservé"))
  self.assertIsNone(a.CONFIRM_SAFE.search(self.rule["reply"]))
 def test_daily_cap_and_state_paths(self):
  self.assertEqual(a.DAILY_CAP,2)
  self.assertTrue(str(a.HISTORY).startswith(str(a.ROOT)))
  self.assertTrue(str(a.BACKUPS).startswith("/opt/softmobile-waha-test/"))
 def test_no_ai_code_imported(self):
  p=a.embedded_source(a.LIVE.read_text(),self.pack)
  self.assertNotIn("eval(",p[:500])
  self.assertNotIn("File.read(",p[:1200])
 def test_only_conversation_scope(self):
  source=a.LIVE.read_text()
  self.assertIn("PILOT_CONVERSATION_ID = 3",source)
  self.assertIn("AUTO_REPLY_LIMIT = 1",source)

if __name__=="__main__":unittest.main()
