# REV-2026-09-26-modulo-usuarios-perfiles-grupos-roles-sucursales-01: `PATCH /product/users/<id>/` devuelve `phone_number` desactualizado en la respuesta (dato real sí se guarda)

**Status:** Resolved — verificado independientemente en la segunda corrida de `delivery-review` (2026-09-26) sobre el PR #47: se revirtió el fix temporalmente y se confirmó que el test nuevo falla con el mismo error (`'11111111' != '99999999'`), luego se restauró y todo pasa. Ver `## Review` de `docs/tasks/TASK-modulo-usuarios-perfiles-grupos-roles-sucursales.md`.
**Severity:** High
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-09-25-modulo-usuarios-perfiles-grupos-roles-sucursales.md (v1)
**Suggested owner:** delivery-engineer

## Description

`UserAdminSerializer.update()` (`praxsa_manager/product/serializer/user_admin_serializer.py:29-45`) actualiza el `Profile` relacionado con una llamada separada, `Profile.objects.update_or_create(user=instance, defaults=profile_data)`, sin refrescar el atributo `instance.profile` que Django ya cacheó en el objeto `User` que llega al `update()`. Ese `instance` proviene de `UserDetailView.queryset` (`praxsa_manager/product/custom_views/user_admin.py:16`), que hace `select_related('profile')` — es decir, `instance.profile` ya está resuelto y cacheado **antes** de que `update_or_create` toque la fila real en la base de datos por otro objeto Python distinto.

Cuando DRF arma la respuesta (`serializer.data` tras `save()`), el campo `phone_number` (con `source='profile.phone_number'`) lee ese `instance.profile` cacheado y stale, no el valor recién guardado — el JSON que recibe el frontend después de un PATCH exitoso trae el teléfono **viejo**, aunque la base de datos ya tiene el valor nuevo.

## Expected behavior

El plan (paso 3, `UserAdminSerializer`) y el acceptance criterion implícito de "editar perfil de usuario" esperan que la respuesta de un `PATCH` exitoso refleje los datos efectivamente guardados — es el contrato estándar de una API REST (y lo que cualquier consumidor futuro de este endpoint asumiría sin pensarlo dos veces).

## Actual behavior

Verificado ejecutando un `PATCH` real contra `UserDetailView` (test ad hoc, no commiteado, sobre la suite real con Postgres):

- Estado antes: `Profile.phone_number = '11111111'`.
- `PATCH` con `phone_number: '99999999'` → `HTTP 200`.
- Body de la respuesta: `{"...", "phone_number":"11111111", ...}` — **el teléfono viejo**.
- `target.refresh_from_db()` inmediatamente después, en el mismo test: `target.profile.phone_number == '99999999'` — **el dato en la base de datos sí es el nuevo**.

Es decir: el `PATCH` persiste correctamente, pero miente en su propia respuesta.

## Evidence

```
STATUS 200
BODY {"id":2,"username":"staffuser2@test.com","email":"nuevo@test.com","first_name":"Nuevo","last_name":"Apellido","is_active":true,"is_staff":true,"phone_number":"11111111","groups":[1],"sucursales":[1]}
first_name Nuevo
phone 99999999
groups ['rev_group']
sucursales ['RevSucursal']
```//`phone` (impreso vía `target.refresh_from_db()` después del PATCH) es `99999999` — el body de la respuesta HTTP dice `"phone_number":"11111111"`.

## Nota sobre impacto real hoy

`UserEditComponent.save()` (`panel_admin/src/app/users/edit/user-edit.component.ts`) navega a `/users/view/:id` tras un PATCH exitoso sin usar el body de la respuesta — la pantalla de "Ver" vuelve a pedir el usuario con un `GET` fresco, así que hoy el bug no es visible en la UI. Sigue siendo un defecto real del contrato de la API: cualquier consumidor que confíe en la respuesta del PATCH (otro cliente, un cambio futuro del frontend a actualización optimista, un test de integración) recibiría un dato incorrecto.

## Fix sugerido (no aplicado por este review)

Antes de serializar la respuesta en `update()`, refrescar la relación cacheada — por ejemplo `instance.refresh_from_db()` seguido de invalidar/recargar `instance.profile` (Django no invalida `refresh_from_db()` las relaciones inversas 1:1 cacheadas por defecto salvo que se listen explícitamente en `fields=[...]`, hay que verificar), o simplemente reasignar `instance.profile = Profile.objects.get(user=instance)` después del `update_or_create`, o evitar el problema devolviendo `UserAdminSerializer(User.objects.select_related('profile').prefetch_related('groups','sucursal_set').get(pk=instance.pk)).data` desde la vista en vez de reusar el `instance` mutado.
