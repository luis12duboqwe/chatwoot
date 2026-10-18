# SoftMobile: contrato verificable del laboratorio de automejora

Actualizado: 18 de octubre de 2026 (UTC).

## Qué significa "100 %"

El estado de ingeniería se calcula por **evidencia observable**, sin
declarar falsamente que una IA no cometerá errores.

`python3 lab_acceptance.py --run` publica
`quality/lab-acceptance-report.json`, con todos los controles, el
puntaje ponderado y los criterios pendientes. Un valor de 100/100
significa exclusivamente que los **controles técnicos del laboratorio**
fueron satisfechos por sus evidencias vigentes. No autoriza publicidad,
precios, apartados, pagos reales ni ampliación de Chatwoot.

## Diez puertas obligatorias (100 puntos en total)

| Puerta | Puntos | Qué debe demostrarse |
|---|---:|---|
| Generación de compradores ficticios | 10 | 200+ diálogos y una ejecución reciente |
| Compradores que reaccionan al bot | 5 | 10+ conversaciones, 8+ categorías |
| Evaluación independiente recuperable | 10 | 95 %+ de conversaciones puntuadas, recuperación reciente |
| Replay seguro sin Internet | 10 | 100+ diálogos, 0 llamadas API, datos frescos |
| Incidentes clasificados | 10 | 100+ observaciones, análisis reciente y sin pruebas falsas atribuidas a IA |
| Señales repetidas clasificadas y resueltas | 10 | 0 grupos de señales reproducidas pendientes de revisión independiente |
| Candidata probada | 10 | Ventas, cuotas, accesorios, Ruby, inventario y backlog sin regresiones; dictamen Groq reciente |
| Bot piloto instalado aprobado | 15 | SHA exacto desplegado y pruebas comerciales repetidas contra la instalación |
| Retest y segunda opinión *después* de instalar | 10 | Revisión posterior independiente favorable de las reglas aprendidas |
| Piloto aislado | 5 | Sin ventas, cambios de stock ni mensajes públicos de entrenamiento |
| Instalación revertible y limitada | 5 | Sin código Groq arbitrario, sin promociones desde el replay y bitácora de despliegues |

Las once filas equivalen a 100 puntos. Son verificaciones
**conjuntivas** (aprobar tests antiguos no reemplaza verificar el
código actualmente instalado).

## Nueva recuperación de evaluaciones pendientes

`deferred_grading.py` procesa en máximo dos llamadas por ejecución
transcripciones ya generadas por `interactive_lab.py`, sin inventar
de nuevo al comprador ni reutilizar clientes reales.

- Verifica IDs/hash del escenario, rol, mensajes y longitud de la
  respuesta antes de mostrarlo al juez Groq.
- Guarda una crítica independiente válida y sincroniza las incidencias
  pendientes sin duplicarlas. Nunca convierte su texto en código.
- Un HTTP 429 o error conserva la conversación para reintentar tras
  30/60/120/240 minutos. El retraso respeta además
  `provider_cooldown.py`.
- Usa el mismo bloqueo y contador Groq compartido, sin reinstaurar
  límites diarios artificiales a la API de desarrollo.
- `softmobile-deferred-grading.timer`: cada 20 minutos.

La primera ejecución del 18 oct evaluó una conversación y conservó
otra pendiente por respuesta no disponible del proveedor, sin pérdida
de mensajes ni nuevos despliegues.

## Nueva priorización de errores por grupos

`issue_resolution_queue.py` cruza el historial con resultados de
`offline_issue_replay.py`; agrupa señales repetibles por tema y
tipo de error. No confunde una señal determinista con un fallo real
confirmado. Ningún registro puede instalar código sin pasar las demás
baterías independientes.

En la primera medición: **112 observaciones**, **108 replays**,
**52 observaciones con señales reproducidas** repartidas entre
**16 grupos** que requieren evaluación. Esas 52 NO equivalen a
52 fallos confirmados en clientes.

Cadencia de reevaluación: clasificación cada 30 minutos (minutos
05 y 35), grupos al 07 y 37, y comprobación de aceptación al 09
y 39. Todo este proceso es offline y no utiliza Groq.

## Estado de aceptación del 18 oct 2026 a las 20:48 UTC

**55/100 puntos** verificados bajo el nuevo contrato estricto.
Puertas pendientes:
- Una de 14 conversaciones interactivas no tiene juicio AI independiente
  validado (13/14 = 92,86 %, menor a 95 %).
- Dieciséis grupos de alertas están pendientes de verificación individual,
  descarte justificado o corrección con evidencia.
- La versión pública conserva SHA-256
  `4dc2814ddb5d3a03c31add202cb004f6369a77b154f2fa5141d5dfb3220ef106`
  y falla todavía las 12 pruebas financieras específicas; el paquete
  mejorado V3 tiene SHA-256
  `d58682904e798606ede7dca3815fee8044f00f5efa87eb2f86220b3cfa520772`,
  pero sigue preparado y NO desplegado.
- Falta validar el nuevo código instalado contra el historial real de
  simulaciones y obtener una segunda revisión Groq posterior a la
  instalación; una aprobación anterior del candidato no es suficiente.

La cifra 55/100 es más rigurosa y no directamente comparable con
anteriores estimaciones generales de avance de implementación,
como 85 %. No significa que el laboratorio haya perdido funciones:
se han definido nuevas puertas de aceptación independientes.

## Herramientas

```bash
cd /opt/softmobile-waha-test/laboratorio-ia
python3 deferred_grading.py --status
python3 issue_resolution_queue.py --run
python3 lab_acceptance.py --run
python3 lab_acceptance.py --status
python3 -m unittest discover -p 'test_*.py' -q
systemctl list-timers --all | grep -E 'deferred-grading|issue-resolution-queue|lab-acceptance'
```

**No prometer 100 % técnico antes de que todas las puertas pasen.**
El inventario real y el recorrido comercial supervisado en Chatwoot
tienen su propia autorización separada y siguen pendientes.
