# PLAN-2026-09-25-inventario-select-for-update (v1)

**Task:** TASK-011
**ADRs relacionados:** Ninguno

## Objective
Cerrar el único hueco `CRÍTICO` que queda en el backlog de seguridad/integridad (docs/integration-and-backlog.md #3): eliminar la condición de carrera que permite sobreventa de inventario cuando dos `create_work_note` concurrentes compiten por el mismo stock, agregando `select_for_update()` a `reduce_inventory`/`return_to_inventory` y un test que reproduce y verifica el fix.

## Context
Ver TASK-011 (`## Investigación`) para el detalle completo. Resumen: `Inventario_Business.reduce_inventory` y `return_to_inventory` leen una fila de `inventario` y la guardan sin bloquearla; ambos métodos ya corren dentro de transacciones atómicas (`Proforma_Business.create_work_note` y `abrir_proforma`, ambos con `@transaction.atomic`), así que falta el lock de fila, no la transacción. El proyecto usa Postgres real, lo que hace viable un test de concurrencia genuino con locks reales.

## Current behavior
- `reduce_inventory` ([praxsa_manager/product/business/inventario.py:52-71](praxsa_manager/product/business/inventario.py:52)): `query = inventario.objects.select_related(...).filter(..., to_install__gte=length_to_reduce).order_by('bobina__width','date')[:1]`, luego `bobina_inventario.to_install -= length_to_reduce; .save()`. Sin lock — dos transacciones concurrentes pueden leer el mismo `to_install` antes de que cualquiera haga commit.
- `return_to_inventory` ([praxsa_manager/product/business/inventario.py:73-83](praxsa_manager/product/business/inventario.py:73)): mismo patrón con `objects.get(id=...)`.
- Caller de `reduce_inventory`: `create_work_note` ([praxsa_manager/product/business/proforma.py:96-138](praxsa_manager/product/business/proforma.py:96)), ya con `@transaction.atomic` + `with transaction.atomic()` interno.
- Caller de `return_to_inventory`: `abrir_proforma` ([praxsa_manager/product/business/proforma.py:61-82](praxsa_manager/product/business/proforma.py:61)), mismo patrón.
- No existe hoy ningún test de concurrencia (`TransactionTestCase`/`threading`) en el proyecto.

## Expected behavior
Cuando dos transacciones compiten por la misma fila de `inventario` con stock exacto para una sola operación: la primera en llegar bloquea la fila (`select_for_update`), reduce el stock y hace commit; la segunda espera el lock, al obtenerlo relee el `to_install` ya actualizado, no cumple `to_install__gte = length_to_reduce`, y falla correctamente con `NoHayLaminasDisponibles` (mismo comportamiento que hoy cuando no hay stock suficiente desde el principio) — sin sobreventa ni valores negativos en `to_install`.

## Architecture considerations
- **Contrato API**: sin impacto. El cambio es interno a `business/inventario.py`; la excepción `NoHayLaminasDisponibles` que se propaga ante falta de stock ya existe y ya se traduce a un error de negocio en `create_work_note` (`except NoHayLaminasDisponibles`) — el frontend ya maneja ese caso hoy (falta de stock), la segunda transacción de una carrera ahora cae en el mismo camino en vez de sobrevender.
- **Datos existentes**: no se requiere migración para el fix principal (`select_for_update()` no toca el esquema). El `CheckConstraint(to_install__gte=0)` opcional mencionado en el backlog sí requeriría migración y no se verificó si hay datos existentes con `to_install` negativo — queda fuera de este plan (ver Out of scope).
- **Dinero/Decimal**: sin cambios; `to_install`/`length_to_reduce` ya son `Decimal` y el fix no altera esa aritmética.
- **Rendimiento**: `select_for_update()` agrega un lock de fila de vida corta (duración de la transacción, que ya existe hoy); impacto esperado despreciable dado el volumen de escrituras concurrentes real (proformas por sucursal, no un sistema de alta frecuencia).
- **Seguridad/permisos**: no aplica, no hay superficie de autorización involucrada.
- **Acoplamiento**: ambos métodos solo tienen un caller cada uno (confirmado en la investigación), así que el fix no tiene efectos secundarios en otros flujos no auditados.
- **Nota técnica de Django**: `select_for_update()` sobre una queryset con slice (`[:1]`) requiere soporte de `LIMIT`/`OFFSET` en locking queries — Postgres lo soporta (a diferencia de MySQL) y el proyecto usa `Django==4.2.1` sobre `django.db.backends.postgresql`, así que `reduce_inventory` puede mantener su `.order_by(...)[:1]` con `select_for_update()` sin reescribir la query.

## Proposed solution
Agregar `.select_for_update()` a la queryset de lectura en ambos métodos, antes de evaluarla (antes del `.exists()`/slice en `reduce_inventory`, antes de `.get()` en `return_to_inventory`), reusando las transacciones atómicas que ya envuelven a ambos callers. No se requiere ningún cambio en `proforma.py` — el lock se libera automáticamente al cierre de la transacción `@transaction.atomic` ya existente.

El `CheckConstraint` de base de datos (paso 3 opcional del backlog) queda fuera de este plan — es una red de seguridad adicional, no necesaria para cerrar la condición de carrera en sí, y requiere verificar datos existentes antes de decidir la migración (ver Out of scope).

## Files/components affected
Backend únicamente:
- `praxsa_manager/product/business/inventario.py` — agregar `select_for_update()` en `reduce_inventory` (líneas 52-71) y `return_to_inventory` (líneas 73-83).
- `praxsa_manager/product/tests/test_inventory_concurrency.py` (nuevo) — test de concurrencia.

No hay componentes de `proforma/` (frontend) afectados.

## Implementation steps
1. Crear `praxsa_manager/product/tests/test_inventory_concurrency.py` usando `TransactionTestCase` (no `TestCase`, para permitir conexiones/transacciones reales concurrentes desde threads separados) y las factories existentes de `tests/helpers.py` (mismo patrón que `test_proforma_status_field.py`): un `inventario` con `to_install` exacto para una sola operación, y dos proformas completas apuntando a la misma sucursal/bobina/ancho.
2. En ese test, lanzar dos threads que ejecuten `Proforma_Business().create_work_note(...)` casi simultáneamente (sincronizados con un `threading.Barrier` o `Event` para maximizar la ventana de carrera), cada uno con su propia conexión de BD (Django abre una por thread automáticamente).
3. Confirmar contra el código actual (antes del fix) que el test demuestra la sobreventa: ambos threads tienen éxito y el `inventario.to_install` final queda por debajo de cero o inconsistente con lo realmente disponible. Dejar constancia de esto en el mensaje del commit o en un comentario del test (evidencia del bug antes del fix), sin dejar el repo en un estado donde el test quede roto/skippeado.
4. Agregar `.select_for_update()` en `reduce_inventory` ([inventario.py:52-71](praxsa_manager/product/business/inventario.py:52)) y `return_to_inventory` ([inventario.py:73-83](praxsa_manager/product/business/inventario.py:73)).
5. Re-ejecutar el test de concurrencia: debe pasar demostrando que exactamente una de las dos transacciones tiene éxito (nota de trabajo creada, `to_install` en 0) y la otra falla correctamente (excepción de negocio equivalente a falta de stock, sin sobreventa).
6. Ejecutar la suite completa (`python manage.py test`) para confirmar que no hay regresión en `test_proforma_status_field.py` y demás tests que ejercitan `create_work_note`/`abrir_proforma`.

## Test strategy
- **Nivel**: integración/concurrencia a nivel de `business/`, usando `TransactionTestCase` real contra Postgres — es el único nivel que puede demostrar la condición de carrera real (un `TestCase` normal envuelve todo en una única transacción de test y no sirve para simular dos conexiones concurrentes).
- **Caso principal**: dos `create_work_note` simultáneos compitiendo por el mismo stock exacto (alcanza para uno) → antes del fix, sobreventa (ambos éxito, `to_install` inconsistente); después del fix, exactamente uno tiene éxito y el otro falla con el error de "no hay lámina disponible".
- **Regresión**: correr la suite completa de `praxsa_manager/product/tests/` para confirmar que `select_for_update()` no cambia el comportamiento de los flujos existentes sin concurrencia (mismo resultado, solo con lock de por medio).
- **¿Corresponde E2E?** No. Este es un bug de integridad de datos a nivel de transacción de base de datos — no depende de la integración real entre Angular y Django, no cambia navegación ni formularios, y un test E2E con Playwright no podría controlar de forma confiable la sincronización de dos transacciones concurrentes (es un problema de timing a nivel de BD, no de UI). El nivel de integración con `TransactionTestCase` es el adecuado y suficiente.

## Acceptance criteria
- Existe un test de concurrencia que, ejecutado contra el código sin el fix, demuestra la sobreventa descrita en el backlog.
- `reduce_inventory` y `return_to_inventory` usan `select_for_update()` dentro de las transacciones atómicas ya existentes en sus callers.
- El test de concurrencia pasa después del fix: exactamente una de las dos operaciones concurrentes tiene éxito, la otra falla correctamente sin sobreventa.
- `to_install` nunca queda en un estado donde se restó más de lo que había disponible en el momento de cada operación.
- La suite completa de tests de `praxsa_manager/product/tests/` sigue pasando (sin regresiones).

## Risks
- **Test de concurrencia frágil**: coordinar dos threads con conexiones de BD separadas es más delicado que un test unitario común; si la sincronización no maximiza la ventana de carrera, el test podría "pasar" sin haber ejercitado realmente la condición concurrente. Mitigación: usar un `threading.Barrier`/`Event` explícito para forzar que ambos threads lean antes de que cualquiera escriba, y verificar en el paso 3 (antes del fix) que el test efectivamente reproduce la sobreventa — si no la reproduce, el test está mal construido y hay que ajustarlo antes de continuar.
- **Deadlocks**: si en el futuro se agregan más locks (`select_for_update`) en el mismo flujo de negocio sobre filas distintas, existe riesgo teórico de deadlock por orden de adquisición inconsistente. No aplica hoy porque cada operación de `create_work_note`/`abrir_proforma` bloquea filas de `inventario` una por una en el mismo orden (`order_by`) dentro del loop — se deja como nota para revisión futura, no como bloqueante de este plan.
- **`select_for_update()` fuera de transacción**: si algún caller futuro llama a `reduce_inventory`/`return_to_inventory` sin estar dentro de `@transaction.atomic`, Django lanza `TransactionManagementError` en tiempo de ejecución. Mitigación: ambos callers actuales ya están correctamente envueltos (verificado en la investigación); no se requiere cambio adicional ahora, pero cualquier caller nuevo debe respetar esa regla.

## Out of scope
- `CheckConstraint(to_install__gte=0)` a nivel de base de datos (paso 3 opcional del backlog #3) — requiere verificar primero si existen datos con `to_install` negativo antes de decidir una migración; queda como candidato a un task separado si se decide perseguirlo.
- Auditoría de otros posibles escritores directos de `inventario.to_install` fuera de `business/inventario.py` (p. ej. edición manual desde el admin de Django) — no se encontró ninguno en la investigación, pero tampoco se auditó `admin_config/` completo; si existiera, quedaría fuera del alcance de este fix puntual.

## Dependencias nuevas
Ninguna.
