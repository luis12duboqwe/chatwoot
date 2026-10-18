# Auditoría del laboratorio: por qué no detectó un bloqueo de venta

**18 octubre 2026.** Alcance: piloto único Chatwoot, cuenta 2,
bandeja 2, conversación 3. Sin venta pública ni inventario verificado.

## Evidencia del problema

Cliente (mensaje 252): «Tienen 14 pro Max?»
Bot instalado V4 (mensaje 254): «Aún no tengo confirmada la existencia
del iPhone 14 Pro Max. Un asesor debe comprobar la unidad con el proveedor
antes de confirmarte disponibilidad.»

La respuesta no inventó stock, pero tampoco preguntó capacidad y color.
La prueba comercial sintética 72/72 no cubría el fallo. El detector
`quality_auditor.detect` tampoco tenía el tipo de error
`stock_no_next_step`. El mecanismo de automejora solo podía crear
reglas para otras cuatro familias.

## Corrección del LABORATORIO, no del bot público

1. El auditor ahora detecta consultas de stock con modelo pero sin
   capacidad que no preguntan la variante faltante. Incluye el
   coloquialismo «14 pro Max», además de «iPhone 14 Pro Max». Respeta
   pedidos completos y peticiones de atención humana.
2. Nuevo indicador `stock_no_next_step` en los informes, registro
   de incidencias y clasificación determinista. Mensaje 254
   retroregistrado como QA pendiente mediante un informe local;
   no se envió ninguna respuesta nueva al cliente.
3. Una prueba determinista de esta clase se ejecuta en cada lote
   sintético, incluso cuando el generador Groq llena sus cupos.
4. Si Groq está limitado, `synthetic_lab` usa compradores ficticios
   aprobados, evalúa el Ruby real y guarda errores deterministas.
   Identifica explícitamente los casos SIN segunda opinión Groq.
5. `autonomous_learning` ahora dispone de la familia
   **acotada** `stock_followup`, con respuesta estática segura:
   «Podemos consultar por ese modelo. Todavía no tengo existencias
   confirmadas. ¿De cuántos GB y en qué color lo buscás?»
   Esta regla solo puede surgir de la señal determinista sobre una
   consulta SIN capacidad ni color; los otros temas siguen requiriendo
   una evaluación AI previa. No se permite que Groq escriba código.
6. El ensayo extremo-a-extremo **sin Groq** sí guardó el error
   `44e4f8ea4027623d47`, lo clasificó y generó una candidata
   desde la regla permitida. `autonomous_learning.py --dry-run`
   produjo `verified_in_sandbox`, `target_improved` y
   **117/117 regresiones Ruby**. Sin cambios públicos.
7. La corrección estática más general de disponibilidad también
   quedó revisada como `stock-followup-c2ddd5f703cd8222ee.rb`:
   5/5 casos dirigidos, 72/72 ventas, 48/48 cuotas,
   8/8 preferencias, 108/108 inventario sintético,
   113 conversaciones históricas sin nuevas alarmas
   y 57/57 pruebas Ruby dentro de Chatwoot.

## Qué todavía NO está terminado

- La V4 pública sigue con SHA-256
  `970ac57ef00ba068d5319ec8b865dbaa597192e21a1ea1f16d9ca5273bf13d7a`.
  **No** tiene instalada la mejora de disponibilidad y continuación.
- El sistema de automejora sigue limitado a familias de reglas
  aprobadas; los problemas fuera de ellas se detectan/revisan, pero no
  se corrigen automáticamente de forma arbitraria.
- El límite diario de despliegues, el respaldo y la reversión
  siguen activos. Esta ejecución NO añadió una excepción de deploy.
- El laboratorio no debe considerarse vendedor completamente
  autónomo hasta completar pruebas inéditas y datos reales
  de inventario, color, precio y entrega.

La distinción fundamental es entre **detectar**, **generar candidata**,
**aprobar en sandbox**, **instalar** y **probar instalada**.
Solo la tercera fase se ha demostrado para esta falla.
