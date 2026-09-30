# PLAN-2026-09-30-agrupacion-menu-instalador-precio-sucursal (v1)

**Task:** TASK-agrupacion-menu-instalador-precio-sucursal
**DDRs relacionados:** [DDR-agrupacion-menu-instalador-precio-sucursal-menu-y-pantallas](../design/DDR-agrupacion-menu-instalador-precio-sucursal-menu-y-pantallas.md)
**ADRs relacionados:** [ADR-agrupacion-menu-instalador-precio-sucursal-api-permisos-borrado](../adr/ADR-agrupacion-menu-instalador-precio-sucursal-api-permisos-borrado.md)

## Objective
Exponer en `panel_admin/` la administración de **Instaladores** (dentro del grupo de menú Usuarios) y de **Precios por sucursal** (dentro de Almacén), con su API en `praxsa_manager`. Solo el rol `admin` puede crear, editar y eliminar; los demás roles solo leen (regla confirmada por el usuario el 2026-09-30).

## Context
Ver `TASK-agrupacion-menu-instalador-precio-sucursal`. Los modelos `instalador` y `precio_venta_sucursal` hoy solo se administran desde el admin Django viejo. El DDR fija el menú y las pantallas (listado `ngx-datatable` + modal); el ADR fija permisos, alcance por sucursal, unicidad y borrado.

## Current behavior
- `instalador` (`praxsa_manager/product/models.py:131-137`): sin `is_active`. Se consulta solo desde `OrdenesInstaladoresView` (`custom_views/ordenes_admin.py:414-423`) y se valida al asignar en `NotaTrabajoUpdateSerializer.validate` (`serializer/ordenes_serializer.py:381-391`).
- `precio_venta_sucursal` (`models.py:328-334`): sin API; el admin viejo (`admin_config/precio_venta_sucursal.py`) acota por `sucursales[0]` y valida duplicados solo en `save_model`.
- Menú (`panel_admin/src/assets/data/routes.json`): Usuarios tiene Credenciales/Grupos/Sucursales; Almacén tiene Láminas/Bobinas/Inventario.
- Existe precedente para dar permisos a grupos con un comando idempotente: `management/commands/asignar_permisos_estados.py`.
- Última migración: `0111_estados_orden.py`.

## Expected behavior
- Menú Usuarios ▸ **Instaladores** (`/users/instaladores`) y Almacén ▸ **Precios por sucursal** (`/almacen/precios-sucursal`), visibles para todo el personal.
- Todos los roles staff ven los listados. Solo con `hasGroup('admin')` aparecen Nuevo/Editar/Eliminar; sin el permiso Django correspondiente, el backend responde `403` a cualquier escritura.
- "Eliminar" un instalador lo desactiva (deja de aparecer en el selector de Notas de Trabajo y no se puede asignar). "Eliminar" un precio borra la fila (la cotización vuelve al precio del inventario).
- No se puede guardar dos precios con la misma sucursal + lámina + ancho.

## Architecture considerations
Resumen del ADR (no se re-decide aquí):
- **API**: rutas nuevas y aditivas; único endpoint existente que cambia es `ordenes/catalogo/instaladores` (excluye inactivos). Sin impacto en `proforma/`.
- **Datos**: una migración aditiva (`instalador.is_active`, default `True`), reversible; los instaladores actuales quedan activos.
- **Dinero**: `precio_venta` y `width` en `Decimal` (`DecimalField` ya existente); validación `> 0`.
- **Permisos**: `DjangoModelPermissions` + `IsStaffUser` (patrón de Almacén/Vehículos); permisos `add/change/delete` de ambos modelos asignados al grupo `admin`. La UI oculta botones pero no es la barrera.
- **Alcance**: Precios usa `User_Helper.get_sucursales_in_scope` (admin ve todas; otros, las suyas) para listado y validación de escritura; esto reemplaza `sucursales[0]`.
- **Rendimiento**: los listados usan `select_related`/`prefetch_related` (sucursal, lámina; sucursales del instalador) para evitar N+1.
- **Unicidad**: validación en serializer; el `UniqueConstraint` en base queda diferido (BIZ-07).

## Proposed solution
Backend: campo `is_active` en `instalador`, serializers y vistas nuevas siguiendo `almacen_admin.py`, filtro de inactivos en Órdenes y un comando para asignar permisos al grupo `admin`. Frontend: dos listados con modal siguiendo `brands-list` / `bobinas-list`, servicios y modelos tipados, rutas y entradas de menú.

## Files/components affected

**Backend (`praxsa_manager/product/`)**
- `models.py` — `instalador.is_active`.
- `migrations/0112_instalador_is_active.py` — nueva (autogenerada).
- `serializer/instalador_precio_serializer.py` — nuevo: `InstaladorSerializer`, `PrecioVentaSucursalSerializer`.
- `custom_views/instalador_admin.py` — nuevo: listado/creación, detalle, `toggle-active`.
- `custom_views/almacen_admin.py` — vistas de Precios por sucursal (listado/creación, detalle con `DELETE`).
- `urls.py` — rutas nuevas.
- `custom_views/ordenes_admin.py` (`OrdenesInstaladoresView`) y `serializer/ordenes_serializer.py` (`NotaTrabajoUpdateSerializer.validate`) — excluir instaladores inactivos.
- `management/commands/asignar_permisos_instalador_precio.py` — nuevo, idempotente, mismo estilo que `asignar_permisos_estados`.
- `tests/test_instaladores_precios_module.py` — nuevo; ajustes menores en `tests/test_ordenes_notas_trabajo.py`.

**Frontend (`panel_admin/src/`)**
- `assets/data/routes.json` — dos entradas de submenú.
- `app/users/users.model.ts`, `users.service.ts`, `users.routes.ts`; `app/users/instaladores/instaladores-list.component.{ts,html,spec.ts}` — nuevos.
- `app/almacen/almacen.model.ts`, `almacen.service.ts`, `almacen.routes.ts`; `app/almacen/precios-sucursal/precios-sucursal-list.component.{ts,html,spec.ts}` — nuevos.

## Implementation steps

**Fase 1 — Backend**
1. Agregar `is_active = models.BooleanField(default=True, verbose_name="Activo")` a `instalador` y generar `0112` con `makemigrations`; comprobar que solo contiene el `AddField`.
2. Crear `InstaladorSerializer`: campos `id`, `name`, `address`, `phonenumber`, `sucursal` (lista de ids, al menos una), `sucursal_names` (solo lectura) e `is_active` (solo lectura). Reusar el `RegexValidator` del modelo.
3. Crear `PrecioVentaSucursalSerializer`: `id`, `sucursal`, `sucursal_name`, `lamina`, `lamina_name` (solo lectura), `width`, `precio_venta`. Validaciones: `width > 0`, `precio_venta > 0`, sucursal dentro de `get_sucursales_in_scope` del solicitante, lámina activa, y unicidad sucursal + lámina + ancho excluyendo la propia fila al editar (mensaje en español).
4. Crear `custom_views/instalador_admin.py`: `InstaladorListCreateView` (solo activos por defecto, `?include_inactive=true`, `?search=`), `InstaladorDetailView` (`get`, `patch`), `InstaladorToggleActiveView` (`has_perm('product.change_instalador')`, mismo contrato que `CarBrandToggleActiveView`).
5. En `custom_views/almacen_admin.py`, agregar `PrecioVentaSucursalListCreateView` y `PrecioVentaSucursalDetailView` (`get`, `patch`, `delete`) con `_STANDARD_PERMISSIONS`; queryset con `select_related('sucursal', 'lamina')` filtrado por sucursales en alcance; `?sucursal=` y `?search=` opcionales.
6. Registrar en `urls.py`: `instaladores`, `instaladores/<pk>/`, `instaladores/<pk>/toggle-active/`, `almacen/precios-sucursal`, `almacen/precios-sucursal/<pk>/`.
7. En `OrdenesInstaladoresView` filtrar `is_active=True`; en `NotaTrabajoUpdateSerializer.validate` rechazar un instalador inactivo con mensaje claro.
8. Crear el comando `asignar_permisos_instalador_precio` (grupo `Admin`: `add/change/delete_instalador` y `add/change/delete_precio_venta_sucursal`; falla con mensaje si el grupo no existe; opción `--dry-run`).
9. Tests del backend (ver Test strategy) y correr la suite completa.

**Fase 2 — Frontend**
10. Agregar tipos `AppInstalador` y `AppPrecioSucursal` y los métodos de servicio (listado, crear, editar, activar/desactivar instalador, borrar precio) en `users.service.ts` y `almacen.service.ts`.
11. Crear `InstaladoresListComponent`: `ngx-datatable` con búsqueda en el navegador, modal reactivo (nombre, dirección, teléfono, `ng-select` de sucursales), botones Nuevo/Editar/Eliminar visibles solo con `hasGroup('admin')`, confirmación con SweetAlert2 ("desactivar"), mensajes de error del servidor en el modal.
12. Crear `PreciosSucursalListComponent`: mismo patrón; selects de sucursal (`ordenes/catalogo/sucursales`, ya acotado al alcance) y de lámina (solo activas), ancho y precio; confirmación de borrado que explica que la cotización vuelve al precio del inventario.
13. Agregar las rutas (`users/instaladores`, `almacen/precios-sucursal`) y las dos entradas en `routes.json` (clase `ml-menu`).
14. Specs de ambos componentes y de los métodos de servicio.

**Fase 3 — Verificación**
15. `manage.py test`, `makemigrations --check --dry-run`, `ng build`, `ng lint` y `ng test`; prueba manual en el navegador con un usuario `admin` y con uno de solo lectura (ver Acceptance criteria).

## Test strategy
**Backend** (`tests/test_instaladores_precios_module.py`, con `helpers.py`):
- Instaladores: lista solo activos por defecto y todos con `include_inactive`; búsqueda por nombre; crear con sucursales; teléfono inválido → 400; sin sucursales → 400; `toggle-active` desactiva y reactiva.
- Permisos: usuario staff sin permisos puede `GET` pero recibe `403` en `POST`/`PATCH`/`toggle-active`/`DELETE`; usuario con permisos de `admin` puede escribir; usuario no staff recibe `403` en todo.
- Precios: crea; duplicado sucursal+lámina+ancho → 400; editar la misma fila no falla por unicidad; `width`/`precio_venta` ≤ 0 → 400; lámina inactiva → 400; `DELETE` borra la fila y `pricing` vuelve al precio del inventario (se reutiliza `helpers` de `precio_venta_sucursal`).
- Alcance: usuario no admin con permiso solo lista/escribe sobre sus sucursales (una sucursal ajena → 400/403); admin ve todas.
- Órdenes: `ordenes/catalogo/instaladores` no incluye inactivos; asignar un instalador inactivo en el PATCH de Nota de Trabajo → 400; notas ya asignadas conservan el nombre.
- Comando: asigna la matriz, es idempotente, `--dry-run` no escribe, grupo inexistente → `CommandError` sin cambios.
- Migración: los instaladores existentes quedan `is_active=True`.

**Frontend** (`TestBed` + `HttpTestingController`, patrón de `bobinas-list.component.spec.ts`):
- Servicios: URL, método y cuerpo de cada llamada.
- Listados: renderiza filas; búsqueda filtra; botones de escritura visibles solo con `hasGroup('admin')`; el modal valida campos requeridos; muestra error del servidor; la confirmación de borrado/desactivación llama al servicio.

**E2E (Playwright): no corresponde.** No es un flujo crítico multi-paso ni cambia navegación existente (son dos pantallas CRUD independientes, como Vehículos y Almacén, que se probaron a nivel unitario/integración), y Playwright no está instalado en el repo; los tests de API más los de componente cubren el contrato y los permisos.

## Acceptance criteria
- [ ] El menú muestra Usuarios ▸ Instaladores y Almacén ▸ Precios por sucursal, sin grupo nuevo.
- [ ] Un usuario `admin` puede crear, editar y eliminar (desactivar) instaladores, y crear, editar y eliminar precios.
- [ ] Un usuario de otro rol ve ambos listados, no ve botones de escritura y recibe `403` si llama a la API directamente.
- [ ] Un instalador desactivado no aparece en el selector de Notas de Trabajo ni se puede asignar; las notas antiguas siguen mostrando su nombre.
- [ ] No se pueden guardar dos precios con la misma sucursal + lámina + ancho.
- [ ] Un usuario no admin solo ve/gestiona los precios de sus sucursales.
- [ ] Sin `float` en ningún cálculo o campo de precio.
- [ ] `manage.py test` verde, `makemigrations --check` limpio, `ng build`/`ng lint` limpios, specs nuevos verdes.

## Risks
- **Duplicados existentes en producción** (sin constraint en base): la validación solo impide nuevos; los previos siguen. Mitigación: chequeo de datos y `UniqueConstraint` en un task aparte (deuda BIZ-07 aceptada).
- **Permisos sin asignar** en cada ambiente: sin ejecutar el comando, ni `admin` puede escribir (falla cerrado). Mitigación: paso explícito en el despliegue y mensaje claro del comando.
- **Nombre "Instalador"** ya usado como rol Django: riesgo de confusión; mitigado con el nombre de menú "Instaladores".
- **Admin Django viejo** sigue mostrando todo y sin `is_active`: puede divergir hasta retirarse.
- **Fallas de tests frontend preexistentes** (se registraron 15 en tasks anteriores): distinguir las nuevas de las heredadas. Sin mitigación de fondo en este task.
- Un instalador cuyas sucursales se editan puede quedar asignado a una nota de una sucursal que ya no cubre; la validación es solo al asignar (aceptado).

## Out of scope
- `UniqueConstraint` en base para precios y saneo de duplicados.
- Vincular instalador con `User`, o cambiar el rol Django `instalador`.
- Retirar o modificar el admin Django viejo.
- Mover `installation_price` fuera de Vehículos ▸ Items.
- Guard de ruta por permiso en Angular.
- Preguntas abiertas: ninguna pendiente de negocio (la regla de permisos quedó confirmada).

## Dependencias nuevas
Ninguna (`ng-select`, `sweetalert2` y `ngx-datatable` ya están instalados en `panel_admin/`).
