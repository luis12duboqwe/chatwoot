# frozen_string_literal: true
# Synthetically discovered (but independently validated) five buyer behavior
# classes. No DB writes, no WhatsApp calls, no real buyer PII.
stock=[]
def sc_plan(msg,hist=[],prev=nil)
  SoftMobileSales.plan(msg,SoftMobileSales.context_from(hist+[msg]),[],prev)
end
def sc_expect(tag,condition)
 raise "SCENARIO_FAIL: #{tag}" unless condition
 puts "SCENARIO_PASS=#{tag}"
end
a=sc_plan('¿Es posible agregar una funda con diseño personalizado al paquete?',
 ['Tengo dudas sobre la garantía del Samsung Galaxy S24',
  '¿El precio incluye una batería extra?'])
sc_expect('custom_funda_not_ignored',a[:reply].to_s.include?('funda personalizada') && a[:reply].to_s.match?(/verificar[aá]|verificar/i) && a[:needs_human])
sc_expect('custom_funda_does_not_promise_offer',!a[:reply].to_s.match?(/claro, podemos añadir|está incluido|regalada/i))
b=sc_plan('Quisiera cambiar el color del iPhone 15 a negro, por favor.')
sc_expect('color_preference_not_repair',b[:intent]!=:repair && b[:reply].to_s.match?(/negro/i) && b[:needs_human])
sc_expect('color_not_confirmed',!b[:reply].to_s.match?(/en existencia|disponible para llevar/i))
c=sc_plan('¿Cuál es el tiempo de entrega estimado para la compra de un Samsung Galaxy S24?')
sc_expect('eta_question_answered',c[:reply].to_s.match?(/plazo de entrega|plazo.*verificado/i) && c[:needs_human])
sc_expect('eta_not_fabricated',!c[:reply].to_s.match?(/\b[1-9]\s*(?:a\s*[1-9])?\s*d[ií]as/i))
d=sc_plan('¿Qué pasa si el producto llega dañado?',
 ['El precio del modelo nuevo parece alto', 'Me preocupa la batería',
  '¿Por qué no me pueden hacer un descuento?'])
sc_expect('damage_escalated',d[:reply].to_s.match?(/dañado/i) && d[:needs_human])
sc_expect('damage_no_refund_guarantee',!d[:reply].to_s.match?(/(?:te ofrecemos|te haremos|garantizamos).*(?:reembolso|reemplazo|devoluci[oó]n)/i))
base=['Busco iPhone 16 Pro de 128 GB en negro']
first=sc_plan(base[0])
e=sc_plan('Mejor de 256 GB',base,first[:reply])
sc_expect('city_acknowledges_storage',e[:reply].to_s.match?(/actualic[eé].*256/i) && !e[:reply].to_s.include?('¿En qué ciudad lo necesitás?'))
f=sc_plan('Y en color dorado',base+['Mejor de 256 GB'],e[:reply])
sc_expect('city_acknowledges_color',f[:reply].to_s.match?(/dorado/i) && !f[:reply].to_s.include?('¿En qué ciudad lo necesitás?'))
g=sc_plan('¿Puedo cambiarlo antes de que se envíe?',
 ['Quisiera cambiar el color del iPhone 15 a negro',
  '¿Hay una diferencia de precio entre negro y plata?'])
sc_expect('prior_shipment_change_escalated',g[:reply].to_s.match?(/estado del pedido|asesor|pago/i) && g[:needs_human])
h=sc_plan('Quiero cambiar la batería del iPhone 15, no funciona')
sc_expect('actual_repair_still_available',h[:intent]==:repair || h[:intent]==:complaint)
j=sc_plan('¿Cuántos días tarda mi pedido?')
sc_expect('existing_order_not_assumed_eta',j[:intent]!=:shipping_eta)
k=sc_plan('¿Trae un estuche normal?', ['Busco iPhone 14 Pro Max'])
sc_expect('regular_accessories_not_custom',k[:intent]!=:custom_accessory)
l=sc_plan('¿Aceptan tarjeta?', ['Busco Samsung S22 Ultra'])
sc_expect('payment_not_overridden',l[:intent]!=:custom_accessory)
puts 'SM_FUTURE_SCENARIOS_TOTAL=15 PASS=15 FAIL=0'
