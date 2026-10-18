import unittest
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import training_inventory as t

class TrainingInventoryUnitTests(unittest.TestCase):
 def setUp(self):self.inv=t.SimulationInventory()
 def test_all_skus_are_fictional_and_unique(self):
  records=self.inv.catalog()
  self.assertEqual(len(records),12)
  self.assertTrue(all(x["sku"].startswith("SIM-") for x in records))
  self.assertEqual(len({x["sku"] for x in records}),len(records))
  self.assertEqual(sum(x["units"] for x in records),23)
 def test_known_color_without_stock_is_not_offered(self):
  q=self.inv.quote("iPhone 14 Pro Max",256,"dorado")
  self.assertEqual(q.status,"out_of_stock")
  self.assertEqual(q.record["units"],0)
  self.assertEqual(len(q.alternatives),1)
  self.assertEqual(q.alternatives[0]["color"],"Negro")
 def test_unknown_model_has_no_inventory(self):
  self.assertEqual(self.inv.quote("iPhone 99",256,"Negro").status,"not_found")
 def test_disallows_invalid_sku_or_duplicate(self):
  rows=deepcopy(t.SEED);rows[1]["sku"]=rows[0]["sku"]
  with self.assertRaises(ValueError):t.SimulationInventory(rows)
  rows=deepcopy(t.SEED);rows[0]["sku"]="REAL-IPHONE"
  with self.assertRaises(ValueError):t.SimulationInventory(rows)
 def test_disallows_negative_and_boolean_quantities(self):
  for value in (-1,True,0.5):
   rows=deepcopy(t.SEED);rows[0]["units"]=value
   with self.subTest(value=value),self.assertRaises(ValueError):t.SimulationInventory(rows)
 def test_returns_deep_copies(self):
  value=self.inv.catalog();value[0]["units"]=999
  self.assertEqual(self.inv.catalog()[0]["units"],3)
 def test_hold_release_and_exhausted_stock(self):
  sku="SIM-S23U-256-BLK"
  hold=self.inv.hold(sku,1)
  self.assertTrue(hold)
  self.assertEqual(self.inv.quote("Samsung S23 Ultra",256,"negro").status,"out_of_stock")
  self.assertIsNone(self.inv.hold(sku,1))
  self.assertTrue(self.inv.release(hold))
  self.assertFalse(self.inv.release(hold))
  self.assertEqual(self.inv.quote("Samsung S23 Ultra",256,"Negro").status,"in_stock")
 def test_checkout_is_fake_and_idempotent(self):
  h=self.inv.hold("SIM-IPH12-128-RED",1)
  r=self.inv.checkout(h)
  self.assertEqual(r["status"],"simulated_only")
  self.assertIsNone(self.inv.checkout(h))
  self.assertIsNone(self.inv.hold("SIM-IPH12-128-RED",1))
  self.assertEqual(set(r),{"status","sku","total_lps"})
 def test_price_change_does_not_persist_to_new_instance(self):
  first=self.inv.quote("iPhone 13",128,"Blanco").record["price_lps"]
  self.inv.reprice("SIM-IPH13-128-WHT",first+1000)
  self.assertEqual(self.inv.quote("iPhone 13",128,"Blanco").record["price_lps"],first+1000)
  self.assertEqual(t.SimulationInventory().quote("iPhone 13",128,"Blanco").record["price_lps"],first)
 def test_blocks_negative_holds_and_prices(self):
  with self.assertRaises(ValueError):self.inv.hold("SIM-IPH15-128-BLU",-1)
  with self.assertRaises(ValueError):self.inv.reprice("SIM-IPH15-128-BLU",0)
 def test_many_simulated_buyers_cannot_oversell(self):
  sku="SIM-IPH14PM-256-BLK"
  # Thirty-two simultaneous fictional customers compete for three units.
  def buyer(_):
   hold=self.inv.hold(sku,1)
   if hold:self.inv.checkout(hold)
   return hold
  with ThreadPoolExecutor(max_workers=16) as pool:
   results=list(pool.map(buyer,range(32)))
  won=[x for x in results if x is not None]
  self.assertEqual(len(won),3)
  self.assertEqual(len(set(won)),3)
  self.assertEqual(self.inv.quote("iPhone 14 Pro Max",256,"Negro").status,"out_of_stock")
  self.assertEqual(sum(x["units"] for x in self.inv.catalog()),20)
 def test_simulated_holds_freeze_selected_price_even_if_edited(self):
  sku="SIM-IPH15-128-BLU"
  before=self.inv.quote("iPhone 15",128,"Azul").record["price_lps"]
  ticket=self.inv.hold(sku,1)
  self.inv.reprice(sku,before+1200)
  paid=self.inv.checkout(ticket)
  self.assertEqual(paid["total_lps"],before)
  self.assertEqual(self.inv.quote("iPhone 15",128,"Azul").record["price_lps"],before+1200)
 def test_uses_distinct_state_per_simulated_training_run(self):
  a=t.SimulationInventory();b=t.SimulationInventory()
  a.hold("SIM-IPH12-128-RED")
  self.assertEqual(a.quote("iPhone 12",128,"Rojo").status,"out_of_stock")
  self.assertEqual(b.quote("iPhone 12",128,"Rojo").status,"in_stock")
if __name__=="__main__":unittest.main()
