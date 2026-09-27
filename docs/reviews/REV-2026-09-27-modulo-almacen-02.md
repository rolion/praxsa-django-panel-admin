# REV-2026-09-27-modulo-almacen-02: El cambio de `get_inventario_queryset_by_role` (None → queryset vacío) silencia el mensaje "Asigne una sucursal al usuario" en dos admins de Django no contemplados en la investigación

**Status:** Resolved
**Severity:** Medium
**Category:** PLAN
**Related plan:** docs/plans/PLAN-2026-09-26-modulo-almacen.md (v3)
**Suggested owner:** delivery-plan

## Description

El ADR/plan de este task decidió adaptar `Inventario_Business.get_inventario_queryset_by_role` (`praxsa_manager/product/business/inventario.py`) para devolver un queryset vacío (`qs.none()`) en vez de `None` cuando el usuario no tiene sucursal asignada, justificando el cambio en que "sin otros consumidores, verificado con `Grep`" (investigación, `## Módulos y dependencias relacionadas`; también repetido en `## Implementación` del TASK).

Esa verificación fue incompleta: `Grep` de `get_inventario_queryset_by_role` muestra que el método tiene otros dos consumidores reales, ninguno mencionado en la investigación, el plan, ni los ADR:

- `praxsa_manager/product/admin_config/report_storage.py:68` (`ReportStorageAdmin.get_queryset`)
- `praxsa_manager/product/admin_config/report_utilidad.py:51` (`ReportUtilidadAdmin.get_queryset`)

Ambos admins de Django (reportes internos) tienen una rama `if base_qs is None:` que, antes de este cambio, mostraba un mensaje explícito al usuario (`self.message_user(..., 'Asigne una sucursal al usuario', level=messages.ERROR)`) cuando un usuario sin sucursal y sin rol admin entraba a esos reportes. Con `get_inventario_queryset_by_role` devolviendo siempre un queryset (nunca `None`), esa rama queda **inalcanzable de forma permanente** — no hay ninguna forma de que `base_qs is None` sea `True` después de este cambio.

## Expected behavior

El plan v1 (sección `Risks`) sí anticipó el riesgo de tocar `Inventario_Business` y dijo explícitamente: *"Mitigación: correr los tests existentes de ese admin (si los hay) tras el cambio, y preferir envolver la función en la vista nueva (sin modificar su comportamiento actual) si el riesgo de tocarla se confirma real durante la implementación."* — es decir, el propio plan ya dejaba una vía de escape (envolver en vez de modificar) si aparecían más consumidores. Lo esperable era que la investigación hubiera encontrado estos dos admins (con un `Grep` que cubriera todo `praxsa_manager/`, no solo una parte) y que el plan hubiera decidido explícitamente entre adaptar la función (con el impacto en estos dos admins ya evaluado) o envolverla solo en la vista nueva.

## Actual behavior

Confirmado ejecutando (no solo leyendo) `ReportStorageAdmin.get_queryset()` con un usuario `is_staff` sin sucursal asignada y sin grupo `admin`:

```python
from django.test import RequestFactory
from django.contrib.auth.models import User
from product.admin_config.report_storage import ReportStorageAdmin
from product.models import inventario_proxy

u = User.objects.create(username='...', is_staff=True)
request = RequestFactory().get('/admin/'); request.user = u
qs = ReportStorageAdmin(model=inventario_proxy, admin_site=None).get_queryset(request)
# qs es un QuerySet vacío (count() == 0), no una excepción --
# pero la rama `if base_qs is None` (que antes mostraba el mensaje de error)
# nunca se ejecuta: `message_user` no se invoca.
```

No hay ningún crash ni resultado incorrecto (el reporte sigue mostrando 0 filas, que es funcionalmente equivalente al fallback anterior `qs.filter(sucursal=-1)`). El único efecto es que el admin que entra a "Reporte Inventario" o "Reporte Utilidades" sin sucursal asignada ya no ve el mensaje que le explicaba por qué no ve datos — queda con un reporte vacío sin explicación. Es una regresión de UX silenciosa en código preexistente no tocado por este PR, causada por un cambio de contrato en una función que sí se tocó.

## Evidence

```
$ grep -rn "get_inventario_queryset_by_role" praxsa_manager
praxsa_manager\product\business\inventario.py:14: def get_inventario_queryset_by_role...
praxsa_manager\product\custom_views\almacen_admin.py:137: queryset = business.get_inventario_queryset_by_role(...)
praxsa_manager\product\tests\test_sucursal_scope_admin.py: (4 llamadas, todas con sucursal asignada o rol admin)
praxsa_manager\product\admin_config\report_storage.py:68: base_qs = self.inventario_business.get_inventario_queryset_by_role(...)
praxsa_manager\product\admin_config\report_utilidad.py:51: base_qs = self.inventario_business.get_inventario_queryset_by_role(...)
```

Ejecución directa (ver arriba): `qs.count() == 0`, sin excepción, pero la rama `if base_qs is None` en ambos admins queda confirmada como código muerto tras este cambio — no hay ningún test en el repo (incluido `test_sucursal_scope_admin.py`, que sí testea estos dos admins pero solo con usuarios que tienen sucursal) que ejercite el caso "usuario sin sucursal" contra `ReportStorageAdmin`/`ReportUtilidadAdmin`, así que la suite completa (189/189) pasa sin detectar esta regresión.

## Suggested resolution (no aplicada, a decidir por delivery-plan)

Dos caminos razonables, ninguno implementado en esta revisión:
1. Actualizar `ReportStorageAdmin.get_queryset`/`ReportUtilidadAdmin.get_queryset` para chequear `not base_qs.exists()` (o simplemente quitar la rama muerta y aceptar que el reporte quede vacío sin mensaje, si el negocio decide que no vale la pena mantenerlo).
2. Revertir el cambio de contrato de `get_inventario_queryset_by_role` y en su lugar envolver la lógica de "sin sucursal → queryset vacío" únicamente dentro de `InventarioListView` (la opción que el propio plan v1 ya había dejado como alternativa preferida si aparecían más consumidores).

## Resolution (verificado en corrida 2, 2026-09-27)

El usuario eligió explícitamente la opción 1 (mantener el contrato de `get_inventario_queryset_by_role`, actualizar los 2 admins). El plan v3 sugería literalmente `if not base_qs.exists():`, pero `delivery-engineer` detectó que esa condición es imprecisa — confunde "sin sucursal asignada" con "sucursal asignada pero reporte legítimamente vacío" (mostraría el mensaje de error a un admin cuya sucursal simplemente no tiene inventario) — y en su lugar implementó `User_Helper.has_assigned_sucursal`, que replica exactamente la condición de sucursal que ya usa `get_inventario_queryset_by_role`. Verificado de forma independiente (no solo leyendo el test): ejecutando `ReportStorageAdmin.get_queryset()` con un usuario sin sucursal, el mensaje "Asigne una sucursal al usuario" aparece; con un usuario que sí tiene sucursal asignada pero cuyo inventario está vacío, el queryset es vacío y el mensaje **no** aparece — confirma que el fix es más preciso que la sugerencia literal del plan, sin introducir el falso positivo que esa sugerencia hubiera causado. Los 3 tests nuevos (`AdminReportsSinSucursalMessageTest`) pasan.
