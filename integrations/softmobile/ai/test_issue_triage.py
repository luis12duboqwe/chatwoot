import json
import unittest
import issue_triage as tr

CASE={"id":"abcd1234abcd1234ab","at":"2026-10-18T00:00:00Z",
      "status":"synthetic_unverified","category":"payments",
      "source":"groq_generated","scenario":{"category":"payments","messages":[
         "Busco un iPhone 15","¿Cómo puedo pagarlo?","¿Y por transferencia?"]},
      "evidence":[
         {"buyer":"Busco un iPhone 15","bot":"Un asesor lo confirma."},
         {"buyer":"¿Cómo puedo pagarlo?","bot":"Podés pagar con tarjeta."},
         {"buyer":"¿Y por transferencia?","bot":"Podés pagar con tarjeta."}],
      "grade":{"error":True},"static_flags":["payment_choice_repeat"]}
class TriageTests(unittest.TestCase):
 def test_convergent_signals_never_proven(self):
  self.assertEqual(tr.bucket(CASE),"convergent_signals_pending_replay")
  r=tr.summarize([CASE])
  self.assertEqual(r["promoted_or_proven_by_ai_alone"],0)
  self.assertEqual(r["bucket_counts"]["convergent_signals_pending_replay"],1)
 def test_ai_only_is_not_confirmed(self):
  i=json.loads(json.dumps(CASE));i["static_flags"]=[]
  self.assertEqual(tr.bucket(i),"ai_only_unverified")
  i["grade"]=None
  self.assertEqual(tr.bucket(i),"not_enough_evidence")
 def test_invalid_evidence_cannot_be_reviewed_as_valid(self):
  i=json.loads(json.dumps(CASE));i["evidence"][1]["buyer"]="una respuesta falsificada"
  self.assertEqual(tr.bucket(i),"invalid_replay_evidence")
 def test_exact_duplicate_count_is_distinct_from_issue_count(self):
  i=json.loads(json.dumps(CASE));i["id"]="000011112222333344"
  r=tr.summarize([CASE,i])
  self.assertEqual(r["duplicate_conversation_fingerprints"],1)
  self.assertEqual(r["distinct_issue_ids"],2)
 def test_deployed_still_requires_retest(self):
  i=json.loads(json.dumps(CASE));i["status"]="fix_deployed_pending_synthetic_retest"
  self.assertEqual(tr.bucket(i),"deployed_needs_retest")
if __name__=="__main__":unittest.main()
