# Chatwoot en chat.invjear.com — estado del despliegue

Comprobado el 15 de octubre de 2026 en el VPS `srv1656045`.

## Preparación finalizada

- DNS de Hostinger: `chat.invjear.com` tiene un registro A autoritativo hacia `2.24.88.110` con TTL de 14400 segundos.
- Certificado TLS de Let's Encrypt emitido para `chat.invjear.com`; válido hasta 2027-01-13.
- Simulación de renovación con Certbot: **correcta**. Timer de Certbot habilitado y deploy hook para recargar Nginx al renovar.
- Nginx: vhost independiente para el nuevo subdominio con HTTPS, redirección HTTP -> HTTPS y proxy a `127.0.0.1:3100`.
- Chatwoot: `FRONTEND_URL=https://chat.invjear.com`, `FORCE_SSL=true`, `ENABLE_ACCOUNT_SIGNUP=false`.
- Rails, Sidekiq, PostgreSQL y Redis de Chatwoot levantados; puerto 3100 expuesto solo en localhost.
- `https://chat.invjear.com/health`: HTTP 200 con certificado validado **antes** de instalar autenticación temporal de onboarding.
- `https://invjear.com/health`: HTTP 200, inventario sin cambios.

## Protección temporal del onboarding

Como todavía no hay cuenta administradora, el sitio HTTPS está protegido por HTTP Basic Auth en el vhost de Nginx para impedir que un tercero se registre como primer administrador. **Nunca guardar el nombre de usuario ni contraseña temporal en GitHub**. Los secretos están gestionados únicamente en el servidor y se entregan al propietario de manera temporal.

- Usuario autorizado: propietario del negocio; crear cuenta propia en el asistente de Chatwoot.
- La credencial de Basic Auth **NO** es la contraseña permanente del administrador.
- Al terminar el registro y verificar un login real, retirar `auth_basic` y `auth_basic_user_file` del bloque HTTPS, comprobar con `nginx -t`, y recargar Nginx.
- Dejar `ENABLE_ACCOUNT_SIGNUP=false` para prevenir altas no autorizadas, salvo que un flujo documentado requiera un cambio temporal y controlado.
- No mostrar credenciales personales ni API tokens en logs, commits o mensajes operativos.


### Incidencia Nginx 500 corregida

El archivo `/etc/nginx/.softmobile-onboarding.htpasswd` se creó inicialmente con permisos `0600 root:root`, provocando respuestas HTTP 500 porque los trabajadores Nginx (`www-data`) no podían leerlo (`Permission denied` en `/var/log/nginx/error.log`). Se corrigió a **`0640 root:www-data`** y se verificó lectura con `runuser -u www-data -- test -r ...`. La respuesta esperada sin credenciales ahora es **HTTP 401** (desafío Basic Auth), no 500; el inventario permaneció en HTTP 200.

Para instalaciones posteriores, usar `chown root:www-data /etc/nginx/.softmobile-onboarding.htpasswd` y `chmod 0640 /etc/nginx/.softmobile-onboarding.htpasswd`. Nunca usar `chmod 644` ni almacenar una contraseña sin hash en el repositorio.

## Próximo paso de ventas

1. Crear primera cuenta de administrador desde el asistente web en HTTPS, bajo la protección temporal.
2. Comprobar cuenta e identificar ID de la cuenta de SoftMobile.
3. Aplicar 8 etiquetas, 11 respuestas rápidas, 7 atributos y 1 regla inicialmente desactivada de `integrations/softmobile/manifest.json`.
4. Validar en la interfaz los 27 registros y probar su idempotencia.
5. Conectar oficialmente las bandejas Meta/WhatsApp/Instagram; probar mensajes entrantes y salientes.
6. Integrar inventario/precios validados antes de automatizar cotizaciones, reservas y promesas de entrega.

No activar automatizaciones de envío sin confirmar primero los canales y las restricciones de mensajería.
