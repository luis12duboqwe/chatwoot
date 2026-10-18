# Revisión de parche SoftMobile: selección de color y capacidad

**Estado: aprobado por pruebas aisladas, pendiente de revisión humana.** El archivo `.patch` es una propuesta de texto y **no modifica ni ejecuta código del bot activo**.

## Problema detectado

El cliente ficticio solicita varios colores y capacidades en una conversación, por ejemplo: «si no hay 512 GB negro, mejor 256 GB azul». El bot actual puede conservar el color de la opción que se descarta.

## Evidencia comparativa — 18 de octubre de 2026 (UTC)

Se probó primero la propuesta original del PR #3, que elegía siempre el último color al encontrar ciertas palabras. Esa primera versión **fue rechazada**: bot actual **23/30** escenarios correctos; candidato original **23/30**, con **6 errores corregidos y 6 regresiones nuevas**.

Se preparó una **segunda versión determinística, escrita para revisión**, que distingue alternativas condicionales de simples preguntas sobre otros colores. Se verificó con el mismo conjunto de 30 escenarios:

| Métrica | Bot actual | Segunda propuesta |
| --- | ---: | ---: |
| Casos correctos | 23/30 | **30/30** |
| Errores previos corregidos | — | **7** |
| Regresiones introducidas | — | **0** |

Además, la propuesta superó **117/117 pruebas comerciales Ruby**, distribuidas en 57 del motor, 5 regresiones básicas, 7 históricas, 20 recorridos, 11 del piloto, 2 de pagos y 15 escenarios futuros.

## Aislamiento y seguridad

Las comparaciones se ejecutaron en contenedores efímeros nuevos, separados del contenedor Chatwoot que atiende usuarios, con `--network none`, raíz de solo lectura, usuario no privilegiado, sin montaje de archivos del VPS ni del socket Docker, sin capacidades Linux y con límites de recursos. Se deshabilitó el origen HTTP del catálogo y se probaron respuestas sin inventario conectado.

**Ninguna propuesta Groq ni esta alternativa se ejecutó en el contenedor de producción.** El parche únicamente modifica `context_from` cuando se aplique expresamente en un paso posterior autorizado. No se envió ningún mensaje al cliente.

## Procedencia y decisiones de revisión

Los cinco intentos anteriores de Groq se rechazaron por falta de efecto, formato incorrecto o sintaxis Ruby inválida. La propuesta actual es una alternativa **determinística elaborada para revisión**, no código de Groq validado automáticamente.

## Pendiente antes de aplicarla

Una persona autorizada debe revisar la lógica, validar un conjunto independiente de diálogos (incluyendo variaciones lingüísticas no presentes en estas 30 pruebas), verificar CI y confirmar que no afecta otras reglas de selección. Solo entonces podrá considerarse un despliegue controlado al piloto, con respaldo y reversión.

**No fusionar ni desplegar automáticamente este PR.**