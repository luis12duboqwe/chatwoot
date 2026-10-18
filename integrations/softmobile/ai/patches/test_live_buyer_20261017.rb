# frozen_string_literal: true
# Regression from live pilot 2026-10-17 (new inbound 216..240), no DB writes.
products=[]
history=[]
previous=nil
reply_log=[]
def assert(condition,message)
  raise "SM_LIVE_REGRESSION_FAIL: #{message}" unless condition
end
script=[
 ["Hola","greeting"],
 ["Busco un iPhone 16 pro","model"],
 ["De 256","capacity"],
 ["Color titanium","titanium"],
 ["Color dorado","gold"],
 ["Comayagua","city"],
 ["Envío","shipping"],
 ["Gasolinera de ejemplo","landmark"],
 ["Si","ambiguous_yes"]
]
script.each do |message,label|
  history << message
  p=SoftMobileSales.plan(message,SoftMobileSales.context_from(history),products,previous)
  reply=p[:reply].to_s
  case label
  when "greeting"
    assert(reply.match?(/celular|busc/i),"greeting must offer help")
  when "model"
    assert(reply.include?("iPhone 16 Pro") && reply.match?(/capacidad|gb/i),"model must request variant")
  when "capacity"
    assert(reply.include?("256GB") && reply.match?(/color/i),"storage must ask color")
  when "titanium"
    assert(reply.downcase.include?("titanio") && reply.match?(/tono/i),"titanium request not recognized")
    assert(!reply.match?(/\btenemos\s+disponible\b/i),"must not claim titanium stock")
  when "gold"
    assert(reply.downcase.include?("dorado") && reply.match?(/ciudad/i),"gold override and city request")
  when "city"
    assert(reply.include?("Comayagua") && reply.match?(/env[ií]o|retirar/i),"city retained")
  when "shipping"
    assert(reply.include?("Comayagua") && reply.match?(/colonia|zona/i),"shipping must ask area")
  when "landmark"
    assert(reply.match?(/referencia/i) && reply.include?("Comayagua"),"landmark not acknowledged")
    assert(!reply.match?(/gasolinera uno/i),"landmark exposed in public reply")
    assert(p[:needs_human],"delivery details must be reviewed by human")
    assert(reply.match?(/(?:efectivo|transferencia|tarjeta)/i),"flow not advanced to payment choice")
  when "ambiguous_yes"
    assert(reply.match?(/(?:efectivo|transferencia|tarjeta)/i),"ambiguous yes must clarify payment")
    assert(!reply.match?(/Tengo anotado el iPhone/i),"order summary repeated on yes")
  end
  previous=reply
  reply_log << [label,p[:intent],p[:tag]]
  puts "SM_LIVE_CASE=#{label} PASS"
end
ctx=SoftMobileSales.context_from(history)
assert(ctx[:model].to_s.include?("iphone") && ctx[:capacity]=="256GB","model+storage lost")
assert(ctx[:color]=="Dorado" && ctx[:city]=="Comayagua" && ctx[:delivery_mode]=="Envío","context lost")
p=SoftMobileSales.plan("Sí",ctx,products,"Tengo anotado el iPhone 16 Pro de 256GB, en dorado, con envío. Precio y existencia todavía deben verificarse con un asesor.")
assert(p[:reply].nil?,"simple positive after completed handoff should be silent")
p=SoftMobileSales.plan("Gasolinera de ejemplo",ctx,products,"¿Qué color preferís?")
assert(p[:tag]!="referencia_pendiente","must not infer location without address question")
puts "SM_LIVE_JOURNEY_TOTAL=11 PASS=11 FAIL=0"
