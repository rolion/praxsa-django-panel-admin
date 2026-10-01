# REV-2026-10-01-favicon-sidebar-icons-02: Logo JPG del header con fondo blanco visible en tema oscuro

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-01-favicon-sidebar-icons.md (v1)
**Suggested owner:** delivery-engineer

## Description
`praxsa-3m-header-logo.jpg` viene de un JPG sin transparencia (fondo blanco). Con la clase `dark` en el body de `/calculadora`, el logo se ve como un rectangulo blanco sobre el fondo oscuro de la pagina.

## Expected behavior
Criterio del plan: "Se ve bien en tema claro y oscuro".

## Actual behavior
En tema claro y en 375px el logo se ve bien (sin desborde, `scrollWidth` 375). En oscuro queda un recuadro blanco; el calculo de `.main-navbar` dio `rgb(255, 255, 255)` incluso con `dark`, asi que la severidad es baja y no hay evidencia de que el header oscuro se use realmente en esta pantalla.

## Evidence
Captura en vivo con `document.body.classList.add('dark')` en `/calculadora`: logo con recuadro blanco. `src` = `assets/images/praxsa-3m-header-logo.jpg`, natural 700x81.
