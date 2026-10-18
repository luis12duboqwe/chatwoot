# Laboratorio de IA SoftMobile — auditoría de preferencias V4
**Fecha de prueba: 18 de octubre de 2026, 21:15 UTC.**

El laboratorio estaba aprobado en otras baterías, pero seguía sin entender correctamente mensajes como «cambiar de negro a azul» y «prefiero 64 GB, ¿es igual al de 128 GB?». Se añadieron ocho pruebas independientes que ejecutan el **Ruby real aislado**, sin conectarse a clientes ni al inventario comercial.

| Comprobación | Antes (bot activo y candidata V3) | Candidata V4 |
|---|---:|---:|
| Cambios explícitos de color y capacidad | 2/8 | 8/8 |
| Ventas completas ficticias | 60/72 bot activo; 72/72 V3 | 72/72 |
| Consultas inéditas de cuotas | 0/48 bot activo; 48/48 V3 | 48/48 |
| Inventario ficticio | 108/108 | 108/108 |
| Ruby histórico | 117/117 | 117/117 |
| Backlog sintético | 110 a 112 casos reejecutados | Sin señales deterministas nuevas |

Se identificó una regresión en una primera corrección: «negro en vez de azul» se interpretaba como elegir azul. Se corrigió **antes** de aprobar el parche; la candidata final eliminó dos señales anteriores de pérdida de color/capacidad sin añadir otras.

La corrección final V4 tiene SHA-256:
`970ac57ef00ba068d5319ec8b865dbaa597192e21a1ea1f16d9ca5273bf13d7a`.

## Estado de despliegue

- El bot piloto instalado sigue en la versión SHA-256 `4dc2814ddb5d3a03c31add202cb004f6369a77b154f2fa5141d5dfb3220ef106`.
- El código V4 está en `quality/combined-pilot-candidates` y `quality/variant-context-candidates`, sin despliegue.
- Los controles combinados incluyen **8/8** preferencias, **72/72** ventas, **48/48** cuotas, **108/108** inventario, **117/117** Ruby y un replay histórico completo sin regresiones nuevas.
- Una evaluación Groq favorable sobre V3 **no se reutiliza para V4**. El promotor V4 exige aprobación independiente **de ambas** consultas de accesorios y de cambios de color/capacidad, con coincidencia exacta de SHA-256 y vigencia máxima de 24 horas.
- El último intento de Groq sobre V4 devolvió error temporal y una pausa del proveedor, por lo que V4 **no está aprobada para instalarse todavía**.
- `softmobile-combined-pilot-promotion.timer` permanece limitado a un despliegue total al día UTC, con respaldo y reversión. Se detuvieron las promociones antiguas individuales de semántica y de financiamiento para evitar versiones parciales incompatibles.
- Los servicios `softmobile-context-accuracy.timer` y `softmobile-context-ai-review.timer` ejecutan, respectivamente, la batería local y el reintento independiente bajo la política de enfriamiento de Groq.

El marcador `lab_acceptance.py` se endureció para exigir también esta memoria de preferencias, por lo que ahora el porcentaje verificado puede disminuir hasta que V4 reciba el dictamen Groq y se instale. Ese descenso no representa pérdida de funcionalidades; es evidencia de más controles de calidad pendientes.

## Qué falta para la aprobación técnica del laboratorio

1. Completar la evaluación independiente de las conversaciones que quedaron sin juicio válido por el proveedor.
2. Investigar los grupos de alertas históricos sobre repeticiones, entregas, pagos y objeciones, sin confundir todas las alertas con errores confirmados.
3. Aprobar V4 independientemente, instalarla en el piloto, volver a comprobarla y garantizar que no se amplía el número de clientes atendidos.
4. Confirmar que la mejora se sostiene ante preguntas inéditas y que el sistema revierte un cambio si introduce regresiones.

El 100 % aquí solo significará **cumplimiento de una lista técnica de aceptación comprobada**, nunca ausencia garantizada de errores de IA ni autorización para atender ventas reales.
