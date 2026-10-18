# Laboratorio de conversión comercial — simulaciones aisladas

Todas las conversaciones y existencias son completamente ficticias. No se envían
mensajes a Chatwoot, WhatsApp, WAHA, ni se cobran pagos. El intérprete Ruby
proviene del bot real, pero corre **sin red** dentro de Docker desechable; el
inventario y la lógica de apartados son adaptadores Python exclusivos de pruebas.

## Recorridos

`conversion_training_lab.py` genera 72 ventas ficticias reproducibles a partir
de 12 variantes de prueba y 6 rutas comerciales:

- compra con intención explícita y checkout **solo simulado**;
- crédito / cuotas y verificación de condiciones financieras;
- negociación sin prometer rebajas ni pagos;
- petición de apartar con control de disponibilidad ficticia;
- entrega y plazo sin garantía no verificada;
- accesorios y garantía con asesor.

Cada caso se evalúa contra un oráculo de modelo, capacidad, color y unidades de
inventario **independiente** de la respuesta del bot. Comprueba además
afirmaciones financieras peligrosas, prohibición de cobros reales, traspaso al
asesor y progreso permitido en la compra ficticia. No concede puntos
comerciales reales por el hecho de crear un checkout simulado.

La ejecución inicial del bot activo el 18 de octubre de 2026 pasó **60/72
(83.3%)**, con **12 fallas en cuotas**: «a 12 meses» se interpretaba como el
modelo Samsung A12 y borraba el contexto del teléfono seleccionado.

## Corrección preparada, no desplegada

`conversion_candidate_review.py` crea **solo para revisión** un parche estático
de una expresión regular con exclusión explícita de «a 12 meses/cuotas/pagos/
plazos», manteniendo la detección legítima de Samsung A12.

El candidato pasó, de manera **aislada**:

- 72/72 conversaciones comerciales (antes 60/72);
- 48/48 preguntas de cuotas que **no estaban** en la primera batería
  (antes 0/48), con 10, 18, 24 y 36 meses/cuotas;
- 117/117 regresiones Ruby y 108/108 conversaciones de inventario;
- reconocimiento legítimo de Samsung A12 de 64 GB negro;
- ninguna declaración nueva de disponibilidad, aprobación crediticia ni pago.

La corrección está guardada en un archivo candidato con SHA-256 registrado
dentro de `quality/conversion-candidates`. No modifica el bot de producción
ni requiere autorización para hacerlo. El reporte
`quality/financing-model-review.json` está marcado
`review_ready_not_deployed`. Una instalación futura debe respetar los
mismos controles de despliegue, revisión y reversión del piloto.

## Estado e incidencias

`quality/sales-conversion-training-report.json` guarda aciertos por familia
y revisión de los errores. `quality/sales-conversion-review-proposals.json`
recoge **solo sugerencias de corrección**, sin instrucciones ejecutables ni
promociones automáticas. Las pruebas del modelo se repiten con cada revisión.

```bash
cd /opt/softmobile-waha-test/laboratorio-ia
python3 conversion_training_lab.py --run
python3 conversion_training_lab.py --status
python3 financing_holdout.py --run
python3 conversion_candidate_review.py --status
python3 -m unittest -q test_conversion_training_lab test_financing_holdout test_conversion_candidate_review
```

El objetivo es seguir aumentando la calidad de mensajes nuevos, pero la
puntuación de estas simulaciones NO mide conversiones reales, ventas completadas
por Ruby, disponibilidad real de celulares ni calidad del modelo Groq sin
filtros. Para atención automática real faltan inventario autorizado, precios
y condiciones verificadas, pruebas supervisadas de extremo a extremo, y
autorización expresa para ampliar el piloto.
