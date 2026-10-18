#!/usr/bin/env python3
"""Deterministic private salesperson handoff; no orders, inventory, or PII.

Only allowlisted model, capacity, color, and coarse city are displayed. No
customer message, provider-authored field, phone or address is copied.
"""
import re
from journey_memory import history_snapshot
from variant_preference import expected_selection
from sales_context import MODELS,STORAGE,COLORS,CITY,ALIASES,preference_snapshot

VALID_STORAGE={64,128,256,512,1024,2048}
VALID_COLOR={"negro","azul","blanco","verde","rojo","dorado",
             "morado","plata","gris","titanio","plateado","rosa"}
VALID_CITY=set(CITY.values())
REJECT_COLOR=re.compile(r"\b(?:no quiero|no prefiero|descarto)\b",re.I)
PRICE=re.compile(r"\b(?:precio|descuento|presupuesto|cuanto cuesta|cuánto cuesta|promocion|promoción|barato)\b",re.I)
SHIPPING=re.compile(r"\b(?:envio|envío|entrega|retiro|retirar|recoger|despacho)\b",re.I)
PAYMENT=re.compile(r"\b(?:pago|cuotas|financiamiento|financiar(?:lo)?|tarjeta|banco|credito|crédito)\b",re.I)
TRADE=re.compile(r"\b(?:parte de pago|canje|reciben mi (?:celular|telefono|equipo)|entregar mi (?:celular|telefono))\b",re.I)
WARRANTY=re.compile(r"\b(?:garantia|garantía|accesorios|cargador|funda|regalias|regalías|seguro)\b",re.I)
BUY=re.compile(r"\b(?:quiero comprar|lo compro|lo llevo|me lo llevo|listo para comprar|comprarlo)\b",re.I)

def _verified_model(text):
 if not isinstance(text,str):return None
 for expression,prefix in MODELS:
  m=expression.fullmatch(text.strip())
  if m:
   return prefix+(" " if prefix=="iPhone" else "")+m.group(1)+(" "+m.group(2).title() if m.group(2) else "")
 return None

def _model_in_last(message):
 # An entire user sentence is untrusted. Reuse the verified tiny extractor,
 # but only if one unambiguous phone is mentioned.
 model=preference_snapshot([message]).get("model")
 return _verified_model(model) if model else None

def lead_facts(clean):
 if not isinstance(clean,dict):return {}
 context=clean.get("context",{})
 if not isinstance(context,dict):context={}
 current=clean.get("message","")
 if not isinstance(current,str):current=""
 result={}
 model=_verified_model(context.get("model"))
 if model:result["model"]=model
 cap=context.get("storage_gb")
 if isinstance(cap,(str,int)) and str(cap).isdigit() and int(cap) in VALID_STORAGE:
  result["storage_gb"]=int(cap)
 col=context.get("color_options")
 if isinstance(col,str):
  color=ALIASES.get(col.casefold(),col.casefold())
  if color in VALID_COLOR:result["color"]=color
 city=context.get("city")
 if isinstance(city,str) and city in VALID_CITY:result["city"]=city
 from groq_pilot import _comparison_only
 pref=expected_selection(current)
 # Price comparisons mention alternatives without changing selected variant.
 if not _comparison_only({"message":current}):
  picked=_model_in_last(current)
  if picked:result["model"]=picked
  if pref["ambiguous"]:
   result.pop("storage_gb",None)
   result.pop("color",None)
  else:
   if pref["storage_gb"] is not None:result["storage_gb"]=pref["storage_gb"]
   if pref["color"] is not None:result["color"]=pref["color"]
   # Rejecting an option without naming replacement unselects that option.
   if REJECT_COLOR.search(current) and pref["color"] is None:
    existing=result.get("color")
    if existing and existing in {ALIASES.get(x.casefold(),x.casefold()) for x in COLORS.findall(current)}:
     result.pop("color",None)
 latest_city=preference_snapshot([current]).get("city")
 if latest_city in VALID_CITY:result["city"]=latest_city
 return result

def followup_actions(clean):
 text=clean.get("message","") if isinstance(clean,dict) else ""
 if not isinstance(text,str):text=""
 # Deterministic, constrained and conditional: no invented commitments.
 if TRADE.search(text):return "Confirmar si existe canje o parte de pago y valorar el equipo; no prometer aceptación"
 if PAYMENT.search(text):return "Confirmar medios de pago y condiciones; nunca pedir datos de tarjeta"
 if BUY.search(text):return "Verificar existencia, precio y entrega antes de aceptar la compra"
 if SHIPPING.search(text):return "Confirmar destino, tienda, disponibilidad y plazo de entrega"
 if WARRANTY.search(text):return "Confirmar estado de la unidad, garantía y accesorios exactos"
 if PRICE.search(text):return "Confirmar precio vigente y promociones reales"
 return "Confirmar existencia, precio y condiciones con un asesor"

def private_lead_summary(clean):
 info=lead_facts(clean)
 fields=[
  ("Modelo",info.get("model")),
  ("Capacidad",str(info["storage_gb"])+" GB" if "storage_gb" in info else None),
  ("Color",info.get("color")),
  ("Ciudad",info.get("city")),
 ]
 parts=[k+": "+v for k,v in fields if v]
 details=" | ".join(parts) if parts else "Modelo y variante pendientes de confirmar"
 return "Ficha comercial: "+details+"\nPendiente: "+followup_actions(clean)
