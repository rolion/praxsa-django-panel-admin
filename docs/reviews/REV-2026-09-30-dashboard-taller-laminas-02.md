# REV-2026-09-30-dashboard-taller-laminas-02: Botón "Convertir a venta" con contraste insuficiente

**Status:** Resolved (verificado en el re-review sobre 02e9153)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-09-30-dashboard-taller-laminas.md (v1)
**Suggested owner:** delivery-engineer

## Description
El botón usa `btn btn-sm btn-success` (desvío declarado frente a `btn-tbl-activate`); en la plantilla ese verde es claro y el texto blanco queda ilegible para algunos usuarios.

## Expected behavior
Acción principal del panel de proformas legible (criterio de accesibilidad del DDR / AC 10).

## Actual behavior
Texto blanco `rgb(255,255,255)` sobre `rgb(84,202,104)`: contraste 2.1:1 (mínimo 4.5), en tema claro y oscuro.

## Evidence
Medición con `getComputedStyle` sobre el dashboard real: `Convertir a venta 2.1 rgb(255, 255, 255) on rgb(84, 202, 104)`.
