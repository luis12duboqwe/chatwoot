import unittest,copy
import issue_resolution_queue as q
import test_issue_triage as fixtures
class QueueTests(unittest.TestCase):
 def test_reproduced_correlated_signal_needs_independent_review(self):
  issue=copy.deepcopy(fixtures.CASE)
  replay={"results":[{"id":issue["id"],"outcome":"previous_flags_reproduced",
                      "new_flags":["payment_choice_repeat"]}]}
  report=q.build([issue],replay)
  self.assertEqual(report["unreviewed_clusters"],1)
  self.assertTrue(report["clusters"][0]["corroborated_by_ai"])
  self.assertEqual(report["real_customer_defects_proven"],0)
  self.assertFalse(report["clusters"][0]["autonomous_code_promotion_authorized"])
 def test_unreproduced_flags_are_not_confirmed(self):
  issue=copy.deepcopy(fixtures.CASE)
  replay={"results":[{"id":issue["id"],"outcome":"previous_flags_no_longer_present",
                      "new_flags":[]}]}
  report=q.build([issue],replay)
  self.assertEqual(report["unreviewed_clusters"],0)
 def test_deduplicated_triage_cluster(self):
  a=copy.deepcopy(fixtures.CASE);b=copy.deepcopy(a);b["id"]="synthetic2"
  replay={"results":[{"id":x["id"],"outcome":"previous_flags_reproduced",
                      "new_flags":["payment_choice_repeat"]} for x in (a,b)]}
  out=q.build([a,b],replay)
  self.assertEqual(out["unreviewed_clusters"],1)
  self.assertEqual(out["clusters"][0]["synthetic_examples"],2)
 def test_invalid_data_fails_closed(self):
  with self.assertRaises(ValueError):q.build([],{"results":"bad"})
if __name__=="__main__":unittest.main()
