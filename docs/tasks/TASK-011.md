# TASK-011: Condición de carrera / sobreventa de inventario (select_for_update en reduce_inventory/return_to_inventory)

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_PLAN
**Rama:** `task/TASK-011-inventario-select-for-update`
**Pull Request:** [#43](https://github.com/rolion/praxsa-django-panel-admin/pull/43)

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-09-25 | (nuevo) → INVESTIGATION | Task creado desde backlog #3 (docs/integration-and-backlog.md) | delivery-investigate |
| 2026-09-25 | INVESTIGATION → PLANNING | Investigación completa, veredicto NEEDS_PLAN | delivery-plan |
| 2026-09-25 | PLANNING → ENGINEERING | Plan v1 listo (docs/plans/PLAN-2026-09-25-inventario-select-for-update.md), PR abierto | delivery-plan |
| 2026-09-25 | ENGINEERING → REVIEW | Implementación completa: select_for_update + test de concurrencia, suite completa sin regresiones | delivery-engineer |

## Investigación

### Requerimiento
Backlog ítem #3 `[CRÍTICO]` en [docs/integration-and-backlog.md:180-186](docs/integration-and-backlog.md:180): `reduce_inventory`/`return_to_inventory` no usan `select_for_update()`, lo que permite condición de carrera/sobreventa de inventario cuando dos `create_work_note` casi simultáneos compiten por el mismo stock (misma sucursal/bobina/ancho) con stock exacto para uno solo. Es el único hueco `CRÍTICO` que queda sin tocar por ningún PR (todo lo demás de las dos primeras semanas del plan ya está en `master`, según [docs/integration-and-backlog.md:294](docs/integration-and-backlog.md:294) y [docs/integration-and-backlog.md:313](docs/integration-and-backlog.md:313)). El backlog ya sugiere 3 pasos: (1) test que reproduce la carrera, (2) `select_for_update()` en ambos métodos, (3) opcional `CheckConstraint(to_install__gte=0)` a nivel de BD.

### Hechos encontrados
- `Inventario_Business.reduce_inventory` ([praxsa_manager/product/business/inventario.py:52-71](praxsa_manager/product/business/inventario.py:52)): hace un `SELECT` con `.filter(..., to_install__gte=length_to_reduce)[:1]` sin `select_for_update()`, y unas líneas después hace `.save()` sobre la instancia leída. Entre el `SELECT` y el `.save()` no hay ningún lock de fila — dos transacciones concurrentes pueden leer el mismo registro con el mismo `to_install` antes de que cualquiera de las dos haga commit.
- `Inventario_Business.return_to_inventory` ([praxsa_manager/product/business/inventario.py:73-83](praxsa_manager/product/business/inventario.py:73)): mismo patrón, `objects.get(id=...)` sin lock seguido de `.save()`.
- Ningún método de `inventario.py` ni de todo `praxsa_manager/product/business/` usa `select_for_update` — confirmado con `grep -rln "select_for_update" praxsa_manager/product/` (sin resultados).
- El único caller de `reduce_inventory` es `Proforma_Business.create_work_note` ([praxsa_manager/product/business/proforma.py:96-138](praxsa_manager/product/business/proforma.py:96)), que ya está decorado con `@transaction.atomic` y además abre un `with transaction.atomic()` interno (líneas 61, 65, 96, 100) — es decir, la operación completa (validar detalle, reducir inventario para cada línea, guardar el detalle, crear la nota de trabajo) ya corre dentro de una transacción de BD. Lo que falta no es la transacción en sí, sino el lock de fila (`select_for_update`) dentro de esa transacción: sin él, Postgres con el nivel de aislamiento por defecto (`READ COMMITTED`) permite que dos transacciones concurrentes lean el mismo `to_install` antes de que ninguna haga commit, y ambas restan de la misma cantidad leída.
- El único caller de `return_to_inventory` es `Proforma_Business.abrir_proforma` ([praxsa_manager/product/business/proforma.py:61-82](praxsa_manager/product/business/proforma.py:61)), también ya envuelto en `@transaction.atomic` + `with transaction.atomic()` interno.
- El modelo `inventario` ([praxsa_manager/product/models.py:119-132](praxsa_manager/product/models.py:119)) define `to_install` como `DecimalField` (línea 123) sin ningún `CheckConstraint` ni `MinValueValidator` que impida valores negativos a nivel de BD o de validación de modelo — confirmado por `grep -n "CheckConstraint" praxsa_manager/product/models.py` (sin resultados) y por lectura completa del bloque `class inventario(models.Model)`.
- El proyecto usa Postgres real en `settings.py` ([praxsa_manager/praxsa_manager/settings.py:153-160](praxsa_manager/praxsa_manager/settings.py:153)): `ENGINE: django.db.backends.postgresql`. Esto importa porque `select_for_update()` y un test de concurrencia con locks reales solo tienen sentido con un motor que soporte locking de filas (SQLite no lo soporta de forma útil para este escenario).
- No existe ningún test de concurrencia hoy: `grep -rln "TransactionTestCase\|threading" praxsa_manager/product/tests praxsa_manager/product/business` no da resultados. Los tests existentes en `praxsa_manager/product/tests/` (`test_proforma_status_field.py`, `test_invoice_pricing.py`, etc.) usan `django.test.TestCase` (transacción envuelta y rollback por test, no válido para simular dos transacciones concurrentes reales).
- `praxsa_manager/product/tests/helpers.py` ya provee factories reusables para armar el fixture necesario: `create_user_with_token`, `create_sucursal`, `create_model`, `create_car_part`, `create_car_model_part`, `create_window_film`, `create_window_film_reel`, `create_inventario` (acepta `to_install` explícito), `create_full_proforma` — visto en uso en [praxsa_manager/product/tests/test_proforma_status_field.py:30-51](praxsa_manager/product/tests/test_proforma_status_field.py:30). Un test de concurrencia para `reduce_inventory`/`create_work_note` puede reusar este mismo patrón de fixture (stock exacto para una sola operación, dos proformas compitiendo por él).
- La rama de trabajo actual (`claude/inventory-race-condition-abb7c7`) estaba 1 commit detrás de `origin/master` (un commit solo de docs, `7029007`); se actualizó con `git merge origin/master` (fast-forward) antes de investigar, así que este reporte refleja el código de `master` al commit `b8feebb`.

### Hipótesis / supuestos no confirmados
- El backlog sugiere `TransactionTestCase` + threads o "simular con dos transacciones manuales" como opciones para el test de concurrencia — no se confirmó cuál de las dos es más viable en este entorno (p. ej. si el test runner tiene acceso a una BD Postgres real con soporte de conexiones concurrentes desde threads separados, o si hay restricciones de configuración que compliquen `TransactionTestCase`). Esto es una decisión de `delivery-plan`/implementación, no algo que se pueda verificar solo leyendo código.
- No se confirmó si hay otros paths de escritura sobre `inventario.to_install` fuera de `reduce_inventory`/`return_to_inventory` (p. ej. algún ajuste manual desde el admin de Django) que también necesitarían el mismo lock — no se encontró ninguno en `business/`, pero no se auditó el admin completo (`admin_config/`) en busca de escrituras directas al campo.

### Módulos y dependencias relacionadas
- `praxsa_manager/product/business/inventario.py` — contiene los dos métodos a corregir (`reduce_inventory`, `return_to_inventory`).
- `praxsa_manager/product/business/proforma.py` — únicos callers (`create_work_note`, `abrir_proforma`), ya envueltos en `transaction.atomic`.
- `praxsa_manager/product/models.py` — modelo `inventario`, candidato para el `CheckConstraint` opcional del paso 3 del backlog.
- `praxsa_manager/product/tests/helpers.py` — factories a reusar para el fixture del test de concurrencia.
- `praxsa_manager/product/tests/test_proforma_status_field.py` — ejemplo más cercano de test que ejercita `create_work_note` de punta a punta con inventario real.

### Implementaciones similares existentes
No hay ningún uso previo de `select_for_update()` en el proyecto que sirva de patrón a seguir — este sería el primer caso. Sí existe el patrón de envolver operaciones multi-paso en `@transaction.atomic` + `with transaction.atomic()` interno (ya usado en `create_work_note` y `abrir_proforma`), que es la base sobre la que se agregaría el lock de fila.

### Comportamiento actual
`create_work_note` (el flujo de negocio real que dispara la sobreventa) hace, por cada línea de detalle de la proforma: lee con `reduce_inventory` la fila de `inventario` con stock suficiente (`to_install__gte = length_to_reduce`), calcula `to_install - length_to_reduce` en Python, y guarda. Como la lectura no bloquea la fila, si dos requests concurrentes (dos proformas distintas apuntando al mismo stock exacto) ejecutan `create_work_note` casi al mismo tiempo, ambas pueden leer el mismo `to_install` antes de que cualquiera haga `save()`, y ambas pasan la condición `to_install__gte = length_to_reduce` del filtro inicial aunque en conjunto excedan el stock real disponible. El resultado es que `to_install` puede terminar en un valor menor al correcto (potencialmente negativo, ya que no hay `CheckConstraint` que lo impida), es decir, sobreventa: se generaron dos notas de trabajo que reservaron más metros de lámina de los que existían físicamente.

### Restricciones
- `docs/CLAUDE.md`: "Todo cambio de lógica de negocio lleva su test" — aplica directamente, y el propio backlog ya pide el test de concurrencia como parte del fix.
- `docs/CLAUDE.md`: "Cambios pequeños: un objetivo por cambio, pensado para un PR" — el backlog ya divide esto en 2 PRs (test que reproduce la carrera, luego el fix) más un tercero opcional (constraint de BD), consistente con esa regla.
- `docs/CLAUDE.md`: "El dinero se maneja con Decimal, nunca con float" — ya se respeta hoy (`to_install`/`length_to_reduce` son `Decimal`), no debería cambiar con el fix.
- `docs/CLAUDE.md`: "No editar migraciones ya aplicadas; crear migraciones nuevas" — relevante si se decide implementar el `CheckConstraint` opcional del paso 3, que requeriría una migración nueva (siguiente sería `0107_*`, dado que la última es `0106_proforma_header_status.py`).

### Riesgos identificados
- `select_for_update()` requiere estar dentro de una transacción atómica para tener efecto — ya se cumple en ambos callers actuales (`create_work_note`, `abrir_proforma` están decorados con `@transaction.atomic`), pero cualquier fix debe verificar que el lock quede realmente dentro del bloque atómico y no antes/después.
- Escribir un test de concurrencia real que reproduzca la condición de carrera con Postgres implica coordinar threads/conexiones de BD separadas (`TransactionTestCase` cierra la envoltura de transacción por test que usa `TestCase`), lo cual es más delicado de armar correctamente que un test unitario común — riesgo de un test "falso positivo" (que parezca reproducir la carrera pero en realidad no ejercite concurrencia real por errores de sincronización de threads).
- Si se agrega el `CheckConstraint(to_install__gte=0)` opcional del paso 3, hay que confirmar que no existan hoy filas con `to_install` negativo en datos reales/de prueba que romperían la migración al aplicarse (no verificado, es un riesgo a validar antes de esa migración si se decide incluirla).
- El fix toca un flujo de negocio central (creación de notas de trabajo, que es el paso que efectivamente descuenta inventario) — cualquier error en el `select_for_update()` (p. ej. bloquear la query equivocada, o no cubrir el `order_by(...)[:1]` que ya existe en `reduce_inventory`) podría introducir deadlocks o cambiar cuál fila de inventario se elige cuando hay varias candidatas.

### Veredicto de complejidad
**NEEDS_PLAN** — el cambio está acotado a dos métodos de un único archivo (`business/inventario.py`) y no introduce ningún módulo, integración externa, ni decisión de autorización/infraestructura nueva; `select_for_update()` es una técnica estándar de Django que encaja directamente en la estructura `transaction.atomic` que ya existe en los dos callers. No hay una decisión arquitectónica real que tomar (el propio backlog ya especifica la solución técnica), solo secuenciar correctamente el test de concurrencia y el fix — trabajo propio de `delivery-plan`.

## Arquitectura
_Pendiente / No aplica según veredicto_

## Plan
[docs/plans/PLAN-2026-09-25-inventario-select-for-update.md](../plans/PLAN-2026-09-25-inventario-select-for-update.md) (v1).

## Implementación

**Cambios:**
- [praxsa_manager/product/business/inventario.py](../../praxsa_manager/product/business/inventario.py) — agregado `.select_for_update()` a la queryset de lectura en `reduce_inventory` (antes de `.filter(...)`) y en `return_to_inventory` (antes de `.get(...)`). Ambos siguen dentro de las transacciones `@transaction.atomic` ya existentes en `Proforma_Business.create_work_note` y `abrir_proforma` (`praxsa_manager/product/business/proforma.py`) — no se tocó ninguno de los dos callers.
- [praxsa_manager/product/tests/test_inventory_concurrency.py](../../praxsa_manager/product/tests/test_inventory_concurrency.py) (nuevo) — `TransactionTestCase` con dos threads reales (conexiones de BD separadas, sincronizados con `threading.Barrier` al inicio) ejecutando `create_work_note` para dos proformas que compiten por el mismo stock exacto (`to_install = 1.00`, alcanza para una sola). Verifica que exactamente una transacción tiene éxito y la otra falla con `NoHayLaminasDisponibles` ("no hay lamina disponible..."), y que el `inventario.to_install` final es `0.00` (nunca negativo).

**Evidencia de que el test reproduce el bug real (paso 3 del plan):** se revirtió temporalmente el fix (vía `git stash` sobre solo `inventario.py`, sin tocar el test) y se corrió el test 3 veces contra el código anterior — las 3 corridas fallaron mostrando que **ambas** transacciones concurrentes tenían éxito (`{'a': ('ok', ...), 'b': ('ok', ...)}`), confirmando la sobreventa descrita en el backlog. Se restauró el fix inmediatamente después y se dejó el repo limpio (sin el stash).

**Verificación:** `python manage.py test` — 82 tests, todos pasan (incluye el nuevo test de concurrencia). Sin regresiones en `test_proforma_status_field.py` ni en el resto de la suite que ejercita `create_work_note`/`abrir_proforma`.

**Deuda técnica / fuera de alcance (ya documentado en el plan):** `CheckConstraint(to_install__gte=0)` a nivel de BD (paso 3 opcional del backlog) no se implementó — requiere verificar datos existentes antes de una migración, queda para un task separado si se decide perseguirlo.

## Review
_Pendiente_

## Publicación
_Pendiente_
