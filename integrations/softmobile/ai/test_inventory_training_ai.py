import unittest
from unittest.mock import patch
import inventory_training_ai as ai

class SyntheticInventoryBuyerTests(unittest.TestCase):
 def test_rejects_fake_sellers_and_leaked_data(self):
  with self.assertRaises(ValueError):
   ai.validate_generated({"scenarios":[{"messages":["Tengo un iPhone 15 128 GB azul",
     "Precio confirmado, depositá hoy 15000 lempiras"]}]})
 def test_rejects_unknown_catalog_product(self):
  with self.assertRaises(ValueError):
   ai.validate_generated({"scenarios":[{"messages":["Quiero iPhone 99 de 256 GB negro",
     "¿Lo tienen disponible?"]}]})
 def test_valid_fictional_customer_dialogue_passes(self):
  sample={"scenarios":[{"messages":[
   "Quiero iPhone 14 Pro Max 256 GB negro","¿Está disponible?"]}]}
  v=ai.validate_generated(sample)
  self.assertEqual(v[0]["id"],"ai-buyer-01")
  self.assertNotIn("price_lps",v[0])
 def test_lacks_selected_color_and_must_reject(self):
  with self.assertRaises(ValueError):
   ai.validate_generated({"scenarios":[{"messages":[
      "Quiero iPhone 14 Pro Max 256 GB","¿Lo tienen?"]}]})
 def test_no_enabled_flag_means_no_provider_consumption(self):
  with patch.dict(ai.os.environ,{"SOFTMOBILE_INVENTORY_AI_ENABLED":"false"}):
   outcome=ai.run_live(api=lambda *args:1,key="should_not_use")
   self.assertEqual(outcome["external_calls"],0)
if __name__=="__main__":unittest.main()
