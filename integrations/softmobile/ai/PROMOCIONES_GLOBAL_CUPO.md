# Límite compartido de promociones automáticas — piloto SoftMobile

18 de octubre de 2026. Este documento aplica solamente a despliegues
automáticos de código Ruby del piloto Chatwoot (cuenta 2, bandeja 2,
conversación 3), no a las llamadas a Groq, generación de simulaciones,
jueces ni consultas de inventario.

**Problema detectado:** había tres registros independientes de mejoras:

- `autofix-history.json` para correcciones de reglas de pago;
- `repair-lab-history.json` para reparaciones por familias;
- `learned-dialogue-history.json` para aprendizaje y promoción semántica.

Cada proceso comprobaba su límite, pero NO los despliegues de los demás.
La lectura histórica identificó tres promociones registradas el 17 de
octubre y dos el 18. No hay prueba de que el límite declarado de
«una promoción por día» fuera global anteriormente.

**Corrección:** `promotion_budget.py` lee los tres historiales protegidos,
cuenta únicamente despliegues confirmados y publica
`usage("YYYY-MM-DD")` y `exhausted(day)`. Cualquier bitácora corrupta,
registro confirmado sin fecha o fecha inválida bloquea por seguridad.
Se mantiene el reloj UTC y el tope GLOBAL `DAILY_LIMIT=1`.

Los seis motores consultan el mismo presupuesto:

1. `auto_improver.py`;
2. `repair_lab.py` (en ambas verificaciones de cuota);
3. `autonomous_learning.py`;
4. `semantic_promoter.py`;
5. `combined_pilot_promotion.py`;
6. `finance_pilot_promoter.py`.

Todos comparten además el bloqueo `auto_improver.LOCK` durante el
despliegue, evitando que dos modificaciones de estos motores se
autoricen simultáneamente. El conteo global no agrega una cuota
artificial a los tokens o a la API de Groq.

## Evidencia al instalar

- 17 oct: 2 correcciones de pago + 1 reparación + 0 aprendidas = **3**.
- 18 oct: 0 pagos + 1 reparación + 1 aprendizaje = **2**.
- 19 oct: todavía **0** antes del siguiente periodo de promoción.
- El 18 oct tanto `combined_pilot_promotion.py --run` como
  `finance_pilot_promoter.py --run` devolvieron
  `daily_deployment_cap` SIN modificar Ruby.
- **345/345 pruebas Python** pasaron después de instalar el guardia.
- SHA-256 del Ruby público antes y después:
  `4dc2814ddb5d3a03c31add202cb004f6369a77b154f2fa5141d5dfb3220ef106`.

El límite se restablecerá solamente al llegar al siguiente día UTC.
La promoción conjunta se revisa en la siguiente ventana a las 00:05 UTC;
si no se instaló, la contingencia de financiamiento revisa a las 00:09.
Si otro motor logra una promoción válida el mismo día, ambos se abstienen.
La instalación NO está garantizada: se revalidan fuente, candidato,
regresiones, evaluación independiente y todos los controles.

## Diagnóstico seguro

```bash
cd /opt/softmobile-waha-test/laboratorio-ia
python3 -c 'import promotion_budget;print(promotion_budget.usage())'
python3 -m unittest -q test_promotion_budget
python3 -m unittest discover -p 'test_*.py' -q
python3 combined_pilot_promotion.py --status
python3 finance_pilot_promoter.py --status
```

Este cambio no habilita clientes generales, no importa el catálogo de
entrenamiento y no permite ventas, apartados o pagos reales.
