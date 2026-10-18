from datetime import datetime,timezone,timedelta
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
import production_readiness as p
class ReadinessTests(unittest.TestCase):
 def sample(self):
  return {"source":p.PUBLIC_SOURCE_ID,
     "checked_at":datetime.now(timezone.utc).isoformat(),
     "items":97,"verified_units":2,"verified_prices":2,"verified_colors":2,
     "approved_by_operator":True}
 def test_missing_stock_always_blocks(self):
  a=self.sample();a["verified_units"]=0
  self.assertEqual(p.validate_stock_evidence(a)[1],"missing_stock_or_pricing")
  a=self.sample();a["approved_by_operator"]=False
  self.assertEqual(p.validate_stock_evidence(a)[1],"operator_approval_required")
 def test_old_values_block_even_with_operator_approval(self):
  a=self.sample();a["checked_at"]=(datetime.now(timezone.utc)-timedelta(days=4)).isoformat()
  self.assertEqual(p.validate_stock_evidence(a)[1],"stale_or_invalid_verification")
 def test_invalid_prices_and_inconsistent_counts_block(self):
  a=self.sample();a["verified_prices"]=-5
  self.assertFalse(p.validate_stock_evidence(a)[0])
  a=self.sample();a["verified_colors"]=200
  self.assertFalse(p.validate_stock_evidence(a)[0])
 def test_source_string_is_not_authority(self):
  a=self.sample();a["source"]="unauthenticated-file"
  self.assertEqual(p.validate_stock_evidence(a)[1],"untrusted_source")
 def test_readiness_never_unilaterally_enables_public_sales(self):
  with tempfile.TemporaryDirectory() as tmp:
   fake=Path(tmp)/"pilot.rb"
   fake.write_text("PILOT_CONVERSATION_ID = 3\nINBOX_ID = 2\nAUTO_REPLY_LIMIT = 1\n")
   with patch.object(p.learn,"BOT",fake):
    r=p.evaluate(self.sample())
  self.assertFalse(r["global_customer_rollout_authorized"])
  self.assertFalse(r["live_price_quote_allowed"])
  self.assertFalse(r["orders_or_payments_authorized"])
if __name__=="__main__":unittest.main()
