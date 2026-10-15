# SoftMobile — MVP de ventas en Chatwoot

Esta integración **no modifica el núcleo de Chatwoot**. Prepara un embudo comercial para atender rápidamente consultas procedentes de anuncios y redes sociales. Usa la API existente de Chatwoot y solo la biblioteca estándar de Python.

## Qué incluye

- 8 etiquetas para oportunidades: interesado, cotizado, seguimiento, visita, reserva, vendido, sin stock y descartado.
- 11 respuestas rápidas en español para calificar compradores, consultar precios, pagos, ubicaciones y cierre.
- 7 atributos de conversación: modelo, presupuesto, ciudad, pago, etapa, origen y siguiente acción.
- 1 automatización **inactiva** que, una vez revisada para las bandejas correctas, puede etiquetar conversaciones nuevas. No envía mensajes automáticos.

Ningún texto promete existencias, financiamiento aprobado, garantías concretas, precios o entregas sin comprobar.

## Uso

Se ejecuta desde `integrations/softmobile`, con Python 3.10+.

```bash
python3 bootstrap.py --plan
python3 -m unittest -v test_bootstrap.py
```

Para consultar una instalación existente (solo lectura), configurar estas variables **en el servidor o terminal privado**, nunca en Git:

```bash
export CHATWOOT_URL="https://tu-chatwoot.example"
export CHATWOOT_ACCOUNT_ID="1"
export CHATWOOT_API_TOKEN="TOKEN_PERSONAL_DE_UN_ADMINISTRADOR"
python3 bootstrap.py --check
```

Para crear recursos faltantes, **después de revisar el plan**:

```bash
python3 bootstrap.py --apply
python3 bootstrap.py --check
```

- `--plan`: sin red, sin credenciales y sin cambios.
- `--check`: lee recursos; devuelve código 2 si hay faltantes o divergencias.
- `--apply`: crea solo faltantes; NO actualiza ni elimina recursos preexistentes.
- Los scripts son repetibles: un segundo `--apply` no debe crear duplicados.
- Una respuesta HTTP 401/403 indica permisos insuficientes o función de API deshabilitada.
- El token de API debe corresponder a un **usuario**, no a un token de bot, y debe tener permisos en la cuenta.
- El cliente exige HTTPS fuera de localhost para no transmitir el token por HTTP.
- La API de Chatwoot **no admite transacciones multirrecurso** en estas rutas: si un recurso falla a mitad, los ya creados permanecen; repetir `--apply` crea únicamente los restantes.

## Flujo comercial prioritario

1. Un anuncio en Meta abre una conversación de Messenger, Instagram o WhatsApp **solo después de conectar los canales mediante los procedimientos oficiales y sus permisos**.
2. Un vendedor identifica modelo, presupuesto, ciudad y forma de pago; usa `/sm_inicio` y `/sm_presupuesto` para acelerar la respuesta.
3. El vendedor verifica inventario/precio/estado del equipo en la fuente autorizada **antes** de compartir una oferta. Marca `sm_cotizado`.
4. Si el comprador necesita atención posterior, marca `sm_seguimiento` y registra la siguiente acción. Contactar solamente cuando corresponda y según el consentimiento y la ventana de mensajería del canal.
5. Cuando el cliente confirma interés real, se comprueba existencia en el punto aliado; `sm_visita` o `sm_reserva` NO implica que el equipo esté apartado.
6. Se usa `sm_vendido` únicamente al confirmar la venta; anotar margen y costo publicitario en un registro financiero aparte.

**Estados operativos sugeridos:** Nuevo → Calificado → Cotizado → Negociación → Reserva pendiente → Vendido o Descartado.

## Reglas para ponerlo en producción

- No activar la automatización borrador hasta confirmar que solo afecta las bandejas de SoftMobile y probar el flujo con una conversación de prueba.
- No integrar campañas masivas ni seguimiento fuera de las reglas de mensajería de Meta/WhatsApp.
- No activar una IA que invente precios, stock, accesorios, garantía ni condiciones bancarias.
- Confirmar si una integración de WhatsApp usa Meta Cloud API, el proveedor oficial disponible o un canal compatible; las credenciales y verificaciones se hacen fuera del repositorio.
- La integración con inventario real se realizará a través de una API autenticada. Hasta entonces, un vendedor validará disponibilidad.
- Nunca guardar claves de Meta, WhatsApp, Chatwoot ni datos de clientes en GitHub.

## Indicadores de ventas para la primera campaña

Medir por día: conversaciones recibidas, conversaciones calificadas, cotizaciones enviadas, visitas coordinadas, ventas confirmadas, gasto de anuncios y margen obtenido. La métrica para evaluar publicidad es el **costo por venta confirmada**, no solo el número de mensajes.

## Compatibilidad técnica

Comprobado contra los controladores de la rama `develop` (15 de octubre de 2026):
- `GET/POST /api/v1/accounts/:account_id/labels` (el listado usa `payload`).
- `GET/POST /api/v1/accounts/:account_id/canned_responses` (listado como arreglo).
- `GET/POST /api/v1/accounts/:account_id/custom_attribute_definitions` (arreglo).
- `GET/POST /api/v1/accounts/:account_id/automation_rules` (`payload`, acciones y condiciones a nivel raíz).

Es un **primer entregable de código**. Crear archivos y superar pruebas unitarias no demuestra que esté desplegado ni que Facebook, Instagram, WhatsApp o el VPS estén conectados.
