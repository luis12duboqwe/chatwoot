# SoftMobile — paquete piloto de dos mejoras seguras

## Alcance y estado

El bot actualmente expuesto a Chatwoot sigue **restringido a cuenta 2,
bandeja 2, conversación piloto 3** y no usa el inventario ficticio. El
paquete combina dos cambios Ruby predefinidos, sin código ejecutable
generado libremente por Groq:

1. Interpretación de cuotas: no tomar «a 12 meses», «a 18 meses»,
   «a 24 cuotas», «a 36 pagos», etc., como si el cliente hubiera
   preguntado por un Samsung A12/A18/A24/A36.
2. Generalización controlada sobre incluir o cotizar funda, protector,
   cargador u otro accesorio. La respuesta obliga a consultar con asesor;
   no inventa precio, existencia, regalías o garantía.

**18 oct 2026 a las 19:10 UTC:** `combined_pilot_promotion.py --stage`
compiló y validó el código candidato, sin instalarlo.
SHA-256 base:
`4dc2814ddb5d3a03c31add202cb004f6369a77b154f2fa5141d5dfb3220ef106`.
SHA-256 candidato:
`7c500af8ee6c6f031e6a89b64ecbd9a63af26df627509c49744fb76e925fa7c2`.
Estado: `verified_staged` y promoción **no ejecutada**.

## Evidencia independiente

| Prueba | Ruby base | Candidato |
|---|---:|---:|
| 72 conversaciones comerciales inventadas | 60 | 72 |
| 48 preguntas adicionales de cuotas no vistas en entrenamiento | 0 | 48 |
| 108 rutas de variantes en inventario ficticio | 108 | 108 |
| 10 nuevas maneras de preguntar por accesorios | — | 10 |
| 14 preguntas que NO debía alterar | — | 14 |
| Regresiones clásicas Ruby | — | 117 |

La simulación realiza checkout *exclusivamente* dentro del inventario
Python efímero. No significa que el vendedor real pueda cobrar o
apartar teléfonos. En las pruebas no se enviaron mensajes públicos ni
se accedió a WAHA, clientes, pagos o stock real.

## Despliegue de seguridad

`softmobile-combined-pilot-promotion.timer` se ejecuta una vez al
día a las **00:05 UTC**. Su primer intento quedó programado para
el **19 de octubre 2026**, luego de que se libere el único cupo
diario compartido para mejoras aprendidas. La ejecución manual del
18 de octubre devolvió **`daily_deployment_cap`**, sin instalar
nada y con `Result=success`.

El servicio debe:
- obtener los mismos bloqueos que el autoaprendizaje y promotor semántico;
- constatar la versión byte-a-byte que fue revisada y las reglas
  aprobadas; cualquier drift cancela el despliegue;
- revisar que el candidato almacenado coincide con el SHA aprobado;
- repetir las pruebas completas de ventas, accesorios, 117 regresiones
  Ruby, 48 ejemplos nuevos y 108 consultas de inventario antes de
  sustituir Ruby;
- pausar el temporizador del piloto, respaldar el código y restaurar
  el temporizador incluso si ocurre una excepción;
- repetir pruebas Ruby **después** de instalar; y comprobar las pruebas
  comerciales de forma independiente, con restauración del código
  anterior si se detecta una regresión;
- registrar como promoción diaria solo una instalación totalmente
  aprobada.

El promotor semántico individual sigue disponible a las 00:17 UTC;
si el paquete combinado consumió el cupo, no instalará un segundo
cambio ese día. El bot **no se expande** a clientes reales por el
hecho de instalar este paquete: continúa vigente el piloto específico.

## Auditoría y parada de emergencia

```bash
cd /opt/softmobile-waha-test/laboratorio-ia
python3 combined_pilot_promotion.py --status
python3 conversion_training_lab.py --status
python3 financing_holdout.py --status
python3 production_readiness.py
systemctl list-timers | grep softmobile
systemctl disable --now softmobile-combined-pilot-promotion.timer
```

El control global `production_readiness.py` sigue bloqueando la venta
automática masiva: el catálogo en Drive es una referencia sin stock
validado ni precios comprobados. No activar mensajes globales, precios
ficticios ni operaciones de pago a partir de este laboratorio.

## Qué NO implica

Ningún porcentaje de aprobación sintética es una tasa real de cierre.
El cumplimiento de esta fase de capacitación tampoco demuestra que
Groq atienda consistentemente ventas reales. Para abrir la venta
automatizada faltan una fuente de inventario real, confirmación de
ofertas y garantía, supervisión en Chatwoot y autorización de alcance.

## Revisión de calidad V2 — 18 oct 2026, 19:45 UTC (prevalece sobre V1)

Una auditoría independiente de Groq señaló que la frase anterior sobre
agregar una funda gratis era demasiado evasiva. Se corrigió con una
respuesta más directa, igualmente limitada por la ausencia de
promociones verificadas:

> «Por ahora no puedo incluirte la funda como accesorio gratis, porque
> no tengo confirmada esa regalía para el equipo. Un asesor puede
> verificar si aplica sin costo o indicarte su precio antes de agregarla.»

La regla general de accesorios también fue actualizada para distinguir
explícitamente el regalo de la cotización sin asumir condiciones.

El **paquete V1 del documento anterior está cancelado y nunca debe
promoverse**. El paquete nuevo tiene:

- versión `bundle-static-semantic-financing-directness-20261018-v2`;
- SHA-256 **`87593b8d9284c8d12b56f02916364d7a74e2726925b76754b824ef3ef38073ca`**;
- 72/72 conversaciones comerciales, 48/48 cuotas no vistas antes,
  10/10 consultas de accesorios, 14/14 controles negativos,
  108/108 consultas ficticias de inventario y 117/117 Ruby;
- 340/340 pruebas Python locales;
- segunda evaluación de Groq de la NUEVA versión: `error=false`,
  categoría `no_issue`, registrada el 18 de octubre a las 19:45 UTC;
- calidad y hashes registrados en
  `quality/directness-independent-review.json` y
  `quality/combined-pilot-review.json`.

Se incorporaron tres servicios:
- `softmobile-directness-ai-review.timer`, una vez por hora al minuto
  52 UTC, con reutilización de una aprobación independiente reciente;
- `softmobile-combined-pilot-promotion.timer`, 00:05 UTC;
- `softmobile-finance-pilot-promoter.timer`, 00:09 UTC, solo de
  contingencia si el paquete completo no se promueve.

El promotor **exige una aprobación Groq reciente vinculada al SHA exacto**,
aparte de todas las pruebas aisladas, del límite de una mejora por día
y de la reversión automática. Al no haber cumplido aún la siguiente
ventana UTC, el estado actual es **preparado y programado, NO
desplegado**.

La ruta de contingencia puede desplegar únicamente la corrección
determinista de cuotas `972b74f1e4a9126059fb273117178f131a7299e5f24b03c15451d7df5734755e`,
siempre que el código base original persista, los tests se repitan y
no se haya usado el cupo diario. Ambos comparten el mismo historial
de despliegues y jamás hacen dos instalaciones aprendidas el mismo día.
El promotor antiguo de accesorios por separado queda detenido para no
competir con el paquete V2.

**La preparación para atención general sigue bloqueada:** no hay
inventario comercial confirmado, no se autorizaron reservas/pagos
reales y no se ampliaron destinatarios. Cualquier falla futura de
Groq o de las pruebas hará que se posponga el despliegue sin
contaminar el inventario ni las comunicaciones de producción.
