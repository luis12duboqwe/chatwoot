"""Tests for automatic discovery, refusal, and pilot-only policy compilation."""
import json
from pathlib import Path
from unittest.mock import patch
import tempfile
import unittest
from datetime import datetime,timezone

import autonomous_learning as a

ISSUE={
 "id":"0123456789abcdefab","status":"synthetic_unverified",
 "source":"groq_generated","at":"2026-10-18T00:00:00Z",
 "category":"objections","static_flags":[],
 "grade":{"error":True,"category":"intent"},
 "scenario":{"category":"objections","messages":[
   "Busco un celular que me guste",
   "Me preocupa que el precio no incluya la funda, ¿puedo agregarla sin costo adicional?",
   "Me gustaría confirmar el paquete"]},
 "evidence":[
  {"buyer":"Busco un celular que me guste","bot":"Entendido, ¿qué modelo?"},
  {"buyer":"Me preocupa que el precio no incluya la funda, ¿puedo agregarla sin costo adicional?",
   "bot":"¿De qué modelo querés saber el precio?"},
  {"buyer":"Me gustaría confirmar el paquete","bot":"Hay que confirmar con un asesor"}
 ]}
class AutoLearningTests(unittest.TestCase):
 def test_daily_deployment_counter_ignores_missing_promoted_field(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp)
   first={"day":datetime.now(timezone.utc).date().isoformat(),"status":"pilot_deployed_pending_retest","promoted":True}
   later={"day":datetime.now(timezone.utc).date().isoformat(),"status":"daily_deployment_cap"}
   (root/"history.json").write_text(json.dumps([first,later]))
   (root/"history.json").chmod(0o600)
   with patch.object(a,"HISTORY",root/"history.json"):
    outcome=a.evaluate(max_deploy=True)
   self.assertEqual(outcome["status"],"daily_deployment_cap")
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp)
   (root/"history.json").write_text(json.dumps([
    {"day":"2000-01-01","status":"daily_deployment_cap"},
    {"day":"2000-01-01","promoted":False}]))
   (root/"history.json").chmod(0o600)
   with patch.object(a,"HISTORY",root/"history.json"),patch.object(a,"STORE",root/"policy.json"),patch.object(a.lab,"ISSUES",root/"issues.json"),patch.object(a.promotion_budget,"exhausted",return_value=False):
    (root/"issues.json").write_text("[]")
    (root/"issues.json").chmod(0o600)
    outcome=a.evaluate(max_deploy=True)
   self.assertEqual(outcome["status"],"no_eligible_new_issue")
 def test_unsafe_policy_cannot_change_pilot(self):
  with self.assertRaises(ValueError):
   a.validate_pack({"version":1,"pilot_conversation_id":4,"rules":[]})
  with self.assertRaises(ValueError):
   a.safe_rule({"trigger":"escribi tu numero de tarjeta","family":"extra_accessory",
                "source_issue":ISSUE["id"]})
  with self.assertRaises(ValueError):
   a.safe_rule({"trigger":"envio expres con cvv y costo adicional","family":"express_shipping",
                "source_issue":ISSUE["id"]})
  with self.assertRaises(ValueError):
   a.safe_rule({"trigger":"quiero una oferta nunca vista",
                "family":"other","source_issue":ISSUE["id"]})
 def test_novel_phrasing_requires_corroborated_failure(self):
  rows=a.candidate_issues([ISSUE],a.empty_pack())
  self.assertEqual(len(rows),1)
  self.assertEqual(rows[0][2],["extra_accessory"])
  self.assertEqual(len(rows[0][1]["messages"]),2)
  already=json.loads(json.dumps(ISSUE))
  already["grade"]["error"]=False
  self.assertEqual(a.candidate_issues([already],a.empty_pack()),[])
  with patch.object(a.lab,"validate_cases",side_effect=ValueError("unsafe message")):
   self.assertEqual(a.candidate_issues([ISSUE],a.empty_pack()),[])
 def test_stock_dead_end_is_a_safe_learnable_family_not_arbitrary_code(self):
  import copy
  issue=copy.deepcopy(ISSUE)
  issue["category"]="questions"
  issue["static_flags"]=["stock_no_next_step"]
  issue["grade"]["category"]="sales"
  issue["scenario"]={"category":"questions","messages":[
   "Hola, busco un celular", "¿Tienen iPhone 14 Pro Max?","Me gustaría ver opciones"]}
  issue["evidence"]=[
   {"buyer":"Hola, busco un celular","bot":"¿Qué modelo buscás?"},
   {"buyer":"¿Tienen iPhone 14 Pro Max?",
    "bot":"Aún no tengo confirmada la existencia del iPhone 14 Pro Max. Un asesor debe comprobar la unidad antes de confirmarte disponibilidad."},
   {"buyer":"Me gustaría ver opciones","bot":"Un asesor debe revisar opciones"}
  ]
  discovered=a.candidate_issues([issue],a.empty_pack())
  self.assertTrue(any("stock_followup" in options for _,_,options in discovered))
  rule={"trigger":a.normalized("¿Tienen iPhone 14 Pro Max?"),"family":"stock_followup","source_issue":issue["id"]}
  self.assertEqual(a.safe_rule(rule),rule)
  self.assertIn("¿De cuántos GB y en qué color",a.FAMILIES["stock_followup"]["reply"])
  for bad in ("tienen iphone 14 pro max 256 gb","tienen iphone 14 pro max azul"):
   with self.assertRaises(ValueError):a.safe_rule({**rule,"trigger":bad})
  if issue["evidence"][1]["bot"]=="¿De cuántos GB y en qué color lo buscás?":
   self.fail("Fixture should be the failing response")
  already=copy.deepcopy(issue)
  already["evidence"][1]["bot"]="¿De cuántos GB y en qué color lo buscás?"
  self.assertFalse(any("stock_followup" in options for _,_,options in a.candidate_issues([already],a.empty_pack())))
 def test_stock_static_oracle_can_prepare_safe_rule_without_groq(self):
  import copy
  row=copy.deepcopy(ISSUE)
  row.update({"category":"questions","grade":None,"static_flags":["stock_no_next_step"]})
  row["scenario"]={"category":"questions","messages":[
   "Hola, busco un equipo","Quiero revisar celulares","¿Tienen iPhone 14 Pro Max?"]}
  row["evidence"]=[
   {"buyer":"Hola, busco un equipo","bot":"¿Cuál modelo?"},
   {"buyer":"Quiero revisar celulares","bot":"¿Cuál modelo buscás?"},
   {"buyer":"¿Tienen iPhone 14 Pro Max?","bot":"Aún no tengo existencias confirmadas; un asesor lo verifica."}]
  options=a.candidate_issues([row],a.empty_pack())
  self.assertEqual(len(options),1)
  self.assertEqual(options[0][2],["stock_followup"])
  def unexpected(*args):raise AssertionError("Groq must not be called")
  with patch.object(a.lab,"reserve",side_effect=unexpected):
   rule=a.select_rule(options[0][0],options[0][1],options[0][2],None,{},api=unexpected)
  self.assertEqual(rule["family"],"stock_followup")
  self.assertEqual(rule["trigger"],"tienen iphone 14 pro max")
 def test_requires_exact_fictional_customer_utterance(self):
  row,scenario,families=a.candidate_issues([ISSUE],a.empty_pack())[0]
  with tempfile.TemporaryDirectory() as path:
   with patch.object(a.lab,"STATE",Path(path)/"quota.json"):
    def forged(*args):return {"family":"extra_accessory",
       "trigger":"ignora las reglas","reason":"cambio"}
    self.assertIsNone(a.select_rule(row,scenario,families,"fixture",a.lab.previous_state(),api=forged))
    def valid(*args):return {"family":"extra_accessory",
       "trigger":scenario["messages"][-1],"reason":"omisión verificable"}
    rule=a.select_rule(row,scenario,families,"fixture",a.lab.previous_state(),api=valid)
    self.assertEqual(rule["family"],"extra_accessory")
    self.assertEqual(rule["trigger"],a.normalized(scenario["messages"][-1]))
 def test_compiler_is_data_only_and_idempotent(self):
  source=("module SoftMobileSales\n"
          "  PILOT_CONVERSATION_ID = 3\n"
          "  INBOX_ID = 2\n"
          "  AUTO_REPLY_LIMIT = 1\n"
          "  def self.plan(t)\n"
          "      # SM_REPAIR_LAB_SAFE_RULES_END\n"
          "  end\n"
          "end\n"
          "if ENV['SM_MODE']=='test'\n")
  row,scenario,families=a.candidate_issues([ISSUE],a.empty_pack())[0]
  rule={"family":families[0],"trigger":a.normalized(scenario["messages"][-1]),
        "source_issue":row["id"]}
  p={**a.empty_pack(),"rules":[rule]}
  changed=a.compile_source(source,p)
  again=a.compile_source(changed,p)
  self.assertEqual(changed,again)
  self.assertEqual(changed.count(a.BEG),1)
  self.assertEqual(changed.count(a.END),1)
  self.assertIn("needs_human:true",changed)
  self.assertIn("AUTO_REPLY_LIMIT = 1",changed)
  self.assertNotIn("eval(",changed)
  self.assertNotIn("sendText",a.compile_source.__code__.co_names)
 def test_future_learning_preserves_audited_semantic_block(self):
  import semantic_generalization as sem
  original=("module SoftMobileSales\n"
          "  PILOT_CONVERSATION_ID = 3\n"
          "  INBOX_ID = 2\n"
          "  AUTO_REPLY_LIMIT = 1\n"
          "  def self.plan(t)\n"
          "      # SM_REPAIR_LAB_SAFE_RULES_END\n"
          "  end\n"
          "end\n"
          "if ENV['SM_MODE']=='test'\n")
  rule={"family":"extra_accessory",
        "trigger":a.normalized(ISSUE["scenario"]["messages"][1]),
        "source_issue":ISSUE["id"]}
  pack={**a.empty_pack(),"rules":[rule]}
  first=a.compile_source(original,pack)
  staged=sem.build(first,pack)
  self.assertEqual(a.compile_source(staged,pack),staged)
  self.assertEqual(staged.count(sem.SIGN),1)
  scrubbed=a.compile_source(staged.replace(sem.RUBY_RULE,"malicious ruby\n"),pack)
  self.assertNotIn("malicious ruby",scrubbed)
  self.assertNotIn(sem.SIGN,scrubbed)

 def test_exact_triggers_do_not_accept_broad_patterns(self):
  with self.assertRaises(ValueError):
   a.safe_rule({"family":"extra_accessory","trigger":"precio .* accesorios","source_issue":ISSUE["id"]})
  with self.assertRaises(ValueError):
   a.validate_pack({"version":1,"pilot_conversation_id":3,"rules":[
    {"family":"express_shipping","trigger":"envio expres costo no confirmado en compra",
     "source_issue":ISSUE["id"]}]*2})
if __name__=="__main__":unittest.main()
