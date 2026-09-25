# PLAN-2026-09-23-idor-invoice-and-proforma-car-part-info (v1)

**Task:** TASK-008
**ADRs relacionados:** [ADR-006-idor-invoice-and-proforma-car-part-info.md](../adr/ADR-006-idor-invoice-and-proforma-car-part-info.md)

## Objective
Cerrar el IDOR de backlog #4 (`docs/integration-and-backlog.md`): `InvoiceView.get` debe dejar de exponer proformas de otros clientes, y `get_proforma_car_part_info` debe dejar de exponer datos de precio/inventario/tipo de venta de cualquier proforma a cualquier request sin auth ni scoping.

## Context
Investigación completa en `docs/tasks/TASK-008.md`. Resumen: `InvoiceView.get` ya está autenticado por token pero no filtra por dueño; `get_proforma_car_part_info` no tiene ningún control de acceso y su único consumidor real es `nota_trabajo.js` (JS del admin de Django, usado por staff para armar la nota de trabajo de instalación de proformas que casi nunca crearon ellos mismos). La decisión de arquitectura (ADR-006) descartó aplicar el filtro `created_by` sugerido literalmente por el backlog a `get_proforma_car_part_info` porque rompería ese flujo, y en su lugar decidió reusar el scoping por sucursal/rol que ya protege `ProformaAdmin`.

## Current behavior
- `InvoiceView.get` ([custom_views/invoice.py:36-75](../../praxsa_manager/product/custom_views/invoice.py)): `Proforma_Header.objects.select_related('car_model_id', 'sucursal').get(id=pk)` sin filtro de dueño. Código muerto comentado en líneas 39 y 70-71 (`# if invoice.client_id.id == client.id: ... # else: not allowed`).
- `get_proforma_car_part_info` ([views.py:153-194](../../praxsa_manager/product/views.py)): vista de función plana sin decorador ni chequeo de auth, `Proforma_Header.objects.select_related('sucursal', 'car_model_id').get(pk=proforma_id)` sin ningún filtro.
- Patrón de referencia ya en el código: `ListUserInvoice.get` filtra con `Proforma_Header.objects.filter(created_by=request.user.id)` ([invoice.py:100-101](../../praxsa_manager/product/custom_views/invoice.py)); `get_bobina` usa `if not (request.user.is_authenticated and request.user.is_staff): return JsonResponse(..., status=403)` ([views.py:45-47](../../praxsa_manager/product/views.py)); `ProformaAdmin.get_queryset` delega en `Proforma_Business.get_proforma_queryset_by_role(user, qs)` ([admin_config/proforma_admin.py:191-197](../../praxsa_manager/product/admin_config/proforma_admin.py), [business/proforma.py:197-216](../../praxsa_manager/product/business/proforma.py)).

## Expected behavior
- `InvoiceView.get`: un cliente autenticado con token solo puede leer su propia proforma por `pk`. Pedir la de otro usuario devuelve `404` (mismo código que "no existe" hoy, sin distinguir los dos casos).
- `get_proforma_car_part_info`: solo un usuario `is_authenticated and is_staff` puede llamarlo. Si es del grupo `Admin`, puede consultar cualquier proforma no borrada; si no, solo las de su(s) propia(s) sucursal(es). Cualquier otro caso (anónimo, no-staff, proforma inexistente, proforma de otra sucursal) devuelve una respuesta de error explícita (`403` para no-staff/anónimo, `404` para "no existe o no es de tu sucursal") — nunca el `200` con datos que devuelve hoy.

## Architecture considerations
Resumen de ADR-006 (decisión ya tomada, no se re-evalúa aquí):
- `InvoiceView.get` no necesita mecanismo nuevo: agregar `created_by=request.user` al `.get()` existente. El `except ObjectDoesNotExist` ya presente cubre "es de otro usuario" como 404 sin código adicional.
- `get_proforma_car_part_info` reusa dos mecanismos ya probados en el proyecto en vez de inventar uno: el chequeo manual de staff de `get_bobina` (ADR-005) y el método `get_proforma_queryset_by_role` que ya usa `ProformaAdmin`. No se introduce DRF ni un nuevo esquema de autenticación.
- Sin migraciones. Sin cambios de contrato de API para el frontend Angular (no consume `get_proforma_car_part_info`; `InvoiceView.get` mantiene el mismo shape de respuesta, solo cambia cuándo responde 404).
- Dinero: no aplica (no se toca ningún cálculo de precio en este task).

## Proposed solution

### 1. `InvoiceView.get` — `praxsa_manager/product/custom_views/invoice.py`
- Cambiar la línea 38 a `Proforma_Header.objects.select_related('car_model_id', 'sucursal').get(id=pk, created_by=request.user)`.
- Eliminar las líneas comentadas 39 y 70-71 (código muerto, referencia campos inexistentes).
- No tocar el manejo de excepciones existente (`ObjectDoesNotExist` → 404, `MultipleObjectsReturned` → 409): ya cubre el nuevo caso sin cambios.

### 2. `get_proforma_car_part_info` — `praxsa_manager/product/views.py`
- Agregar como primera línea del cuerpo de la función (antes del `try`):
  ```python
  if not (request.user.is_authenticated and request.user.is_staff):
      return JsonResponse(data={'error': True, 'message': 'not allowed'}, status=403)
  ```
- Dentro del `try`, reemplazar `Proforma_Header.objects.select_related('sucursal', 'car_model_id').get(pk=proforma_id)` por:
  ```python
  proforma_business = Proforma_Business()
  qs = Proforma_Header.objects.select_related('sucursal', 'car_model_id')
  scoped_qs = proforma_business.get_proforma_queryset_by_role(user=request.user, qs=qs)
  if scoped_qs is None:
      return JsonResponse(data={'error': True, 'message': 'not allowed'}, status=403)
  proforma = scoped_qs.get(pk=proforma_id)
  ```
- Separar la captura de excepciones: `ObjectDoesNotExist` (o el `DoesNotExist` específico de `Proforma_Header`) → `404` explícito; mantener el `except Exception` general solo para errores realmente inesperados (500), como ya hace el resto del archivo (`get_bobina`, `get_car_part_info`). Esto es necesario porque hoy el único `except Exception` amplio convertiría un 404 legítimo en un 500 genérico.
- Import nuevo: `from .business.proforma import Proforma_Business` (verificar que no genere import circular — `business/proforma.py` ya se importa desde otros módulos de `views.py`/`admin_config`, se espera que no haya problema, pero se confirma en el paso de implementación).

## Files/components affected
Backend únicamente:
- `praxsa_manager/product/custom_views/invoice.py` (`InvoiceView.get`)
- `praxsa_manager/product/views.py` (`get_proforma_car_part_info`, nuevo import de `Proforma_Business`)
- `praxsa_manager/product/tests/` (tests nuevos, ver abajo)

Frontend: ninguno (confirmado en la investigación — sin consumidor Angular de `get_proforma_car_part_info`; `InvoiceView.get` no cambia su shape de respuesta, solo agrega casos de 404).

## Implementation steps
1. Test de caracterización para `InvoiceView.get`: dos usuarios con token (`create_user_with_token`), cada uno con su propia proforma (`create_full_proforma`); usuario A pide la proforma de B por `pk` → hoy pasa (200 con datos ajenos). Este test debe fallar contra el código actual (documenta el bug) antes del fix.
2. Aplicar el fix de `InvoiceView.get` (paso 1 de "Proposed solution"). Reescribir el test del paso 1 para que ahora afirme `404` en el caso cruzado, y agregar un caso positivo (A pide su propia proforma → 200 con los datos correctos).
3. Test de caracterización para `get_proforma_car_part_info`: request sin sesión (`self.client.get(...)` sin login) sobre una proforma real → hoy pasa (200 con datos). Debe fallar contra el código actual.
4. Aplicar el fix de `get_proforma_car_part_info` (paso 2 de "Proposed solution").
5. Ampliar los tests de `get_proforma_car_part_info` a los escenarios de la matriz de autorización (ver Test strategy) hasta cubrir: anónimo, autenticado no-staff, staff del grupo `Admin`, staff de la sucursal correcta, staff de otra sucursal, proforma inexistente.
6. Correr la suite completa de `praxsa_manager/product/tests/` (regresión) — el cambio toca `Proforma_Header`/`Proforma_Business`, usados también por `ProformaAdmin` y otros tests ya existentes (`test_sucursal_scope_admin.py`).
7. Verificación manual (ver Acceptance criteria): navegador como cliente Angular real (dos usuarios) y como staff en el admin de Django (nota de trabajo).

## Test strategy

**Nivel:** unitario/integración con Django `TestCase`, en `praxsa_manager/product/tests/`, reusando `helpers.py` (`create_user_with_token`, `create_staff_user`, `add_user_to_group`, `create_full_proforma`, `create_sucursal`). Nuevo archivo: `praxsa_manager/product/tests/test_idor_invoice_and_proforma_car_part_info.py`.

**`InvoiceView.get`:**
- Usuario A puede leer su propia proforma (200, shape correcto).
- Usuario A no puede leer la proforma de usuario B (404).
- `pk` inexistente sigue devolviendo 404 (regresión del comportamiento ya existente).

**`get_proforma_car_part_info`:**
- Request anónimo (sin login) → 403.
- Usuario autenticado no-staff → 403.
- Staff del grupo `Admin` → 200, puede ver una proforma de cualquier sucursal.
- Staff sin grupo `Admin`, asignado a la sucursal de la proforma (`Sucursal.empleado`) → 200 con el shape actual (`items`, `window_film`, `inv_widths`, `sales_type`).
- Staff sin grupo `Admin`, asignado a otra sucursal → 404 (no 403, para no confirmar la existencia de la proforma).
- `proforma_id` inexistente, pedido por staff válido → 404 (antes daba 500 genérico — se documenta el cambio de comportamiento).

**Regresión:** correr `python manage.py test product` completo desde `praxsa_manager/` — el cambio toca un método de `business/proforma.py` ya usado por `ProformaAdmin` (backlog #10 / TASK-002), hay que confirmar que `test_sucursal_scope_admin.py` sigue pasando sin cambios.

**E2E:** no corresponde. Justificación: el cambio es 100% server-side y no modifica ningún flujo de navegación, formulario multi-paso ni contrato de API que el frontend consuma de forma distinta (`InvoiceView.get` sigue devolviendo el mismo shape en 200, solo cambia cuándo responde 404; `get_proforma_car_part_info` no tiene consumidor en `proforma/src`). Un test de integración de Django contra la vista real ya ejercita la ruta HTTP completa sin necesitar un navegador. Playwright no está instalado en el proyecto y este task no lo requiere.

## Acceptance criteria
- [ ] `InvoiceView.get`: un cliente ve su propia proforma; un `pk` de otro cliente devuelve 404.
- [ ] `get_proforma_car_part_info`: rechaza anónimos y no-staff (403); un staff no-admin solo ve proformas de su propia sucursal (404 para las demás); un staff del grupo `Admin` ve cualquiera.
- [ ] Ningún test existente de `praxsa_manager/product/tests/` se rompe (regresión).
- [ ] Verificación manual: logueado como cliente Angular real, `proforma/<propio-id>` sigue funcionando igual que antes; `proforma/<id-ajeno>` ya no muestra datos de otro cliente.
- [ ] Verificación manual: logueado como staff no-admin en el admin de Django, la nota de trabajo de una proforma de la propia sucursal sigue cargando los items correctamente (sin regresión funcional para el equipo de instalación).
- [ ] Código muerto comentado en `invoice.py` (líneas 39, 70-71) eliminado.

## Risks
- **Import circular al traer `Proforma_Business` a `views.py`**: no confirmado en la investigación si genera un ciclo de imports. Mitigación: verificar en el primer intento de implementación (`python manage.py check`); si hay ciclo, mover la importación dentro de la función en vez de al tope del archivo (patrón ya usado en otras partes del proyecto para evitar ciclos).
- **`get_proforma_queryset_by_role` devuelve `None` para un staff sin sucursal asignada**: ya documentado en ADR-006 como riesgo aceptado con mitigación (test explícito + verificación manual); si ocurre en producción, el staff afectado necesita que se le asigne una sucursal en `Sucursal.empleado` (mismo problema que ya existe hoy para `ProformaAdmin`, no es nuevo de este cambio).
- **Cambiar `get_proforma_car_part_info` de 500 a 404 para proforma inexistente**: es un cambio de comportamiento visible (aunque nunca documentado como contrato), se registra explícitamente en el plan y en el PR para que `delivery-review` lo verifique con evidencia real, no solo se asuma correcto.

## Out of scope
- `get_car_part_info` (otra vista sin auth del hallazgo original SEC-03) — no es parte de backlog #4.
- Corregir que `get_inventory_window_film_reel_widths` reciba `request.user` en vez de resolver la sucursal desde `proforma.sucursal` — bug preexistente independiente, no evaluado a fondo.
- Decidir si `InvoiceView.get` debería devolver `403` en vez de `404` ante una proforma ajena — ADR-006 ya fijó `404` para no revelar existencia; no es una pregunta abierta de este plan.

## Dependencias nuevas
Ninguna.
