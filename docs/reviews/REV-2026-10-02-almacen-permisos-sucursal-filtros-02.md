# REV-2026-10-02-almacen-permisos-sucursal-filtros-02: Rama sin `request` de `InventarioCreateSerializer.validate_sucursal` sin test

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-02-almacen-permisos-sucursal-filtros.md (v1)
**Suggested owner:** delivery-engineer

## Description
`validate_sucursal` rechaza con `ValidationError` cuando el contexto no trae `request` (`serializer/almacen_serializer.py`, rama añadida por este cambio). Ningún test de `tests/test_inventario_alcance_sucursal.py` ejercita esa rama (todos entran por la vista, que siempre pasa `request`).

## Expected behavior
Cada rama nueva en `serializer/` tiene un test que la ejercite (criterio de cobertura del Quality Gate; `coverage.py` no está instalado, verificación manual).

## Actual behavior
Rama defensiva sin cobertura. Riesgo bajo: la única vista que usa el serializer pasa el contexto.

## Evidence
`grep -n "context\|validate_sucursal" praxsa_manager/product/tests/test_inventario_alcance_sucursal.py` no muestra instanciación directa del serializer sin contexto. No bloquea el PR.
