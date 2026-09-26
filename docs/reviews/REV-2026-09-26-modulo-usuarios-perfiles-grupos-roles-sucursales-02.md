# REV-2026-09-26-modulo-usuarios-perfiles-grupos-roles-sucursales-02: `UserDetailView` (GET/PATCH de un usuario existente) no tiene ningún test

**Status:** Resolved — `UserDetailViewTest` (GET, PATCH con verificación de datos, PATCH sin permiso) agregado y verificado en la segunda corrida de `delivery-review` (2026-09-26) sobre el PR #47. Ver `## Review` de `docs/tasks/TASK-modulo-usuarios-perfiles-grupos-roles-sucursales.md`.
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-09-25-modulo-usuarios-perfiles-grupos-roles-sucursales.md (v1)
**Suggested owner:** delivery-engineer

## Description

`praxsa_manager/product/tests/test_user_admin_module.py` cubre creación (`UserCreationTest`), listado (`UserListTest`), activar/desactivar (`UserToggleActiveTest`) y cambio de contraseña (`UserSetPasswordTest`), pero no tiene ninguna clase de test para `UserDetailView` — ni el `GET` (detalle de un usuario) ni el `PATCH` (edición de perfil/grupos/sucursales), que es exactamente el endpoint que consume `UserEditComponent` del frontend.

`docs/CLAUDE.md`: "Todo cambio de lógica de negocio lleva su test" — `UserAdminSerializer.update()` tiene lógica real (perfil anidado, `groups.set()`, `sucursal_set.set()`, todo en una transacción) sin ningún test que la ejercite.

## Expected behavior

El plan (paso 7, sección de tests) lista casos para creación, login, permisos, activar/desactivar y cambio de contraseña, pero **no incluye explícitamente** un caso de "editar los datos de un usuario existente" — es una omisión en la enumeración del plan que se propagó a la implementación (ningún test lo cubre porque el plan nunca lo pidió por su nombre).

## Actual behavior

`Grep` de `PATCH.*users/<pk>|UserDetailView` en `product/tests/test_user_admin_module.py` no devuelve resultados — cero cobertura. Esta ausencia es la razón por la que el bug documentado en `REV-2026-09-26-modulo-usuarios-perfiles-grupos-roles-sucursales-01` (respuesta con `phone_number` desactualizado tras un PATCH) llegó hasta esta revisión sin detectarse antes.

## Evidence

```
$ grep -n "UserDetailView\|users/{.*}/'.*patch\|\.patch(" product/tests/test_user_admin_module.py
(sin resultados)
```

## Nota

Agregar esta cobertura debería incluir, como mínimo: PATCH feliz (verificando que la respuesta refleje los datos nuevos, lo que habría atrapado REV-01), GET de detalle, y el caso de permisos (PATCH sin `change_user` → 403, ya cubierto indirectamente por el patrón usado en `UserToggleActiveTest`/`UserSetPasswordTest` pero no replicado aquí).
