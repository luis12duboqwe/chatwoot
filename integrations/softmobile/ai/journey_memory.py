#!/usr/bin/env python3
"""Privacy-restricted deterministic sales memory.

Only derive a few product preferences from up to four previous buyer
messages after local PII filtering. No raw history is sent to Groq.
"""
import re
from typing import Any
from sales_context import MAX_PREVIOUS,MODELS,STORAGE,CITY,safe_previous
from variant_preference import expected_selection

COMPARE=re.compile(
 r"\b(?:cu[aá]nto (?:cuesta|vale|sale)|cuesta|vale|sale|mismo precio|qu[eé] precio|precio (?:tiene|del)|"
 r"cu[aá]l (?:sale|conviene)|comparar|comparaci[oó]n|diferencia|"
 r"y (?:el|la|los|las) (?:de|del))\b",re.I)
NEGATE=re.compile(r"\b(?:no quiero|no prefiero|no me gusta|descarto)\b",re.I)
PREFER=re.compile(
 r"\b(?:prefiero|mejor|quiero|me quedo|elijo|busco|ahora quiero|"
 r"lo quiero|me sirve|necesito|el que quiero)\b",re.I)
ONE_COLOR=re.compile(r"\b(?:negro|negra|azul|blanco|blanca|verde|rojo|roja|dorado|dorada|morado|morada|plata|gris|titanio)\b",re.I)

def history_snapshot(messages:Any)->dict:
 if not isinstance(messages,list) or len(messages)>MAX_PREVIOUS:
  return {}
 state={}
 for raw in messages:
  clean=safe_previous(raw)
  if not clean:continue
  txt=clean.lower()
  pref=expected_selection(clean)
  # "No quiero negro, mejor azul" contains an explicit new choice.
  # A rejected color alone must clear the previously selected color.
  affirmative=[m for m in PREFER.finditer(txt)
      if not txt[max(0,m.start()-3):m.start()].endswith("no ")]
  is_comparison=bool(COMPARE.search(txt)) and not bool(affirmative)
  has_negation=bool(NEGATE.search(txt))
  model_hits=[]
  for rx,label in MODELS:
   for match in rx.finditer(txt):
    model_hits.append(label+(" " if label=="iPhone" else "")+
      match.group(1)+(" "+match.group(2).title() if match.group(2) else ""))
  named=set(model_hits)
  if len(named)==1:
   if "model" not in state or not is_comparison:
    state["model"]=model_hits[-1]
  elif len(named)>1 and bool(affirmative):
   state.pop("model",None)
  has_capacity=bool(STORAGE.search(txt))
  has_color=bool(ONE_COLOR.search(txt))
  if pref["ambiguous"]:
   if has_capacity:state.pop("storage_gb",None)
   if has_color:state.pop("color_options",None)
  else:
   # Negation with an explicit affirmative replacement still updates the
   # preferred option; pure rejection must not keep the rejected SKU.
   if has_negation and not affirmative:
    if has_capacity and state.get("storage_gb") in {int(x) for x in STORAGE.findall(txt)}:
     state.pop("storage_gb",None)
    if has_color and state.get("color_options") in {
       {"negra":"negro","blanca":"blanco","roja":"rojo","dorada":"dorado",
        "morada":"morado"}.get(x.lower(),x.lower()) for x in ONE_COLOR.findall(txt)}:
     state.pop("color_options",None)
   else:
    if pref["storage_gb"] is not None and (not is_comparison or "storage_gb" not in state):
     state["storage_gb"]=pref["storage_gb"]
    if pref["color"] is not None and (not is_comparison or "color_options" not in state):
     state["color_options"]=pref["color"]
  cities=[(txt.rfind(s),v) for s,v in CITY.items()
     if re.search(r"\b"+re.escape(s)+r"\b",txt)]
  if cities:state["city"]=max(cities)[1]
 return state
