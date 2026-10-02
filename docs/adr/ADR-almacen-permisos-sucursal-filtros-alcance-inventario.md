# ADR-almacen-permisos-sucursal-filtros-alcance-inventario: Alcance por sucursal y filtros de lámina/sucursal en Inventario

**Estado:** Propuesto
**Task relacionado:** TASK-almacen-permisos-sucursal-filtros
**Fecha:** 2026-10-02

## Contexto

El task (alcance reducido a **Inventario**; bobinas quedan fuera) pide que el usuario solo vea, agregue y edite inventario de las sucursales que tiene asignadas, y que el listado se pueda filtrar por lámina y sucursal. El DDR `DDR-almacen-permisos-sucursal-filtros-filtros-y-selector-sucursal` fija el comportamiento visual (selector de sucursal fijo con una sola sucursal, acciones de escritura ocultas según permiso, filtros servidor-side) y deja a esta etapa la verificación del alcance en el servidor y cómo el frontend conoce su alcance.

Hechos relevantes (verificados en la investigación):
- `InventarioListView` filtra con `Inventario_Business.get_inventario_queryset_by_role`, que para no-admin usa solo `sucursales[0]` (`business/inventario.py:25-38`). Ese método lo comparten el reporte de almacén del Django Admin (`admin_config/report_storage.py:69`) y tests de `test_sucursal_scope_admin.py`; no conviene cambiar su semántica.
- Ya existe `Inventario_Business.get_panel_inventario_queryset` (`business/inventario.py:17-23`): admin ve todo, el resto todas sus sucursales habilitadas. Es exactamente el alcance pedido.
- `InventarioUpdateView` (`almacen_admin.py:194-216`) e `InventarioToggleActiveView` (`:156-191`) buscan por id sin alcance; el alta (`InventarioCreateSerializer`, `almacen_serializer.py:118`) acepta cualquier `Sucursal`.
- `User_Helper.get_sucursales_in_scope` (`helper/user.py:41-47`) es el patrón de alcance ya adoptado por Órdenes y Precios por sucursal (`almacen_admin.py:219-227`).
- El login del panel ya devuelve `permissions` efectivos (`custom_views/auth_token.py:55-58`) y el frontend ya tiene `AuthService.hasPermission` (`core/service/auth.service.ts:105-109`, con test), por lo que el frontend puede saber si puede escribir sin cambiar el login.
- `GET /product/sucursales` devuelve todas las sucursales sin alcance (`user_admin.py:134-138`).
- Decisión previa que este ADR modifica: `ADR-modulo-almacen-permisos-rol-frontend` (decisiones 2 y 6) deja a `almacen` sin permisos de escritura y oculta acciones con `hasGroup('admin')`; para Inventario, esa decisión queda reemplazada por la de abajo (Láminas y Bobinas no cambian).

## Decisión

1. **Alcance de Inventario = `get_panel_inventario_queryset`** (admin: todas las filas; resto: filas de todas sus sucursales habilitadas; sin sucursal: ninguna). Se usa para listado, detalle por id y activar/desactivar. El método legado `get_inventario_queryset_by_role` **no se toca** (lo usa el reporte del Django Admin); queda sin llamadores en la API de almacén. Fuera de alcance → **404** (la fila no existe para ese usuario), igual que en Órdenes.
2. **Autorización de escritura = permiso Django + alcance (ambas condiciones).** `add_inventario` para el alta (ya vía `DjangoModelPermissions` en POST) y `change_inventario` para PATCH y toggle (ya verificados explícitamente). El alcance por sucursal se suma; el permiso decide *si* puede escribir, la sucursal decide *dónde*. A los grupos no admin que deban operar (p. ej. `Almacen`) se les asignan `add_inventario` y `change_inventario` como paso de datos (grupos/permisos), no por nombre de grupo en código.
3. **Alta**: la sucursal enviada debe estar en `User_Helper.get_sucursales_in_scope(user)`; si no, error de validación 400 en el campo `sucursal`. Para lograrlo, la vista pasa `context={'request': request}` al `InventarioCreateSerializer` (hoy no lo pasa, `almacen_admin.py:150`) y el serializer valida el campo. Cambio de comportamiento aceptado: ninguna cuenta, tampoco admin, puede dar de alta inventario en una sucursal **deshabilitada** (`enable_to_install_windows_film=False`); esas filas no son vendibles de todos modos (`eligible_rows`, `business/inventario.py:54-60`).
4. **Activar/desactivar (“Eliminar”)**: se rige por la misma regla que editar (`change_inventario` + alcance). El pedido no lo menciona; se adopta este default por coherencia con la convención existente de los toggles (`change_*`) y se señala como supuesto de negocio (ver Consecuencias).
5. **Filtros del listado**: nuevos parámetros `?window_film=<id>` y `?sucursal=<id>` en `GET almacen/inventario`, ambos aplicados **sobre** el alcance (intersección, no lo amplían): una sucursal fuera de alcance devuelve lista vacía, sin 404 ni filtración de información. Valores no numéricos se ignoran (mismo criterio que `?sucursal=` de Precios por sucursal, `almacen_admin.py:241-243`). Conviven con `?search=` e `?include_inactive=`. Contrato aditivo: sin parámetros el comportamiento de lectura es el del alcance.
6. **Sucursales en alcance para el frontend**: nuevo endpoint `GET almacen/sucursales` (`IsAuthenticated` + `IsStaffUser`) que devuelve `[{id, name}]` de `get_sucursales_in_scope(user)` (misma forma que `OrdenesSucursalesView`, `ordenes_admin.py:390-398`). No se reutiliza el de Órdenes (acopla módulos) ni `GET /product/sucursales` (no acotado). Es la fuente para el selector de sucursal del listado y del alta; la regla "una sola → fija y deshabilitada" la calcula el frontend con `length === 1`.
7. **Capacidad de escritura en el frontend**: se usa el `permissions` ya devuelto por el login y `AuthService.hasPermission('product.add_inventario' | 'product.change_inventario')` para mostrar/ocultar Crear y Editar/Eliminar-Activar. No se modifica `PanelAdminAuthToken`. Como toda fila listada ya está dentro del alcance, no hace falta decidir visibilidad por fila. Los permisos del frontend son una foto del login (cambios de grupo requieren nuevo login), supuesto ya vigente en el panel.
8. **Fuera de esta decisión**: Láminas, Bobinas, Precios por sucursal (siguen con su listado de sucursales no acotado) y la semántica de `get_inventario_queryset_by_role`.

## Alternativas consideradas

- **Modificar `get_inventario_queryset_by_role` para usar todas las sucursales.** Más simple, pero cambia el alcance del reporte de almacén del Django Admin y sus tests (`test_sucursal_scope_admin.py`) sin que se haya pedido. Descartada; se reutiliza el método ya existente `get_panel_inventario_queryset`.
- **Decidir permisos por nombre de grupo (`is_request_user_almacen`).** Simple pero rígido y contrario al patrón `Group`/`Permission` ya adoptado (ADR de permisos de almacén). Descartada.
- **Filtros en cliente.** Ya descartada en el DDR (fila sin id de lámina; datos sin acotar viajan al navegador).
- **Reutilizar `ordenes/catalogo/sucursales` para el selector.** Evita un endpoint pero acopla Almacén a Órdenes. Descartada por una vista de 3 líneas propia.
- **Devolver 404 para `?sucursal=` fuera de alcance** (como Órdenes). Más estricto, pero en un listado con filtro opcional rompe la UI sin aportar seguridad (el alcance ya acota). Descartada.
- **Permiso `delete_inventario` separado para Eliminar/Activar.** Respetaría literalmente “ver, agregar o editar”, pero rompe la convención de toggles (`change_*`) y exige reasignar permisos al grupo admin. Descartada por ahora; reabrible si el negocio lo pide.
- **Añadir alcance al login (lista de sucursales).** Evita una llamada, pero mete datos de dominio en la autenticación y queda desactualizado en sesión larga. Descartada.

## Estrategia de rollback / mitigación

- **Sin migraciones ni cambios de esquema**: el cambio es de vistas/serializer/helpers y un endpoint nuevo; se revierte con el commit. Los parámetros nuevos del listado y el endpoint de sucursales son aditivos.
- **Riesgo de seguridad (cambio de autorización)**: es una **restricción** respecto de hoy en detalle/toggle/alta (antes sin alcance) y una **ampliación** solo para quienes reciban `add/change_inventario`. Mitigación: la ampliación depende de asignar permisos a grupos (dato), de modo que revertirla en producción es quitar esos permisos del grupo sin desplegar; hasta asignarlos, un usuario no admin conserva solo lectura.
- **Regresión probable**: usuarios con varias sucursales pasan a ver todas las suyas (antes solo la primera) y un admin deja de poder dar de alta en sucursales deshabilitadas; ambos son efectos buscados/aceptados y se cubren con tests.
- Verificación de filtración entre sucursales con tests de API (list, detalle, PATCH, toggle y alta con un usuario de otra sucursal) antes de fusionar; prueba manual en vivo recomendada (ver memoria del proyecto sobre smoke tests de autorización).

## Consecuencias

- Inventario queda con alcance coherente en lectura, detalle, alta, edición y toggle; el frontend solo decide visibilidad, la barrera real es el servidor.
- Se acepta como deuda: dos métodos de alcance de inventario conviviendo (`get_inventario_queryset_by_role` legado con `sucursales[0]` en el Django Admin y `get_panel_inventario_queryset` en la API); unificarlos queda para otra tarea.
- Se acepta que Precios por sucursal y el resto del panel sigan usando `GET /product/sucursales` sin alcance.
- Supuestos de negocio pendientes de confirmar: (1) Eliminar/Activar sigue la regla de editar; (2) `admin` conserva acceso a todas las sucursales habilitadas; (3) qué grupos reciben `add_inventario`/`change_inventario` (operativo); (4) con cero sucursales el usuario ve el listado vacío y sin acciones.
- Tests existentes de `test_almacen_module.py` que asumen “solo admin” o el alcance por primera sucursal deben ajustarse; se enumeran en el plan.
- El DDR asumía que el frontend necesita conocer el alcance: queda resuelto con el endpoint `almacen/sucursales` y los `permissions` del login, sin tocar autenticación.
