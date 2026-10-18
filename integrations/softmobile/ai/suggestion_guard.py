#!/usr/bin/env python3
"""Conservative validation for private Groq sales drafts, never public send."""
import re

HARD_CLAIMS=re.compile(
 r"\b(?:te lo (?:reserve|reserv[eé]|reservo)|ya (?:qued[oó] reservado|"
 r"est[aá] reservado|aprobamos? tu cr[eé]dito|aprobado el financiamiento)|"
 r"tenemos (?:en stock|disponible|disponibles|existencias)|"
 r"s[ií] (?:hay|tenemos) (?:stock|existencia)|"
 r"garantizamos|te aseguramos|cobertura incluida|"
 r"incluye (?:cargador|funda|seguro|garant[ií]a extendida)|"
 r"te (?:llega|lo entregamos|lo enviamos) (?:hoy|ma[ñn]ana)|"
 r"el (?:env[ií]o|transporte) es gratis|sin intereses aprobados)\b",re.I)
FIGURES=re.compile(
 r"(?:\b(?:L\.?\s*|HNL\s*|USD\s*|\$\s*)\d[\d,.]*|\b\d+\s*(?:lempiras|d[oó]lares|"
 r"horas?|d[ií]as?|meses?|semanas?|%)\b)",re.I)
CREDENTIALS=re.compile(
 r"\b(?:comp[aá]rteme|env[ií]ame|dame|escr[ií]beme)\b.{0,45}"
 r"\b(?:n[uú]mero de tarjeta|cuenta bancaria|pin|otp|c[oó]digo de verificaci[oó]n|cvv|contrase[ñn]a)\b",re.I)
FALLBACK=("Un asesor puede confirmar disponibilidad, precio, accesorios, "
          "garantía y condiciones antes de que tomés una decisión. "
          "¿Qué modelo te interesa revisar?")

def guarded_draft(output):
 if not isinstance(output,dict) or not isinstance(output.get("suggested_reply"),str):
  raise ValueError("Invalid Groq proposal")
 reply=output["suggested_reply"]
 if (HARD_CLAIMS.search(reply) or FIGURES.search(reply)
      or CREDENTIALS.search(reply)):
  clean=dict(output)
  clean.update({"suggested_reply":FALLBACK,"human_review":True})
  return clean,True
 return output,False
