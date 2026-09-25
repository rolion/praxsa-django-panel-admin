# REV-2026-09-23-002: Backfill de la migración 0106 no usa `select_related`, contradice lo planificado

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-09-23-proforma-status-field.md (v1)
**Suggested owner:** delivery-engineer

## Description
El plan, en "Architecture considerations" (sección Rendimiento), especifica explícitamente: *"el backfill recorre todas las Proforma_Header existentes una vez, con select_related/prefetch sobre la cadena nota_trabajo__nota_venta__pago para evitar N+1"*. La implementación real de `backfill_status` en la migración `0106_proforma_header_status.py` no usa `select_related` ni `prefetch_related`: itera `Proforma_Header.objects.all().iterator()` y accede a `nota_trabajo`, `nota_trabajo.nota_venta`, `nota_trabajo.nota_venta.pago` con `hasattr()` directo, lo que dispara hasta 3 queries adicionales por fila en el peor caso (proformas ya finalizadas).

## Expected behavior
Según el plan, el backfill debería precargar la cadena de relaciones con `select_related('nota_trabajo', 'nota_trabajo__nota_venta', 'nota_trabajo__nota_venta__pago')` (válido en Django para relaciones O2O reversas) antes de iterar, para evitar el patrón N+1 sobre la tabla completa.

## Actual behavior
```python
Proforma_Header = apps.get_model('product', 'Proforma_Header')
for proforma in Proforma_Header.objects.all().iterator():
    try:
        status = 'proforma'
        if hasattr(proforma, 'nota_trabajo'):
            ...
```
(`praxsa_manager/product/migrations/0106_proforma_header_status.py:15-26`) — sin `select_related` antes de `.iterator()`.

## Evidence
Verificado leyendo el archivo real del diff (no solo el plan): confirmado que no hay ningún `select_related`/`prefetch_related` en la migración. Funcionalmente no falla — se re-verificó el backfill dos veces contra la base de datos de desarrollo real (rollback + reaplicación de la migración) con 0 discrepancias sobre 25 filas reales:
```
total 25 mismatches 0
[{'status': 'finalizado', 'n': 11}, {'status': 'nota_trabajo', 'n': 3}, {'status': 'por_cobrar', 'n': 1}, {'status': 'proforma', 'n': 10}]
```
Dado que es una migración de una sola vez (no un endpoint ni un camino ejecutado repetidamente) y el propio plan estima "a lo sumo unos pocos miles de filas" para el tamaño actual del negocio, el impacto real es bajo (algunos miles de queries adicionales en el peor caso, ejecutados una sola vez al desplegar). Se registra como severidad Low, no bloqueante, pero es una desviación real y verificable de lo que el plan pidió explícitamente para esta migración.
