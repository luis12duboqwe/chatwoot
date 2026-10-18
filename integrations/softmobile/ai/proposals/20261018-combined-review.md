# SoftMobile — revisión conjunta de las correcciones conversacionales

Fecha UTC: 18-10-2026. **Propuesta de código Ruby en revisión; no instalada en el motor público.**

## Alcance
La evaluación combina el parche de variantes de color/capacidad (antes PR #3) y el de preguntas comerciales combinadas (PR #4), en ese orden. Se construyó desde una copia exacta del motor del VPS, sin escribir sobre él.

- SHA-256 de la versión Ruby de referencia: `e1c5fd9d11754972b60257f906907d48e918b905584930e8adbbc3c57e55dacd`
- SHA-256 del candidato combinado: `79d457ca3f3bc295819a1c430249af77a33f5ea347d1d9929b85c949a7ec1c4d`
- Comparación de variantes: referencia **23/30**, candidato **30/30**; 7 fallos corregidos, 0 regresiones.
- Conversaciones dirigidas: **16 escenarios**; 7 conductas corregidas, 9 controles no afectados, 0 regresiones y 0 objetivos pendientes.
- Regresión Ruby aislada: **117/117** aprobadas (57 motor, 5 regresiones, 7 históricas, 20 recorridos, 11 piloto, 2 pagos, 15 futuras).
- Entorno de prueba: contenedores efímeros sin red, sin acceso a credenciales ni volúmenes de producción, raíz de solo lectura y usuario no privilegiado.
- Mensajes públicos emitidos durante las pruebas: **0**.

## Separación entre evaluaciones y producción
Este candidato de Ruby **no fue aplicado** a `sales-bot-v2.rb`. La funcionalidad de Groq que sí se instaló en el VPS es exclusivamente el *filtro de notas privadas* (`suggestion_guard.py`), SHA de blob Git `38b74386d6475a8753465ca3d622c00e33e42510`, después de 234/234 pruebas Python. Conserva la restricción de piloto cuenta 2, bandeja 2 y conversación 3.

## Requisitos aún abiertos
1. Revisión técnica y comercial independiente de reglas y mensajes.
2. Comprobar una conversación nueva end-to-end por el canal autorizado, con consentimiento.
3. Verificar por unidad inventario, precios, garantía, condiciones de pago y entrega.
4. Medir claridad, exactitud y utilidad comercial del modelo con un juez independiente; la evaluación de 20 turnos de Groq sigue teniendo 7/20 respuestas aprobadas bajo la rúbrica estricta. El buen resultado del respaldo determinístico no sustituye esa evidencia.
5. Respetar límites diarios de despliegue, test de regresión posterior y rollback antes de ampliar alcance.

**No fusionar hacia producción ni abrir respuestas automáticas globales hasta completar lo anterior.**
