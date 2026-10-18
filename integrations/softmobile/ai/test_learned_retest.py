import unittest
from unittest.mock import patch
import learned_retest as retest
import autonomous_learning as learn

class RetestTests(unittest.TestCase):
 def setUp(self):
  self.rule={"trigger":"me preocupa que el precio no incluya la funda puedo agregarla sin costo adicional",
             "family":"extra_accessory","source_issue":"b735b499e02b3eea74"}
  self.message="Me preocupa que el precio no incluya la funda, ¿puedo agregarla sin costo adicional?"
  self.pack={"version":1,"pilot_conversation_id":3,"rules":[self.rule]}
 def test_status_distinguishes_offline_from_provider_validation(self):
  r={"checked":1,"deterministic_failed":0,"ai_confirmed":0,"ai_flagged":0}
  self.assertEqual(retest.report_status(r,False),"deterministic_only_passed")
  self.assertEqual(retest.report_status(r,True),"deterministic_passed_ai_pending")
  r["ai_confirmed"]=1
  self.assertEqual(retest.report_status(r,True),"deterministic_and_ai_passed")
  r["ai_flagged"]=1
  self.assertEqual(retest.report_status(r,True),"ai_flagged_needs_review")
  r["deterministic_failed"]=1
  self.assertEqual(retest.report_status(r,True),"needs_review")
 def test_safe_error_classification_does_not_leak_provider_details(self):
  from urllib.error import HTTPError
  try:
   raise HTTPError("https://provider.invalid",429,"rate limited",{},None)
  except HTTPError as cause:
   try:raise RuntimeError("Remote provider request failed") from cause
   except RuntimeError as e:
    self.assertEqual(retest.failure_category(e),"provider_rate_limited")
  self.assertEqual(retest.failure_category(ValueError("some unsafe model output")),
                   "judge_validation_rejected")
  self.assertEqual(retest.failure_category(RuntimeError("other")),
                   "provider_or_response_unavailable")
 def test_requires_replayable_original_utterance(self):
  issue={"id":self.rule["source_issue"],"scenario":{"category":"questions","messages":[
    "Busco un iPhone 15",self.message,"Quiero consultar otro color"]}}
  x=retest.collect_rules(self.pack,[issue])
  self.assertEqual(len(x),1)
  self.assertEqual(len(x[0][1]),2)
  self.assertIsNone(x[0][2])
  self.assertEqual(retest.collect_rules(self.pack,[])[0][2],"missing_original_issue")
 def test_wrong_or_unreviewed_answer_fails(self):
  bads=[
   {"reply":"Sí, funda gratis","needs_human":False,"tag":"sm_learned_dialogue"},
   {"reply":"Un asesor confirma.","needs_human":True,"tag":"sm_learned_dialogue"},
   {"reply":learn.FAMILIES["extra_accessory"]["reply"],"needs_human":True,"tag":"ordinary"}
  ]
  for response in bads:
   result=retest.check_one("source",self.rule,[self.message],simulate=lambda a,b:response)
   self.assertEqual(result["status"],"deterministic_failed")
 def test_exact_approved_reply_passes_without_llm(self):
  reply=learn.FAMILIES["extra_accessory"]["reply"]
  response={"reply":reply,"needs_human":True,"tag":"sm_learned_dialogue"}
  x=retest.check_one("source",self.rule,[self.message],simulate=lambda a,b:response)
  self.assertEqual(x["status"],"deterministic_passed")
 def test_ai_is_not_required_to_accept_safe_local_gate(self):
  self.assertEqual(retest.check_one("source",self.rule,[self.message],
    simulate=lambda a,b:{"reply":learn.FAMILIES["extra_accessory"]["reply"],
        "needs_human":True,"tag":"sm_learned_dialogue"})["status"],"deterministic_passed")
if __name__=="__main__":unittest.main()
