# REV-2026-09-23-001: Archivo `business/orden_trabajo.py` tocado fuera de lo declarado en el plan

**Status:** Open
**Severity:** Low
**Category:** PLAN
**Related plan:** docs/plans/PLAN-2026-09-23-proforma-status-field.md (v1)
**Suggested owner:** delivery-plan

## Description
El plan (sección "Files/components affected") declara exactamente estos archivos backend a tocar: `models.py`, `helper/proforma.py`, `business/proforma.py`, `business/pago.py`, `migrations/0106_proforma_header_status.py`, `tests/test_proforma_status_field.py`. El diff real del PR también modifica `praxsa_manager/product/business/orden_trabajo.py` (agrega una llamada a `Proforma_Business().refresh_status()` dentro de `delete_work_note`, con un import diferido para evitar un ciclo con `proforma.py`).

## Expected behavior
Según el criterio de "Alcance" de esta revisión, cualquier archivo tocado fuera de lo que el plan declaró es un hallazgo a registrar, incluso si el cambio en sí es razonable — el plan debería reflejar el alcance real antes de mergear, o quedar versionado a v2 con el motivo.

## Actual behavior
`delivery-engineer` documentó la razón en detalle en `## Implementación` de TASK-009 (evidencia: `Orden_Trabajo_Business.delete_work_note` es el único camino existente que remueve la relación `proforma↔nota_trabajo`, y sin sincronizar `status` ahí el campo quedaría desactualizado tras borrar una nota de trabajo — verificado independientemente en esta revisión, ver `Orden_Trabajo_Business.delete_work_note` en `business/orden_trabajo.py:61-91` y el test `test_eliminar_nota_trabajo_revierte_status_a_proforma`, que pasa). El cambio es correcto, necesario para el criterio de aceptación "`status` coincide con `get_estado()` en todo momento del ciclo", y de bajo riesgo (mismo mecanismo ya diseñado, extendido a un sitio adicional). No se marcó `PLAN_UPDATE_REQUIRED`, razonablemente dado que no cambia arquitectura ni nivel de riesgo — pero el plan v1 en disco sigue sin reflejar este archivo ni esta quinta transición.

## Evidence
```
$ git diff origin/master...HEAD --stat
 praxsa_manager/product/business/orden_trabajo.py   |   8 ++
 ...

$ git diff origin/master...HEAD -- praxsa_manager/product/business/orden_trabajo.py
+                from .proforma import Proforma_Business
+                proforma.refresh_from_db()
+                Proforma_Business().refresh_status(proforma)
```
No bloquea: no es un defecto funcional, es una discrepancia documental entre el plan v1 y el diff real. Sugerido para `delivery-plan`: versionar el plan a v2 agregando este archivo/transición al alcance declarado (changelog), para que el documento quede consistente con lo efectivamente implementado y aprobado.
