#!/usr/bin/env python3
"""Deterministic preference constraints; ambiguity escalates instead of guessing.

No stock, checkout, commercial policy or customer identifiers are used.
Only the last buyer message is interpreted here, never the whole chat.
"""
import re
from typing import Any

GB = re.compile(r"(?<!\d)(64|128|256|512|1024|2048)\s*(?:gb|gigas?)\b",re.I)
COLOR_MAP={
 "negro":"negro","negra":"negro","azul":"azul","blanco":"blanco",
 "blanca":"blanco","rojo":"rojo","roja":"rojo","morado":"morado",
 "morada":"morado","violeta":"morado","dorado":"dorado","dorada":"dorado",
 "verde":"verde","gris":"gris","plateado":"plateado","plateada":"plateado",
 "rosa":"rosa","titanio":"titanio"
}
COLORS=re.compile(r"\b("+ "|".join(sorted(COLOR_MAP,key=len,reverse=True))+r")\b",re.I)
# Preference markers only, never assume that questions, comparisons, or
# negative mentions are the customer's selected phone.
PREFERENCE=re.compile(
 r"\b(?:mejor(?:\s+el(?:\s+de)?)?|prefiero(?:\s+el(?:\s+de)?)?|"
 r"quiero(?:\s+el(?:\s+de)?)?|lo quiero(?:\s+de)?|"
 r"me quedo con(?:\s+el(?:\s+de)?)?|elijo(?:\s+el(?:\s+de)?)?|"
 r"me sirve(?:\s+el(?:\s+de)?)?|ahora(?:\s+quiero)?(?:\s+el(?:\s+de)?)?)\b",re.I)
CLAUSE_STOP=re.compile(r"\b(?:pero|aunque|mientras|y\s+cuanto|y\s+cu[aá]nto)\b|[;,.!?¿¡\n]",re.I)
ALTERNATIVE=re.compile(r"\s+(?:o|versus|vs)\s+",re.I)
QUESTION=re.compile(r"\b(?:cu[aá]nto|c[oó]mo|cu[aá]l|diferencia|comparar|conviene)\b",re.I)
NEGATED=re.compile(r"\b(?:no quiero|no me gusta|no prefiero|descarto)\b",re.I)

def _choices(fragment:str)->tuple[set[int],set[str]]:
 return {int(x) for x in GB.findall(fragment)}, {COLOR_MAP[x.lower()] for x in COLORS.findall(fragment)}

def expected_selection(message:Any)->dict:
 """Return exact requirements only for unambiguous explicit preferences.

 Fields: storage_gb, color, ambiguous. Absent values never force a choice.
 """
 if not isinstance(message,str) or len(message)>1500:
  return {"storage_gb":None,"color":None,"ambiguous":True}
 text=message.lower()
 mentions=[m for m in PREFERENCE.finditer(text) if not text[max(0,m.start()-3):m.start()].endswith("no ")]
 selected=text
 if mentions:
  selected=text[mentions[-1].end():]
  selected=CLAUSE_STOP.split(selected,maxsplit=1)[0]
  if not selected.strip():
   selected=text
 capacities,colors=_choices(selected)
 all_capacities,all_colors=_choices(text)
 if len(capacities)==0 and len(all_capacities)==1:capacities=all_capacities
 if len(colors)==0 and len(all_colors)==1:colors=all_colors
 # When no explicit marker and a buyer is asking to compare alternatives,
 # ask for human review rather than declaring the last mention as chosen.
 ambiguous=(len(capacities)>1 or len(colors)>1
    or (not mentions and (len(all_capacities)>1 or len(all_colors)>1))
    or (bool(ALTERNATIVE.search(selected)) and
        (len(all_capacities)>1 or len(all_colors)>1))
    or (not mentions and bool(QUESTION.search(text)) and
        (len(all_capacities)>1 or len(all_colors)>1)))
 # Treat explicit rejection as a comparative statement, not selection.
 if NEGATED.search(text) and not mentions:
  ambiguous=True
 return {"storage_gb":next(iter(capacities)) if len(capacities)==1 and not ambiguous else None,
   "color":next(iter(colors)) if len(colors)==1 and not ambiguous else None,
   "ambiguous":bool(ambiguous)}
