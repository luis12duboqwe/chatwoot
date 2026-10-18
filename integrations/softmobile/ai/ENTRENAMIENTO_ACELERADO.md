# SoftMobile — entrenamiento acelerado y criterios para salida pública

**Estado comprobado: 18 de octubre de 2026, 20:35 UTC.**

## Qué se aceleró

- `softmobile-offline-issue-replay.timer`: cada **10 minutos**.
  Reproduce en Ruby real, ejecutado en contenedores desechables sin red,
  las conversaciones ficticias registradas por Groq.
  También compara el bot activo con una candidata revisada y rechaza
  formalmente diferencias que introduzcan nuevas banderas deterministas.
  **Cero peticiones API**; el mismo corpus se revalida, no se contabiliza
  erróneamente como conversaciones totalmente nuevas.
- `softmobile-inventory-quality.timer`: cada **30 minutos**;
  variantes y disponibilidad ficticia, con verificación independiente.
- `softmobile-sales-conversion.timer`: cada **30 minutos**;
  recorrido comercial simulado, no checkout ni cobro real.
- `softmobile-financing-holdout.timer`: cada **30 minutos**;
  frases de financiación no usadas en los escenarios anteriores.

El laboratorio Groq de generación sigue a intervalos de diez minutos
y el interactivo de quince; **NO se aumentaron esas frecuencias**,
pues Groq ya respondió con límite HTTP 429 en algunas ejecuciones.
`provider_cooldown.py` sigue respetando Retry-After. El límite
artificial diario de desarrollo NO se ha restaurado.

## Hallazgos y corrección antes de promover código

Primera corrida, sobre **111** incidentes sintéticos guardados:
- 107 reproducibles en el contenedor sin red; 4 descartados previamente.
- 51 seguían mostrando al menos una señal determinista previa.
- 54 seguían sin pruebas deterministas suficientes (solo sospecha).
- 1 señal anterior desapareció; 1 caso mostró una señal nueva.
- Reproducción completada en ~5 segundos, sin tocar mensajes públicos.

El comparador descubrió que la candidata V2 añadía una **repetición**:
contestaba con el mismo texto sobre el precio de la funda cuando
el comprador preguntaba después si el cargador incluido era original.
Se corrigió en la regla general, excluyendo preguntas de autenticidad
del detector de precios/regalías. Se agregó esa pregunta a los
**15 controles negativos**.

La versión revisada **V3**
(`bundle-static-semantic-financing-directness-20261018-v3`)
tiene SHA-256
`d58682904e798606ede7dca3815fee8044f00f5efa87eb2f86220b3cfa520772`.
Nueva evidencia:
- 72/72 recorridos de venta ficticia;
- 48/48 frases desconocidas de cuotas;
- 108/108 casos de inventario ficticio;
- 10/10 positivos y **15/15 negativos** de accesorios;
- 117/117 regresiones Ruby;
- **107/107** conversaciones sintéticas reejecutadas SIN señales
  deterministas adicionales en la candidata respecto al bot activo;
- Groq volvió a revisar la nueva versión de código con
  `error=false`, `category=no_issue` en la consulta crítica.
- **352/352 pruebas Python** locales del laboratorio.

El código candidato está revisado, pero las pruebas no significan que
se hayan resuelto todos los incidentes históricos (51 siguen mostrando
señales genéricas en ambos códigos). Deben clasificarse y corregirse
sin tratar falsas alarmas como errores comerciales probados.

## Criterios de salida pública pendientes

1. Cumplir los controles del desplegador piloto V3, con cupo global
   único por día, copia de seguridad, revalidación y reversión.
2. Repetir nuevas conversaciones que NO estaban en el conjunto de
   construcción, sin regresiones críticas de seguridad, pagos,
   información comercial ni entrega.
3. Depurar las señales deterministas persistentes, diferenciar
   repeticiones legítimas de respuestas que perjudican al comprador.
4. Conectar inventario, colores, unidades y precios **reales y
   autorizados** (el catálogo maestro no tiene stock validado).
5. Verificar en Chatwoot un recorrido real supervisado:
   preguntas, foto/condición, stock, financiación, apartado,
   entrega, escalamiento, ausencia de pagos ficticios y recuperación
   de errores. Obtener aprobación explícita antes de ampliar el piloto.

**No existe garantía técnica de 100 % de precisión en mensajes
arbitrarios.** El objetivo es cero fallos críticos demostrados en una
batería reproducible, resultados estables en casos inéditos,
supervisión y reversión. Un resultado de 100 % en simulaciones
no autoriza abrir el bot comercial.

## Comandos

```bash
cd /opt/softmobile-waha-test/laboratorio-ia
python3 offline_issue_replay.py --run
python3 offline_issue_replay.py --status
python3 inventory_quality_lab.py --status
python3 conversion_training_lab.py --status
python3 financing_holdout.py --status
python3 promotion_budget.py
python3 production_readiness.py
systemctl list-timers --all | grep softmobile-
systemctl disable --now softmobile-offline-issue-replay.timer
```

Todos los datos del nuevo informe son casos ficticios y etiquetas de
calidad. Ninguna operación del laboratorio usa inventario real,
autorizaciones de cobro ni comunicaciones públicas.
