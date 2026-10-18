import tempfile,unittest,json
from datetime import datetime,timezone,timedelta
from pathlib import Path
import promotion_budget as p
from quality_auditor import _atomic_json

class SharedBudgetTests(unittest.TestCase):
 def temporary_logs(self,root,repairs=None,autofixes=None,learned=None):
  root=Path(root);root.mkdir(exist_ok=True)
  for file,records in (("repair-lab-history.json",repairs or []),
      ("autofix-history.json",autofixes or []),("learned-dialogue-history.json",learned or [])):
   _atomic_json(root/file,records)
 def test_utc_date_not_host_time(self):
  stamp=datetime(2026,10,19,1,20,tzinfo=timezone(timedelta(hours=3)))
  self.assertEqual(p.active_day(stamp),"2026-10-18")
 def test_counts_separately_recorded_deployments_as_one_budget(self):
  with tempfile.TemporaryDirectory() as tmp:
   self.temporary_logs(tmp,
      repairs=[{"day":"2026-10-18","promoted":True}],
      learned=[{"day":"2026-10-18","promoted":True},
               {"day":"2026-10-18","status":"daily_deployment_cap"}])
   x=p.usage("2026-10-18",root=tmp)
   self.assertEqual(x["total"],2)
   self.assertFalse(x["available"])
   self.assertEqual(x["by_source"]["repair_family"],1)
   self.assertEqual(x["by_source"]["learned_and_semantic"],1)
   self.assertEqual(p.usage("2026-10-19",root=tmp)["total"],0)
 def test_autofix_individually_counts_even_without_promoted_flag(self):
  with tempfile.TemporaryDirectory() as tmp:
   self.temporary_logs(tmp,autofixes=[{"day":"2026-10-19","status":"deployed"}])
   self.assertEqual(p.usage("2026-10-19",root=tmp)["total"],1)
 def test_fail_closed_on_corrupted_or_undated_deployments(self):
  with tempfile.TemporaryDirectory() as tmp:
   self.temporary_logs(tmp,repairs=[{"promoted":True}])
   with self.assertRaises(ValueError):p.usage("2026-10-19",root=tmp)
  with tempfile.TemporaryDirectory() as tmp:
   self.temporary_logs(tmp)
   _atomic_json(Path(tmp)/"autofix-history.json",{"corrupted":1})
   with self.assertRaises(ValueError):p.usage("2026-10-19",root=tmp)
 def test_no_reintroduced_external_token_limit(self):
  self.assertEqual(p.DAILY_LIMIT,1)
  self.assertEqual(p.SOURCES.keys(),{
   "payment_autofix":"autofix-history.json",
   "repair_family":"repair-lab-history.json",
   "learned_and_semantic":"learned-dialogue-history.json"}.keys())
if __name__=="__main__":unittest.main()
