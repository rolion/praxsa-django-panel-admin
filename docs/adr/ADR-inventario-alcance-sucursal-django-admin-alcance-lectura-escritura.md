# ADR-inventario-alcance-sucursal-django-admin-alcance-lectura-escritura: Alcance por sucursales asignadas (sin excepción de grupo) con lectura y escritura separadas

**Estado:** Propuesto
**Task relacionado:** TASK-inventario-alcance-sucursal-django-admin
**Fecha:** 2026-10-02

## Contexto

Regla de negocio confirmada por el usuario: **todo grupo (incluido admin) solo ve y opera lo de las sucursales asignadas a su cuenta**; un admin sin sucursales ve 0 datos; solo el **superusuario de Django** ve todo; el módulo Usuarios queda fuera; el impacto en producción está aceptado. Una sucursal **inactiva** (`enable_to_install_windows_film=False`) se puede ver pero no se puede agregar ni modificar nada en ella, para todos los grupos (DDR `DDR-inventario-alcance-sucursal-django-admin-sucursales-inactivas-y-filtro-reportes`).

Estado actual (verificado):
- El alcance está centralizado en `User_Helper` (`helper/user.py`): `can_view_all_sucursales` (= grupo admin, `:28-29`), `get_enabled_sucursal_ids` (`:31-39`), `get_sucursales_in_scope` (`:41-47`) y `has_assigned_sucursal` (`:57`). Todos los métodos `get_panel_*` de la API del panel (`business/inventario.py:17-23`, `proforma.py:160-168`, `orden_trabajo.py:36-45`, `pago.py:15-32`, `dashboard.py`) y las validaciones de alta (`almacen_serializer.py:155`, `ordenes_serializer.py:166`, `instalador_precio_serializer.py:52`) dependen de ellos. Por eso quitar la excepción de admin y separar lectura/escritura se resuelve casi en un solo punto.
- **Todos** esos métodos mezclan dos conceptos: filtran por sucursal *activa* tanto para leer como para escribir. Hoy una sucursal inactiva desaparece también de la lectura.
- La escritura de Inventario y Órdenes parte del objeto obtenido con alcance (404 fuera de alcance, `ordenes_admin.py:65-69`, `almacen_admin.py:199-205,234-235`), pero **no verifica que la sucursal esté activa** al modificar: PATCH de proforma (`ordenes_admin.py:148-151`), generar nota (`:161-183`), anular (`:266-271`), acciones de nota de trabajo (`:283-288`) y de nota de venta (`:351-356`), PATCH/toggle de inventario. Además `ProformaWriteSerializer.validate_sucursal` retorna sin validar cuando es edición (`ordenes_serializer.py:162-164`).
- Las transiciones del servicio no reciben al usuario (`Orden_Estado_Business().anular_proforma(Proforma_Header...)`, `ordenes_admin.py:270`), por lo que la regla no cabe naturalmente en esa capa sin cambiar firmas.
- Los métodos legados `*_by_role` (`sucursales[0]`, devuelven `None` sin sucursal) alimentan **solo el Django Admin** (`admin_config/proforma_admin.py:168`, `reporte_proforma.py:104`, `nota_trabajo.py:128`, `nota_venta.py:124`, `pagos.py:158`, `precio_venta_sucursal.py:56`, `report_storage.py:69`) y `views.py:159` (`get_proforma_car_part_info`). `InventoryAdmin` tiene su propia lógica (`admin_config/inventory.py:43-115`), con estado mutable por petición y alta sin acotar la sucursal.

## Decisión

1. **Una sola definición de alcance, en `User_Helper`.** `can_view_all_sucursales(user)` pasa a significar `user.is_superuser`; el grupo admin deja de ser global. `is_request_user_admin` se conserva (otros usos de rol) pero ya no concede alcance.
2. **Dos alcances explícitos, con nombres distintos** (se elimina `get_sucursales_in_scope` para que ningún llamador quede en el concepto equivocado sin notarlo):
   - **Lectura**: sucursales asignadas (`Sucursal.empleado`), activas o no; el superusuario, todas. Métodos: `get_readable_sucursales(user)` / `get_readable_sucursal_ids(user)`.
   - **Escritura**: lo anterior restringido a `enable_to_install_windows_film=True`. Métodos: `get_writable_sucursales(user)` / `get_writable_sucursal_ids(user)`.
   - `has_assigned_sucursal` pasa a significar "tiene alguna sucursal en el alcance de lectura" (base de los avisos "sin sucursal" y de los 0 datos del admin sin sucursales).
3. **Lecturas** (listados, detalle, reportes, dashboard, catálogos de sucursales) usan el alcance de **lectura**. **Validaciones de alta** (inventario, proforma, precio por sucursal) usan el de **escritura**.
4. **Toda modificación de una fila existente** (PATCH, toggle, anular, generar nota, terminar/corregir, cobrar/anular pago) exige además que la sucursal de la fila esté en el alcance de **escritura**. Se aplica en la capa de vistas/serializers con un único helper (`sucursal_writable_or_409` o equivalente, junto a `_get_in_scope_or_404`) y responde **409 Conflict** con un mensaje fijo ("La sucursal está inactiva: solo lectura"), igual que las demás reglas de estado de negocio de Órdenes (`ordenes_admin.py:77-83`); fuera del alcance de lectura se mantiene el **404**. Se corrige además la validación saltada en `ProformaWriteSerializer.validate_sucursal` para ediciones.
5. **Exposición al frontend (aditiva, sin romper contrato):**
   - Cada fila/detalle de inventario, proforma, nota de trabajo y nota de venta incluye `sucursal_activa: bool`.
   - Los catálogos `almacen/sucursales` y `ordenes/catalogo/sucursales` devuelven las sucursales del alcance de **lectura** con el campo `activa: bool`; los formularios de alta filtran a las activas y los filtros de listado muestran todas.
   - La barrera real sigue siendo el servidor (puntos 3 y 4); la bandera solo permite ocultar botones.
6. **Superusuario:** ve todo (lectura: todas las sucursales, también inactivas). Para escritura queda **sujeto a la misma regla de sucursal activa** (supuesto conservador, coherente con el alta de inventario actual; pendiente de confirmar).
7. **Django Admin en el mismo cambio.** Los métodos legados `*_by_role` pasan a **delegar** en los `get_panel_*` equivalentes (siempre un queryset, nunca `None`; se verifica cada llamador listado arriba, todos del Django Admin salvo `views.py:159`). `InventoryAdmin` se reescribe sin mutar atributos de la instancia por petición (`get_list_display`/`get_fields`/`get_readonly_fields`), limita el campo `sucursal` con `formfield_for_foreignkey` al alcance de escritura, y los `ModelAdmin` de inventario y órdenes aplican la regla de escritura por objeto con un mixin común (`has_add_permission`, `has_change_permission(obj)`, `has_delete_permission(obj)`). El superusuario conserva su acceso global de Django Admin.
8. **Sin migraciones ni cambios de modelo.** Ninguna regla se guarda en base de datos; solo cambia el cálculo.

Las precisiones de contrato de reportes se registran en `ADR-inventario-alcance-sucursal-django-admin-filtro-multisucursal-reportes`.

## Alternativas consideradas

- **Dejar `get_sucursales_in_scope` con su significado y añadir solo un método de lectura.** Cambio mínimo, pero deja el nombre ambiguo: un llamador nuevo elegiría el equivocado sin error visible. Descartada; el renombrado es mecánico y los tests lo detectan.
- **Aplicar la regla de escritura dentro de `Orden_Estado_Business`.** Cubriría API y Django Admin en un punto, pero las transiciones no reciben al usuario y ya se llaman desde varios sitios; cambiar firmas ampliaría el alcance. Descartada. Compensación: un test por endpoint de escritura que fije el 409.
- **Aplicarlo con un permiso de DRF (`BasePermission.has_object_permission`) por vista.** Elegante, pero las vistas de Órdenes obtienen el objeto mediante `_get_in_scope_or_404` y no por `get_object()` en todas; habría que reescribirlas. Descartada por riesgo de dejar vistas sin cubrir.
- **Bloqueo en la base de datos (trigger o constraint por sucursal inactiva).** Protege incluso scripts, pero es una migración compleja, difícil de revertir y bloquea procesos legítimos (p. ej. devolución de inventario al anular). Descartada.
- **Feature flag para mantener la excepción de admin durante una transición.** El usuario aceptó el impacto inmediato en producción; un flag añade una rama de código que conservaría el comportamiento prohibido. Descartada (ver rollback).
- **Limitar el cambio a Inventario y dejar Órdenes/Reportes con excepción de admin.** Contradice la decisión del usuario (regla en todo el sistema). Descartada.
- **Dejar fuera el Django Admin.** Es una puerta de entrada real a inventario (alta en cualquier sucursal, estado mutable compartido) y a las órdenes; dejarlo sería incumplir la regla. Se incluye, delegando en los métodos del panel para no duplicar lógica.

## Estrategia de rollback / mitigación

Cambio de **autorización** sin migraciones ni escritura de datos:
- **Rollback:** revertir el commit y redesplegar; no hay estado persistido que deshacer. Como el alcance vive en `User_Helper`, un `git revert` del cambio del helper restaura el comportamiento anterior de la API; el cambio al Django Admin se revierte con el mismo commit.
- **Mitigación operativa antes del despliegue:** verificar que existe al menos una cuenta con `is_superuser=True` para quien deba seguir viendo todo; las cuentas admin sin sucursales verán 0 datos (aceptado por el negocio). Asignar sucursales desde el Django Admin (cuenta superusuario) o el módulo Usuarios si se necesita restaurar acceso. Un script de listado de cuentas admin sin sucursales es opcional y no forma parte del cambio.
- **Pruebas como red de seguridad:** matriz de tests por rol (superusuario, admin, no admin; 0, 1 y N sucursales; activa e inactiva) para listados, detalle, alta, edición y cada acción de estado; test de que `get_sucursales_in_scope` ya no existe en el código de producción.
- No hay riesgo de pérdida de datos: no se borra ni se modifica información.

## Consecuencias

- La regla se define en un único módulo y los permisos de escritura/lectura dejan de confundirse.
- Cualquier cuenta admin sin sucursales deja de ver datos (impacto aceptado). El superusuario es el único acceso global; conviene documentarlo en operación.
- Cambia el significado de "Todas" en vistas agregadas (ver ADR de reportes); los tests existentes que suponen admin global (`test_sucursal_scope_admin.py`, `test_inventario_alcance_sucursal.py`, `test_ordenes_scope_permissions.py`, reportes y dashboard) deberán actualizarse.
- Deuda aceptada: `get_user_inventory_window_films` y `get_inventory_window_film_reel_widths` (`business/inventario.py:189-203`, usados por proformas del Django Admin y `views.py:119,181`) siguen filtrando por `sucursal__empleado=user` sin la regla de activa; no se tocan. El módulo Usuarios (`SucursalListCreateView`, `user_admin.py:134-138`) queda fuera de alcance por decisión del usuario. Precios por sucursal pasa a lectura/escritura separadas por el mismo cambio, sin marca visual (DDR).
- Reemplaza parcialmente: `ADR-almacen-permisos-sucursal-filtros-alcance-inventario` (decisión 1 y el supuesto "admin conserva todas las sucursales"), `ADR-modulo-ordenes-proforma-nota-trabajo-alcance-permisos` (decisión 2, admin ve todo), `ADR-dashboard-taller-laminas-api-agregados-alcance` y `ADR-reportes-utilidad-ventas-diarias-permisos` (alcance de admin).
- Supuestos de negocio pendientes de confirmar: (a) el superusuario también queda bloqueado para escribir en sucursales inactivas; (b) código de estado 409 para "sucursal inactiva" (frente a 403).
