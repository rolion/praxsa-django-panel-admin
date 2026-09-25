# PLAN-2026-09-25-modulo-usuarios-perfiles-grupos-roles-sucursales (v1)

**Task:** TASK-modulo-usuarios-perfiles-grupos-roles-sucursales
**DDRs relacionados:** [DDR-modulo-usuarios-perfiles-grupos-roles-sucursales-listado-y-flujo-usuarios](../design/DDR-modulo-usuarios-perfiles-grupos-roles-sucursales-listado-y-flujo-usuarios.md)
**ADRs relacionados:** [ADR-modulo-usuarios-perfiles-grupos-roles-sucursales-modelo-datos-permisos](../adr/ADR-modulo-usuarios-perfiles-grupos-roles-sucursales-modelo-datos-permisos.md), [ADR-modulo-usuarios-perfiles-grupos-roles-sucursales-api-autenticacion-admin](../adr/ADR-modulo-usuarios-perfiles-grupos-roles-sucursales-api-autenticacion-admin.md)

## Objective

Agregar al panel `panel_admin/` un módulo de gestión de Usuarios (con Perfiles, Grupos, Roles y Sucursales) construido sobre `django.contrib.auth` estándar, reemplazando el login/mock actual del panel por una integración HTTP real contra `praxsa_manager`, para que el personal administrativo pueda crear/ver/editar/desactivar usuarios y administrar sus grupos, permisos y sucursales desde una superficie propia distinta al admin de Django.

## Context

Ver `docs/tasks/TASK-modulo-usuarios-perfiles-grupos-roles-sucursales.md` (`## Investigación`) para el detalle completo. Resumen de lo que ya está decidido y no se reabre en este plan:

- **Modelo de datos** (ADR modelo-datos-permisos): `Profile` nuevo 1:1 con `User` (solo `phone_number`); "Roles" = `Group`+`Permission` nativos, sin tabla `Rol` paralela; `Sucursal.empleado` (ya existente) es la única fuente de verdad usuario↔sucursal; soft delete = `User.is_active=False`.
- **Auth/API** (ADR api-autenticacion-admin): Token auth de DRF (no JWT); endpoint de login nuevo para staff, aislado de `CustomAuthToken` (que rompería porque asume `Client`); endpoints REST nuevos bajo `DjangoModelPermissions` + `is_staff`; creación de usuario = un solo POST atómico.
- **UI** (DDR listado-y-flujo-usuarios): `ngx-datatable` (no `angular-datatables`), páginas propias para Ver/Editar (no modal), wizard de 4 pasos para crear, `ng-select` para selección múltiple de grupos/sucursales, menú editado en `routes.json` siguiendo el patrón de "Multi level Menu", "Perfiles" sin tabla propia separada de "Usuarios".

## Current behavior

- `panel_admin/src/app/core/service/auth.service.ts:15-76` — login 100% mock en memoria, sin HTTP.
- `panel_admin/src/app/core/models/user.ts:1-7` — sin campos de rol/permiso.
- `panel_admin/src/app/core/guard/auth.guard.ts` — solo verifica sesión, no privilegio.
- `praxsa_manager/product/custom_views/auth_token.py` (`CustomAuthToken`) — asume `Client.objects.get(user_id=user)`, rompería (500) para un usuario de staff sin `Client`.
- `praxsa_manager/product/urls.py` — sin ningún endpoint de gestión de usuarios/grupos/permisos/sucursales.
- `praxsa_manager/product/models.py:101-109` — `Sucursal` ya existe con M2M `empleado` a `User`; no hay `Profile`.
- `praxsa_manager/product/migrations/` — última migración real: `0106_proforma_header_status.py`.
- `panel_admin/src/assets/data/routes.json` — sin entrada de menú "Usuarios".

## Expected behavior

- El personal de staff inicia sesión en `panel_admin/` con sus credenciales reales de `praxsa_manager` (Token auth), no con el mock.
- El menú lateral muestra "Usuarios" con submenús Usuarios, Perfiles, Grupos, Roles, Sucursales.
- La tabla de Usuarios lista usuario/correo/nombre/apellido/teléfono con acciones Ver/Editar/Cambiar contraseña/Activar-Desactivar/Eliminar (soft).
- El wizard de creación valida credenciales, perfil, grupos y sucursales, muestra un resumen, y al confirmar crea todo atómicamente en el backend (o no crea nada si algo falla).
- Grupos/Roles(permisos)/Sucursales tienen sus propias pantallas CRUD simples.

## Architecture considerations

Ver ADRs enlazados arriba — ya cubren contrato API, autenticación, permisos y estrategia de rollback. Puntos operativos adicionales propios de este plan:

- **Orden de dependencia dura**: el frontend no puede probarse contra datos reales hasta que exista el endpoint de login de staff y al menos el endpoint de listado/creación de usuarios — el plan ordena backend antes que frontend por esta razón, no por preferencia estética.
- **Migraciones**: una sola migración nueva (`Profile`), aditiva, no debe tocar `0106_proforma_header_status.py` ni ninguna anterior (regla de `docs/CLAUDE.md`).
- **Dinero/Decimal**: no aplica — este módulo no maneja precios ni pagos.
- **Rendimiento**: el listado de usuarios debe usar `select_related('profile')` y `prefetch_related('groups', 'sucursal_set')` (o el `related_name` que se defina) para evitar N+1 al mostrar grupos/sucursales por fila si se muestran en la tabla — no se pidió explícitamente mostrarlos en la tabla (solo en Ver/Editar), así que el listado principal no necesita el prefetch de grupos/sucursales, solo de `profile` (para `phone_number`).
- **Seguridad**: los endpoints nuevos son el área más sensible de este cambio (crean usuarios, tocan contraseñas, exponen grupos/permisos). Cambiar contraseña y activar/desactivar deben, además del permiso Django, impedir que un usuario se desactive a sí mismo por error (validación explícita en el serializer/vista, no solo en el frontend).
- **Acoplamiento**: `product/helper/user.py::User_Helper` se reusa tal cual para resolver "admin" en el chequeo de acceso al módulo — no se modifica su lógica existente (usada hoy por reportes/pagos), solo se llama desde el nuevo código.

## Proposed solution

Implementación en dos fases dentro del mismo PR (backend primero, para que el frontend tenga contra qué integrarse; frontend después), con pasos pequeños y verificables en cada una.

### Fase 1 — Backend (`praxsa_manager/product/`)

1. Modelo `Profile` (`models.py`): `user = OneToOneField(User, on_delete=CASCADE, related_name='profile')`, `phone_number = CharField(validators=[RegexValidator('(\+)*\d{7,11}')], null=True)` — mismo validador de teléfono que ya usa `Sucursal.phone_number` y `Client.phone_number`, por consistencia.
2. Migración nueva (parte de `0106_proforma_header_status.py`).
3. Serializers nuevos en `product/serializer/`:
   - `ProfileSerializer` (solo `phone_number`).
   - `UserAdminSerializer` (lectura: `id, username, email, first_name, last_name, is_active, profile.phone_number, groups[], sucursales[]`; escritura restringida a los campos editables, sin `password` — password va por endpoint separado).
   - `UserCreateSerializer` (escritura, campos del wizard completo: `username, password, password_confirm, is_active, first_name, last_name, email, phone_number, sucursales(ids), groups(ids)`), con:
     - `validate_username`: unicidad (ya la garantiza `User.username` con `unique=True`, pero se valida explícito para devolver un error de campo claro, no un `IntegrityError` de 500).
     - `validate`: `password == password_confirm`; `django.contrib.auth.password_validation.validate_password(password)`.
     - `create()`: dentro de `transaction.atomic()` — `User.objects.create_user(...)`, crear `Profile`, `user.groups.set(groups)`, `sucursal.empleado.add(user)` por cada sucursal seleccionada (o el patrón M2M inverso equivalente).
   - `GroupSerializer` (nombre + `permissions` ids).
   - `SucursalSerializer` (nuevo — no existía ninguno).
4. Vista de login para staff: `StaffAuthToken(ObtainAuthToken)` en `product/custom_views/auth_token.py` (junto a `CustomAuthToken`), que valida `user.is_staff` antes de emitir el token; si no es staff, `403`.
5. Vistas nuevas (patrón de clase, consistente con `InvoiceView`/`BobinaView`) en `product/custom_views/user_admin.py` (archivo nuevo):
   - `UserListCreateView` (GET lista con paginación, POST crea con `UserCreateSerializer`).
   - `UserDetailView` (GET detalle, PATCH edición de perfil/grupos/sucursales, sin tocar password).
   - `UserSetPasswordView` (POST, valida `validate_password`, `user.set_password(...)`).
   - `UserToggleActiveView` (POST/PATCH, setea `is_active`; rechaza si `request.user == target_user`).
   - `GroupListCreateView`, `GroupDetailView` (incluye asignar `permissions`).
   - `PermissionListView` (solo lectura — lista `Permission.objects.all()` para poblar el selector de "Roles").
   - `SucursalListCreateView`, `SucursalDetailView`.
   - Todas con `permission_classes = [IsAuthenticated, DjangoModelPermissions]` + un chequeo adicional `request.user.is_staff` (mixin o chequeo explícito en cada vista, según se decida al implementar).
6. `product/urls.py`: registrar las rutas nuevas (`admin-token-auth/`, `users/`, `users/<id>/`, `users/<id>/set-password/`, `users/<id>/toggle-active/`, `groups/`, `groups/<id>/`, `permissions/`, `sucursales/`, `sucursales/<id>/`).
7. Tests backend (`product/tests/`, reusando `helpers.py` para fixtures de usuario/sucursal ya existentes):
   - Creación de usuario: caso feliz (crea `User`+`Profile`+grupos+sucursales), username duplicado (400, no 500), password que no cumple validadores (400), password/confirmación no coinciden (400).
   - Atomicidad: forzar un fallo a mitad de la creación (p. ej. sucursal inexistente) y verificar que no queda un `User` huérfano sin perfil/grupos.
   - Login de staff: usuario `is_staff=True` obtiene token; usuario `is_staff=False` (ej. un `Client`) recibe 403; `/product/api-token-auth/` (endpoint existente) sigue funcionando igual para clientes (test de no-regresión).
   - Permisos: usuario sin `Permission` correspondiente recibe 403 en cada endpoint nuevo.
   - Activar/desactivar: un usuario no puede desactivarse a sí mismo.
   - Cambiar contraseña: valida contra `AUTH_PASSWORD_VALIDATORS`, nunca guarda en texto plano (verificar `user.password` no es igual al valor enviado).

### Fase 2 — Frontend (`panel_admin/src/app/`)

8. `environments/environment.ts` y `environment.development.ts`: `apiUrl` apuntando al backend real de `praxsa_manager` (puerto/host a confirmar con el usuario — ver "Out of scope").
9. `core/models/user.ts`: agregar `email, isStaff, groups: string[]` (lo que el nuevo endpoint de login devuelve).
10. `core/service/auth.service.ts`: reemplazar el array mock por `HttpClient.post(apiUrl + '/product/admin-token-auth/', {username, password})`; guardar token+datos vía `LocalStorageService` ya existente.
11. `core/interceptor/jwt.interceptor.ts`: adaptar el header de `Bearer <token>` a `Token <token>` (esquema de DRF `TokenAuthentication`).
12. `core/guard/auth.guard.ts`: mantiene el chequeo de sesión existente; se evalúa si agregar chequeo de `isStaff` aquí o dejarlo a nivel de componente (decisión menor, no bloqueante, a resolver al implementar).
13. Nuevo módulo `panel_admin/src/app/users/` con `users.routes.ts` (lazy-loaded desde `app.routes.ts`, mismo patrón que `dashboard`/`multilevel`):
    - `list/` (tabla `ngx-datatable`, columnas usuario/correo/nombre/apellido/teléfono/acciones).
    - `view/:id` (solo lectura).
    - `edit/:id` (Reactive Form).
    - `create/` (wizard de 4 pasos: `create-step1-credentials`, `create-step2-profile`, `create-step3-groups`, `create-step4-confirm`, o un solo componente con estado de paso interno — decisión de implementación, no de diseño).
    - `groups/` (listado simple + asignación de permisos).
    - `roles/` (vista de permisos disponibles, según lo que defina el DDR — lectura+asignación desde Grupos).
    - `sucursales/` (listado simple CRUD).
14. `assets/data/routes.json`: agregar el bloque de menú "Usuarios" con sus 5 submenús, siguiendo el patrón de `routes.json:171-250` ("Multi level Menu").
15. Tests frontend (`TestBed` + `HttpTestingController`, patrón ya usado en `proforma/` según `docs/integration-and-backlog.md` backlog #8):
    - `AuthService`: login exitoso guarda token; login fallido no guarda nada; header `Token` se envía en requests subsiguientes.
    - `UsersListComponent`: renderiza filas desde la respuesta HTTP mockeada; botones de acción llaman al servicio correcto.
    - Wizard de creación: cada paso valida antes de avanzar; el resumen final refleja lo ingresado; el submit dispara un único POST con el payload completo.
    - Guard: sin sesión redirige a login (comportamiento ya existente, test de no-regresión tras el cambio de modelo `User`).

## Files/components affected

**Backend:**
- `praxsa_manager/product/models.py` (nuevo `Profile`)
- `praxsa_manager/product/migrations/` (nueva migración)
- `praxsa_manager/product/serializer/` (`profile_serializer.py`, `user_admin_serializer.py`, `group_serializer.py`, `sucursal_serializer.py` — nuevos)
- `praxsa_manager/product/custom_views/auth_token.py` (agregar `StaffAuthToken`)
- `praxsa_manager/product/custom_views/user_admin.py` (nuevo)
- `praxsa_manager/product/urls.py` (rutas nuevas)
- `praxsa_manager/product/tests/` (tests nuevos, reusando `helpers.py`)

**Frontend:**
- `panel_admin/src/environments/environment.ts`, `environment.development.ts`
- `panel_admin/src/app/core/models/user.ts`
- `panel_admin/src/app/core/service/auth.service.ts`
- `panel_admin/src/app/core/interceptor/jwt.interceptor.ts`
- `panel_admin/src/app/core/guard/auth.guard.ts` (posible)
- `panel_admin/src/app/users/**` (módulo nuevo completo)
- `panel_admin/src/assets/data/routes.json`
- `panel_admin/src/app/app.routes.ts` (registrar `loadChildren` de `users`)

## Test strategy

- **Unitario/integración backend**: sí, obligatorio — todo lo listado en el paso 7 (creación, atomicidad, login staff vs. cliente, permisos, auto-desactivación bloqueada, cambio de contraseña). Sigue el patrón ya usado en `product/tests/` con `helpers.py` (visto en `TASK-005`/`TASK-007`/`TASK-008`/`TASK-010`).
- **Unitario/integración frontend**: sí — `TestBed`+`HttpTestingController` para `AuthService`, componente de listado, y el wizard completo (validación por paso + payload final).
- **E2E (Playwright): NO corresponde para este plan.** Justificación explícita: aunque el wizard es un flujo multi-paso, el requerimiento y el DDR ya lo cubren con tests de integración de componente (`TestBed` puede simular navegación entre pasos y verificar el payload final sin un navegador real) y tests de integración backend que verifican la creación atómica end-to-end a nivel HTTP. `proforma/package.json` no tiene Playwright instalado hoy, e instalarlo sería una dependencia nueva que requiere confirmación explícita (regla de `docs/CLAUDE.md`) para un beneficio marginal sobre lo que los tests de integración ya cubren en este caso. Si más adelante aparece un bug real que solo un E2E real hubiera detectado (p. ej. un problema de integración entre el interceptor HTTP real y el guard), se puede reconsiderar en una revisión posterior — no se decide preventivamente ahora.
- **Manual**: se recomienda una prueba manual en vivo en el admin (login real de staff → crear usuario con grupos y sucursales → verificar en el Django admin que el `User`/`Profile`/`Group`/`Sucursal.empleado` quedaron consistentes), siguiendo el patrón ya usado en `TASK-007`/`TASK-008`/`TASK-010` de este mismo proyecto.

## Acceptance criteria

- [ ] `Profile` existe, migración aplicada sin tocar migraciones previas.
- [ ] Login de staff (`is_staff=True`) obtiene token vía el endpoint nuevo; un `Client` sin `is_staff` recibe 403 ahí, y sigue pudiendo loguearse sin cambios por `/product/api-token-auth/` (no-regresión verificada con test).
- [ ] Crear usuario vía el wizard completo (con 0, 1 y varios grupos; 0, 1 y varias sucursales) crea `User`+`Profile`+relaciones atómicamente; un fallo a mitad de camino no deja datos huérfanos.
- [ ] Username duplicado, password que no cumple validadores, y confirmación de password no coincidente devuelven error 400 con mensaje de campo, no 500.
- [ ] La contraseña nunca se persiste ni se loguea en texto plano (verificado en test).
- [ ] Un usuario no puede desactivarse a sí mismo.
- [ ] Endpoints nuevos rechazan (403) a un usuario sin el `Permission` Django correspondiente, y a un usuario sin `is_staff`.
- [ ] Menú "Usuarios" visible en `panel_admin/` con sus 5 submenús, siguiendo el patrón visual ya usado por "Multi level Menu".
- [ ] Tabla de Usuarios muestra usuario/correo/nombre/apellido/teléfono y acciones Ver/Editar/Cambiar contraseña/Activar-Desactivar/Eliminar.
- [ ] Eliminar = `is_active=False` (verificado que la fila no desaparece de la base de datos).
- [ ] Suite de tests backend y frontend en verde.
- [ ] Verificación manual en vivo documentada (login real, creación real, chequeo en Django admin).

## Risks

- **Tamaño del cambio**: el propio task ya señaló este riesgo en la investigación. Mitigación: dentro de este único PR (regla del skill: un PR por task), los commits se ordenan por los pasos numerados arriba (backend completo y en verde primero, frontend después) para que el diff sea revisable por fases aunque se mergee de una sola vez.
- **`StaffAuthToken` nuevo introduce una segunda forma de autenticarse**: mitigado por el test de no-regresión explícito sobre `/product/api-token-auth/` (paso 7) y por que ambos endpoints coexisten sin compartir lógica modificada.
- **`ng-select` sin ejemplo de uso previo en `panel_admin/src/app/`**: riesgo bajo (ya está en `package.json`), pero su integración exacta (multi-select con chips para grupos/sucursales) no tiene precedente en el código — se prueba con un test de componente simple antes de dar por buena la UX.
- **Ambigüedad menor no bloqueante**: si el chequeo de `isStaff` va en el guard global o en cada componente del módulo — no cambia el resultado funcional, se decide al implementar sin volver a esta etapa.

## Out of scope

- Migrar `proforma/` a Angular 21 o fusionar código con `panel_admin/` (pregunta abierta ya señalada en `docs/frontend/panel_admin/reference.md:18`, fuera del alcance de este task).
- Migrar el token a cookie `httpOnly` (deuda ya documentada como épica separada en `docs/integration-and-backlog.md` backlog #6).
- Una vista de "Perfil" separada de "Usuarios" para autoedición (el DDR ya decidió no incluirla; si negocio la pide, es un task nuevo).
- Desplegar `panel_admin/` a producción (`docker-compose*.yml`/`nginx/`) — no está conectado hoy y este task no lo conecta.
- **Pregunta abierta para el usuario, no resuelta por investigación/arquitectura/diseño**: ¿qué `apiUrl` real debe usar `panel_admin/` en desarrollo (host/puerto donde corre `praxsa_manager` localmente)? Se necesita antes de implementar el paso 8.
- **Pregunta abierta**: ¿el estado "eliminado" (`is_active=False`) debe ocultarse por defecto del listado de Usuarios (con un filtro "mostrar inactivos"), o mostrarse siempre con indicador visual? El DDR lo dejó como pregunta abierta para esta etapa y tampoco se resolvió aquí — se necesita una decisión antes de implementar el paso 13 (`list/`).

## Dependencias nuevas

Ninguna. `ng-select` ya está en `panel_admin/package.json`; no se requiere instalar Playwright (ver justificación de E2E arriba) ni ninguna librería backend nueva (`rest_framework.authtoken` ya está instalado).
