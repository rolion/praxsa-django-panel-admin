# REV-2026-10-01-favicon-sidebar-icons-01: Logo casi invisible en el sidebar con skin oscura

**Status:** Open
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-01-favicon-sidebar-icons.md (v1)
**Suggested owner:** delivery-engineer

## Description
Con la skin oscura del sidebar (`body.dark-sidebar`, fondo `rgb(22, 25, 42)`), el logo completo y el Rx (ambos azul oscuro sobre transparente) casi no se distinguen del fondo.

## Expected behavior
Acceptance criteria del plan: "Se ve bien en tema claro y oscuro". El paso 5 del plan pedia revisar `skins/_darksidebar.scss:87-93`.

## Actual behavior
No se toco `_darksidebar.scss` y el logo queda con muy bajo contraste en la skin oscura (verificado en vivo agregando `dark dark-sidebar` al `<body>`). La propia nota de Implementacion del TASK admite que el tema oscuro no se reviso.

## Evidence
`getComputedStyle(.sidebar-brand).backgroundColor` = `rgb(22, 25, 42)` con `dark-sidebar`; la captura muestra el logo azul apenas visible sobre ese fondo. Tema claro: OK.
