# TASK-009: Máquina de estados para proforma→instalación→venta→pago (backlog #9)

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Rama:** `claude/proforma-state-machine-186295`
**Pull Request:** [#37](https://github.com/rolion/praxsa-django-panel-admin/pull/37)

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-09-23 17:52 | (nuevo) → INVESTIGATION | Task creado | delivery-investigate |
| 2026-09-23 17:58 | INVESTIGATION → PLANNING | Decisión arquitectónica registrada en ADR-006 | delivery-architect |
| 2026-09-23 18:05 | PLANNING → ENGINEERING | Plan v1 escrito y PR #37 abierto | delivery-plan |
| 2026-09-23 18:32 | ENGINEERING → REVIEW | Implementación completa, verificada localmente (tests + backfill real) | delivery-engineer |
| 2026-09-23 18:43 | REVIEW → PUBLISH | Quality Gate: PASS (3 hallazgos Low, no bloqueantes) | delivery-review |
| 2026-09-23 18:59 | PUBLISH → PUBLISH | PR #37 completo y listo; pendiente aprobación humana (cambio sensible: schema + ADR) | delivery-publish |

## Investigación

### Requerimiento
Ítem #9 del backlog unificado (`docs/integration-and-backlog.md:241-247`): *"Sin máquina de estados para proforma→instalación→venta→pago"*, severidad MEDIO, estado `⬜ PENDIENTE`. Corresponde a `BIZ-04` de `docs/backend-audit.md:509-514`. El backlog ya propone 3 pasos (no es una arquitectura a decidir desde cero, sino una secuencia a validar):

1. Tests de caracterización del flujo actual (sin cambiar comportamiento).
2. Campo `status` explícito con `choices`, poblado en cada transición existente, sin quitar todavía la inferencia por `hasattr`.
3. `CheckConstraint`/validación en `clean()` para invariantes mínimas (p. ej. no `pago` sin `nota_venta.is_close`), migrando el admin a leer el campo persistido.

### Hechos encontrados

**El estado hoy es inferido, no persistido, y depende de 3 booleanos + una cadena de `hasattr()`:**
- `Proforma_Header` no tiene campo `status`. Tiene `is_close` (`BooleanField`, default `False`) — [models.py:163](praxsa_manager/product/models.py:163).
- `Nota_trabajo` tiene su propio `is_close` — [models.py:191](praxsa_manager/product/models.py:191).
- `Nota_Venta` tiene su propio `is_close` — [models.py:255](praxsa_manager/product/models.py:255).
- `pago` tiene `cerrado` (mismo concepto, nombre distinto) — [models.py:281](praxsa_manager/product/models.py:281).
- El "estado visible" en el admin de `ProformaAdmin` se calcula recorriendo relaciones inversas O2O con `hasattr()`, sin tocar ninguno de esos booleanos: `Proforma → Nota_trabajo → Nota_Venta → pago` — [admin_config/proforma_admin.py:96-111](praxsa_manager/product/admin_config/proforma_admin.py:96-111).
- `NotaVentaAdmin.get_estado` infiere un estado distinto ("Pagado"/"No Pagado") con su propia lógica ad-hoc: `hasattr(obj, 'pago') and obj.pago.cerrado` — [admin_config/nota_venta.py:80-85](praxsa_manager/product/admin_config/nota_venta.py:80-85).
- `NotaTrabajoAdmin.get_estado` infiere un tercer estado ("Sí"/"No" de "Finalizado") consultando `Nota_Venta.objects.filter(nota_trabajo=obj)` en vez de `hasattr` — [admin_config/nota_trabajo.py:113-119](praxsa_manager/product/admin_config/nota_trabajo.py:113-119). Es decir, hay **tres implementaciones independientes** de "¿en qué estado está esto?", cada una en el `ModelAdmin` de una entidad distinta, ninguna reusa a la otra.

**Ya existió un campo de estado persistido — se quitó deliberadamente en 2023:**
- La migración `0024_sale_header_sales_status_alter_sale_header_date.py` agregó `sales_status` (choices) al modelo predecesor de `Proforma_Header`.
- La migración `0075_remove_pago_proforma_and_more.py:25-29` (2023-11-03) todavía tiene `sales_status` con choices `[('prof','Proforma'), ('ntra','Nota Trabajo'), ('nove','Nota Venta')]`, default `'prof'`.
- La migración `0076_delete_notaventa_alter_nota_venta_options_and_more.py:24-45` (2023-11-04, **al día siguiente**) elimina `sales_status`, `is_paid`, `is_nota_venta_canceled`, `is_nota_venta_refund` de `Proforma_Header` y los reemplaza por el `is_close` booleano actual, en el mismo commit que crea `Nota_Venta` como modelo aparte.
- `helper/proforma.py:5-12` **todavía define** `self.status = [(prof,'Proforma'), (notra,'Nota Trabajo'), (nov,'Nota Venta')]` y `self.default_status`, pero ningún modelo usa ese choices set — es la definición huérfana de un campo que ya no existe.
- Última migración aplicada en el repo: `0105_alter_pago_registro_contable.py`.

**Hay código muerto que referencia el campo/atributos ya eliminados, y fallaría si se ejecutara:**
- `Proforma_Business.delete_proforma` — [business/proforma.py:27-36](praxsa_manager/product/business/proforma.py:27-36) — lee `proforma.sales_status` (no existe, `AttributeError`) y compara contra `self.helper.req` (tampoco existe en `Proforma_Helper`, sería otro `AttributeError` antes de llegar al primero). Esta acción (`delete_proforma`, definida en `admin_config/proforma_admin.py:236-242`) **no está en `ProformaAdmin.actions`** (línea 81), así que hoy es inalcanzable desde el admin.
- `CarModelPartForm.is_proforma_approved`/`is_proforma_installed` — [Forms/car_model_part.py:20-24](praxsa_manager/product/Forms/car_model_part.py:20-24) — leen `proforma.sales_status` contra `self.proforma_helper.apr`/`.inst`, atributos que no existen en `Proforma_Helper`. Sin llamadores en todo el repo (verificado con grep).
- `ProformaAdmin.actions` (línea 81) incluye la cadena `"create_sales_note"`, pero ese método **no existe en `ProformaAdmin`** — existe en `NotaTrabajoAdmin` ([admin_config/nota_trabajo.py:161-166](praxsa_manager/product/admin_config/nota_trabajo.py:161-166)). Verificado contra `ModelAdmin.get_action()` de Django ([site-packages/django/contrib/admin/options.py:1033-1058](C:/Users/Lion/AppData/Roaming/Python/Python312/site-packages/django/contrib/admin/options.py:1033)): si el string no coincide con un método de la clase ni con una acción global del `admin.site`, `get_action()` retorna `None` y `_get_base_actions()` lo descarta silenciosamente — no rompe el admin, pero es una entrada muerta/confusa en la lista de acciones.

**Las transiciones reales de negocio y quién las dispara hoy:**
1. `Proforma_Header.is_close: False → True` — en `Proforma_Business.create_work_note` ([business/proforma.py:101-103](praxsa_manager/product/business/proforma.py:101-103)), como parte de la acción de admin "crear/actualizar nota trabajo" ([admin_config/proforma_admin.py:260-265](praxsa_manager/product/admin_config/proforma_admin.py:260-265)). También puede volver `True → False` vía `abrir_proforma` ([business/proforma.py:39-58](praxsa_manager/product/business/proforma.py:39-58), acción "abrir proforma"), que además devuelve las láminas al inventario.
2. `Nota_trabajo.is_close: False → True` — en `Proforma_Business.crear_nota_venta` ([business/proforma.py:162-183](praxsa_manager/product/business/proforma.py:162-183)), llamada desde `NotaTrabajoAdmin.create_sales_note` ([admin_config/nota_trabajo.py:161-166](praxsa_manager/product/admin_config/nota_trabajo.py:161-166)). Esta función valida precondiciones a mano: `nota_trabajo.proforma.is_close == False` → excepción; si `sales_type == venta_instalacion`, exige `codigo_garantia` e `instaladar`.
3. `Nota_Venta` se crea en el mismo paso 2 (no hay transición de estado propia en su creación; su `is_close` nace en `False` y no se toca hasta el pago).
4. `pago.cerrado: False → True`, `Nota_Venta.is_close: False → True`, `Proforma_Header.is_close` y `Nota_trabajo.is_close` **reafirmados** a `True` (ya lo eran) — todo en `Pago_Business.cerrar_pago` ([business/pago.py:27-44](praxsa_manager/product/business/pago.py:27-44)), llamada desde la acción "concluir transaccion" de `PagosAdmin` ([admin_config/pagos.py:145-152](praxsa_manager/product/admin_config/pagos.py:145-152)).
5. Camino alterno: `convertir_venta_metro_lineal` ([business/proforma.py:116-160](praxsa_manager/product/business/proforma.py:116-160)) solo se permite si `proforma.is_close == False`, y reemplaza los `Proforma_Detail` existentes.
6. Ninguna transición pasa por `clean()`/`full_clean()` del modelo ni por un `CheckConstraint` a nivel de base de datos — todas las precondiciones son `if`/`raise Exception` sueltos dentro de los métodos de `business/`.

**No hay ningún test que ejercite estas transiciones hoy** (`praxsa_manager/product/tests/`): `test_sucursal_scope_admin.py` cubre exclusivamente filtrado de querysets por sucursal/rol (trabajo de TASK-002); `test_invoice_pricing.py` cubre cálculo de precio (TASK-005); `test_public_catalog_endpoints.py` cubre endpoints públicos (TASK-006); `test_smoke.py` es smoke test genérico. Ningún archivo crea un `Nota_trabajo`, `Nota_Venta` o `pago` para verificar `create_work_note`, `crear_nota_venta`, `cerrar_pago` o `abrir_proforma`.

### Hipótesis / supuestos no confirmados
- No se confirmó **por qué** se eliminó `sales_status` en la migración 0076 (2023-11-04) — no hay commit message ni ADR de esa época en el repo que lo explique; se infiere del propio diff (se introdujo `Nota_Venta` como modelo separado el mismo día) que el equipo decidió modelar el flujo con relaciones O2O entre entidades en vez de un enum plano, pero esto no está documentado.
- No se confirmó si `PagosForm`/`nota_venta_form.py` o el JS de admin (`sales_event.js`, `nota_trabajo.js`) imponen alguna validación de secuencia adicional en el cliente (no se abrieron esos archivos en esta investigación); si la hubiera, sería una capa más de "estado" implícito a reconciliar.
- No se confirmó si algún reporte (`report_daily_sell.py`, `report_utilidad.py`, `reporte_proforma.py`, `report_nota_trabajo.py`) depende del **timing exacto** de cuándo se setea cada `is_close`/`cerrado` (p. ej. reportes de "ventas del día" que filtren por el momento en que `pago.cerrado` se vuelve `True`); un campo `status` con historial de timestamps podría cambiar sutilmente ese filtrado si no se preservan los campos de fecha existentes.
- La pregunta de negocio ya señalada en `docs/integration-and-backlog.md:301` y `docs/backend-audit.md:616` sigue sin respuesta: *¿existe una regla de negocio formal para las transiciones proforma→instalación→venta→pago, o se decide caso a caso por el personal?* Esto determina si las invariantes propuestas en el paso 3 del backlog (p. ej. "no `pago` sin `nota_venta.is_close`") son correctas o demasiado estrictas para excepciones operativas reales.

### Módulos y dependencias relacionadas
- **Modelos** (`praxsa_manager/product/models.py`): `Proforma_Header`, `Nota_trabajo`, `Nota_Venta`, `pago` — los 4 puntos que hoy cargan el estado de forma fragmentada.
- **Business** (`praxsa_manager/product/business/`): `proforma.py` (`create_work_note`, `abrir_proforma`, `crear_nota_venta`, `convertir_venta_metro_lineal`, `delete_proforma` muerto, `create_nota_venta_pago` muerto — ver BIZ-03 en backend-audit), `pago.py` (`cerrar_pago`).
- **Admin** (`praxsa_manager/product/admin_config/`): `proforma_admin.py`, `nota_trabajo.py`, `nota_venta.py`, `pagos.py` — cada uno con su propio `get_estado`/`has_change_permission` ad-hoc que tendría que migrar a leer el campo nuevo si se agrega.
- **Helper**: `helper/proforma.py` (`Proforma_Helper.status`/`default_status`, huérfanos, candidatos naturales a reusar o reemplazar).
- **Forms**: `Forms/car_model_part.py` tiene los dos métodos muertos que referencian el viejo `sales_status`.
- **Migraciones**: última aplicada es `0105_alter_pago_registro_contable.py`; cualquier campo nuevo necesita una migración `0106_...`.
- El frontend Angular (`proforma/src/`) **no consume ningún estado de proforma hoy** más allá del campo `status` que el modelo `Invoice` envía y el backend descarta en silencio (`docs/integration-and-backlog.md:38-48`, sección 1.5) — no es una dependencia directa de este backlog #9, pero es la misma brecha conceptual del lado frontend y ya está registrada como pregunta de negocio abierta separada (línea 303).

### Implementaciones similares existentes
- No hay un patrón de "máquina de estados" ya implementado en otra parte del código que este cambio debería seguir — es, de hecho, el segundo intento: el primero (`sales_status` con choices) se implementó y se removió en 2023 a favor de la inferencia actual por relaciones O2O.
- El único precedente de "constraint a nivel de negocio" parcialmente centralizado es `pago.Meta.constraints` con un `UniqueConstraint` condicional sobre `registro_contable` ([models.py:286-293](praxsa_manager/product/models.py:286-293)) — muestra que el proyecto sí usa `CheckConstraint`/`UniqueConstraint` de Django en al menos un lugar, como referencia de estilo para el paso 3 del backlog.

### Comportamiento actual
El flujo de negocio (`docs/CLAUDE.md`: "el cliente ... genera una proforma... luego va a la sucursal y se inicia la instalación... pago de proforma") se implementa hoy como una cadena de relaciones `OneToOne` opcionales que se van creando secuencialmente vía acciones de admin distintas (una por cada `ModelAdmin`), cada una con sus propias validaciones `if/raise Exception` sueltas en `business/`. No existe un objeto o campo único que represente "el estado de esta proforma"; existe únicamente la presencia/ausencia de registros relacionados (`Nota_trabajo`, `Nota_Venta`, `pago`) y 4 booleanos (`is_close` × 3 + `cerrado` × 1) que dos de esas transiciones vuelven a escribir de forma redundante (`cerrar_pago` reafirma `is_close=True` en `proforma` y `nota_trabajo`, que ya estaba en `True` desde pasos anteriores).

### Restricciones
- `docs/CLAUDE.md`: cambios pequeños con un objetivo por PR; no editar migraciones ya aplicadas (crear nuevas); todo cambio de lógica de negocio lleva su test; antes de cambios que afecten varios archivos, proponer un plan y esperar confirmación — este ítem toca modelos + 4 `business/` + 4 `admin_config/` + helper, así que aplica de lleno la regla de "proponer plan antes".
- El propio backlog (`docs/integration-and-backlog.md:243`) ya exige que el paso 1 sean tests de caracterización **antes** de agregar restricciones, "para no romper flujos legítimos existentes" — reconoce implícitamente que hoy pueden existir secuencias fuera de lo esperado en datos de producción (p. ej. `pago` creado sin que `nota_venta.is_close` fuera `True` en ese momento, dado que hoy nada lo impide).
- Dinero: cualquier cambio en este flujo debe seguir usando `Decimal` (ya se cumple en los modelos tocados).

### Riesgos identificados
- **Repetir el mismo diseño que ya se abandonó**: si el campo nuevo se modela igual que el viejo `sales_status` (un enum plano en `Proforma_Header` con valores `Proforma`/`Nota Trabajo`/`Nota Venta`), no queda claro cómo representaría el estado de `pago` (hoy vive en un modelo distinto) sin repetir el mismo problema que llevó a separarlo en 2023 — este es exactamente el tipo de decisión que `delivery-architect` debería resolver explícitamente, no asumir.
- **Tres `get_estado()` independientes** (`ProformaAdmin`, `NotaVentaAdmin`, `NotaTrabajoAdmin`) tendrían que migrar todos a leer el mismo campo/fuente de verdad para que el cambio tenga sentido; hacerlo a medias dejaría inconsistencias visibles en el admin.
- **Datos existentes en producción**: si ya hay proformas/notas/pagos creados fuera de la secuencia esperada (nada lo impide hoy), un `CheckConstraint` nuevo podría fallar al aplicarse o al guardar esos registros existentes — de ahí que el backlog explícitamente pida caracterizar antes de restringir.
- **Cero cobertura de test actual** sobre las 4 transiciones reales — cualquier refactor aquí es alto riesgo sin la red de seguridad del paso 1.
- Código muerto que referencia el concepto de estado anterior (`sales_status`, `helper.req`, `helper.apr`, `helper.inst`, la acción `create_sales_note` mal listada) puede confundir a quien implemente esto si no se identifica como muerto antes de empezar (ya documentado arriba con evidencia).

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — el cambio toca un campo persistido nuevo en el modelo central del dominio (`Proforma_Header`, y potencialmente `Nota_Venta`/`pago`), migra código en 4 `ModelAdmin` distintos y 2 módulos `business/`, y — el factor decisivo — es un segundo intento sobre un diseño que el propio equipo implementó y removió en 2023 sin documentar por qué. Elegir cómo modelar el estado (¿un enum en `Proforma_Header` como antes? ¿un campo por relación? ¿una tabla de transiciones?) y qué invariantes son seguras de imponer dado que no hay constraint hoy, es una decisión arquitectónica real, no un detalle de implementación — encaja directamente en los indicadores "cambios importantes de base de datos", "impacto en múltiples módulos" y "decisión que puede generar deuda técnica importante" que definen cuándo interviene `delivery-architect`.

## Arquitectura

**[ADR-006: Campo `status` persistido en `Proforma_Header`, escrito explícitamente en cada transición existente](../adr/ADR-006-proforma-status-field.md)**

Resumen de la decisión:
- Un solo campo `status` (`CharField` + `choices`, 4 valores: `proforma`/`nota_trabajo`/`por_cobrar`/`finalizado`) en `Proforma_Header` — no un campo por modelo, y no se reintroduce `sales_status` tal como era en 2023 (ese diseño nunca cubrió el estado de pago).
- Un único método de recálculo (`refresh_status()`, reimplementa la misma lógica de `hasattr()` que ya usa `ProformaAdmin.get_estado`) llamado explícitamente al final de las 4 transiciones existentes (`create_work_note`, `abrir_proforma`, `crear_nota_venta`, `cerrar_pago`) — no asignación manual del string en cada sitio, para no repetir el riesgo de desincronización que motivó parte de la investigación.
- La inferencia por `hasattr()` en el admin **no se quita** en este alcance; sirve de referencia para tests de equivalencia contra `status`.
- Requiere una migración de datos (`RunPython`) que recalcule `status` para las filas ya existentes, no solo un default estático.
- Las `CheckConstraint`/validación de invariantes (paso 3 del backlog) quedan **explícitamente diferidas**: dependen de la pregunta de negocio sin responder sobre si existe una regla formal de transición. Este ADR solo entrega el campo observacional.
- No se agrega ninguna librería de máquina de estados (evita nueva dependencia no autorizada y sobreingeniería para un pipeline lineal de 4 estados).
- Limpieza del código muerto encontrado en la investigación (`sales_status` residual, acción `create_sales_note` mal referenciada, métodos muertos en `car_model_part.py`) queda fuera de alcance de este ADR — es un cambio independiente de bajo riesgo.

## Plan

[PLAN-2026-09-23-proforma-status-field.md (v1)](../plans/PLAN-2026-09-23-proforma-status-field.md)

Resumen: campo `status` en `Proforma_Header` + método único `Proforma_Business.refresh_status()` llamado desde las 4 transiciones existentes + migración `0106` con backfill de datos existentes + tests de equivalencia contra `ProformaAdmin.get_estado()`. Sin E2E (cambio 100% backend/admin). Constraints e migrar el admin a leer el campo quedan fuera de alcance (ver `## Out of scope` del plan).

## Implementación

Implementado según [PLAN-2026-09-23-proforma-status-field.md (v1)](../plans/PLAN-2026-09-23-proforma-status-field.md) / [ADR-006](../adr/ADR-006-proforma-status-field.md). PR [#37](https://github.com/rolion/praxsa-django-panel-admin/pull/37).

### Resumen de lo implementado
- `Proforma_Header.status` (choices, default `'proforma'`) — [models.py:164](../../praxsa_manager/product/models.py).
- `Proforma_Helper`: repurpose de `status`/`default_status` (huérfanos) a los 4 valores nuevos — [helper/proforma.py](../../praxsa_manager/product/helper/proforma.py).
- `Proforma_Business.refresh_status()` — replica la misma lógica y el mismo orden que `ProformaAdmin.get_estado` — [business/proforma.py](../../praxsa_manager/product/business/proforma.py).
- Llamadas a `refresh_status()` desde `create_work_note`, `abrir_proforma`, `crear_nota_venta` (`business/proforma.py`) y `cerrar_pago` (`business/pago.py`), tal como especifica el plan.
- Migración `0106_proforma_header_status.py`: `AddField` + `RunPython` de backfill sobre modelos históricos, con manejo de excepción por fila.
- Tests nuevos: `tests/test_proforma_status_field.py` (7 casos).

### Desvío del plan encontrado durante la implementación (documentado, no escalado — ver criterio abajo)
El plan listaba 4 transiciones (`create_work_note`, `abrir_proforma`, `crear_nota_venta`, `cerrar_pago`) como "cada transición existente". Al implementar se encontró una **quinta**: `Orden_Trabajo_Business.delete_work_note` ([business/orden_trabajo.py:61-88](../../praxsa_manager/product/business/orden_trabajo.py)) — invocada desde `NotaTrabajoAdmin.delete_queryset` al borrar una nota de trabajo — es el único camino existente que **remueve** la relación `proforma↔nota_trabajo` (a diferencia de `abrir_proforma`, que solo reabre el formulario sin borrar nada). Sin sincronizar `status` ahí, el campo quedaría permanentemente desactualizado (`'nota_trabajo'`) después de borrar la nota, violando el criterio de aceptación "`status` coincide con `get_estado()` en todo momento del ciclo". Se agregó la llamada a `refresh_status()` en ese método (con `proforma.refresh_from_db()` previo, necesario porque `work_note.delete()` no limpia el caché en memoria de la relación inversa ya cacheada). No se marcó `PLAN_UPDATE_REQUIRED` porque no cambia arquitectura, dependencias ni nivel de riesgo — extiende el mismo mecanismo ya diseñado a un caso que el propio objetivo del plan ("sincronizado explícitamente en cada transición real de negocio") ya implicaba cubrir.

También se corrigió una afirmación del plan: "Expected behavior" decía que `abrir_proforma` revertía `status` a `'proforma'`. Verificado que **no es así**: `abrir_proforma` no borra la `Nota_trabajo` existente, así que `status` correctamente se queda en `'nota_trabajo'` tras reabrir (igual que ya hace `get_estado()` hoy) — el diseño de `refresh_status()` (replicar la misma lógica de `get_estado`) ya produce el resultado correcto por construcción; solo la prosa del plan estaba equivocada sobre el resultado esperado. Test correspondiente ajustado y con comentario explicando el porqué.

### Verificación propia (no reemplaza el Quality Gate de delivery-review)
- `python manage.py test`: 53/53 en verde (46 preexistentes + 7 nuevos), sin regresiones.
- `python manage.py makemigrations --check --dry-run`: sin cambios pendientes.
- Migración `0106` aplicada contra la base de desarrollo real (Postgres local): backfill sobre 25 `Proforma_Header` existentes, comparado 1 a 1 contra `ProformaAdmin.get_estado()` — 0 discrepancias.

### Deuda técnica / fuera de alcance (sin resolver, según ADR-006)
- `CheckConstraint`/validación de invariantes de transición.
- Migrar `ProformaAdmin.get_estado`, `NotaVentaAdmin.get_estado`, `NotaTrabajoAdmin.get_estado` a leer `status` en vez de recalcular por `hasattr()`.
- Limpieza del código muerto ya identificado en la investigación (`sales_status` residual en `business/proforma.py:28`/`Forms/car_model_part.py:20-24`, entrada `"create_sales_note"` mal referenciada en `ProformaAdmin.actions`) — no tocado, cambio independiente.
- Nota colateral (no es un hallazgo nuevo del backlog, solo una observación hecha al verificar `abrir_proforma`): ese método no valida que la proforma no tenga ya una `Nota_Venta`/`pago` antes de "reabrirla" — podría, en teoría, reabrirse una proforma ya finalizada. Comportamiento preexistente, no introducido ni agravado por este cambio; se deja constancia por transparencia, sin acción tomada.

## Review

**Veredicto: PASS.** PR [#37](https://github.com/rolion/praxsa-django-panel-admin/pull/37).

Nota de aislamiento: esta revisión corrió en la misma sesión de Claude Code que implementó el código (limitación procedimental, no real — ver detalle en `## Review` del PR). Se mitigó reconstruyendo contexto solo desde artefactos en disco y re-ejecutando cada verificación de forma independiente: suite completa (53/53 OK, corrida dos veces), rollback + reaplicación real de la migración `0106` sobre la base de desarrollo, backfill re-verificado 1 a 1 contra `ProformaAdmin.get_estado()` (0 discrepancias sobre 25 filas reales), y relectura directa del código fuente de `abrir_proforma` para confirmar de forma independiente la corrección más consecuente que hizo `delivery-engineer`.

3 hallazgos, todos **Low**, ninguno bloqueante:
- [REV-2026-09-23-001](../reviews/REV-2026-09-23-001-orden-trabajo-file-not-in-plan-scope.md) (PLAN) — `business/orden_trabajo.py` tocado fuera de lo declarado en el plan v1 (justificado, pero el plan no se versionó a v2).
- [REV-2026-09-23-002](../reviews/REV-2026-09-23-002-backfill-n-plus-1.md) (IMPLEMENTATION) — backfill de la migración sin `select_related`, N+1 de impacto bajo dado el volumen actual.
- [REV-2026-09-23-003](../reviews/REV-2026-09-23-003-adr-plan-abrir-proforma-narrative-incorrect.md) (ARCHITECTURE) — ADR-006 y el plan describen incorrectamente el resultado de `abrir_proforma`; el código y los tests ya son correctos, solo el texto de la decisión quedó desactualizado.

Verificaciones no ejecutadas (no por omisión, sino porque las herramientas no están instaladas en el proyecto — declarado explícitamente, no un PASS silencioso): lint (`flake8`/`ruff`), type-checking (`mypy`), security (`bandit`/`safety`). Frontend/E2E no aplican (diff no toca `proforma/`).

## Publicación

**Estado: Listo para aprobación humana.** PR [#37](https://github.com/rolion/praxsa-django-panel-admin/pull/37), descripción completa (Summary, Changes, Testing, Architecture decisions, Related plan/ADRs, Review, Known limitations).

Verificado antes de publicar:
- `git status` limpio, sin nada pendiente de comitear.
- `HEAD` coincide exactamente con el último commit revisado por `delivery-review` (sin commits nuevos sin revisar).
- Diff completo (`git diff origin/master...HEAD --name-only`) corresponde íntegramente al plan + hallazgos ya documentados — sin archivos temporales, sin `.env`/credenciales, sin cambios fuera de lo evaluado por el review.

**No se mergea en esta invocación.** Este task tiene ADR (ADR-006) y modifica el esquema de la tabla central del dominio (`Proforma_Header`) — es un cambio sensible según las reglas de este flujo, así que requiere aprobación humana explícita en el chat antes de considerarlo listo para merge, independientemente del `PASS` de `delivery-review`. `**Etapa actual:**` se mantiene en `PUBLISH` hasta esa aprobación.
