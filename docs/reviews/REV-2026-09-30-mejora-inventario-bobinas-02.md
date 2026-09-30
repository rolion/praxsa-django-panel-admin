# REV-2026-09-30-mejora-inventario-bobinas-02: Falta el test planeado de PDF y reportes con una línea repartida en varios lotes

**Status:** Closed
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-09-30-mejora-inventario-bobinas.md (v1)
**Suggested owner:** delivery-engineer

## Description
La "Test strategy" del plan incluye: "reportes (`report_storage`, `report_utilidad`) sólo se comprueba que siguen ejecutando sobre datos con reparto multi-fila", y el criterio de aceptación 10 exige que "PDF de proforma y reportes siguen funcionando con datos multi-fila". `tests/test_inventario_asignacion.py` no incluye ningún caso de PDF ni de reportes.

## Expected behavior
Un test que apruebe una proforma repartida en dos lotes y compruebe que la hoja de trabajo en PDF y los reportes de almacén y utilidades se generan sin error.

## Actual behavior
El comportamiento **sí es correcto hoy**: lo verificó esta revisión con un script temporal (no commiteado, eliminado), pero no queda ninguna protección de regresión.

## Evidence
Línea de 50 m repartida en L100 (30 m) y L200 (20 m), aprobada con el servicio:

```
PDF bytes: 25553 | lotes en detalle (FK): ['L100']
UTILIDAD filas: [('L100', '6000.0000')]
STORAGE filas: [('L100', '0.00', '30.00')]
STORAGE agregado: [{... 'total_to_install': Decimal('10.00'), 'total_installed': Decimal('50.00'), ...}]
Ran 2 tests in 0.717s OK
```

Sin errores; los saldos agregados son correctos (10 m disponibles, 50 m instalados). Se observa además, como ya estaba diferido por decisión del usuario, que PDF y reporte de utilidades solo muestran el primer lote (L100). La lista de filas del reporte de almacén está deduplicada por diseño (`distinct` por sucursal, lámina y ancho).


## Resolución (revisión corrida 2, 2026-09-30)
Corregido en b667e50 (`PdfYReportesConRepartoTest`: PDF de la hoja de trabajo, reporte de almacén y de utilidades con una línea repartida en dos lotes). Verificado en la corrida 2: los tests pasan dentro de la suite completa (403 OK).
