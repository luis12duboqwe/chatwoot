# Auditoría de calidad conversacional — SoftMobile (18 octubre 2026, UTC)

**Estado: propuesta aislada, no desplegada.** Los cambios de este PR están guardados exclusivamente como un archivo `.patch` y evidencia `.json`.

## Tres defectos tratados

1. **Garantía + accesorios + condición del teléfono.** Un comprador pregunta por plazo/cobertura de garantía, regalías o accesorios y si el equipo es nuevo o usado. El bot respondía a una sola pregunta y olvidaba las demás. La propuesta recoge los tres datos pendientes y deriva a un asesor sin inventar estado o accesorios.
2. **Plazo de entrega.** Preguntas como «¿en qué plazo entregan una vez que pago?» o «¿cuál es el tiempo estimado de entrega?» eran clasificadas erróneamente o recibían respuestas genéricas. La propuesta solicita ciudad y confirma que los plazos dependen de stock y transporte.
3. **Seguimiento y cambios.** «¿Cuándo llegará mi pedido?» solicita número de pedido o guía y verificación humana. «¿Qué tiempo tardaría el cambio?» después de elegir una variante exige verificar plazo y disponibilidad, en lugar de repetir la última pregunta sobre la ciudad.

## Evidencia aislada

Se reprodujeron **16 diálogos sintéticos** en dos instancias Docker efímeras independientes (bot activo y versión candidata), con `--network none`, raíz de solo lectura, usuario sin privilegios, sin montajes ni credenciales del VPS.

- **7 fallas de conversación corregidas.**
- **9 diálogos de control sin regresiones ni cambios de respuesta.**
- **117/117 regresiones comerciales Ruby aprobadas en el candidato.**
- **150/150 pruebas Python locales existentes aprobadas.**
- Sin mensajes públicos enviados a WhatsApp, sin consulta de inventario real, sin ejecución en el contenedor Chatwoot que atiende clientes.
- Se capturó huella SHA-256 del código activo y de la candidata en la evidencia de este PR.

## Condiciones de seguridad

La propuesta **no asegura** disponibilidad, precio, promociones, seguro, accesorios, garantía específica, estado nuevo/usado, fecha de entrega ni aprobación de cambios. Todas las afirmaciones concretas requieren confirmación del personal encargado y de la unidad.

La promoción está **bloqueada** hasta revisión independiente y autorización: el sistema ya utilizó su límite de una instalación automática diaria. No cambiar esta limitación ni fusionar el PR automáticamente.

## Pendientes antes de expandir

Revisar frases alternativas no cubiertas por los 16 escenarios, hacer nuevas conversaciones del piloto con un comprador real, probar derivaciones humanas y observar métricas de cierre sin depender exclusivamente de un evaluador LLM. Las mejoras de color/capacidad siguen en el PR #3 separado; este PR no las incluye.
