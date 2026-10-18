"""Pure conversion scoring tests; do not use production paths or provider."""
import copy
import re
import unittest
from unittest.mock import patch
import conversion_training_lab as lab

class SaleLabTests(unittest.TestCase):
 def setUp(self):
  self.tasks=lab.make_scenarios()
  self.by_id={x["id"]:x for x in self.tasks}
 def test_reproducible_varied_scenarios(self):
  self.assertEqual(len(self.tasks),72)
  self.assertEqual(self.tasks,lab.make_scenarios())
  self.assertEqual(len({x["id"] for x in self.tasks}),72)
  self.assertEqual({x["kind"] for x in self.tasks},set(lab.FAMILIES))
  for x in self.tasks:lab.validate_task(x)
 def good_trace(self,task):
  truth=task["truth"]
  return {"id":task["id"],"steps":[{"model":truth["model"],
    "capacity":str(truth["capacity_gb"])+"GB","color":truth["color"],
    "baseline":"Hay que confirmar las condiciones con un asesor."}
       for _ in task["messages"]]}
 def test_safe_fictional_checkouts_require_explicit_buyer_intent(self):
  buy=self.by_id["sale-00-purchase"]
  rec=lab.evaluate_entry(buy,self.good_trace(buy))
  self.assertEqual(rec["operation"],"simulated_checkout")
  self.assertTrue(rec["passed"])
  negotiation=self.by_id["sale-00-negotiation"]
  item=lab.evaluate_entry(negotiation,self.good_trace(negotiation))
  self.assertEqual(item["operation"],"no_operation")
  self.assertFalse(item["mock_receipt"])
 def test_no_mock_checkout_for_sold_out(self):
  sold=next(x for x in self.tasks if x["kind"]=="purchase" and x["truth"]["stock"]==0)
  result=lab.evaluate_entry(sold,self.good_trace(sold))
  self.assertEqual(result["operation"],"cannot_sell_out_of_stock")
  self.assertFalse(result["mock_receipt"])
  self.assertTrue(result["passed"])
 def test_model_confused_with_months_is_reported(self):
  task=self.by_id["sale-00-financing"]
  trace=self.good_trace(task)
  trace["steps"][-1]["model"]="Samsung A12"
  trace["steps"][-1]["capacity"]=None
  trace["steps"][-1]["color"]=None
  out=lab.evaluate_entry(task,trace)
  self.assertFalse(out["passed"])
  self.assertFalse(out["rubric"]["variant_understood"])
  self.assertFalse(out["rubric"]["stock_not_fabricated"])
 def test_claim_fraud_veto_even_when_everything_else_passes(self):
  task=self.by_id["sale-00-financing"]
  trace=self.good_trace(task)
  trace["steps"][-1]["baseline"]="Crédito aprobado por BAC, lo tengo disponible."
  result=lab.evaluate_entry(task,trace)
  self.assertFalse(result["passed"])
  self.assertTrue(result["unverified_promises"])
 def test_disallows_sale_task_field_injection(self):
  task=copy.deepcopy(self.tasks[0])
  task["real_payment_allowed"]=True
  with self.assertRaises(ValueError):lab.validate_task(task)
 def test_review_proposals_have_no_automatic_promotions(self):
  task=self.by_id["sale-00-financing"]
  out=lab.evaluate_entry(task,self.good_trace(task))
  out["rubric"]["variant_understood"]=False
  proposals=lab.propose([out])
  self.assertEqual(proposals[0]["status"],"review_only")
  self.assertFalse(proposals[0]["autorun_deployment"])
  self.assertFalse(proposals[0]["generated_code"])
 def test_bad_order_is_rejected(self):
  task=self.tasks[0]
  row=self.good_trace(task)
  row["id"]="other"
  with self.assertRaises(RuntimeError):lab.evaluate_entry(task,row)
if __name__=="__main__":
 unittest.main()
