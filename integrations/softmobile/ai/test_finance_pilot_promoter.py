import tempfile
from pathlib import Path
from unittest.mock import Mock,patch
import unittest
import finance_pilot_promoter as f

class FinancePromotionTests(unittest.TestCase):
 def test_is_not_a_second_same_day_deployment(self):
  with patch.object(f.bundled,"deployed_today",return_value=1):
   x=f.promote(installer=Mock())
  self.assertEqual(x["status"],"daily_deployment_cap")
 def test_requires_known_exact_source(self):
  with self.assertRaises(ValueError):f.fixed_candidate("untrusted source")
 def test_no_install_for_changed_source(self):
  with tempfile.TemporaryDirectory() as d:
   bot=Path(d)/"bot.rb";bot.write_text("malicious source drift")
   install=Mock()
   with patch.object(f.bundled,"deployed_today",return_value=0),patch.object(f.learner,"BOT",bot),patch.object(f.promotion_budget,"exhausted",return_value=False):
    x=f.promote(installer=install)
   self.assertEqual(x["status"],"source_changed")
   install.assert_not_called()
 def test_production_scope_is_not_manually_expanded(self):
  self.assertEqual(f.KNOWN_FIN_SHA,"972b74f1e4a9126059fb273117178f131a7299e5f24b03c15451d7df5734755e")
if __name__=="__main__":unittest.main()
