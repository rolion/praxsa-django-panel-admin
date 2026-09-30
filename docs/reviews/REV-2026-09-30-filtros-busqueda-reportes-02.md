# REV-2026-09-30-filtros-busqueda-reportes-02: Las opciones de los selects se recalculan en cada ciclo de detección de cambios

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-09-30-filtros-busqueda-reportes.md (v2)
**Suggested owner:** delivery-engineer

## Description
`sucursalOptions`, `marcaOptions`, `modeloOptions` e `instaladorOptions` son getters que recorren todas las filas (`this.data`) cada vez que Angular evalúa el template. Con el volumen actual es despreciable, pero el costo crece con el número de filas y de ciclos de detección (cada tecla en el buscador, cada evento de la tabla).

## Expected behavior
Las opciones dependen solo de `data` (y `modeloOptions` además de la marca elegida); bastaría calcularlas al cargar las filas y al cambiar la marca.

## Actual behavior
Se recalculan (recorrido + `Set` + ordenamiento) varias veces por ciclo de detección.

## Evidence
- `panel_admin/src/app/ordenes/proformas/proformas-list.component.ts`, `notas-trabajo/notas-trabajo-list.component.ts`, `notas-venta/notas-venta-list.component.ts`: `get sucursalOptions()`, `get marcaOptions()`, `get modeloOptions()`, `get instaladorOptions()`.
- No se midió impacto; se reporta por inspección del diff (sin evidencia de un problema real con los datos actuales: 25 proformas en el entorno local).
