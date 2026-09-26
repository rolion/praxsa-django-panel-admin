# REV-2026-09-26-modulo-usuarios-perfiles-grupos-roles-sucursales-03: `ng lint` falla en dos specs nuevos (`@typescript-eslint/no-explicit-any`)

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-09-25-modulo-usuarios-perfiles-grupos-roles-sucursales.md (v1)
**Suggested owner:** delivery-engineer

## Description

`npx ng lint` (configurado en `panel_admin/angular.json` vía `@angular-eslint/builder:lint`) falla con 2 errores, ambos en archivos nuevos de este task:

- `panel_admin/src/app/core/guard/auth.guard.spec.ts:31` — `(authService as any).currentUserSubject.next(...)`.
- `panel_admin/src/app/users/list/users-list.component.spec.ts:69` — `spyOn(Swal, 'fire').and.returnValue(Promise.resolve({ isConfirmed: true } as any))`.

## Expected behavior

El proyecto tiene lint configurado y, según se puede inferir de la regla activa (`@typescript-eslint/no-explicit-any` como `error`, no `warning`), se espera que el código nuevo no la viole. Ninguna otra verificación del plan menciona lint explícitamente, pero es una verificación técnica estándar que `delivery-review` corre igual.

## Actual behavior

```
$ npx ng lint
Linting "oreva"...

E:\...\panel_admin\src\app\core\guard\auth.guard.spec.ts
  31:21  error  Unexpected any. Specify a different type  @typescript-eslint/no-explicit-any

E:\...\panel_admin\src\app\users\list\users-list.component.spec.ts
  69:82  error  Unexpected any. Specify a different type  @typescript-eslint/no-explicit-any

✖ 2 problems (2 errors, 0 warnings)
```

## Evidence

Ver salida completa arriba — es la salida real y completa de `npx ng lint` desde `panel_admin/`, sin recortar.

## Nota

Ambos son solo de test (no código de producción) y de bajo riesgo real, pero son errores de lint reproducibles y triviales de resolver: el primero puede tiparse como `AuthService & { currentUserSubject: BehaviorSubject<User> }` o exponer un setter de test; el segundo puede tipar el resultado de `Swal.fire` según el tipo real que expone `sweetalert2` (`SweetAlertResult<unknown>`) en vez de `as any`.
