# PLAN-2026-09-21-filtrado-sucursal-pagos-reportes-admin (v2)

**Task:** TASK-002
**ADRs relacionados:** [ADR-002](../adr/ADR-002-filtrado-sucursal-pagos-reportes-admin.md)

## Objective

Que `PagosAdmin`, `ReportDailySellAdmin`, `ReportStorageAdmin`, `ReportUtilidadAdmin` y `ReportNotaTrabajoAdmin` dejen de mostrar datos financieros de todas las sucursales a cualquier staff, y en su lugar respeten la sucursal del usuario — salvo el grupo `Admin`, que sigue viendo todo. Cierra el ítem #10 del backlog (`SEC-06`).

## Context

Investigación completa en [TASK-002](../tasks/TASK-002.md#investigación). Decisión arquitectónica en [ADR-002](../adr/ADR-002-filtrado-sucursal-pagos-reportes-admin.md): centralizar en `User_Helper` qué roles ven todas las sucursales (solo `Admin`, corregido el 2026-09-22 — ver Changelog), y agregar un método `get_*_queryset_by_role(user, qs)` por cada `business/*.py` relevante, siguiendo la convención ya usada por `Proforma_Business`.

Confirmado explícitamente fuera de alcance (no tocar en este plan): el chequeo inline de `'Admin'` en `Proforma_Business.get_proforma_queryset_by_role`, el bug preexistente de "Admin sin sucursal ve listas vacías" en `NotaVentaAdmin`/`NotaTrabajoAdmin`, y SEC-07 (mutación de estado compartido en `changelist_view`).

## Current behavior

- `PagosAdmin.get_queryset` — [admin_config/pagos.py:131-138](../../praxsa_manager/product/admin_config/pagos.py) — sin filtro por sucursal.
- `ReportDailySellAdmin.get_queryset` — [admin_config/report_daily_sell.py:136-140](../../praxsa_manager/product/admin_config/report_daily_sell.py) — sin filtro.
- `ReportStorageAdmin.get_queryset` — [admin_config/report_storage.py:65-74](../../praxsa_manager/product/admin_config/report_storage.py) — sin filtro; además calcula `self.aggregated_result` (atributo de clase) en una query separada, también sin filtro.
- `ReportUtilidadAdmin.get_queryset` — [admin_config/report_utilidad.py:49-60](../../praxsa_manager/product/admin_config/report_utilidad.py) — sin filtro.
- `Orden_Trabajo_Business.get_finish_nota_queryset` — [business/orden_trabajo.py:29-43](../../praxsa_manager/product/business/orden_trabajo.py) — filtro de sucursal comentado, método no recibe `user`; consumido por `ReportNotaTrabajoAdmin.get_queryset` — [admin_config/report_nota_trabajo.py:106-111](../../praxsa_manager/product/admin_config/report_nota_trabajo.py).
- `User_Helper` — [helper/user.py](../../praxsa_manager/product/helper/user.py) — conoce los roles `admin`, `instalador`, `supervisor`; no conoce `caja`.

## Expected behavior

- Un usuario del grupo `Admin` ve, en los 5 admins listados arriba, los registros de **todas** las sucursales (igual que hoy).
- Un usuario de cualquier otro grupo (`Caja` incluido) o sin grupo ve solo los registros de la sucursal a la que pertenece vía `Sucursal.empleado`.
- Un usuario sin `Admin` y sin sucursal asignada ve una lista vacía, con el mismo mensaje "Asigne una sucursal al usuario" ya usado por `ProformaAdmin`/`NotaVentaAdmin` — mismo contrato, nada nuevo.
- En `ReportStorageAdmin`, los "metros disponibles" mostrados (`aggregated_result`) corresponden a la misma sucursal(es) visible(s) en el listado — hoy pueden estar calculados sobre datos de otra sucursal que ni siquiera aparece en la tabla.

## Architecture considerations

Resumen de ADR-002 (ver documento para alternativas descartadas):
- Un único punto de decisión de rol: `User_Helper.can_view_all_sucursales(user)`.
- Un método `get_*_queryset_by_role(user, qs)` por `business/*.py` afectado, mismo contrato de retorno (`None` si el usuario no tiene sucursal y no ve todo) que ya usan `Proforma_Business`/`Orden_Trabajo_Business`.
- Sin cambios de modelo ni migraciones — el grupo `Caja` ya existe en el admin real.
- Cambio de autorización, no de infraestructura ni de contrato API — el frontend Angular no consume estos endpoints de admin, así que no hay coordinación de despliegue backend/frontend.

## Proposed solution

1. `User_Helper.is_request_user_caja` (mismo patrón que los tres `is_request_user_*` existentes, primitivo reutilizable aunque no lo use `can_view_all_sucursales`) y `User_Helper.can_view_all_sucursales` (`is_request_user_admin(user)` — solo Admin ve todas las sucursales; corregido en v2, ver Changelog).
2. `Pago_Business.get_pago_queryset_by_role(user, qs)` — usado por `PagosAdmin` y `ReportDailySellAdmin` (ambos sobre el modelo `pago`/`Proxy_Pagos`, ruta `nota_venta__nota_trabajo__proforma__sucursal`).
3. `Inventario_Business.get_inventario_queryset_by_role(user, qs)` — usado por `ReportStorageAdmin` y `ReportUtilidadAdmin` (ambos sobre `inventario`/`inventario_proxy`/`utilidades`, FK directa `sucursal`). `ReportStorageAdmin` además filtra su query de agregación (`aggregated_result`) por la(s) misma(s) sucursal(es) resueltas para el usuario.
4. `Orden_Trabajo_Business.get_finish_nota_queryset(user, qs)` — se descomenta el filtro, se reemplaza por `can_view_all_sucursales`, usado por `ReportNotaTrabajoAdmin`.
5. Cada `ModelAdmin.get_queryset` llama al método correspondiente, con el mismo patrón de manejo de `None` que ya usan `ProformaAdmin`/`NotaVentaAdmin` (mensaje de error + queryset vacía).

## Files/components affected

**Backend** (`praxsa_manager/product/`):
- `helper/user.py` — nuevo `is_request_user_caja`, nuevo `can_view_all_sucursales`.
- `business/pago.py` — nuevo `get_pago_queryset_by_role`.
- `business/inventario.py` — nuevo `get_inventario_queryset_by_role`.
- `business/orden_trabajo.py` — modifica `get_finish_nota_queryset` (agrega `user`, descomenta filtro).
- `admin_config/pagos.py` — `get_queryset` delega a `Pago_Business`.
- `admin_config/report_daily_sell.py` — `get_queryset` delega a `Pago_Business`.
- `admin_config/report_storage.py` — `get_queryset` delega a `Inventario_Business`; `aggregated_result` filtrado.
- `admin_config/report_utilidad.py` — `get_queryset` delega a `Inventario_Business`.
- `admin_config/report_nota_trabajo.py` — `get_queryset` pasa `request.user` a `get_finish_nota_queryset`.
- `tests/helpers.py` — nuevas fábricas: `create_nota_trabajo`, `create_nota_venta`, `create_pago`, `add_user_to_group`.
- `tests/test_sucursal_scope_admin.py` (nuevo) — tests de los métodos `business/` y de wiring de cada `ModelAdmin.get_queryset`.

**Frontend**: ninguno — estos admins no son consumidos por `proforma/`.

## Implementation steps

1. `User_Helper`: agregar `is_request_user_caja` y `can_view_all_sucursales`. Test unitario cubriendo Admin/Caja/Supervisor-o-ninguno.
2. `tests/helpers.py`: agregar `add_user_to_group(user, group_name)` (usa `django.contrib.auth.models.Group.objects.get_or_create`), `create_nota_trabajo(proforma, **kwargs)`, `create_nota_venta(nota_trabajo, created_by, **kwargs)`, `create_pago(nota_venta, created_by, **kwargs)` — mínimos necesarios para los tests de este plan, sin reusar campos que no hagan falta.
3. `Pago_Business.get_pago_queryset_by_role(user, qs)`: implementar siguiendo el contrato de `Proforma_Business.get_proforma_queryset_by_role` (ver all si `can_view_all_sucursales`; si no, filtrar por `sucursales[0].id` vía `nota_venta__nota_trabajo__proforma__sucursal__id`; `None` si no hay sucursal). Tests: Admin ve todo, Caja ve todo, usuario con sucursal ve solo la suya, usuario sin sucursal y sin rol devuelve `None`.
4. Wire `PagosAdmin.get_queryset` al método anterior, mismo patrón de manejo de `None` que `ProformaAdmin`. Test de wiring: `PagosAdmin().get_queryset(request)` con usuario de sucursal A no devuelve pagos de sucursal B.
5. Wire `ReportDailySellAdmin.get_queryset` al mismo método de `Pago_Business` (reusa el trabajo del paso 3). Test de wiring análogo.
6. `Inventario_Business.get_inventario_queryset_by_role(user, qs)`: mismo contrato, filtro directo por `sucursal__id`. Tests: Admin/Caja ven todo, usuario con sucursal ve solo la suya, sin sucursal y sin rol → `None`.
7. Wire `ReportStorageAdmin.get_queryset` al método anterior, aplicando el mismo filtro de sucursal también a la query que arma `aggregated_result` (para que `get_metros_disponibles` no muestre datos de una sucursal fuera del listado visible). Test de wiring: verifica tanto las filas devueltas como que `aggregated_result` no contiene sucursales ajenas.
8. Wire `ReportUtilidadAdmin.get_queryset` al mismo método de `Inventario_Business`. Test de wiring análogo (incluye verificar que `precio_compra_mtr_lineal`/utilidad de otra sucursal no aparece).
9. `Orden_Trabajo_Business.get_finish_nota_queryset`: agregar parámetro `user`, descomentar el filtro, reemplazar el bloque comentado por `can_view_all_sucursales`. Tests: Admin/Caja ven todo, usuario con sucursal ve solo la suya, sin sucursal y sin rol → `None` (mismo contrato que el resto).
10. Wire `ReportNotaTrabajoAdmin.get_queryset` pasando `request.user`. Test de wiring análogo.
11. Correr la suite completa (`python manage.py test`) y `python manage.py makemigrations --check --dry-run` (se espera "sin cambios" — este plan no toca modelos).

## Test strategy

**¿E2E?** No corresponde. El cambio vive enteramente en el panel de administración de Django (`ModelAdmin.get_queryset`), no es un flujo de usuario del frontend Angular, y Playwright no está instalado en `proforma/package.json` (agregarlo sería una dependencia nueva injustificada para probar una vista de admin de Django). Se valida con tests de Django.

**Unitarios** (capa `business/` y `helper/`), en `praxsa_manager/product/tests/test_sucursal_scope_admin.py`, usando `django.test.TestCase` + las fábricas de `helpers.py`:
- `User_Helper.can_view_all_sucursales`: `True` para grupo `Admin`, `False` para `Caja`/`Supervisor`/`Instalador`/sin grupo.
- `Pago_Business.get_pago_queryset_by_role`, `Inventario_Business.get_inventario_queryset_by_role`, `Orden_Trabajo_Business.get_finish_nota_queryset`: para cada uno — (a) Admin ve pagos/inventario/notas de 2 sucursales distintas, (b) un usuario del grupo `Caja` con sucursal propia solo ve los de su sucursal (no ve las de otra sucursal), (c) usuario con sucursal propia sin rol especial solo ve los de su sucursal (creando datos en una segunda sucursal como control negativo), (d) usuario sin `Admin` y sin sucursal asignada recibe `None`.

**Integración/wiring** (uno por cada `ModelAdmin.get_queryset` tocado — `PagosAdmin`, `ReportDailySellAdmin`, `ReportStorageAdmin`, `ReportUtilidadAdmin`, `ReportNotaTrabajoAdmin`): instanciar el `ModelAdmin` real con `django.test.RequestFactory`, asignar `request.user` a un usuario de sucursal A, y verificar que `get_queryset(request)` no incluye registros de una sucursal B creada como control. Esto existe porque un test que solo cubre `business/*.py` no detectaría el error de olvidar conectar el admin al método nuevo (la clase de bug más probable en este cambio).

Si algún paso de implementación cambiara lógica de negocio sin su caso de prueba correspondiente aquí, el plan está incompleto — no aplica en este caso: todos los pasos 1, 3, 6, 9 (lógica) y 4, 5, 7, 8, 10 (wiring) tienen su test explícito arriba.

## Acceptance criteria

- [ ] `User_Helper.can_view_all_sucursales` existe y está cubierto por test.
- [ ] `PagosAdmin`, `ReportDailySellAdmin`, `ReportStorageAdmin`, `ReportUtilidadAdmin` filtran por sucursal salvo para `Admin`, cada uno con test de wiring.
- [ ] `Orden_Trabajo_Business.get_finish_nota_queryset` ya no tiene el filtro comentado, recibe `user`, y `ReportNotaTrabajoAdmin` lo usa correctamente, con test de wiring.
- [ ] `ReportStorageAdmin.aggregated_result` respeta el mismo filtro de sucursal que el queryset principal.
- [ ] `python manage.py test` pasa completo (incluye smoke tests existentes, sin regresiones).
- [ ] `python manage.py makemigrations --check --dry-run` no reporta migraciones pendientes.
- [ ] Ningún archivo de `proforma/` (frontend) modificado.
- [ ] `Proforma_Business.get_proforma_queryset_by_role`, `NotaVentaAdmin`, `NotaTrabajoAdmin` sin cambios (confirmado fuera de alcance).

## Risks

- **Usuario sin `Admin` y sin sucursal asignada verá listas vacías** en los 5 admins de este cambio (esto incluye a un eventual usuario `Caja` sin sucursal) — mismo comportamiento que ya tienen `ProformaAdmin`/`NotaVentaAdmin` hoy, no es un riesgo nuevo, pero conviene que quien despliegue lo sepa antes de recibir un reporte de "no veo nada" de un usuario mal configurado. Mitigación: ya cubierto por ADR-002 (verificación manual pre/post-despliegue).
- **`ReportStorageAdmin.aggregated_result` desincronizado del `qs` filtrado** si el paso 7 se implementa filtrando solo uno de los dos. Mitigación: test de wiring del paso 7 verifica ambos explícitamente.
- **Sin migraciones de por medio**, el riesgo de romper datos existentes es nulo; el riesgo real es puramente de autorización (ver arriba), no de integridad de datos.

## Out of scope

- Unificar `Proforma_Business.get_proforma_queryset_by_role` para usar `User_Helper` (decisión explícita del usuario, ver ADR-002).
- Corregir el bug de "Admin sin sucursal ve listas vacías" en `NotaVentaAdmin`/`NotaTrabajoAdmin` (decisión explícita del usuario).
- SEC-07 (mutación de estado compartido en `changelist_view` de `InventoryAdmin`/`ProformaAdmin`/`ReportStorageAdmin`) — hallazgo independiente, no se toca aquí.
- Crear el grupo `Caja` — ya existe según confirmó el usuario.

## Dependencias nuevas

Ninguna.

## Changelog
- **v2** (2026-09-22): corrección de alcance — solo el grupo `Admin` ve todas las sucursales; `Caja` pasa a comportarse como cualquier usuario sin rol especial (filtrado por su propia sucursal). El usuario detectó el error probando la rama manualmente contra su Postgres real y lo corrigió en el chat. Cambio de código mínimo: una línea en `User_Helper.can_view_all_sucursales` (deja de incluir `is_request_user_caja`); no hizo falta tocar ningún admin ni método de `business/`, porque todos ya delegaban en ese único punto de decisión — confirma que la abstracción elegida en ADR-002 cumplió su propósito. Se actualizaron los tests que asumían "Caja ve todo" para en cambio verificar "Caja ve solo su sucursal", y se re-verificó la suite completa (27/27) contra Postgres real.
