#!/usr/bin/env python3
"""Reviewer-authored conversational repair candidate; NEVER write live bot."""
import os
from pathlib import Path
import hashlib
import json

LIVE=Path("/opt/softmobile-waha-test/sales-bot-v2.rb")
STAGE=Path("/opt/softmobile-waha-test/laboratorio-ia/quality/conversation-quality-candidates")
ANCHOR="      if ambiguous_model_choice?(raw) && [:stock,:price,:other,:comparison].include?(intent_type)\n"
LABEL="      # SM_CONVERSATION_QUALITY_20261018_BEGIN\n"
BLOCK=r'''      # SM_CONVERSATION_QUALITY_20261018_BEGIN
      # Explicit mixed questions take priority over single-intent rules.
      # Never invent unit condition, accessories, stock or warranty policies.
      if t.match?(/\bgarantia\b/) &&
         t.match?(/\b(?:accesorios?|regalias|cargador|funda|estuche|auriculares?|audifonos?)\b/) &&
         !t.match?(/\b(?:ya compre|lo compre|comprado|compre|fallo|fallan|fallas|defecto|se dano|danado|danados|no funciona|no sirven|reclamar|reclamo|garantia del cargador|garantia de accesorios)\b/) &&
         !t.match?(/\bgarantia\b.{0,35}\b(?:incluye|cubre)\b.{0,45}\b(?:accesorios?|cargador|funda|estuche)\b/)
        return {reply:"#{device ? 'Del '+device+', ' : ''}el plazo y la cobertura de garantía dependen de la unidad y deben confirmarse. También confirmaremos qué accesorios o regalías incluye exactamente y si la unidad es nueva o usada. Un asesor te dará esos tres datos antes de cobrarte.",
                note:'PREGUNTA COMBINADA: garantía, accesorios/regalías y condición nuevo/usado. Confirmar por unidad y punto; no inventar plazos, estado ni regalos.',
                needs_human:true,intent: :bundle_warranty_accessories,tag:'garantia_accesorios_estado_pendientes'}
      end
      # Fulfilment ETA is not battery/condition inquiry and is never a promise.
      if t.match?(/\b(?:tiempo estimado de entrega|plazo de entrega|en que plazo entregan|cuanto (?:tiempo )?tardan? en entregar|cuanto tarda(?:ria)? el envio|fecha estimada de llegada|para cuando esta estimada la entrega|en que fecha llegaria el equipo)\b/) &&
         !t.match?(/\b(?:mi pedido|pedido ya pagado|mi paquete|mi envio|numero de orden)\b/)
        return {reply:"Aún no tengo confirmado el plazo de entrega. Un asesor verificará la disponibilidad, el destino y el transporte antes de darte una fecha. ¿A qué ciudad sería?",
                note:'PLAZO DE ENTREGA: confirmar stock, origen, destino y transportista; no inventar días ni fecha.',
                needs_human:true,intent: :shipping_eta,tag:'entrega_fecha_por_confirmar'}
      end
      # "When will my order arrive?" after purchase is not a new sales ETA.
      if t.match?(/\b(?:cuando (?:llega|llegara|recibire) mi pedido|cuando (?:llega|llegara|recibire) mi paquete|en cuanto tiempo (?:llega|llegara|recibire) mi pedido)\b/)
        return {reply:"Para revisar cuándo podría llegar tu pedido, un asesor debe verificar su estado y los datos de envío con el transportista. ¿Tenés el número de pedido o guía? No enviés datos bancarios.",
                note:'ESTADO PEDIDO EXISTENTE: comprobar despacho, transporte y número de guía con asesor; no inventar una entrega.',
                needs_human:true,intent: :order_delivery_status,tag:'estado_pedido_por_confirmar'}
      end
      # Timing of a buyer's color/capacity change is not a shipping quote.
      if device && t.match?(/\b(?:que tiempo tardaria el cambio|cuanto tarda(?:ria)? el cambio|cuando estaria el cambio|cuanto demoraria el cambio|en que plazo me cambian el color|que tiempo tardaria en cambiar el modelo|cuanto tardaria en cambiar el color)\b/) &&
         (cap || col || t.match?(/\b(?:modelo|color|capacidad|gb)\b/)) &&
         !t.match?(/\b(?:pantalla|bateria|reparar|reparacion|servicio tecnico)\b/)
        return {reply:"No tengo un plazo confirmado para cambiar la variante del #{device}. Un asesor debe comprobar si se puede conseguir la opción que preferís y cuánto tardaría. No confirmaremos el cambio sin verificarla.",
                note:'PLAZO DE CAMBIO DE VARIANTE: confirmar nueva configuración, stock, pedido y viabilidad; no prometer fechas.',
                needs_human:true,intent: :variant_change_eta,tag:'plazo_cambio_por_confirmar'}
      end
      # SM_CONVERSATION_QUALITY_20261018_END
'''
def candidate():
 src=LIVE.read_text()
 if src.count(ANCHOR)!=1 or LABEL in src:
  raise ValueError("Unexpected live source / cannot safely stage")
 if src.count("PILOT_CONVERSATION_ID = 3")!=1 or src.count("AUTO_REPLY_LIMIT = 1")!=1:
  raise ValueError("Pilot scope not verified")
 return src,src.replace(ANCHOR,BLOCK+ANCHOR,1)

def write():
 src,out=candidate()
 STAGE.mkdir(mode=0o700,parents=True,exist_ok=True)
 dest=STAGE/"sales-bot-composite-sales-stage.rb"
 dest.write_text(out)
 os.chmod(dest,0o600)
 report={"status":"review_only","live_source_sha256":hashlib.sha256(src.encode()).hexdigest(),
     "candidate_sha256":hashlib.sha256(out.encode()).hexdigest(),
     "code_inserted_lines":len(BLOCK.splitlines()),"live_bot_unchanged":True}
 return dest,report

if __name__=="__main__":
 dest,result=write()
 print("CANDIDATE",dest.name,json.dumps(result))
