# frozen_string_literal: true
# Learned safely from a synthetic customer scenario. No prices or stock claims.
products=[]
ctx=SoftMobileSales.context_from([
 'Busco un iPhone 14 Pro Max de 256 GB negro',
 'En San Pedro Sula',
 'Para retirar',
 '¿Cómo puedo pagar?'
])
prev='Podés pagar en efectivo, transferencia o tarjeta, según las condiciones del punto de entrega.'
result=SoftMobileSales.plan('Transferencia',ctx,products,prev)
raise 'method choice ignored' unless result[:reply].to_s.match?(/prefer[ií]s pagar por transferencia/i)
raise 'repeated full payment menu' if result[:reply].to_s.match?(/efectivo.*transferencia.*tarjeta/i)
raise 'missing verification step' unless result[:needs_human]
unsafe=SoftMobileSales.plan('¿Ya pagué por transferencia?',ctx,products,prev)
raise 'unverified bank payment bypass' if unsafe[:tag]=='sm_autofix'
puts 'SM_AUTOFIX_PAYMENT_MENU_TOTAL=2 PASS=2 FAIL=0'
