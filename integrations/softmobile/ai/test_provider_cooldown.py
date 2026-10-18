import tempfile
from datetime import datetime,timezone,timedelta
from pathlib import Path
from unittest.mock import patch
import unittest
import provider_cooldown as p

class ProviderCooldownTests(unittest.TestCase):
 def test_retry_after_is_provider_bounded(self):
  self.assertEqual(p.delay_seconds({"Retry-After":"120"}),120)
  self.assertEqual(p.delay_seconds({"Retry-After":"99999"}),900)
  self.assertEqual(p.delay_seconds({"Retry-After":"bad"}),90)
  self.assertEqual(p.delay_seconds(None),90)
 def test_temporary_status_is_reversible_not_daily(self):
  with tempfile.TemporaryDirectory() as temp:
   with patch.object(p,"STATE",Path(temp)/"state.json"),patch.object(p,"LOCK",Path(temp)/"lock"):
    now=datetime(2026,10,18,13,0,tzinfo=timezone.utc)
    self.assertEqual(p.state_at(now),0)
    p.register_http_429({"Retry-After":"50"},now)
    self.assertEqual(p.state_at(now),50)
    with self.assertRaises(RuntimeError):p.enforce(now)
    p.enforce(now+timedelta(minutes=2))
    self.assertEqual(p.STATE.stat().st_mode&0o777,0o600)
    self.assertNotIn("Bearer",p.STATE.read_text())
 def test_repeated_429_does_not_shorten_provider_wait(self):
  with tempfile.TemporaryDirectory() as temp:
   with patch.object(p,"STATE",Path(temp)/"state.json"),patch.object(p,"LOCK",Path(temp)/"lock"):
    now=datetime(2026,10,18,13,0,tzinfo=timezone.utc)
    p.register_http_429({"Retry-After":"240"},now)
    p.register_http_429({"Retry-After":"30"},now)
    self.assertEqual(p.state_at(now),240)
if __name__=="__main__":unittest.main()
