"""All promotion unit scenarios run against temporary files and fake installers."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch
import combined_pilot_promotion as p

class BundledPromotionTests(unittest.TestCase):
 def test_fixed_base_required_no_arbitrary_code_generation(self):
  with self.assertRaises(ValueError):p.prepare("arbitrary model authored code",p.learner.empty_pack())
 def test_history_cap_ignores_non_deploy_entries(self):
  with patch.object(p,"_load",return_value=[
   {"day":"2099-10-18","status":"daily_deployment_cap"},
   {"day":"2099-10-18","promoted":False}]):
   self.assertEqual(p.deployed_today("2099-10-18"),0)
  with patch.object(p,"_load",return_value=[{"day":"2099-10-18","promoted":True}]):
   self.assertEqual(p.deployed_today("2099-10-18"),1)
 def test_already_promoted_today_blocks_installer(self):
  day=p.datetime.now(p.timezone.utc).date().isoformat()
  with patch.object(p,"_load",return_value=[{"day":day,"promoted":True}]):
   install=Mock()
   x=p.promote(installer=install)
   self.assertEqual(x["status"],"daily_deployment_cap")
   install.assert_not_called()
 def fixtures(self,container,tamper=False):
  root=Path(container)
  live=root/"bot.rb";live.write_text("safe original")
  base=live.read_text()
  candidate=base+"\ncombined safe changes\n"
  stage=root/"stage";stage.mkdir()
  archive=stage/"combined-test.rb"
  archive.write_text("malicious tampered" if tamper else candidate)
  review={"status":"verified_staged","revision":p.REVISION,
   "baseline_sha256":p.digest(base),"candidate_sha256":p.digest(candidate),
   "stage_file":archive.name}
  def load(path,default=None):
   if path==p.learner.HISTORY:return []
   if path==p.REVIEW:return review
   if path==p.learner.STORE:return p.learner.empty_pack()
   raise AssertionError("Unexpected private file requested")
  return live,candidate,stage,load
 def test_tampered_staged_candidate_is_not_deployed(self):
  with tempfile.TemporaryDirectory() as temp:
   live,candidate,stage,load=self.fixtures(temp,tamper=True)
   install=Mock()
   with patch.object(p.learner,"BOT",live),patch.object(p,"STAGING",stage),        patch.object(p,"_load",side_effect=load),patch.object(p,"prepare",return_value=candidate),patch.object(p,"independent_quality_approved",return_value=True):
    out=p.promote(installer=install)
   self.assertEqual(out["status"],"staged_candidate_tampered")
   install.assert_not_called()
   self.assertEqual(live.read_text(),"safe original")
 def test_still_evaluates_when_cup_available_but_never_sends_messages(self):
  with tempfile.TemporaryDirectory() as temp:
   live,candidate,stage,load=self.fixtures(temp)
   install=Mock()
   def badcheck(*args):return {"status":"mock_inventory_regression_rejected"}
   with patch.object(p.learner,"BOT",live),patch.object(p,"STAGING",stage),        patch.object(p,"_load",side_effect=load),patch.object(p,"prepare",return_value=candidate),patch.object(p,"independent_quality_approved",return_value=True):
    out=p.promote(installer=install,validator=badcheck)
   self.assertEqual(out["status"],"independent_gates_failed")
   install.assert_not_called()
 def test_simulated_promotion_success_only_after_post_validation(self):
  with tempfile.TemporaryDirectory() as temp:
   live,candidate,stage,load=self.fixtures(temp)
   def install(text):
    live.write_text(text)
    return {"status":"deployed","backup_name":"fixture.bak"}
   checks=Mock(return_value={"status":"gates_passed","tested":72})
   written=[]
   with patch.object(p.learner,"BOT",live),patch.object(p,"STAGING",stage),        patch.object(p,"_load",side_effect=load),patch.object(p,"prepare",return_value=candidate),        patch.object(p,"_atomic_json",side_effect=lambda path,value:written.append((path,value))),patch.object(p,"independent_quality_approved",return_value=True):
    out=p.promote(installer=install,validator=checks)
   self.assertEqual(out["status"],"pilot_deployed_pending_retest")
   self.assertTrue(out["promoted"])
   self.assertEqual(checks.call_count,2)
   self.assertEqual(out["public_messages_sent_during_tests"],0)
   self.assertEqual(len(written),1)
 def test_postdeployment_validation_failure_rolls_back(self):
  with tempfile.TemporaryDirectory() as temp:
   live,candidate,stage,load=self.fixtures(temp)
   def install(text):
    live.write_text(text)
    return {"status":"deployed","backup_name":"fixture.bak"}
   results=iter([{"status":"gates_passed"},{"status":"fail"}])
   def restore(previous,expected):
    self.assertEqual(live.read_text(),expected)
    live.write_text(previous)
   with patch.object(p.learner,"BOT",live),patch.object(p,"STAGING",stage),        patch.object(p,"_load",side_effect=load),patch.object(p,"prepare",return_value=candidate),        patch.object(p,"restore_before_going_live",side_effect=restore),patch.object(p,"independent_quality_approved",return_value=True):
    out=p.promote(installer=install,validator=lambda *_:next(results))
   self.assertEqual(out["status"],"postdeploy_failed_rolled_back")
   self.assertFalse(out["promoted"])
   self.assertEqual(live.read_text(),"safe original")
 def test_missing_independent_quality_approval_blocks_install(self):
  with tempfile.TemporaryDirectory() as temp:
   live,candidate,stage,load=self.fixtures(temp)
   installer=Mock()
   with patch.object(p.learner,"BOT",live),patch.object(p,"STAGING",stage),        patch.object(p,"_load",side_effect=load),patch.object(p,"prepare",return_value=candidate),        patch.object(p,"independent_quality_approved",return_value=False):
    res=p.promote(installer=installer)
   self.assertEqual(res["status"],"independent_ai_quality_pending")
   installer.assert_not_called()
 def test_promotion_time_guard_is_explicitly_one_per_day(self):
  self.assertEqual(p.DAILY_CAP,1)
  self.assertFalse(p.run.__defaults__[0])
if __name__=="__main__":unittest.main()
