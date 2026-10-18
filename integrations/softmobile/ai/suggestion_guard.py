#!/usr/bin/env python3
"""Conservative post-validation for PRIVATE Groq sales suggestions only.

No public message delivery, no inventory access and no policy changes.
"""
import re
import unicodedata
from variant_preference import expected_selection
from sales_context import preference_snapshot
from sales_quality_gate import assess

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

TOPIC_PATTERNS=(
 ("trade_in",re.compile(r"\b(?:parte de pago|reciben mi (?:celular|telefono|equipo)|entregar mi (?:celular|telefono)|canje|trade.?in)\b",re.I),
  "No tengo confirmada una opción para recibir tu teléfono como parte de pago. Un asesor debe revisar si existe esa posibilidad, sus condiciones y la valoración antes de ofrecerte algo."),
 ("payment",re.compile(r"\b(?:cuotas|financiamiento|financiar|credito|crédito|tarjetas?|sin prima|mensualidades|extrafinanciamiento|donde pago|dónde pago|forma de pago)\b",re.I),
  "Un asesor debe confirmar las formas de pago, bancos participantes, requisitos y cuotas aplicables. No puedo aprobar financiamiento ni solicitar datos de tarjetas aquí."),
 ("shipping",re.compile(r"\b(?:envio|envío|entrega|retirar|retiro|recoger|despacho|transporte|tardaria en llegar|tardaría en llegar|llegara|llegará)\b",re.I),
  "La entrega o el retiro deben confirmarse según la unidad, el punto disponible y el destino. Un asesor puede verificarlo antes de darte un plazo o fecha."),
 ("inspection",re.compile(r"\b(?:probarlo|probar|revisarlo|revisar|nuevo o usado|es usado|es nuevo|estado del equipo)\b",re.I),
  "Un asesor debe confirmar el estado real de esa unidad y si es posible revisarla o probarla antes de pagar, así como las condiciones del punto."),
 ("warranty",re.compile(r"\b(?:garantía|garantia|cargador|funda|estuche|regalías|regalias|accesorios|batería|bateria|cobertura)\b",re.I),
  "Antes de concretar la compra, un asesor debe confirmar por unidad la garantía, el estado y los accesorios incluidos. No puedo asegurar esas condiciones sin verificarlas."),
 ("price",re.compile(r"\b(?:descuento|más barato|mas barato|presupuesto|promoción|promocion|precio|cuanto cuesta|cuánto cuesta|efectivo)\b",re.I),
  "Entiendo que buscás una opción que se ajuste a tu presupuesto. Un asesor debe verificar el precio actual de la unidad y si existe alguna alternativa o promoción."),
 ("purchase",re.compile(r"\b(?:quiero comprarlo|listo para comprar|lo compro|lo llevo|quiero llevarlo|apartarlo|apartame|apártamelo|reservarlo|reserva)\b",re.I),
  "Para avanzar con la compra, un asesor debe confirmar la unidad elegida, disponibilidad, precio y forma de entrega antes de generar cualquier compromiso.")
)
TRADE_IN_REPLY_KEYS=("parte de pago","canje","valoracion","valoración","recibir tu celular","recibir el celular","tomar tu celular")
RUBRIC_BY_TOPIC={"trade_in":"trade_in","payment":"payment","shipping":"shipping",
 "inspection":"inspection","warranty":"warranty","price":"budget","purchase":"closing"}

def _buyer_topic(clean):
 if not isinstance(clean,dict) or not isinstance(clean.get("message"),str):
  return None
 message=clean["message"]
 for name,pattern,_ in TOPIC_PATTERNS:
  if pattern.search(message):
   if name=="price" and re.search(r"\b(?:descuento|promocion|promoción|oferta)\b",message,re.I):
    return "discount"
   return RUBRIC_BY_TOPIC[name]
 known=preference_snapshot([message])
 context=clean.get("context")
 if known.get("model") or (isinstance(context,dict) and context.get("model")):
  return "product"
 return None

def _topic_fallback(clean):
 if not isinstance(clean,dict):return FALLBACK
 message=clean.get("message","")
 if not isinstance(message,str):return FALLBACK
 for _,regex,reply in TOPIC_PATTERNS:
  if regex.search(message):return reply
 from sales_context import preference_snapshot
 context=clean.get("context") or {}
 if (isinstance(context,dict) and context.get("model")) or preference_snapshot([message]).get("model"):
  return ("Podemos revisar el modelo que te interesa. Un asesor debe confirmar "
          "la disponibilidad, el precio y la configuración exacta antes de "
          "avanzar con la compra.")
 return FALLBACK

def guarded_draft(output,clean=None):
 if not isinstance(output,dict) or not isinstance(output.get("suggested_reply"),str):
  raise ValueError("Invalid Groq proposal")
 reply=output["suggested_reply"]
 topic=_buyer_topic(clean)
 quality=assess(reply,topic) if topic else None
 if (quality is not None and not all(quality[k] for k in ("relevant","actionable","specific","meaningful"))) or (HARD_CLAIMS.search(reply) or FIGURES.search(reply) or
     CREDENTIALS.search(reply) or _repeats_known_question(reply,clean) or
     (isinstance(clean,dict) and isinstance(clean.get("message"),str) and
      TOPIC_PATTERNS[0][1].search(clean["message"]) and
      not any(key in _fold(reply) for key in TRADE_IN_REPLY_KEYS))):
  repaired=dict(output)
  repaired.update({"suggested_reply":_topic_fallback(clean),"human_review":True})
  return repaired,True
 return output,False
