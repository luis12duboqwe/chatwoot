#!/usr/bin/env python3
"""In-memory fictitious phone inventory for *offline testing only*.

Never connects to the public bot, payment providers, Chatwoot, real ERP, or
Google Sheets. Training fixtures are NEVER authoritative customer quotes.
"""
from copy import deepcopy
from dataclasses import dataclass
import re
import unicodedata
from threading import RLock

LABEL="SIMULACIÓN / INVENTARIO FICTICIO — NO OFRECER A CLIENTES"
CATALOG_VERSION="training-fixture-20261018-v1"

# Fictitious sample inventory; prices, units, condition and location are
# invented for automated testing. They are NOT SoftMobile supplier offers.
SEED=[
 {"sku":"SIM-IPH14PM-256-BLK","brand":"Apple","model":"iPhone 14 Pro Max","capacity_gb":256,"color":"Negro","price_lps":18950,"units":3},
 {"sku":"SIM-IPH14PM-256-GLD","brand":"Apple","model":"iPhone 14 Pro Max","capacity_gb":256,"color":"Dorado","price_lps":18875,"units":0},
 {"sku":"SIM-IPH14PM-128-BLK","brand":"Apple","model":"iPhone 14 Pro Max","capacity_gb":128,"color":"Negro","price_lps":16990,"units":4},
 {"sku":"SIM-IPH13-128-WHT","brand":"Apple","model":"iPhone 13","capacity_gb":128,"color":"Blanco","price_lps":10850,"units":2},
 {"sku":"SIM-IPH13-128-BLK","brand":"Apple","model":"iPhone 13","capacity_gb":128,"color":"Negro","price_lps":10950,"units":0},
 {"sku":"SIM-IPH15-128-BLU","brand":"Apple","model":"iPhone 15","capacity_gb":128,"color":"Azul","price_lps":16500,"units":5},
 {"sku":"SIM-IPH15-256-BLK","brand":"Apple","model":"iPhone 15","capacity_gb":256,"color":"Negro","price_lps":18400,"units":2},
 {"sku":"SIM-S24U-256-BLU","brand":"Samsung","model":"Samsung S24 Ultra","capacity_gb":256,"color":"Azul","price_lps":23900,"units":2},
 {"sku":"SIM-S24U-256-BLK","brand":"Samsung","model":"Samsung S24 Ultra","capacity_gb":256,"color":"Negro","price_lps":23750,"units":0},
 {"sku":"SIM-S23U-256-BLK","brand":"Samsung","model":"Samsung S23 Ultra","capacity_gb":256,"color":"Negro","price_lps":17800,"units":1},
 {"sku":"SIM-S22U-128-BLK","brand":"Samsung","model":"Samsung S22 Ultra","capacity_gb":128,"color":"Negro","price_lps":12100,"units":3},
 {"sku":"SIM-IPH12-128-RED","brand":"Apple","model":"iPhone 12","capacity_gb":128,"color":"Rojo","price_lps":8200,"units":1},
]
REQUIRED={"sku","brand","model","capacity_gb","color","price_lps","units"}
SKU=re.compile(r"^SIM-[A-Z0-9-]{7,40}$")

def normalize(value):
 s=unicodedata.normalize("NFKD",str(value or "")).casefold()
 s="".join(ch for ch in s if not unicodedata.combining(ch))
 return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9]+"," ",s)).strip()

def validate(rows):
 if not isinstance(rows,list) or not 1<=len(rows)<=60:raise ValueError("Invalid inventory size")
 seen=set()
 for item in rows:
  if not isinstance(item,dict) or set(item)!=REQUIRED:raise ValueError("Bad inventory fields")
  sku=item["sku"]
  if not isinstance(sku,str) or not SKU.fullmatch(sku) or sku in seen:raise ValueError("Invalid simulated SKU")
  seen.add(sku)
  for field in ("brand","model","color"):
   if not isinstance(item[field],str) or not 2<=len(item[field])<=55:raise ValueError("Invalid label")
  for key,lo,hi in (("capacity_gb",32,1024),("price_lps",1,100000),("units",0,500)):
   v=item[key]
   if type(v) is not int or not lo<=v<=hi:raise ValueError("Invalid simulated amount")
 return rows

@dataclass
class Quote:
 status:str
 record:dict|None
 alternatives:list

class SimulationInventory:
 def __init__(self,records=None):
  self._lock=RLock()
  self._items={r["sku"]:deepcopy(r) for r in validate(deepcopy(SEED if records is None else records))}
  self._holds={}
  self._counter=0
  self._events=[]
 def catalog(self):
  with self._lock:
    return deepcopy(list(self._items.values()))
 def quote(self,model,capacity_gb=None,color=None):
  with self._lock:
    if not model or not isinstance(model,str):return Quote("missing_model",None,[])
    if capacity_gb is not None and (type(capacity_gb) is not int or capacity_gb<=0):
     raise ValueError("Invalid requested capacity")
    key=normalize(model);shade=normalize(color) if color else None
    matching=[v for v in self._items.values() if normalize(v["model"])==key
              and (capacity_gb is None or v["capacity_gb"]==capacity_gb)]
    if not matching:return Quote("not_found",None,[])
    chosen=[v for v in matching if shade is None or normalize(v["color"])==shade]
    available=[v for v in chosen if v["units"]>0]
    if available:return Quote("in_stock",deepcopy(available[0]),deepcopy([v for v in matching if v["units"]>0 and v["sku"]!=available[0]["sku"]]))
    # Never present an out-of-stock color as available.
    others=[v for v in matching if v["units"]>0]
    return Quote("out_of_stock",deepcopy(chosen[0]) if chosen else None,deepcopy(others))
 def hold(self,sku,quantity=1):
  with self._lock:
    if type(quantity) is not int or quantity<=0 or quantity>10:raise ValueError("Invalid quantity")
    record=self._items.get(sku)
    if not record or record["units"]<quantity:return None
    record["units"]-=quantity
    self._counter+=1
    token="LAB-HOLD-"+str(self._counter).zfill(5)
    self._holds[token]={"sku":sku,"quantity":quantity,"unit_price":record["price_lps"]}
    self._events.append({"action":"hold","sku":sku,"quantity":quantity})
    return token
 def release(self,token):
  with self._lock:
    hold=self._holds.pop(token,None)
    if not hold:return False
    self._items[hold["sku"]]["units"]+=hold["quantity"]
    self._events.append({"action":"release","sku":hold["sku"],"quantity":hold["quantity"]})
    return True
 def checkout(self,token):
  with self._lock:
    # Training-only: never captures payment, PII, an address or a real order.
    hold=self._holds.pop(token,None)
    if not hold:return None
    self._events.append({"action":"simulated_checkout","sku":hold["sku"],"quantity":hold["quantity"]})
    return {"status":"simulated_only","sku":hold["sku"],"total_lps":hold["quantity"]*hold["unit_price"]}
 def reprice(self,sku,new_lps):
  with self._lock:
    if type(new_lps) is not int or not 1<=new_lps<=100000:raise ValueError("Invalid price")
    if sku not in self._items:raise ValueError("Unknown fictitious SKU")
    old=self._items[sku]["price_lps"]
    self._items[sku]["price_lps"]=new_lps
    self._events.append({"action":"simulated_price_change","sku":sku,"old_lps":old,"new_lps":new_lps})
 def events(self):
  with self._lock:
    return deepcopy(self._events)
