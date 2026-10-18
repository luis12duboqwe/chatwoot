import unittest,tempfile,hashlib
from datetime import datetime,timezone,timedelta
from pathlib import Path
from unittest.mock import patch
import lab_acceptance as a

class AcceptanceTests(unittest.TestCase):
 def test_missing_reports_never_claim_complete(self):
  with tempfile.TemporaryDirectory() as tmp,      patch.object(a,"QA",Path(tmp)):
   r=a.calculate(load=lambda *args:{},active_ruby="fictional Ruby")
  self.assertEqual(sum(x["possible"] for x in r["checks"]),100)
  self.assertFalse(r["complete"])
  self.assertLess(r["weighted_score_percent"],100)
  self.assertTrue(r["cannot_authorize_public_rollout"])
 def test_stale_evidence_fails(self):
  t=datetime(2026,10,18,tzinfo=timezone.utc)
  self.assertTrue(a.recent(t.isoformat(),2,now=t+timedelta(minutes=45)))
  self.assertFalse(a.recent(t.isoformat(),2,now=t+timedelta(hours=3)))
  self.assertFalse(a.recent("not a date",3,now=t))
 def test_no_hardcoded_bot_path_needed_for_unit_checks(self):
  with tempfile.TemporaryDirectory() as tmp,      patch.object(a,"QA",Path(tmp)):
   x=a.calculate(load=lambda *args:{},active_ruby="text")
  self.assertFalse(next(i["passed"] for i in x["checks"]
                        if i["name"]=="version_instalada_aprueba_ventas"))
 def test_a_passed_score_does_not_allow_real_sales(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(a,"QA",Path(tmp)):
   report=a.calculate(load=lambda *args:{},active_ruby="fictional Ruby")
   self.assertEqual(report["category"],"TECHNICAL_LAB_ACCEPTANCE_ONLY")
   self.assertTrue(report["cannot_authorize_public_rollout"])
if __name__=="__main__":unittest.main()
