# SoftMobile: piloto de IA gratuita con Groq (NO ACTIVADO)

Este módulo produce **sugerencias internas**, no respuestas públicas. No tiene ninguna
función para escribir en Chatwoot, WAHA, ERP ni WhatsApp. Conserva el motor de reglas actual.
La prueba solo permite conversación Chatwoot #3; otras conversaciones se rechazan.

## Estado actual
- Python 3.12; sin dependencias de terceros ni n8n.
- 11 pruebas unitarias offline aprobadas (17-10-2026).
- Sin credencial Groq; no se realizaron llamadas externas al proveedor.
- Feature flag `SOFTMOBILE_AI_ENABLED` apagado por defecto.
- Contrato de salida JSON estricto de Groq; validador de tipos y escalación.
- Redacción básica de datos personales; **NO** sustituye anonimización rigurosa.
- Datos comerciales no verificados: siempre revisión humana y sin envío automático.

## Ejecución de desarrollo (sin gastar tokens)
Desde este directorio:

```bash
python3 -m unittest -v test_groq_pilot
printf '%s\n' '{"conversation_id":3,"message":"Busco iPhone 13 Pro Max 256 GB"}' | python3 groq_pilot.py
```

## Integración externa (cuando exista una clave en el VPS)
Crear una clave de Groq en https://console.groq.com/keys.
No pegarla en ChatGPT, archivos públicos, logs ni GitHub.
Guardarla como `GROQ_API_KEY` en una ubicación privada con acceso restringido (0600).
Habilitar `SOFTMOBILE_AI_ENABLED=true` SOLO para ejecutar explícitamente
`python3 groq_pilot.py --live` con entradas ficticias o suficientemente anonimizadas.

Ejemplo de llamada *manual* (solo después de configurar la clave y revisar privacidad):

```bash
printf '%s\n' '{"conversation_id":3,"message":"Quiero Samsung S22 Ultra de 256 GB negro"}' | python3 groq_pilot.py --live
```

Esto únicamente imprime una propuesta JSON; no escribe ni envía a clientes.

## Próximas etapas separadas
1. Validar la API gratuita en modo privado con preguntas ficticias.
2. Comparar propuestas frente al corpus de pruebas del bot existente.
3. Guardar fallos **anonimizados** y aplicar mejoras solo si las pruebas pasan.
4. Integrar con Chatwoot mediante una compuerta con idempotencia y aprobación
   humana, inicialmente solo conversación #3.
5. Conectar catálogo oficial de aliados verificable antes de cotizaciones reales.
6. Elegir proveedor de pago si la calidad y el volumen lo justifican.

**No se autoriza** activación global, seguimiento automático, descuentos,
reservas, precios definitivos, cobros, fotografías ni promociones masivas.

## Instalación segura de la clave en el VPS (sin revelar el token en el chat)
El dueño entra al Terminal SSH de Hostinger y ejecuta:
```bash
sudo python3 /opt/softmobile-waha-test/laboratorio-ia/configurar_clave_groq.py
```
El instalador pide la clave con entrada oculta, valida el formato y la guarda solo
en `/etc/softmobile/groq.env` con permisos 0600 (carpeta 0700).
Luego prueba la conexión con un mensaje ficticio y muestra una sugerencia
solo interna. Si no puede conectar, conserva el bot actual sin cambios.
Nunca pegar la clave en ChatGPT, GitHub, la línea de comandos ni en archivos públicos.

## Integración activa: sugerencias privadas dentro de Chatwoot (17 oct 2026)
Archivo: `chatwoot_ai_bridge.py`. Se instaló el servicio/timer de referencia en
`/etc/systemd/system/softmobile-groq-pilot.{service,timer}`.
Esta integración NO forma parte del motor Ruby original ni modifica sus respuestas públicas.

### Límites fijos
- Cuenta 2, bandeja 2, conversación piloto 3 solamente; comprobación doble en Rails.
- Lee mensajes entrantes nuevos posteriores al cursor inicial, jamás históricos.
- No envía mensajes a clientes. Solo crea notas de Chatwoot con `private:true` y
  marcador de idempotencia `[SMAI:<ID>]`.
- Si hay multimedia, texto vacío, datos personales detectados o API fallida,
  no hace envíos. El filtro de datos sensibles es básico: no habilitar a clientes reales
  hasta terminar evaluación de privacidad.
- Máximo 30 solicitudes diarias al proveedor y una por ejecución.
- Guardado del cursor local en `.pilot_bridge_state.json` (0600, no subir a GitHub).
- El proveedor puede generar sugerencias incorrectas: un vendedor debe verificarlas,
  especialmente precios, existencias, garantías, envíos, financiación y reservas.

### Comprobaciones del VPS
```bash
cd /opt/softmobile-waha-test/laboratorio-ia
python3 -m unittest -v test_groq_pilot test_configurar_clave_groq test_chatwoot_ai_bridge
systemctl status softmobile-groq-pilot.timer --no-pager
journalctl -u softmobile-groq-pilot.service -n 30 --no-pager
```

### Suspender inmediatamente sin afectar el bot comercial
```bash
sudo systemctl disable --now softmobile-groq-pilot.timer
```

### Reanudar exclusivamente después de revisar
```bash
sudo systemctl enable --now softmobile-groq-pilot.timer
```
Para una revisión puntual del piloto:
```bash
sudo systemctl start softmobile-groq-pilot.service
```

### Auditoría real
Se verificó en Chatwoot un mensaje de laboratorio
`[SMAI:DEMO-1]`: una única nota guardada, `private=true`, `outgoing`.
Una segunda escritura devolvió `duplicate` sin crear otra nota.
Se detectó y corrigió un problema de ordenación heredada del modelo Chatwoot:
la fuente usa `maximum(:id)` para inicializar y `reorder(id: :asc)` para nuevas entradas.
El cursor fue migrado al máximo de mensajes entrantes existentes y una ejecución real
posterior devolvió `no_new_messages`. Las respuestas públicas continúan en el motor Ruby.

Importante: el análisis automático de calidad/aprendizaje continuo todavía es una etapa
posterior. Este servicio es el puente de sugerencias internas, no un editor autónomo del bot.

## Auditoría automática y propuestas de mejora (17 oct 2026)
Archivos: `quality_auditor.py`, `test_quality_auditor.py`, y
`quality_payment_delivery.patch` en `patches/`.

### Ciclo implementado
1. Leer respuestas públicas del bot con marca de origen, exclusivamente de Chatwoot
   cuenta 2, bandeja 2, conversación 3, sin escribir ni enviar mensajes.
2. Emparejar cada respuesta con el mensaje entrante exacto; conservar un cursor
   para evaluar **solo las respuestas nuevas** en posteriores ejecuciones.
3. Identificar repeticiones, elecciones de pago ignoradas, ambigüedad entre retiro
   y envío, y afirmaciones comerciales no verificadas.
4. Omitir mensajes con números, emails, direcciones y otros identificadores
   detectados por los filtros locales. No enviar notas internas, nombres ni logs.
5. Enviar como máximo 3 casos relevantes y anonimizados a Groq por ejecución
   (límite del auditor: 12 consultas/día). La IA propone correcciones, pero no
   controla escrituras a Chatwoot, códigos, precios, reservas ni pagos.
6. Validar el formato y prohibiciones básicas de las propuestas; guardar
   hallazgos en `quality/findings.json` (permisos 0600, directorio restringido).
7. Crear borradores de casos de regresión con estado
   `pending_human_review`, no autorizar automáticamente despliegues.
8. Ejecutar revisión cada hora con `softmobile-quality-audit.timer`.
   Rotación: máximo 250 hallazgos, con antigüedad máxima de 30 días.

Las pruebas de Python no garantizan que un modelo nunca genere una mala propuesta.
No debe habilitarse el aprendizaje autónomo sobre código de producción sin
control de calidad, aprobación y capacidad de reversión.

### Prueba de despliegue y corrección concreta
- Se analizaron 33 respuestas reales del bot piloto y se identificaron
  11 alertas candidatas (9 repeticiones, 1 pago, 1 ambigüedad de entrega).
- Groq realizó tres valoraciones en la primera ejecución. Se conserva
  un juicio humano obligatorio antes de aprobar cambios.
- Se aplicaron manualmente, tras pruebas, dos correcciones delimitadas:
  reconocer 'Efectivo' como elección y aclarar 'Galerías' tras solicitud de envío.
- El motor Ruby superó 57/57 pruebas y 5/5 nuevas regresiones sobre la versión
  candidata antes de desplegarse. Backup local en directorio restringido
  `/opt/softmobile-waha-test/quality-backups`.
- El sistema de IA **no** escribió ni desplegó código por sí mismo.
- El fichero `quality/findings.json` contiene únicamente registros del piloto;
  no debe subirse a GitHub ni adjuntarse a informes públicos.

### Consultar estado sin repetir manualmente pruebas
```bash
python3 /opt/softmobile-waha-test/laboratorio-ia/quality_auditor.py --summary
systemctl status softmobile-quality-audit.timer --no-pager
journalctl -u softmobile-quality-audit.service -n 15 --no-pager
```

### Parar solamente la auditoría (bot y Groq piloto siguen funcionando)
```bash
sudo systemctl disable --now softmobile-quality-audit.timer
```
