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

## Mejora automática CONTROLADA en la fase piloto (17 oct 2026)
`auto_improver.py` se ejecuta cada hora a los :20, después del auditor de calidad
que corre a los :00. El mecanismo no es simplemente una alerta; aprende reglas
preaprobadas de fallos detectados por la auditoría, ejecuta pruebas de Ruby
y las incorpora automáticamente al bot que atiende **solo la conversación #3**.

### Recorrido sin intervención humana para errores soportados
1. El auditor marca fallos repetidos y los pone en `quality/findings.json`.
2. El mejorador local lee esos hallazgos y propone una **regla de una lista finita
   de patrones permitidos**. Nunca ejecuta código proporcionado por Groq o clientes.
3. Genera un cambio de datos con condiciones exactas (frase, intención, contexto).
4. Verifica 57 pruebas originales y 5 regresiones de la atención comercial,
   más escenarios particulares de la nueva regla. Si falla, **no despliega**.
5. Si pasa, pausa el temporizador del bot, espera que el servicio termine, hace
   una copia local de su código, lo reemplaza atómicamente y vuelve a probar.
   Si la prueba posterior falla, revierte a la copia anterior.
6. Actualiza el paquete de reglas activas y el registro de auditoría; reanuda bot.
7. Limita automáticamente a 2 despliegues de automejoras por día, hasta 8 reglas
   activas permitidas en esta primera fase. Los defectos no cubiertos por la
   lista continúan registrados pero NO se corrigen solos.

### Resultado real
- El sistema tomó un caso de respuesta incorrecta a `Transferencias`, lo convirtió
  automáticamente en una regla para reconocer la elección de pago, y la instaló en
  el piloto tras pasar 57 pruebas del motor, 5 regresiones y una simulación de
  interacción específica. Copia segura en `quality-backups/`.
- Los temporizadores activos siguen: bot comercial, notas Groq, auditor por hora,
  y mejorador por hora a los :20.
- La clave Groq sigue fuera de GitHub. Ni los mensajes privados, el historial
  detallado de clientes ni `quality/findings.json` se suben al repositorio.
- Los cambios se versionan en GitHub mediante PR de desarrollo. El proceso local
  autónomo **todavía no publica commits futuros a GitHub por sí mismo**.

### Ver resultados y reversiones
```bash
python3 /opt/softmobile-waha-test/laboratorio-ia/auto_improver.py --status
systemctl list-timers softmobile-auto-improver.timer --no-pager
journalctl -u softmobile-auto-improver.service -n 25 --no-pager
```

Para suspender automejoras sin detener el bot:
```bash
sudo systemctl disable --now softmobile-auto-improver.timer
```

## Validación de conversaciones históricas y corrección de cursor (17 oct 2026)
- Incorporadas 7 conversaciones simuladas a `quality/test_historical_replay.rb`,
  tomadas de las fallas históricas detectadas en el piloto. Cubren:
  Villanueva, confirmación de retiro («Pasaré por él», «Retirarlo», «Paso»),
  petición «No entiendo» y pregunta de precio después de una derivación.
- Tanto `quality_auditor.test_gate()` como `auto_improver.gates()`
  ejecutan ahora las 57 pruebas originales, 5 de regresión comercial
  y **7 reproducciones históricas**; si alguna falla, el autoparche no se instala.
- El auditor corrigió el cursor de paginación: procesa hasta 60 respuestas
  por lote y guarda el ID de la última del lote, sin saltarse las posteriores.
- Las 7 alertas históricas fueron reclasificadas como
  `regression_passed_pending_live_test`, y las otras 4 como
  `fix_deployed_pending_live_test`. **Ninguna es evidencia de prueba real
  por WhatsApp**, la verificación final requiere una conversación nueva.
- 56 pruebas Python locales superadas tras estas mejoras.

## Verificación reforzada del piloto — 17 octubre 2026

- Chatwoot público verificó HTTP 200.
- WAHA respondió HTTP 200 a su endpoint autenticado y su sesión tiene estado
  `WORKING`. El endpoint sin credenciales devuelve HTTP 401 (esperado).
- Mensajes históricos de Chatwoot: 40 salientes públicos, todos con estado
  `sent`. **Esto no prueba entrega efectiva ni lectura en el teléfono.**
  No se enviaron nuevos mensajes a números externos para esta comprobación.
- Se añadieron veinte recorridos completos simulados de clientes:
  selección de modelo y capacidad, cambios de variante, equipo existente vs.
  solicitado, consultas múltiples, stock, precio, elección de efectivo o
  transferencia, tarjeta, bancos, retiro vs. envío, cambios de entrega,
  consulta tras derivación, garantía, fotografías, datos sensibles y cancelación.
- Tanto el auditor como el mejorador exigen pasar ahora cuatro barreras antes
  de cualquier autocorrección: 57 tests Ruby base, 5 comerciales, 7
  conversaciones históricas y **20 recorridos de cliente nuevos**.
- Se afinó la detección de `exact_repeat` para no alertar por un simple
  agradecimiento, saludo, confirmación ni una pregunta idéntica repetida.
- La suite Python de integraciones y seguridad pasó 57/57 pruebas.

**Pendiente físico real:** verificar una conversación nueva desde el teléfono
piloto hasta el acuse/entrega WhatsApp. Los estados `sent` y los replays Rails
no deben citarse como `delivered`. No habilitar la integración en otras bandejas.

**Inventario de aliados:** aún no hay fuente oficial y autorizada con SKU, precio
y disponibilidad; se siguen bloqueando las cotizaciones automáticas.

## Pilot autonomous quality and transport monitoring — 17 October 2026

Additional read-only monitor:
- `pilot_transport_monitor.py` runs every ten minutes via
  `softmobile-pilot-transport.timer`; it checks Chatwoot #3 and authenticated
  WAHA session state, but **never sends WhatsApp messages**, reveals credentials
  or claims that `sent` means physically delivered.
- The latest inbound message category is classified *inside Rails*, without
  copying the buyer's raw text. Short acknowledgments need no extra public bot reply.
- The observer records metadata in `quality/e2e-transport.json` (permissions 0600).
  An older inbound without a corresponding bot or human reply is marked
  `unanswered_inbound_needs_review`, not automatically interpreted as a bug.

Broader automatic issue detection:
- Explicit payment choices not acknowledged (`payment_choice_ignored`).
- Explicit color and capacity corrections which the reply failed to respect.
- `payment_choice_ignored` may enter the bounded autofix catalog only for
  exact approved expressions and checkout context. Groq cannot inject Ruby.

Private quality-score snapshots:
- The auditor calculates a heuristic **regression signal** (0–100) for new
  non-sensitive bot messages, using conservative weighted issue detections.
- Saved as metadata-only in `quality/quality-score-history.json` with an initial
  historical baseline separate from later new responses.
- Initial baseline: 32 of 33 historical bot replies eligible for analysis;
  score 91.4/100, 10 candidates with rule-based alerts.
  **It is NOT a validated sales conversion or actual quality percentage.**
- The signal will enable tracking whether new batches show more or fewer
  suspicious patterns; no change is automatically deemed an improvement solely
  because a score increases.

As of this update: 72/72 Python tests passed; prior 57+5+7+20
Ruby regression gates passed. All five pilot timers active.
The only remaining real transport limitation is that no new WhatsApp handset
receipt has been confirmed in this session.


## New pilot buyer test and verified patches (2026-10-17 22:08-22:13 UTC)

The buyer asked for an iPhone 16 Pro with 256GB, titanium finish then gold,
delivery in Comayagua, gave an address landmark, and answered "Si".

Faults confirmed in original Chatwoot replies:
1. Titanium preference was ignored; the bot asked color again.
2. A shipping landmark was not acknowledged; bot reverted to a generic recap.
3. Affirmative "Si" repeated the previous summary.
4. The first issue independently triggered an exact-repeat audit flag.

Pilot fixes: accept generic titanium and ask the tone without claiming stock;
acknowledge delivery landmarks without echoing the private location or promising
shipping coverage; clarify an ambiguous payment answer or stay silent after
a completed handoff rather than repeating the summary.

Security: only pilot Chatwoot conversation #3. No public AI message send;
no automated price, stock, bank approval, reserve or shipping confirmation.
Original customer landmark is not included in GitHub test cases.

Verification:
- 57 existing Ruby tests, 5 commercial regressions, 7 historical replays,
  20 completed customer journeys, and 11 new buyer replay checks: all passed.
- 75 Python tests across AI bridge, quality auditor, bounded autofix,
  privacy filters and transport observer: all passed.
- Post-deployment verification passed; restricted rollback backup retained.
- New automated audit: 9 replies examined, 4 quality flags linked to the
  3 observed faults. Groq reviewed 3 sanitized samples; private QA note added.
- 15 historical audit flags: 8 deployed pending live retest, 7 historical
  regressions passed pending live retest, no unreviewed pending issue.
- All five systemd pilot timers active.

Address handling: delivery landmarks are stripped down to coarse category labels
before external AI review. This is best-effort redaction, not complete PII protection.

Next step: fresh customer messages in the already approved pilot WhatsApp chat
to independently verify transport receipt and corrected reply behavior.
Chatwoot sent status alone is not proof of physical WhatsApp delivery.


## Autonomous Groq synthetic conversation laboratory, 17 October 2026
Run synthetic_lab.py every 30 minutes with the softmobile-synthetic-lab.timer.
This is a **separate closed pilot**: account 2 / inbox 2 / conversation 3. No
customer messages are transmitted to the generator; Groq produces fictional
3-6 turn buyer dialogues across changing product variants, delivery, payment,
objections, cancellation, financing and safety. The deployed Ruby bot runs each
dialogue in an **isolated memory-only Rails runner**; no Chatwoot writes occur.
Groq then separately grades the responses in structured JSON and proposes
a safer answer and reproducible behavioral expectation.

User messaging and live traffic remain controlled by the Ruby bot, not by the
Groq API. No untrusted LLM Ruby source is evaluated or deployed.

Limits: maximum 4 fictional scenarios per run, up to 5 Groq calls per run and
160 Groq requests per UTC day from this laboratory, respecting provider 429s.
All other active Groq processes have separate, conservative budgets. Groq
free-usage limits are imposed by the provider; this configuration is not
evidence of unlimited free inference. Stops requesting on exhaustion.

Laboratory records are private root-mode JSON files in quality/:
  synthetic-lab-state.json       0600, request budget and counters
  synthetic-lab-issues.json      0600, synthetic-only simulated evidence
  synthetic-lab-summary.json     0600, per-run metadata and findings
  synthetic-lab.lock             0600, prevents parallel runs

Reliability: scenario validation rejects attempts to impersonate the seller,
actual personal identifiers, precise addresses, bank details, invented prices
and currencies. Grade validation independently rejects unsafe commercial
promises and suggestions. Invalid model-generated scenarios are discarded and
substituted with known-safe fictional fixtures. Findings are tentative until
the deterministic replay corroborates them; non-supported categories are
kept for review, never automatically published.

Bounded self-improvement integration: when a synthetic buyer selects
"Transferencia" after receiving the fixed payment menu, the deterministic
detector may propose the predefined safe transfer-choice reply via the
**existing** auto_improver.py. It does not trust an AI-generated response or
modify arbitrary code. The autofixer runs its full Ruby regression suites,
stores a rollback backup, atomically installs the exact rule in the single
pilot script, and then checks again. All other speculative findings remain
unverified. The derived payment-menu rule was autonomously installed,
after passing the previous 100 checks and specific replay. New persistent
regression test_synthetic_payment_menu.rb adds 2 more checks.

As of this step the root-owned lab has completed two real Groq cycles:
10 API requests total (4 synthetic dialogues each cycle).
It rejected four initially invalid model-generated scenarios; one
preapproved payment-menu correction was installed by the bounded autofixer.
No generated answer was sent to WhatsApp, and no actual stock, payment or
price confirmation was made.

To inspect:
  python3 /opt/softmobile-waha-test/laboratorio-ia/synthetic_lab.py --status
  journalctl -u softmobile-synthetic-lab.service -n 20 --no-pager
To disable AI-generated synthetic testing only:
  sudo systemctl disable --now softmobile-synthetic-lab.timer

## Autonomous audit-to-fix results — 17 October 2026

Five synthetic customer dialogue defects were reproduced in the previous pilot
Ruby bot, and five corresponding reply improvements were implemented in the
isolated candidate after independent scenario testing. Groq had offered unsafe
answers with unverified inventory, shipping estimates and refund promises;
those text proposals were explicitly rejected.

Safe fixed-response families installed:
- Personalized cases/accessories: acknowledge inquiry, verify whether offered,
  confirm price/compatibility with agent; no invented availability.
- Color preference changes: do not misclassify as hardware repair; distinguish
  preference from modifying an existing paid or shipped order.
- Delivery lead times: explain that timings need route/provider verification.
- Delivery damage: human escalation without automatic promises of refund,
  replacement or waiver of applicable legal rights.
- Sequential storage/color changes: acknowledge each update without repeating
  identical city requests on every message; keep missing city as open context.

Tests: 57 baseline Ruby tests + 5 commercial + 7 historical + 20 complete
journeys + 11 live pilot replays + 2 synthetic payment + 15 additional
future-scenario assertions = 117 checks, all passed pre-deployment and
post-deployment. Local Python tests initially 89/89.
Verified backup: sales-bot.autofix.20261017T230712Z.bak under quality-backups.
The pilot commercial bot and autofix timers were successfully restarted.

The synthetic lab now replays up to three previously unresolved fictional
dialogues per cycle against the new live Ruby engine, submits them to Groq
for an independent assessment, and compares new replies with stored earlier
replies. Groq retest calls count toward the lab's local 160 daily requests cap.
When a case has changed, no deterministic flags and AI reports no error, it
is marked 'retested_ai_clear_pending_deterministic_review'. This provisional
state is NOT proof of real customer quality and triggers no autonomous code
change. Unsupported findings remain open.

The user-facing WhatsApp pilot remains restricted to account 2, inbox 2,
conversation 3; no new phone messages are sent by this simulation lab.

## Groq interactive step-by-step customer pilot — 2026-10-17

Separate read-only automated lab added alongside the existing batch simulator.
The interactive Groq actor now creates **one** fictional customer message,
the deployed Ruby sales engine replies inside an isolated read-only Rails
runner, and Groq receives that exact bot reply before composing its next
customer message. The actor does not generate a whole dialogue upfront.

- 3 to 5 turn customer dialogues; persona rotates across ten different
  buyer concerns (device variants, shipping, payment, objection, financing,
  trust, warranty, checkout and cancellation).
- Every created customer message must pass the previous synthetic lab's
  strict fake-data, anti-vendor-imitation and privacy filters.
- A separate Groq call evaluates the completed dialogue with structured
  output, records what was good/bad and may suggest a better customer reply.
  The evaluation is explicitly advisory: suggestions that claim unverified
  terms are discarded, but the diagnostic can still be retained.
- The entire **fictional** transcript, AI evaluation and detected flags are
  saved root-only under quality/interactive-lab-transcripts.json. Only
  flagged cases enter the existing private synthetic-lab-issues.json queue.
  Existing bounded autofix rules can consider permitted payment-intent
  patterns, subject to mandatory tests/rollback; AI cannot execute code.
- Shared lock and same **combined** local 160 Groq API requests/day quota as
  the older batch scenario lab. The interactive session uses up to five
  customer-generation requests and one independent judge request.
- Additional systemd timer runs every half hour at :15 and :45 UTC;
  original scripted synthetic lab remains at :05 and :35 UTC. Services
  remain entirely scoped to Chatwoot account 2 / inbox 2 / conversation 3.
  The new lab itself sends **zero** Chatwoot / WAHA / WhatsApp messages.
- The first live Groq interactive test ran five turns and discovered a
  previously missed ambiguity as the customer changed iPhone 15 capacity
  and color several times. The independent Groq grader marked the
  discrepancy as a potential intent/context error. It is recorded for
  corroboration and **not deployed** as an arbitrary AI patch.
- 103 offline Python tests passed after initial activation; the existing
  Ruby conversation safety gates remain in place for any autofixer release.
- CI now includes the interactive module and its regression/security tests.

Read-only status:
  cd /opt/softmobile-waha-test/laboratorio-ia
  python3 interactive_lab.py --status

To stop ONLY this stepwise simulation process:
  systemctl disable --now softmobile-interactive-lab.timer

No provider-free-plan quota or approval of actual customer messaging is
guaranteed. The local cap protects the combined synthetic labs.

## AI-selected, staged and regression-gated pilot code-repair loop (2026-10-17)

The first repair generator is now implemented as repair_lab.py, with eight
systemd timers including softmobile-repair-lab.timer scheduled hourly at :55 UTC.
The new service *only* sees fictional synthetic_lab / interactive_lab findings;
no customer messages, secrets, account details, addresses or payments enter
the repair generator.

Pipeline:
1. Search unresolved fictional dialogues for one of two pre-reviewed behavior
   families (advisor_response_eta, shipping_tracking_followup).
2. Require an independent Groq structured-JSON selection of the issue type.
   No source code, arbitrary expressions, regular expressions, or executable
   suggestions from Groq are accepted.
3. Compile trusted fixed Ruby policy into a private staged candidate file
   (0600); no live bot code is changed at this step.
4. Replay the triggering 3-6-message customer journey against both actual
   pilot code and staged candidate. Reject if the targeted reply is unchanged,
   does not address the question, contains fabricated facts, lacks required
   human escalation, or introduces new deterministic regression flags.
5. Run the *entire* 117-case Ruby suite with the staged code. Only on all
   gates passing may repair_lab.py --run install the allowlisted candidate.
6. Atomically back up and replace only the pilot bot; rerun full Ruby suites
   after replacing it. Unexpected post-install exceptions also trigger atomic
   restoration of the previous source. Preserve existing timers.
7. Store private metadata + versioned source patch. Mark original synthetic
   issue 'fix_deployed_pending_synthetic_retest'; no production signoff until
   it passes a fresh test.

First real full cycle: selected advisor_eta from interactive trial
de90d42caef83f2141, staged it, verified candidate and replays, deployed it
with backup sales-bot.autofix.20261017T234314Z.bak and confirmed the modified
actual pilot handles an advisor response-time inquiry. No invented hour, stock
or payment; no WhatsApp messages were sent. 113 Python tests pass, including
an intentional gate exception testing atomic rollback. The 117 Ruby tests all
passed in pre-/post-deploy gates.

Controls:
- At most ONE AI-directed code repair deployed per UTC day, and only in the
  existing pilot account 2 / inbox 2 / conversation 3.
- The repair service shares exclusive locks with the existing safe auto-improver
  and both simulation labs. Contending on a lock skips that run safely.
- Both existing labs and repair selection share the local 160 API
  requests/day budget. Provider limits and free credits still apply.
- Only TWO authorized fix classes exist at this point. The system does *not*
  program itself arbitrarily, merge PRs or modify price, delivery, warranty,
  product stock, payments, external accounts, or inventory.
- New unsupported errors continue to be recorded for expanding the authorized
  correction catalog and verifying future fixes.

Inspection:
  python3 repair_lab.py --status
  journalctl -u softmobile-repair-lab.service -n 15 --no-pager

Disabling *just* the code-repair scheduler:
  systemctl disable --now softmobile-repair-lab.timer

PR remains a draft pending independent review, CI status and real handset
WhatsApp receive/send verification.


## GitHub draft patch proposals (2026-10-17 local / 2026-10-18 UTC)

New patch_proposer.py consumes ONLY synthetic conversational defects,
asks Groq for a JSON text replacement in the restricted Ruby context_from
method, statically checks scope, size, dangerous operations and ineffective
changes, then checks syntax with ruby -c (without running the bot). It stores
proposal diffs/metadata as private files with mode 0600. The generator has
NO CODE EXECUTION, NO LIVE DEPLOYMENT and NO Chatwoot/WhatsApp writes.
Schedule: softmobile-patch-proposer.timer runs at 02:25,08:25,14:25,20:25
UTC, shares the synthetic lab's exclusive lock and Groq call budget, and
limits itself to four attempts per UTC day.

Live Groq patch-generation test: five candidate code proposals were rejected
(one semantically ineffective and four later rejected by static or syntax
checks). The safe validator did not apply any of them to sales-bot-v2.rb.
A separate deterministic, reviewer-authored fallback for the same previously
detected customer color/capacity bug passed Ruby syntax checking; it was
staged as a text-only diff, NOT executed or behaviorally validated.

Draft GitHub code-review proposal:
https://github.com/luis12duboqwe/chatwoot/pull/3
The PR contains an inert .patch file and risk/test notes only; its
base is the feature branch of the original pilot PR, not production.
There is no automated GitHub publishing credential on the VPS proven
available in this workflow: publishing this proposal was performed via
the existing GitHub connector. Future VPS runs save local review files
but do not autonomously publish GitHub pull requests.

Required before any production use: review the proposed algorithm,
exercise actual Ruby behavior in a restricted test environment, run all
existing 117 commercial cases plus the new regression journey, check
false positives, and approve a separately gated pilot rollout. Do not
merge/execute untrusted diffs automatically. The existing bounded
repair scheduler continues independently.

## Fase 8 — Evaluación aislada de propuestas nuevas (18 octubre 2026, UTC)

Se agregó un flujo de evaluación **antes de presentar código nuevo para revisión**:
1. `patch_proposer.py` valida alcance, riesgos estáticos y sintaxis del cambio.
2. `sandbox_review.py` ejecuta **30 conversaciones determinísticas** sobre
   el motor Ruby del bot actual y sobre el candidato.
3. `sandbox_stress.py` genera otras **150 variantes independientes** con
   colores, capacidades, alternativas condicionales, comparaciones y decisiones
   explícitas del comprador. Un parche que introduce cualquier regresión
   comprobada en estas pruebas queda rechazado.
4. `isolated_gate.py` exige las **117 regresiones comerciales Ruby**.
5. Solo si supera las tres puertas, se guarda un reporte de candidato
   `review_ready` y un archivo de diferencia para revisión humana.
   **No existe ninguna llamada a instalación automática de este código.**

### Aislamiento de seguridad

Todas las evaluaciones de código candidato utilizan contenedores Docker
efímeros basados en la imagen Chatwoot local, con `--network none`,
`--read-only`, `--user 65534:65534`, `--cap-drop ALL`,
`--security-opt no-new-privileges`, límite de memoria/CPU y procesos,
sin montajes de código, disco o socket del VPS. Se bloquea la consulta
a catálogo HTTP del motor Ruby mediante un sustituto de pruebas de solo
inventario vacío. La candidata nunca se ejecuta en el contenedor productivo
ni se usa Rails runner de producción.

Una imagen/contendor aislado reduce el riesgo, pero no prueba que un parche
desconocido sea seguro. Por eso la publicación/aplicación continúa sujeta
a revisión humana.

### PR #3: Caso color/capacidad

Primera propuesta rechazada: 23/30 respuestas correctas (iguales al original),
con 6 errores corregidos pero 6 regresiones.

Segunda propuesta determinística para revisión:
- Primer conjunto: original **23/30**, candidata **30/30**;
  7 problemas corregidos, ninguna regresión en las pruebas.
- Conjunto independiente de 150: original **60/150**,
  candidata **150/150**, 90 mejoras, ninguna regresión.
- Batería Ruby completa candidata **117/117** superada.
- Pruebas Python de herramientas **133/133** aprobadas en el VPS.
- Código público bot activo: **sin modificaciones**.
- URL PR borrador: https://github.com/luis12duboqwe/chatwoot/pull/3

Las estadísticas describen solo conjuntos sintéticos específicos, no
rendimiento de ventas, cobertura total del lenguaje o calidad real
en WhatsApp. El PR #3 contiene únicamente archivos inertes de propuesta
y evidencia, sin despliegue. PR #2 conserva el motor y la infraestructura
de auditoría, igualmente en borrador.

Falta aún revisión autorizada del código, evaluación de datos distintos
a los conjuntos desarrollados aquí, confirmación CI y una prueba con
dispositivo piloto antes de producción.

### Uso local
`python3 sandbox_review.py --proposal quality/untrusted-patch-proposals/<propuesta>.diff`

El generador `patch_proposer.py` ejecuta estas pruebas aisladas
en futuras propuestas Groq antes de clasificarlas como aptas para revisión.
Los cambios no seleccionados por las reglas de despliegue existentes
**nunca** se instalan autónomamente.

## Fase 9 — revisión de seguridad y nuevas familias de reparación (18 oct 2026 UTC)

Se amplió el catálogo de respuestas comerciales que pueden seleccionarse
por Groq e instalarse automáticamente **solo si pasan los controles
existentes**. El motor seguro ahora reconoce cuatro familias:

- `advisor_eta`: evita inventar un plazo de respuesta humana.
- `tracking_followup`: consulta de número de guía o rastreo del envío.
- `prepurchase_inspection`: pregunta por probar o revisar la unidad antes
  de comprar o pagar; no promete que sea posible.
- `optional_coverage`: consulta de seguro opcional de pantalla, protección
  contra daños o garantía extendida; no promete existencia, cobertura, costo
  ni aprobación de un seguro.

Se añadió `family_gate.py` como requisito obligatorio antes de la
batería completa: 15 casos positivos/negativos ejecutados en un contenedor
ephemeral Docker `--network none`, `--read-only`, UID no privilegiada,
sin montajes del VPS ni acceso al Chatwoot productivo. Detecta si
consultas de reparación, daños posteriores a compra, garantía estándar,
precio, fotos o stock quedan confundidas con las familias nuevas.

### Primera promoción: cobertura opcional

Hallazgo de ejemplo de prueba `33367edaf5b0271c9b`.
Groq seleccionó una respuesta segura para preguntar por protección
adicional del teléfono. Se reprodujo el diálogo, pasaron **15/15**
casos aislados y **117/117** regresiones Ruby. Despliegue automatizado al
piloto completado con respaldo
`sales-bot.autofix.20261018T005139Z.bak`. La política instalada tiene
las familias `advisor_eta` y `optional_coverage`. No se modificó el
número de cuenta/bandeja/conversación autorizado (2/2/3). No se enviaron
mensajes reales desde las simulaciones.

### Segunda propuesta: prueba de teléfono antes de comprar

Hallazgo ficticio `db278a3db2956d4a69`: respuesta anterior omitía
la pregunta sobre probar el teléfono antes de comprar. Nuevo candidato
`prepurchase_inspection` verificado por replay, **15/15** casos
aislados y las **117/117** pruebas Ruby. La nueva regla **no se instaló**
porque el límite seguro permanece en UNA promoción automática diaria.
Se conservaron candidato privado y resultados para reevaluación en la
siguiente ventana elegible. No se anticipa aprobación ni se omite el
bloqueo por límite diario.

### Seguridad del generador de código no aprobado

`patch_proposer.syntax_only()` ya no analiza propuestas AI dentro del
contenedor productivo Chatwoot, ni siquiera mediante `ruby -c`. Ahora
invoca el parser Ruby exclusivamente en un contenedor efímero restringido,
sin red, montajes, acceso al socket Docker ni secretos de Chatwoot.
La cadena de evaluación posterior mantiene 30 comparaciones originales,
150 casos sintéticos adicionales y 117 regresiones completas, también
en aislamiento. En el estado nuevo, el PR #3 continúa validado y no
aplicado al bot.

Las **143/143 pruebas Python locales** pasaron; `test_family_gate.py`
usa datos simulados embebidos para ejecutarse también en GitHub CI sin
copiar a ese repositorio los hallazgos privados del VPS.

### Límites

El generador de código AI arbitrario nunca se despliega al piloto sin
revisión y autorización. Los fixes automáticos están limitados a
plantillas estáticas, un despliegue diario, el flujo de pruebas
independientes, respaldo y reversión. Se mantienen los servicios de
laboratorio y el estado de propuestas de revisión separado de los chats
reales.

Solo pruebas reales autorizadas de recepción y envío en el dispositivo
piloto podrían justificar ampliar cobertura a otras bandejas.

## Fase 10 — Retroalimentación y reintentos limitados para parches Groq

El generador de propuestas para revisión (`patch_proposer.py`) ahora utiliza
`proposal_iteration.py` para intentar corregir un problema **hasta dos
veces por ejecución**, y **cuatro intentos por día UTC** entre ejecuciones.
Todos los intentos comparten además el límite diario global de Groq con los
laboratorios anteriores.

Después del primer rechazo, el segundo intento recibe exclusivamente
retroalimentación **fija y autorizada** del validador:
- error estático del reemplazo y de la estructura JSON;
- sintaxis Ruby inválida;
- regresiones en 30 conversaciones de color/capacidad;
- regresiones en 150 variaciones adicionales;
- pruebas generales Ruby fallidas (117 casos);
- parche repetido exactamente sin modificación útil.

El generador **no envía logs internos, rutas privadas, claves ni datos de
clientes**. Solo ingresa en la API la conversación ficticia y un método de
código previamente autorizado para revisión. Los parches propuestos que
superen los controles solo se guardan como diferencias y reportes privados:
siguen marcados como `review_ready_not_deployed`. No pueden ejecutarse
como Ruby en el contenedor activo ni instalarse de manera autónoma.

Los `test_proposal_iteration.py` incluyen siete nuevas verificaciones
del ciclo de reintentos, el bloqueo por presupuesto, indisponibilidad API,
parches duplicados, filtrado estático, pruebas de comportamiento/regresión y
ausencia de despliegues. Total actualizado: **150/150 pruebas Python locales**.

### Error de CI corregido

La ejecución GitHub Actions del commit anterior había fallado porque la
prueba `test_sandbox_review.py` leía las suites Ruby desde la ruta
`/opt/softmobile-waha-test/laboratorio-ia/quality/` del VPS. En un
runner GitHub esa ruta no existe. El test ahora simula el contenido de esas
suites para comprobar el comando de contenedor sin depender de archivos
privados. El CI sigue revisándose por separado; no se debe inferir que
ha pasado solo porque las pruebas locales terminan con éxito.

Al momento de esta actualización, el laboratorio agotó sus **cuatro**
intentos de generación de código correspondientes al 18 de octubre UTC.
La ejecución solicitada retornó `daily_proposal_cap` sin efectuar nuevas
llamadas ni modificar producción. Los nueve timers VPS y la exclusividad
de Chatwoot cuenta 2, bandeja 2, conversación 3 siguen verificados.

Los cambios de código de alcance desconocido continúan requiriendo
revisión humana y no pueden ser instalados por el automejorador de reglas.

## Groq private copilot: bounded memory + claim guard (18 October 2026 UTC)

This iteration improves the *commercial assistant*, not the source-patch lab.
The existing `chatwoot_ai_bridge.py` remains exclusively scoped to Chatwoot
account 2 / inbox 2 / pilot conversation 3; it creates **PRIVATE** internal
agent notes only, never public replies.

- Incoming source now retrieves up to four previous **public incoming buyer
  messages** in the same verified conversation. It does not retrieve private
  notes or other inboxes. Older messages longer than 420 chars or containing
  attachments are never considered for memory.
- `sales_context.py` never forwards those previous messages verbatim. It
  derives only allowlisted model, storage, one unambiguous color and known city.
  Messages containing email, phone, bank/payment details, precise address,
  credentials or order numbers are discarded before context extraction.
- `suggestion_guard.py` blocks high-confidence unsupported claims (exact
  price/amount, delivery time, reserved stock, guarantee of approval,
  included accessories or insurance, requests for sensitive credentials).
  A risky Groq suggestion is replaced with a generic *private* assistant
  draft requiring a human, not sent to the buyer.
- The newest buyer message is still independently checked by the existing
  sensitive-content filter; the bridge skips stale/short/private/multimedia
  messages and limits usage to 30 suggestions per UTC day.
- The new context reader was verified as valid Ruby syntax and performed a
  **read-only** Rails query on the authorized pilot. No actual customer text
  or credentials were printed or transferred to this report.

Tests: **162/162** local Python tests pass, including nine new privacy/claim
cases and bridge integration tests. Two **fictitious** live Groq API probes
passed: a 128GB black -> 256GB blue customer correction retained the right
new capacity/color, and a warranty+accessories answer triggered the safety
fallback. Neither probe wrote a Chatwoot message.

This change intentionally **does not enable Groq to send public customer
messages**. The existing rule-based public bot and its 117-case Ruby test
suite remain separate; PR #4 has 42 independent dialogue scenarios and is
still pending independent human review.

## Groq vendedor — interpretación de opciones y evaluación sombra (18 Oct 2026 UTC)

El piloto sigue **sólo en notas privadas** para el asesor. No se activó el
envío público por Groq, no se cambió el código Ruby del bot, no se modificó
inventario ni se realizaron ventas o mensajes reales.

### Preferencias de compra
- `variant_preference.py` distingue preferencia explícita de comparaciones,
  una alternativa condicional, un rechazo y preguntas ambiguas. No asume que
  el **último producto mencionado** siempre es el elegido.
- `groq_pilot.py` transmite `selected_preference` calculado sobre el mensaje
  ficticio/filtrado y exige coherencia de color y capacidad cuando hay una
  selección clara. Si hay dos variantes y ninguna elección unívoca, fuerza
  revisión humana y nunca elige una sin confirmación.
- Se mejoró el prompt para no confundir una comparación de precios con una
  nueva elección del comprador.

### Calidad de sugerencias
- `suggestion_guard.py` también rechaza afirmaciones no comprobadas de
  disponibilidad, reserva, regalos, cargadores, seguro, entrega inmediata
  o aprobación bancaria. Su respuesta de respaldo ya no vuelve a
  preguntar qué modelo busca el cliente: solicita verificación de los datos
  comerciales pendientes sin inventar políticas.

### Pruebas con Groq REAL usando datos ficticios (sin clientes)
Se ejecutó `groq_sales_shadow.py --run` dos veces con **siete**
consultas fijas: cambio de capacidad/color, preferencia frente a comparación,
alternativa si no hay stock, ambigüedad, garantía con accesorios, plazo de
entrega e intención nueva.
- Primera evaluación: **4/7** propuestas estructuradas válidas y
  controladas; 3 fueron rechazadas, 1 sugerencia bloqueada por el filtro.
- Tras añadir selección explícita determinística a la entrada:
  **7/7** propuestas válidas, **7/7** preferencias o escalaciones esperadas,
  2 sugerencias reemplazadas por respuesta interna prudente.
- Un resultado bueno en 7 escenarios no implica una tasa real de éxito
  ni autoriza respuestas públicas.
- `groq_sales_shadow.py` guarda **solo indicadores fijos y agregados** de
  los casos ficticios; no guarda las salidas redactadas del proveedor ni
  texto de clientes reales, ni realiza escrituras a Chatwoot.
- `test_variant_preference.py` y `test_groq_sales_shadow.py` son pruebas
  independientes y reproducibles con mocks; **173/173** pruebas Python
  locales aprobadas antes de sincronizar la rama con GitHub.
- Las pruebas CI sólo verifican módulos offline: no acceden a Groq,
  Chatwoot ni al VPS y no validan WhatsApp real.

Pendiente: ampliar la muestra independiente de conversaciones comerciales,
verificar la entrega real del canal piloto, conectar el inventario con
control de existencias y demostrar una mejora medible antes de habilitar
autorespuestas en producción.

### Additional quality gate — repeated buyer questions (18 Oct 2026 UTC)

The private Groq suggestion guard now accepts the sanitized message and
allowlisted context through `guarded_draft(output,clean)`, and rejects
asking again for a model, color or capacity the buyer already provided.
When it rejects such a draft, it produces a private, human-review-required
fallback that does not ask the same question again. The fallback never
states that a model, color or shipping route is available.

This applies only to the agent's INTERNAL private Chatwoot note, not
outgoing WhatsApp replies. No change to live Ruby bot or its send policy.

New offline tests cover duplicate model, GB and color prompts and legitimate
pickup/delivery follow-ups. **175/175 Python tests** pass on VPS.
Re-executed seven synthetic Groq API prompts with the final code: **7/7**
structured responses met preference and handoff requirements; two claims
were blocked. This is a small synthetic sample, not a success rate in
commercial production. Private aggregate results only were persisted.

## Prueba multipaso: Groq vendedor privado (18 oct 2026, UTC)

Esta etapa evaluó CUATRO conversaciones ficticias completas de TRES mensajes
cada una, conectadas a la API real de Groq, sin Chatwoot ni WhatsApp. Los
escenarios fueron: alternativa por falta de una variante y retiro en Choloma;
comparación de precios sin perder el teléfono elegido y pregunta de garantía;
cambio de opinión y consulta para probar una unidad antes de pagar; y
comparación ambigua que termina en una selección y consulta de entrega.

Se detectó antes de llamar a la API que `preference_snapshot` perdía la
variante seleccionada al procesar frases como «Si no hay 512GB negro,
mejor 256GB azul» antes de una pregunta logística. Se añadió
`journey_memory.py`: memoria determinística y minimizada de hasta cuatro
mensajes previos; evita sustituir la elección por la variante de una
pregunta comparativa y elimina elecciones ambiguas. Sigue descartando
mensajes con identificadores personales o información de pagos.

Primera prueba real con Groq: 10/12 turnos superaron todos los controles,
con cero errores de memoria, cuatro afirmaciones no verificadas interceptadas
y dos fallos de derivación humana (retiro en tienda y prueba previa).
Se amplió el enrutamiento de temas sensibles de `groq_pilot.py` para forzar
`human_review=true` en retiro, prueba antes de pagar y entrega.

Segunda ejecución real (mismos escenarios): **12/12 turnos aprobados**,
cero errores de memoria, tres afirmaciones comerciales interceptadas y
derivación humana correcta en los turnos que la requerían. Se ejecutaron
**188/188 pruebas Python locales**. El script conserva únicamente métricas
por ID ficticio y nunca redactados originales de Groq.

Fuentes: `groq_sales_journeys.py`, `test_groq_sales_journeys.py`,
`journey_memory.py` y `test_variant_preference.py`.
El CI ejecuta pruebas unitarias sin API keys y NO repite las solicitudes
reales a Groq.

La **IA aún no envía respuestas públicas**; sólo funciona el copilot que
escribe notas internas de asesores en la conversación piloto autorizada.
No hay transacciones, inventario integrado, reservas, WhatsApps a clientes
ni despliegue nuevo del motor Ruby. Los resultados corresponden a una
muestra sintética reducida, no a efectividad real de cierre de ventas.

## Fase: objeciones y conversaciones comerciales de 5 turnos (18 oct 2026 UTC)

Se verificaron **4 conversaciones de cinco mensajes ficticios cada una**
mediante la API real de Groq, SIN escribir en Chatwoot ni WhatsApp. Temas:
presupuesto, descuento, condición del equipo, financiación a cuotas,
garantía, objeción por precio de otro vendedor, cambios de variante,
comparación de precios, entrega, parte de pago, revisión física y
disposición final de compra.

### Fallos detectados y corregidos

- Memoria `journey_memory.py`: «No quiero negro, mejor azul» conservaba
  el negro; «¿Y el azul cuesta lo mismo?» sustituía la selección anterior
  aunque fuera solo una comparación. Ahora actualiza ante una preferencia
  afirmativa y conserva la elección en preguntas comparativas. Un rechazo
  sin sustitución elimina el color rechazado.
- `groq_pilot.py`: una pregunta sobre el precio de la segunda variante
  ya NO se etiqueta como nueva elección. El JSON de entrada agrega
  `comparison_only` y no fuerza `selected_preference` cuando se trata
  exclusivamente de comparación. El validador mantiene la variante
  previamente elegida o rechaza la propuesta y exige verificación humana
  del estado nuevo/usado.
- `suggestion_guard.py`: cuando una respuesta contiene precio, stock,
  regalo, envío o financiamiento no verificados, el fallback privado
  responde a la **objeción concreta** (precio, cuotas, descuento,
  garantías, entrega, inspección, parte de pago, compra) en vez de
  devolver siempre el mismo texto genérico. También intercepta una
  consulta por parte de pago si el borrador ignoró esa intención.
- `groq_sales_objections.py`: evaluación con límite estricto de 20
  peticiones por ejecución, ritmo de 2 segundos entre peticiones en
  `--run`, máximo 2 ejecuciones reales por día UTC, y aborto seguro
  cuando hay errores HTTP 429/5xx o red. Las pruebas no envían
  mensajes públicos. No se guardan respuestas ni chats de usuarios.

### Evidencia

1. Primera ronda real: **16/20** turnos superaron las comprobaciones;
   1 pérdida de preferencia, 1 derivación humana omitida y 2 respuestas
   poco relacionadas con la objeción. Se bloquearon 3 afirmaciones.
2. Segunda ronda sin pausas: **12/20** aceptadas; 8 solicitudes fallaron
   (proveedor o validación, causa no distinguida en el registro antiguo).
   Estos 8 rechazos NO se contaron como fallos comerciales y motivaron
   clasificar errores de API y reducir la velocidad de ejecución.
3. Tercera ronda real con pausas y las correcciones: **20/20** cumplen el
   control de memoria, tema relevante y derivación humana; **0** fallos
   de memoria, **0** omisiones de derivación, **0** respuestas fuera de
   tema según palabras-clave y **3** afirmaciones comerciales
   interceptadas. Ningún error de proveedor en esa ejecución.
4. **204/204 pruebas Python locales** aprobadas, incluidas pruebas de
   presupuesto por día, interrupción tras error 429, fallos estructurados,
   tratamiento de rechazo de color, comparación sin cambio de elección,
   decisiones sensibles y fallback temático.

El resultado indica conformidad en **esta muestra fija ficticia**, NO tasa
de cierre real, ni calidad subjetiva de cada respuesta. Se utiliza
evaluación con reglas determinísticas simples de tema, no una validación
de ventas reales por un juez humano independiente. No hay integración
de inventario, precios verificados ni autorización para autoenviar
mensajes de Groq. El bot Ruby activo y el parche conversacional PR #4
siguen sin cambios ni nuevas implementaciones de esta fase.
