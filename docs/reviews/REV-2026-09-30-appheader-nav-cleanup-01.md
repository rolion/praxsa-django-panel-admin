# REV-2026-09-30-appheader-nav-cleanup-01: Indentación rota en header.component.html tras el recorte

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-09-30-appheader-nav-cleanup.md (v1)
**Suggested owner:** delivery-engineer

## Description
Al eliminar los bloques, `header.component.html` quedó con indentación inconsistente: `</ul>`, `</div>` y `<ul class="navbar-nav navbar-right">` en columna 0 o con sangría que no refleja el anidamiento, y el `<li ngbDropdown>` del usuario sin sangría.

## Expected behavior
Plantilla legible con sangría acorde al árbol DOM (clean code en código modificado).

## Actual behavior
Funciona igual (verificado en navegador), pero la estructura es difícil de leer. La plantilla original ya tenía indentación irregular; el cambio no la empeora funcionalmente, solo la deja más evidente.

## Evidence
`git diff origin/master...HEAD -- panel_admin/src/app/layout/header/header.component.html` muestra `  </ul>` / `</div>` / `<ul class="navbar-nav navbar-right">` con sangría incorrecta. No bloquea el PR; se puede corregir en publicación o en un commit aparte.
