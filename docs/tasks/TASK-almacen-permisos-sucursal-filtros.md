# TASK-almacen-permisos-sucursal-filtros: Almacén — alcance por sucursal en bobinas e inventario, y filtros de lámina/sucursal

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-almacen-permisos-sucursal-filtros
**Pull Request:** [#66](https://github.com/rolion/praxsa-django-panel-admin/pull/66)

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-02 | (nuevo) → INVESTIGATION | Task creado | delivery-investigate |
| 2026-10-02 | (sin cambio de etapa) | Usuario reduce el alcance: se omite bobinas, solo inventario; veredicto sin cambio; DDR anotado | delivery-design |
| 2026-10-02 | ARCHITECTURE → PLANNING | ADR de alcance por sucursal y filtros de Inventario registrado | delivery-architect |
| 2026-10-02 | PLANNING → ENGINEERING | Plan v1 escrito y PR abierto; queda a la espera de la aprobación humana del plan y de la respuesta a las 3 preguntas abiertas antes de implementar | delivery-plan |
| 2026-10-02 | ENGINEERING → REVIEW | Implementación completa de los pasos 1 a 9 del plan v1; el paso 10 (verificación manual en vivo) queda para review/usuario | delivery-engineer |
| 2026-10-02 | DESIGN → ARCHITECTURE | DDR de filtros y selector de sucursal registrado; veredicto NEEDS_ARCHITECTURE | delivery-design |

## Investigación

### Requerimiento
"En el módulo de almacén, en bobinas e inventario agrega los siguientes: el usuario solo debería poder ver, agregar y editar bobinas en las sucursales que tiene asignadas; el usuario solo debería poder ver, agregar o editar inventario en las sucursales que está asignado. Agrega filtros en las vistas de **bobina** (filtro de lámina, sucursal; si el usuario solo tiene una sucursal, no puede seleccionar otra sucursal) e **inventario** (lámina, sucursal; si el usuario tiene una sucursal no puede seleccionar otra sucursal)."

> **Alcance actualizado (2026-10-02, por indicación del usuario):** se **omite la parte de bobinas**. Este task cubre solo **Inventario**: alcance por sucursal (ver/agregar/editar solo en las sucursales asignadas) y filtros de lámina y sucursal (selector de sucursal fijo si el usuario tiene una sola). Todo lo referido a bobinas más abajo queda como contexto y **fuera de alcance**; la pregunta abierta de bobina global vs. por sucursal ya no bloquea.

### Hechos encontrados

**Bobinas: no pertenecen a ninguna sucursal (fuera de alcance, solo contexto: el selector de bobina del alta de inventario sigue usando el catálogo global)**
- `praxsa_manager/product/models.py:74-88` — `Window_Film_Reel` solo tiene `window_film`, `width`, `length`, `price`, `is_active`. **No tiene FK a `Sucursal`**; es un catálogo global (misma conclusión que `TASK-mejora-inventario-bobinas`).
- `praxsa_manager/product/models.py:141-155` — la relación bobina↔sucursal solo existe a través de `inventario` (FK `sucursal` + FK `bobina`).
- Última migración: `0115_client_car_plate.py` (`praxsa_manager/product/migrations/`).

**Backend actual de bobinas (sin ningún filtro por sucursal)**
- `custom_views/almacen_admin.py:70-86` — `WindowFilmReelListCreateView`: `queryset = Window_Film_Reel.objects.select_related('window_film')`, permisos `_STANDARD_PERMISSIONS` (`:19`: `IsAuthenticated, IsStaffUser, DjangoModelPermissions`). Soporta `?search=` (por nombre de lámina) e `?include_inactive=true`. No hay filtro por lámina ni por sucursal; cualquier staff ve todas.
- `custom_views/almacen_admin.py:89-94` — `WindowFilmReelDetailView` (GET/PATCH) sin alcance; `:97-115` `WindowFilmReelToggleActiveView` valida `change_window_film_reel` pero no sucursal.
- `serializer/almacen_serializer.py:37-53` — `WindowFilmReelSerializer` no expone sucursal alguna.
- `custom_views/bobina.py:8-21` — `BobinaView` legado (`IsAuthenticated`) devuelve un objeto de modelo sin serializar; no figura en `urls.py` para `almacen/` (las rutas de almacén están en `urls.py:133-140`). No se verificó si algo lo consume.

**Backend actual de inventario**
- `custom_views/almacen_admin.py:118-153` — `InventarioListView` (GET lista + POST alta). GET usa `[IsAuthenticated, IsStaffUser]`; POST añade `DjangoModelPermissions` (`:128-131`). `get_queryset` (`:136-147`) aplica `Inventario_Business.get_inventario_queryset_by_role`, `?search=` (lámina o lote) e `include_inactive`. No hay filtro por `?sucursal=` ni `?window_film=`.
- `business/inventario.py:25-38` — `get_inventario_queryset_by_role`: admin ve todo; el resto **solo la primera sucursal** habilitada (`sucursales[0]`, `:31-33`); sin sucursal → `qs.none()`. Ya está señalado como legado en `TASK-mejora-inventario-bobinas` (hecho de `:62` de ese task).
- `helper/user.py:31-47` — `get_enabled_sucursal_ids(user)` (todas las sucursales habilitadas del empleado) y `get_sucursales_in_scope(user)` (admin: todas las habilitadas; resto: las suyas). Es el patrón ya adoptado por Órdenes y Precios por sucursal (`almacen_admin.py:219-227`, `ordenes_admin.py:390-398`).
- `custom_views/almacen_admin.py:149-153` — el `create` usa `InventarioCreateSerializer(data=request.data)` **sin `context`**; `serializer/almacen_serializer.py:118` — `sucursal = PrimaryKeyRelatedField(queryset=Sucursal.objects.all())`: se puede crear inventario en **cualquier** sucursal (incluso deshabilitadas) y no hay verificación de pertenencia del usuario.
- `custom_views/almacen_admin.py:194-216` — `InventarioUpdateView` (GET/PATCH): `queryset = inventario.objects.select_related(...)` **sin alcance por sucursal** (`:202`), de modo que un usuario con `change_inventario` puede leer/editar por id una fila de otra sucursal. `:156-191` `InventarioToggleActiveView` tampoco valida sucursal (`:174`).
- `serializer/almacen_serializer.py:81-93` — `InventarioUpdateSerializer` solo permite `to_install, installed, precio_compra_mtr_lineal, precio_venta_mtr_lineal, nro_lote` (no cambia sucursal/bobina).

**Roles hoy (decisión previa que este pedido cambia)**
- `docs/adr/ADR-modulo-almacen-permisos-rol-frontend.md` (decisión 2 y 6): `admin` = CRUD completo de Láminas/Bobinas/Inventario; `almacen` = solo lectura, "no se le asigna ningún `Permission` de escritura" sobre `Window_Film_Reel`/`inventario`; el frontend oculta Crear/Editar/Eliminar con `hasGroup('admin')`.
- `panel_admin/src/app/almacen/bobinas/bobinas-list.component.ts:51-53` y `inventario/inventario-list.component.ts:35-37` — `canManage` = `authService.hasGroup('admin')`. El botón de alta/edición/eliminar solo se muestra a admin (`inventario-list.component.html:35-43,76-89`).
- `praxsa_manager/product/management/commands/inicializar_datos.py:35` define los grupos `Admin, Almacen, Caja, Vendedor`; `asignar_permisos_estados.py:23` asigna a `Almacen` solo permisos de órdenes. No se encontró (en `management/`) ninguna asignación de permisos de escritura de bobina/inventario al grupo `Almacen` ni a otros grupos no admin.

**Frontend actual**
- `panel_admin/src/app/almacen/almacen.service.ts:86-88,121-123` — `listBobinas`/`listInventario` solo aceptan `search` e `includeInactive` (`:16-30`); no hay parámetros `sucursal` ni `window_film`.
- `bobinas-list.component.ts:41-78` — carga todo y filtra en cliente solo por nombre de lámina; **no hay ningún filtro de sucursal** (la bobina no la tiene). `inventario-list.component.ts:54-66` filtra en cliente por texto libre (lámina, sucursal o lote) sobre `data` ya descargada.
- `inventario-create.component.ts:41-42` — el formulario de alta carga sucursales con `listSucursales()` → `GET /product/sucursales` y bobinas con `listBobinas()`.
- `custom_views/user_admin.py:134-138` — `SucursalListCreateView` devuelve **todas** las sucursales (`Sucursal.objects.all()`), sin alcance por usuario. El endpoint ya alcanzado por usuario es `ordenes/catalogo/sucursales` (`ordenes_admin.py:390-398`, usa `get_sucursales_in_scope`), pero ese vive en el módulo Órdenes.
- `panel_admin/src/app/almacen/almacen.routes.ts:13-24` — sin guards por rol; la barrera real es el backend (ADR de permisos, decisión 7).

**Tests existentes**
- `praxsa_manager/product/tests/test_almacen_module.py` (76 referencias a almacén; clases como `InventarioTest` `:355`, `InventarioCreateTest` `:471`, `InventarioToggleActiveTest` `:625`), `tests/test_sucursal_scope_admin.py:104` (`InventarioBusinessQuerysetByRoleTest`) y `tests/test_inventario_asignacion.py:34`. Los dos primeros prueban hoy el comportamiento "solo admin gestiona / primera sucursal"; este pedido los cambia. No se leyó cada caso.

### Hipótesis / supuestos no confirmados
- **(Resuelta por reducción de alcance: bobinas quedan fuera del task.)** Pregunta que ya no bloquea: como la bobina no tiene sucursal, "ver/agregar/editar bobinas en las sucursales asignadas" admite al menos dos lecturas: (a) bobinas **con inventario** en las sucursales del usuario (derivado vía `inventario`); (b) una pertenencia nueva bobina→sucursal (cambio de modelo). Con (a), una bobina recién creada no tiene inventario y quedaría invisible para quien la creó hasta que exista una fila de inventario; con (b) cambia el catálogo global (hoy compartido por todas las sucursales y usado por `Pricing_Business`, órdenes, calculadora pública y reportes). No se confirmó cuál quiere el negocio.
- Se asume que "el usuario" incluye a roles no admin (p. ej. `Almacen`) a quienes hoy el ADR de permisos les quita escritura; el pedido parece levantar esa restricción *dentro* de su sucursal. No se confirmó si `admin` sigue viendo y editando todo (es lo coherente con `can_view_all_sucursales`, `helper/user.py:28-29`) ni si el permiso de escritura sigue gobernado por `Permission` de Django o pasa a depender solo de la sucursal.
- "Sucursales que tiene asignadas" se asume = `Sucursal.empleado` con `enable_to_install_windows_film=True` (`helper/user.py:31-39`), igual que el resto del panel; no se confirmó que sucursales deshabilitadas deban quedar fuera.
- "Si el usuario solo tiene una sucursal, no puede seleccionar otra": se asume que el filtro de sucursal queda **preseleccionado y deshabilitado** con esa sucursal; con varias, selector libre acotado a las suyas; admin, todas. No se confirmó el comportamiento con 0 sucursales (hoy `qs.none()`).
- No se confirmó si hay clientes fuera de `panel_admin/` que consuman `GET almacen/bobinas` o `almacen/inventario`.
- No se confirmó cómo debe tratarse la edición de una bobina global compartida: editar `width/length/price` de una bobina con inventario en varias sucursales afecta a las otras sucursales.

### Módulos y dependencias relacionadas
- Backend: `custom_views/almacen_admin.py`, `business/inventario.py`, `helper/user.py`, `serializer/almacen_serializer.py`, `urls.py:133-140`, `models.py:74-88,141-155`; consumidores de bobina/inventario: `business/pricing.py`, `business/orden_estado.py`, reportes (`admin_config/report_*`), calculadora pública (`views.py` `get_inventory`).
- Frontend: `panel_admin/src/app/almacen/{almacen.service.ts,almacen.model.ts,bobinas/*,inventario/*}`, `core/service/auth.service.ts` (`hasGroup`).

### Implementaciones similares existentes
- `PrecioVentaSucursalListCreateView` / `_precios_in_scope` (`almacen_admin.py:219-263`): lista y detalle acotados a `get_sucursales_in_scope`, filtro `?sucursal=` (`:241-243`) y `?search=`. Es el patrón más cercano dentro del mismo módulo.
- Órdenes: `_sucursal_in_scope_or_404` (usado en `ordenes_admin.py:409`) y `OrdenesSucursalesView` (`:390-398`) para el selector de sucursal acotado.
- `Inventario_Business.get_panel_inventario_queryset` (`business/inventario.py:17-23`): ya implementa el alcance "todas las sucursales habilitadas del usuario" para el reporte de utilidad.
- Frontend: `precios-sucursal-list.component.ts` y `listSucursales()` del service son el punto de partida para el selector de sucursal; no se verificó si ese listado ya tiene filtros por lámina/sucursal que se puedan reutilizar (hipótesis a revisar en diseño).

### Comportamiento actual
Cualquier usuario staff lista **todas** las bobinas (activas) y puede, si tiene `add/change_window_film_reel`, crearlas/editarlas sin relación con sucursales. Para inventario, un no-admin ve solo la primera de sus sucursales habilitadas; por id (`PATCH/GET inventario/<pk>/`, toggle) no hay restricción de sucursal, y el alta acepta cualquier sucursal. En la UI, solo admin ve Crear/Editar/Eliminar; ninguna de las dos listas tiene filtros de lámina/sucursal (solo un buscador de texto cliente).

### Restricciones
- `docs/CLAUDE.md`: cambios de lógica de negocio con test; cambios en varios archivos requieren plan antes; no editar migraciones aplicadas; dinero con `Decimal`.
- `ADR-modulo-almacen-permisos-rol-frontend`: el backend es la barrera real (no confiar solo en ocultar botones); este task **modifica** ese modelo de roles → requiere ADR nuevo o superseder parcial.
- `ADR-modulo-almacen-modelo-datos-imagen-soft-delete`: soft delete con `is_active`; edición de inventario limitada a ciertos campos.
- Contrato de `get_inventory` (público) consumido por `proforma/`; no debe romperse.

### Riesgos identificados
- Cambio de **autorización** (quién escribe qué, por sucursal) sobre un ADR vigente: riesgo de regresión de permisos y de filtración entre sucursales por las rutas por id (`InventarioUpdateView`, toggle) y por el alta (sucursal arbitraria).
- Ambigüedad de modelo de bobinas (global vs. por sucursal); si se opta por pertenencia, hay migración y afectación de `pricing`, órdenes, reportes y calculadora pública.
- Editar una bobina compartida desde una sucursal altera el catálogo de las demás.
- Tests existentes codifican el comportamiento anterior (solo admin / primera sucursal) y tendrán que cambiar.
- `get_inventario_queryset_by_role` usa solo `sucursales[0]`; con usuarios de varias sucursales el filtro y el alcance actual divergen del requerimiento.
- `GET /product/sucursales` no está acotado por usuario: sin un endpoint/ajuste de alcance, el selector expondría sucursales ajenas aunque el backend las rechace.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — cambia autorización (alcance por sucursal en lectura, detalle por id, alta, edición y toggle de inventario, y relajación del ADR de rol de solo lectura para `almacen`). Con el alcance reducido a inventario desaparece la decisión de modelo de bobinas y no hay migración prevista, pero la autorización sigue siendo sensible y requiere ADR.

### Diseño requerido
**SI** — se agregan filtros (lámina/sucursal) a dos listados, con un selector de sucursal que se fija/deshabilita según cuántas sucursales tiene el usuario, y cambia la visibilidad de acciones de alta/edición por rol y sucursal; conviene definir el comportamiento en la plantilla `panel_admin/` antes de implementar.

## Diseño
- [DDR-almacen-permisos-sucursal-filtros-filtros-y-selector-sucursal](../design/DDR-almacen-permisos-sucursal-filtros-filtros-y-selector-sucursal.md) — filtros Lámina/Sucursal en Bobinas e Inventario (servidor-side, junto al buscador de texto en cliente); selector de sucursal fijo y deshabilitado con una sola sucursal, "Todas mis sucursales" con varias, todas para admin; acciones de escritura visibles según alcance (se ocultan, no se deshabilitan). El frontend no es la barrera de seguridad: pendiente de arquitectura el alcance por sucursal en el servidor, la semántica de "bobinas de mi sucursal" y cómo el frontend conoce su alcance.

## Arquitectura
- [ADR-almacen-permisos-sucursal-filtros-alcance-inventario](../adr/ADR-almacen-permisos-sucursal-filtros-alcance-inventario.md) — alcance de inventario con `get_panel_inventario_queryset` (todas las sucursales del usuario) en listado, detalle, toggle y alta (404 / 400 fuera de alcance); escritura = permiso Django (`add/change_inventario`) + alcance; filtros `?window_film=` / `?sucursal=` sobre el alcance; nuevo `GET almacen/sucursales`; el frontend usa los `permissions` ya devueltos por el login. Sin migraciones; rollback por commit y por quitar permisos al grupo. Reemplaza parcialmente (Inventario) a `ADR-modulo-almacen-permisos-rol-frontend`.

Supuestos de negocio pendientes de confirmar (marcados en el ADR): Eliminar/Activar sigue la regla de editar; admin conserva todas las sucursales habilitadas; grupos que reciben `add/change_inventario`; alta bloqueada en sucursales deshabilitadas también para admin.

## Plan
- [PLAN-2026-10-02-almacen-permisos-sucursal-filtros](../plans/PLAN-2026-10-02-almacen-permisos-sucursal-filtros.md) — **v1**. 10 pasos (vista de sucursales en alcance, listado con alcance y filtros, detalle/toggle/alta con alcance, tests backend, servicio y componentes del panel, specs y verificación manual en vivo). E2E: no corresponde (sin Playwright; integración de API + specs + verificación manual). Sin dependencias nuevas, sin migraciones. Tres preguntas abiertas (Eliminar/Activar, grupos con permisos, alta en sucursales deshabilitadas).

## Implementación
Pasos 1 a 9 del [plan v1](../plans/PLAN-2026-10-02-almacen-permisos-sucursal-filtros.md), sin desvíos de alcance. Commits `260e7d2` (backend) y `d4c7ad8` (panel) en el PR [#66](https://github.com/rolion/praxsa-django-panel-admin/pull/66).

**Backend**
- `almacen_admin.py`: `_inventario_in_scope(user)` (usa `Inventario_Business.get_panel_inventario_queryset`) en `InventarioListView`, `InventarioUpdateView.get_queryset` e `InventarioToggleActiveView` (404 fuera de alcance); filtros `?sucursal=`/`?window_film=` (solo dígitos, sobre el alcance); `create` pasa `context={'request': request}`; nueva `AlmacenSucursalesView` y ruta `almacen/sucursales` (`urls.py`).
- `almacen_serializer.py`: `InventarioCreateSerializer.validate_sucursal` contra `get_sucursales_in_scope` (400; sin `request` rechaza). Único uso del serializer: `InventarioListView` (verificado por grep).
- Sin migraciones; `get_inventario_queryset_by_role` intacto.

**Panel**
- `almacen.service.ts` (`InventarioListParams`, `listSucursalesAlcance`), `inventario-list` (selects Lámina/Sucursal, sucursal fija con una sola, aviso sin sucursales, `canCreate`/`canEdit` por `hasPermission`), `inventario-create` (sucursales en alcance, preselección y bloqueo con una, `getRawValue()` al enviar), `inventario-view` (`canManage` por `change_inventario`).

**Pruebas**
- `tests/test_inventario_alcance_sucursal.py` (nuevo, 30 casos): listado (varias sucursales, admin, sin sucursal, sucursal deshabilitada), filtros (propia, ajena, lámina, combinados, no numéricos, con búsqueda/inactivos), detalle/PATCH/toggle propios y ajenos (404), sin permiso (403), admin, alta (propia, ajena, deshabilitada, admin, sin permiso) y endpoint de sucursales.
- Ajuste de 5 tests de `test_almacen_module.py` (`InventarioTest.test_manage_*`, `InventarioToggleActiveTest.*`): el usuario pasa a ser empleado de la sucursal del inventario; no se relajó el alcance.
- Specs del panel: listado (carga con parámetros, sucursal fija/varias/ninguna, filtros, permisos), alta (sucursal única bloqueada y enviada, varias) y vista (`canManage` por permiso).
- Corrida propia (no es el Quality Gate): `manage.py test product` 618 OK; `makemigrations --check --dry-run` sin cambios; `ng build` OK; specs de `almacen/` 48 OK. La suite completa del panel da 13 fallos en specs `should create` de componentes demo de la plantilla (AdvanceTable, Blank, Dashboard2, First/Second/Third, Footer, Page404/500, Signup) que no tocan almacén; no se comprobó contra `master` si ya fallaban antes.

**Decisiones por defecto aplicadas (preguntas abiertas del plan sin respuesta del usuario):** Eliminar/Activar sigue la regla de editar (`change_inventario` + alcance); el alta se bloquea en sucursales deshabilitadas también para admin; no se agregó comando de asignación de permisos a grupos (paso operativo). Si el negocio decide otra cosa, cambia solo el punto afectado (toggle: permiso aparte; comando: aditivo).

**Deuda técnica / límites señalados**
- Conviven dos métodos de alcance de inventario (`get_inventario_queryset_by_role`, legado con `sucursales[0]`, usado por el reporte del Django Admin; y `get_panel_inventario_queryset` en la API).
- `GET /product/sucursales` y Precios por sucursal siguen sin alcance por usuario (fuera de alcance).
- Los botones del panel reflejan los permisos del último login; un cambio de grupo exige volver a iniciar sesión (el servidor sí aplica el cambio de inmediato).
- Los permisos `add_inventario`/`change_inventario` hay que asignarlos a los grupos no admin que deban operar; mientras tanto siguen en solo lectura.
- **Pendiente:** verificación manual en vivo (paso 10 del plan: admin, usuario de 1 sucursal, de 2, sin permisos y sin sucursal; intento directo por API a una fila ajena) — no ejecutada por el engineer.

## Review
_Pendiente_

## Publicación
_Pendiente_
