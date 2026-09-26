# REV-2026-09-26-modulo-usuarios-perfiles-grupos-roles-sucursales-04: El plan v1 quedó desactualizado por la fusión con `TASK-login-panel-admin-backend` (nunca se versionó a v2)

**Status:** Resolved — plan versionado a v2 con `## Changelog` (2026-09-26), reconciliando el login/menú reales y agregando los pasos 16-18. Ver `## Review` de `docs/tasks/TASK-modulo-usuarios-perfiles-grupos-roles-sucursales.md`.
**Severity:** Low
**Category:** PLAN
**Related plan:** docs/plans/PLAN-2026-09-25-modulo-usuarios-perfiles-grupos-roles-sucursales.md (v1)
**Suggested owner:** delivery-plan

## Description

Dos de los acceptance criteria del plan v1 ya no son ciertos tal como están escritos, por un cambio externo a este task (el merge con `master`, que ya traía `TASK-login-panel-admin-backend`/PR #46 mergeado):

1. *"Login de staff (`is_staff=True`) obtiene token vía el endpoint nuevo; un `Client` sin `is_staff` recibe 403 ahí"* — el endpoint de login de `panel_admin/` terminó siendo `PanelAdminAuthToken` (`/product/api-panel-admin-token-auth/`), no el `StaffAuthToken`/`admin-token-auth/` que este plan proponía, y **no verifica `is_staff`** (decisión de negocio explícita documentada en `ADR-login-panel-admin-backend-staff-auth-endpoint.md`). Esto ya está anotado como "Actualización" en `ADR-modulo-usuarios-perfiles-grupos-roles-sucursales-api-autenticacion-admin.md`, pero el plan mismo nunca se versionó a v2 para reflejarlo.
2. *"Menú 'Usuarios' visible... con sus 5 submenús"* — por pedido explícito del usuario durante la implementación, el menú final tiene 3 submenús (Credenciales, Grupos, Sucursales) — "Usuarios"/"Perfiles" se consolidaron en "Credenciales" y "Roles" se eliminó (permisos se asignan directo en Grupos). Esto está documentado en la sección "Actualización (post-implementación)" del DDR, pero tampoco se reflejó en el plan.

## Expected behavior

Por convención del propio flujo `delivery-*` (ver `SKILL.md` de `delivery-plan`, sección "Si es una actualización: versionar, no sobrescribir"), cuando la arquitectura o el diseño cambian después de escrito el plan, el plan debería versionarse (v2) con un `## Changelog` explicando el motivo — así el plan sigue siendo una fuente de verdad confiable para comparar contra la implementación.

## Actual behavior

El plan sigue en v1, sin `## Changelog`, con acceptance criteria que ya no describen el comportamiento real y ya documentado en ADR/DDR. No es un defecto de código — es una inconsistencia de trazabilidad entre documentos.

## Evidence

- `docs/plans/PLAN-2026-09-25-modulo-usuarios-perfiles-grupos-roles-sucursales.md` — sin sección `## Changelog`, encabezado sigue en `(v1)`.
- `docs/adr/ADR-modulo-usuarios-perfiles-grupos-roles-sucursales-api-autenticacion-admin.md` — tiene su propia sección "Actualización (2026-09-25, al sincronizar con `master`)" documentando el cambio de endpoint de login.
- `docs/design/DDR-modulo-usuarios-perfiles-grupos-roles-sucursales-listado-y-flujo-usuarios.md` — tiene su propia sección "Actualización (2026-09-25, post-implementación)" documentando la consolidación de menú.

## Nota

No bloquea el comportamiento funcional del sistema (ambos ADR/DDR ya explican el porqué) — es puramente una actualización de `docs/plans/...` a v2 con un `## Changelog` que sume ambos puntos, para que el plan deje de contradecirse con la implementación real.
