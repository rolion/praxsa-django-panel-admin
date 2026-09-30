# REV-2026-09-30-dashboard-taller-laminas-01: Valores de KPI y "Ver todos" ilegibles en tema oscuro

**Status:** Resolved (verificado en el re-review sobre 02e9153)
**Severity:** High
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-09-30-dashboard-taller-laminas.md (v1)
**Suggested owner:** delivery-engineer

## Description
En el tema oscuro de la plantilla, las cifras principales de las cuatro tarjetas KPI (Ventas del mes, Proformas activas, Conversión, Instalaciones) y el enlace "Ver todos" del stock crítico quedan prácticamente invisibles: texto negro/gris oscuro sobre fondo azul marino.

## Expected behavior
Criterio de aceptación 10 del plan: "legible en tema claro y oscuro".

## Actual behavior
`.dash-kpi-value` no define color y `a.dash-link` usa `color: inherit` (`panel_admin/src/assets/scss/_dashboard.scss:83-85,149-154`); la tarjeta no aporta color de texto propio en tema oscuro, así que el valor se pinta con `rgb(0,0,0)`. El Engineer declaró que el tema oscuro no se había revisado.

## Evidence
Dashboard real (backend y `ng serve` de la rama, usuario Admin, tema Dark activado desde el panel de ajustes), relación de contraste calculada con `getComputedStyle` sobre `app-main`:

```
1200.00 Bs   1.2  rgb(0, 0, 0)    on rgb(22, 25, 42)
3375.00 Bs   1.2  rgb(0, 0, 0)    on rgb(22, 25, 42)
4            1.2  rgb(0, 0, 0)    on rgb(22, 25, 42)
Ver todos    1.1  rgb(37, 37, 37) on rgb(22, 25, 42)
```
(mínimo WCAG AA: 4.5). Además los textos secundarios (`#8a93a2`/`rgb(100,120,154)`) dan 3.9:1 en oscuro y 4.2:1 en el encabezado "Actualizado…": mejorar junto con lo anterior.
