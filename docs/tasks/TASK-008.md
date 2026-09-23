# TASK-008: IDOR en `InvoiceView.get` y `get_proforma_car_part_info` (backlog #4)

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Rama:** `task/TASK-008-idor-proforma-access`
**Pull Request:** [#35](https://github.com/rolion/praxsa-django-panel-admin/pull/35)

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-09-23 | (nuevo) → INVESTIGATION | Task creado | delivery-investigate |
| 2026-09-23 | INVESTIGATION → PLANNING | Decisión de arquitectura registrada en ADR-006 | delivery-architect |
| 2026-09-23 | PLANNING → ENGINEERING | Plan v1 escrito y PR abierto | delivery-plan |
| 2026-09-23 | ENGINEERING → REVIEW | Implementación completa, tests OK, PR actualizado | delivery-engineer |
| 2026-09-23 | REVIEW → PUBLISH | Veredicto PASS, sin issues Critical/High | delivery-review |

## Investigación

### Requerimiento
IDOR (Insecure Direct Object Reference) en dos endpoints, backlog #4 de `docs/integration-and-backlog.md` (línea 160-165, "[ALTO] IDOR — cualquier usuario ve proformas ajenas"):
- `InvoiceView.get` no filtra por `created_by`: cualquier usuario autenticado puede leer la proforma de otro cliente cambiando el `pk` en la URL.
- `get_proforma_car_part_info` no tiene autenticación ni filtro de pertenencia: cualquiera, autenticado o no, puede leerlo cambiando el `proforma_id`.

El backlog sugiere como pasos: "test + fix en `InvoiceView.get` (agregar `.filter(created_by=request.user)`)" y "test + fix en `get_proforma_car_part_info` (requerir auth y filtrar por pertenencia, mismo patrón que `ListUserInvoice`)". Esta investigación verifica ambos supuestos contra el código real antes de aceptarlos como solución (ver Riesgos).

### Hechos encontrados

**`InvoiceView.get`** — [custom_views/invoice.py:36-75](praxsa_manager/product/custom_views/invoice.py:36-75)
- La vista usa `authentication_classes = [TokenAuthentication]` / `permission_classes = [IsAuthenticated]` a nivel de clase ([invoice.py:17-18](praxsa_manager/product/custom_views/invoice.py:17-18)), así que el request ya está autenticado — el problema es exclusivamente falta de filtro por pertenencia, no falta de auth.
- La query es `Proforma_Header.objects.select_related(...).get(id=pk)` ([invoice.py:38](praxsa_manager/product/custom_views/invoice.py:38)) — sin ningún `filter(created_by=...)`.
- Hay un intento de chequeo de pertenencia **comentado y roto**: `# if invoice.client_id.id == client.id:` ... `# else: return Response(data={'not allowed'}, status=401)` ([invoice.py:39](praxsa_manager/product/custom_views/invoice.py:39), [invoice.py:70-71](praxsa_manager/product/custom_views/invoice.py:70-71)). Referencia una variable `client` que no existe en el método actual y un atributo `client_id` que el modelo `Proforma_Header` no tiene — es código muerto de una versión anterior, nunca terminado ni reactivado.
- El fix sugerido por el backlog (agregar `.filter(created_by=request.user)`) ya tiene un ejemplo funcionando **en el mismo archivo**: `ListUserInvoice.get` hace exactamente `Proforma_Header.objects.filter(created_by=request.user.id)` ([invoice.py:100-101](praxsa_manager/product/custom_views/invoice.py:100-101)).

**`get_proforma_car_part_info`** — [views.py:153-194](praxsa_manager/product/views.py:153-194)
- Es una vista de función Django plana (no `@api_view`, no `Response`/DRF), sin ningún decorador de auth ni chequeo manual — a diferencia de `get_bobina` en el mismo archivo, que sí tiene `if not (request.user.is_authenticated and request.user.is_staff): return JsonResponse(..., status=403)` como primera línea ([views.py:45-47](praxsa_manager/product/views.py:45-47)).
- Hace `Proforma_Header.objects.select_related(...).get(pk=proforma_id)` sin ningún filtro de pertenencia ni de sucursal.
- Devuelve, para cualquier `proforma_id` existente: el `sales_type` de esa proforma, la lista de partes de auto requeridas (`items`, con `installation_price`), y el inventario de láminas disponible en la sucursal de esa proforma (`window_film`, con precio `precio_venta_mtr_lineal` y `reel_id`) — datos de negocio (precios, stock) equivalentes en sensibilidad a los que `get_car_part_info`/`get_inventory` ya protegen o dejan explícitamente públicos con throttling (TASK-006/ADR-005).
- Ruta: `path('get_proforma_car_part_info/<int:proforma_id>', ...)` en [urls.py:12](praxsa_manager/product/urls.py:12).
- **Único consumidor encontrado en el repo**: `praxsa_manager/product/static/product/nota_trabajo.js:25`, un AJAX `$.get` disparado desde el inline `ProformaDetailInLine` del admin de Django ([admin_config/nota_trabajo.py:24-27,103](praxsa_manager/product/admin_config/nota_trabajo.py:24-27)) — es decir, se usa para armar la nota de trabajo de instalación, dentro de una página que ya requiere sesión de staff para cargar. **No hay ningún consumidor en `proforma/src`** (Angular) — no coincide ninguna búsqueda de `get_proforma_car_part_info` en el frontend del cliente final.
- El caso de uso real (staff armando la nota de trabajo) necesita ver el detalle de **cualquier proforma que le corresponda atender**, no solo las que él mismo creó — el concepto de "pertenencia" aquí no es "creado por este usuario" como en `ListUserInvoice`, sino más parecido a "sucursal del usuario staff", igual que ya filtra el admin de proformas (ver más abajo).
- `get_inventory_window_film_reel_widths(request.user)` ([business/inventario.py:157-162](praxsa_manager/product/business/inventario.py:157-162)) filtra `sucursal__empleado=user` y se invoca pasándole `request.user` dentro de esta vista — para un request sin sesión (`AnonymousUser`), esa sub-consulta devuelve vacío hoy (no lanza excepción), pero `items` y `window_film` (resueltos por `proforma.sucursal`, no por el usuario) sí se devuelven igual sin ninguna restricción.

**Patrones de autorización ya existentes en el código, relevantes para decidir el fix de `get_proforma_car_part_info`:**
- `get_bobina` (mismo módulo): chequeo manual `is_authenticated and is_staff` inline, sin migrar a DRF — establecido en TASK-006/ADR-005 para el mismo tipo de consumidor (JS del admin, sin precedente de sesión-admin en DRF).
- `ProformaAdmin.get_queryset` ([admin_config/proforma_admin.py:191-197](praxsa_manager/product/admin_config/proforma_admin.py:191-197)) delega en `Proforma_Business.get_proforma_queryset_by_role` ([business/proforma.py:197-216](praxsa_manager/product/business/proforma.py:197-216)): si el usuario es del grupo `Admin` ve todas las proformas no borradas; si no, solo las de la(s) sucursal(es) donde figura como `empleado`. Esto es lo que hoy protege, a nivel de admin, que un staff de una sucursal vea proformas de otra — pero **solo protege la carga de la página del admin**, no el endpoint AJAX crudo, que la ignora por completo.
- `InventoryAdmin.get_queryset` ([admin_config/inventory.py:43-53](praxsa_manager/product/admin_config/inventory.py:43-53)) usa el mismo patrón de sucursal-por-empleado para inventario.

**Modelo:**
- `Proforma_Header.created_by` es un `ForeignKey(User, ..., null=False)` ([models.py:162](praxsa_manager/product/models.py:162)) — el dato para filtrar por pertenencia en `InvoiceView.get` ya existe y está poblado siempre (no nullable).

**Exploit confirmado end-to-end (no solo teórico):**
- El frontend Angular navega a la ruta `proforma/:id` ([pages/proforma/proforma.component.ts:37-43](proforma/src/app/pages/proforma/proforma.component.ts:37-43)), que solo verifica `this.currentUser` (cualquier usuario logueado) antes de llamar `getProforma(id)` — sin verificar que `id` le pertenezca. `ProformaService.getProforma` hace `GET /product/invoice/${invoice_id}` ([service/pybackend/proforma/proforma.service.ts:38-44](proforma/src/app/service/pybackend/proforma/proforma.service.ts:38-44)). Cualquier cliente logueado puede escribir manualmente otra URL `proforma/<id-ajeno>` y ver nombre, email, CI/NIT, teléfono, placa, sucursal (nombre/dirección/teléfono) y total de otra persona.

**Tests existentes reusables:**
- `praxsa_manager/product/tests/helpers.py` ya tiene `create_user_with_token`, `create_staff_user`, `create_full_proforma(user, ...)` ([tests/helpers.py:154-199](praxsa_manager/product/tests/helpers.py:154-199)) — permite crear dos usuarios con proformas propias en un test, exactamente el escenario necesario para caracterizar el IDOR de `InvoiceView.get`.
- `praxsa_manager/product/tests/test_public_catalog_endpoints.py` ya tiene el patrón de test para vistas de función plana sin auth (`self.client.get(...)` sin token, verificar `status_code`) — reusable para `get_proforma_car_part_info`.
- No existe hoy ningún test para `InvoiceView.get` ni para `get_proforma_car_part_info` (no aparecen en `grep` de `tests/*.py`).

### Hipótesis / supuestos no confirmados
- **La recomendación del propio backlog para `get_proforma_car_part_info` ("filtrar por pertenencia, mismo patrón que `ListUserInvoice`") probablemente no aplica tal cual**: `ListUserInvoice` filtra por `created_by=request.user` porque su consumidor es el cliente dueño de la proforma; `get_proforma_car_part_info` lo consume el staff armando la nota de trabajo de una proforma que casi nunca creó él mismo. Aplicar literalmente "filtrar por `created_by`" rompería la funcionalidad de nota de trabajo para todo el equipo de instalación. Esto no se decide aquí — es la pregunta central que debe resolver `delivery-architect`.
- No se confirmó si existe algún otro consumidor de `get_proforma_car_part_info` fuera de este repo (app externa, integración) — solo se verificó `proforma/src` y `praxsa_manager/product/static`.
- No se confirmó si es intencional que `get_inventory_window_film_reel_widths` reciba `request.user` en vez de resolver la sucursal desde la propia `proforma` — podría ser un bug preexistente independiente del IDOR, no evaluado a fondo por estar fuera del alcance de esta investigación.
- No se confirmó con negocio si, una vez logueado, un cliente debería recibir `403` o `404` al intentar ver una proforma ajena por `InvoiceView.get` (afecta si el frontend puede distinguir "no existe" de "no autorizado").

### Módulos y dependencias relacionadas
- Backend: `praxsa_manager/product/custom_views/invoice.py` (`InvoiceView`, `ListUserInvoice`), `praxsa_manager/product/views.py` (`get_proforma_car_part_info`, y como referencia `get_bobina`, `get_car_part_info`, `get_inventory`), `praxsa_manager/product/business/proforma.py` (`get_proforma_queryset_by_role`), `praxsa_manager/product/business/inventario.py` (`get_inventory_window_film_reel_widths`), `praxsa_manager/product/admin_config/proforma_admin.py`, `praxsa_manager/product/admin_config/nota_trabajo.py`, `praxsa_manager/product/static/product/nota_trabajo.js`, `praxsa_manager/product/urls.py`.
- Frontend: no requiere cambios de código (el problema es 100% server-side), pero `proforma/src/app/pages/proforma/proforma.component.ts` y `proforma.service.ts` son el camino de exploit confirmado, relevante para escribir el caso de prueba desde la perspectiva del cliente.
- Tests: `praxsa_manager/product/tests/helpers.py`, `praxsa_manager/product/tests/test_public_catalog_endpoints.py` (patrón de referencia).

### Implementaciones similares existentes
- `ListUserInvoice.get` ([invoice.py:100-101](praxsa_manager/product/custom_views/invoice.py:100-101)) — filtro por `created_by`, aplicable directo a `InvoiceView.get`.
- `get_bobina` ([views.py:45-47](praxsa_manager/product/views.py:45-47)) — chequeo manual de sesión de staff para una vista de función plana consumida solo por JS del admin, mismo tipo de consumidor que `get_proforma_car_part_info`.
- `Proforma_Business.get_proforma_queryset_by_role` / `InventoryAdmin.get_queryset` — patrón ya establecido de "staff ve solo su(s) sucursal(es), admin ve todo", que es el modelo de autorización real que necesitaría `get_proforma_car_part_info` si el objetivo es igualar lo que el admin de proformas ya protege.

### Comportamiento actual
- `InvoiceView.get`: cualquier usuario con token válido lee cualquier proforma por `pk`, sin importar quién la creó. Confirmado con lectura de código; el chequeo de pertenencia que alguna vez existió está comentado y además roto (referencia campos inexistentes).
- `get_proforma_car_part_info`: cualquier request, autenticado o no, lee items/precios/inventario de cualquier proforma por `proforma_id`. Sin decorador de auth, sin filtro de sucursal ni de pertenencia. Su único consumidor real hoy es una pantalla de admin (nota de trabajo) que ya está protegida a nivel de página por sesión de staff y por `get_proforma_queryset_by_role`, pero el endpoint AJAX ignora ambas protecciones.

### Restricciones
- `docs/CLAUDE.md`: "Todo cambio de lógica de negocio lleva su test" — aplica directo, hay que escribir tests de caracterización (hoy pasa el acceso cruzado) antes de tocar el código.
- `docs/CLAUDE.md`: "Cambios pequeños: un objetivo por cambio, pensado para un PR" — sugiere separar el fix de `InvoiceView.get` (simple, sin decisión pendiente) del de `get_proforma_car_part_info` (requiere decidir el modelo de autorización primero).
- No se debe generalizar el fix de `get_proforma_car_part_info` a un "filtro por `created_by`" sin resolver antes qué significa "pertenencia" para un endpoint consumido por staff, no por el cliente dueño.

### Riesgos identificados
- Cambiar la autorización de `get_proforma_car_part_info` sin caracterizar antes el flujo de nota de trabajo puede romper esa pantalla del admin para todo el equipo de instalación si se aplica ingenuamente el patrón `created_by` sugerido por el backlog.
- Los dos endpoints tienen consumidores y modelos de autorización completamente distintos (cliente final vía token vs. staff vía sesión de admin) — no hay un único fix que sirva para ambos, aumentan las probabilidades de una solución parcial si se trata como un solo cambio homogéneo.
- Ninguno de los dos endpoints tiene test hoy — el fix debe empezar por un test de caracterización (dos usuarios / proforma cruzada) antes de cualquier cambio de código, siguiendo el patrón ya usado en `test_public_catalog_endpoints.py`.
- El manejo de excepción amplio (`except Exception`) en `get_proforma_car_part_info` ya devuelve 500 genérico ante cualquier error (incluida una proforma inexistente) — al agregar una verificación de autorización hay que decidir explícitamente qué código HTTP corresponde (401/403/404) en vez de dejar que caiga en el 500 genérico existente.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — el fix de `InvoiceView.get` por sí solo sería trivial (aplicar el mismo `.filter(created_by=...)` que ya usa `ListUserInvoice` en el mismo archivo), pero `get_proforma_car_part_info` es un cambio de autorización (indicador explícito de `delivery-architect`) donde el patrón sugerido por el backlog no encaja con el consumidor real identificado (staff de admin, no el cliente dueño), y coexisten al menos dos precedentes distintos en el código (`get_bobina` con chequeo manual de staff, y `get_proforma_queryset_by_role` con scoping por sucursal) sin que ninguno aplique 1:1. Se necesita decidir explícitamente el modelo de autorización de `get_proforma_car_part_info` (staff-only global, staff scoped a su sucursal, u otra opción) antes de planificar la implementación de ambos endpoints como un solo task.

## Arquitectura

Ver [ADR-006-idor-invoice-and-proforma-car-part-info.md](../adr/ADR-006-idor-invoice-and-proforma-car-part-info.md).

Resumen de la decisión:
- **`InvoiceView.get`**: agregar `.filter(created_by=request.user)` (mismo patrón que `ListUserInvoice.get` en el mismo archivo) y eliminar el código muerto comentado. El `except ObjectDoesNotExist` existente ya cubre "es de otro usuario" como 404, sin lógica nueva.
- **`get_proforma_car_part_info`**: agregar chequeo `is_authenticated and is_staff` (mismo mecanismo que `get_bobina`, sin migrar a DRF) y reemplazar la consulta directa por el queryset ya acotado de `Proforma_Business.get_proforma_queryset_by_role(user=request.user, qs=...)` — el mismo método que ya usa `ProformaAdmin.get_queryset`. Sin fila visible en ese queryset (no existe, o existe pero es de otra sucursal) → 404, sin distinguir los dos casos.
- Alternativas descartadas: chequeo de solo `is_staff` sin scoping por sucursal (deja una brecha más chica entre sucursales); función de scoping nueva (duplicaría `get_proforma_queryset_by_role`); migrar a DRF `SessionAuthentication`+`IsAdminUser` (sin consumidor DRF real, mismo argumento que ADR-005 para `get_bobina`).
- Rollback: ambos cambios son código puro sin migraciones — revertibles con `git revert` por separado. Mitigación previa detallada en el ADR (tests de caracterización con múltiples usuarios/sucursales + verificación manual en el navegador y en el admin).
- Fuera de alcance de este ADR: distinguir `ObjectDoesNotExist` de otras excepciones dentro del `except Exception` amplio de `get_proforma_car_part_info` (queda como detalle de implementación, con la sola restricción de que el caso no autorizado debe ser 404, no 500); `get_inventory_window_film_reel_widths(request.user)`; `get_car_part_info`.

## Plan

Ver [PLAN-2026-09-23-idor-invoice-and-proforma-car-part-info.md](../plans/PLAN-2026-09-23-idor-invoice-and-proforma-car-part-info.md) (v1).

Resumen: fix trivial en `InvoiceView.get` (`.get(id=pk, created_by=request.user)`, mismo patrón que `ListUserInvoice.get`) + fix en `get_proforma_car_part_info` (chequeo `is_authenticated and is_staff` + scoping por sucursal/rol reusando `Proforma_Business.get_proforma_queryset_by_role`). Tests de caracterización antes de cada fix, matriz de autorización completa para el segundo endpoint, regresión de la suite de `product/tests/`. Sin E2E (justificado: cambio 100% server-side, sin consumidor Angular de `get_proforma_car_part_info`). Sin dependencias nuevas.

## Implementación

Implementado según el plan v1 sin desvíos. Resumen:

- **`InvoiceView.get`** ([custom_views/invoice.py:36-73](../../praxsa_manager/product/custom_views/invoice.py)): `Proforma_Header.objects.select_related('car_model_id', 'sucursal').get(id=pk, created_by=request.user)`. Eliminado el código muerto comentado. El `except ObjectDoesNotExist` existente cubre el 404 sin cambios.
- **`get_proforma_car_part_info`** ([views.py:154-201](../../praxsa_manager/product/views.py)): chequeo `is_authenticated and is_staff` (403 si falla) + scoping con `Proforma_Business().get_proforma_queryset_by_role(user=request.user, qs=...)` (403 si devuelve `None`, 404 si el `.get(pk=...)` no encuentra la fila dentro del queryset acotado). `except ObjectDoesNotExist` separado del `except Exception` genérico.
- Import nuevo `from .business.proforma import Proforma_Business` en `views.py` — verificado sin ciclo de imports (`python -c "... import product.views"` importa limpio).
- Tests nuevos: `praxsa_manager/product/tests/test_idor_invoice_and_proforma_car_part_info.py`, 10 casos (3 para `InvoiceView.get`, 7 para `get_proforma_car_part_info`, incluida la matriz completa de autorización: anónimo, no-staff, admin, staff de la sucursal correcta, staff de otra sucursal, staff sin sucursal asignada, proforma inexistente).
- Regresión: `python manage.py test product` completo → 56/56 OK (46 preexistentes + 10 nuevos). Corrido contra Postgres real local, no SQLite.

**Deuda técnica / fuera de alcance señalada, no resuelta aquí** (ya documentada como out-of-scope en el plan/ADR): `get_inventory_window_film_reel_widths` sigue recibiendo `request.user` (el staff) en vez de resolver la sucursal desde `proforma.sucursal`; `get_car_part_info` sigue sin auth (no es parte de backlog #4).

**No verificado en esta etapa** (pendiente de `delivery-review`, según sus propias reglas): verificación manual en navegador (cliente Angular real con dos usuarios; staff no-admin en el admin de Django abriendo la nota de trabajo).

## Review

**Veredicto: PASS.** Cero issues (ningún `REV-*.md` generado). Detalle completo de la verificación en `## Testing`/`## Review` del [PR #35](https://github.com/rolion/praxsa-django-panel-admin/pull/35).

Nota de aislamiento: esta revisión corrió en la misma sesión que implementó el código (limitación procedimental declarada al usuario al inicio de la revisión). Mitigación aplicada: reconstrucción de contexto solo desde artefactos (TASK, plan, ADR, diff real contra `origin/master`), y verificación 100% ejecutada (regresión completa corrida dos veces de forma independiente + verificación HTTP en vivo con `StaticLiveServerTestCase`+`requests`, no solo relectura del código ya escrito).

Resumen de evidencia:
- 56/56 tests OK (regresión completa, dos corridas independientes contra Postgres real).
- Verificación en vivo con HTTP real (servidor real, login real de admin con CSRF, token real): dueño ve su proforma (200), otro usuario 404, anónimo 403 en `get_proforma_car_part_info`, staff de la sucursal correcta 200, staff de otra sucursal 404.
- `makemigrations --check --dry-run`: sin cambios pendientes.
- Lint/type-check/security: no instalados en el backend — registrado como verificación no realizada, no como PASS silencioso.
- Sin scope creep: diff limitado a los archivos que el plan identificó.
- ADR-006 compliance: verificado punto por punto, sin desvíos.

**Hallazgo fuera de alcance, no bloqueante**: `product_proforma_header` tiene una columna `status` NOT NULL en la Postgres real de desarrollo que no existe en `models.py` ni en las migraciones actuales (drift de esquema preexistente). Se marcó por separado para investigación futura, no es parte de backlog #4.

## Publicación
_Pendiente_
