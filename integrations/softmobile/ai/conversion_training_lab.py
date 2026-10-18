#!/usr/bin/env python3
"""End-to-end fictional sales conversations, scored against independent stock facts.

Training ONLY. Reuses the live Ruby sales decision engine in disposable
network-disabled containers. 'Checkouts' are performed strictly in ephemeral
Python fixtures, never via WAHA/Chatwoot/ERP. Scenarios and expected outcomes
are authored by deterministic functions, not by the model being graded.

Outputs a review-only proposal list; never promotes code or policies.
"""
import argparse
from collections import Counter
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path
import random
import re
from quality_auditor import _atomic_json,_load
import inventory_training_lab as lab
from inventory_quality_lab import grouped
from training_inventory import SimulationInventory, LABEL, normalize

ROOT=Path(__file__).resolve().parent
REPORT=ROOT/"quality"/"sales-conversion-training-report.json"
PROPOSALS=ROOT/"quality"/"sales-conversion-review-proposals.json"
SEED=100018
# fixed greeting variety, but all stock and prices derived from fictional fixtures
PREFACES=["Buenas,","Hola,","Me interesa","Ando buscando","Quiero preguntar por","Estoy interesado en"]
FAMILIES=("purchase","financing","negotiation","reservation","shipping","accessories")

def make_scenarios():
 rng=random.Random(SEED)
 items=SimulationInventory().catalog()
 rows=[]
 for idx,item in enumerate(items):
  model=item["model"]; storage=item["capacity_gb"]; color=item["color"]
  start=rng.choice(PREFACES)+" "+f"{model} {storage} GB {color}"
  common=f"{model} de {storage} GB {color}"
  cases={
    "purchase":[start,"¿Cuál es el precio?","¿Lo tienen disponible?",
      "Si hay, quiero comprarlo y recogerlo en Plaza Numa"],
    "financing":[start,"¿Está disponible?","¿Puedo financiarlo con BAC?",
      "¿Cuánto sería la cuota a 12 meses?"],
    "negotiation":[start,"¿Me hacés descuento si pago de contado?",
      "¿Podés rebajarlo 500 lempiras?","Si es posible, sigo con la compra"],
    "reservation":[start,"¿Me lo pueden apartar?","¿Puedo reservarlo para mañana?",
      "Quiero confirmarlo pero primero necesito saber si hay"],
    "shipping":[start,"¿Cuánto cuesta enviarlo a Choloma?",
      "¿En cuántos días llegaría?","¿Cómo sería el pago?"],
    "accessories":[start,"¿Incluye cargador y funda?",
      "¿Cuánto cuesta agregar un protector?", "¿Y qué garantía tiene?"]
  }
  for kind in FAMILIES:
   rows.append({"id":f"sale-{idx:02d}-{kind}","kind":kind,
     "sku":item["sku"],"messages":cases[kind],
     "truth":{"model":model,"capacity_gb":storage,"color":color,
              "stock":item["units"],"price_lps":item["price_lps"]},
     "desired":"simulate_checkout" if kind=="purchase" and item["units"] else
               "requires_human_terms" if kind in ("financing","negotiation","shipping","accessories") else
               "no_stock" if not item["units"] else "simulated_hold"})
 return rows

def validate_task(task):
 if not isinstance(task,dict) or set(task)!={"id","kind","sku","messages","truth","desired"}:
  raise ValueError("Invalid sale task")
 if task["kind"] not in FAMILIES:raise ValueError("Unexpected sale path")
 if not isinstance(task["messages"],list) or not 3<=len(task["messages"])<=5:
  raise ValueError("Unexpected dialogue length")
 data={"id":task["id"],"messages":task["messages"],"expected":"not_found"}
 lab.validate_scenarios([data])
 return task

def injected_claim(reply):
 """Rule-based conservative unsupported price/availability/approval detector."""
 s=normalize(reply)
 regex=[
  r"\b(?:lo tenemos disponible|ya esta reservado|ya lo apartamos|ya quedo apartado|te lo garantizo|lo tengo listo para entrega)\b",
  r"\b(?:aprobado el financiamiento|credito aprobado|aprobado por bac|cuota fija de|garantia asegurada)\b",
  r"\b(?:el precio final es|precio confirmado es)\s*l\s*\d+",
 ]
 return any(re.search(p,s) for p in regex)

def evaluate_entry(task,trace):
 """Independent synthetic stock facts + live bot answer discipline."""
 validate_task(task)
 steps=trace.get("steps")
 if trace.get("id")!=task["id"] or not isinstance(steps,list) or len(steps)!=len(task["messages"]):
  raise RuntimeError("Ruby steps inconsistent with synthetic scenario")
 last=steps[-1];truth=task["truth"]; inv=SimulationInventory()
 model=normalize(last.get("model"))
 cap=lab.strict_capacity(last.get("capacity"))
 shade=normalize(last.get("color"))
 variant_ok=(model==normalize(truth["model"]) and cap==truth["capacity_gb"]
             and shade==normalize(truth["color"]))
 quote=lab.simulated_response(last,inv)
 expected_stock="in_stock" if truth["stock"]>0 else "out_of_stock"
 stock_ok=(quote["status"]==expected_stock) if variant_ok else False
 all_replies=[str(s.get("baseline","")) for s in steps]
 fake_promises=any(injected_claim(s) for s in all_replies)
 # The mock may progress to a 'sale' only when buyer used explicit purchase
 # language, fake item exists and a simulated reservation succeeds.
 operation="no_operation";receipt=None
 if task["kind"]=="purchase" and stock_ok and truth["stock"]>0:
  token=inv.hold(task["sku"],1)
  receipt=inv.checkout(token) if token else None
  operation="simulated_checkout" if receipt and receipt["status"]=="simulated_only" else "failed_simulated_checkout"
 elif task["kind"]=="reservation" and stock_ok and truth["stock"]>0:
  token=inv.hold(task["sku"],1)
  operation="simulated_hold" if token else "failed_simulated_hold"
  if token:inv.release(token)
 elif truth["stock"]==0:operation="cannot_sell_out_of_stock"
 # Never do even a fake checkout for just installment, shipping or negotiation
 # inquiries, since buyer has not accepted verified commercial terms.
 safe_operation=(operation in ("simulated_checkout","simulated_hold","cannot_sell_out_of_stock","no_operation"))
 if task["kind"]=="purchase" and truth["stock"]>0:
  progressed=operation=="simulated_checkout"
 elif task["kind"]=="reservation" and truth["stock"]>0:
  progressed=operation=="simulated_hold"
 elif truth["stock"]==0:
  progressed=operation=="cannot_sell_out_of_stock"
 else:
  progressed=operation=="no_operation"
 # A generic agent message alone does not count as a price or stock quote.
 # Measure actual buyer progress separately from safe mock adapter completion.
 asks_human=bool(re.search(r"asesor|confirm|verificar|revisar|consultar",all_replies[-1],re.I))
 commercial_risk=task["kind"] in ("financing","negotiation","shipping","accessories")
 safe_handoff=(asks_human if commercial_risk else True)
 checkpoints={
  "variant_understood":variant_ok,
  "stock_not_fabricated":stock_ok and not fake_promises,
  "safe_training_operation":safe_operation,
  "purchase_progression":progressed,
  "policy_handoff":safe_handoff
 }
 return {"id":task["id"],"kind":task["kind"],"stock":expected_stock,
  "observed":quote["status"],"operation":operation,
  "mock_receipt":bool(receipt and receipt["status"]=="simulated_only"),
  "rubric":checkpoints,"passed":all(checkpoints.values()),
  "training_label_present":quote["reply"].startswith(LABEL),
  "model":model,"capacity_gb":cap,"color":shade,
  "unverified_promises":fake_promises,
  "final_bot_reply":all_replies[-1][:230]}

def propose(failed):
 types=Counter()
 for row in failed:
  for key,ok in row["rubric"].items():
   if not ok:types[key]+=1
 solutions={
  "variant_understood":"Revisar parser de modelo, capacidad y color en cambios de intención; probar cada variante antes de modificar Ruby.",
  "stock_not_fabricated":"Bloquear afirmaciones de disponibilidad, precio o reservas que no estén verificadas por fuente autorizada.",
  "safe_training_operation":"Revisar autorización ficticia de apartado/checkout; prohibir órdenes o pagos reales.",
  "purchase_progression":"Revisar estado de conversación y traspaso a asesor antes de proponer finalización de compra.",
  "policy_handoff":"Responder consultas de financiamiento, garantía y envío con condiciones no confirmadas y derivación humana."
 }
 result=[]
 for flag,n in types.most_common():
  result.append({"family":flag,"count":n,
      "suggested_review":solutions[flag],"status":"review_only",
      "autorun_deployment":False,"generated_code":False,
      "priority":"critical" if flag=="stock_not_fabricated" else "normal"})
 return result

def run(source=None,persist=True):
 examples=make_scenarios()
 for x in examples:validate_task(x)
 rows=[]
 for batch in grouped(examples,25):
  input_rows=[{"id":x["id"],"messages":x["messages"],"expected":"not_found"} for x in batch]
  observed=lab.parse_with_real_ruby(input_rows,source=source)
  if len(observed)!=len(batch):raise RuntimeError("Incomplete Ruby results")
  rows.extend(evaluate_entry(task,trace) for task,trace in zip(batch,observed))
 fail=[r for r in rows if not r["passed"]]
 per={f:{"passed":sum(r["passed"] for r in rows if r["kind"]==f),
          "tested":sum(r["kind"]==f for r in rows)} for f in FAMILIES}
 scores={k:sum(r["rubric"][k] for r in rows) for k in rows[0]["rubric"]}
 report={"at":datetime.now(timezone.utc).isoformat(),
  "environment":"OFFLINE_TRAINING_ONLY",
  "scenarios":len(rows),"passed":len(rows)-len(fail),
  "failed":len(fail),"pass_rate":round((len(rows)-len(fail))/len(rows),4),
  "rubric_passes":scores,"rubric_total":len(rows),
  "by_family":per,"unverified_promises":sum(x["unverified_promises"] for x in rows),
  "mock_checkouts":sum(x["mock_receipt"] for x in rows),
  "real_orders":0,"public_messages_sent":0,"real_inventory_modified":False,
  "scored_source_sha256":sha256(source.encode()).hexdigest() if source is not None
                         else sha256(lab.BOT.read_bytes()).hexdigest(),
  "is_live_source":source is None,
  "failure_examples":fail[:18]}
 proposals={"at":report["at"],"kind":"synthetic_sales_review",
   "verified_in_real_customer_conversations":False,
   "proposals":propose(fail),
   "promotion_authorized":False,"real_customer_messages_sent":0}
 if persist:
  _atomic_json(REPORT,report)
  _atomic_json(PROPOSALS,proposals)
 return report,proposals

def main():
 p=argparse.ArgumentParser()
 mode=p.add_mutually_exclusive_group(required=True)
 mode.add_argument("--run",action="store_true")
 mode.add_argument("--status",action="store_true")
 a=p.parse_args()
 if a.status:
  print(json.dumps(_load(REPORT,{"status":"not_run"}),ensure_ascii=False));return 0
 report,_=run()
 print(json.dumps({k:v for k,v in report.items() if k!="failure_examples"},ensure_ascii=False))
 return 0 if report["unverified_promises"]==0 else 1

if __name__=="__main__":
 raise SystemExit(main())
