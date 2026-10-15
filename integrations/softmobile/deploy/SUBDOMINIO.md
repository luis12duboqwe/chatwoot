# Subdominio de Chatwoot: chat.invjear.com

## Estado verificado: 2026-10-15

- Host actual del inventario: `invjear.com`
- Servidores de nombres: `helios.dns-parking.com`, `aster.dns-parking.com` (Hostinger)
- IPv4 pública del VPS: `2.24.88.110`
- `invjear.com` y `www.invjear.com` ya usan esa dirección.
- `chat.invjear.com`: **registro A no publicado** en los servidores autoritativos a la hora de la revisión.
- Virtual host HTTP de `chat.invjear.com` creado en `/etc/nginx/sites-available/chat.invjear.com` y habilitado.
- Solicitudes HTTP a la raíz del nuevo subdominio devuelven 503 por seguridad; los retos ACME de `/.well-known/acme-challenge/` devuelven 200.
- `/health` de Chatwoot devuelve HTTP 200 en la dirección privada `127.0.0.1:3100`.
- La web y API de inventario siguen funcionando sin cambios.
- El certificado de `invjear.com` solo incluye `invjear.com` y `www.invjear.com`, **no** cubre el nuevo subdominio.

## Único registro DNS que falta

Agregar en Hostinger hPanel, sin editar registros de inventario:

| Campo | Valor |
| --- | --- |
| Dominio | invjear.com |
| Tipo | A |
| Nombre / Host | chat |
| Apunta a | 2.24.88.110 |
| TTL | Predeterminado |

Ruta de Hostinger (puede variar según el plan): **Dominios > Portafolio de dominios > Administrar invjear.com > DNS / Nameservers > Registros DNS**. Si está asociado a un alojamiento web, usar **Sitios web > sitio > Avanzado > Editor de zona DNS**.

No reemplazar la zona DNS completa, no alterar `@`, `www`, MX, SPF ni registros existentes.

Documentación del proveedor: https://www.hostinger.com/es/support/4468886-como-administrar-registros-a-en-hpanel-hostinger/

## Pasos posteriores (solo cuando el A ya sea visible)

1. Verificar `dig @helios.dns-parking.com +short chat.invjear.com A`; debe devolver `2.24.88.110`.
2. Ejecutar Certbot usando `--webroot -w /var/www/letsencrypt -d chat.invjear.com` y una cuenta de notificación HTTPS válida. No intentar emitir antes de configurar DNS.
3. Confirmar `/etc/letsencrypt/live/chat.invjear.com/fullchain.pem` y `privkey.pem`; comprobar que existe también `/etc/letsencrypt/ssl-dhparams.pem`.
4. Copiar `nginx-https.conf.example` al vhost nuevo (guardar un respaldo previo), ejecutar `nginx -t`; aplicar `systemctl reload nginx` solo si pasa. Mantener intacto `/etc/nginx/sites-available/invjear.com`.
5. En `/opt/chatwoot-softmobile/.env`, cambiar solo `FRONTEND_URL=https://chat.invjear.com` y `FORCE_SSL=true`, conservar todas las claves y secretos ya generados.
6. `cd /opt/chatwoot-softmobile && docker compose up -d --force-recreate rails sidekiq`.
7. Verificar con `curl -I https://chat.invjear.com/health`, navegador, certificados, WebSocket, login, y estado del inventario.
8. Dar de alta un administrador por un flujo seguro y posteriormente configurar bandejas y el embudo comercial.

Hasta completar estos pasos, **no afirmar que el sitio público está operativo**.
