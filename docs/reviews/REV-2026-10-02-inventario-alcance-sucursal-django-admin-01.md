# REV-2026-10-02-inventario-alcance-sucursal-django-admin-01: Botón "Crear" del listado de proformas sigue visible sin sucursales activas

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-02-inventario-alcance-sucursal-django-admin.md (v1)
**Suggested owner:** delivery-engineer

## Description
El DDR pide ocultar el botón de alta cuando el usuario no tiene ninguna sucursal activa. En Inventario se cumple; en el listado de proformas el botón "Crear" se deja visible (desvío 4 declarado en la sección Implementación del TASK, motivo: habría exigido una petición extra por listado).

## Expected behavior
Plan, paso 12-13 y DDR: "altas solo con sucursales activas ... botón de alta oculto si no hay ninguna". Criterio de aceptación 3: "las altas no la ofrecen".

## Actual behavior
Un usuario cuyas sucursales asignadas están todas inactivas ve "Crear" en proformas; el formulario avisa y no deja crear. El servidor es la barrera (alta en sucursal inactiva responde 400, cubierto por tests), así que no hay riesgo de datos; es solo coherencia de UI. No bloquea.

## Evidence
- Desvío 4 en `docs/tasks/TASK-inventario-alcance-sucursal-django-admin.md` (Implementación).
- Verificado en el código: `panel_admin/src/app/ordenes/proformas/proformas-list.component.html` muestra el botón "Nueva proforma" (línea 94) solo con `canCreate` (permiso), sin condición de sucursales activas.
- `manage.py test product`: Ran 685 tests ... OK (el 400 de alta en sucursal inactiva está cubierto).
