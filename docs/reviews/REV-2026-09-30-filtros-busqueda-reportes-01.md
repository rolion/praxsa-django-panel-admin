# REV-2026-09-30-filtros-busqueda-reportes-01: Las opciones de sucursal salen de las filas, no de `listSucursales()` como dicen el DDR y el plan

**Status:** Open
**Severity:** Low
**Category:** PLAN
**Related plan:** docs/plans/PLAN-2026-09-30-filtros-busqueda-reportes.md (v2)
**Suggested owner:** delivery-plan

## Description
El DDR (`docs/design/DDR-filtros-busqueda-reportes-filtros-listados-ordenes.md`, "Comportamiento de los controles") y el plan v2 (Fase 2, "Current behavior" y "Proposed solution" punto 3) indican que las opciones del filtro de Sucursal se cargan con `OrdenesService.listSucursales()`. La implementación las deriva de las filas ya cargadas (`opcionesPorId(this.data, ...)`), decisión documentada solo en `## Implementación` del TASK.

## Expected behavior
Plan y DDR coherentes con el código: o bien las opciones vienen de `listSucursales()`, o bien el DDR/plan documentan que vienen de las filas.

## Actual behavior
Código y documentos divergen. El efecto para el usuario es aceptable (el backend ya acota las filas a sus sucursales; solo no aparece una sucursal propia que no tenga filas), por eso es Low y no bloquea.

## Evidence
- `panel_admin/src/app/ordenes/proformas/proformas-list.component.ts`: `get sucursalOptions() { return opcionesPorId(this.data, (r) => r.sucursal, (r) => r.sucursal_name); }`
- `panel_admin/src/app/ordenes/notas-trabajo/notas-trabajo-list.component.ts` y `notas-venta-list.component.ts`: mismo patrón con `sucursal_id`/`sucursal_name`.
- Ninguna de las tres listas llama a `listSucursales()` para poblar el filtro (solo para el aviso de "sin sucursal").
