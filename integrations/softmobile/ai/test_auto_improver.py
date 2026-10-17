#!/usr/bin/env python3
"""Fully offline safety tests for the bounded autonomous pilot self-improver."""
import unittest
from unittest.mock import patch
from pathlib import Path
import auto_improver as a

class AutoImproverTests(unittest.TestCase):
 def source(self):
  """Portable offline fixture. VPS separately tests the actual production Ruby."""
  return (
   "# frozen_string_literal: true\n"
   "module SoftMobileSales\n"
   "  INBOX_ID = 2\n"
   "  PILOT_CONVERSATION_ID = 3\n"
   "  AUTO_REPLY_LIMIT = 1\n"
   "  class << self\n"
   "    def plan(message, ctx, products, previous_bot=nil)\n"
   "      raw=message.to_s\n"
   "      intent_type=:payments\n"
   "      if ambiguous_model_choice?(raw) && [:stock,:price,:other,:comparison].include?(intent_type)\n"
   "        return nil\n"
   "      end\n"
   "    end\n"
   "  end\n"
   "end\n"
   "if ENV['SM_MODE']=='test'\n"
   "  exit\n"
   "end\n"
  )

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
  source=self.source()
  self.assertIn("PILOT_CONVERSATION_ID = 3",source)
  changed=source.replace("PILOT_CONVERSATION_ID = 3","PILOT_CONVERSATION_ID = 5")
  with self.assertRaises(RuntimeError):a.embedded_source(changed,self.pack)
 def test_deterministic_source(self):
  source=self.source()
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
 def test_new_payment_intent_flag_can_feed_bounded_fix(self):
  issue={"bot_message_id":320,"status":"pending_human_review",
         "category":"payment_choice_ignored","customer_sample":"Tarjeta",
         "bot_sample":"Perfecto, sería para retirar. Tengo anotado el Samsung S22 Ultra."}
  plan=a.discover([issue],a.default_pack())
  self.assertEqual(plan,[{"when":"tarjeta","intent":"payments","previous_gate":"checkout",
                          "reply":a.ALLOWED_REPLIES["tarjeta"]}])
  self.assertEqual(a.discover([dict(issue,customer_sample="Mi tarjeta es 41111111")],a.default_pack()),[])
 def test_synthetic_payment_menu_is_bounded(self):
  issue={"id":"synthetic-1","status":"synthetic_unverified",
    "category":"payments","static_flags":["payment_choice_repeat"],
    "evidence":[
      {"buyer":"¿Cómo puedo pagar?","bot":"Podés pagar en efectivo, transferencia o tarjeta."},
      {"buyer":"Transferencia","bot":"Podés pagar en efectivo, transferencia o tarjeta."}]}
  rule={"when":"transferencia","intent":"payments","previous_gate":"payment_menu",
        "reply":a.ALLOWED_REPLIES["transferencia"]}
  self.assertEqual(a.discover_synthetic([issue],a.default_pack()),[(rule,"synthetic-1")])
  self.assertEqual(a.discover_synthetic([issue],{"version":1,"pilot_conversation_id":3,"rules":[rule]}),[])
  self.assertEqual(a.discover_synthetic([dict(issue,static_flags=[])],a.default_pack()),[])
  self.assertEqual(a.discover_synthetic([dict(issue,category="financing")],a.default_pack()),[])
  self.assertEqual(a.discover_synthetic([dict(issue,status="discarded_invalid_scenario")],a.default_pack()),[])
 def test_synthetic_rule_cannot_override_commercial_reply(self):
  rule={"when":"transferencia","intent":"payments","previous_gate":"payment_menu",
        "reply":a.ALLOWED_REPLIES["transferencia"]}
  a.valid_pack({"version":1,"pilot_conversation_id":3,"rules":[rule]})
  with self.assertRaises(ValueError):
   a.valid_pack({"version":1,"pilot_conversation_id":3,"rules":[
    dict(rule,reply="Pago confirmado, enviá comprobante")]})
 def test_safety_pattern_always_checks_outputs(self):
  self.assertIsNotNone(a.CONFIRM_SAFE.search("precio final es L20000"))
  self.assertIsNotNone(a.CONFIRM_SAFE.search("te lo reservé"))
  self.assertIsNone(a.CONFIRM_SAFE.search(self.rule["reply"]))
 def test_daily_cap_and_state_paths(self):
  self.assertEqual(a.DAILY_CAP,2)
  self.assertTrue(str(a.HISTORY).startswith(str(a.ROOT)))
  self.assertTrue(str(a.BACKUPS).startswith("/opt/softmobile-waha-test/"))
 def test_no_ai_code_imported(self):
  p=a.embedded_source(self.source(),self.pack)
  self.assertNotIn("eval(",p[:500])
  self.assertNotIn("File.read(",p[:1200])
 def test_only_conversation_scope(self):
  source=self.source()
  self.assertIn("PILOT_CONVERSATION_ID = 3",source)
  self.assertIn("AUTO_REPLY_LIMIT = 1",source)

if __name__=="__main__":unittest.main()
