# PLAN-2026-09-26-modulo-almacen (v1)

**Task:** TASK-modulo-almacen
**DDRs relacionados:** [DDR-modulo-almacen-listado-y-flujo-almacen](../design/DDR-modulo-almacen-listado-y-flujo-almacen.md)
**ADRs relacionados:** [ADR-modulo-almacen-modelo-datos-imagen-soft-delete](../adr/ADR-modulo-almacen-modelo-datos-imagen-soft-delete.md), [ADR-modulo-almacen-permisos-rol-frontend](../adr/ADR-modulo-almacen-permisos-rol-frontend.md)

## Objective

Agregar el módulo Almacén (Láminas, Bobinas, Inventario) a `panel_admin/`, con permisos diferenciados por rol (`admin` CRUD completo, `almacen` solo lectura) validados en backend y reflejados en frontend, reutilizando en todo lo posible el patrón ya probado por `TASK-modulo-usuarios` y `TASK-modulo-vehiculos`.

## Context

Ver `## Investigación`, `## Diseño` y `## Arquitectura` de `TASK-modulo-almacen`. Resumen operativo: `Window_Film` (Lámina), `Window_Film_Reel` (Bobina) e `inventario` ya existen como modelos de dominio; no tienen CRUD administrativo, imagen ni soft delete. `TASK-modulo-vehiculos` (PR #48, ya en `master`) resolvió el mismo problema para otro conjunto de modelos y es el precedente a replicar casi 1:1. El frontend no tiene hoy ningún dato de rol tras el login — se cierra en este plan extendiendo `PanelAdminAuthToken`.

## Current behavior

- `Window_Film` (`praxsa_manager/product/models.py:57-65`): `name`, `description`, `content`. Sin `image` ni `is_active`.
- `Window_Film_Reel` (`models.py:67-80`): FK a `Window_Film`, `width`, `length`, `price`. Sin `is_active`.
- `inventario` (`models.py:131-144`): FK a `Sucursal`/`Window_Film_Reel`, cantidades, precios, fecha, lote. Sin estado.
- Único acceso hoy: Django admin (`admin_config/window_film_reel.py`, `admin_config/inventory.py`) y endpoints públicos de solo lectura (`views.py:46-58`, `views.py:211-217`, rutas `bobina/<pk>`/`layer/<layer_id>` en `urls.py:48-49`).
- `product/serializer/layer_serializer.py` existe y está vacío; `product/custom_views/bobina.py` solo tiene un `GET` puntual.
- `custom_views/auth_token.py:32-54` (`PanelAdminAuthToken`) devuelve `{token, user_id, username, name, lastname}` — sin `groups`/`is_staff`.
- `core/models/user.ts:1-7`, `core/service/auth.service.ts:37-59`: sin campo de rol.
- `panel_admin/src/assets/data/routes.json`: grupos "Usuarios" (líneas 14-58) y "Vehículos" (líneas 59-103) ya existen con el patrón de menú a replicar.
- `panel_admin/src/app/shared/image-upload/image-upload.component.ts`: componente compartido de carga/preview de imagen, ya construido y reutilizable tal cual.
- `serializer/vehicle_serializer.py:54-68` (`validate_car_model_image`): validación de imagen (Pillow, 5MB) a extraer a un módulo compartido.
- `business/inventario.py:14-27` (`Inventario_Business.get_inventario_queryset_by_role`): filtro por sucursal ya implementado, devuelve `None` si el usuario no tiene sucursal (pensado para el admin de Django).

## Expected behavior

- Menú "Almacén" con 3 submenús (Láminas, Bobinas, Inventario), visible para ambos roles.
- `admin`: CRUD completo (crear/editar/eliminar lógico) de Láminas y Bobinas; edición acotada de Inventario.
- `almacen`: solo lectura de los tres listados, sin botones de Crear/Editar/Eliminar/Gestionar.
- Lámina soporta imagen: carga, preview, miniatura en listado, reemplazo al editar, placeholder cuando no hay imagen.
- Registros eliminados (Lámina/Bobina) no aparecen en listados normales ni en selectores, se conservan en base de datos.
- Backend rechaza con `403` cualquier intento de escritura de un usuario sin el `Permission` correspondiente, independientemente de lo que muestre la UI.
- Login de `panel_admin/` devuelve `groups`/`is_staff`, y el frontend los usa para ocultar acciones administrativas.

## Architecture considerations

Resumen operativo de los ADR (ver documentos completos para el detalle y las alternativas descartadas):

- **Modelo de datos**: `Window_Film.image` (`ImageField`, `upload_to='window_films/'`) + `Window_Film.is_active` + `Window_Film_Reel.is_active`. Migración aditiva nueva, sin tocar migraciones existentes (última real: `0108_car_brand_is_active_car_model_image_and_more.py`). `inventario` sin cambios de esquema.
- **Imagen**: reutiliza `MEDIA_ROOT`/`MEDIA_URL` ya configurados (`settings.py:211-212`) y Pillow ya instalado — sin dependencia ni infraestructura nueva. Validación extraída a un módulo compartido para no duplicarla entre Vehículos y Almacén.
- **Soft delete**: `is_active` + filtrado por defecto en `get_queryset()` (`?include_inactive=true`) + endpoint dedicado `toggle-active` — nunca `DELETE` físico ni campo escribible en `create`/`update` (evitar el bug de checkbox HTML ya corregido en Vehículos, `is_active` va `read_only=True` en los serializers).
- **Contrato API**: nuevo bajo `almacen/laminas`, `almacen/bobinas`, `almacen/inventario` — no colisiona con las rutas públicas existentes.
- **Alcance de "Gestionar Inventario"**: acotado a `to_install`, `installed`, `precio_compra_mtr_lineal`, `precio_venta_mtr_lineal`, `nro_lote`. Sin alta manual.
- **Permisos**: `[IsAuthenticated, IsStaffUser, DjangoModelPermissions]` para list/create/detail de Lámina/Bobina; `[IsAuthenticated, IsStaffUser]` + `has_perm` explícito para `toggle-active` y para el `PATCH` de gestionar-inventario. El grupo `almacen` se crea manualmente (vía `/users/groups`, ya construido) sin permisos de escritura sobre los 3 modelos; el grupo `admin` recibe los permisos `add_`/`change_`/`delete_` correspondientes. Esta asignación de permisos es un paso operativo de configuración, no algo que este plan deba scriptear.
- **Brecha de rol en frontend**: `PanelAdminAuthToken` se extiende (aditivo, no rompe nada) con `groups`/`is_staff`; `AuthService.hasGroup()` nuevo. Sin guard de ruta por permiso (fuera de alcance, ver ADR) — el backend es la barrera real.
- **Dinero**: `precio_compra_mtr_lineal`/`precio_venta_mtr_lineal` ya son `DecimalField`; el serializer de "gestionar inventario" debe mantenerlos como `DecimalField`/`serializers.DecimalField`, nunca `float`.
- **Rendimiento**: listados con `select_related`/`prefetch_related` donde aplique (`Window_Film_Reel.window_film`, `inventario.bobina__window_film`, `inventario.sucursal`), siguiendo el patrón ya usado en `admin_config/inventory.py:43-44` y `vehicle_admin.py` (`select_related('car_brand_id')`).

## Proposed solution

Backend: un módulo nuevo `custom_views/almacen_admin.py` con vistas DRF genéricas (mismo estilo que `vehicle_admin.py`), un serializer agrupador `serializer/almacen_serializer.py`, y una función de validación de imagen compartida extraída a `serializer/image_validation.py` (usada por Almacén y por Vehículos). Reutiliza `Inventario_Business.get_inventario_queryset_by_role` para el filtro por sucursal del listado de Inventario, adaptando el caso `None` a un queryset vacío.

Frontend: un módulo nuevo `panel_admin/src/app/almacen/` con 3 sub-áreas (`laminas/` con páginas separadas list/create/edit/view + `app-image-upload`; `bobinas/` con listado + modal inline; `inventario/` con listado + modal "Gestionar" solo-admin), siguiendo exactamente los dos patrones de pantalla ya establecidos por Vehículos (entidad rica vs. entidad simple). `AuthService`/`user.ts` extendidos con `groups`, y `hasGroup()` usado en los templates para ocultar acciones.

## Files/components affected

**Backend (`praxsa_manager/product/`)**
- `models.py` — agregar `image`/`is_active` a `Window_Film`, `is_active` a `Window_Film_Reel`.
- `migrations/010X_window_film_image_is_active_window_film_reel_is_active.py` — nueva, aditiva.
- `serializer/image_validation.py` — nuevo (extrae `validate_car_model_image` de `vehicle_serializer.py`, renombrada a algo genérico como `validate_uploaded_image`).
- `serializer/vehicle_serializer.py` — actualizar el import para usar la función extraída (sin cambiar su comportamiento).
- `serializer/almacen_serializer.py` — nuevo: `WindowFilmSerializer`, `WindowFilmReelSerializer`, `InventarioSerializer` (lectura), `InventarioUpdateSerializer` (los 5 campos editables).
- `custom_views/almacen_admin.py` — nuevo: `WindowFilmListCreateView`, `WindowFilmDetailView`, `WindowFilmToggleActiveView`, `WindowFilmReelListCreateView`, `WindowFilmReelDetailView`, `WindowFilmReelToggleActiveView`, `InventarioListView`, `InventarioUpdateView`.
- `urls.py` — agregar rutas `almacen/laminas`, `almacen/laminas/<pk>/`, `almacen/laminas/<pk>/toggle-active/`, `almacen/bobinas`, `almacen/bobinas/<pk>/`, `almacen/bobinas/<pk>/toggle-active/`, `almacen/inventario`, `almacen/inventario/<pk>/`.
- `helper/user.py` — agregar `is_request_user_almacen`.
- `business/inventario.py` — adaptar `get_inventario_queryset_by_role` (o envolverla en la vista) para devolver queryset vacío en vez de `None`.
- `custom_views/auth_token.py` — extender `PanelAdminAuthToken.post()` con `is_staff`/`groups`.
- `tests/helpers.py` — ya tiene `create_window_film`, `create_window_film_reel`, `create_inventario`, `add_user_to_group`, `create_staff_user_with_token` — reutilizar tal cual, sin cambios.
- `tests/test_almacen_module.py` — nuevo.
- `tests/test_panel_admin_auth.py` — extender el caso existente para cubrir `groups`/`is_staff` en la respuesta.

**Frontend (`panel_admin/src/app/`)**
- `assets/data/routes.json` — agregar grupo "Almacén" (3 submenús).
- `app.routes.ts` — registrar `path: 'almacen'` con `loadChildren` hacia `almacen.routes.ts`.
- `core/models/user.ts` — agregar `groups: string[]`.
- `core/service/auth.service.ts` — mapear `groups` del response; agregar `hasGroup(name: string): boolean`.
- `almacen/almacen.model.ts` — `AppWindowFilm`, `AppWindowFilmReel`, `AppInventario`.
- `almacen/almacen.service.ts` — llamadas HTTP a los 8 endpoints nuevos.
- `almacen/almacen.routes.ts` — rutas del módulo.
- `almacen/laminas/laminas-list.component.{ts,html}` — listado con miniatura, búsqueda client-side, acciones por rol.
- `almacen/laminas/lamina-create.component.{ts,html}` — formulario + `app-image-upload`.
- `almacen/laminas/lamina-edit.component.{ts,html}` — idem, con imagen actual precargada.
- `almacen/laminas/lamina-view.component.{ts,html}` — detalle de solo lectura.
- `almacen/bobinas/bobinas-list.component.{ts,html}` — listado + modal inline (patrón Marca/Item).
- `almacen/inventario/inventario-list.component.{ts,html}` — listado + modal "Gestionar" (solo `admin`).
- Specs `.spec.ts` correspondientes a cada componente nuevo (siguiendo `models-list.component.spec.ts`/`brands-list.component.spec.ts` como referencia).

## Implementation steps

1. Migración: agregar `image`/`is_active` a `Window_Film`, `is_active` a `Window_Film_Reel`; correr `makemigrations`/`migrate` local; verificar `makemigrations --check --dry-run` limpio.
2. Extraer `validate_car_model_image` de `vehicle_serializer.py` a `serializer/image_validation.py` (renombrar genéricamente); actualizar el import en `vehicle_serializer.py`; correr los tests existentes de Vehículos para confirmar que no se rompió nada.
3. Crear `serializer/almacen_serializer.py`: `WindowFilmSerializer` (con `is_active` read-only, validación de imagen vía el módulo compartido, borrado del archivo anterior en `update()` igual que `CarModelSerializer`), `WindowFilmReelSerializer` (con `is_active` read-only, `window_film` como `PrimaryKeyRelatedField` restringido a `is_active=True`), `InventarioSerializer` (lectura completa) e `InventarioUpdateSerializer` (solo los 5 campos editables, `Decimal` para precios).
4. Adaptar `Inventario_Business.get_inventario_queryset_by_role` (o envolverla) para devolver `inventario.objects.none()` en vez de `None` cuando el usuario no tiene sucursal asignada.
5. Crear `custom_views/almacen_admin.py` con las 8 vistas (list/create/detail/toggle-active para Lámina y Bobina; list/update para Inventario), mismo patrón de permisos que `vehicle_admin.py` (`_STANDARD_PERMISSIONS`, `has_perm` explícito en toggle-active/gestionar), filtro `?include_inactive=true` y `?search=` en los listados de Lámina/Bobina.
6. Agregar las rutas nuevas a `urls.py` bajo el prefijo `almacen/`.
7. Agregar `is_request_user_almacen` a `helper/user.py`.
8. Extender `PanelAdminAuthToken.post()` (`custom_views/auth_token.py`) con `is_staff`/`groups` en la respuesta.
9. Escribir `tests/test_almacen_module.py`: CRUD de Lámina (con y sin imagen), CRUD de Bobina, toggle-active de ambos (incluida la verificación de que `is_active` no se puede setear vía `create`/`update` normal), listado de Inventario filtrado por sucursal, `PATCH` de gestionar-inventario (campos permitidos y rechazo de campos no permitidos), y permisos: usuario `almacen` recibe `403` en escritura, usuario `admin` puede todo. Extender `test_panel_admin_auth.py` para `groups`/`is_staff`.
10. Correr `python manage.py test` completo y `makemigrations --check --dry-run` antes de pasar a frontend.
11. Frontend: agregar grupo "Almacén" a `routes.json` y registrar `almacen.routes.ts` en `app.routes.ts`.
12. Extender `core/models/user.ts` (`groups: string[]`) y `core/service/auth.service.ts` (mapear `groups`, agregar `hasGroup()`); actualizar el test existente de `auth.service.spec.ts` si existe.
13. Crear `almacen/almacen.model.ts` y `almacen/almacen.service.ts` (llamadas a los 8 endpoints).
14. Construir `laminas-list`/`lamina-create`/`lamina-edit`/`lamina-view` reutilizando literalmente `app-image-upload` y el layout de `models-list`/`model-create`/`model-edit`/`model-view` de Vehículos, con las acciones envueltas en `*ngIf="authService.hasGroup('admin')"`.
15. Construir `bobinas-list` reutilizando el layout de `brands-list` (modal inline), con el selector de Lámina restringido a activas.
16. Construir `inventario-list` (listado de solo lectura + modal "Gestionar" visible solo para `admin`).
17. Escribir specs de cada componente nuevo (`TestBed` + mocks del service, siguiendo `models-list.component.spec.ts`/`brands-list.component.spec.ts`).
18. Correr `ng build`, `ng lint`, `ng test` completos.
19. Verificación manual end-to-end en navegador (ver Test strategy): login como `admin` y como `almacen` (dos usuarios de prueba), recorrer los 3 listados, crear/editar/eliminar una Lámina con imagen, crear/editar/eliminar una Bobina, gestionar una fila de Inventario, confirmar que `almacen` no ve ninguna acción de escritura y que un intento directo contra el endpoint con ese usuario devuelve `403`.

## Test strategy

**Backend (unitario/integración, `praxsa_manager/product/tests/`)**: obligatorio por `docs/CLAUDE.md` ("todo cambio de lógica de negocio lleva su test"). Casos concretos en `test_almacen_module.py`:
- Lámina: crear con y sin imagen (multipart), listar (default solo activas, `?include_inactive=true`), editar (incluye reemplazo de imagen, verificar que el archivo anterior se borra), `toggle-active` (verificar que `is_active` no es escribible vía `create`/`update` normal — replica el caso `REV-2026-09-26-modulo-vehiculos-01`), validación de imagen (tipo/tamaño rechazados).
- Bobina: crear/editar/`toggle-active`, selector de Lámina restringido a activas.
- Inventario: `GET` filtrado por sucursal (usuario con sucursal ve solo la suya, `admin` ve todas, usuario sin sucursal ve vacío — no `None`/error), `PATCH` de gestionar (campos permitidos aceptados, campos no permitidos ignorados/rechazados, `Decimal` preservado sin conversión a `float`).
- Permisos: usuario `almacen` (sin permisos de escritura) recibe `403` en `POST`/`PATCH`/`toggle-active`/gestionar-inventario de los 3 recursos; usuario `admin` (con permisos) puede todo; usuario no-staff autenticado recibe `403` en todo (vía `IsStaffUser`).
- `PanelAdminAuthToken`: la respuesta de login incluye `groups`/`is_staff` correctos para un usuario con grupos asignados.

**Frontend (unitario, Angular `TestBed`)**: specs por componente (mock de `AlmacenService`/`AuthService` vía `HttpTestingController` o spies, siguiendo `models-list.component.spec.ts`) cubriendo: carga y render del listado, comportamiento de búsqueda client-side, ocultamiento de acciones cuando `hasGroup('admin')` es `false`, envío de formulario con y sin imagen nueva en Lámina (distinguiendo `dirty` como ya hace `model-edit.component.ts:70`).

**E2E: no corresponde.** Este cambio es un CRUD administrativo más (tercer módulo del mismo tipo, Usuarios y Vehículos no llevaron E2E), no un flujo crítico de negocio de punta a punta como login→proforma→pago; la combinación de tests unitarios/integración de backend (que ya validan el contrato real de la API) y specs de frontend con mocks cubre el riesgo real sin necesitar Playwright, que además no está instalado en `panel_admin/package.json` (instalarlo sería una dependencia nueva a confirmar, y no está justificado para este alcance). La verificación manual del paso 19 cubre el riesgo residual de integración real navegador↔backend antes de dar el módulo por terminado.

## Acceptance criteria

- [ ] Migración aplicada, `makemigrations --check --dry-run` sin cambios pendientes.
- [ ] Menú "Almacén" visible con 3 submenús, mismo estilo visual que "Usuarios"/"Vehículos".
- [ ] `admin` puede crear/editar/eliminar (lógico) Láminas y Bobinas, y gestionar Inventario, desde la UI.
- [ ] `almacen` ve los 3 listados sin ninguna acción de Crear/Editar/Eliminar/Gestionar.
- [ ] Un usuario `almacen` que llame directamente `POST`/`PATCH`/`DELETE`/`toggle-active` sobre cualquiera de los 3 recursos recibe `403`, verificado con un test automático (no solo manual).
- [ ] Lámina: imagen se carga, se previsualiza, se muestra como miniatura en el listado, se reemplaza al editar (borrando el archivo anterior), y muestra un placeholder cuando no hay imagen.
- [ ] Bobina/Lámina eliminadas (soft delete) no aparecen en el listado por defecto ni en los selectores de creación/edición, y siguen en la base de datos.
- [ ] `python manage.py test` completo en verde; `ng build`/`ng lint`/`ng test` sin errores nuevos.
- [ ] `PanelAdminAuthToken` devuelve `groups`/`is_staff`; `AuthService.hasGroup()` funciona con un test.

## Risks

- **El grupo `almacen` no existe en ningún ambiente todavía** — es un paso manual de configuración (crear el grupo y asignarle nada de escritura sobre los 3 modelos; crear/actualizar el grupo `admin` con los permisos nuevos), no algo que el código resuelva solo. Mitigación: documentarlo explícitamente en el PR como paso operativo pendiente antes de que el rol `almacen` sea usable en un ambiente real.
- **Adaptar `get_inventario_queryset_by_role`** podría afectar al admin de Django que ya la usa (`admin_config/inventory.py:43-55`), si ese código dependía de que devolviera `None` en algún caso. Mitigación: correr los tests existentes de ese admin (si los hay) tras el cambio, y preferir envolver la función en la vista nueva (sin modificar su comportamiento actual) si el riesgo de tocarla se confirma real durante la implementación.
- **Extraer `validate_car_model_image` a un módulo compartido** toca código de Vehículos ya en producción (mergeado). Mitigación: es un movimiento de función sin cambiar su lógica; correr `test_vehicle_admin_module` (o el nombre real de sus tests) después del refactor para confirmar cero regresión.
- **Tamaño del cambio**: 8 endpoints backend + 6+ componentes frontend + extensión de auth — comparable a Usuarios/Vehículos, ambos terminaron con más de una vuelta de review. Mitigación: los pasos 1-10 (backend) y 11-19 (frontend) son verificables de forma independiente; se puede entregar y revisar el backend antes de completar el frontend si el PR se vuelve difícil de revisar de una sola vez (a decidir con el usuario si conviene partir en dos PRs — ver Out of scope).

## Out of scope

- Guard de ruta por permiso en el frontend (bloquear la navegación, no solo ocultar botones) — decisión explícita del ADR de permisos, no de este plan.
- Alta manual de filas de Inventario (`POST`) — el pedido no lo exige.
- Cascada de soft-delete (desactivar Lámina no desactiva sus Bobinas) — consistente con `ADR-modulo-vehiculos-soft-delete.md`.
- Creación automática (migración de datos) del grupo `almacen` — se crea manualmente, mismo criterio que los grupos existentes.
- Pregunta abierta para el usuario: ¿se prefiere un solo PR con backend+frontend completos (como hicieron Usuarios y Vehículos), o partir en dos PRs (backend primero, frontend después) dado el tamaño del cambio? Este plan asume **un solo PR**, consistente con el precedente, pero se puede ajustar si el usuario prefiere partirlo.

## Dependencias nuevas

Ninguna. Pillow ya está instalado (`requirements-3.8.10.txt:21`); `MEDIA_ROOT`/`MEDIA_URL` ya configurados; `app-image-upload` ya existe en `panel_admin/src/app/shared/`; `ngx-datatable` ya es dependencia de `panel_admin/`.
