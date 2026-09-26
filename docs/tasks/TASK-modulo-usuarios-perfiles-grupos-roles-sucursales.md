# TASK-modulo-usuarios-perfiles-grupos-roles-sucursales: Módulo de Usuarios, Perfiles, Grupos, Roles y Sucursales en `panel_admin/`

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** `claude/admin-panel-user-module-bd8fd2`
**Pull Request:** [#47](https://github.com/rolion/praxsa-django-panel-admin/pull/47)

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-09-25 | (nuevo) → INVESTIGATION | Task creado | delivery-investigate |
| 2026-09-25 | INVESTIGATION → ARCHITECTURE | Diseño de UI completado (menú, tabla, wizard, componentes de plantilla); veredicto de complejidad del task exige decisión arquitectónica (modelo de datos, permisos, auth) antes de planificar | delivery-design |
| 2026-09-25 | ARCHITECTURE → PLANNING | Decisiones de modelo de datos (Profile, Group/Permission como Roles, Sucursal.empleado único, soft delete vía is_active) y de autenticación/API admin (Token auth, endpoint de login staff nuevo, permisos Django nativos) registradas en ADR | delivery-architect |
| 2026-09-25 | PLANNING → ENGINEERING | Plan v1 escrito (backend primero, frontend después), PR #47 abierto sobre la rama ya asignada a este task por el entorno de trabajo | delivery-plan |
| 2026-09-25 | ENGINEERING (implícito) | Backend y frontend implementados en la misma sesión que planificó (backend: Profile/serializers/endpoints/login staff, 15 tests; frontend: auth real + módulo `users/` completo, 8 tests); conflictos de merge con `master` (que ya traía `TASK-login-panel-admin-backend`) resueltos adoptando su login/branding y conciliando el menú; varios ajustes de UI (consolidar menú a "Credenciales", quitar "Roles", iconos redondos, quitar numeración del wizard) aplicados en vivo por pedido directo del usuario | delivery-engineer (conversacional, sin transición formal registrada en su momento) |
| 2026-09-26 | ENGINEERING → REVIEW → PLANNING | Quality Gate corrido (backend 100/100, frontend build limpio, 30/45 tests con las mismas 15 fallas preexistentes de la plantilla, `ng lint` con 2 errores nuevos, `npm audit` solo con deuda preexistente). Verificación funcional real encontró un bug confirmado (PATCH de usuario devuelve `phone_number` desactualizado en la respuesta, sin test que lo hubiera atrapado) más una brecha de trazabilidad (plan v1 nunca versionado pese a que ADR/DDR ya registran cambios post-merge). FAIL — 4 issues (1 PLAN, 3 IMPLEMENTATION) | delivery-review |
| 2026-09-26 | PLANNING → ENGINEERING | Plan versionado a v2: reconciliado con la implementación real (login `PanelAdminAuthToken`, menú de 3 submenús) y con 3 pasos nuevos (16-18) para cerrar REV-01/02/03 | delivery-plan |
| 2026-09-26 | ENGINEERING → REVIEW | Pasos 16-18 del plan v2 implementados: fix del bug de caché en `PATCH /users/<id>/` (REV-01, verificado revirtiéndolo temporalmente y confirmando que el test nuevo falla como se esperaba), `UserDetailViewTest` nuevo (REV-02), `ng lint` limpio (REV-03). Backend 103/103, frontend build+lint limpios, 30/45 tests (mismas 15 fallas preexistentes, 0 nuevas) | delivery-engineer |
| 2026-09-26 | REVIEW → PUBLISH | Quality Gate corrido de nuevo, verificación independiente de cada fix (incluida una reversión manual del fix de REV-01 para confirmar que el test lo detecta). Backend 103/103, `ng lint` limpio, `ng build` sin errores, frontend 30/45 (mismas 15 fallas preexistentes, 0 nuevas), `npm audit` solo con deuda preexistente. Los 4 issues de la revisión anterior quedaron Resolved. PASS — 0 issues nuevos | delivery-review |

## Investigación

### Requerimiento
Agregar al nuevo panel de administración (`panel_admin/`, plantilla Angular) una opción principal de menú **Usuarios** con submenús **Usuarios**, **Perfiles**, **Grupos**, **Roles** y **Sucursales**.

- **Usuarios**: gestiona credenciales/acceso (username, password, estado activo/inactivo, grupos asignados). Tabla con columnas usuario, correo, nombre, apellido, teléfono y acciones (ver, editar, cambiar contraseña, activar/desactivar). Eliminar = soft delete, no borrado físico.
- **Perfiles**: datos personales (nombre, apellido, correo, teléfono, sucursales asignadas), separado del modelo de credenciales al estilo `User`/`Profile` de Django.
- **Grupos**: gestión de grupos (Django `Group`).
- **Roles**: gestión de roles/permisos asignables a grupos.
- **Sucursales**: gestión de sucursales.
- Relaciones: Usuario ↔ Grupo (M2M, 0 o varios) y Usuario ↔ Sucursal (M2M, 0 o varias).
- Flujo de creación de usuario en 4 pasos (credenciales → perfil → grupos → confirmación), con validación de contraseña vía las reglas de Django (`AUTH_PASSWORD_VALIDATORS`), hashing estándar de Django (nunca custom), y creación atómica de user+profile+grupos+sucursales en el backend.
- Debe reusar el modelo de autenticación/usuarios/grupos/permisos de Django "siempre que sea posible", no un sistema paralelo.

### Hechos encontrados

**Backend (`praxsa_manager/`) — modelo de usuarios y permisos**
- No hay `AUTH_USER_MODEL` custom en `praxsa_manager/praxsa_manager/settings.py` — el proyecto usa `django.contrib.auth.models.User` por defecto (confirmado por `swappable_dependency(settings.AUTH_USER_MODEL)` apuntando siempre al modelo estándar en todas las migraciones revisadas, p. ej. `product/migrations/0070_proforma_header_created_by.py:11`).
- `INSTALLED_APPS` (`praxsa_manager/praxsa_manager/settings.py:41-56`) ya incluye `django.contrib.auth`, `django.contrib.admin`, `rest_framework`, `rest_framework.authtoken` — no incluye `rest_framework_simplejwt` ni ninguna librería JWT.
- `AUTH_PASSWORD_VALIDATORS` (`settings.py:168-181`) ya configura los 4 validadores estándar de Django (`UserAttributeSimilarityValidator`, `MinimumLengthValidator`, `CommonPasswordValidator`, `NumericPasswordValidator`) — listos para reusar en cualquier formulario/serializer nuevo.
- `REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES']` = `['rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly']` (`settings.py:119-129`) — el proyecto ya delega en el sistema de permisos estándar de Django (`auth.Permission`/`ContentType`), no en uno custom.
- Django `Group` (de `django.contrib.auth.models`) **ya se usa activamente** en el backend como mecanismo de rol: `product/helper/user.py:4-25` (`User_Helper`) compara `user.groups.values_list('name', flat=True)` en minúsculas contra literales `'admin'`, `'instalador'`, `'supervisor'`, `'caja'` para decidir permisos de negocio (p. ej. `can_view_all_sucursales`, línea 24-25). No hay modelo de "Rol" separado de `Group`/`Permission` — hoy el "rol" es literalmente el nombre del `Group`.
- `Sucursal` (`product/models.py:101-109`): `name`, `address`, `enable_to_install_windows_film` (bool), `empleado` = `ManyToManyField(User)` ya existente, `phone_number`. **Ya es M2M con `User`** — la relación usuario↔sucursal pedida en el requerimiento ya existe en el modelo, con el nombre de campo `empleado` (no `sucursales`).
- No existe ningún modelo `Profile` en `product/models.py` (verificado con `Read` completo del archivo hasta la línea 118 y `Grep` de `class Profile` sin resultados) — no hay dónde guardar `teléfono` hoy; el `User` estándar de Django trae `username`, `password`, `first_name`, `last_name`, `email`, `is_active`, `groups`, `user_permissions`, pero no `phone_number`.
- No existe ningún modelo de "Rol" separado de `Group`/`Permission` (`Grep` de `class Rol`/`class Role` sin resultados).
- No hay soft delete en ningún lado del backend: `Grep` de `is_deleted|soft_delete|SoftDelete|deleted_at` en todo `praxsa_manager/` sin resultados. El único campo booleano de estado existente y usado en el dominio es el propio `User.is_active` de Django (estándar) y `Sucursal.enable_to_install_windows_film` (para otro propósito).
- No existe ningún endpoint REST de administración de usuarios/grupos/roles/sucursales hoy. `product/urls.py` solo expone: `create_client` (registro de cliente final, `ClientSerializer` en `product/serializer/client_serializer.py:6`, campos `email, password, name, lastname, phone_number, ci_nit` — es para el flujo de `proforma/`, no para el panel admin), `api-token-auth/` (`CustomAuthToken`), y endpoints de catálogo/proforma/inventario. No hay serializer para `Sucursal`, `Group` ni `User` orientado a gestión administrativa (`ls product/serializer/` solo lista `client_serializer.py`, `invoice_serializer.py`, `layer_serializer.py`).
- El panel de administración interno actual del proyecto es el Django admin por defecto (`django.contrib.admin` en `INSTALLED_APPS`), que ya trae gestión de `User`/`Group`/`Permission` "gratis" (no hay `admin.site.unregister`/override visto para esos modelos en `Grep` de `product/admin_config/*.py`). El requerimiento pide una superficie **nueva** en `panel_admin/` (Angular), no modificar ese admin de Django.

**Frontend nuevo (`panel_admin/`) — estado real de la plantilla**
- `panel_admin/` es un proyecto Angular **standalone** independiente (`angular.json`/`package.json` propios), Angular `^21.0.8`, sin relación de import con `proforma/` (Angular `^16.1.0`) — confirmado en `docs/frontend/panel_admin/reference.md:5-18`.
- `panel_admin/src/app/core/service/auth.service.ts:15-24,37-56` — el login es **100% mock hardcodeado en memoria**: un array `users` fijo (`admin@email.com`/`admin@123`), sin ninguna llamada HTTP. No hay integración real con ningún backend todavía.
- `panel_admin/src/app/core/models/user.ts:1-7` — el modelo `User` del frontend solo tiene `id, username, password, firstName, lastName, token`; sin rol ni permisos.
- `panel_admin/src/app/core/guard/auth.guard.ts:1-8` (citado en `reference.md:67-75`) solo verifica `currentUserValue` (sesión existe), no rol/permiso.
- `panel_admin/src/environments/environment.ts` y `environment.development.ts` — `apiUrl: 'http://localhost:4200'` (el puerto del propio Angular dev server, no el de `praxsa_manager`) — no apunta al backend Django hoy.
- El menú lateral se define en JSON estático `panel_admin/src/assets/data/routes.json`, tipado por `RouteInfo` (`panel_admin/src/app/layout/sidebar/sidebar.metadata.ts:2-12`: `path, title, iconType, icon, class, groupTitle, badge, badgeClass, submenu`) y se carga vía `SidebarService.getRouteInfo()` (`panel_admin/src/app/layout/sidebar/sidebar.service.ts:17-22`), consumido por `SidebarComponent.ngOnInit` (`panel_admin/src/app/layout/sidebar/sidebar.component.ts:94-99`) solo si hay `authService.currentUserValue`. Agregar la entrada de menú "Usuarios" con sus 5 submenús es, en este punto, editar ese JSON siguiendo el patrón ya usado para "Multi level Menu" (`routes.json:171-250`, que ya anida hasta 3 niveles vía `submenu`).
- El routing raíz (`panel_admin/src/app/app.routes.ts:7-41`) ya sigue un patrón de módulo con lazy loading por `loadChildren` + archivo `<feature>.routes.ts` propio (ver `dashboard.routes.ts`, `advance-table.routes.ts`, `multilevel.routes.ts`) — un módulo nuevo "Usuarios" seguiría ese mismo patrón.
- La plantilla ya trae página de ejemplo de tabla con paginación/orden/filtro (`panel_admin/src/app/advance-table/`, usa `ngx-datatable`, ver `docs/frontend/panel_admin/reference.md:85`) y un patrón de menú multinivel real (`panel_admin/src/app/multilevel/`) reutilizable para el submenú de Usuarios.

### Hipótesis / supuestos no confirmados
- No se confirmó si `panel_admin/` está pensado para reemplazar al Django admin actual o para coexistir como un panel adicional — el requerimiento asume "el nuevo panel admin" pero no se investigó ningún documento de producto que lo declare explícitamente fuera de `docs/frontend/panel_admin/reference.md`, que ya lo trata como decisión pendiente de `delivery-architect` (línea 18: "mantener `panel_admin/` como app separada... sin fusionar el código con `proforma/`" es una de las opciones, no una decisión tomada).
- No se confirmó si el backend expondrá esta gestión vía `rest_framework.authtoken` (Token auth, como ya usa `proforma/`) o si se introducirá un mecanismo distinto — `reference.md:76` señala que la plantilla trae JWT vía `jwt.interceptor.ts`, pero el backend no tiene `simplejwt` instalado, así que probablemente haya que adaptar el interceptor a Token auth, aunque esto no se verificó como decisión tomada.
- No se confirmó si "Roles" debe ser un modelo Django nuevo (tabla `Rol`) distinto de `Group`, o si "Roles" es simplemente la UI para administrar `Group`+`Permission` de Django (el requerimiento dice "Grupos (gestión de grupos)" y "Role (gestión de roles, permisos que se pueden agregar a los grupos)" como cosas separadas, pero Django no tiene un concepto de "Rol" nativo entre `User` y `Group`/`Permission` — esto es ambiguo y no se resolvió leyendo código, es una pregunta de diseño/arquitectura).
- No se confirmó cómo se relaciona el "Perfil" nuevo con `Sucursal.empleado` (M2M ya existente hoy en `Sucursal`, no en un `Profile`) — si el nuevo `Profile.sucursales` reemplaza ese M2M, lo espeja, o convive con él, es una decisión de arquitectura, no un hecho verificable en el código actual.
- No se confirmó si existe ya un flujo de "reset password" esperado por el negocio (el requerimiento original solo pide password en la creación, más "cambiar contraseña" como acción de la tabla) — no se investigó más allá de constatar que no existe endpoint de cambio de contraseña hoy en `product/urls.py`.

### Módulos y dependencias relacionadas
- **Backend**: `praxsa_manager/product/models.py` (agregar `Profile`, posiblemente `Rol` o reusar `Group`), `product/serializer/` (nuevos serializers: `User`, `Profile`, `Group`, `Permission`, `Sucursal`), `product/urls.py` (nuevos endpoints REST), `praxsa_manager/settings.py` (`REST_FRAMEWORK`, posible ajuste de permisos), `product/migrations/` (última migración real: `0106_proforma_header_status.py` — cualquier migración nueva debe partir de ahí), `product/helper/user.py` (ya tiene la lógica de grupo/rol a reusar o extender).
- **Frontend**: `panel_admin/src/app/` completo — requiere un módulo nuevo (p. ej. `panel_admin/src/app/users/`) con sub-rutas para usuarios/perfiles/grupos/roles/sucursales, actualizar `panel_admin/src/assets/data/routes.json` (menú), reemplazar `core/service/auth.service.ts` (login mock → HTTP real contra `praxsa_manager`), `core/models/user.ts` (agregar campos de rol/permiso), `core/guard/auth.guard.ts` (agregar verificación de permiso, no solo sesión), `environments/environment*.ts` (`apiUrl` real del backend).

### Implementaciones similares existentes
- **Patrón de tabla con acciones**: `panel_admin/src/app/advance-table/` (`ngx-datatable`) es la referencia más cercana a la tabla de usuarios pedida (columnas + acciones), documentado en `docs/frontend/panel_admin/reference.md:85`.
- **Patrón de menú multinivel**: `panel_admin/src/app/multilevel/` + su entrada en `routes.json:171-250` es el ejemplo real más parecido a un menú "Usuarios" con 5 submenús.
- **Patrón de resolución de rol por grupo**: `product/helper/user.py` (`User_Helper`) ya resuelve "rol" comparando nombre de `Group` — cualquier solución de "Roles" en el backend nuevo debería evaluar si extiende este helper o lo reemplaza, no inventar un tercer mecanismo.
- **Patrón de filtrado por sucursal + `DjangoModelPermissionsOrAnonReadOnly`**: los `ModelAdmin` del Django admin (`product/admin_config/*.py`, p. ej. `PagosAdmin` mencionado en `docs/integration-and-backlog.md` ítem 10) ya filtran queryset por sucursal del usuario vía `User_Helper` — mismo patrón candidato a reusar en los nuevos endpoints REST de Sucursales/Usuarios si aplica una regla de negocio equivalente (no confirmado que aplique aquí).

### Comportamiento actual
- Hoy no existe ningún panel de gestión de usuarios/grupos/roles/sucursales fuera del admin de Django por defecto (que ya administra `User`/`Group`/`Permission` sin personalización visible). `panel_admin/` es una plantilla comprada (ex-"Oreva") recién integrada al repo (`docs/integration-and-backlog.md`, `docs/frontend/panel_admin/reference.md`) sin ninguna pantalla de negocio real construida todavía — todo lo que trae es demo/mock (login, dashboard, tablas de ejemplo).
- El backend ya modela `User` (estándar Django) y `Sucursal` (con M2M a `User`), y ya usa `Group` como mecanismo de rol en la lógica de negocio existente (filtrado por sucursal en reportes/pagos). No hay `Profile` ni "Rol" como conceptos separados hoy.

### Restricciones
- `docs/CLAUDE.md:31-38`: cambios pequeños (un objetivo por cambio, pensado para un PR); no editar migraciones ya aplicadas, crear migraciones nuevas; todo cambio de lógica de negocio lleva su test; no agregar dependencias sin avisar antes; antes de cambios que afecten varios archivos, proponer un plan y esperar confirmación.
- El requerimiento pide explícitamente reusar el modelo de auth/usuarios/grupos/permisos de Django "siempre que sea posible" — no crear un sistema paralelo. Esto ya es consistente con lo que hace el backend hoy (`User`, `Group`, `DjangoModelPermissionsOrAnonReadOnly`).
- El requerimiento pide nunca hashear contraseñas manualmente ni implementar hashing custom — el backend ya usa el mecanismo estándar de Django (`AbstractUser`/`django.contrib.auth.hashers` implícito, no hay evidencia de override).
- `docs/frontend/panel_admin/reference.md:18` marca explícitamente que la brecha de versión Angular 16 (`proforma/`) vs 21 (`panel_admin/`) es una "decisión de `delivery-architect`, no algo que se resuelva copiando archivos" — refuerza que este task no debe decidir esa integración por su cuenta.

### Riesgos identificados
- **Autenticación real pendiente de construir por completo**: `panel_admin/` no tiene ninguna integración HTTP real hoy (`auth.service.ts` es 100% mock). Cualquier pantalla de usuarios nueva depende de resolver primero cómo se autentica el panel contra `praxsa_manager` (Token auth existente vs. JWT que trae la plantilla) — impacto transversal, no solo del módulo de usuarios.
- **Ambigüedad "Grupos" vs "Roles"**: Django no distingue nativamente "Rol" de `Group`/`Permission`; construir un modelo `Rol` nuevo sin necesidad duplicaría lo que `Group` ya resuelve (riesgo de sistema paralelo, justo lo que el requerimiento pide evitar). Requiere decisión explícita antes de modelar.
- **Solapamiento con `Sucursal.empleado` ya existente**: el requerimiento pide `Profile.sucursales` (M2M), pero `Sucursal.empleado` (M2M a `User`) ya cumple ese rol hoy, consumido por bastante lógica de negocio existente (`business/inventario.py`, `business/proforma.py`, `business/pago.py`, `business/precio_venta.py`, `business/orden_trabajo.py`, todos filtran por `Sucursal.empleado`). Introducir un segundo M2M paralelo sin reconciliarlo generaría dos fuentes de verdad para "a qué sucursal pertenece un usuario" — riesgo señalado también como pregunta de negocio abierta en `docs/integration-and-backlog.md` sección 6 ("¿`Sucursal.empleado` es la única fuente de verdad...?").
- **Ningún soft delete existe hoy en el proyecto**: hay que decidir el mecanismo (probablemente `User.is_active = False`, que es literalmente la convención de Django y ya existe como campo, en vez de un flag custom) — bajo riesgo técnico pero es una decisión explícita pendiente.
- **Superficie grande para un solo cambio**: 5 submenús, un flujo de creación de 4 pasos, backend nuevo (modelos + migraciones + serializers + endpoints) y frontend nuevo (módulo Angular completo + posible reescritura de auth) — muy por encima de "un objetivo por cambio" (`docs/CLAUDE.md:31`), candidato claro a partirse en varios tasks/PRs más chicos durante `delivery-plan`.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — el requerimiento introduce un modelo de datos nuevo (`Profile`, posible `Rol`), toca autenticación/autorización de un panel que hoy no tiene ninguna integración real con el backend, se solapa con una relación M2M ya existente (`Sucursal.empleado`) que otras partes del sistema ya consumen, y abarca múltiples módulos (backend `product/` + frontend `panel_admin/` completo). Cualquiera de estos puntos por sí solo ya calificaría; juntos, decidir la arquitectura antes de planificar evita construir dos fuentes de verdad para usuario↔sucursal o un sistema de roles paralelo a `Group`.

### Diseño requerido
**SI** — es una pantalla y flujo completamente nuevos en `panel_admin/` (menú de 5 submenús, tabla con acciones, wizard de creación de 4 pasos), con componentes de la plantilla (`advance-table`, `multilevel`) que hay que decidir cómo adoptar con criterio de consistencia visual, no solo copiarlos.

## Diseño
[DDR-modulo-usuarios-perfiles-grupos-roles-sucursales-listado-y-flujo-usuarios](../design/DDR-modulo-usuarios-perfiles-grupos-roles-sucursales-listado-y-flujo-usuarios.md) — define pantallas (menú de 5 submenús, listado de Usuarios, Ver/Editar como páginas propias, wizard de creación de 4 pasos, listados simples de Grupos/Roles/Sucursales), componentes de la plantilla elegidos (`ngx-datatable` en vez de `angular-datatables`, Reactive Forms, `ng-select` para multi-selección de grupos/sucursales, edición de `routes.json` siguiendo el patrón de "Multi level Menu") y el comportamiento de UI por privilegio (ocultar acciones administrativas sin privilegio, con nota explícita de que la barrera real es responsabilidad de arquitectura/backend). "Perfiles" queda como entrada de menú sin tabla propia separada de Usuarios — a revisar si negocio pide autoedición de perfil independiente.

## Arquitectura
- [ADR-modulo-usuarios-perfiles-grupos-roles-sucursales-modelo-datos-permisos](../adr/ADR-modulo-usuarios-perfiles-grupos-roles-sucursales-modelo-datos-permisos.md) — `Profile` nuevo (1:1 `User`, solo `phone_number`; nombre/apellido/correo ya viven en `User`); "Roles" = `Group`+`Permission` nativos de Django, sin modelo `Rol` paralelo; `Sucursal.empleado` (ya existente) queda como única fuente de verdad usuario↔sucursal, sin M2M nuevo; soft delete = `User.is_active=False`.
- [ADR-modulo-usuarios-perfiles-grupos-roles-sucursales-api-autenticacion-admin](../adr/ADR-modulo-usuarios-perfiles-grupos-roles-sucursales-api-autenticacion-admin.md) — `panel_admin/` se autentica con Token auth de DRF (no JWT, pese a que la plantilla trae interceptor JWT); nuevo endpoint de login para staff (no se reusa `CustomAuthToken`, que asume `Client` y rompería con usuarios de staff); endpoints REST nuevos para User/Profile/Sucursal/Group/Permission bajo `DjangoModelPermissions` + chequeo de `is_staff`; creación de usuario = un solo POST atómico al confirmar el wizard, no un endpoint por paso.

## Plan
[PLAN-2026-09-25-modulo-usuarios-perfiles-grupos-roles-sucursales](../plans/PLAN-2026-09-25-modulo-usuarios-perfiles-grupos-roles-sucursales.md) (v2) — v1 (backend+frontend completos, ya implementados) reconciliado con la realidad post-merge (login `PanelAdminAuthToken`, menú de 3 submenús) y con 3 pasos nuevos (16-18) para `delivery-engineer`: fix del bug de caché en `PATCH /users/<id>/` (REV-01), test nuevo para `UserDetailView` (REV-02), fix de 2 errores de `ng lint` (REV-03). Ver `## Changelog` del plan.

## Implementación
**Backend** (`praxsa_manager/product/`): modelo `Profile` (migración `0107_profile.py`, aditiva); serializers nuevos (`profile_serializer.py`, `user_admin_serializer.py`, `group_serializer.py`, `sucursal_serializer.py`); `permissions.py::IsStaffUser`; vistas nuevas en `custom_views/user_admin.py` (User list/create/detail/set-password/toggle-active, Group list/detail, Permission list, Sucursal list/detail); rutas nuevas en `urls.py`. 18 tests propios (luego 15 tras la reconciliación del merge, ver abajo) en `tests/test_user_admin_module.py`, más helpers nuevos en `tests/helpers.py`.

**Frontend** (`panel_admin/`): módulo `src/app/users/` completo (list con `ngx-datatable`, view, edit, create con wizard de 4 pasos, groups, sucursales — `roles/` se agregó y luego se eliminó, ver ajustes post-implementación); `AuthService`/`jwt.interceptor`/`auth.guard` conectados a HTTP real; fix de un bug preexistente de la plantilla (`provideHttpClient()` sin `withInterceptorsFromDi()`, que hacía que los interceptors nunca corrieran).

**Merge con `master`**: mientras se implementaba, se mergeó `TASK-login-panel-admin-backend` (PR #46) — mismo problema de login resuelto en paralelo con su propio endpoint (`PanelAdminAuthToken`) y su propio rediseño de sidebar/login (branding PRAXSA, menú reducido a solo Dashboard). Se resolvieron los conflictos adoptando ese login (se descartó el `StaffAuthToken` propio) y conciliando el menú (Dashboard + Usuarios, en vez de que uno pisara al otro) — detalle completo en `ADR-modulo-usuarios-perfiles-grupos-roles-sucursales-api-autenticacion-admin.md` (sección "Actualización").

**Ajustes post-implementación** (pedidos en vivo por el usuario, aplicados directamente sin pasar por `delivery-plan`/`delivery-engineer` formalmente en el momento): consolidar "Usuarios"+"Perfiles" en un submenú único "Credenciales"; eliminar el submenú "Roles" (permisos ahora se asignan directo en el formulario de Grupos, con `groupBy="app_label"` para conservar el agrupamiento); botones de acción circulares con FontAwesome (`.btn-tbl-edit`/`.btn-tbl-delete`/`.btn-tbl-view`/`.btn-tbl-activate`, mismo patrón que `advance-table.component.html`) en Credenciales, Grupos y Sucursales; quitar la numeración de las pestañas del wizard. Todo documentado en `DDR-modulo-usuarios-perfiles-grupos-roles-sucursales-listado-y-flujo-usuarios.md` (sección "Actualización").

**Deuda/hallazgos abiertos (previos)**: ver `## Review` — el plan v1 nunca se versionó a v2 para reflejar el merge ni estos ajustes (REV-04).

**Fixes del Quality Gate (plan v2, pasos 16-18)**: `UserAdminSerializer.update()` (`praxsa_manager/product/serializer/user_admin_serializer.py`) reasigna `instance.profile` tras `Profile.objects.update_or_create()`, corrigiendo que `PATCH /product/users/<id>/` devolviera `phone_number` desactualizado en la respuesta (REV-01, verificado revirtiendo el fix temporalmente y confirmando que el test nuevo falla exactamente como se esperaba antes de restaurarlo); `UserDetailViewTest` nuevo en `test_user_admin_module.py` cubre GET, el PATCH que reproduce REV-01, y PATCH sin permiso (REV-02); 2 `as any` reemplazados por tipos explícitos en `auth.guard.spec.ts`/`users-list.component.spec.ts`, `ng lint` limpio (REV-03). Backend 103/103 tests, frontend build+lint limpios, 30/45 tests (mismas 15 fallas preexistentes de la plantilla, 0 nuevas).

## Review

### Corrida 1 (2026-09-26) — FAIL
4 issues encontrados (detalle abajo, todos marcados `Resolved` tras la corrida 2). Backend 100/100 tests, frontend build limpio, 30/45 tests frontend (15 fallas preexistentes de la plantilla, sin relación). Por tener issues PLAN + IMPLEMENTATION, la etapa volvió a **PLANNING**.

- [REV-2026-09-26-modulo-usuarios-perfiles-grupos-roles-sucursales-01](../reviews/REV-2026-09-26-modulo-usuarios-perfiles-grupos-roles-sucursales-01.md) — High, IMPLEMENTATION. `PATCH /product/users/<id>/` responde con `phone_number` desactualizado (persistencia real sí es correcta).
- [REV-2026-09-26-modulo-usuarios-perfiles-grupos-roles-sucursales-02](../reviews/REV-2026-09-26-modulo-usuarios-perfiles-grupos-roles-sucursales-02.md) — Medium, IMPLEMENTATION. Sin tests para `UserDetailView` (GET/PATCH).
- [REV-2026-09-26-modulo-usuarios-perfiles-grupos-roles-sucursales-03](../reviews/REV-2026-09-26-modulo-usuarios-perfiles-grupos-roles-sucursales-03.md) — Low, IMPLEMENTATION. 2 errores de `ng lint` (`no-explicit-any`) en specs nuevos.
- [REV-2026-09-26-modulo-usuarios-perfiles-grupos-roles-sucursales-04](../reviews/REV-2026-09-26-modulo-usuarios-perfiles-grupos-roles-sucursales-04.md) — Low, PLAN. Plan v1 desactualizado (login endpoint y menú finales no coinciden con lo escrito, aunque ADR/DDR ya lo documentan).

### Corrida 2 (2026-09-26, tras plan v2 + fixes) — PASS
Los 4 issues de la corrida 1 se verificaron de forma independiente y quedaron `Resolved` (incluida una reversión manual del fix de REV-01 para confirmar que el test nuevo realmente lo detecta — falló con `'11111111' != '99999999'` como se esperaba, luego se restauró el fix). 0 issues nuevos.

- Backend: 103/103 tests, `makemigrations --check` sin cambios pendientes.
- Frontend: `ng build` sin errores, `ng lint` limpio (0 errores), 30/45 tests (mismas 15 fallas preexistentes de la plantilla, verificado que los componentes que fallan no tienen ningún cambio de este PR, 0 regresiones nuevas).
- `npm audit`: 3 vulnerabilidades, todas preexistentes (echarts, lodash-es, xlsx), ninguna introducida por este PR.
- Backend `bandit`/`safety`: no instalados en el entorno, no ejecutados (declarado explícitamente, no un PASS silencioso).

Detalle completo de comandos/salidas en PR #47.

## Publicación
_Pendiente_
