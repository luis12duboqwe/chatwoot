import unittest
from unittest.mock import patch
from pathlib import Path
import postdeploy_pilot_smoke as p
class PostdeploySmokeTests(unittest.TestCase):
 def test_non_deployed_source_fails_safely_without_external_calls(self):
  with patch.object(p.combined,"chatwoot_runtime_smoke") as runner:
   x=p.review(source="untrusted old pilot Ruby")
   runner.assert_not_called()
   self.assertEqual(x["status"],"not_installed")
   self.assertEqual(x["public_messages_sent"],0)
   self.assertFalse(x["real_client_journey_verified"])
 def test_candidate_without_scope_cannot_open_general_inbox(self):
  with patch.object(p.combined,"KNOWN_V4_SHA",p.combined.digest("anything")):
   x=p.review(source="anything")
  self.assertEqual(x["status"],"pilot_scope_failed")
 def test_source_cannot_be_declared_piloted_without_promotion_record(self):
  source="PILOT_CONVERSATION_ID = 3\nINBOX_ID = 2"
  with patch.object(p.combined,"KNOWN_V4_SHA",p.combined.digest(source)),\
       patch.object(p,"_load",return_value=[]),\
       patch.object(p.combined,"chatwoot_runtime_smoke") as runner:
   x=p.review(source=source)
   runner.assert_not_called()
  self.assertEqual(x["status"],"promotion_history_missing")
if __name__=="__main__":unittest.main()
