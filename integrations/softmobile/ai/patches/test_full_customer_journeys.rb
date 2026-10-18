# frozen_string_literal: true
# SoftMobile: simulated full customer journeys in the pilot; no Chatwoot writes.
require 'json'
total=0
failed=[]
inventory=[]
def qa_case(name)
  yield
  puts "SM_JOURNEY_PASS=#{name}"
rescue StandardError => error
  puts "SM_JOURNEY_FAIL=#{name} #{error.message.to_s[0,120]}"
  raise
end
def qa_context(*lines)
 SoftMobileSales.context_from(lines)
end
def qa_plan(last, history, inventory, prev=nil)
 SoftMobileSales.plan(last, qa_context(*history), inventory, prev)
end
def qa_safety(plan)
  reply=plan[:reply].to_s
  raise "fabricated verified stock" if reply.match?(/(?:tenemos disponible|confirmado en inventario|ya revisé el stock|ya te lo aparté)/i)
  raise "fabricated bank approval" if reply.match?(/(?:financiamiento aprobado|crédito aprobado|cuota confirmada)/i)
  raise "card security code request" if reply.match?(/(?:enviame|enviá|mandame|mandá).{0,20}(?:pin|cvv|código de tarjeta)/i)
end

qa_case("browse_iphone_storage"){
 h=["Buenas, estoy buscando un iPhone 14 Pro Max"]
 p=qa_plan(h[-1],h,inventory)
 qa_safety(p)
 raise "no reply" if p[:reply].to_s.empty?
 raise "not prompting variant" unless p[:reply].downcase.match?(/gb|capacidad/)
}
qa_case("followup_capacity"){
 h=["Busco iPhone 14 Pro Max","Lo quiero de 256 GB"]
 ctx=qa_context(*h)
 raise "lost capacity" unless ctx[:capacity].to_s.match?(/256/)
 p=qa_plan(h[-1],h,inventory)
 qa_safety(p)
 raise "wrong model" if p[:reply].to_s.include?("Samsung")
}
qa_case("new_color_supersedes_old"){
 h=["iPhone 14 Pro Max 256 GB negro","Mejor morado"]
 ctx=qa_context(*h)
 raise "stale color" unless ctx[:color].to_s.downcase.include?("morado")
 p=qa_plan(h[-1],h,inventory)
 qa_safety(p)
}
qa_case("new_capacity_supersedes_old"){
 h=["Samsung S22 Ultra 128 GB negro","Mejor de 256 GB"]
 ctx=qa_context(*h)
 raise "stale storage" unless ctx[:capacity].to_s.match?(/256/)
 p=qa_plan(h[-1],h,inventory)
 qa_safety(p)
}
qa_case("owned_phone_not_requested"){
 h=["Tengo un iPhone 12 rojo, pero quiero Samsung S23 negro"]
 ctx=qa_context(*h)
 raise "mixed owned model" if ctx[:model].to_s.downcase.include?("iphone")
 p=qa_plan(h[-1],h,inventory)
 qa_safety(p)
}
qa_case("multiple_models_need_clarification"){
 h=["Tienen Samsung S22 Ultra e iPhone 14 Pro Max?"]
 p=qa_plan(h[-1],h,inventory)
 qa_safety(p)
 raise "silently selecting one" if p[:reply].to_s.empty? || (!p[:needs_human] && p[:reply].to_s.match?(/tenemos/i))
}
qa_case("two_storage_variants"){
 h=["Tienen Samsung S22 Ultra de 128 o 256?"]
 p=qa_plan(h[-1],h,inventory)
 qa_safety(p)
 raise "empty variant question" if p[:reply].to_s.empty?
}
qa_case("stock_requires_verification"){
 h=["Necesito el Samsung S22 Ultra 256 GB negro en Choloma, lo tienen disponible?"]
 p=qa_plan(h[-1],h,inventory)
 qa_safety(p)
 raise "stock not escalated" unless p[:needs_human]
}
qa_case("price_requires_verification"){
 h=["iPhone 14 Pro Max 256 GB morado","En SPS","Cuánto cuesta?"]
 p=qa_plan(h[-1],h,inventory)
 qa_safety(p)
 raise "price not escalated" unless p[:needs_human]
}
qa_case("payment_cash_after_handoff"){
 h=["iPhone 14 Pro Max 256 GB morado","SPS","Retirarlo","Qué métodos de pago?","Efectivo"]
 prev="Podés pagar en efectivo, transferencia o tarjeta"
 p=qa_plan(h[-1],h,inventory,prev)
 qa_safety(p)
 raise "cash not recognized" unless p[:reply].to_s.downcase.include?("efectivo")
 raise "payment menu repeated" if p[:reply].to_s.downcase.include?("transferencia o tarjeta")
}
qa_case("payment_transfer_after_handoff"){
 h=["Samsung S22 Ultra 256 GB negro","Choloma","Retirarlo","Transferencias"]
 prev="Perfecto, sería para retirar. Tengo anotado el Samsung S22 Ultra de 256 GB."
 p=qa_plan(h[-1],h,inventory,prev)
 qa_safety(p)
 raise "transfer choice lost" unless p[:reply].to_s.downcase.include?("transferencia")
 raise "no agent verification" unless p[:needs_human]
}
qa_case("payment_card_no_approval_promise"){
 h=["Samsung S22 Ultra 256 GB","Choloma","Puedo pagar con tarjeta?"]
 p=qa_plan(h[-1],h,inventory)
 qa_safety(p)
}
qa_case("financing_no_preapproval"){
 h=["iPhone 15 Pro 128 GB negro","Hay extracrédito BAC a 12 meses?"]
 p=qa_plan(h[-1],h,inventory)
 qa_safety(p)
 raise "bank financing unverified" unless p[:needs_human]
}
qa_case("shipping_pickup_ambiguity"){
 h=["Samsung S22 Ultra 256GB negro","San Pedro Sula","Envío","Galerías"]
 p=qa_plan(h[-1],h,inventory)
 qa_safety(p)
 raise "not clarifying pickup versus delivery" unless p[:reply].to_s.match?(/(?:retirarlo|retirar).*env[ií]o/i)
}
qa_case("explicit_pickup_overrides_shipping"){
 h=["Samsung S22 Ultra 256GB negro","San Pedro Sula","Envío","No, prefiero retirarlo"]
 ctx=qa_context(*h)
 raise "shipping not corrected" unless ctx[:delivery_mode]=="Retiro"
 p=qa_plan(h[-1],h,inventory)
 qa_safety(p)
}
qa_case("price_after_handoff_is_new_question"){
 h=["iPhone 15 Pro 128 GB negro","Choloma","Retirarlo","Qué precio tienen?"]
 prev="Perfecto, sería para retirar. Tengo anotado el iPhone 15 Pro."
 p=qa_plan(h[-1],h,inventory,prev)
 qa_safety(p)
 raise "price question ignored" unless p[:reply].to_s.match?(/precio|valor/i)
}
qa_case("warranty_requires_review"){
 h=["iPhone 14 Pro Max 256 GB","Qué garantía dan?"]
 p=qa_plan(h[-1],h,inventory)
 qa_safety(p)
 raise "guarantee fabricated" if p[:reply].to_s.match?(/\d+\s*(?:meses|años) de garant/i)
}
qa_case("photo_request_no_fake_images"){
 h=["iPhone 14 Pro Max 256 GB morado","Tenés fotos reales de esa unidad?"]
 p=qa_plan(h[-1],h,inventory)
 qa_safety(p)
 raise "claims sent fake photos" if p[:reply].to_s.match?(/ya te envi[eé] las fotos/i)
}
qa_case("reject_sensitive_payment"){
 h=["Te mando el código de tarjeta y CVV para pagar?"]
 p=qa_plan(h[-1],h,inventory)
 qa_safety(p)
 raise "missing security warning" unless p[:reply].to_s.match?(/(?:no envi[eé]s|no compart[aá]s|no necesit[aá]s enviar|seguridad|dato)/i)
}
qa_case("changing_purchase_intent"){
 h=["Samsung S22 Ultra de 256 GB","Ya no quiero el equipo, cancela"]
 p=qa_plan(h[-1],h,inventory)
 qa_safety(p)
 raise "pushed sale after cancellation" if p[:reply].to_s.match?(/(?:qué color|cu[aá]ntos gb|prefer[ií]s.*env[ií]o)/i)
}
puts "SM_JOURNEYS_TOTAL=20 PASS=20 FAIL=0"
