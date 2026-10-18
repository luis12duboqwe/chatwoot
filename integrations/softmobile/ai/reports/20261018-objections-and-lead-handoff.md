# SoftMobile — conversaciones largas y notas útiles para el vendedor

Fecha: 18 de octubre de 2026 (UTC). Alcance: Chatwoot piloto de cuenta 2,
bandeja 2 y conversación 3; sólo sugerencias PRIVADAS para el asesor.

## Hallazgos y correcciones

Se ejecutaron cuatro conversaciones ficticias de cinco mensajes cada una,
con datos de prueba y la API real de Groq. Cubrieron presupuesto limitado,
descuentos, financiación, garantía, inspección, cambio de color/capacidad,
comparaciones de precio, canje de equipo y cierre de compra.

- Primera ronda: **16/20** turnos que superaron los controles: un error de
  memoria de variante, una derivación humana omitida y dos contestaciones
  no suficientemente relacionadas con la objeción del cliente.
- Segundo intento: **12/20** turnos aceptados, pero ocho solicitudes de
  Groq dieron una respuesta no válida o un problema de proveedor.
  Esa ronda no se trató como una aprobación.
- Ronda final con control de límites, espaciamiento y rechazo seguro:
  **20/20** turnos pasaron las comprobaciones definidas, cero errores de
  memoria, cero omisiones de revisión humana y cero respuestas fuera de tema
  según el evaluador determinístico. Estos controles usan heurísticas y
  **no equivalen a una calificación objetiva del cierre de ventas**.

`groq_sales_objections.py` ahora identifica distintas clases de error
sin registrar respuestas del proveedor ni conversaciones reales, y puede
detenerse ante HTTP 429, errores de servidor o problemas de conexión.
Por seguridad se limita a 20 llamadas por ejecución y máximo 2 ejecuciones
manuales por día UTC, sin automatización pública.

También se arregló `journey_memory.py` para distinguir «No quiero negro,
mejor azul» de una comparación de precios con la variante negra. El filtro
comercial de `suggestion_guard.py` tiene respuestas de respaldo adaptadas
a precio, descuentos, financiación, entrega, garantía y canje, siempre
con verificación humana antes de confirmar políticas.

## Mejoras directas para SoftMobile

`lead_handoff.py` produce, de forma determinística y sin extraer datos
personales, un resumen del modelo, capacidad, color y ciudad que pueden
reconocerse con confianza. Indica al asesor el siguiente dato comercial
que debe verificar. Las notas privadas de Groq incluyen ahora esa ficha,
sin prometer disponibilidad, reservas, cobros ni entregas.

Se verificó mediante pruebas simuladas que la ficha no copia direcciones,
números telefónicos, cuentas ni información arbitraria generada por Groq.

## Verificaciones

- Suite completa Python: **215/215** pruebas aprobadas en el VPS.
- Servicio de Groq conectado a Chatwoot: ejecución satisfactoria,
  resultado `no_new_messages` durante la prueba.
- Sin mensajes públicos enviados por estas simulaciones.
- Sin cambio en el motor Ruby activo, en inventario, precios o condiciones.
- CI de GitHub debe verificarse por separado; los tests CI funcionan
  sin llamar a Groq ni a Chatwoot.

La siguiente etapa práctica no es añadir más casos idénticos al laboratorio:
es verificar una conversación piloto con un comprador autorizado y después
conectar fuentes reales de inventario y precio, con validación y permisos
de escritura diferenciados.
