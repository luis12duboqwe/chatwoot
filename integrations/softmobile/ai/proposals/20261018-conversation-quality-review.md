# SoftMobile — revisión de respuestas comerciales (18 octubre 2026 UTC)

**Estado:** propuesta de código y pruebas, sin despliegue. Este PR no altera el vendedor activo de Chatwoot.

## Problemas corregidos en el candidato

1. Preguntas combinadas sobre **garantía, accesorios y estado nuevo/usado**, que antes quedaban contestadas parcialmente.
2. Preguntas sobre **plazo de entrega** antes de comprar, para las que el bot debe confirmar disponibilidad, destino y transporte sin inventar fechas.
3. Preguntas sobre **seguimiento de pedidos ya pagados** y cuánto tardaría un **cambio de color, capacidad o modelo**.

### Segunda ronda adversarial

La primera prueba de 16 conversaciones consiguió corregir 7 casos, pero una ronda ampliada reveló dos regresiones: garantías por accesorios ya dañados se confundían con dudas previas a la compra. El parche fue revisado para separar ambos contextos. Se añadieron variantes de lenguaje y controles de reparaciones, reclamaciones, fotos, financiamiento y stock.

**Resultado definitivo de la candidata:**

| Evaluación | Resultado |
|---|---:|
| Conversaciones ficticias en contenedor aislado | 42 |
| Respuestas incorrectas corregidas | 19 |
| Casos de control sin regresiones | 23 |
| Casos nuevos sin resolver del objetivo probado | 0 |
| Pruebas comerciales Ruby del candidato | 117/117 |
| Pruebas Python locales del laboratorio | 153/153 |

Se ejecutaron dos versiones del motor Ruby por separado en contenedores efímeros con `--network none`, sin montajes del VPS, con raíz de solo lectura, usuario no privilegiado y recursos limitados. **No se enviaron mensajes a clientes ni se consultó inventario real.**

### Evidencia y límites

- `20261018-conversation-quality.patch`: únicamente diferencias de texto; no son código aplicado.
- `20261018-conversation-quality-report.json`: resultados y huellas SHA-256 del código original y candidato.
- `prepare_conversation_quality.py`, `evaluate_conversation_quality.py`, `test_conversation_quality_extended.py`: lógica de construcción, evaluación y casos portables de seguridad.
- Sigue pendiente **revisión humana independiente** de la política comercial y de las coincidencias lingüísticas. Los 42 casos no prueban capacidad de venta ni cubren todas las frases posibles.
- Toda garantía, promoción, estado de la unidad, plazo de entrega, precio o accesorio concreto debe confirmarse por una persona autorizada.
- No fusionar ni desplegar automáticamente. No ampliar la bandeja piloto a clientes generales.
- El [PR #3](https://github.com/luis12duboqwe/chatwoot/pull/3) sobre variantes de color/capacidad es independiente.

**Nota:** una ejecución de CI con pruebas unitarias sin secretos verifica reproducibilidad, pero por sí sola no vuelve a ejecutar las pruebas Ruby del VPS. Ambas evidencias deben evaluarse por separado.