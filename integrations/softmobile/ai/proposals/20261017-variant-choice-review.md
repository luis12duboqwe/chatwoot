# SoftMobile: propuesta de revisión de capacidad y color

**Estado:** propuesta inerte; no aplicada al bot ni ejecutada como código Ruby.

**Caso sintético:** `6080c2a5b31ef5b2a9`. En una conversación ficticia, el comprador cambió sucesivamente entre iPhone 15 con distintas capacidades y colores; el bot conservó el color de una alternativa que acababa de descartarse.

## Origen del parche

Groq produjo cinco intentos de parche; el primero no tenía efecto práctico y los otros cuatro fueron rechazados por los controles de validación. La revisión automatizada rechazó los que no generaban un cambio de comportamiento, no coincidían con el fragmento exacto o no superaban el análisis de sintaxis Ruby. **Este parche es una alternativa determinística elaborada para revisión tras analizar esos errores; no es código libre de Groq aprobado.**

## Cambio propuesto

Al detectar varias opciones de color en el mismo mensaje, reconocer frases condicionales como «si no hay» o «mejor» antes de seleccionar la última alternativa, en lugar de usar siempre el primer color mencionado.

## Verificaciones realizadas

- Análisis estático de alcance: únicamente un bloque del método `context_from`.
- Sintaxis Ruby: **aprobada** mediante `ruby -c`, que no ejecuta la aplicación.
- Batería Python del generador y sus controles de seguridad: **123/123** en el VPS.
- **No se ha ejecutado** la batería de escenarios comerciales sobre el código propuesto ni se ha efectuado un despliegue. Por tanto, la funcionalidad aún **no está validada**.
- Sin acceso a API keys, datos personales de clientes, cuentas bancarias ni WhatsApp.

## Antes de aprobar

Un revisor debe inspeccionar el comportamiento con mensajes «si no hay X, mejor Y», solicitudes de dos colores sin preferencia, comparaciones de catálogo, cambio de capacidad sin cambio de color y conversaciones históricas. Luego ejecutar la batería completa en un entorno aislado sin acceso a la red y solo considerar el despliegue piloto mediante el mecanismo de copias de seguridad y reversión.

Este PR modifica **solo archivos de propuesta de revisión**, no ejecutables ni configuración del bot.
