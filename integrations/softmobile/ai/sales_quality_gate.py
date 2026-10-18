#!/usr/bin/env python3
"""Conservative business relevance for fictional SoftMobile drafts.

Pass/fail is an offline screening heuristic, NOT a claim of genuine sales
competence or customer satisfaction. Requires one concrete customer-topic
anchor and an actionable, non-committal next step, rejecting kitchen-sink
replies that simply list all sales terms to game keyword checks.
"""
import re
import unicodedata

TOPIC_ANCHORS={
 "product":(r"\b(?:iphone|samsung|modelo|equipo|telefono|celular|unidad|retirar|retiro|envio|entrega)\b",),
 "budget":(r"\b(?:presupuesto|precio|opcion(?:es)?|alternativa(?:s)?|barat[oa]|economi[ac])\b",),
 "discount":(r"\b(?:descuento|precio|promocion|oferta|presupuesto)\b",),
 "payment":(r"\b(?:cuotas?|financiamiento|banc[oa]|tarjeta|forma de pago|pagar|credito)\b",),
 "warranty":(r"\b(?:garantia|cobertura|defecto|unidad|cargador)\b",),
 "condition":(r"\b(?:estado|nuevo|usado|revisar|probar|unidad)\b",),
 "shipping":(r"\b(?:entrega|envio|retiro|retirar|transport|recoger|llegad)\w*\b",),
 "inspection":(r"\b(?:probar|revisar|estado|condicion|unidad)\b",),
 "trade_in":(r"\b(?:parte de pago|canje|valoracion|recibir (?:tu|el) celular|tomar (?:tu|el) celular)\b",),
 "closing":(r"\b(?:compr[ao]|disponibilidad|confirmar|asesor|retirar|entrega|unidad)\b",),
 "comparison":(r"\b(?:comparar|diferencia|opciones|alternativas|precio|variantes)\b",),
}
ACTION=re.compile(r"\b(?:asesor|confirmar|verificar|revisar|consultar|comparar|"
 r"aclarar|dime|decime|prefer[ií]s|qu[eé] te parece|opci[oó]n|"
 r"buscar|podemos|pod[eé]s|si quer[eé]s)\b",re.I)
REJECT_GENERIC=re.compile(r"^(?:un|el) asesor (?:revisara|verificara|confirmara) (?:las condiciones del equipo|la consulta|las condiciones)\.?$",re.I)
REJECT_BULK=re.compile(r"\b(?:asesor.{0,15}comparar opciones y modelos|"
 r"precio y presupuesto, descuento y promoci[oó]n|"
 r"cuota, financiaci[oó]n, banco, garant[ií]a)",re.I)
# Generic 'all areas' spam often includes > 6 unrelated topics.
DOMAINS={
 "money":r"\b(?:precio|cuota|descuento|presupuesto|banco|financiamiento|promocion|pagar)\b",
 "warranty":r"\b(?:garantia|cobertura|defecto)\b",
 "delivery":r"\b(?:envio|entrega|retiro|recoger|transporte)\b",
 "tradein":r"\b(?:canje|parte de pago|valoracion)\b",
 "condition":r"\b(?:nuevo|usado|estado|revisar|probar)\b",
 "stock":r"\b(?:existencia|disponibilidad|reservar|apartar)\b",
 "accessory":r"\b(?:funda|cargador|accesorios|regalias)\b"
}

def fold(s):
 return "".join(c for c in unicodedata.normalize("NFKD",s.lower())
                if not unicodedata.combining(c))
def assess(reply,topic):
 if not isinstance(reply,str) or topic not in TOPIC_ANCHORS:
  return {"relevant":False,"actionable":False,"specific":False,
          "meaningful":False,"bulk_topics":0}
 v=fold(reply)
 relevant=any(re.search(pattern,v) for pattern in TOPIC_ANCHORS[topic])
 actionable=bool(ACTION.search(v))
 bulk=sum(bool(re.search(pattern,v)) for pattern in DOMAINS.values())
 specific=not (REJECT_GENERIC.fullmatch(v.strip()) or REJECT_BULK.search(v) or bulk>=6 or len(reply)>300)
 # Do not accept a generic one-liner like "Un asesor lo revisará".
 meaningful=bool(len(v.strip())>=30)
 return {"relevant":bool(relevant),"actionable":actionable,
  "specific":bool(specific),"meaningful":meaningful,
  "bulk_topics":bulk}
