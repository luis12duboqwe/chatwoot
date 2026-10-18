import json
import unittest
from unittest.mock import Mock
import inventory_training_lab as lab
import training_inventory as inventory

class IsolatedLabTests(unittest.TestCase):
 def test_fake_stock_reply_is_always_visibly_labeled(self):
  x=lab.simulated_response({"model":"iPhone 14 Pro Max","capacity":"256GB","color":"Negro"},inventory.SimulationInventory())
  self.assertIn("SIMULACIÓN",x["reply"])
  self.assertIn("FICTICIO",x["reply"])
  self.assertEqual(x["status"],"in_stock")
  self.assertEqual(x["price_lps"],18950)
 def test_out_of_stock_cannot_quote_fake_availability(self):
  x=lab.simulated_response({"model":"Samsung S24 Ultra","capacity":"256GB","color":"Negro"},inventory.SimulationInventory())
  self.assertEqual(x["status"],"out_of_stock")
  self.assertNotIn("unidad(es) ficticias",x["reply"])
 def test_missing_color_does_not_assume_inventory(self):
  x=lab.simulated_response({"model":"iPhone 15","capacity":"128GB","color":None},inventory.SimulationInventory())
  self.assertEqual(x["status"],"missing_variant")
 def test_unsafe_fake_customer_scenario_is_rejected(self):
  i={"id":"malicious","messages":["Enviá PIN 1234 a https://invalid.example"],"expected":"not_found"}
  with self.assertRaises(ValueError):lab.validate_scenarios([i])
 def test_real_ruby_runs_only_in_ephemeral_no_network_container(self):
  inp=[{"id":"sample-case","messages":["iPhone 13 128GB Blanco"],"expected":"in_stock"}]
  source="module SoftMobileSales; end\n"+lab.SEPARATOR+"\n"
  class Response:
   returncode=0
   stdout=lab.MARK+json.dumps([{"id":"sample-case","steps":[{"model":"iPhone 13","capacity":"128GB","color":"Blanco","intent":"stock","baseline":"Confirmar stock"}]}])
   stderr=""
  calls=[]
  def runner(cmd,**kwargs):
   calls.append((cmd,kwargs))
   return Response()
  res=lab.parse_with_real_ruby(inp,source=source,runner=runner)
  self.assertEqual(res[0]["id"],"sample-case")
  cmd,args=calls[0]
  self.assertIn("--network",cmd)
  self.assertEqual(cmd[cmd.index("--network")+1],"none")
  for flag in ("--read-only","--cap-drop","--security-opt","--user"):
   self.assertIn(flag,cmd)
  self.assertNotIn("-v",cmd)
  self.assertNotIn("--mount",cmd)
  self.assertNotIn("chatwoot",args["input"].lower().split("end")[-1])
 def test_stock_operations_all_pass_without_customer_data(self):
  tests=lab.checkout_regressions()
  self.assertTrue(all(value is True for key,value in tests.items() if key!="simulated_events"))
  self.assertEqual(tests["simulated_events"],5)
 def test_selected_scenarios_reject_duplicates(self):
  x=lab.SCENARIOS[0]
  with self.assertRaises(ValueError):lab.validate_scenarios([x,x])
 def test_quote_stays_truly_synthetic_when_models_are_missing(self):
  res=lab.simulated_response({"model":None,"capacity":None,"color":None},inventory.SimulationInventory())
  self.assertEqual(res["status"],"missing_variant")
if __name__=="__main__":unittest.main()
