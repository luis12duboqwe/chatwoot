# Despliegue aislado de Chatwoot para SoftMobile

## Estado validado — 15 de octubre de 2026

Instalación de prueba ejecutada en el VPS `srv1656045`, Ubuntu 24.04 LTS, Docker 29.1.3, Compose 2.40.3.

- Código y pruebas del configurador: `integrations/softmobile`.
- Imagen fijada: `chatwoot/chatwoot:v4.18.0-ce`.
- Proyecto Docker: `softmobile-chatwoot`.
- Puerto exclusivamente local: `127.0.0.1:3100`.
- Persistencia separada: volúmenes PostgreSQL, Redis y almacenamiento de Chatwoot.
- PostgreSQL del ERP y Nginx existentes: **no se sustituyen**.
- Comprobaciones iniciales de `/api` y `/health`: HTTP 200.
- Al comenzar, ninguna cuenta administrativa ni bandeja estaba creada.

### Reconstrucción

1. En el servidor, instalar Docker Engine y Docker Compose según el método oficial.
2. Crear un directorio privado con permiso `0700` y copiar `compose.yaml` y el ejemplo `.env.example` como `.env`.
3. Sustituir **todos** los valores `GENERATE_RANDOM_...` de `.env` con secretos independientes generados localmente (`openssl rand -hex 64` para `SECRET_KEY_BASE`; `openssl rand -hex 32` para claves de cifrado, PostgreSQL y Redis).
4. Restringir permisos con `chmod 600 .env`. No subir secretos al repositorio.
5. Ejecutar `docker compose config --quiet`, `docker compose pull`, `docker compose up -d postgres redis` y `docker compose run --rm rails bundle exec rails db:chatwoot_prepare`.
6. Arrancar con `docker compose up -d rails sidekiq`, comprobar `curl -fsS http://127.0.0.1:3100/health`.

### Pendiente para acceso público

- Confirmar el dominio/subdominio dedicado y configurar su registro A/AAAA hacia la IP pública del VPS.
- Crear un bloque **independiente** de Nginx para ese hostname, con proxy a `127.0.0.1:3100`, y obtener certificado HTTPS.
- Cambiar `FRONTEND_URL` a la URL pública con HTTPS, activar `FORCE_SSL=true`, recrear Rails/Sidekiq y volver a comprobar.
- Habilitar temporalmente altas **solo durante el alta del administrador en HTTPS** si el flujo de primera cuenta las requiere; después deshabilitarlas.
- Configurar correctamente SMTP y cifrado antes de depender de restablecimientos de contraseña, invitaciones y notificaciones.
- Aplicar los recursos de `../bootstrap.py` mediante una credencial API del administrador, y comprobarlos desde la interfaz.
- Conectar canales oficiales WhatsApp/Messenger/Instagram con permisos de Meta; probar un mensaje entrante y uno saliente en cada canal antes de automatizar.
- Conectar inventario/precios verificados mediante API autenticada; nunca garantizar stock automáticamente sin esa fuente.

### Comandos seguros

```bash
cd /opt/chatwoot-softmobile
docker compose ps
docker compose logs --tail 50 rails sidekiq
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:3100/health
```

**Importante:** no publicar el puerto 3100 en `0.0.0.0`, ni activar el ejemplo de Nginx o SSL antes de preparar el DNS y validar el dominio. No correr `docker compose down -v`: eliminaría las bases de datos de Chatwoot.
