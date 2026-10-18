import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import inventory_quality_lab as q

class InventoryQualityLabTests(unittest.TestCase):
 def test_scenarios_are_deterministic_independent_oracles(self):
  first=q.scenarios();second=q.scenarios()
  self.assertEqual(first,second)
  self.assertGreaterEqual(len(first),100)
  self.assertEqual(len(first),len({x["id"] for x in first}))
  self.assertTrue(all(set(x)=={"id","messages","expected","truth","kind"} for x in first))
 def test_buyer_parser_wrong_storage_is_detected(self):
  item=q.scenarios()[0]
  self.assertEqual(item["expected"],"variant")
  row={"id":item["id"],"steps":[{
    "model":item["truth"]["model"],"capacity":"999GB",
    "color":item["truth"]["color"],"baseline":"Precio pendiente de confirmar"}]}
  result=q.trace_eval(item,row,q.SimulationInventory())
  self.assertFalse(result["passed"])
  self.assertFalse(result["parser_match"])
 def test_unsafe_stock_claim_must_fail_even_if_variant_matches(self):
  item=q.scenarios()[0];t=item["truth"]
  row={"id":item["id"],"steps":[{
     "model":t["model"],"capacity":str(t["capacity_gb"])+"GB",
     "color":t["color"],"baseline":"Lo tengo disponible, depositá ahora"}]}
  result=q.trace_eval(item,row,q.SimulationInventory())
  self.assertFalse(result["passed"])
  self.assertTrue(result["unsafe_public_claim"])
 def test_metamorphic_full_lab_detects_and_stores_review_only(self):
  catalog={x["id"]:x for x in q.scenarios()}
  def parser(batch,source=None):
   output=[]
   for b in batch:
    original=catalog[b["id"]]
    truth=original["truth"]
    steps=[]
    for msg in b["messages"]:
     parsed={"model":truth["model"],"capacity":str(truth["capacity_gb"])+"GB",
        "color":truth["color"],"baseline":"Un asesor debe confirmar los detalles."}
     steps.append(parsed)
    if original["expected"]=="incomplete":steps[-1]["color"]=None
    # Inject ONE expected-mismatch fault as a proof the independent
    # oracle is capable of rejecting a broken live-Ruby parser.
    if b["id"]=="m00-t00":steps[-1]["capacity"]="512GB"
    output.append({"id":b["id"],"steps":steps})
   return output
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)
   fake=p/"sales-bot-v2.rb";fake.write_text("only-a-fixture")
   with patch.object(q,"REPORT",p/"report.json"),patch.object(q,"ISSUES",p/"issues.json"),patch.object(q.trainer,"BOT",fake):
    report=q.run(parser=parser)
    queue=json.loads((p/"issues.json").read_text())
  self.assertEqual(report["scenario_count"],108)
  self.assertEqual(report["failed"],1)
  self.assertEqual(report["safety_violations"],0)
  self.assertEqual(len(queue),1)
  self.assertEqual(queue[0]["status"],"training_review_only")
  self.assertFalse(queue[0]["may_deploy_automatically"])
  self.assertEqual(queue[0]["id"],"m00-t00")
 def test_batch_rejects_changed_order(self):
  def wrong(batch,source=None):
   return [{"id":"wrong-id","steps":[{}]} for _ in batch]
  with tempfile.TemporaryDirectory() as d:
   fake=Path(d)/"fake.rb";fake.write_text("mock")
   with patch.object(q.trainer,"BOT",fake),patch.object(q,"REPORT",Path(d)/"r.json"),patch.object(q,"ISSUES",Path(d)/"i.json"):
    with self.assertRaises(RuntimeError):q.run(parser=wrong)
if __name__=="__main__":unittest.main()
