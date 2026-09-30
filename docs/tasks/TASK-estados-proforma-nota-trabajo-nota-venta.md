# TASK-estados-proforma-nota-trabajo-nota-venta: Revisar y reorganizar estados y transiciones de Proforma, Nota de Trabajo y Nota de Venta

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-estados-proforma-nota-trabajo-nota-venta
**Pull Request:** [#51](https://github.com/rolion/praxsa-django-panel-admin/pull/51)

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-09-30 01:13 UTC | (nuevo) → INVESTIGATION | Task creado | delivery-investigate |
| 2026-09-30 01:19 UTC | INVESTIGATION → ARCHITECTURE (via DESIGN) | Diseño de UX resuelto en DDR (vocabulario unificado de estados, estado global derivado, acción "Marcar trabajo terminado", pantallas nuevas de Nota de Venta y modal de pago); veredicto NEEDS_ARCHITECTURE exige definir el modelo de estados, transiciones en servidor, migración de datos y endpoints | delivery-design |
| 2026-09-30 01:25 UTC | ARCHITECTURE → PLANNING | Decisiones tomadas: estado explícito por documento con servicio único de transiciones, nota de venta creada con la nota de trabajo, migración reversible con backfill (acordado con el usuario), endpoints de acción y de lectura con permisos Django estándar; sin anticipos | delivery-architect |
| 2026-09-30 02:10 UTC | PLANNING → ENGINEERING | Plan v1 escrito y PR abierto; queda pendiente de aprobación humana del plan antes de implementar. Permisos por grupo indicados por el usuario incorporados (Admin/Caja/Vendedor: add_pago, delete_pago; Admin/Almacen: change_proforma_header, change_nota_trabajo) | delivery-plan |

## Investigación

### Requerimiento
Buscar en `praxsa_manager` cuáles son los estados de una proforma, nota de trabajo y nota de venta, y qué acciones cambian esos estados. Evaluar si es un buen manejo de estados y si se puede mejorar.

Hipótesis de negocio del usuario: hoy, al aprobar la proforma se crea la nota de trabajo, al terminar el trabajo se crea la nota de venta ("nota de pago") y al pagarse se finaliza el flujo. El usuario cree que se puede reorganizar y que la nota de venta podría crearse **junto con la nota de trabajo**, en estado "por cobrar". Pide una propuesta de tabla de estados y transiciones.

### Hechos encontrados

**Dónde vive cada "estado" (no hay un estado explícito por documento; hay 4 mecanismos mezclados):**
- `Proforma_Header.status` (CharField, 4 valores: `proforma`, `nota_trabajo`, `por_cobrar`, `finalizado`) — `praxsa_manager/product/models.py:184`, valores en `helper/proforma.py:10-19`.
- `Proforma_Header.is_close` (bool) — `models.py:183`; `Nota_trabajo.is_close` — `models.py:212`; `Nota_Venta.is_close` — `models.py:276`; `pago.cerrado` — `models.py:302`; `Proforma_Header.is_delete` (bool, borrado lógico) — `models.py:181`.
- `Nota_trabajo` y `Nota_Venta` **no tienen campo `status`**; su estado se infiere de `is_close` y de la existencia del documento siguiente (`hasattr(...)`).

**`Proforma_Header.status` se calcula, no se transiciona:** `Proforma_Business.refresh_status` (`business/proforma.py:30-50`) recalcula por existencia de relaciones: sin `nota_trabajo` → `proforma`; con NT → `nota_trabajo`; con `nota_venta` → `por_cobrar`; con `pago` → `finalizado`. La misma lógica está duplicada en `ProformaAdmin.get_estado` (`admin_config/proforma_admin.py:96-109`) y en la migración `0106_proforma_header_status.py:10-32`. El valor es "observacional" según el comentario de la migración (`0106…:28-31`) y el test `tests/test_proforma_status_field.py` fija que el campo persistido coincida con `get_estado` (`:62-148`).

**Acciones que cambian estado hoy (todas por Django Admin salvo la marcada):**

| Acción | Dónde | Efecto en estado |
|---|---|---|
| Crear proforma | admin `ProformaAdmin` / API `ProformaListCreateView` (`custom_views/ordenes_admin.py:63`) | `status='proforma'` (default), `is_close=False` |
| "crear/actualizar nota trabajo" | `proforma_admin.py:248-253` → `Proforma_Business.create_work_note` (`business/proforma.py:98-140`); **también API** `ProformaGenerateNotaView` (`ordenes_admin.py:121-150`) | Descuenta inventario (`:114-119`), `proforma.is_close=True` (`:127`), crea/actualiza `Nota_trabajo` (`orden_trabajo.py:110-137`, `entrada_vehiculo=now`), `status→nota_trabajo` (`:130`) |
| "abrir proforma" | `proforma_admin.py:232-238` → `abrir_proforma` (`business/proforma.py:63-84`) | Devuelve inventario, `is_close=False`; la `Nota_trabajo` **no se borra**, `status` queda `nota_trabajo` (test `test_proforma_status_field.py:87-101`). Solo verifica `proforma.is_close` (`:65`), no verifica si ya existe nota de venta |
| Editar NT (instalador, garantía, salida, observaciones) | API `NotaTrabajoDetailView` PATCH (`ordenes_admin.py:203-224`) | Sin cambio de estado; bloqueado si `nota.is_close` o ya tiene `nota_venta` (`:222`) |
| "crear nota venta" | admin `NotaTrabajoAdmin.create_sales_note` (`admin_config/nota_trabajo.py:160-166`) → `crear_nota_venta` (`business/proforma.py:201-223`) | Exige `proforma.is_close` (`:202`); si `venta_instalacion` exige `codigo_garantia` e `instaladar` (`:204-208`); crea `Nota_Venta` con `total = total_price - discount` (snapshot, `:213`); `nota_trabajo.is_close=True` (`:218`); `status→por_cobrar`. **No existe endpoint API ni pantalla del panel para esto.** |
| "Gestionar Pago" | `nota_venta.py:123-130` → alta de `pago` (`pagos.py:88-96`) con `cerrado=False` | Crea el `pago` (1:1 con `Nota_Venta`, `models.py:288`). **No llama a `refresh_status`** |
| "concluir transaccion" | `pagos.py:145-153` → `Pago_Business.cerrar_pago` (`business/pago.py:29-47`) | `pago.cerrado=True`, `nota_venta.is_close=True`, `proforma.is_close=True`, `nota_trabajo.is_close=True`, `refresh_status` → `finalizado` |
| Eliminar proforma | `ProformaAdmin.delete_queryset` (`proforma_admin.py:199-222`) | `is_delete=True`; bloqueado si ya existe NT (`:203-209`) |
| Eliminar NT | `NotaTrabajoAdmin.delete_queryset` → `delete_work_note` (`orden_trabajo.py:74-109`) | Bloqueado si existe nota de venta (`:77-79`); si no, borra la NT, devuelve inventario, `proforma.is_close=False`, `refresh_status → proforma` |
| Convertir a metro lineal | `proforma_admin.py:240-246` → `convertir_venta_metro_lineal` (`business/proforma.py:143-188`) | Solo cambia `sales_type`; requiere `is_close=False` |

**Inconsistencias verificadas entre definiciones de "estado / terminado / pagado":**
- `ProformaAdmin.get_estado` muestra **"Finalizado" apenas existe un `pago`** (`proforma_admin.py:106`), aunque `pago.cerrado=False`. Como `refresh_status` solo se llama en `cerrar_pago` (`pago.py:44`) y no al crear el pago (`pagos.py:88-96`), el `status` persistido sigue en `por_cobrar` hasta "concluir transaccion" → **el campo persistido y el admin pueden divergir** entre crear el pago y cerrarlo (el test de paridad `test_proforma_status_field.py:127-142` no cubre ese intervalo — ver hipótesis).
- `NotaVentaAdmin.get_estado` usa otra regla: "Pagado" solo si `pago.cerrado` (`nota_venta.py:80-84`).
- `NotaTrabajoAdmin.get_estado` muestra columna "Finalizado" = existe `Nota_Venta` (`nota_trabajo.py:113-119`); la API igual: `is_finalizada = hasattr(obj,'nota_venta')` (`serializer/ordenes_serializer.py:307-308`) y el panel lo rotula "Finalizado"/"En ejecución" (`panel_admin/src/app/ordenes/notas-trabajo/nota-trabajo-view.component.ts:51`). Es decir, "Finalizado" significa "facturada" en la NT pero "pagada" en la proforma.
- `is_close` significa cosas distintas: en proforma = "tiene NT / inventario descontado" (`proforma.py:127`); en NT = "tiene nota de venta" (`:218`); en `Nota_Venta`, proforma y NT se pone además en `True` al cerrar el pago (`pago.py:36-43`) — `cerrar_pago` re-escribe los `is_close` de los tres documentos.
- No hay fecha/usuario por transición: `proforma_created_on` es `auto_now=True` (`models.py:168`), o sea se actualiza en cada `save()` (es "última modificación"); `Nota_Venta.created_on` se setea a mano con `datetime.now()` naive (`proforma.py:216`) mientras la NT usa `timezone.now()` (`orden_trabajo.py:120`).
- No existe estado "anulada/cancelada": el único mecanismo es `is_delete` en la proforma, bloqueado desde que existe NT; una NT o una nota de venta no se pueden anular (solo la NT sin venta se puede borrar físicamente).

**Código muerto / roto relacionado a estados:**
- `Proforma_Business.delete_proforma` (`business/proforma.py:52-61`) usa `proforma.sales_status` (campo inexistente en `models.py:164-192`) y `self.helper.req` (inexistente en `helper/proforma.py`), y referencia `e` fuera de un `except` (`:60`); la acción no está registrada en `ProformaAdmin.actions` (`proforma_admin.py:81`).
- `Proforma_Business.create_nota_venta_pago` (`business/proforma.py:301-314`) asigna `paidment.proforma` (campo inexistente en `pago`, `models.py:286-306`).
- `ProformaAdmin.actions` (`proforma_admin.py:81`) lista `create_sales_note` y `print_proforma`; en lo leído (hasta `:254`) solo se ven definidos `open_proforma`, `create_work_note`, `convertir_proforma_metro_lineal` y `delete_proforma` (no se leyó el resto del archivo).

**Restricciones que impactarían mover la creación de la nota de venta al momento de crear la NT (verificado en código):**
- `NotaTrabajoDetailView.perform_update` bloquea PATCH si `hasattr(nota,'nota_venta')` (`ordenes_admin.py:222`) → si la nota de venta nace junto con la NT, la NT quedaría no editable desde el primer instante (instalador/garantía/salida se cargan *después* por PATCH — `NotaTrabajoUpdateSerializer`, `ordenes_serializer.py:351-358`).
- `is_finalizada = hasattr(nota_venta)` (`serializer:307-308`) y el filtro `nota_venta__isnull=False` en `get_finish_nota_queryset` (`orden_trabajo.py:48`) pasarían a ser siempre verdaderos.
- `delete_work_note` bloquea borrar la NT si hay nota de venta (`orden_trabajo.py:77-79`) y `abrir_proforma` no lo contempla (`business/proforma.py:65`).
- `crear_nota_venta` exige garantía e instalador (`:204-208`), datos que hoy se llenan después de crear la NT.
- El total de la nota de venta es un snapshot (`:213`); si la proforma se reabre con `abrir_proforma` y se edita, un `Nota_Venta` ya creado quedaría desactualizado.
- `Nota_Venta.nota_trabajo` y `pago.nota_venta` son `OneToOneField` (`models.py:267, 288`).

**Migraciones:** la última es `0110_inventario_is_active.py` (`praxsa_manager/product/migrations/`); `0106_proforma_header_status.py` introdujo `status` con backfill.

**Frontend:** `panel_admin/src/app/ordenes/ordenes.model.ts:38-40,89` consume `status`, `status_label`, `nota_trabajo_id`, `is_finalizada`; el filtro `?status=` existe en la API (`ordenes_admin.py:91-92`). El panel **no tiene pantallas de nota de venta ni de pago** (no hay ninguna referencia en `panel_admin/src`; hoy solo existen en Django Admin).

### Hipótesis / supuestos no confirmados
- El intervalo "pago creado, aún no cerrado" probablemente deja `status='por_cobrar'` persistido mientras el admin muestra "Finalizado"; no se ejecutó para confirmarlo.
- `PagosForm` (`Forms/pagos.py`) no se leyó: no se confirmó si valida que `monto == nota_venta.total_price` (el admin solo lo deshabilita cuando viene `?nota_venta=` en GET, `pagos.py:55-57`).
- Se supone que `create_sales_note`/`print_proforma` de `ProformaAdmin` están definidos más abajo en el archivo (no se leyó del todo) o son acciones huérfanas.
- No se verificó si hay datos productivos con NT abiertas + nota de venta (necesario para dimensionar un backfill).
- Se supone que para `venta_metro_lineal` el concepto "nota de trabajo" (instalación) aplica poco; `crear_nota_venta` ya lo trata distinto (`:204-208`) pero no se confirmó con negocio.
- No se confirmó si otros consumidores (reportes `admin_config/reporte_proforma.py`, `report_nota_trabajo.py`, PDF) dependen de `is_close`/`status`.

### Módulos y dependencias relacionadas
- Backend: `product/models.py`, `product/helper/proforma.py`, `product/helper/pagos.py`, `product/business/{proforma,pago,orden_trabajo,inventario}.py`, `product/admin_config/{proforma_admin,nota_trabajo,nota_venta,pagos,reporte_proforma,report_nota_trabajo}.py`, `product/custom_views/ordenes_admin.py`, `product/serializer/ordenes_serializer.py`.
- Frontend: `panel_admin/src/app/ordenes/**`.
- ADRs previos relevantes: `docs/adr/ADR-006-proforma-status-field.md` (introdujo `status` derivado), `docs/adr/ADR-modulo-ordenes-proforma-nota-trabajo-*.md`.

### Implementaciones similares existentes
- `Proforma_Header.status` con `choices` + `refresh_status` (`business/proforma.py:30-50`) es el único patrón de estado explícito; no hay máquina de estados ni tabla de transiciones. Las otras entidades del proyecto usan `is_active` para borrado lógico (`almacen_admin.py`, `vehicle_admin.py`).

### Comportamiento actual
Flujo real hoy: Proforma (editable) → *generar NT* (proforma se cierra, inventario se descuenta) → NT se completa por PATCH (instalador, garantía, salida) → *crear nota de venta* desde Django Admin (cierra la NT, congela total) → *Gestionar pago* crea el `pago` → *concluir transacción* cierra pago, nota de venta, NT y proforma. Estados de proforma: `proforma → nota_trabajo → por_cobrar → finalizado` (derivado). Retrocesos posibles: "abrir proforma" (deja NT viva) y borrar NT (solo sin nota de venta). No hay retroceso desde nota de venta/pago.

### Restricciones
- `docs/CLAUDE.md`: no editar migraciones aplicadas; dinero con `Decimal`; cambios de lógica llevan test; cambios multiarchivo requieren plan y confirmación previa.
- Cambiar significados de estado rompe `tests/test_proforma_status_field.py` (paridad con `get_estado`), `tests/test_ordenes_proformas.py`, `tests/test_ordenes_notas_trabajo.py` y los specs del panel (`notas-trabajo.components.spec.ts`, `proforma-form.component.spec.ts`).

### Riesgos identificados
- Triple definición de "pagado/finalizado" (proforma vs nota de venta vs nota de trabajo) → hoy la UI puede mostrar estados contradictorios.
- `abrir_proforma` sin guarda sobre nota de venta y con NT viva puede desalinear inventario/NT/proforma.
- Estado derivado por `hasattr` no permite registrar cancelaciones ni auditar quién/cuándo cambió el estado.
- Migrar datos existentes (backfill de nota de venta para NT ya creadas, o reinterpretar `is_close`) toca dinero y cierre contable (`pago.cerrado`).
- Mover la creación de la nota de venta rompe el bloqueo de edición de la NT (`ordenes_admin.py:222`) y la semántica de `is_finalizada`.
- Cero cobertura de API/panel para nota de venta y pago: cualquier nuevo flujo exige endpoints y pantallas nuevas.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — cambia el modelo de estados de tres entidades con cambio de base de datos (nuevos campos de estado y probable backfill), impacta múltiples módulos (modelos, negocio, admin, API, panel, reportes) y toca lógica de cierre contable/dinero. Hay una decisión que, mal tomada, deja deuda técnica (cuántas fuentes de verdad de estado).

### Diseño requerido
**SI** — el panel hoy no tiene nota de venta ni pago, y cualquier reorganización cambia rótulos, badges y acciones visibles (p. ej. qué significa "Finalizado", botón "Marcar trabajo terminado", "Registrar pago").

### Propuesta preliminar pedida por el usuario (NO vinculante; la decisión formal es de `delivery-architect`)
Ver la tabla de estados/transiciones propuesta en la respuesta de chat de esta investigación; se resume así: un estado explícito por documento (Proforma: `vigente|aprobada|anulada`; Nota de Trabajo: `en_proceso|terminado|cancelada`; Nota de Venta: `por_cobrar|pagada|anulada`), la nota de venta nace con la NT en `por_cobrar`, el pago solo se permite con la NT `terminada`, y el estado global de la orden es un derivado de solo lectura.

## Diseño
- [DDR-estados-proforma-nota-trabajo-nota-venta-estados-y-cobro](../design/DDR-estados-proforma-nota-trabajo-nota-venta-estados-y-cobro.md) — Propuesto. Vocabulario unificado ("Finalizado" = terminado y pagado), badge de estado global derivado en proformas, estado propio en nota de trabajo, nuevas pantallas Nota de Venta + modal "Registrar pago", "Marcar trabajo terminado", comportamiento por estado.
- Pendiente de confirmar con el usuario: ¿se admiten anticipos (cobrar antes de terminar el trabajo)? El DDR asume que no.

## Arquitectura
- [ADR-estados-proforma-nota-trabajo-nota-venta-maquina-de-estados](../adr/ADR-estados-proforma-nota-trabajo-nota-venta-maquina-de-estados.md) — Propuesto. Estado explícito en `Nota_trabajo` y `Nota_Venta`; `Proforma_Header.status` como estado global derivado (`proforma|en_trabajo|por_cobrar|finalizado|anulada`); nota de venta nace con la nota de trabajo; servicio único de transiciones con tabla declarativa; `is_close` queda como legado derivado; migración `0111` con backfill y reverso real. Reemplaza parcialmente ADR-006-proforma-status-field.
- [ADR-estados-proforma-nota-trabajo-nota-venta-api-y-permisos](../adr/ADR-estados-proforma-nota-trabajo-nota-venta-api-y-permisos.md) — Propuesto. 7 endpoints de acción, listado/detalle de notas de venta con alcance por sucursal, monto fijado por servidor, permisos Django estándar, cambio de contrato (`status`, sin `is_finalizada`).
- Decisiones del usuario incorporadas: sin anticipos (hoy tampoco se puede pagar sin nota de venta, aunque `salida_vehiculo` no se validaba; ahora se valida); backfill de notas de venta `por_cobrar` para notas de trabajo abiertas.
- Pendiente para el plan: asignar permisos `add_pago`, `delete_pago`, `change_proforma_header`, `change_nota_trabajo` a los grupos reales (decisión de negocio sobre qué rol cobra, anula y reabre).

## Plan
- [PLAN-2026-09-30-estados-proforma-nota-trabajo-nota-venta](../plans/PLAN-2026-09-30-estados-proforma-nota-trabajo-nota-venta.md) — **v1**. 6 fases (modelo+migración 0111, servicio de transiciones, Django Admin, API, frontend, permisos por grupo y verificación en vivo). E2E Playwright: no corresponde (ver plan).

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
