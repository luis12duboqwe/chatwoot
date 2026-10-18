#!/usr/bin/env python3
"""Deterministic stress-test guard for synthetic variant parsing in isolation."""
import unittest
from unittest.mock import patch
import sandbox_stress as stress

class StressTests(unittest.TestCase):
 def test_150_reproducible_cases_without_pii(self):
  cases=stress.generate()
  self.assertEqual(len(cases),150)
  self.assertEqual(cases,stress.generate())
  self.assertEqual(len({c[0] for c in cases}),150)
  self.assertTrue(all(len(c[1])==2 and c[2] in stress.CAPACITIES for c in cases))
  self.assertTrue(all(c[3].lower() in stress.COLORS for c in cases))
 def test_stress_test_requires_improvement_without_regression(self):
  cases=stress.generate()
  correct=[{"id":k,"capacity":cap,"color":color} for k,_,cap,color in cases]
  bad=[dict(x) for x in correct]
  bad[0]["color"]="Violeta"
  with patch.object(stress.sandbox,"isolated_run",side_effect=[bad,correct]):
   result=stress.analyze("base","candidate")
  self.assertEqual(result["status"],"stress_passed")
  self.assertEqual(result["fixed"],1)
  self.assertFalse(result["regressions"])
 def test_stress_fail_closed_on_new_regression(self):
  cases=stress.generate()
  correct=[{"id":k,"capacity":cap,"color":color} for k,_,cap,color in cases]
  wrong=[dict(x) for x in correct]
  wrong[0]["capacity"]="32GB"
  with patch.object(stress.sandbox,"isolated_run",side_effect=[correct,wrong]):
   result=stress.analyze("base","candidate")
  self.assertEqual(result["status"],"stress_failed")
  self.assertEqual(len(result["regressions"]),1)

if __name__=="__main__":unittest.main()
