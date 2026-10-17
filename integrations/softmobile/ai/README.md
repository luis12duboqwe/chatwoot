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
