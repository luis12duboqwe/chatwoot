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
