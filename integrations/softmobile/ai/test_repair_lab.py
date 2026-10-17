#!/usr/bin/env python3
"""All repair generator security tests run offline with mocked Groq/runner."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import repair_lab as r
import synthetic_lab as s

class RepairLabTests(unittest.TestCase):
 def setUp(self):
  self.issue={"id":"de90d42caef83f2141","at":"2026-10-17T23:30:00Z",
    "category":"shipping","status":"synthetic_unverified",
    "scenario":{"category":"shipping","messages":[
      "Me interesa el Samsung S24 Ultra. ¿Tienen disponible?",
      "¿Cuánto tiempo tardará el asesor en darme una respuesta?",
      "¿Cuánto tiempo tardará el asesor en darme una respuesta?"]},
    "evidence":[
      {"buyer":"Me interesa el Samsung S24 Ultra. ¿Tienen disponible?","bot":"Aún no tengo confirmada la existencia."},
      {"buyer":"¿Cuánto tiempo tardará el asesor en darme una respuesta?","bot":"Aún no tengo confirmada la existencia."},
      {"buyer":"¿Cuánto tiempo tardará el asesor en darme una respuesta?","bot":"Aún no tengo confirmada la existencia."}]}
  self.template="PILOT_CONVERSATION_ID = 3\nINBOX_ID = 2\nAUTO_REPLY_LIMIT = 1\n"+r.ANCHOR+"    def plan(x)\n      nil\n    end\nif ENV['SM_MODE']=='test'\n"

 def test_classifies_advisor_failure_only_with_safe_synthetic_evidence(self):
  result=r.eligible([self.issue],[])
  self.assertIsNotNone(result)
  self.assertEqual(result[2],["advisor_eta"])
  invalid=dict(self.issue,status="retested_ai_clear_pending_deterministic_review")
  self.assertIsNone(r.eligible([invalid],[]))
  unsafe=dict(self.issue,scenario={"category":"shipping","messages":[
    "Contactame al +50499991234","¿Cuánto tiempo tardará el asesor?","Ok"]})
  self.assertIsNone(r.eligible([unsafe],[]))
 def test_separate_followup_detection(self):
  x=dict(self.issue,id="other",category="checkout",
   scenario={"category":"checkout","messages":[
     "Quiero comprar","¿Cuándo recibo el número de seguimiento del envío?","¿Me lo dan?"]},
   evidence=[
     {"buyer":"Quiero comprar","bot":"¿Qué modelo?"},
     {"buyer":"¿Cuándo recibo el número de seguimiento del envío?","bot":"¿A qué ciudad sería?"},
     {"buyer":"¿Me lo dan?","bot":"¿A qué ciudad sería?"}])
  self.assertEqual(r.eligible([x],[])[2],["tracking_followup"])
 def test_only_fixed_allowlisted_ruby_can_be_generated(self):
  candidate=r.compile_candidate(self.template,["advisor_eta","tracking_followup"])
  self.assertIn("plazo confirmado",candidate)
  self.assertIn("transportista",candidate)
  self.assertEqual(candidate.count(r.BEG),1)
  self.assertEqual(candidate.count(r.END),1)
  self.assertEqual(r.compile_candidate(candidate,["advisor_eta","tracking_followup"]),candidate)
  with self.assertRaises(ValueError):r.compile_candidate(self.template,["os.system('evil')"])
  with self.assertRaises(ValueError):r.compile_candidate(self.template,["advisor_eta","advisor_eta"])
  with self.assertRaises(ValueError):r.compile_candidate("untrusted code",["advisor_eta"])
 def test_ai_response_is_never_code_and_requires_allowlisted_family(self):
  with tempfile.TemporaryDirectory() as temp,patch.object(s,"STATE",Path(temp)/"calls.json"):
   state=s.previous_state()
   def stub(k,sys,prompt,schema,name):
    self.assertNotIn("systemctl",prompt)
    return {"family":"advisor_eta","reason":"La respuesta repite stock."}
   found=r.choose_with_groq(self.issue,["advisor_eta"],"test",state,api=stub)
   self.assertEqual(found,"advisor_eta")
   self.assertEqual(state["api_calls"],1)
   self.assertIsNone(r.choose_with_groq(self.issue,["advisor_eta"],"test",state,
       api=lambda *_:{"family":"arbitrary_ruby","reason":"hacking"}))
   self.assertIsNone(r.choose_with_groq(self.issue,["advisor_eta"],"test",state,
       api=lambda *_:{"family":"advisor_eta","reason":"OK","ruby":"puts 'hacked'"}))
 def test_stage_is_root_only_and_uses_fixed_suffix(self):
  with tempfile.TemporaryDirectory() as temp,patch.object(r,"STAGE",Path(temp)):
   x=r.stage(r.compile_candidate(self.template,["advisor_eta"]),"de90d42caef83f2141","advisor_eta")
   self.assertEqual(x.stat().st_mode&0o777,0o600)
   self.assertEqual(x.read_text().count("SM_REPAIR_LAB_SAFE_RULES_BEGIN"),1)
 def test_no_model_authored_ruby_may_deploy(self):
  src=Path(r.__file__).read_text()
  self.assertNotIn("exec(",src)
  self.assertNotIn("eval(",src)
  self.assertNotIn("MessageBuilder",src)
  self.assertNotIn("sendText",src)
  self.assertIn("r.SAFE_REPLIES" if False else "SAFE_REPLIES[",src)
 def test_safe_replay_requires_change_not_only_approval(self):
  with patch.object(s,"simulate") as fake:
   trace={"category":"shipping","turns":[
      {"buyer":t,"bot":"No tengo datos","human":True,"intent":"other"}
      for t in self.issue["scenario"]["messages"]]}
   fake.return_value=[trace]
   check=r.safe_replay(Path("candidate"),self.issue,self.issue["scenario"],"advisor_eta")
   self.assertEqual(check["status"],"no_target_improvement")
 def test_previously_deployed_repair_family_is_not_reselected(self):
  self.assertIsNone(r.eligible([self.issue],["advisor_eta"]))
 def test_pack_validates_scope_and_family(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(r,"RULES",Path(tmp)/"pack.json"):
   self.assertEqual(r.current_pack()["families"],[])
   r._atomic_json(r.RULES,{"version":1,"pilot_conversation_id":14,"families":[]})
   with self.assertRaises(ValueError):r.current_pack()
   r._atomic_json(r.RULES,{"version":1,"pilot_conversation_id":3,"families":["unreviewed_python"]})
   with self.assertRaises(ValueError):r.current_pack()

if __name__=="__main__":unittest.main()
