#!/usr/bin/env python3
"""Conservative post-validation for PRIVATE Groq sales suggestions only.

No public message delivery, no inventory access and no policy changes.
"""
import re
import unicodedata
from variant_preference import expected_selection
from sales_context import preference_snapshot

HARD_CLAIMS=re.compile(
 r"\b(?:te lo (?:reserve|reserv[eé]|reservo)|ya (?:qued[oó] reservado|"
 r"est[aá] reservado|aprobamos? tu cr[eé]dito|aprobado el financiamiento)|"
 r"tenemos (?:en stock|disponible|disponibles|existencias)|"
 r"s[ií] (?:hay|tenemos) (?:stock|existencia)|"
 r"garantizamos|te aseguramos|cobertura incluida|"
 r"(?:incluye|trae|viene con) (?:el |una? )?(?:cargador|funda|estuche|seguro|garant[ií]a extendida)|"
 r"(?:est[aá]|tenemos|contamos con|hay) (?:ya |actualmente )?(?:disponible|en existencia|en inventario|en stock)|"
 r"(?:te lo aparto|te confirmo la reserva|entrega inmediata garantizada|te aprueban el cr[eé]dito)|"
 r"te (?:llega|lo entregamos|lo enviamos) (?:hoy|ma[ñn]ana)|"
 r"el (?:env[ií]o|transporte) es gratis|sin intereses aprobados)\b",re.I)
FIGURES=re.compile(
 r"(?:\b(?:L\.?\s*|HNL\s*|USD\s*|\$\s*)\d[\d,.]*|\b\d+\s*(?:lempiras|d[oó]lares|"
 r"horas?|d[ií]as?|meses?|semanas?|%)\b)",re.I)
CREDENTIALS=re.compile(
 r"\b(?:comp[aá]rteme|env[ií]ame|dame|escr[ií]beme)\b.{0,45}"
 r"\b(?:n[uú]mero de tarjeta|cuenta bancaria|pin|otp|c[oó]digo de verificaci[oó]n|cvv|contrase[ñn]a)\b",re.I)
FALLBACK=("Un asesor debe confirmar las condiciones de esa unidad, "
          "como disponibilidad, precio, accesorios, garantía o entrega, "
          "antes de concretar la compra. No tengo esos datos confirmados.")
ASK_MODEL=re.compile(r"\b(?:que|cual)\s+(?:modelo|telefono|celular)\b|"
                     r"\b(?:modelo|telefono|celular)\s+(?:buscas|quieres|prefieres)\b")
ASK_STORAGE=re.compile(r"\b(?:de )?cuantos\s+(?:gb|gigas)\b|"
   r"\b(?:que capacidad|que almacenamiento|cuanta memoria)\b")
ASK_COLOR=re.compile(r"\b(?:que|cual)\s+color\b|"
   r"\bcolor\s+(?:buscas|quieres|prefieres)\b")

def _fold(text):
 return "".join(c for c in unicodedata.normalize("NFKD",text.lower())
                if not unicodedata.combining(c))

def _repeats_known_question(reply,clean):
 if not isinstance(clean,dict):return False
 context=clean.get("context") or {}
 if not isinstance(context,dict):return False
 last=clean.get("message","")
 if not isinstance(last,str):last=""
 known=preference_snapshot([last]) if last else {}
 pref=expected_selection(last)
 capacity=pref["storage_gb"] or known.get("storage_gb") or context.get("storage_gb")
 color=pref["color"] or known.get("color_options") or context.get("color_options")
 model=known.get("model") or context.get("model")
 folded=_fold(reply)
 return bool((model and ASK_MODEL.search(folded)) or
             (capacity and ASK_STORAGE.search(folded)) or
             (color and ASK_COLOR.search(folded)))

def guarded_draft(output,clean=None):
 if not isinstance(output,dict) or not isinstance(output.get("suggested_reply"),str):
  raise ValueError("Invalid Groq proposal")
 reply=output["suggested_reply"]
 if (HARD_CLAIMS.search(reply) or FIGURES.search(reply) or
     CREDENTIALS.search(reply) or _repeats_known_question(reply,clean)):
  repaired=dict(output)
  repaired.update({"suggested_reply":FALLBACK,"human_review":True})
  return repaired,True
 return output,False
