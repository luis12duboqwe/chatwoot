import unittest
from unittest.mock import patch,Mock
from pathlib import Path
import tempfile,json
import accessory_directness as fix
import autonomous_learning as learner
import learned_retest as checker
import combined_pilot_promotion as bundle
import directness_independent_review as independent

class DirectnessTests(unittest.TestCase):
 def test_direct_reply_is_explicit_and_human_reviewed(self):
  self.assertIn("sin costo",fix.REPLY)
  self.assertIn("no puedo incluirte",fix.REPLY)
  self.assertIn("regalía",fix.REPLY)
  self.assertIn("asesor",fix.REPLY)
  self.assertNotIn("gratis.",fix.REPLY)
  self.assertIn("needs_human:true",fix.CODE)
  self.assertIn("sm_learned_dialogue",fix.CODE)
 def test_old_bot_requires_same_old_expected_policy(self):
  rule={"family":"extra_accessory","trigger":fix.TRIGGER}
  self.assertIsNone(fix.expected_reply("old ruby",rule))
 def test_new_bot_response_only_if_fixed_source_matches(self):
  rule={"family":"extra_accessory","trigger":fix.TRIGGER}
  self.assertEqual(fix.expected_reply(fix.CODE,rule),fix.REPLY)
  with self.assertRaises(ValueError):
   fix.expected_reply(fix.CODE.replace("no puedo incluirte","sí te la doy"),rule)
 def test_quality_decision_requires_valid_exact_hash_and_recent_result(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"report.json"
   candidate="test-candidate"
   with patch.object(bundle,"QA",Path(d)):
    self.assertFalse(bundle.independent_quality_approved(candidate))
    r={"status":"independent_ai_approved","revision":bundle.REVISION,
      "candidate_sha256":bundle.digest(candidate),"judge_error":False,
      "at":bundle.datetime.now(bundle.timezone.utc).isoformat()}
    p.write_text(json.dumps(r));p.chmod(0o600)
    (Path(d)/"directness-independent-review.json").write_text(json.dumps(r))
    (Path(d)/"directness-independent-review.json").chmod(0o600)
    variant_review={"status":"ai_approved_for_review","ai_approved":True,
      "candidate_sha256":bundle.digest(candidate),
      "at":bundle.datetime.now(bundle.timezone.utc).isoformat()}
    (Path(d)/"variant-context-ai-review.json").write_text(json.dumps(variant_review))
    (Path(d)/"variant-context-ai-review.json").chmod(0o600)
    self.assertTrue(bundle.independent_quality_approved(candidate))
    r["judge_error"]=True
    (Path(d)/"directness-independent-review.json").write_text(json.dumps(r))
    self.assertFalse(bundle.independent_quality_approved(candidate))
    r["judge_error"]=False;r["candidate_sha256"]="other hash"
    (Path(d)/"directness-independent-review.json").write_text(json.dumps(r))
    self.assertFalse(bundle.independent_quality_approved(candidate))
 def test_independent_model_must_not_be_called_for_stale_stage(self):
  with patch.object(independent,"_load",return_value={}):
   fake=Mock()
   r=independent.review(judge=fake,key="test")
   self.assertEqual(r["status"],"candidate_not_preverified")
   fake.assert_not_called()
if __name__=="__main__":unittest.main()
