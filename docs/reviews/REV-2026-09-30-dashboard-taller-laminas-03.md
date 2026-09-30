# REV-2026-09-30-dashboard-taller-laminas-03: Textos secundarios `.text-muted` con contraste 2.5:1 en tema claro

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-09-30-dashboard-taller-laminas.md (v1)
**Suggested owner:** delivery-engineer

## Description
El markup nuevo del dashboard usa `.text-muted` para información real (subtítulos de los KPI "N sin cerrar" / "X de Y proformas del mes", "vs. … mes anterior", placa y fecha de proformas, "Actualizado …"). En tema claro la plantilla pinta ese color `rgb(152,166,173)`, que no llega al mínimo AA. La corrección de REV-01 cubrió el tema oscuro (`body.dark .dashboard .text-muted`) y el gris propio `.dash-*`, pero no `.text-muted` en tema claro. El Engineer ya lo anotó como "observación sin corregir".

## Expected behavior
Criterio de aceptación 10 del plan: "legible en tema claro y oscuro" (mínimo WCAG AA 4.5:1 para texto normal).

## Actual behavior
`.text-muted` dentro de `.dashboard` en tema claro: 2.5:1 sobre tarjeta blanca y 2.3:1 sobre el fondo de página. Es un problema de la plantilla, pero el dashboard nuevo lo usa para datos informativos. No bloquea el uso (los valores principales sí son legibles).

## Evidence
Medición con `getComputedStyle` y luminancia WCAG, sobre el CSS compilado real (`ng build`, `styles-*.css`) y el markup del dashboard en una página de prueba (no la app con login), body sin clase `dark`:

```
2.3  Actualizado hoy          rgb(152, 166, 173) on rgb(246, 246, 246)
2.5  vs. 0 mes anterior       rgb(152, 166, 173) on rgb(255, 255, 255)
2.5  2 de 5                   rgb(152, 166, 173) on rgb(255, 255, 255)
2.5  Placa                    rgb(152, 166, 173) on rgb(255, 255, 255)
```
Sugerencia: en `_dashboard.scss` fijar `.dashboard .text-muted { color: #5f6b7d; }` (5.4:1 sobre blanco, el mismo gris ya usado en `.dash-kpi-label`), manteniendo el bloque `body.dark`.
