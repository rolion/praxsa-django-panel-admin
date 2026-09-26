# PLAN-2026-09-25-modulo-usuarios-perfiles-grupos-roles-sucursales (v2)

**Task:** TASK-modulo-usuarios-perfiles-grupos-roles-sucursales
**DDRs relacionados:** [DDR-modulo-usuarios-perfiles-grupos-roles-sucursales-listado-y-flujo-usuarios](../design/DDR-modulo-usuarios-perfiles-grupos-roles-sucursales-listado-y-flujo-usuarios.md)
**ADRs relacionados:** [ADR-modulo-usuarios-perfiles-grupos-roles-sucursales-modelo-datos-permisos](../adr/ADR-modulo-usuarios-perfiles-grupos-roles-sucursales-modelo-datos-permisos.md), [ADR-modulo-usuarios-perfiles-grupos-roles-sucursales-api-autenticacion-admin](../adr/ADR-modulo-usuarios-perfiles-grupos-roles-sucursales-api-autenticacion-admin.md)

## Objective

Agregar al panel `panel_admin/` un módulo de gestión de Usuarios (con Perfiles, Grupos, Roles y Sucursales) construido sobre `django.contrib.auth` estándar, reemplazando el login/mock actual del panel por una integración HTTP real contra `praxsa_manager`, para que el personal administrativo pueda crear/ver/editar/desactivar usuarios y administrar sus grupos, permisos y sucursales desde una superficie propia distinta al admin de Django.

**Nota (v2):** el backend y el frontend de este módulo ya están implementados (ver `## Implementación` del TASK) y pasaron por un Quality Gate (`delivery-review`, PR #47) que encontró 4 issues — 3 de implementación (uno de ellos un bug real confirmado ejecutando el endpoint) y 1 de plan (este mismo documento, desactualizado). Este v2 no vuelve a plantear el módulo desde cero: reconcilia lo que ya cambió por fuera de este plan (login, menú) y agrega los pasos puntuales para resolver los issues abiertos.

## Context

Ver `docs/tasks/TASK-modulo-usuarios-perfiles-grupos-roles-sucursales.md` (`## Investigación`, `## Implementación`, `## Review`) para el detalle completo. Resumen de lo que ya está decidido y no se reabre en este plan:

- **Modelo de datos** (ADR modelo-datos-permisos): `Profile` nuevo 1:1 con `User` (solo `phone_number`); "Roles" = `Group`+`Permission` nativos, sin tabla `Rol` paralela; `Sucursal.empleado` (ya existente) es la única fuente de verdad usuario↔sucursal; soft delete = `User.is_active=False`.
- **Auth/API** (ADR api-autenticacion-admin, actualizado tras el merge con `master`): Token auth de DRF (no JWT); el login real de `panel_admin/` terminó siendo `PanelAdminAuthToken` (`/product/api-panel-admin-token-auth/`) de `TASK-login-panel-admin-backend` (PR #46, mergeado antes que este) — **no** el `StaffAuthToken`/`admin-token-auth/` que proponía v1 de este plan, ver "Reconciliación" abajo. Endpoints REST de gestión (`/product/users`, `/groups`, `/sucursales`, etc.) siguen bajo `DjangoModelPermissions` + `IsStaffUser`, sin cambios.
- **UI** (DDR listado-y-flujo-usuarios, con su propia actualización post-implementación): `ngx-datatable` (no `angular-datatables`), páginas propias para Ver/Editar (no modal), wizard de 4 pasos para crear, `ng-select` para selección múltiple de grupos/sucursales. El menú final quedó en **3 submenús** (Credenciales, Grupos, Sucursales) tras pedido explícito del usuario en vivo — "Usuarios"+"Perfiles" se consolidaron en "Credenciales" y "Roles" se eliminó (los permisos ya se asignan directo en el formulario de Grupos, con `groupBy="app_label"`).

### Reconciliación con `TASK-login-panel-admin-backend` (por qué el plan v1 quedó desactualizado)

Mientras se implementaba este módulo, se mergeó `master`, que ya traía mergeado un task paralelo (`TASK-login-panel-admin-backend`, PR #46) resolviendo el mismo problema de login de `panel_admin/` con su propio endpoint (`PanelAdminAuthToken`, sin verificación de `is_staff` — decisión de negocio explícita de ese task) y su propio rediseño de sidebar/login (branding PRAXSA, menú reducido a solo Dashboard). Al resolver el conflicto se adoptó ese login (se descartó el `StaffAuthToken` propio de este plan) y se concilió el menú (Dashboard + Usuarios, en vez de que uno pisara al otro). Esto ya está documentado en el ADR y el DDR de este task, pero nunca se reflejó aquí — es exactamente el hallazgo `REV-2026-09-26-modulo-usuarios-perfiles-grupos-roles-sucursales-04` que motiva este v2.

## Current behavior

- `praxsa_manager/product/custom_views/auth_token.py` — tiene `CustomAuthToken` (para `proforma/`, sin cambios) y `PanelAdminAuthToken` (login real de `panel_admin/`, ya implementado y en producción de código — no requiere trabajo nuevo).
- `praxsa_manager/product/custom_views/user_admin.py` — `UserListCreateView`, `UserDetailView`, `UserSetPasswordView`, `UserToggleActiveView`, `GroupListCreateView`, `GroupDetailView`, `PermissionListView`, `SucursalListCreateView`, `SucursalDetailView` — todas implementadas y con tests, **excepto `UserDetailView`** (sin ningún test, ver `REV-02`).
- `praxsa_manager/product/serializer/user_admin_serializer.py:29-45` (`UserAdminSerializer.update()`) — actualiza `Profile` con `Profile.objects.update_or_create(user=instance, defaults=profile_data)`, pero `instance` llega desde `UserDetailView.queryset` con `select_related('profile')` ya resuelto — la respuesta serializada después de `update()` lee el `instance.profile` cacheado (viejo), no el que acaba de guardarse. **Bug confirmado** ejecutando un `PATCH` real (`REV-2026-09-26-modulo-usuarios-perfiles-grupos-roles-sucursales-01`): la base de datos queda bien, la respuesta HTTP no.
- `panel_admin/src/app/users/` — módulo completo implementado: `list/`, `view/`, `edit/`, `create/` (wizard), `groups/`, `sucursales/` (no hay `roles/`, se eliminó).
- `panel_admin/src/assets/data/routes.json` — menú con 2 entradas de primer nivel (Dashboard, Usuarios) y el submenú de Usuarios con 3 ítems (Credenciales, Grupos, Sucursales).
- `ng lint` (`panel_admin/`) falla con 2 errores `@typescript-eslint/no-explicit-any` en `core/guard/auth.guard.spec.ts:31` y `users/list/users-list.component.spec.ts:69` (`REV-2026-09-26-modulo-usuarios-perfiles-grupos-roles-sucursales-03`).

## Expected behavior

- El personal de staff inicia sesión en `panel_admin/` con sus credenciales reales de `praxsa_manager` (ya funciona vía `PanelAdminAuthToken`, sin cambios en este plan).
- El menú lateral muestra "Usuarios" con submenús Credenciales, Grupos, Sucursales (ya implementado, sin cambios en este plan).
- La tabla de Credenciales lista usuario/correo/nombre/apellido/teléfono con acciones Ver/Editar/Eliminar/Activar (ya implementado; "Cambiar contraseña" vive como sección propia dentro de Editar, no como botón de fila — decisión de implementación ya tomada, no se reabre).
- El wizard de creación ya funciona atómicamente (sin cambios en este plan).
- **Nuevo en este plan**: `PATCH /product/users/<id>/` devuelve en su respuesta los datos realmente guardados (incluido `phone_number`), sin depender de una relación cacheada obsoleta.
- **Nuevo en este plan**: `UserDetailView` (GET y PATCH) tiene cobertura de test que hubiera atrapado el bug anterior.
- **Nuevo en este plan**: `ng lint` pasa sin errores en `panel_admin/`.

## Architecture considerations

Sin cambios de arquitectura en este v2 — los ADR siguen vigentes tal como están. El fix de `REV-01` es una corrección de implementación (manejo de caché de Django en una relación 1:1), no una decisión arquitectónica nueva.

## Proposed solution

Todo lo de v1 (backend completo, frontend completo, menú, wizard) **ya está implementado y no se re-explica aquí** — ver `docs/tasks/TASK-modulo-usuarios-perfiles-grupos-roles-sucursales.md` `## Implementación` para el resumen de lo hecho. Este v2 agrega solo los pasos puntuales para cerrar los 3 issues de implementación abiertos:

16. **Fix `REV-01`** — en `UserAdminSerializer.update()` (`praxsa_manager/product/serializer/user_admin_serializer.py:29-45`), después de aplicar `Profile.objects.update_or_create(...)`, refrescar la relación cacheada antes de que DRF serialice la respuesta. Opción más simple y menos invasiva: en `UserDetailView.update()`/`partial_update()` (o sobrescribiendo `get_object()`), volver a resolver el objeto con una query fresca antes de devolver la respuesta — por ejemplo, que la vista, tras `serializer.save()`, haga `instance = self.get_queryset().get(pk=instance.pk)` y devuelva `Response(self.get_serializer(instance).data)` en vez de reusar `serializer.data` directamente. Alternativa dentro del propio serializer: en `update()`, tras el `update_or_create`, hacer `instance.refresh_from_db()` y reasignar explícitamente `instance.profile = Profile.objects.get(user=instance)` antes de `return instance` (más acoplado al detalle de implementación de Django, pero no requiere tocar la vista). Cualquiera de las dos es aceptable — decisión de implementación, no de arquitectura.
17. **Fix `REV-02`** — agregar una clase de test nueva en `praxsa_manager/product/tests/test_user_admin_module.py` (p. ej. `UserDetailViewTest`) cubriendo: `GET` de detalle (200, shape correcto); `PATCH` feliz verificando que **la respuesta** (no solo la base de datos) refleje `first_name`, `phone_number`, `groups` y `sucursales` actualizados (este caso es el que hubiera atrapado `REV-01` antes de mergear); `PATCH` sin permiso `change_user` → 403.
18. **Fix `REV-03`** — en `panel_admin/src/app/core/guard/auth.guard.spec.ts:31`, tipar el acceso a `currentUserSubject` sin `as any` (por ejemplo, un tipo local `AuthServiceWithInternals` o exponer un método de test-only); en `panel_admin/src/app/users/list/users-list.component.spec.ts:69`, tipar el valor de `spyOn(Swal, 'fire').and.returnValue(...)` según el tipo real que expone `sweetalert2` (`SweetAlertResult`) en vez de `as any`.

No hay paso 19 — el issue `REV-04` (este plan desactualizado) se resuelve con la publicación de este mismo v2, no con un paso de código adicional.

## Files/components affected

**Backend (nuevo en v2):**
- `praxsa_manager/product/serializer/user_admin_serializer.py` (fix `REV-01`) **o** `praxsa_manager/product/custom_views/user_admin.py` (`UserDetailView`, si el fix se hace en la vista en vez del serializer)
- `praxsa_manager/product/tests/test_user_admin_module.py` (clase de test nueva, `REV-02`)

**Frontend (nuevo en v2):**
- `panel_admin/src/app/core/guard/auth.guard.spec.ts` (fix de tipo, `REV-03`)
- `panel_admin/src/app/users/list/users-list.component.spec.ts` (fix de tipo, `REV-03`)

Todo lo demás (modelos, serializers, vistas, migraciones, módulo `users/` completo, menú, wizard) ya está implementado — ver v1 de este mismo documento (historial de git) para el detalle original, o `## Implementación` del TASK para el resumen de lo que se construyó.

## Test strategy

- **Backend**: el nuevo test de `UserDetailView` (paso 17) es obligatorio y debe fallar contra el código actual (reproduce `REV-01`) y pasar una vez aplicado el fix del paso 16 — es la prueba de que el fix es real, no solo una corrección "a ojo".
- **Frontend**: no se agregan tests nuevos de comportamiento en v2 — el paso 18 es una corrección de tipos que no cambia comportamiento, solo debe seguir pasando la suite existente (30/45, con las mismas 15 fallas preexistentes de la plantilla ya documentadas en el PR).
- **E2E**: sigue sin corresponder, mismo razonamiento que v1 — ninguno de los 3 fixes de este v2 es un caso que solo un E2E real detectaría; el bug de `REV-01` ya se detectó y se reproduce con un test de integración normal (`self.client.patch(...)` contra Postgres real).
- **Manual**: repetir la verificación manual del wizard/edición en vivo (ya hecha una vez para v1) específicamente sobre el flujo de edición, confirmando que el teléfono mostrado tras guardar coincide con lo ingresado (antes del fix se veía el valor viejo si algo llegara a leer la respuesta del PATCH directamente, aunque hoy el frontend no lo hace).

## Acceptance criteria

Los criterios de v1 ya cumplidos (verificados en el Quality Gate del PR #47) se mantienen sin cambios y no se repiten acá salvo que este v2 los modifique explícitamente:

- [x] `Profile` existe, migración aplicada sin tocar migraciones previas.
- [x] ~~Login de staff (`is_staff=True`) obtiene token vía el endpoint nuevo...~~ **Reemplazado**: el login real es `PanelAdminAuthToken` (`/product/api-panel-admin-token-auth/`), sin verificación de `is_staff` (decisión de `TASK-login-panel-admin-backend`); los endpoints de gestión de usuarios siguen exigiendo `is_staff` + permiso Django independientemente de cómo se logueó.
- [x] Crear usuario vía el wizard completo crea `User`+`Profile`+relaciones atómicamente.
- [x] Username duplicado, password inválido, confirmación no coincidente → 400.
- [x] La contraseña nunca se persiste en texto plano.
- [x] Un usuario no puede desactivarse a sí mismo.
- [x] Endpoints nuevos rechazan sin `Permission` ni sin `is_staff`.
- [x] ~~Menú "Usuarios" con sus 5 submenús~~ **Reemplazado**: menú con 3 submenús (Credenciales, Grupos, Sucursales), por pedido explícito del usuario.
- [x] Tabla de Credenciales con las columnas pedidas y acciones Ver/Editar/Eliminar/Activar (botones circulares con FontAwesome); "Cambiar contraseña" vive en la página de Editar, no en la fila de la tabla.
- [x] Eliminar = `is_active=False`, oculto por defecto con filtro "mostrar inactivos".
- [ ] **Nuevo (v2)**: `PATCH /product/users/<id>/` devuelve en su respuesta el `phone_number` (y el resto de los campos de `Profile`) realmente guardado, verificado con un test que falla contra el código pre-fix.
- [ ] **Nuevo (v2)**: existe al menos un test para `UserDetailView` (GET y PATCH, incluido el caso sin permiso).
- [ ] **Nuevo (v2)**: `npx ng lint` en `panel_admin/` termina sin errores.
- [ ] Suite de tests backend y frontend en verde (backend: 100% + los nuevos de `UserDetailView`; frontend: mismas 30/45 de siempre, sin nuevas fallas).

## Risks

- **El fix de `REV-01` toca código ya cubierto por otros tests** (`UserAdminSerializer`, usado también por `UserListCreateView`/creación): mitigado corriendo la suite completa de `test_user_admin_module.py` (no solo el test nuevo) después del fix, para confirmar que no rompe la creación ni el resto de los casos ya verificados.
- **Elegir dónde aplicar el fix (serializer vs. vista) puede no ser obvio**: se deja como decisión de implementación (ver paso 16), ambas opciones son igualmente válidas y de bajo riesgo — no bloquea el plan.

## Out of scope

- Migrar `proforma/` a Angular 21 o fusionar código con `panel_admin/`.
- Migrar el token a cookie `httpOnly`.
- Una vista de "Perfil" separada de "Credenciales" para autoedición.
- Desplegar `panel_admin/` a producción.
- Revisar si `PanelAdminAuthToken` debería exigir `is_staff` (decisión de negocio de `TASK-login-panel-admin-backend`, explícitamente pospuesta por ese task — no se reabre acá).

## Dependencias nuevas

Ninguna.

## Changelog

- **v2** (2026-09-26): Reconcilia el plan con la implementación real (login `PanelAdminAuthToken` en vez de `StaffAuthToken` propio, menú de 3 submenús en vez de 5) y agrega 3 pasos nuevos (16, 17, 18) para cerrar los issues del Quality Gate. Solicitado por `delivery-review`, referenciando `REV-2026-09-26-modulo-usuarios-perfiles-grupos-roles-sucursales-01` (bug de caché en `PATCH`, High), `-02` (falta de test para `UserDetailView`, Medium), `-03` (2 errores de `ng lint`, Low) y `-04` (este plan desactualizado, Low — resuelto por la existencia misma de este v2).
