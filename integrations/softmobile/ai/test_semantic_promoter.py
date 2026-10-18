import unittest
from unittest.mock import patch
import semantic_promoter as p
class PromotionTests(unittest.TestCase):
 def test_one_confirmed_promotion_blocks_second(self):
  self.assertEqual(p.daily_count([{"day":"today","promoted":True},{"day":"today","status":"cap"}],"today"),1)
  self.assertEqual(p.daily_count([{"day":"today","promoted":False},{"day":"today","status":"cap"}],"today"),0)
 def test_invalid_history_rejected(self):
  with self.assertRaises(ValueError):p.daily_count({"invalid":True},"today")
 def test_dry_run_never_calls_installer_when_cap_reached(self):
  with patch.object(p.learn,"HISTORY") as history:
   # patch loading inputs, never use production in unit tests
   with patch.object(p,"_load",return_value=[{"day":p.datetime.now(p.timezone.utc).date().isoformat(),"promoted":True}]):
    calls=[]
    out=p.assess(allow_deploy=True,installer=lambda *_:calls.append(True))
    self.assertEqual(out["status"],"daily_deployment_cap")
    self.assertEqual(calls,[])
if __name__=="__main__":unittest.main()
