# REV-2026-09-30-mejora-inventario-bobinas-01: La devolución al inventario no es segura ante llamadas concurrentes (`delete_work_note` no bloquea)

**Status:** Open
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-09-30-mejora-inventario-bobinas.md (v1)
**Suggested owner:** delivery-engineer

## Description
`Inventario_Business.return_detail_to_inventory` (`business/inventario.py`) calcula el neto a devolver (egresos menos devoluciones) **antes** de bloquear las filas de inventario, y no bloquea el detalle ni la proforma. Dos ejecuciones simultáneas sobre el mismo detalle leen el mismo neto y devuelven los metros dos veces.

Quien protege hoy esa concurrencia es el bloqueo de la proforma que toma `Orden_Estado_Business._bloquear` en `_cancelar_orden`. Pero `Orden_Trabajo_Business.delete_work_note` (`business/orden_trabajo.py:76-117`, borrado físico desde el Django Admin) **no toma ese bloqueo**: solo usa `transaction.atomic()`. Un doble clic o dos usuarios ejecutando "eliminar nota de trabajo" a la vez, o eliminar mientras otro usuario anula por la API, sobre-acredita el inventario.

## Expected behavior
ADR-mejora-inventario-bobinas-asignacion-y-movimientos, decisión 2: "toda operación de descuento o devolución toma primero la proforma y luego las filas en el mismo orden". Criterio de aceptación 2 del plan: la devolución es exacta e idempotente ("sin devolver dos veces").

## Actual behavior
La devolución solo es idempotente de forma secuencial (cubierto por `test_devolver_dos_veces_es_idempotente`). En concurrencia devuelve el doble.

## Evidence
Prueba temporal (no commiteada, ya eliminada): fila con 30 m, un detalle que descontó 10 m (saldo 20), y dos hilos llamando a `return_detail_to_inventory(detalle)` a la vez dentro de `transaction.atomic()`. Repetido 15 veces:

```
ANOMALIAS (saldo final != 30.00): ['40.00', '40.00', '40.00', '40.00', '40.00', '40.00', '40.00', '40.00', '40.00',
'40.00', '40.00', '40.00', '40.00', '40.00', '40.00'] de 15
```

Saldo esperado 30.00, saldo obtenido 40.00 en 15 de 15 intentos.

## Fix sugerido (para el owner, no aplicado por la revisión)
Que `return_detail_to_inventory` (o `delete_work_note`) tome primero el bloqueo de la proforma/detalle antes de calcular el neto, y agregar un test de concurrencia de doble devolución.
