# ADR-agrupacion-menu-instalador-precio-sucursal-api-permisos-borrado: API, permisos, alcance por sucursal, unicidad y borrado de Instaladores y Precios por sucursal

**Estado:** Propuesto
**Task relacionado:** TASK-agrupacion-menu-instalador-precio-sucursal
**Fecha:** 2026-09-30

## Contexto

El DDR `DDR-agrupacion-menu-instalador-precio-sucursal-menu-y-pantallas` decidió que Instaladores va en el grupo Usuarios y Precios por sucursal en Almacén, ambos como listado + modal, y dejó a arquitectura cuatro puntos: permisos, alcance por sucursal de Precios, unicidad y qué significa "eliminar".

Hechos relevantes (verificados en el código):
- Los patrones de API y permisos ya existen y se reutilizan: `_STANDARD_PERMISSIONS = [IsAuthenticated, IsStaffUser, DjangoModelPermissions]` en `custom_views/almacen_admin.py:17` y `vehicle_admin.py:16`; `toggle-active` con `has_perm` explícito; soft delete por `is_active` (`ADR-modulo-vehiculos-soft-delete`, `ADR-modulo-almacen-modelo-datos-imagen-soft-delete`); `groups`/`is_staff` ya viajan en el login y el frontend ya tiene `AuthService.hasGroup()` (`ADR-modulo-almacen-permisos-rol-frontend`).
- `User_Helper.get_sucursales_in_scope` (`helper/user.py`) ya entrega las sucursales habilitadas que un usuario puede usar: todas para `admin`, las propias para el resto (`ADR-modulo-ordenes-proforma-nota-trabajo-alcance-permisos`). A diferencia del admin viejo de precios, que usa solo `sucursales[0]` (`business/precio_venta.py:16-19`).
- `instalador` no tiene `is_active` y `Nota_trabajo.instaladar` lo referencia con `on_delete=DO_NOTHING` (`models.py:207`): un borrado físico de un instalador ya asignado falla con error de integridad (o deja huérfanos si la base no fuerza la FK).
- `precio_venta_sucursal` es una tabla hoja: ninguna otra tabla la referencia (`models.py:328-334`), y lo que ya se cotizó vive copiado en la proforma, no leído de esta tabla.
- Unicidad sucursal+lámina+ancho solo se valida en `PrecioVentaSucursalAdmin.save_model` (`admin_config/precio_venta_sucursal.py:31-44`); no hay constraint en base (BIZ-07, `docs/backend-audit.md:530`). No se puede verificar desde el repo si producción ya tiene duplicados.
- `OrdenesInstaladoresView` (`custom_views/ordenes_admin.py:414-423`) alimenta el selector de instalador en Notas de Trabajo, y el PATCH de nota valida pertenencia a sucursal (`serializer/ordenes_serializer.py:389`).

**Regla de negocio (confirmada por el usuario el 2026-09-30):** solo el rol `admin` crea, edita y elimina instaladores y precios; los demás roles solo pueden leerlos. Es el mismo criterio que Láminas/Bobinas; el mecanismo elegido permite cambiarlo asignando permisos a otro grupo, sin tocar código.

## Decisión

1. **Permisos (backend, barrera real).** Mismo patrón que Almacén/Vehículos: listado/creación/detalle con `_STANDARD_PERMISSIONS` (`DjangoModelPermissions` exige `add_/change_/delete_instalador` y `add_/change_/delete_precio_venta_sucursal` para escribir; `GET` solo pide staff autenticado). Se asignan esos permisos al grupo `admin` desde `/users/groups`, sin migración de datos. No se crea un rol nuevo.
2. **Frontend.** Botones Nuevo/Editar/Eliminar visibles solo con `authService.hasGroup('admin')`, igual que Almacén. Sin guard de ruta nuevo. Las dos entradas de menú se muestran a todos los perfiles staff.
3. **Instaladores: borrado lógico.** Migración nueva y aditiva: `instalador.is_active = BooleanField(default=True)`. "Eliminar" en la pantalla es `toggle-active` (mismo contrato y permiso `change_instalador` que `CarBrandToggleActiveView`); no hay `DELETE` físico. El listado del panel devuelve solo activos por defecto y `?include_inactive=true` los trae todos. El selector de Notas de Trabajo (`OrdenesInstaladoresView`) y la validación de asignación en el PATCH de nota (`ordenes_serializer.py:389`) excluyen instaladores inactivos; las notas ya asignadas conservan el nombre. No se modifica ninguna migración existente.
4. **Precios por sucursal: borrado físico.** Al ser tabla hoja, `DELETE` real con `DjangoModelPermissions`. Efecto funcional documentado en la UI: sin la fila, la cotización vuelve al precio del inventario (`business/pricing.py:80-81`). Lo ya cotizado no cambia.
5. **Alcance por sucursal de Precios.** El queryset y los selects se acotan con `User_Helper.get_sucursales_in_scope`: `admin` ve y gestiona todas las sucursales habilitadas; cualquier otro usuario con permiso de escritura solo las suyas. En crear/editar el servidor rechaza (`403`/`400` de validación) una sucursal fuera de ese alcance, aunque el cliente la envíe. Se reemplaza así el `sucursales[0]` del admin viejo por el criterio ya establecido en Órdenes; el admin Django viejo no se toca.
6. **Unicidad de Precios.** Validación en el serializer sobre (sucursal, lámina, ancho), excluyendo la propia fila al editar, con mensaje de negocio en español. **No** se agrega `UniqueConstraint` en base en este task: no se puede garantizar que producción no tenga duplicados y la migración fallaría; se registra como deuda (BIZ-07) para un task aparte con un chequeo previo de datos.
7. **Validaciones de campos.** `precio_venta` y `width` mayores que 0, `Decimal` siempre; teléfono con el mismo `RegexValidator` del modelo. Láminas del selector: solo activas; no se exige que la lámina tenga inventario en la sucursal (esa restricción del admin viejo era de comodidad de formulario).
8. **Contrato de API (aditivo, sin romper `proforma/`).**
   - `GET/POST instaladores`, `GET/PATCH instaladores/<pk>/`, `PATCH instaladores/<pk>/toggle-active/` (bajo el prefijo de Usuarios; soporta `?search=`).
   - `GET/POST almacen/precios-sucursal`, `GET/PATCH/DELETE almacen/precios-sucursal/<pk>/`.
   - Rutas del frontend: `/users/instaladores` y `/almacen/precios-sucursal`.
   - Único cambio a un endpoint existente: `ordenes/catalogo/instaladores` deja de listar inactivos.

## Alternativas consideradas

- **Borrado físico de Instaladores, bloqueando con error si están asignados.** Más simple, pero el instalador sale de circulación solo si nunca trabajó; ante la primera nota asignada quedaría inmovible, inconsistente con el soft delete ya usado en Vehículos y Almacén.
- **Borrado lógico también en Precios.** Sobreingeniería: no hay historial que proteger y una fila inactiva confundiría la resolución de precio (habría que filtrar en dos implementaciones de la regla, `pricing.py` y `inventario.py`).
- **`UniqueConstraint` en base ahora.** Es la protección correcta a largo plazo pero arriesga una migración fallida sobre datos que no se pueden ver desde el repo. Se difiere.
- **Mantener `sucursales[0]` como alcance.** Es el comportamiento heredado frágil: un usuario con dos sucursales solo vería una. Se descarta por el criterio ya decidido en Órdenes.
- **Rol nuevo (p. ej. `gestor-precios`).** Sin requerimiento; los permisos por grupo ya permiten dárselo a quien negocio decida.
- **Guard de ruta por permiso.** Igual que en Almacén: superficie nueva no pedida; el backend ya rechaza.

## Estrategia de rollback / mitigación

- **Migración** (`instalador.is_active`): aditiva, con default `True`, reversible con la operación inversa autogenerada; no toca datos existentes ni migraciones aplicadas. Si falla, no se aplica el resto.
- **Endpoints nuevos**: aditivos; revertirlos es quitar rutas y vistas. Ningún cliente actual los usa.
- **Cambio en `ordenes/catalogo/instaladores` y en la validación del PATCH de nota**: si aparece un problema, se revierte el filtro `is_active` sin migrar datos (todos los instaladores existentes quedan activos por el default, por lo que el comportamiento inicial es idéntico al actual).
- **Permisos**: configuración de datos por grupo, corregible desde `/users/groups` sin despliegue. Hay que asignar los permisos al grupo `admin` en cada ambiente (dev/stg/prod) como paso manual, como ya ocurre con `almacen`.
- **Borrado físico de precios**: irreversible por fila. Mitigación: confirmación explícita en la UI que explica el efecto (vuelve el precio del inventario) y backup normal de la base; sin impacto en proformas ya emitidas.
- Sin cambios de infraestructura ni de autenticación.

## Consecuencias

- Instaladores queda alineado con Vehículos/Almacén (activar/desactivar) y desaparece el riesgo de error de integridad al "eliminar".
- Precios por sucursal deja de depender de `sucursales[0]` y valida la unicidad en el servidor, pero la protección en base sigue pendiente (deuda BIZ-07 aceptada conscientemente).
- El admin Django viejo sigue mostrando todos los instaladores (activos e inactivos) y aplicando su propia lógica; hasta que se retire, las dos superficies pueden divergir.
- El supuesto "solo `admin` escribe" queda pendiente de confirmación de negocio; cambiarlo es asignar permisos a otro grupo y ajustar el `hasGroup()` de la UI.
- Una tercera copia de la regla de precio no se crea: no se toca `pricing.py` ni `inventario.py`.
