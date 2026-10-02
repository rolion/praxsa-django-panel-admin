# PLAN-2026-10-02-almacen-permisos-sucursal-filtros (v1)

**Task:** TASK-almacen-permisos-sucursal-filtros
**DDRs relacionados:** [DDR-almacen-permisos-sucursal-filtros-filtros-y-selector-sucursal](../design/DDR-almacen-permisos-sucursal-filtros-filtros-y-selector-sucursal.md)
**ADRs relacionados:** [ADR-almacen-permisos-sucursal-filtros-alcance-inventario](../adr/ADR-almacen-permisos-sucursal-filtros-alcance-inventario.md) (reemplaza parcialmente, para Inventario, a [ADR-modulo-almacen-permisos-rol-frontend](../adr/ADR-modulo-almacen-permisos-rol-frontend.md))

## Objective
Que un usuario solo vea, agregue y edite **inventario** de las sucursales que tiene asignadas (admin: todas), y que el listado de Inventario tenga filtros de lámina y sucursal, con el selector de sucursal fijo cuando el usuario tiene una sola. Bobinas queda fuera por indicación del usuario.

## Context
Ver `docs/tasks/TASK-almacen-permisos-sucursal-filtros.md` (investigación, alcance reducido a Inventario), el DDR (comportamiento visual) y el ADR (alcance en el servidor, filtros, endpoint de sucursales, uso de los `permissions` del login).

## Current behavior
- Listado: `InventarioListView.get_queryset` (`praxsa_manager/product/custom_views/almacen_admin.py:136-147`) usa `get_inventario_queryset_by_role` (`business/inventario.py:25-38`): admin todo; el resto solo `sucursales[0]`. Sin filtros `?sucursal=`/`?window_film=`.
- Detalle/PATCH: `InventarioUpdateView.queryset` sin alcance (`almacen_admin.py:202`); toggle busca por id sin alcance (`:174`); alta acepta cualquier sucursal (`serializer/almacen_serializer.py:118`) y la vista no pasa `context` al serializer (`almacen_admin.py:150`).
- Sucursales para el selector: `GET /product/sucursales` sin alcance (`custom_views/user_admin.py:134-138`).
- Frontend: `canManage = hasGroup('admin')` en `inventario-list.component.ts:35-37` y `inventario-view.component.ts:22-24`; `listInventario` solo acepta `search`/`includeInactive` (`almacen.service.ts:16-30,121-123`); el alta usa `listSucursales()` (`inventario-create.component.ts:41`).
- Verificado vigente al planificar: las rutas, firmas y números de línea de arriba coinciden con el código actual; `AuthService.hasPermission` y `permissions` del login existen (`core/service/auth.service.ts:105-109`, `custom_views/auth_token.py:55-58`).

## Expected behavior
- Admin: ve y opera todo inventario; selector de sucursal con todas las habilitadas.
- Usuario con permiso `add_inventario`/`change_inventario` y N sucursales: ve y opera inventario de sus N sucursales; filas ajenas dan 404 por id y alta en sucursal ajena da 400.
- Sin permiso de escritura: solo lectura de su alcance (como hoy).
- Sin sucursales: lista vacía, sin acciones, mensaje informativo.
- Listado: filtros de lámina y sucursal; con una sola sucursal el select está fijo y deshabilitado.

## Architecture considerations
Resumen del ADR (sin re-derivar):
- **Alcance**: reutilizar `Inventario_Business.get_panel_inventario_queryset` (`business/inventario.py:17-23`) en listado, detalle y toggle; no tocar `get_inventario_queryset_by_role` (lo usa `admin_config/report_storage.py:69`).
- **Escritura**: permiso Django + alcance. Alta valida sucursal con `User_Helper.get_sucursales_in_scope`.
- **Contrato API**: aditivo (`?window_film=`, `?sucursal=`, `GET almacen/sucursales`). Cambios de comportamiento: detalle/PATCH/toggle fuera de alcance → 404 (antes accedían); alta en sucursal ajena o deshabilitada → 400; usuarios con varias sucursales ven todas (antes solo la primera). Frontend y backend se despliegan juntos (el panel usa el endpoint nuevo).
- **Datos**: sin migraciones. **Dinero**: sin cálculos nuevos. **Rendimiento**: filtros sobre el queryset ya con `select_related`; el endpoint de sucursales es una consulta simple.
- **Seguridad**: el alcance se aplica en el servidor en todas las rutas de inventario; el frontend solo oculta/fija controles.
- **Acoplamiento**: `InventarioCreateSerializer` pasa a requerir `request` en el contexto; la única vista que lo usa es `InventarioListView` (se verifica por grep en el paso 1 antes de cambiarlo).

## Proposed solution
Según el ADR: alcance en vistas/serializer con helpers existentes, filtros por query params sobre el alcance, un endpoint `almacen/sucursales`, y en el panel selects de lámina/sucursal servidor-side más visibilidad de acciones por `hasPermission` (no por grupo). Alternativas descartadas (modificar el método legado, permisos por nombre de grupo, filtros en cliente, reutilizar el endpoint de Órdenes, 404 en filtro fuera de alcance, `delete_inventario` separado, sucursales en el login) están en el ADR.

## Files/components affected
**Backend (`praxsa_manager/product/`)**
- `custom_views/almacen_admin.py` — `InventarioListView` (alcance, filtros, `context` en `create`), `InventarioUpdateView` (`get_queryset` con alcance), `InventarioToggleActiveView` (búsqueda dentro del alcance), vista nueva de sucursales en alcance.
- `serializer/almacen_serializer.py` — `InventarioCreateSerializer.validate_sucursal` contra el alcance del usuario.
- `urls.py` — ruta `almacen/sucursales` (junto a `:133-140`).
- `tests/test_almacen_module.py` — tests nuevos y ajuste de los existentes que asumían "solo admin"/sucursal ajena (ver Test strategy).
- Sin cambios en `business/inventario.py` ni en `helper/user.py` salvo que el engineer decida extraer un helper de filtros; no se prevé.

**Frontend (`panel_admin/src/app/almacen/`)**
- `almacen.service.ts` — `ListParams` con `sucursal`/`windowFilm`; método `listSucursalesAlcance()` → `GET almacen/sucursales`.
- `inventario/inventario-list.component.{ts,html}` — filtros, carga con parámetros, bloqueo por una sola sucursal, `canCreate`/`canEdit` por `hasPermission`, mensaje sin sucursales.
- `inventario/inventario-create.component.ts` y su HTML — sucursales desde el endpoint de alcance, preselección y bloqueo con una sola.
- `inventario/inventario-view.component.ts` — `canManage` → permiso de edición.
- Specs: `inventario-list.component.spec.ts`, `inventario-view.component.spec.ts`, `inventario-create.component.spec.ts`, `almacen.service` si existe spec.
- Sin cambios en Bobinas, Láminas ni Precios por sucursal.

## Implementation steps
1. **Backend – vista de sucursales en alcance**: `GET almacen/sucursales` (`IsAuthenticated`, `IsStaffUser`) devolviendo `[{id, name}]` de `get_sucursales_in_scope`; registrar la ruta. Verificar con grep que `InventarioCreateSerializer` solo se usa en `InventarioListView`.
2. **Backend – listado**: cambiar `get_queryset` a `get_panel_inventario_queryset`; agregar `?sucursal=` y `?window_film=` (solo dígitos; intersección con el alcance); mantener `?search=` e `include_inactive`.
3. **Backend – detalle/toggle**: `InventarioUpdateView.get_queryset` y `InventarioToggleActiveView` buscan dentro del alcance (404 fuera). Mantener la verificación explícita de `change_inventario`.
4. **Backend – alta**: pasar `context={'request': request}` y validar `sucursal` contra `get_sucursales_in_scope` (400 en el campo `sucursal`).
5. **Backend – tests** (ver estrategia) y corrida de `python manage.py test product` y `makemigrations --check --dry-run`.
6. **Frontend – servicio**: parámetros nuevos y `listSucursalesAlcance()`.
7. **Frontend – listado**: selects Lámina/Sucursal (opciones: láminas activas y sucursales en alcance), recarga al cambiar, reinicio de paginación, sucursal fija si hay una sola, "Todas mis sucursales"/"Todas las sucursales" en los demás casos, mensaje con cero sucursales; `canCreate` = `hasPermission('add_inventario')`, `canEdit` = `hasPermission('change_inventario')` (Editar y Eliminar/Activar).
8. **Frontend – alta y vista**: selector de sucursal de alcance con preselección y bloqueo; usar el valor crudo del control deshabilitado al enviar; botón Editar de la vista según `canEdit`.
9. **Frontend – specs**, `npm test` y `npm run build` en `panel_admin/`.
10. **Verificación manual en vivo** (admin, usuario con 1 sucursal, usuario con 2, usuario sin permisos, usuario sin sucursal): listado, filtros, alta, edición, toggle, intento por URL/API directo a una fila ajena.

## Test strategy
Nivel de integración backend (patrón de `tests/test_almacen_module.py` con `helpers.py`):
- **Listado**: usuario con 2 sucursales ve ambas y no la ajena; sin sucursales → `[]`; admin ve todo; `?sucursal=` propia filtra; `?sucursal=` ajena → `[]`; `?window_film=` filtra; ambos combinados; valor no numérico se ignora; combinación con `?search=` e `include_inactive`.
- **Detalle/PATCH/toggle**: fila propia (con `change_inventario`) OK; fila de sucursal ajena → 404 en GET, PATCH y toggle; sin permiso → 403 aunque sea propia (`almacen` sin escritura).
- **Alta**: sucursal propia con `add_inventario` → 201; sucursal ajena → 400 en `sucursal`; sucursal deshabilitada → 400 (también admin); sin permiso → 403.
- **Sucursales en alcance**: usuario ve solo las suyas habilitadas; admin todas las habilitadas; no staff → 403.
- **Ajuste de tests existentes**: `InventarioTest.test_manage_*`, `InventarioCreateTest.*` y `InventarioToggleActiveTest.*` usan staff con permiso pero inventario/sucursal sin pertenencia al usuario o `create_inventario()` con sucursal ajena; se ajustan para que el usuario sea empleado de la sucursal (o pertenezca al grupo `admin`). `AlmacenRolePermissionTest.test_almacen_role_can_read_but_not_write` ya espera 403 para escritura sin permisos y se mantiene (para inventario ajeno ahora el 403 sigue precediendo al 404 en PATCH/toggle porque el permiso se verifica antes; el engineer lo confirma).
- Regresión: `test_sucursal_scope_admin.py` y reportes no cambian (no se toca el método legado).

Nivel unitario frontend (`TestBed` + `HttpTestingController`, patrón de los specs existentes): listado carga con parámetros al cambiar filtros; una sucursal → select fijo y deshabilitado, varias → "Todas mis sucursales"; cero → mensaje y sin acciones; `canCreate`/`canEdit` según `permissions`; alta con una sucursal envía su id; spec de servicio de parámetros.

**E2E (Playwright): no corresponde.** No hay Playwright instalado ni en `panel_admin/` ni en `proforma/`; el cambio es una lista con filtros y control de acceso verificable con integración de API más specs de componente. El riesgo de integración real (permisos y alcance por sucursal) se cubre con la verificación manual en vivo del paso 10, recomendada antes de fusionar. Si el usuario quiere E2E, requeriría instalar Playwright (dependencia nueva, a confirmar).

## Acceptance criteria
- Un usuario con permisos y sucursales A y B ve, crea y edita inventario de A y B y nunca de C (listado, detalle, PATCH, toggle y alta se rechazan fuera de alcance: 404 o 400 según corresponda).
- Un usuario sin `add/change_inventario` no puede escribir (403) aunque la sucursal sea suya.
- El listado filtra por lámina y por sucursal desde el servidor; un filtro de sucursal ajena no devuelve datos.
- Con una sola sucursal el selector está preseleccionado y deshabilitado en el listado y en el alta; con varias hay "Todas mis sucursales" y sus sucursales; admin ve todas las habilitadas.
- Crear/Editar/Eliminar-Activar se muestran según permiso, no según grupo `admin`.
- Bobinas, Láminas y Precios por sucursal no cambian.
- `python manage.py test product`, `makemigrations --check --dry-run`, `npm test` y `npm run build` en `panel_admin/` pasan; la verificación manual del paso 10 se ejecutó o se declara no ejecutada.

## Risks
- **Regresión de permisos / filtración entre sucursales**: mitigada con tests de cada ruta con un usuario de otra sucursal y verificación manual.
- **Tests existentes** que asumen el comportamiento anterior pueden ocultar fallos si se "arreglan" quitando la comprobación: el ajuste debe dar pertenencia al usuario, no relajar el alcance.
- **Permisos como foto del login**: un cambio de permisos de grupo requiere volver a iniciar sesión para que el frontend muestre/oculte botones; el servidor sí aplica el cambio de inmediato. Sin mitigación en este task.
- **Cambio para admin**: ya no puede crear inventario en sucursales deshabilitadas (aceptado en el ADR).
- **Dos métodos de alcance conviviendo** (legado y `get_panel_inventario_queryset`): deuda aceptada; unificar en otra tarea.
- **Despliegue coordinado**: el panel nuevo usa `almacen/sucursales`; backend y frontend deben desplegarse juntos (sin mitigación adicional; rollback por commit).
- **Sin sucursal asignada y permiso de escritura**: el usuario ve lista vacía y no puede operar; es el comportamiento esperado, no un error.

## Out of scope
- Bobinas (listado, alcance, filtros), Láminas y Precios por sucursal.
- Unificar `get_inventario_queryset_by_role` con `get_panel_inventario_queryset`, y acotar `GET /product/sucursales`.
- Asignar permisos a grupos (`add_inventario`/`change_inventario` a `Almacen` u otros): paso operativo, ver preguntas.
- Permiso `delete_inventario` separado para Eliminar/Activar.
- Actualización de la sesión sin re-login cuando cambian los permisos.

**Preguntas abiertas para el usuario**
1. ¿Eliminar/Activar debe seguir la regla de editar (default del ADR) o quedar solo para admin?
2. ¿Qué grupos deben recibir `add_inventario` y `change_inventario`? ¿Quieres que el task incluya un comando de gestión idempotente (patrón de `management/commands/asignar_permisos_estados.py`) que se los asigne a `Almacen`, o se asignan a mano desde el panel de grupos?
3. ¿Confirmas que admin tampoco debe poder dar de alta inventario en sucursales deshabilitadas?
