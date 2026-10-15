# Prueba del flujo comercial sin Meta — 15 de octubre de 2026

## Contexto

La aplicación de Meta `Chatwoot SoftMobile` está en proceso de verificación de empresa/número para WhatsApp. El plazo de unos dos días es una estimación comunicada por Meta; no es confirmación de aprobación.

Durante la espera, se hizo una validación independiente en la instalación Chatwoot de SoftMobile (cuenta ID 2) sin tocar Meta, la aplicación del inventario ni sus campañas.

## Entorno

- Chatwoot: `https://chat.invjear.com` (HTTPS válido).
- Bandeja creada: `SoftMobile | Web de pruebas` (canal de widget web, 1 agente administrador asignado).
- Esta bandeja **no está incrustada en la página del inventario ni publicada como canal de ventas**.
- Configuración comercial previa intacta: 8 etiquetas, 11 respuestas rápidas, 7 atributos, automatización inactiva.
- Copia de seguridad previa en el VPS: `/opt/chatwoot-softmobile/backups/before-web-sales-test-20261015.dump`; no contiene datos reales nuevos y nunca se debe publicar en GitHub.

## Prueba de extremo a extremo, verificada

1. Se realizó `POST /api/v1/widget/config` vía HTTPS; código 200, token de sesión del widget generado.
2. Se realizó `POST /api/v1/widget/conversations` con un mensaje sintético de consulta de iPhone 14; código 200. Se verificó que la conversación entrante quedó registrada con atributos comerciales `sm_modelo`, `sm_ciudad` y `sm_etapa`.
3. Se simuló una respuesta saliente desde un agente y se consultó `GET /api/v1/widget/messages`; código 200 y la respuesta apareció visible para el cliente sintético.
4. La conversación de prueba se resolvió y **se eliminaron la conversación y el contacto sintéticos** para no alterar las métricas de ventas.
5. El canal web de prueba permanece creado, pero no embebido.
6. La página principal de Chatwoot y el inventario respondieron HTTP 200 al finalizar.

## Pendiente

- No se ha verificado la recepción o envío de WhatsApp, Messenger ni Instagram. No atribuir a esos canales la prueba web.
- Esperar el resultado de Meta. Revisar avisos de `Acciones requeridas` para corregir solicitudes de información; no crear múltiples aplicaciones para intentar eludir verificaciones.
- Completar alta del número, el token empresarial oficial y la conexión manual de WhatsApp Cloud API dentro de Chatwoot.
- Confirmar inventario autenticado antes de automatizar precios, existencias o reservas.
- Si se decide captar consultas en la web, aprobar por separado la inserción del widget en el sitio; no se modificó el ERP.
