# Inventario aislado para entrenar SoftMobile

**Solo simulación. Todos los precios, existencias y colores son inventados.**
Nunca se publican en Chatwoot, WAHA, WhatsApp, campañas o el inventario real.

## Cómo funciona

- `training_inventory.py`: catálogo artificial con 12 variantes y 23
  unidades ficticias, controlado íntegramente en memoria. Cada ejecución
  comienza con un stock NUEVO y descarta todos sus cambios al finalizar.
- `inventory_training_lab.py`: envía las consultas ficticias al **intérprete
  del Ruby real**, en un contenedor Docker desechable SIN red, SIN volúmenes,
  sin acceso a Chatwoot y con raíz de solo lectura. Toma modelo, capacidad y
  color interpretados por Ruby y comprueba la respuesta frente al catálogo
  ficticio usando un adaptador de entrenamiento independiente en Python.
  **No inserta stock en el Ruby público.**
- `inventory_training_ai.py`: opcional. Groq redacta preguntas ficticias del
  comprador usando SOLAMENTE los modelos/capacidades/colores de esta prueba.
  Nunca produce precios ni modifica existencias, y el resultado pasa por
  el mismo intérprete aislado. El proveedor puede responder HTTP 429, que
  suspende temporalmente las llamadas sin afectar la práctica local.
- `quality/training-inventory-catalog.json`: copia privada del catálogo de
  muestra, con el aviso de simulación y marcada como no autorizada para uso
  comercial.
- `quality/training-inventory-report.json`: pruebas de disponibilidad,
  agotados, variantes, cambios de capacidad, apartados, liberación, venta
  ficticia, prevención de sobreventa y reajuste ficticio de precio.
- `quality/training-inventory-ai-report.json`: observaciones de compradores
  ficticios generados por IA o estado de indisponibilidad de Groq.

## Datos de ejemplo (TOTALMENTE INVENTADOS)

- iPhone 14 Pro Max 256 GB negro: **3 ficticios**, **L 18,950 ficticios**.
- iPhone 14 Pro Max 256 GB dorado: **0**, **L 18,875 ficticios**.
- Samsung S24 Ultra 256 GB azul: **2 ficticios**, **L 23,900 ficticios**.
- iPhone 13 128 GB blanco: **2 ficticios**, **L 10,850 ficticios**.

Estos valores NO provienen de una lista comercial y jamás deberían
ofrecerse a un cliente.

## Seguridad

No hay acceso a ERP real, base de datos Chatwoot, Google Sheets de producción,
pasarelas de pago, IMEI reales, direcciones de clientes ni credenciales en
el contenedor de pruebas. Los apartados generan identificadores `LAB-HOLD-`
que solo existen durante esa ejecución. Ninguna venta de entrenamiento
cobra dinero ni altera el stock de SoftMobile. Las respuestas están
precedidas por `SIMULACIÓN / INVENTARIO FICTICIO — NO OFRECER A CLIENTES`.

La prueba de precio no significa que el bot real ya tenga inventario:
el adaptador de la consulta está **solo en el laboratorio**. Para ventas
reales se requerirá integrar un inventario autorizado y actualizar
comprobaciones de veracidad.

## Comandos

```bash
cd /opt/softmobile-waha-test/laboratorio-ia
python3 inventory_training_lab.py --run
python3 inventory_training_lab.py --status
SOFTMOBILE_INVENTORY_AI_ENABLED=true python3 inventory_training_ai.py --run
python3 -m unittest -q test_training_inventory test_inventory_training_lab test_inventory_training_ai
```

Servicios programados (si están habilitados):
`softmobile-inventory-training.timer` — simulador sin red cada dos horas;
`softmobile-inventory-ai.timer` — cliente Groq ficticio cada cuatro horas.

Ambos pueden detenerse sin afectar Chatwoot:

```bash
systemctl disable --now softmobile-inventory-training.timer softmobile-inventory-ai.timer
```

## Ampliación: auditoría de 108 conversaciones y 32 compradores simultáneos

`inventory_quality_lab.py` compara **108 recorridos generados de forma
determinista** con el motor Ruby REAL ejecutado en contenedores temporales
sin red. Un oráculo independiente conoce la intención del comprador
simulado y compara modelo, capacidad, color, disponibilidad y omisiones.
La puntuación de calidad nunca se calcula a partir de la opinión de Ruby
sobre sí mismo. El informe se guarda en
`quality/training-inventory-quality-report.json`.

Las consultas cubren 9 familias (12 casos por familia): modelo específico,
pregunta de existencia, aclaraciones sucesivas, cambio de color, contexto de
precio, contexto de inventario, cambio de modelo, falta de color y capacidad
no vendida. Si una prueba falla, el laboratorio registra una incidencia
**solo para revisión** en `quality/training-inventory-review-issues.json`.
No autoriza cambios automáticos de producción.

El inventario artificial ahora protege apartados, liberaciones, checkout y
cambios de precio con un bloqueo en memoria. La prueba paralela simula
**32 compradores** compitiendo por **tres unidades**: nunca se vende una
cuarta. Si el precio ficticio cambia DESPUÉS de un apartado, la operación
de entrenamiento conserva el valor del apartado original.

El promotor `semantic_promoter.py` ahora exige, además de sus pruebas Ruby,
**no empeorar** en los 108 escenarios de inventario simulados y registrar
**cero afirmaciones no verificadas** antes de plantear un despliegue
piloto. Una prueba futura del promotor cumplió todos los criterios SIN
instalar código; la promoción real sigue limitada por las salvaguardas
del ciclo automático.

Para ejecutar/revisar:
```bash
python3 inventory_quality_lab.py --run
python3 inventory_quality_lab.py --status
python3 -m unittest -q test_inventory_quality_lab
systemctl status softmobile-inventory-quality.timer
```

`softmobile-inventory-quality.timer` ejecuta estas comprobaciones cada
dos horas al minuto 39 UTC. La programación conserva el aislamiento del
piloto y NO habilita la venta real del inventario ficticio.
