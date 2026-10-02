# REV-2026-10-02-theme-switcher-relocation-01: Cambio de color primario del skin claro fuera del plan y sin registrar

**Status:** Open
**Severity:** Medium
**Category:** PLAN
**Related plan:** docs/plans/PLAN-2026-10-02-theme-switcher-relocation.md (v1)
**Suggested owner:** delivery-plan

## Description
El commit `44b394c` ("icono de tema oscuro en light y primario #203b84 en el skin claro") toca archivos que el plan no menciona y que no constan en el TASK (`## Implementación`) ni en la sección `## Changes` del PR:
- `panel_admin/src/assets/scss/skins/_white.scss`: `$color-primary` pasa de `#6777ef` a `#203b84`. Esa variable la usan todas las reglas del skin `theme-white` (botones, enlaces, items activos, etc.), es decir, cambia el color primario de **todas** las pantallas de staff en modo claro, no solo el botón de tema.
- `panel_admin/src/assets/scss/skins/_lightsidebar.scss`: dos ocurrencias de `#6777ef` → `#203b84` en `.ml-menu .active`.
- `panel_admin/src/app/layout/header/header.component.sass`: regla `:host-context(.light) .theme-toggle { color: #203b84 }` (esta sí es necesaria para que se lea la luna, pero tampoco figura en el plan).

Los demás skins y overrides siguen con `#6777ef` (`grep` en `src/assets/scss`: `_calendar`, `_contact`, `_layout`, `_sidebar`, `_breadcrumb`, `_button`, `_card`, `_form`, `_black`, etc.), así que el recoloreo es parcial.

## Expected behavior
El plan v1 (`Files/components affected`, `Out of scope`) limita el cambio al botón, el `ThemeService`, el retiro del panel y la doc. Todo cambio fuera de ese alcance debe quedar en el plan (versión nueva con changelog) o en el TASK, con su justificación.

## Actual behavior
Hay un cambio visual global (color primario del tema claro) sin trazabilidad en plan, TASK ni PR. No se puede saber desde los artefactos si fue pedido explícitamente por el usuario ni si la intención es unificar el color primario en el resto de skins/overrides.

## Evidence
```
$ git diff --stat origin/master...HEAD -- panel_admin/src/assets panel_admin/src/app/layout/header/header.component.sass
 panel_admin/src/app/layout/header/header.component.sass |  5 +++++
 panel_admin/src/assets/scss/skins/_lightsidebar.scss    |  4 ++--
 panel_admin/src/assets/scss/skins/_white.scss           |  2 +-

$ grep -n "color-primary" panel_admin/src/assets/scss/skins/_white.scss
4:$color-primary: #203b84;
8:  background-color: $color-primary;
...
```
Verificación en navegador (revisor): en light la luna se ve con `rgb(32, 59, 132)` (legible); el cambio de color en sí no rompe el build, lint ni tests.

## Cómo resolverlo
No requiere cambiar código: registrar el cambio (y quién lo pidió) en el plan/TASK, o revertirlo si no fue solicitado.
