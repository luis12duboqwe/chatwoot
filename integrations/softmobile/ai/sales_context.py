#!/usr/bin/env python3
"""PII-minimized commercial context for the existing private Groq copilot.

Only a small tuple of product preferences may leave Chatwoot. Never forward
full prior chats, addresses, contact details, order IDs or payment details.
The last buyer message is supplied independently and takes precedence.
"""
import re
from typing import Any

MAX_PREVIOUS=4
MAX_CHARS=420
MODELS=(
 (re.compile(r"\b(?:iphone|ipone|iphon|ifon)\s*(11|12|13|14|15|16|17)(?:\s+(pro\s+max|pro|plus|mini|air))?\b",re.I),"iPhone"),
 (re.compile(r"\b(?:samsung\s+|galaxy\s+)?s\s*(2[0-6])(?:\s+(ultra|plus|fe))?\b",re.I),"Samsung S"),
 (re.compile(r"\b(?:samsung\s+|galaxy\s+)?a\s*(\d{2})(?:\s+(5g|4g))?\b",re.I),"Samsung A"),
 (re.compile(r"\b(?:samsung\s+|galaxy\s+)?note\s*(\d{1,2})(?:\s+(ultra|plus))?\b",re.I),"Samsung Note "),
)
STORAGE=re.compile(r"\b(64|128|256|512|1024)\s*(?:gb|gigas?)\b",re.I)
COLORS=re.compile(r"\b(negro|negra|azul|blanco|blanca|verde|rojo|roja|dorado|dorada|morado|morada|plata|gris|titanio)\b",re.I)
CITY={
 "san pedro sula":"San Pedro Sula",
 "choloma":"Choloma",
 "tegucigalpa":"Tegucigalpa",
 "la ceiba":"La Ceiba",
 "comayagua":"Comayagua"
}
ALIASES={"negra":"negro","blanca":"blanco","roja":"rojo","dorada":"dorado","morada":"morado"}
SENSITIVE=re.compile(
 r"(?:[\w.+-]+@[\w.-]+\.[a-z]{2,}|https?://\S+|"
 r"(?<!\d)(?:\+?504[\s-]?)?[2-9]\d{3}[\s-]?\d{4}(?!\d)|"
 r"(?<!\d)(?:\d[\s-]?){13,19}(?!\d)|"
 r"\b(?:contrasena|contraseña|codigo|código|pin|cvv|otp|pasaporte|"
 r"identidad|clave|direccion|dirección|calle|avenida|colonia|residencial|"
 r"numero de pedido|número de pedido|transferencia|cuenta bancaria|"
 r"banco|tarjeta|depósito|deposito)\b)",re.I)

def safe_previous(raw: Any)->str|None:
 if not isinstance(raw,str) or not 4<=len(raw)<=MAX_CHARS:
  return None
 if SENSITIVE.search(raw):return None
 return raw.strip()

def preference_snapshot(messages: Any)->dict:
 if not isinstance(messages,list) or len(messages)>MAX_PREVIOUS:return {}
 result={}
 for message in messages:
  text=safe_previous(message)
  if not text:continue
  lower=text.lower()
  hits=[]
  for rx,prefix in MODELS:
   for m in rx.finditer(lower):
    hits.append((m.start(),prefix+(" " if prefix=="iPhone" else "")+m.group(1)+(" "+m.group(2).title() if m.group(2) else "")))
  if hits:
   # A message naming multiple distinct phones may be a comparison. Do
   # not silently select a particular SKU as the customer's preference.
   named={x[1] for x in hits}
   if len(named)==1:
    result["model"]=hits[-1][1]
   else:
    result.pop("model",None)
  capacity=[int(x) for x in STORAGE.findall(lower)]
  if capacity:
   if len(set(capacity))==1:result["storage_gb"]=capacity[0]
   else:result.pop("storage_gb",None)
  colors=[ALIASES.get(c.lower(),c.lower()) for c in COLORS.findall(lower)]
  if colors:
   if len(set(colors))==1:result["color_options"]=colors[0]
   else:result.pop("color_options",None)
  # City is only a city name from a fixed, non-address whitelist.
  city_found=[(lower.rfind(key),name) for key,name in CITY.items()
       if re.search(r"\b"+re.escape(key)+r"\b",lower)]
  if city_found:
   result["city"]=max(city_found)[1]
 return result
