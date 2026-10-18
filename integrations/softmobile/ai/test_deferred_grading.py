import copy,hashlib,json,tempfile,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from unittest.mock import patch,Mock
import deferred_grading as d
import synthetic_lab as lab
from quality_auditor import _atomic_json

def example():
 s={"category":"questions","messages":["Busco un iPhone 14 Pro Max",
    "¿Incluye cargador?","¿Tiene garantía?"]}
 ident=hashlib.sha256(json.dumps(s,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:18]
 return {"id":ident,"at":"2026-10-18T00:00:00+00:00","source":"interactive_step_by_step_groq",
  "category":s["category"],"scenario":s,
  "evidence":[{"buyer":x,"bot":"Un asesor debe verificar las condiciones del equipo.",
    "intent":"other","human":True} for x in s["messages"]],
  "status":"synthetic_ungraded","grade":None,"static_flags":[]}
class DeferredGradingTests(unittest.TestCase):
 def test_pii_or_synthetic_hash_mismatch_rejected(self):
  row=example()
  self.assertTrue(d.eligible(row))
  row["id"]="faked";self.assertFalse(d.eligible(row))
  row=example();row["scenario"]["messages"][0]="Mi teléfono es 9999-4444"
  self.assertFalse(d.eligible(row))
 def test_skips_customer_like_rows(self):
  x=example();x["source"]="production_customer"
  self.assertFalse(d.eligible(x))
 def test_successful_grade_updates_same_conversation_only(self):
  r=example()
  grade={"error":True,"severity":"medium","category":"sales",
    "reason":"Falta aclaración de precio","suggested_reply":"Un asesor debe confirmar el precio.",
    "expected_behavior":"Solicitar consulta comercial"}
  with tempfile.TemporaryDirectory() as temp,      patch.object(lab,"STATE",Path(temp)/"state.json"),      patch.object(d,"state_at",return_value=0):
   issues=[]
   result=d.evaluate([r],issues,lab.previous_state(),api=lambda *a:grade,key="fictional")
  self.assertEqual(result["considered"],1)
  self.assertEqual(result["flagged_for_review"],1)
  self.assertEqual(result["left_ungraded"],0)
  self.assertTrue(r["grade"]["error"])
  self.assertEqual(len(issues),1)
  self.assertFalse(issues[0]["eligible_for_unreviewed_code_change"])
 def test_provider_failure_retries_without_new_case_or_duplicate(self):
  r=example();state=lab.previous_state()
  with tempfile.TemporaryDirectory() as temp,     patch.object(lab,"STATE",Path(temp)/"state.json"),     patch.object(d,"state_at",return_value=0):
   now=datetime(2026,10,18,tzinfo=timezone.utc)
   err=d.evaluate([r],[],state,api=Mock(side_effect=RuntimeError("429")),key="fixture",now=now)
   self.assertEqual(err["provider_unavailable"],1)
   self.assertIsNone(r["grade"])
   self.assertFalse(d.eligible(r,now+timedelta(minutes=10)))
   self.assertTrue(d.eligible(r,now+timedelta(minutes=31)))
   self.assertEqual(err["left_ungraded"],1)
 def test_skips_provider_when_no_cases(self):
  judge=Mock()
  with patch.object(d,"stored_key",return_value="key"):
   result=d.evaluate([],[],lab.previous_state(),api=judge)
   judge.assert_not_called()
   self.assertEqual(result["status"],"no_due_items")
 def test_false_grade_closes_backlog_without_issue(self):
  r=example()
  grade={"error":False,"severity":"low","category":"no_issue",
    "reason":"Correcto","suggested_reply":"","expected_behavior":""}
  with tempfile.TemporaryDirectory() as temp,      patch.object(lab,"STATE",Path(temp)/"state.json"),      patch.object(d,"state_at",return_value=0):
   issues=[]
   result=d.evaluate([r],issues,lab.previous_state(),api=lambda *a:grade,key="fictional")
  self.assertEqual(result["approved_no_issue"],1)
  self.assertEqual(result["left_ungraded"],0)
  self.assertFalse(issues)
 def test_full_run_with_fixture_json_and_no_public_writes(self):
  with tempfile.TemporaryDirectory() as temp:
   p=Path(temp);_atomic_json(p/"transcripts.json",[example()])
   with patch.object(d.interactive,"TRANSCRIPTS",p/"transcripts.json"),        patch.object(d.lab,"ISSUES",p/"issues.json"),        patch.object(d.lab,"STATE",p/"state.json"),        patch.object(d.lab,"LOCK",p/"synthetic.lock"),        patch.object(d,"REPORT",p/"result.json"),        patch.object(d,"state_at",return_value=0):
    grade={"error":False,"severity":"low","category":"no_issue",
      "reason":"Correcto","suggested_reply":"","expected_behavior":""}
    out=d.run(api=lambda *a:grade,key="fixture")
    self.assertEqual(out["public_messages_sent"],0)
    self.assertEqual(out["code_deployments"],0)
    saved=json.loads((p/"transcripts.json").read_text())
    self.assertEqual(len(saved),1)
    self.assertFalse(saved[0]["grade"]["error"])
if __name__=="__main__":unittest.main()
