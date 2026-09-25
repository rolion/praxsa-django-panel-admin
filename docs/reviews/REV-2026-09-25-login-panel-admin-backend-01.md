# REV-2026-09-25-login-panel-admin-backend-01: El plan v1 no se versionó tras cambios post-implementación pedidos por el usuario

**Status:** Resolved
**Severity:** Low
**Category:** PLAN
**Related plan:** docs/plans/PLAN-2026-09-25-login-panel-admin-backend.md (v2)
**Suggested owner:** delivery-plan

## Resolution

Resuelto en `PLAN-2026-09-25-login-panel-admin-backend.md` v2 (2026-09-25), a pedido explícito del usuario ("actualiza el REV-01"). Se actualizaron `Expected behavior`, los pasos 9/10/12/14 de `Proposed solution`, `Acceptance criteria`, `Risks` y `Out of scope` para reflejar la implementación real (assets reales en vez de SVG, eliminación del bloque de identidad del sidebar, nombre de usuario en el nav izquierdo del header), con un `## Changelog` documentando el motivo del cambio. No hubo cambio de código — solo el documento del plan quedó desincronizado, ahora corregido.

## Description

Tras la primera implementación, el usuario pidió en el chat varios ajustes que cambian lo que describen el `Proposed solution` y `Acceptance criteria` del plan v1: reemplazar los dos assets SVG generados por imágenes reales que él mismo proveyó, eliminar el bloque de identidad del propio sidebar ("Emily Smith"), y mover el nombre del usuario del dropdown derecho del header al nav izquierdo (dejando el dropdown derecho con un ícono genérico en vez de logo+nombre). Todos estos cambios se implementaron y se documentaron como una sección `## Actualización` en el DDR y como "Ajuste post-implementación" en el TASK, pero **el documento del plan (`PLAN-2026-09-25-login-panel-admin-backend.md`) se quedó en v1** sin un `## Changelog` ni una v2 que reflejen el cambio de solución/acceptance criteria.

## Expected behavior

Según el flujo del equipo (`delivery-plan`, sección 7: "Si es una actualización... versionar, no sobrescribir"), cualquier cambio que modifique la solución propuesta o los acceptance criteria de un plan ya escrito debería pasar por una actualización versionada del plan (v2 + `## Changelog`), incluso cuando el cambio lo pide el usuario directamente en el chat durante `delivery-engineer` en vez de pasar formalmente por `/delivery-plan`.

## Actual behavior

El plan sigue en v1 y describe una solución que ya no coincide con lo que está desplegado:
- `PLAN...md:63` dice "Reemplazar `assets/images/login.jpg` por el asset de auto generado... por el logo generado + wordmark 'PRAXSA'" — la implementación final usa `praxsa-login-hero.png`/`praxsa-admin-logo.png`, imágenes reales provistas por el usuario, no generadas.
- `PLAN...md:66` dice "reemplazar el trigger... por el logo generado (pequeño) apilado sobre el nombre del usuario" — la implementación final muestra el nombre en el nav izquierdo del header y un ícono genérico (`i-feather name="user"`) en el dropdown derecho, sin logo ahí.
- `PLAN...md:131` (acceptance criteria) sigue afirmando literalmente "El menú de usuario del header muestra el logo de PRAXSA sobre el nombre real del usuario autenticado" — esto ya no es cierto tal cual está escrito.

Quien lea solo el plan (sin revisar el TASK/DDR completos) se lleva una imagen incorrecta de qué se implementó finalmente.

## Evidence

Diff real del PR (`git diff origin/master...HEAD`) confirma la implementación final descrita arriba (`header.component.html`, `sidebar.component.html`, `signin.component.html`, y los dos PNG nuevos `praxsa-admin-logo.png`/`praxsa-login-hero.png` reemplazando los SVG). El TASK (`## Implementación`, sección "Ajuste post-implementación") y el DDR (sección `## Actualización`) sí documentan el cambio real, pero el `PLAN-2026-09-25-login-panel-admin-backend.md` no tiene ninguna sección `## Changelog` ni un encabezado `(v2)`.

No es un defecto funcional — verificado en el navegador que el comportamiento final es el que el usuario pidió explícitamente y confirmó como correcto. Es un hallazgo de disciplina de proceso/documentación: el plan como artefacto queda desactualizado respecto a lo entregado.
