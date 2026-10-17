inventory=[]
base=SoftMobileSales.context_from(["Busco el iPhone 14 Pro Max de 128","En negro","De SPS","Envío","Métodos de pago??"])
cash=SoftMobileSales.plan("Efectivo",base,inventory,"Podés pagar en efectivo, transferencia o tarjeta")
raise "did_not_confirm_cash" unless cash[:reply].to_s.include?("anoté pago en efectivo")
raise "payment_methods_repeated" if cash[:reply].to_s.include?("transferencia o tarjeta")
raise "cash_not_human" unless cash[:needs_human]
raise "unexpected_price" if cash[:reply].to_s.match?(/L\s*\d{4,}/)

shipping=SoftMobileSales.context_from(["Busco el iPhone 14 Pro Max de 128","En negro","De SPS","Envío","Galerías"])
ambiguous=SoftMobileSales.plan("Galerías",shipping,inventory,"¿En qué colonia o zona sería?")
raise "not_clarifying_shipping_vs_pickup" unless ambiguous[:reply].to_s.include?("retirarlo en Mall Galerías") && ambiguous[:reply].to_s.include?("envío")
raise "wrong_category" unless ambiguous[:intent]==:clarify_delivery
raise "human_not_required" unless ambiguous[:needs_human]

general=SoftMobileSales.plan("Métodos de pago??",base,inventory)
raise "generic_payments_broken" unless general[:reply].to_s.include?("efectivo") && general[:reply].to_s.include?("transferencia")

clarified=SoftMobileSales.plan("Galerías",SoftMobileSales.context_from(["De SPS","Retiro","Galerías"]),inventory)
raise "false_stock_promise" if clarified[:reply].to_s.match?(/100% disponible|tenemos disponible/i)
puts "SOFTMOBILE_QA_REGRESSION=5/5 PASS"
