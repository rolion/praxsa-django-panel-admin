# TASK-modulo-vehiculos: Módulo de Vehículos (Marcas, Modelos, Items) en el panel admin

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** claude/modulo-vehiculos-2168ac
**Pull Request:** [#48](https://github.com/rolion/praxsa-django-panel-admin/pull/48)

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-09-26 00:56 UTC | (nuevo) → INVESTIGATION | Task creado | delivery-investigate |
| 2026-09-26 01:20 UTC | INVESTIGATION → ARCHITECTURE (via DESIGN) | Diseño de UI (listados, formularios, upload, búsqueda/paginación) resuelto en DDR; veredicto de complejidad exige definir modelo de datos, soft delete y almacenamiento de imágenes | delivery-design |
| 2026-09-26 01:45 UTC | ARCHITECTURE → PLANNING | Decisiones de arquitectura tomadas: reutilizar `Car_Model_Part` para la relación Modelo↔Item, soft delete con `is_active` filtrado por defecto, almacenamiento de imágenes en filesystem local con `MEDIA_ROOT`/`MEDIA_URL` nuevos servidos por nginx | delivery-architect |
| 2026-09-26 02:05 UTC | PLANNING → ENGINEERING | Plan v1 escrito y PR por abrir; queda pendiente de aprobación humana antes de implementar | delivery-plan |
| 2026-09-26 02:20 UTC | ENGINEERING → ENGINEERING | Corrección post-diseño: sí existe patrón de búsqueda reutilizable en `advance-table.component.html/.ts` (usuario lo señaló); se actualiza DDR/TASK/Plan a v2 para reutilizarlo en vez de construir `shared/search-box/` | usuario |
| 2026-09-26 10:30 UTC | ENGINEERING → REVIEW | Implementación completa (backend + frontend + infra) según Plan v2, empujada al PR #48 | delivery-engineer |
| 2026-09-26 11:15 UTC | REVIEW → ENGINEERING | Quality Gate: **FAIL**. REV-01 (Critical, IMPLEMENTATION): crear un Modelo vía la UI real deja `is_active=False` (multipart + BooleanField sin default explícito en el serializer) y desaparece del listado al instante. REV-02 (Medium, IMPLEMENTATION): faltan specs de `model-create`/`model-edit`/`model-view` definidos en el plan. Ambos issues son de implementación, no de plan/arquitectura | delivery-review |
| 2026-09-26 12:00 UTC | ENGINEERING → ENGINEERING | Fixes y feature pedidos directamente por el usuario fuera del ciclo `delivery-plan` (no ameritaban replanificar): alinear imagen con datos del modelo en `model-view`; corregir bug real (no relacionado con REV-01) por el cual editar un Modelo con imagen existente no la mostraba y la borraba al guardar; agregar edición de ancho/largo/cantidad de un item ya asociado; ocultar el campo de precio de instalación del formulario. REV-01 sigue abierto (no tocado por estos cambios); REV-02 bajó a Low (ya existen specs de `model-edit`/`model-view`, solo falta `model-create`) | usuario |

## Investigación

### Requerimiento

Agregar al panel administrativo (`panel_admin/`) un nuevo grupo de menú "Vehículos" con tres secciones administrables: **Marcas**, **Modelos** e **Items**. Requisitos principales del pedido:

- CRUD completo (listar/crear/ver/editar/eliminar) para las tres entidades, con borrado lógico (no físico).
- Relación Marca 1─N Modelo (un modelo pertenece a una sola marca).
- Modelo con campo de imagen del vehículo: opcional (salvo que el negocio actual la requiera obligatoria), subir/reemplazar/eliminar desde el formulario, placeholder si no hay imagen, thumbnail en el listado.
- Relación Modelo↔Item a definir según lo que ya exista en el dominio (el pedido explícitamente pide no asumir 1─N vs N─N sin revisar el modelo de datos existente).
- Desde el detalle de un Modelo, poder agregar Items: creando uno nuevo o buscando/asociando uno existente, evitando duplicados.
- Todas las listas con tabla avanzada existente, búsqueda y paginación, reutilizando componentes ya existentes en el panel.
- Todas las acciones de tabla (Ver/Editar/Eliminar) deben usar los mismos botones/iconos/estilos que la sección de Credenciales.
- Backend Django/DRF con validaciones de datos y de archivos; frontend Angular reutilizando componentes/servicios existentes.
- Pruebas automatizadas para las funcionalidades principales de cada entidad.

### Hechos encontrados

**Frontend — hay dos apps Angular en el monorepo, no una.** `panel_admin/` (Angular 21 standalone, plantilla admin con sidebar — es donde vive "Credenciales"/Usuarios) y `proforma/` (Angular 16 basado en módulos, frontend de cliente final para cotizaciones). Todo lo pedido en este task (menú, tablas, acciones tipo Credenciales) es sobre `panel_admin/`. `docs/CLAUDE.md` (líneas 4-7) describe el monorepo como solo `praxsa_manager/` + `proforma/` y no menciona `panel_admin/` — está desactualizado.

**Menú principal**: no es código TS, es un JSON estático servido como asset y cargado por HTTP: `panel_admin/src/assets/data/routes.json`. Se lee vía `SidebarService.getRouteInfo()` (`panel_admin/src/app/layout/sidebar/sidebar.service.ts:17-22`, `http.get('assets/data/routes.json')`) y se consume en `SidebarComponent.ngOnInit()` (`panel_admin/src/app/layout/sidebar/sidebar.component.ts:94-99`) solo si hay usuario logueado. La interfaz de cada entrada es `RouteInfo` (`panel_admin/src/app/layout/sidebar/sidebar.metadata.ts:1-13`: path, title, iconType, icon, class, groupTitle, badge, badgeClass, submenu).

**"Credenciales" no es un módulo aparte** — es el título de menú del listado de usuarios existente. El grupo "Usuarios" con sus 3 hijos ("Credenciales" → `/users`, "Grupos" → `/users/groups`, "Sucursales" → `/users/sucursales`) está en `panel_admin/src/assets/data/routes.json:14-58`.

**Tabla usada en "Credenciales"**: `panel_admin/src/app/users/list/users-list.component.ts/.html` usa `NgxDatatableModule` de `@swimlane/ngx-datatable` **directamente**, no hay un wrapper propio (`users-list.component.ts:4,12`; `<ngx-datatable class="material" [rows]="rows" [limit]="10">` en `users-list.component.html:31-40`).

**No existe un componente de "tabla avanzada" genérico reutilizable.** Existe `panel_admin/src/app/advance-table/` pero es la página de demo de la plantilla comercial (confirmado en `docs/frontend/panel_admin/reference.md:26,85`), sin ningún otro consumidor en el proyecto (única referencia externa: la ruta lazy en `panel_admin/src/app/app.routes.ts:20-25`). No existe carpeta `shared/` en `panel_admin/src/app/` (confirmado explícitamente en `docs/frontend/panel_admin/reference.md:22,49`, y por búsqueda directa en el filesystem).

**No existe búsqueda en "Credenciales"** (`users-list.component.html` no tiene ningún `<input>` de búsqueda, solo un checkbox "Mostrar inactivos", líneas 16-25), **pero sí existe un patrón de búsqueda funcional en la plantilla, corrección post-diseño (2026-09-26)**: `panel_admin/src/app/advance-table/advance-table.component.html:29-35` (markup `table-search-area`, ícono `search` de Material Icons, input `search-field`, `(keyup)='filterDatatable($event)'`) + `advance-table.component.ts:231-257` (`filterDatatable()`: filtra `this.data` por substring en cualquier columna y resetea `this.table.offset = 0`, resolviendo ya el requisito de volver a la página 1 al buscar). La investigación inicial citó este componente solo como referencia de tabla y no notó que también resuelve la búsqueda — ver DDR de diseño, sección "Corrección".

**No existe componente de paginación reutilizable.** La única paginación disponible en `panel_admin/` es el footer nativo de `ngx-datatable` (client-side, `[limit]="10"`), sin query params de paginación en `UsersService.listUsers()` (`panel_admin/src/app/users/users.service.ts:16-48`, único query param real es `include_inactive`).

**No existe ningún componente de upload de imágenes/archivos en el frontend.** Sin `<input type="file">`, sin dropzone, sin preview, en todo `panel_admin/src/app/`. Ningún modelo del frontend (`panel_admin/src/app/users/users.model.ts:1-46`) tiene campo de imagen.

**Botones de acción de "Credenciales"**: implementados inline en el HTML de la columna Acciones (`users-list.component.html:55-91`), no como componente reutilizable. Iconos Font Awesome (`fas fa-eye`, `fas fa-pen`, `far fa-trash-alt`, `fas fa-user-check`) con clases propias `btn-tbl-view`, `btn-tbl-edit`, `btn-tbl-delete`, `btn-tbl-activate` (líneas 59, 66, 74, 83). Ver → `routerLink="/users/view/:id"`, Editar → `routerLink="/users/edit/:id"`. El botón de "eliminar" en realidad alterna `is_active` (ver soft delete más abajo), y su ícono/label cambian condicionalmente (líneas 71-89) entre "eliminar" y "activar".

**Confirmación de eliminación**: SweetAlert2 (`Swal.fire(...)`), no un modal Angular propio — `panel_admin/src/app/users/list/users-list.component.ts:5,45-57` (método `deactivate`).

**Backend — no hay `MEDIA_ROOT`/`MEDIA_URL` configurados** en `praxsa_manager/praxsa_manager/settings.py` (grep exhaustivo sin resultados). Solo existe configuración de estáticos: `STATIC_URL='/static/'` (línea 199), `STATICFILES_DIRS` (línea 204), `STATIC_ROOT` (línea 209).

**Backend — no hay ningún `ImageField`/`FileField` en todo el proyecto** (grep exhaustivo en `praxsa_manager/`, cero resultados). No hay ningún precedente de "cómo el proyecto sirve imágenes al frontend" para replicar.

**Backend — soft delete: tres mecanismos distintos y no unificados convivientes hoy:**
1. `Proforma_Header.is_delete` (BooleanField, `praxsa_manager/product/models.py:173`) — nunca expuesto por API, solo oculto del Django Admin (`exclude=["is_delete","is_paid",...]`, documentado con drift en `docs/backend-audit.md:539-540`, ya que `is_paid` ni existe en el modelo actual).
2. `User.is_active` (campo nativo de Django, no propio) — expuesto vía endpoint dedicado `UserToggleActiveView.patch` (`praxsa_manager/product/custom_views/user_admin.py:82-106`), que hace `user.is_active=bool(...); user.save(update_fields=['is_active'])`. El frontend lo presenta como "Eliminar/Activar" en la lista de Credenciales.
3. Borrado físico real para `Group`/`Sucursal`: `GroupDetailView`/`SucursalDetailView` son `RetrieveUpdateDestroyAPIView` sin soft-delete (`user_admin.py:116-120,141-145`).

No hay manager personalizado ni mixin de soft-delete en ningún lugar de `product/` (grep de managers sin resultados fuera de los managers por defecto de Django).

**Backend — los modelos de Marca/Modelo/Item YA EXISTEN, activos, con datos en producción, pero sin API REST.** Todos en `praxsa_manager/product/models.py`:
- `Car_Brand` (líneas 16-22): `name` (CharField, `unique=True`, verbose_name "Nombre"), `Meta.ordering=['name']`, `Meta.verbose_name='Marca'`.
- `Car_Model` (líneas 24-31): `car_brand_id` FK a `Car_Brand` (`on_delete=DO_NOTHING`, verbose_name "Marca"), `name` (`unique=True`), `Meta.verbose_name='Modelo'`. Confirma la relación pedida: **Marca 1─N Modelo ya existe en el esquema actual** (FK simple, no M2M).
- `Car_Part` (líneas 33-39): `name` (CharField, sin `unique`), `Meta.verbose_name='Item'`.
- `Car_Model_Part` (líneas 41-55): tabla de asociación Modelo↔Item con **campos de negocio propios** — `width`, `length` (Decimal), `quantity` (PositiveInteger, default 1), `installation_price` (Decimal) — y `UniqueConstraint(['car_model_id','car_part_id'], name='unique_model_item')` (evita ya hoy duplicar el mismo item en el mismo modelo). `car_part_id` es `null=True`. Esto **no es una relación N─N genérica**: cada fila `Car_Model_Part` representa la configuración de instalación de un item específico en un modelo específico, con su propio precio.
- Registrados en Django Admin: `praxsa_manager/product/admin.py:34-37` (`admin.site.register(Car_Brand, CarBrand)`, `Car_Model, CarModel)`, `Car_Model_Part, CarModelPart)`, `Car_Part)`), con `ModelAdmin` custom en `product/admin_config/car_brand.py:3-7` y `product/admin_config/car_model.py:13-23` (inline de `Car_Model_Part`, `search_fields` con `car_brand_id__name`, `select_related`).
- **Uso real en lógica de negocio de cotización/facturación**, no solo catálogo estático: referenciados desde `praxsa_manager/product/business/proforma.py`, `praxsa_manager/product/serializer/invoice_serializer.py`, y desde tests dedicados (`praxsa_manager/product/tests/test_admin_price_recalculation.py`, `test_invoice_pricing.py`, `tests/helpers.py`). `Car_Model_Part` también tiene su propio Form: `praxsa_manager/product/Forms/car_model_part.py`.
- Endpoints públicos existentes (funciones planas, no DRF, sin auth de panel_admin): `praxsa_manager/product/urls.py:22` (`get_car_part_info/<car_model_id>/<sucursal_id>`), línea 25 (`calculator_info`), línea 27 (`model_parts/<model_id>`), implementados en `praxsa_manager/product/views.py`. Estos alimentan la calculadora de precios de `proforma/`, no el panel admin.
- FK adicionales hacia estos modelos: `Proforma_Header.car_model_id` (`models.py:171`), `Nota_trabajo.car_model` (`models.py:202`).
- **No existe ningún serializer DRF, viewset ni entrada en `urls.py` para CRUD administrable de estos 4 modelos.** Todo el mantenimiento hoy es exclusivamente vía Django Admin. Ninguna clase llamada "Vehiculo"/"Vehicle"/"Brand" (inglés) existe; los nombres reales de dominio son `Car_Brand`/`Car_Model`/`Car_Part`/`Car_Model_Part`.

**Backend — patrón CRUD DRF más reciente para replicar** (módulo de Usuarios, mergeado desde `master` en esta misma sesión): modelo `Profile` (`models.py:111-121`, OneToOne con `User`), migration `product/migrations/0107_profile.py`, serializers `product/serializer/user_admin_serializer.py` (`UserAdminSerializer` líneas 10-55, `UserCreateSerializer` líneas 58-118, `update()` en `transaction.atomic()`), vistas en `product/custom_views/user_admin.py` (`UserListCreateView` 17-39 con filtro `is_active` por query param `include_inactive`, `UserDetailView` 42-50, `UserToggleActiveView` 82-106, `GroupListCreateView`/`SucursalListCreateView` 109-145), URLs planas con `path()` (no `DefaultRouter`) en `product/urls.py:39-47`, permisos custom `IsStaffUser` (`product/permissions.py:4-11`) combinado con `DjangoModelPermissions`.

**Sin paginación configurada en DRF a nivel global**: no hay `DEFAULT_PAGINATION_CLASS`/`PAGE_SIZE` en `settings.py:119-125` (confirmado también en `docs/backend-audit.md:249`, y señalado como riesgo específico para catálogos que crecen — línea 553-556, PERF-02 — mencionando explícitamente marcas/modelos/piezas).

**Todas las FK del dominio usan `on_delete=models.DO_NOTHING`** (`docs/backend-audit.md:123`, confirmado en `Car_Model.car_brand_id` y `Car_Model_Part`) — relevante para decidir qué pasa con Modelos/Items al hacer soft-delete de una Marca/Modelo padre.

### Hipótesis / supuestos no confirmados

- No se confirmó si el negocio requiere que la imagen del Modelo sea obligatoria; el pedido dice "opcional salvo que el negocio actual lo requiera" y no se encontró ninguna regla existente al respecto (no hay precedente de imágenes en el proyecto).
- No se confirmó si algún cliente externo (aparte de `proforma/`) consume `get_car_part_info`/`calculator_info`/`model_parts` — se asume que sí por ser endpoints públicos de negocio, pero no se verificó exhaustivamente todo el frontend `proforma/`.
- No se confirmó cuál sería el criterio de unicidad deseado para "Marca+Modelo" a nivel de negocio nuevo — hoy `Car_Model.name` ya es único globalmente (no compuesto con marca), lo cual ya impide nombres de modelo duplicados entre marcas distintas; si el negocio quisiera permitir el mismo nombre de modelo en dos marcas distintas, eso requeriría cambiar una constraint ya existente en producción.
- No se confirmó el volumen actual de filas en `Car_Brand`/`Car_Model`/`Car_Part`/`Car_Model_Part` en la base real, relevante para decidir si la paginación server-side es urgente o cosmética.

### Módulos y dependencias relacionadas

- Backend: `praxsa_manager/product/models.py` (modelos existentes), `product/admin_config/car_brand.py`, `product/admin_config/car_model.py`, `product/admin_config/car_model_part.py`, `product/Forms/car_model_part.py`, `product/business/proforma.py`, `product/serializer/invoice_serializer.py`, `product/views.py` (endpoints públicos de calculadora), `product/urls.py`.
- Backend, módulo de referencia para el patrón CRUD nuevo: `product/custom_views/user_admin.py`, `product/serializer/user_admin_serializer.py`, `product/serializer/group_serializer.py`, `product/serializer/sucursal_serializer.py`, `product/permissions.py`.
- Frontend: `panel_admin/src/app/users/*` (patrón a replicar visualmente), `panel_admin/src/assets/data/routes.json`, `panel_admin/src/app/layout/sidebar/*`, `panel_admin/src/app/app.routes.ts`.
- Documentación relevante para la fase de diseño/arquitectura: `docs/frontend/panel_admin/reference.md` (más actualizado que `docs/CLAUDE.md` respecto a `panel_admin/`), `docs/backend-audit.md` (líneas 94, 100-103, 123, 249, 366-373, 539-540, 553-556), `docs/frontend-audit.md` (líneas 16, 22, 89 — sobre `proforma/`, no aplica directo a `panel_admin/`).

### Implementaciones similares existentes

- El único CRUD administrable end-to-end (DRF + Angular con lista/crear/editar/ver + soft-ish-delete + permisos) es el módulo de Usuarios/Grupos/Sucursales recién mergeado — es la referencia estructural más cercana para vistas, serializers, urls y permisos del nuevo módulo de Vehículos.
- No hay ningún ejemplo de tabla con búsqueda+paginación combinadas, ni de upload de imagen, en ningún punto de `panel_admin/`. La sección de Sucursales/Grupos (`sucursales-list.component.html`, `groups-list.component.html`) tampoco tiene búsqueda ni paginación propia — usan el mismo patrón simple de `ngx-datatable` sin filtros.

### Comportamiento actual

Hoy, la gestión de Marcas/Modelos/Items/relaciones de instalación se hace **exclusivamente por Django Admin** (`/admin/`), sin ninguna superficie en el panel administrativo Angular (`panel_admin/`) ni API REST dedicada. Los únicos consumidores programáticos de estos datos son: (a) el Django Admin mismo, y (b) tres endpoints públicos de función plana (`get_car_part_info`, `get_proforma_car_part_info`, `calculator_info`, `model_parts`) que alimentan la calculadora de precios del frontend de cliente (`proforma/`), no del panel admin.

### Restricciones

- `docs/CLAUDE.md` (líneas 30-38): reglas generales — "Todo cambio de lógica de negocio lleva su test", "No editar migraciones ya aplicadas" (relevante: cualquier cambio a `Car_Model`/`Car_Model_Part` debe ser migración nueva, nunca editar `0002_car_brand_car_model_car_model_part_and_more.py` ni las migraciones posteriores 0004/0005/0007/0008/0012/0025/0071/0084 que ya las tocan).
- El proyecto "NO se construyó con buenas prácticas" (nota general del proyecto) — no asumir convenciones limpias por el nombre de un archivo.
- `Car_Model_Part` ya tiene una `UniqueConstraint` de negocio (`unique_model_item`) que debe respetarse/reutilizarse al construir la asociación Modelo↔Item pedida en el punto 18 del requerimiento (evitar asociar dos veces el mismo item al mismo modelo) — no hay que inventar una constraint nueva, ya existe.
- No hay `MEDIA_ROOT`/`MEDIA_URL` ni política de tipos/tamaños de imagen existente — cualquier definición de formatos/tamaños permitidos será una decisión nueva del proyecto, no una reutilización.

### Riesgos identificados

- **Riesgo de negocio**: `Car_Model_Part` no es una tabla de asociación simple — trae `width`, `length`, `quantity`, `installation_price` usados por la calculadora de precios y facturación (`business/proforma.py`, `invoice_serializer.py`). El requerimiento pide una pantalla de "agregar item a un modelo" simple (crear o buscar+asociar); si la implementación crea filas `Car_Model_Part` sin definir criterio para esos 4 campos de precio, podría romper o distorsionar cálculos de cotización/facturación ya en producción. Esto es exactamente el tipo de ambigüedad de relación que el punto 12 del requerimiento pide no resolver sin revisar el modelo existente — ya se revisó y la relación NO es un M2M genérico, es una entidad de negocio con datos propios.
- **Riesgo de arquitectura**: el pedido asume que existen "tabla avanzada", "búsqueda", "paginación" y "upload de imágenes" reutilizables en el panel — ninguno existe. Construirlos desde cero (aunque sea el mínimo para las 3 pantallas) es trabajo estructural nuevo, no solo reutilización, y una decisión de si conviene extraerlos como componentes compartidos (dado que se usarán 3 veces en este módulo) o replicar el patrón inline de Credenciales tres veces más.
- **Riesgo de almacenamiento**: no hay `MEDIA_ROOT`/`MEDIA_URL` configurado — hay que decidir y configurar el mecanismo de almacenamiento de archivos por primera vez en el proyecto (filesystem local vs. algún storage backend), lo cual es una decisión de infraestructura, no un simple "usar lo que ya existe" porque no existe nada.
- **Riesgo de soft delete**: hay 3 patrones convivientes distintos (`is_delete` no expuesto, `is_active` con endpoint dedicado, borrado físico real). Elegir uno para Marca/Modelo/Item es una decisión de diseño que además debe resolver qué pasa con Modelos/Items hijos cuando se soft-elimina su Marca/Modelo padre, dado que todas las FK son `DO_NOTHING` (no hay cascada a nivel de BD).
- **Riesgo de integridad**: `Car_Model.name` ya es único **globalmente** (no compuesto con marca) en el esquema actual — si el negocio esperara nombres de modelo repetibles entre marcas distintas (ej. "Sport" en dos marcas), la constraint actual ya lo impide y cambiarla es una migración sobre datos en producción, no una decisión trivial de frontend.
- **Riesgo de paginación**: no hay paginación configurada a nivel DRF global; agregarla solo para este módulo (vs. global) es una decisión de arquitectura con impacto potencial en otros endpoints existentes si se cambia el default global.

### Veredicto de complejidad

**NEEDS_ARCHITECTURE** — hay múltiples indicadores simultáneos: nuevo módulo/bounded context en el panel (Vehículos), integración con datos de negocio existentes y sensibles (`Car_Model_Part` alimenta pricing/facturación), decisión de infraestructura nueva (almacenamiento de imágenes, sin precedente en el proyecto), impacto en múltiples módulos si se toca la constraint de unicidad de `Car_Model.name` o el default de paginación DRF global, y una decisión de soft-delete que hoy no tiene un patrón único a seguir (3 variantes convivientes). Además, el pedido asume componentes reutilizables (tabla avanzada, búsqueda, paginación, upload) que verificablemente no existen, lo cual por sí solo ya amerita una decisión arquitectónica sobre qué construir y cómo compartirlo entre las 3 pantallas nuevas.

### Diseño requerido

**SI** — el módulo agrega 3 pantallas de listado nuevas, 2 formularios de creación/edición con upload de imagen (UX de preview/reemplazo/eliminación sin precedente en el proyecto), una pantalla de detalle de Modelo con gestión de Items asociados (crear nuevo vs. buscar y asociar existente), y debe verse visualmente consistente con Credenciales pese a que ninguno de los componentes base (tabla, búsqueda, paginación, upload) existe hoy. Es exactamente el escenario de "superficie de UI nueva no trivial" que amerita una decisión de diseño antes de construir.

## Diseño

Ver [DDR-modulo-vehiculos-listado-y-flujo-vehiculos.md](../design/DDR-modulo-vehiculos-listado-y-flujo-vehiculos.md).

Resumen de decisiones:
- Tablas de Marcas/Modelos/Items: `ngx-datatable`, mismo componente y look que "Credenciales" (columna de acciones circular con íconos `eye`/`edit-2`/`trash-2` de `FeatherModule`, confirmación de borrado con SweetAlert2). No se introduce ninguna librería de tabla nueva.
- Búsqueda: **corregido tras revisión del usuario** — se reutiliza el patrón ya existente en `advance-table.component.html:29-35`/`.ts:231-257` (markup + `filterDatatable()`), copiado y adaptado por lista (no se crea `shared/search-box/`). Paginación: se mantiene client-side nativa de `ngx-datatable`, igual que Credenciales (no hay paginación DRF configurada ni precedente server-side en `panel_admin/`) — queda como pregunta abierta para arquitectura si el volumen real de estos catálogos lo justifica.
- Upload de imagen del Modelo: no existe componente ni patrón previo; se construye uno reutilizable (`shared/image-upload/`, `ControlValueAccessor`) con preview, reemplazo, eliminación y placeholder con ícono `image`. Es ahora el único componente nuevo en `shared/`.
- Marca e Item: modal (`NgbModal`) para ver/crear/editar (formulario de un solo campo). Modelo: página propia (selección de marca + imagen). Detalle de Modelo: página propia con lista simple de items + modal "Agregar item" (crear nuevo o buscar y asociar existente).
- Sin diferenciación de privilegios específica pedida para este módulo; mismo nivel de acceso que Credenciales hoy.
- Pendiente para `delivery-architect`: qué es realmente la relación Modelo↔Item por debajo (dado que `Car_Model_Part` ya existe con datos de precio/instalación usados en facturación), estrategia de soft delete a elegir (hay 3 patrones convivientes hoy) y estrategia de almacenamiento de imágenes (no hay `MEDIA_ROOT`/`MEDIA_URL` configurado).

## Arquitectura

- [ADR-modulo-vehiculos-relacion-modelo-item.md](../adr/ADR-modulo-vehiculos-relacion-modelo-item.md) — la relación Modelo↔Item ya existe como `Car_Model_Part` (N─N real, con `width`/`length`/`quantity`/`installation_price` propios, consultada en vivo por la calculadora de precios de proformas). No se crea ninguna tabla de asociación nueva. El formulario de "agregar item a un modelo" debe capturar esos 4 campos, no solo el item — amplía lo que el DDR de diseño había previsto solo con nombre/selección; `delivery-plan` debe reconciliar el formulario del modal con esto. Desasociar un item = borrado físico de la fila `Car_Model_Part` (verificado seguro: `Proforma_Detail` copia sus propios valores, no referencia viva a `Car_Model_Part`).
- [ADR-modulo-vehiculos-soft-delete.md](../adr/ADR-modulo-vehiculos-soft-delete.md) — se agrega `is_active` (default `True`) a `Car_Brand`/`Car_Model`/`Car_Part`, filtrado por defecto en cada vista (mismo patrón que ya funciona en `UserListCreateView`, no el `is_delete` decorativo de `Proforma_Header`). "Eliminar" = `PATCH is_active=false` vía endpoint dedicado (mismo patrón que `UserToggleActiveView`). Los selectores (Marca en form de Modelo, búsqueda de Item para asociar) consumen el mismo filtro. Sin cascada automática entre Marca→Modelo→Item.
- [ADR-modulo-vehiculos-almacenamiento-imagenes.md](../adr/ADR-modulo-vehiculos-almacenamiento-imagenes.md) — `Car_Model.image` como `ImageField` (opcional), nuevo `MEDIA_ROOT`/`MEDIA_URL` en `settings.py` (no existían), validación de tipo (jpg/png/webp vía Pillow, ya es dependencia existente) y tamaño (5 MB) en el serializer, reemplazo de imagen borra el archivo anterior. Infraestructura: nuevo volumen Docker `media` + bloque `location /media/` en nginx, replicando exactamente el patrón ya usado por `/static/` en `docker-compose.prod.yml`/`.stg.yml` y `nginx.conf.prod`/`.stg`. Sin cambios en `docker-compose.dev.yml` (dev corre el backend local, no en contenedor).

Patrón de API/CRUD (serializers, vistas, urls, permisos) para las 3 entidades: no requiere un ADR propio — se aplica sin alternativas el mismo patrón ya establecido por el módulo de Usuarios (`product/custom_views/user_admin.py`, `IsStaffUser` + `DjangoModelPermissions`, URLs planas con `path()`), consistencia directa con lo ya decidido, no una decisión nueva.

## Plan

[PLAN-2026-09-26-modulo-vehiculos.md](../plans/PLAN-2026-09-26-modulo-vehiculos.md) (v2 — corrige búsqueda para reutilizar el patrón de `advance-table`, ver Changelog del plan).

## Implementación

Implementado íntegramente según [PLAN-2026-09-26-modulo-vehiculos.md](../plans/PLAN-2026-09-26-modulo-vehiculos.md) (v2), sin desvíos de alcance. Detalle completo en la sección `## Changes` del [PR #48](https://github.com/rolion/praxsa-django-panel-admin/pull/48). Resumen:

- **Backend**: migración aditiva `0108_car_brand_is_active_car_model_image_and_more.py` (`is_active` en las 3 entidades, `image` en Modelo); `product/serializer/vehicle_serializer.py` y `product/custom_views/vehicle_admin.py` nuevos, siguiendo el patrón ya establecido por el módulo de Usuarios (permisos, estructura de URLs); `MEDIA_ROOT`/`MEDIA_URL` nuevos en `settings.py`, servidos por Django en dev y por nginx en prod/stg. 39 tests de integración nuevos en `test_vehicles_module.py`; suite completa del backend (142 tests) en verde.
- **Frontend**: módulo `panel_admin/src/app/vehicles/` completo (listados, formularios, detalle de Modelo con gestión de items), componente compartido `shared/image-upload/` (primera pieza en `shared/`), menú actualizado. `ng build` y `ng lint` limpios; 24 tests Angular nuevos (69 total, mismas 15 fallas preexistentes de la plantilla — ninguna nueva).
- **Infraestructura**: `docker-compose.prod.yml`/`.stg.yml` y `nginx/nginx.conf.prod`/`.stg` actualizados con el volumen `media` y el bloque `location /media/`, sin tocar `docker-compose.dev.yml` (no aplica, dev corre el backend local).

Deuda técnica y desviaciones señaladas explícitamente (ninguna bloqueante):
- Las acciones de tabla (Ver/Editar/Eliminar) replican el estilo **real** de Credenciales hoy (`btn-tbl-view`/`btn-tbl-edit`/`btn-tbl-delete` con iconos FontAwesome) — el DDR de diseño citaba una actualización a íconos `FeatherModule` circulares que no está presente en el código actual de `users-list.component.html`; se siguió el código real, no la descripción del DDR (ver nota en DDR de usuarios vs. código verificado durante esta implementación).
- Cobertura de tests Angular: no se agregó spec dedicado para `model-create` (sí existen ahora `model-edit.component.spec.ts` y `model-view.component.spec.ts`, agregados en los fixes post-review — ver abajo). Ver REV-02, bajado a Low.
- El volumen Docker `media` debe crearse manualmente (`docker volume create media`) antes del primer despliegue en `stg`/`prod` — no se pudo verificar en este entorno de desarrollo (sin Docker/nginx real).

### Cambios post-review pedidos directamente por el usuario (2026-09-26, fuera del ciclo `delivery-plan`)

No ameritaban replanificar (ajustes de UX acotados y un bug real encontrado en uso, no desviaciones de arquitectura/plan):

1. **Alineación imagen/datos en `model-view`** (commit `6b3e176`): la imagen y el bloque Marca/Modelo/Estado estaban apilados con desalineación visual; ahora van lado a lado en una fila con `align-items-center`.
2. **Fix: editar un Modelo con imagen existente no la mostraba y la borraba al guardar** (commit `2bc6ad7`, bug real reportado por el usuario, no relacionado con REV-01). Causa raíz: `FormControl` normaliza un valor inicial `undefined` a `null` (parámetro por defecto de su propio constructor), así que `ImageUploadComponent.writeValue(null)` interpretaba la carga inicial como "el usuario quitó la imagen", y `model-edit.component.save()` leía ese mismo `null` como intención real de borrar. Fix: `writeValue()` ya no apaga la imagen existente por `null`/`undefined` (solo `removeImage()` lo hace), y `save()` usa `FormControl.dirty` en vez del valor crudo para decidir si manda la imagen. Agrega `model-edit.component.spec.ts`, que reproduce el bug original antes del fix.
3. **Editar item asociado + ocultar precio de instalación** (commit `2ab222a`, pedido explícito del usuario): nueva acción "Editar" en cada item de `model-view` para ajustar ancho/largo/cantidad de la asociación sin cambiar el item. Backend: `CarModelItemDetailView` pasa a `RetrieveUpdateDestroyAPIView`; el serializer ignora `car_part_id`/`new_car_part_name` en `update()` (defensa en profundidad). `installation_price` se oculta del formulario (crear y editar) y se relaja a opcional en el serializer (usa el default del modelo, 0) — es exactamente el camino de rollback que `ADR-modulo-vehiculos-relacion-modelo-item` ya había previsto para este campo si resultaba fricción excesiva, así que no contradice esa decisión. Agrega `model-view.component.spec.ts`.

Verificación de cada uno: `manage.py test` (146 tests, suite completa en verde) y `ng build`/`ng lint`/`ng test` (77 tests, mismas 15 fallas preexistentes de la plantilla) tras cada cambio. **REV-01 sigue abierto** — ninguno de estos cambios lo toca.

## Review

**Veredicto: FAIL** (2026-09-26). Nota de aislamiento: esta revisión corrió en la misma sesión de Claude Code que acaba de implementar el código con `delivery-engineer` — no hay aislamiento real de contexto, solo procedimental (se reconstruyó el veredicto desde artefactos y comandos ejecutados de nuevo, no desde memoria de la implementación).

Verificaciones ejecutadas (evidencia completa en `## Review`/`## Testing` del [PR #48](https://github.com/rolion/praxsa-django-panel-admin/pull/48)):
- Backend: `manage.py test` → 142/142 OK. `makemigrations --check` → sin cambios pendientes. `flake8`/`bandit` no instalados/configurados — verificación no realizada.
- Frontend: `ng build` limpio, `ng lint` limpio, `ng test --code-coverage` → 54/69 (mismas 15 fallas preexistentes de la plantilla, ninguna nueva). `npm audit` → 3 vulnerabilidades preexistentes de la plantilla, no introducidas por este PR.
- Verificación manual en vivo contra `manage.py runserver` real: confirmó que las imágenes se sirven correctamente en `/media/`, y en el proceso encontró el bug de REV-01.

Issues abiertos:
- [REV-2026-09-26-modulo-vehiculos-01.md](../reviews/REV-2026-09-26-modulo-vehiculos-01.md) — **Critical**, IMPLEMENTATION. Crear un Modelo desde la UI real (siempre envía `FormData`) lo deja `is_active=False` por cómo DRF interpreta un `BooleanField` ausente en payloads tipo formulario; el modelo desaparece del listado inmediatamente. Reproducido en vivo con `curl`. No detectado por los tests existentes porque los tests que crean vía multipart nunca verifican `is_active` en la respuesta.
- [REV-2026-09-26-modulo-vehiculos-02.md](../reviews/REV-2026-09-26-modulo-vehiculos-02.md) — Medium → **Low** (actualizado 2026-09-26: `model-edit`/`model-view` ya tienen spec, agregados en los cambios post-review; solo falta `model-create`).

Plan compliance: sin scope creep (diff coincide con los archivos declarados en el plan v2), ADRs respetados en el diseño de datos/API. Ambos issues son de calidad de implementación, no de plan ni de arquitectura.

## Publicación
_Pendiente_
