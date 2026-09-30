# REV-2026-09-30-estados-proforma-nota-trabajo-nota-venta-01: Django Admin responde 500 al eliminar un pago cerrado (y al fallar el alta de un pago)

**Status:** Open
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-09-30-estados-proforma-nota-trabajo-nota-venta.md (v2.1)
**Suggested owner:** delivery-engineer

## Description
`PagosAdmin.delete_model` (`praxsa_manager/product/admin_config/pagos.py:101`) delega en `Orden_Estado_Business.anular_pago` sin capturar `OrdenEstadoException`. Cuando el pago está cerrado contablemente (`cerrado=True`) el servicio lanza la excepción (comportamiento correcto) pero, en la vista de eliminación individual de Django Admin, nadie la captura y el usuario recibe un HTTP 500. `delete_queryset` (acción masiva) sí captura y muestra el mensaje; `save_model` (línea 97, `registrar_pago_instancia`) tampoco captura, aunque `PagosForm.clean` cubre la mayoría de casos de alta.

## Expected behavior
Plan, Fase 3 / criterio de aceptación 10: "Django Admin y reportes siguen funcionando con las acciones re-cableadas". Un pago cerrado no se puede anular (criterio 5), pero el admin debe informarlo con un mensaje, no con un 500.

## Actual behavior
`POST /admin/product/pago/<id>/delete/` con `post=yes` sobre un pago `cerrado=True` → HTTP 500; el pago sigue existiendo (la regla de negocio sí se respeta, falla la presentación). Ningún test del PR cubre este camino (`test_orden_estado_admin.py` solo prueba `delete_model` con pago abierto).

## Evidence
Prueba desechable (ejecutada y eliminada por el revisor) con superusuario y `Client(raise_request_exception=False)`:

```
Ran 1 test in 0.490s
OK
STATUS delete cerrado: 500 True      # (status HTTP, el pago sigue existiendo)
```

Sugerencia: deshabilitar `has_delete_permission` para pagos cerrados (patrón ya usado en `has_change_permission`) o capturar la excepción en `delete_model`/`save_model` con `message_user` + redirect; agregar el test.
