# PLAN-2026-10-02-inventario-alcance-sucursal-django-admin (v1)

**Task:** TASK-inventario-alcance-sucursal-django-admin
**DDRs relacionados:** [DDR-inventario-alcance-sucursal-django-admin-sucursales-inactivas-y-filtro-reportes](../design/DDR-inventario-alcance-sucursal-django-admin-sucursales-inactivas-y-filtro-reportes.md)
**ADRs relacionados:**
- [ADR-inventario-alcance-sucursal-django-admin-alcance-lectura-escritura](../adr/ADR-inventario-alcance-sucursal-django-admin-alcance-lectura-escritura.md)
- [ADR-inventario-alcance-sucursal-django-admin-filtro-multisucursal-reportes](../adr/ADR-inventario-alcance-sucursal-django-admin-filtro-multisucursal-reportes.md)

## Objective
Que todo usuario (incluido el grupo admin) vea y opere solo lo de las sucursales asignadas a su cuenta, con el superusuario de Django como única excepción global; y que una sucursal inactiva sea de solo lectura (se ve, no se agrega ni se modifica) en Inventario y Órdenes. Los reportes ganan un filtro de sucursal multiselect.

## Context
Ver `docs/tasks/TASK-inventario-alcance-sucursal-django-admin.md`. La causa del síntoma (el admin de Santa Cruz ve La Paz) es la excepción de grupo en `User_Helper.can_view_all_sucursales`; el resto de la regla (lectura vs. escritura, sucursales inactivas, Django Admin, reportes multiselect) la fijaron el usuario, el DDR y los dos ADR.

## Current behavior
- `helper/user.py:28-29` — `can_view_all_sucursales` = grupo admin; `:31-47` `get_enabled_sucursal_ids` y `get_sucursales_in_scope` filtran siempre por sucursal activa, para leer y para escribir; `:57` `has_assigned_sucursal`.
- Los `get_panel_*` (`business/inventario.py:17-23`, `proforma.py:160-168`, `orden_trabajo.py:36-45`, `pago.py:15-32`) devuelven todo al admin y filtran por sucursales activas al resto.
- Las vistas de escritura parten del objeto con alcance pero no comprueban que la sucursal esté activa: `almacen_admin.py:199-205,234-243`, `ordenes_admin.py:148-151,161-183,266-288,351-356`. `ProformaWriteSerializer.validate_sucursal` no valida en ediciones (`ordenes_serializer.py:162-164`).
- Reportes: `ReporteParamsSerializer.sucursal` único (`reportes_serializer.py:16-21`); `_ventas` valida contra `get_sucursales_in_scope` (`reportes_admin.py:44-60`); `filtrar_pagos(sucursal_id=...)` (`business/reportes.py:117-125`); el panel envía un id o `null` (`reporte-base.ts:31,73-84`).
- Django Admin: métodos `*_by_role` con `sucursales[0]` y `None` (`proforma.py:134-198`, `orden_trabajo.py:16-60`, `pago.py:34-48`, `precio_venta.py`, `inventario.py:25-38`); `InventoryAdmin` muta `self.*` por petición y no acota la sucursal en el alta (`admin_config/inventory.py:43-115`).

## Expected behavior
- Admin con solo Santa Cruz ve y opera únicamente Santa Cruz en Inventario, Órdenes, Pagos, Dashboard y Reportes; admin sin sucursales ve 0 datos; el superusuario ve todo.
- Una sucursal inactiva asignada: se ve (badge "Inactiva"), pero alta, edición, anulación, cobro y cambios de estado devuelven 409 y la UI oculta esas acciones; no aparece en los formularios de alta.
- Reportes: `?sucursales=1,2` además de `?sucursal=`; "Todas" = activas del alcance; multiselect en el panel.
- Django Admin respeta la misma regla (lectura y escritura por objeto).

## Architecture considerations
Resumen de los ADR (no se re-deriva):
- Alcance en un solo lugar (`User_Helper`), dos alcances con nombre (lectura = asignadas; escritura = asignadas y activas), `get_sucursales_in_scope` eliminado para forzar la elección consciente en cada llamador.
- Regla de escritura en la capa de vistas/serializers con un helper único que responde 409; 404 fuera del alcance de lectura. No se toca `Orden_Estado_Business` (sus transiciones no reciben al usuario).
- Contrato API **aditivo**: `sucursal_activa` por fila, `activa` en los catálogos de sucursales, `?sucursales=` nuevo con `?sucursal=` intacto. Lo que cambia para un cliente existente: el admin deja de ver todo, y "Todas" excluye inactivas. Backend y panel se despliegan juntos (el panel nuevo usa los campos nuevos; el panel viejo con el backend nuevo sigue funcionando porque los campos son aditivos).
- Sin migraciones, sin dinero ni `Decimal` nuevo, sin dependencias nuevas (el multiselect usa `NgbDropdown` de `@ng-bootstrap/ng-bootstrap` 20.0.0, ya instalado).
- Rendimiento: `sucursal_activa` sale de relaciones ya cargadas con `select_related` (`sucursal`, `proforma__sucursal`); reportes pasan de `=` a `IN` sobre pocos ids. No se esperan consultas N+1; se verifica con `assertNumQueries` donde ya exista el patrón.
- Rollback: revertir el commit; sin datos persistidos.

## Proposed solution
Cambiar primero el helper y sus consumidores de lectura (que ya pasan por un punto), después añadir el guard de escritura, exponer la bandera de actividad, extender reportes, alinear el Django Admin y finalmente adaptar el panel. Las alternativas descartadas están en los ADR.

## Files/components affected
**Backend** (`praxsa_manager/product/`)
- `helper/user.py` (nuevos métodos, `can_view_all_sucursales`, `has_assigned_sucursal`; se elimina `get_sucursales_in_scope`).
- `business/inventario.py`, `proforma.py`, `orden_trabajo.py`, `pago.py`, `precio_venta.py`, `dashboard.py`, `reportes.py` (alcance de lectura, `filtrar_pagos` con lista, `*_by_role` delegando).
- `custom_views/almacen_admin.py`, `ordenes_admin.py`, `reportes_admin.py`, `dashboard_admin.py` (guard de escritura, catálogos con `activa`, parámetros de reportes).
- `serializer/almacen_serializer.py`, `ordenes_serializer.py`, `instalador_precio_serializer.py`, `reportes_serializer.py` (`sucursal_activa`, validaciones de alta/edición, `sucursales`).
- `utils/exception/` (excepción 409 compartida por Inventario y Órdenes).
- `admin_config/inventory.py`, `report_storage.py`, `proforma_admin.py`, `nota_trabajo.py`, `nota_venta.py`, `pagos.py`, `precio_venta_sucursal.py`, `filtros_reportes.py` y un mixin nuevo de escritura por sucursal.
- `views.py:159` (único consumidor no-admin de un `*_by_role`: comprobar el manejo de `None`).
- Tests: `tests/test_sucursal_scope_admin.py`, `test_inventario_alcance_sucursal.py`, `test_almacen_module.py`, `test_ordenes_scope_permissions.py`, `test_ordenes_*`, `test_reportes_*`, `test_dashboard_*`, `helpers.py` y tests nuevos.

**Frontend** (`panel_admin/src/app/`)
- `almacen/almacen.service.ts`, `almacen.model.ts`, `inventario/*` (list, create, view, edit).
- `ordenes/ordenes.model.ts`, `ordenes.service.ts`, `proformas/*`, `notas-trabajo/*`, `notas-venta/*` (incluido `pago-modal`).
- `reportes/reporte-base.ts`, `reportes.model.ts`, `reportes.service`, `ventas-diarias/*`, `utilidad/*`; componente nuevo del multiselect de sucursales.
- `dashboard/main/main.component.ts` (catálogo con `activa`).

## Implementation steps
Un solo PR, commits por fase. Cada paso termina con tests verdes antes de seguir.

**Fase A — Alcance (backend)**
1. **Helper.** En `helper/user.py`: `can_view_all_sucursales` → `user.is_superuser`; agregar `get_readable_sucursales`/`get_readable_sucursal_ids` y `get_writable_sucursales`/`get_writable_sucursal_ids`; `has_assigned_sucursal` sobre el alcance de lectura; método `is_sucursal_writable(user, sucursal_id)`; eliminar `get_sucursales_in_scope` y `get_enabled_sucursal_ids`. Tests unitarios del helper (superusuario, admin, no admin; 0/1/N sucursales; activa/inactiva).
2. **Excepción y guard de escritura.** Excepción 409 en `utils/exception/` (reemplaza `Conflict` local de `ordenes_admin.py:47` para no duplicarla) y helper de vista `require_sucursal_writable(user, sucursal_id)` con mensaje fijo "La sucursal está inactiva: solo lectura".
3. **Lecturas de la API.** `get_panel_*` de inventario, proforma, nota de trabajo, nota de venta y pago usan el alcance de lectura; `almacen/sucursales` y `ordenes/catalogo/sucursales` devuelven las sucursales de lectura con `activa`; `_sucursal_in_scope_or_404`, `_precios_in_scope`, `dashboard_admin.py:42` y `reportes_admin.py:48` pasan al alcance de lectura; el dashboard usa la misma regla de "Todas = activas".
4. **Altas.** `almacen_serializer.validate_sucursal`, `ordenes_serializer.validate_sucursal` e `instalador_precio_serializer.validate_sucursal` usan el alcance de escritura. En ediciones de proforma, `validate_sucursal` verifica que la sucursal de la instancia sea escribible.
5. **Modificaciones.** Aplicar `require_sucursal_writable` (después del 404 de alcance y del 403 de permiso) a: PATCH y toggle de inventario; PATCH, generar nota y anular de proforma; PATCH, terminar, corregir y anular de nota de trabajo; pago, anular pago y anular de nota de venta.
6. **Bandera `sucursal_activa`.** Campo de solo lectura en `InventarioSerializer`, `ProformaListSerializer` (hereda el detalle), `NotaTrabajoListSerializer` y `NotaVentaListSerializer`, derivado de las relaciones ya cargadas.

**Fase B — Reportes (backend)**
7. `ReporteParamsSerializer.sucursales` (lista de ids por comas, validada) más `sucursal` conservado; `filtrar_pagos` acepta lista (`sucursal_ids`); validación 404 contra el alcance de lectura; "Todas" = activas; `sin_sucursal` = sin ninguna sucursal asignada; campo aditivo `sucursales` en la respuesta.

**Fase C — Django Admin**
8. Los `*_by_role` delegan en los `get_panel_*` (siempre querysets, nunca `None`); revisar `views.py:159` y cada `ModelAdmin` que dependa de `None`.
9. Reescribir `InventoryAdmin` sin mutar `self.*` en `changelist_view` (`get_list_display`, `get_fields`, `get_readonly_fields`) y con `formfield_for_foreignkey` de `sucursal` al alcance de escritura.
10. Mixin de escritura por sucursal (`has_add_permission`, `has_change_permission(obj)`, `has_delete_permission(obj)`) aplicado a los `ModelAdmin` de inventario, proforma, nota de trabajo, nota de venta, pago y precio por sucursal; `ReportStorageAdmin` y los filtros de reportes usan el alcance de lectura.

**Fase D — Panel**
11. Modelos y servicios: `activa` en `OrdenSucursal` y en la sucursal de Almacén, `sucursal_activa` en las filas, `sucursales` en `ReporteFiltros` y en el servicio de reportes.
12. Inventario: badge "Inactiva", botones Editar/Eliminar ocultos y aviso en la vista, altas solo con sucursales activas, aviso "No tienes sucursales activas" y botón de alta oculto si no hay ninguna.
13. Órdenes: lo mismo en listados y detalles de proformas, notas de trabajo y notas de venta (`canEdit`, `canAnular`, `canGenerateNota`, `canCorregir`, `canTerminar`, `canPay`, `canAnularPago` con `&& row.sucursal_activa`); `proforma-form` ofrece solo activas; los filtros de listado muestran inactivas con "(inactiva)".
14. Reportes: componente de multiselect con `NgbDropdown` y casillas en `reporte-base`, `ventas-diarias` y `utilidad`; control `number[]`, por defecto las activas marcadas; texto fijo con una sola sucursal.

**Fase E — Verificación**
15. Corrida completa (`manage.py test product`, `makemigrations --check --dry-run`, specs del panel, `ng build`, `ng lint`) y verificación manual en vivo (ver Test strategy).

## Test strategy
**Backend (`praxsa_manager/product/tests/`, Django `TestCase` con `helpers.py`)**
- Helper: matriz rol × nº de sucursales × actividad (superusuario, admin, almacén/caja/vendedor; 0, 1, 2; activa e inactiva) para lectura y escritura.
- Inventario: admin de una sola sucursal no ve ni toca filas de otra (listado, detalle 404, PATCH 404, toggle 404, alta 400); sucursal inactiva: listado y detalle OK, PATCH/toggle 409, alta 400; admin sin sucursales: 0 filas; superusuario: todo.
- Órdenes: por cada endpoint de escritura (PATCH proforma, generar nota, anular proforma; PATCH nota de trabajo, terminar, corregir, anular; pago, anular pago y anular nota de venta) un caso de sucursal inactiva → 409, uno de otra sucursal → 404, uno normal → éxito; proforma nueva en sucursal inactiva → 400; edición de proforma con la sucursal inactiva → 409.
- Reportes y dashboard: `sucursal`, `sucursales`, ambos, ids ajenos/no numéricos (404), "Todas" con y sin sucursales inactivas, admin sin sucursales (`sin_sucursal=true`, 0 filas).
- Serializers: `sucursal_activa` presente y correcto; catálogos con `activa`.
- Django Admin: `InventoryAdmin` (alta limitada a sucursales escribibles, ausencia de fuga de estado entre peticiones con dos usuarios consecutivos), mixin (`has_change_permission` por objeto), `*_by_role` devuelven querysets y no `None`.
- Regresión: actualizar los tests que suponen "admin ve todo" y un test que verifique que `get_sucursales_in_scope` ya no existe.

**Frontend (Jasmine/`TestBed` + `HttpTestingController`)**
- Specs de los listados, vistas y formularios de Inventario y Órdenes: botones ocultos con `sucursal_activa=false`, badge visible, formularios sin sucursales inactivas, aviso sin sucursales activas.
- Spec del multiselect: marcar/desmarcar, "Todas", envío de `sucursales=1,2`, valor por defecto de activas, una sola sucursal fija.

**E2E: no corresponde.** El proyecto no tiene Playwright y las reglas se prueban en el servidor (integración de API) y en la UI (specs de componentes); lo que ningún test aislado cubre —el recorrido real del panel contra el backend— se cubre con la verificación manual de la fase E con los perfiles: superusuario, admin con 1 sucursal, usuario con 2, usuario con una sucursal inactiva, admin sin sucursales, e intento directo por API a una fila ajena y a una inactiva.

## Acceptance criteria
1. Un admin con solo Santa Cruz no ve ni opera filas de La Paz en Inventario, Proformas, Notas de trabajo, Notas de venta, Reportes ni Dashboard; por id obtiene 404.
2. Un admin sin sucursales ve 0 datos y no puede crear nada; el superusuario ve todo.
3. En una sucursal inactiva asignada, cualquier grupo ve los datos pero toda escritura responde 409 y la UI oculta las acciones; las altas no la ofrecen.
4. `?sucursales=1,2` funciona, `?sucursal=` sigue funcionando, "Todas" = activas, y los ids fuera de alcance dan 404.
5. El panel muestra el multiselect de sucursales en ambos reportes y el badge "Inactiva" donde corresponde.
6. Django Admin: no se puede agregar ni modificar inventario ni órdenes de sucursales ajenas o inactivas, y `InventoryAdmin` ya no comparte estado entre usuarios.
7. `manage.py test product` y `makemigrations --check --dry-run` sin cambios, specs del panel de los módulos tocados en verde, `ng build` y `ng lint` OK; los 13 fallos preexistentes de componentes demo no aumentan.

## Risks
- **Regresión de permisos** al eliminar `get_sucursales_in_scope`: mitigado por los tests de matriz y porque el renombrado rompe la importación de cualquier llamador olvidado.
- **Tests existentes que asumen admin global** (varias suites): se actualizan en el mismo PR; si alguna prueba cubre el comportamiento antiguo a propósito, se reevalúa con el usuario.
- **`None` de los `*_by_role`** podría ser tratado como "sin acceso" por algún `ModelAdmin` o por `views.py:159`; se verifica llamador por llamador (paso 8). Sin mitigación automática si un llamador depende de `None` para otra lógica: se corrige en ese sitio.
- **Cuentas admin sin sucursales dejan de ver datos en producción** (aceptado por el negocio); se documenta que el superusuario es el acceso global.
- **Tamaño del PR** (backend + admin + panel). Se mantiene por commits por fase para poder revisarlo y revertirlo por partes; si el revisor prefiere partirlo, las fases A–B y C–D son separables sin romper el contrato.
- **Botones del panel desactualizados** hasta recargar (el servidor es la autoridad).
- **Calidad de la verificación manual:** `delivery-review` y el engineer no ejecutaron el paso equivalente en el task anterior; aquí es parte de los criterios de aceptación.

## Out of scope
- Módulo Usuarios (`SucursalListCreateView`, gestión de grupos y sucursales), Láminas, Bobinas, endpoints públicos de catálogo y de la calculadora, `get_user_inventory_window_films`/`get_inventory_window_film_reel_widths`.
- Multiselect en el dashboard y en el Django Admin de reportes.
- Retirar el parámetro `?sucursal=` de reportes.
- Cambios de modelo o migraciones.

**Preguntas abiertas (con el valor por defecto que se aplicará si no hay respuesta):**
1. ¿El superusuario también queda en solo lectura en sucursales inactivas? *Por defecto sí.*
2. ¿Respuesta 409 para "sucursal inactiva"? *Por defecto 409 (403 solo para falta de permiso).*
3. ¿"Todas" en reportes y dashboard = solo activas? *Por defecto sí; las inactivas se marcan a mano.*
4. ¿Se puede dividir el PR si resulta demasiado grande? *Por defecto un solo PR con commits por fase.*

## Dependencias nuevas
Ninguna.
