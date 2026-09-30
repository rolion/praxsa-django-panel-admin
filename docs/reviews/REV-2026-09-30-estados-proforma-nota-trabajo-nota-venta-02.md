# REV-2026-09-30-estados-proforma-nota-trabajo-nota-venta-02: Método huérfano `ProformaAdmin.delete_proforma` apunta a un método de negocio eliminado

**Status:** Closed (corrida 2, 2026-09-30: verificado)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-09-30-estados-proforma-nota-trabajo-nota-venta.md (v2.1)
**Suggested owner:** delivery-engineer

## Description
El PR elimina `Proforma_Business.delete_proforma` (código roto, según el plan), pero `ProformaAdmin.delete_proforma` (`praxsa_manager/product/admin_config/proforma_admin.py:211-217`) sigue llamándolo. No está registrado en `actions`, por lo que hoy no se puede invocar desde la UI; queda como referencia colgante (`AttributeError` si alguien lo re-registra).

## Expected behavior
Criterio 10 / Files affected: no debe quedar código que dependa de lo eliminado; el mismo PR retiró la acción huérfana `create_sales_note` por el mismo motivo.

## Actual behavior
```
$ grep -rn "\.delete_proforma(" praxsa_manager/product --include=*.py | grep -v tests
./admin_config/proforma_admin.py:214:            [self.proforma_business.delete_proforma(user= request.user, proforma=qs) for qs in list(queryset)]
```
Ver `Proforma_Business` en el diff: el método ya no existe.

## Evidence
Salida del grep anterior; la suite completa pasa porque ningún test lo ejerce.
