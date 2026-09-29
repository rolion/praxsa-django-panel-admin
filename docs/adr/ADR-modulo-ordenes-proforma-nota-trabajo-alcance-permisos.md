# ADR-modulo-ordenes-proforma-nota-trabajo-alcance-permisos: Alcance por sucursal y permisos Django por acción para las Órdenes, con permisos efectivos expuestos al frontend

**Estado:** Propuesto
**Task relacionado:** TASK-modulo-ordenes-proforma-nota-trabajo
**Fecha:** 2026-09-29

## Contexto

La API de Órdenes (`ADR-modulo-ordenes-proforma-nota-trabajo-api-y-calculo`) expone datos con PII de clientes y acciones que mutan inventario. La investigación encontró que el filtrado por rol/sucursal actual es inconsistente:
- `Proforma_Business.get_proforma_queryset_by_role` (`business/proforma.py:235-254`) compara el grupo con `'Admin'` **sensible a mayúsculas**, mientras el resto del proyecto usa `admin` en minúsculas (`helper/user.py:7-10`, `AuthService.hasGroup` en `panel_admin/src/app/core/service/auth.service.ts:69-71`, `ADR-modulo-almacen-permisos-rol-frontend`). Un usuario del grupo `admin` del panel caería en la rama "solo su sucursal".
- `Orden_Trabajo_Business.get_nota_queryset_by_role` (`business/orden_trabajo.py:18-30`) no tiene bypass de admin; `get_finish_nota_queryset` (líneas 32-47) sí, pero solo devuelve notas ya finalizadas.
- Ambos usan solo la **primera** sucursal habilitada del empleado, sin orden definido (`sucursales[0]`), y devuelven `None` si no hay ninguna.

Además, el frontend hoy sabe los **grupos** del usuario (`PanelAdminAuthToken`, `custom_views/auth_token.py:47-55`) pero no sus permisos Django; qué rol puede crear/editar/generar nota en Órdenes **no está definido por negocio** (pregunta 4 de la investigación, sin responder). Lecciones previas: el IDOR de `InvoiceView`/`get_proforma_car_part_info` (ADR-006-idor) obligó a acotar siempre por alcance en el detalle, no solo en el listado.

## Decisión

1. **Todas las vistas de Órdenes**: `TokenAuthentication` + `IsAuthenticated` + `IsStaffUser` (`permissions.py:4-11`), igual que Vehículos/Almacén. El detalle y toda acción sobre un `<id>` obtienen el objeto **desde el queryset con alcance**; un objeto fuera de alcance responde 404 (no 403), para no confirmar su existencia.

2. **Alcance (qué filas ve/usa un usuario)** con dos métodos nuevos, uno para proformas y otro para notas, en `business/`, sin tocar los métodos legados (que siguen alimentando Django Admin y `get_proforma_car_part_info`):
   - Usuario con permiso de ver todas las sucursales (`User_Helper.can_view_all_sucursales`, comparación case-insensitive con `admin`, `helper/user.py:28-29`): todas las filas no borradas (`is_delete=False`; en notas, por `proforma__is_delete`).
   - Resto: filas cuya sucursal esté entre **todas** las sucursales habilitadas (`enable_to_install_windows_film=True`) de las que el usuario es empleado (deja de usar `[0]` sin orden).
   - Sin sucursal asignada: `qs.none()` (no `None`), y el listado devuelve una respuesta vacía con un indicador/mensaje que la UI usa para mostrar "Asigne una sucursal al usuario" (`Inventario_Business.get_inventario_queryset_by_role` ya sigue este patrón, `business/inventario.py:14-27`; `User_Helper.has_assigned_sucursal`, `helper/user.py:31-39`).
   - Al **crear** una proforma, la sucursal debe estar dentro del alcance; un usuario no-admin no puede crear en una sucursal ajena. Los catálogos (`ordenes/catalogo/*`) también se acotan al alcance.

3. **Permisos por acción con permisos Django estándar, sin permisos custom ni migración:**

   | Acción | Verificación en servidor |
   |---|---|
   | Listar / ver proformas y notas, PDF | `IsStaffUser` + alcance (los `GET` no exigen permiso en `DjangoModelPermissions`, igual que Almacén) |
   | Crear proforma | `product.add_proforma_header` |
   | Editar proforma | `product.change_proforma_header` |
   | Generar nota de trabajo | `product.add_nota_trabajo` |
   | Editar nota de trabajo | `product.change_nota_trabajo` |

   Las vistas de lista/alta y detalle usan `DjangoModelPermissions`; la acción de generar nota usa `has_perm` explícito, mismo patrón que los `toggle-active` (`almacen_admin.py:47-65`). **Qué grupos reciben cada permiso es configuración de datos** (módulo Grupos del panel), no código; el plan debe incluir el paso de asignarlos a los grupos reales y verificarlo, porque sin ese paso ningún usuario no-superusuario podrá crear/editar/generar.

4. **Reglas de estado aplicadas siempre en servidor**, con independencia de la UI: proforma cerrada o borrada no se edita; no se genera nota sobre una proforma ya cerrada; nota con nota de venta no se edita; `sales_type` y `sucursal` inmutables tras crear.

5. **Frontend: exponer los permisos efectivos.** `PanelAdminAuthToken` agrega al login un campo `permissions` (lista de `app_label.codename` de `user.get_all_permissions()`), aditivo y compatible con `groups`/`is_staff` ya devueltos. `AuthService` incorpora `hasPermission(codename)` junto a `hasGroup`, y la UI de Órdenes oculta Crear/Editar/Generar nota según esos permisos, no según nombres de grupo. La UI es solo presentación (ver DDR); la barrera real es el punto 3.

## Alternativas consideradas

- **Corregir `get_proforma_queryset_by_role` en el lugar** (comparación case-insensitive, todas las sucursales). Es más limpio y elimina una rama duplicada, pero cambia lo que ve hoy el personal en Django Admin y en `get_proforma_car_part_info`, ampliando acceso a usuarios cuyo grupo se llame `admin` en minúsculas sin haber verificado los datos reales. Se descarta en este task; se deja como tarea de unificación posterior con verificación de grupos reales.
- **Reutilizar los métodos legados tal cual** (como hizo ADR-006-idor para el detalle de nota). Descartada aquí: dejarían a un admin del panel sin ver proformas/notas (caso `admin` vs `Admin`; nota sin bypass) y rompería el requisito de "todas las proformas".
- **Gating del frontend por nombre de grupo (`hasGroup('admin')`) como en Almacén.** Más simple, pero exige decidir hoy qué grupos pueden qué acción, y esa decisión de negocio no existe. Con permisos efectivos la UI refleja lo que el módulo Grupos configure, sin hardcodear roles.
- **Permisos custom (`generate_nota_trabajo`, etc.).** Requeriría migración y no aporta: `add_nota_trabajo` describe correctamente la acción.
- **403 en vez de 404 para objetos fuera de alcance.** Descartada: filtrar por queryset es el patrón ya usado y evita revelar existencia.

## Estrategia de rollback / mitigación

Cambio de autorización y de respuesta de login, ambos **aditivos** (no se quitan ni cambian campos ni permisos existentes; métodos legados intactos; sin migraciones).
- Riesgo principal: **sobre-permisividad** (un usuario ve/edita filas ajenas) o **sub-permisividad** (usuarios legítimos sin acceso por sucursal/permiso faltante). Mitigación: tests de API por escenario (admin ve todo; empleado de sucursal A no ve ni edita ni genera nota sobre B → 404; sin sucursal → vacío; sin permiso → 403; cliente no-staff → 403) y verificación manual en vivo con usuarios reales de distintos grupos, práctica ya usada en TASK-002/005 y sugerida por la memoria del proyecto para cambios de autorización.
- Reversión: `git revert` del PR; los permisos asignados a grupos son datos inocuos sin los endpoints. Si `permissions` en el login causara problemas, el frontend cae a ocultar por defecto y los endpoints siguen protegidos.

## Consecuencias

**Más fácil:** un único criterio de alcance para las dos entidades del módulo nuevo; el frontend no depende de nombres de grupo; los permisos se administran desde el módulo Grupos existente.

**Más difícil / deuda aceptada:**
- Coexisten dos criterios de alcance (legado para Django Admin, nuevo para el panel) que pueden divergir para usuarios con varias sucursales o grupo `Admin`/`admin`; unificarlos es trabajo posterior.
- Las asignaciones de permisos a grupos son un paso operativo fuera del código; olvidarlo se manifiesta como 403.
- Un usuario con varias sucursales ve todas las suyas en el panel, mientras el Django Admin sigue mostrando solo la primera.
- El login del panel ahora devuelve más datos (lista de permisos); es información del propio usuario, no sensible para terceros.
