# PLAN-2026-09-26-modulo-vehiculos (v2)

**Task:** TASK-modulo-vehiculos
**DDRs relacionados:** [DDR-modulo-vehiculos-listado-y-flujo-vehiculos](../design/DDR-modulo-vehiculos-listado-y-flujo-vehiculos.md)
**ADRs relacionados:** [ADR-modulo-vehiculos-relacion-modelo-item](../adr/ADR-modulo-vehiculos-relacion-modelo-item.md), [ADR-modulo-vehiculos-soft-delete](../adr/ADR-modulo-vehiculos-soft-delete.md), [ADR-modulo-vehiculos-almacenamiento-imagenes](../adr/ADR-modulo-vehiculos-almacenamiento-imagenes.md)

## Objective

Agregar al panel `panel_admin/` un módulo "Vehículos" (Marcas, Modelos, Items) con CRUD completo y borrado lógico, para que el personal administrativo pueda mantener el catálogo de `Car_Brand`/`Car_Model`/`Car_Part` sin pasar por Django Admin, incluyendo la imagen del vehículo por Modelo y la asociación Modelo↔Item (`Car_Model_Part`) con sus datos de precio de instalación.

## Context

Ver `docs/tasks/TASK-modulo-vehiculos.md` (`## Investigación`, `## Diseño`, `## Arquitectura`) para el detalle completo. Resumen de lo ya decidido, no se reabre en este plan:

- **Modelos ya existen**: `Car_Brand`, `Car_Model`, `Car_Part`, `Car_Model_Part` (`praxsa_manager/product/models.py:16-55`), gestionados hoy solo por Django Admin, sin API REST.
- **Relación Modelo↔Item** (ADR relacion-modelo-item): es `Car_Model_Part`, N─N real con `width`/`length`/`quantity`/`installation_price` propios, consultada en vivo por la calculadora de precios de proformas (`invoice_serializer.py:46-67`, `business/proforma.py:90-92`). No se crea tabla nueva. Asociar un item a un modelo desde el panel **debe** capturar esos 4 campos, no solo el item, para no crear asociaciones con costo $0 silencioso.
- **Soft delete** (ADR soft-delete): `is_active` (default `True`) nuevo en `Car_Brand`/`Car_Model`/`Car_Part`, filtrado por defecto en cada vista (mismo patrón que `UserListCreateView`, `product/custom_views/user_admin.py:26-30`), toggle vía endpoint dedicado (mismo patrón que `UserToggleActiveView`, `user_admin.py:82-106`). Sin cascada automática.
- **Imágenes** (ADR almacenamiento-imagenes): `Car_Model.image` (`ImageField`, opcional), `MEDIA_ROOT`/`MEDIA_URL` nuevos en `settings.py`, validación de tipo/tamaño (jpg/png/webp, 5 MB) en el serializer, reemplazo borra el archivo anterior. Infraestructura: volumen Docker `media` + `location /media/` en nginx (prod/stg), sin cambios en dev.
- **UI** (DDR listado-y-flujo-vehiculos, corregido en v2): `ngx-datatable` igual que Credenciales (mismos íconos/estilo de acciones: `eye`/`edit-2`/`trash-2`), **búsqueda reutilizando el patrón ya existente en `advance-table.component.html:29-35`/`.ts:231-257`** (markup `table-search-area` + método `filterDatatable()`, copiado y adaptado por lista — no un componente nuevo), un único componente nuevo en `shared/` (`image-upload`), paginación client-side, modal (`NgbModal`) para Marca/Item (formulario de un campo), página propia para Modelo (marca + nombre + imagen) y para el detalle de Modelo (imagen + items + modal "Agregar item").

## Current behavior

- `Car_Brand`/`Car_Model`/`Car_Part`/`Car_Model_Part` sin serializer, sin vista DRF, sin entrada en `praxsa_manager/product/urls.py` más allá de 3 funciones de lectura para la calculadora (`urls.py:22,25,27`). Todo el mantenimiento es vía Django Admin (`product/admin.py:34-37`, `product/admin_config/car_brand.py`, `car_model.py`).
- `panel_admin/src/assets/data/routes.json` no tiene ninguna entrada "Vehículos" — solo "Dashboard" y "Usuarios" (con Credenciales/Grupos/Sucursales).
- No existe carpeta `shared/` en `panel_admin/src/app/`.
- **Sí existe un patrón de búsqueda funcional en `panel_admin/src/app/advance-table/advance-table.component.html:29-35` y `.ts:231-257`** (markup + `filterDatatable()`, filtra por substring en cualquier columna y resetea la página) — no usado hoy por Credenciales, pero disponible para reutilizar.
- No existe `MEDIA_ROOT`/`MEDIA_URL` en `praxsa_manager/praxsa_manager/settings.py` (solo `STATIC_URL`/`STATICFILES_DIRS`/`STATIC_ROOT`, líneas 199-209).

## Expected behavior

- El sidebar muestra "Vehículos" con 3 submenús: Marcas, Modelos, Items.
- Cada uno lista, busca (client-side) y pagina (client-side, `ngx-datatable`) sus registros activos, con acciones Ver/Editar/Eliminar (mismos íconos/estilo que Credenciales) y Eliminar = soft delete (`is_active=False`, no aparece más en listas ni selectores).
- Marca: CRUD de un campo (`name`), vía modal. La tabla muestra además la cantidad de modelos asociados.
- Modelo: CRUD con selección de Marca (obligatoria, solo marcas activas), nombre, e imagen opcional con preview/reemplazo/eliminación; la tabla muestra thumbnail (o placeholder) + marca + nombre + cantidad de items.
- Detalle de Modelo: imagen grande (o placeholder), marca, nombre, lista de items asociados con su configuración de instalación, botón "Agregar item" (crear nuevo item + asociar, o buscar item activo existente + asociar) capturando ancho/largo/cantidad/precio de instalación, y acción para quitar una asociación existente.
- Item: CRUD de un campo (`name`), vía modal.
- El backend valida todo de nuevo del lado servidor (marca obligatoria y activa, nombre único donde aplique, tipo/tamaño de imagen, unicidad de la asociación Modelo-Item) independientemente de lo que el frontend ya valide.

## Architecture considerations

Ya resueltas en los 3 ADR listados arriba — este plan las traduce a pasos de implementación, no las reabre. Puntos que sí ameritan atención al implementar:

- **Contrato API nuevo, sin consumidores previos**: no rompe nada existente (Angular no consume hoy `Car_Brand`/`Car_Model`/`Car_Part` desde `panel_admin/`; los 3 endpoints de calculadora que sí se usan desde `proforma/` no se tocan).
- **Dinero**: `installation_price` ya es `Decimal` en el modelo — el serializer de asociación debe mantenerlo así, nunca `float`, igual que el resto del proyecto.
- **Despliegue backend/infra coordinado**: el cambio de imágenes requiere que el volumen Docker `media` y el bloque nginx `/media/` existan en `stg`/`prod` **antes o junto con** el despliegue del código que sirve imágenes — ver ADR almacenamiento-imagenes, sección de rollback. En este entorno de desarrollo (worktree, sin Docker) no aplica, pero debe quedar explícito en el PR para quien despliegue.
- **N+1**: el conteo de "modelos asociados" por Marca y "items asociados" por Modelo debe hacerse con `annotate(Count(...))` en el queryset del listado, no con una consulta por fila.

## Proposed solution

### Backend (`praxsa_manager/product/`)

1. **Migración `is_active`**: nueva migración que agrega `is_active = models.BooleanField(default=True)` a `Car_Brand`, `Car_Model`, `Car_Part` (no se toca ninguna migración existente).
2. **Migración `image`**: nueva migración que agrega `image = models.ImageField(upload_to='car_models/', null=True, blank=True, verbose_name="Imagen")` a `Car_Model`.
3. **Settings**: agregar `MEDIA_URL = '/media/'` y `MEDIA_ROOT = BASE_DIR / 'media'` en `praxsa_manager/praxsa_manager/settings.py`, junto a la configuración de estáticos (líneas 199-209). Agregar `+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)` a las `urlpatterns` raíz del proyecto cuando `DEBUG=True` (patrón estándar de Django, para que las imágenes se vean en desarrollo local sin nginx).
4. **Serializers nuevos** (`praxsa_manager/product/serializer/`, un archivo nuevo, p. ej. `vehicle_serializer.py`, siguiendo el patrón ya usado por `user_admin_serializer.py`):
   - `CarBrandSerializer`: `id`, `name`, `is_active`, `models_count` (`SerializerMethodField` o anotación pasada por el queryset). Validación de `name` único entre marcas activas (el campo ya es `unique=True` a nivel de BD, así que el error de integridad ya existe; el serializer solo debe convertirlo en un mensaje claro en vez de un 500).
   - `CarModelSerializer`: `id`, `name`, `car_brand_id` (`PrimaryKeyRelatedField`, queryset filtrado a `is_active=True`), `image` (URL absoluta de lectura, `ImageField` de escritura), `items_count`. `validate_image()`: tipo (jpg/jpeg/png/webp verificado con Pillow, no solo extensión) y tamaño (≤ 5 MB). En `update()`: si llega una imagen nueva o se pide eliminar la actual, borrar el archivo físico anterior (`old_image.delete(save=False)`) antes de asignar/limpiar.
   - `CarPartSerializer`: `id`, `name`, `is_active`.
   - `CarModelPartSerializer` (asociación): `car_part_id` (crear nuevo item inline **o** referenciar uno existente activo — replicar el patrón de "nested writable" ya usado por `UserCreateSerializer` para crear relacionados atómicamente), `width`, `length`, `quantity`, `installation_price`, todos requeridos (no confiar en los defaults del modelo para esta vía de creación — ver ADR relacion-modelo-item). Validación explícita de la `UniqueConstraint` (`unique_model_item`) con mensaje de negocio claro antes de que suba como error de integridad.
5. **Vistas** (nuevo archivo `praxsa_manager/product/custom_views/vehicle_admin.py`, mismo patrón que `user_admin.py`):
   - `CarBrandListCreateView` / `CarBrandDetailView` (+ `CarBrandToggleActiveView`), `CarModelListCreateView` / `CarModelDetailView` (+ `CarModelToggleActiveView`), `CarPartListCreateView` / `CarPartDetailView` (+ `CarPartToggleActiveView`) — mismo trío por entidad que ya existe para `User`/`Sucursal`/`Group`. Todas con `get_queryset()` filtrando `is_active=True` salvo `?include_inactive=true`, y `search` por query param (`?search=`) filtrando por `name__icontains` (Marca, Item) o `name__icontains`/`car_brand_id__name__icontains` (Modelo, para cubrir "buscar por nombre de modelo o marca").
   - `CarModelItemsView` (`GET`/`POST` sobre `car_model_part` filtrado por `car_model_id`): `GET` lista los items asociados a un Modelo (con `select_related('car_part_id')`); `POST` crea la asociación (item nuevo o existente + `width`/`length`/`quantity`/`installation_price`), usando `CarModelPartSerializer`.
   - `CarModelItemDetailView` (`DELETE` sobre una fila `Car_Model_Part` puntual) para "quitar item del modelo" (borrado físico de la asociación, no del `Car_Part` en sí — ver ADR relacion-modelo-item).
   - Permisos: mismo patrón que el resto del módulo de usuarios — `authentication.TokenAuthentication` + `[permissions.IsAuthenticated, IsStaffUser, permissions.DjangoModelPermissions]` (`product/permissions.py:4-11`).
6. **URLs**: registrar en `praxsa_manager/product/urls.py` bajo un comentario nuevo ("Módulo de Vehículos (panel_admin/)"), mismo estilo de `path()` plano que el bloque de Usuarios (líneas 39-47): `vehicles/brands`, `vehicles/brands/<id>/`, `vehicles/brands/<id>/toggle-active/`, y análogos para `models`/`parts`, más `vehicles/models/<id>/items/` y `vehicles/models/<id>/items/<item_id>/`.
7. **Tests** (`praxsa_manager/product/tests/test_vehicles_module.py`, nuevo, siguiendo el patrón de `test_user_admin_module.py`/`tests/helpers.py`): ver `## Test strategy`.

### Frontend (`panel_admin/src/app/`)

8. **Búsqueda**: copiar el markup de `advance-table.component.html:29-35` (`table-search-area`, ícono `search`, input `search-field`) y adaptar `filterDatatable()` (`advance-table.component.ts:231-257`) a cada uno de los 3 componentes de lista (Marcas: filtra por `name`; Modelos: por `name` y por `car_brand_id.name`; Items: por `name`), incluyendo el reset de `table.offset = 0` ya presente en el original. No se crea ningún componente nuevo para esto.
9. **`shared/image-upload/`**: componente `ControlValueAccessor` (preview, seleccionar/reemplazar/quitar, placeholder con ícono `image` de `FeatherModule`, muestra errores de tipo/tamaño validados también en el cliente antes de enviar). Único componente nuevo en `shared/` (no existía la carpeta).
10. **`vehicles/vehicles.model.ts`** y **`vehicles/vehicles.service.ts`**: tipos (`CarBrand`, `CarModel`, `CarPart`, `CarModelPart`) y llamadas HTTP a los endpoints del paso 6, mismo estilo que `users.service.ts`.
11. **`vehicles/vehicles.routes.ts`**, lazy-loaded desde `app.routes.ts` (mismo patrón que `users.routes.ts`).
12. **Marcas**: `brands/list` (`ngx-datatable` + búsqueda estilo `advance-table` (paso 8) + columna Nombre/Cantidad de modelos/Acciones) y un modal reutilizado para Ver/Crear/Editar (un solo campo).
13. **Items**: `parts/list` (mismo patrón que Marcas) y su modal Ver/Crear/Editar.
14. **Modelos**: `models/list` (`ngx-datatable` + búsqueda estilo `advance-table` filtrando por nombre de modelo y de marca + columna Imagen-thumbnail/Marca/Modelo/Cantidad de items/Acciones), `models/create` y `models/edit` (página propia: `ng-select` o `<select>` de Marca activa, nombre, `image-upload`), `models/view` (imagen grande o placeholder, marca, nombre, lista simple de items asociados con su `width`/`length`/`quantity`/`installation_price`, botón "Agregar item" y acción "Quitar" por fila).
15. **Modal "Agregar item"** (desde `models/view`): toggle "Crear nuevo item" (nombre) vs. "Buscar item existente" (mismo patrón de búsqueda + lista de items activos no ya asociados a ese modelo), y en ambos casos los campos `width`/`length`/`quantity`/`installation_price` antes de confirmar (ver ADR relacion-modelo-item).
16. **Menú**: agregar el grupo "Vehículos" (Marcas/Modelos/Items, ícono `truck`) a `panel_admin/src/assets/data/routes.json`, mismo formato que el bloque "Usuarios" (`routes.json:14-58`).
17. **Tests Angular** (`.spec.ts` por componente/servicio, `TestBed` + `HttpTestingController`, mismo patrón que `users-list.component.spec.ts`): ver `## Test strategy`.

## Files/components affected

**Backend:**
- `praxsa_manager/product/models.py` (agregar campos, sin tocar nada existente)
- `praxsa_manager/product/migrations/` (2 migraciones nuevas)
- `praxsa_manager/praxsa_manager/settings.py` (MEDIA_ROOT/MEDIA_URL)
- `praxsa_manager/praxsa_manager/urls.py` (o el módulo de urls raíz que corresponda — confirmar nombre exacto del archivo al implementar) (static() en DEBUG)
- `praxsa_manager/product/serializer/vehicle_serializer.py` (nuevo)
- `praxsa_manager/product/custom_views/vehicle_admin.py` (nuevo)
- `praxsa_manager/product/urls.py` (nuevas rutas)
- `praxsa_manager/product/tests/test_vehicles_module.py` (nuevo)

**Frontend:**
- `panel_admin/src/app/shared/image-upload/` (nuevo)
- `panel_admin/src/app/vehicles/` (nuevo: `brands/`, `models/`, `parts/`, `vehicles.routes.ts`, `vehicles.service.ts`, `vehicles.model.ts`)
- `panel_admin/src/assets/data/routes.json` (nueva entrada de menú)

**Infraestructura (solo documentado en el PR, no ejecutado en este entorno):**
- `docker-compose.prod.yml`, `docker-compose.stg.yml` (volumen `media` nuevo)
- `nginx/nginx.conf.prod`, `nginx/nginx.conf.stg` (bloque `location /media/`)

## Test strategy

**Backend** (`test_vehicles_module.py`, integración con `APITestCase`/`self.client`, siguiendo `tests/helpers.py`):
- Marcas: crear, editar, visualizar, listar (solo activas por defecto, `?include_inactive=true` trae todas), soft delete (`toggle-active` → ya no aparece en listado ni en el selector de Modelo), buscar por nombre, paginación (si se configura `PAGE_SIZE`; si no, verificar que el listado devuelve todo y que el frontend pagina client-side — dejar explícito cuál de las dos aplica al implementar).
- Modelos: crear (con y sin imagen), asociar marca, marca obligatoria (falta → 400), marca inactiva rechazada, editar, soft delete, buscar por nombre de modelo y por nombre de marca, filtrar por marca (`?car_brand_id=`), paginación.
- Imagen: crear con imagen válida (jpg/png/webp), crear sin imagen (campo opcional, no falla), formato inválido (ej. `.txt` renombrado a `.jpg` → detectado por Pillow, no por extensión → 400), tamaño mayor a 5 MB → 400, reemplazar imagen (verifica que el archivo anterior se borra del filesystem), eliminar imagen (`image=null`), la respuesta del serializer siempre devuelve una URL absoluta o `null`, nunca una ruta de filesystem.
- Items: crear, editar, visualizar, listar (activos por defecto), soft delete, buscar por nombre, paginación, asociar a un modelo (vía `CarModelItemsView`) requiriendo `width`/`length`/`quantity`/`installation_price`, evitar asociación duplicada (mismo modelo + mismo item → 400 con mensaje de negocio, no 500 de integridad), quitar una asociación existente (`DELETE`) y confirmar que no afecta ninguna `Proforma_Detail` ya creada (test de regresión explícito: crear una proforma que use esa asociación, luego eliminar la asociación, y verificar que la proforma ya creada sigue intacta).
- Permisos: cada endpoint nuevo rechaza sin `is_staff` ni el `Permission` correspondiente (mismo patrón que `test_user_admin_module.py`).

**Frontend** (`.spec.ts`, `TestBed` + `HttpTestingController`, mismo patrón que `users-list.component.spec.ts`):
- `vehicles.service.ts`: cada método hace la llamada HTTP esperada con los query params correctos (búsqueda, `include_inactive`, `car_brand_id`).
- `image-upload.component.ts`: `ControlValueAccessor` (escribe/lee el valor del form correctamente), muestra error de validación de tipo/tamaño cuando corresponde, botón "Quitar" limpia el valor.
- `brands-list`/`parts-list`: `filterDatatable()` filtra correctamente por substring y resetea a la página 1 (mismo caso que ya cubriría, si existiera, un test de `advance-table.component.spec.ts` — no existe hoy, así que este test es la primera cobertura real de ese método, aunque copiado), dispara el modal de confirmación (`Swal`) al eliminar, no muestra inactivos.
- `models-create`/`models-edit`: formulario inválido sin marca seleccionada, envío con y sin imagen, reemplazo de imagen dispara el nuevo `FormData`.
- `models-view`: modal "Agregar item" en sus dos modos (crear nuevo / buscar existente), validación de los campos numéricos antes de confirmar.

**E2E: no corresponde.** Justificación explícita: es un módulo de administración de catálogo (CRUD + asociación), no un flujo crítico de cliente final de punta a punta (a diferencia de login→sucursal→proforma→pago, que sí lo sería). Los tests de integración del backend (contra la base de datos real, `self.client.post/patch/delete`) ya cubren la interacción real entre serializers/vistas/modelo, y los tests de componente Angular con `HttpTestingController` cubren la lógica de UI sin necesidad de levantar el stack completo. `panel_admin/package.json` no tiene Playwright instalado — no se agrega para este task.

## Acceptance criteria

- [ ] Migraciones `is_active` (Marca/Modelo/Item) e `image` (Modelo) aplicadas, sin tocar ninguna migración existente.
- [ ] `MEDIA_ROOT`/`MEDIA_URL` configurados; imágenes visibles en desarrollo local vía `manage.py runserver`.
- [ ] Endpoints REST de Marca/Modelo/Item con CRUD completo, búsqueda, filtrado (Modelo por Marca), soft delete vía toggle, y todos rechazando sin `is_staff`/permiso.
- [ ] Endpoint de asociación Modelo↔Item reutiliza `Car_Model_Part`, exige `width`/`length`/`quantity`/`installation_price`, rechaza duplicados con mensaje de negocio claro, y permite quitar una asociación sin afectar proformas históricas.
- [ ] El sidebar de `panel_admin/` muestra "Vehículos" con Marcas/Modelos/Items.
- [ ] Las 3 listas usan `ngx-datatable` con búsqueda y paginación, y las acciones usan los mismos íconos/estilo que Credenciales.
- [ ] Crear/editar Modelo permite subir/reemplazar/eliminar la imagen con preview; sin imagen se muestra un placeholder consistente (tabla y detalle).
- [ ] El detalle de Modelo muestra sus items asociados y permite agregar (crear nuevo o buscar existente) y quitar, evitando duplicados.
- [ ] Registros con soft delete no aparecen en listas normales ni en selectores (Marca en form de Modelo, búsqueda de Item para asociar).
- [ ] Todas las validaciones de imagen (tipo/tamaño) y de negocio (marca obligatoria, nombre único, asociación duplicada) están duplicadas en backend, no solo en frontend.
- [ ] Suite de tests backend (`test_vehicles_module.py`) y frontend (nuevos `.spec.ts`) en verde.

## Risks

- **El formulario de "agregar item" queda más complejo que lo previsto originalmente en el DDR de diseño** (4 campos numéricos además de elegir/crear el item) — riesgo de UX, no de datos; mitigado dejando el motivo explícito en el modal ("estos datos determinan el precio de instalación que se cobrará") para que no se sienta arbitrario.
- **Paginación/búsqueda client-side no escala indefinidamente** (mismo riesgo que ya existe hoy en Credenciales, `docs/backend-audit.md:553-556`, PERF-02) — aceptado conscientemente por el ADR de diseño; si el volumen real de estos catálogos crece mucho, es una tarea futura de migración a server-side, no bloqueante para esta.
- **Despliegue de imágenes requiere coordinar infraestructura (volumen Docker + nginx) con el código** — mitigado dejándolo explícito en el PR y en el ADR de almacenamiento; no aplica a este entorno de desarrollo.
- **Cambiar `car_part_id` de `null=True` a requerido en la práctica** (el modelo lo permite nulo pero la asociación real siempre necesita un item) — no se cambia la migración (evitar tocar la nullabilidad de un campo con datos existentes sin necesidad), se valida a nivel de serializer que el nuevo endpoint de asociación siempre lo exija.

## Out of scope

- Editar `width`/`length`/`installation_price` de una asociación Modelo-Item ya creada desde el panel (el pedido solo describe "agregar item"; si el negocio lo necesita, es una extensión pequeña y acotada de una tarea futura, no de esta).
- Migrar la búsqueda/paginación de Credenciales (ya existente) a server-side.
- Cualquier vista de "Perfiles"/roles diferenciados para el módulo de Vehículos — mismo nivel de acceso que el resto del panel hoy.
- Aplicar de hecho los cambios de `docker-compose.*.yml`/`nginx.conf.*` en un entorno real (se documentan y se dejan listos en el PR, pero no hay Docker/nginx real en este entorno de desarrollo para verificarlos en vivo).
- Unificar los 3 (ahora 4) mecanismos de soft-delete distintos que conviven en el proyecto.

## Dependencias nuevas

Ninguna — `Pillow==10.0.1` (necesario para `ImageField`) ya está en `praxsa_manager/requirements-3.8.10.txt:21`.

## Changelog

- **v2** (2026-09-26): corrige la investigación/diseño original, que había afirmado que no existía ningún patrón de búsqueda reutilizable en `panel_admin/`. El usuario señaló que `panel_admin/src/app/advance-table/advance-table.component.html:29-35` (markup) y `.ts:231-257` (`filterDatatable()`) ya resuelven la búsqueda sobre `ngx-datatable`, con reset de página incluido. Se elimina el componente `shared/search-box/` de v1 y se reemplaza en todos los pasos/criterios por reutilizar ese patrón existente, copiado y adaptado a las columnas de cada lista. No cambia ningún otro aspecto del plan (backend, imágenes, soft delete, relación Modelo-Item). Ver DDR-modulo-vehiculos-listado-y-flujo-vehiculos.md, sección "Corrección".
