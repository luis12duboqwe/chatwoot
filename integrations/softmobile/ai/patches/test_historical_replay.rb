cases=[
 ["city_two_words","De Villanueva",["Samsung S22 Ultra 256 GB negro","De Villanueva"],"Te ayudo a revisar el Samsung S22 Ultra de 256GB en negro. ¿En qué ciudad lo necesitás?"],
 ["city_one_word","Villanueva",["Samsung S22 Ultra 256 GB negro","Villanueva"],"Te ayudo a revisar el Samsung S22 Ultra de 256GB en negro. ¿En qué ciudad lo necesitás?"],
 ["pickup_explicit","Pasaré por él",["Samsung S22 Ultra 256 GB negro","Choloma","Pasaré por él"],"Te ayudo a confirmar si podemos conseguir el Samsung S22 Ultra de 256GB en negro para Choloma. ¿Preferís retirarlo o recibir envío?"],
 ["pickup_choice","Retirarlo",["Samsung S22 Ultra 256 GB negro","Choloma","Retirarlo"],"Te ayudo a confirmar si podemos conseguir el Samsung S22 Ultra de 256GB en negro para Choloma. ¿Preferís retirarlo o recibir envío?"],
 ["pickup_short","Paso",["iPhone 15 Pro 128 GB negro","Choloma","Paso"],"Te ayudo a confirmar si podemos conseguir el iPhone 15 Pro de 128GB en negro para Choloma. ¿Preferís retirarlo o recibir envío?"],
 ["confusion","No entiendo?",["iPhone 15 Pro 128 GB negro","Choloma","Retirarlo","No entiendo?"],"Perfecto, sería para retirar. Tengo anotado el iPhone 15 Pro de 128GB, en negro, para Choloma. Primero hay que confirmar disponibilidad, precio y punto de retiro; te atiende un asesor con esos datos."],
 ["price_after_handoff","Qué precio tienen?",["iPhone 15 Pro 128 GB negro","Choloma","Retirarlo","Qué precio tienen?"],"Perfecto, sería para retirar. Tengo anotado el iPhone 15 Pro de 128GB, en negro, para Choloma. Primero hay que confirmar disponibilidad, precio y punto de retiro; te atiende un asesor con esos datos."]
]
failed=[]
cases.each do |id,text,turns,prev|
 ctx=SoftMobileSales.context_from(turns)
 response=SoftMobileSales.plan(text,ctx,[],prev)
 reply=response[:reply].to_s
 good=case id
 when /^city_/ then ctx[:city]=='Villanueva' && !reply.include?('¿En qué ciudad lo necesitás?')
 when /^pickup_/ then ctx[:delivery_mode]=='Retiro' && !reply.include?('¿Preferís retirarlo o recibir envío?')
 when "confusion" then reply.match?(/(?:expliqué mal|Disculpá|Todavía no tengo confirmados)/i) && !reply.include?("Perfecto, sería para retirar")
 when "price_after_handoff" then response[:intent]==:price && reply.match?(/precio/i) && !reply.start_with?("Perfecto, sería para retirar")
 else false
 end
 puts "HISTORICAL_REPLAY=#{id} #{good ? 'PASS' : 'FAIL'} intent=#{response[:intent]} mode=#{ctx[:delivery_mode]}"
 failed << id unless good
end
puts "HISTORICAL_REPLAY_TOTAL=#{cases.length} PASS=#{cases.length-failed.length} FAIL=#{failed.length}"
raise "Historical replays failed: #{failed.join(',')}" unless failed.empty?
