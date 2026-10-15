# Conexión de WhatsApp Cloud API — SoftMobile

Actualizado: 15 de octubre de 2026.

**Instalación:** Chatwoot Community Edition autoalojado en https://chat.invjear.com, cuenta SoftMobile n.º 2.

## Verificado en el servidor

- Certificado HTTPS válido, `/app/login` accesible y configuración DNS completa.
- Administrador confirmado, 8 etiquetas, 11 respuestas rápidas, 7 atributos de ventas y equipo `ventas softmobile`.
- No hay bandejas de Messenger, Instagram ni WhatsApp configuradas.
- No hay ninguna credencial de aplicaciones Meta (`FB_APP_ID`, `INSTAGRAM_APP_ID` y afines) configurada en el servicio Chatwoot.
- La ruta `/webhooks/whatsapp/<phone>` existe (sin un canal válido, una verificación dará error de autorización: esto **no significa que la integración esté conectada**).
- No se han activado automatizaciones que envíen mensajes.

## Configurar WhatsApp: flujo manual para autohospedado

**Nunca pegar los tokens privados en un chat ni subirlos a GitHub.** Introducirlos directamente en el formulario HTTPS de Chatwoot.

1. Iniciar sesión con el administrador en https://chat.invjear.com.
2. Ir a **Configuración > Bandejas de entrada > Añadir bandeja de entrada > WhatsApp > WhatsApp Cloud > Configuración manual**.
3. Entrar a https://developers.facebook.com/apps y crear/seleccionar una aplicación vinculada al negocio, con el caso de uso **WhatsApp**.
4. En **Configuración de API** de WhatsApp dentro de Meta, agregar/verificar el teléfono comercial. Obtener el **ID del número de teléfono** y el **ID de la cuenta de WhatsApp Business (WABA)**. Son datos diferentes.
5. En Meta Business Settings > Usuarios > Usuarios del sistema, asignar al usuario de sistema los activos correspondientes y crear un **token permanente** con los permisos `whatsapp_business_messaging` y `whatsapp_business_management`. Guardarlo en un gestor de secretos; **no** compartirlo en este chat.
6. Pegar ambos IDs y el token directamente en Chatwoot, seguir la validación, nombrar la bandeja `SoftMobile WhatsApp Ventas`, y verificar los cuatro indicadores: acceso al número, acceso a plantillas, callback y suscripción de webhook.
7. Asignar a la bandeja los agentes del equipo `ventas softmobile`.
8. Enviar un mensaje desde **otro teléfono** al número empresarial. Validar recepción y una respuesta enviada por un agente; comprobar estado de entrega, no solo registro local.
9. Habilitar reglas comerciales específicas únicamente para esa bandeja y después de verificar contenido y horarios. La regla de ejemplo está **desactivada**.

**Limitación:** La configuración manual no mantiene el uso simultáneo de la app WhatsApp Business con el mismo número. Antes de registrar un número en la Cloud API, asegurarse de que no está activo en la app.

## Conexiones posteriores

- Messenger requiere una aplicación de Meta para Chatwoot autohospedado, permisos apropiados sobre la página y callback/webhook comprobados. No se configura solo porque el usuario tenga Facebook o una cuenta publicitaria.
- Instagram Business Login requiere una cuenta profesional y su propia configuración de aplicación Meta/Instagram para Chatwoot autohospedado. No mezclar acceso de WhatsApp con Instagram.
- Los chats, mensajes y permisos reales deben probarse antes de declarar producción lista.

## Fuentes oficiales

- Chatwoot: https://app.chatwoot.com/hc/user-guide/articles/1784258744-como-configurar-un-canal-de-whats_app-flujo-manual
- Meta Developers: https://developers.facebook.com/apps
- Meta Business Settings: https://business.facebook.com/settings

## Mediciones del embudo

Las conversaciones recibidas por WhatsApp deben etiquetarse con modelo, presupuesto, ciudad y etapa. Medir: consultas nuevas, consultas calificadas, cotizaciones, reservas confirmadas, ventas y costo publicitario por venta. No anunciar precio/stock con IA hasta tener un inventario autenticado en tiempo real.
