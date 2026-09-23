# ADR-006: Cerrar el IDOR de `InvoiceView.get` (filtro por dueño) y de `get_proforma_car_part_info` (scoping por sucursal/rol, reusando `get_proforma_queryset_by_role`)

**Estado:** Propuesto
**Task relacionado:** TASK-008
**Fecha:** 2026-09-23

## Contexto

`docs/tasks/TASK-008.md` (investigación) confirmó backlog #4 de `docs/integration-and-backlog.md`: dos endpoints sin control de pertenencia sobre `Proforma_Header`.

- **`InvoiceView.get`** ([custom_views/invoice.py:36-75](praxsa_manager/product/custom_views/invoice.py:36)) ya está protegido por `TokenAuthentication`+`IsAuthenticated` a nivel de clase — el problema es solo la falta de `.filter(created_by=...)`. `ListUserInvoice.get`, tres líneas más abajo en el mismo archivo, ya resuelve exactamente esto (`Proforma_Header.objects.filter(created_by=request.user.id)`, [invoice.py:100-101](praxsa_manager/product/custom_views/invoice.py:100)). Consumidor real: el cliente final vía Angular (`proforma.component.ts`, ruta `proforma/:id`), pidiendo su propia proforma por token.
- **`get_proforma_car_part_info`** ([views.py:153-194](praxsa_manager/product/views.py:153)) no tiene ningún chequeo de auth ni de pertenencia. Su único consumidor real en el repo es `nota_trabajo.js:25`, AJAX disparado desde el inline `ProformaDetailInLine` del admin de Django ([admin_config/nota_trabajo.py:24-27,103](praxsa_manager/product/admin_config/nota_trabajo.py:24)) — es decir, lo usa **staff armando la nota de trabajo de instalación**, no el cliente dueño de la proforma. La recomendación literal del backlog ("filtrar por pertenencia, mismo patrón que `ListUserInvoice`") no aplica aquí: un `created_by` casi nunca coincide con el staff que atiende la instalación, así que ese filtro dejaría la pantalla de nota de trabajo sin datos para prácticamente todos los casos reales.

El propio admin de proformas ya resuelve una versión de este problema para la carga de la página: `ProformaAdmin.get_queryset` ([admin_config/proforma_admin.py:191-197](praxsa_manager/product/admin_config/proforma_admin.py:191)) delega en `Proforma_Business.get_proforma_queryset_by_role` ([business/proforma.py:197-216](praxsa_manager/product/business/proforma.py:197)): el grupo `Admin` ve todas las proformas no borradas; cualquier otro staff solo ve las de la sucursal donde figura como `empleado`. Hoy esa protección solo cubre la carga de la página del admin — el endpoint AJAX `get_proforma_car_part_info` la ignora por completo y responde a cualquier `proforma_id`, autenticado o no.

`ADR-005` (TASK-006) ya estableció el precedente de "vista de función plana consumida solo por JS del admin de Django → chequeo manual `is_authenticated and is_staff`, sin migrar a DRF" para `get_bobina` ([views.py:45-47](praxsa_manager/product/views.py:45)), en vez de introducir `SessionAuthentication`/`IsAdminUser` de DRF sin un cliente real que lo necesite. `get_proforma_car_part_info` es el mismo tipo de consumidor (JS del admin, no cliente Angular), así que este ADR mantiene esa misma decisión de mecanismo — pero le suma el scoping por sucursal que `get_bobina` no necesitaba (una bobina no pertenece a un cliente ni tiene noción de "sucursal ajena" sensible de la misma forma que una proforma con datos de un cliente específico).

Restricciones de `docs/CLAUDE.md` relevantes: cambios pequeños, un objetivo por cambio; todo cambio de lógica de negocio lleva su test; evitar sobreingeniería.

## Decisión

Dos mecanismos distintos, uno por endpoint, según su consumidor real — consistente con el criterio ya usado en ADR-005.

### 1. `InvoiceView.get` → agregar filtro por `created_by`

Cambiar la consulta de `Proforma_Header.objects.select_related(...).get(id=pk)` a `Proforma_Header.objects.select_related(...).get(id=pk, created_by=request.user)`. Mismo patrón que `ListUserInvoice.get` en el mismo archivo. El bloque `except ObjectDoesNotExist: return Response('not found', 404)` que ya existe hoy cubre automáticamente el caso de "existe pero es de otro usuario" — no hace falta lógica nueva de manejo de errores, el filtro solo hace que ese `.get()` falle con `DoesNotExist` también en ese caso. Se elimina el código muerto comentado (`# if invoice.client_id.id == client.id: ...`), que referenciaba un campo inexistente.

### 2. `get_proforma_car_part_info` → chequeo de staff + scoping por sucursal/rol, reusando `get_proforma_queryset_by_role`

- Como primera línea de la vista: `if not (request.user.is_authenticated and request.user.is_staff): return JsonResponse({'error': True, 'message': 'not allowed'}, status=403)` — mismo chequeo que `get_bobina` (ADR-005), mismo idioma de respuesta (`JsonResponse` con `status`) que el resto del archivo.
- Reemplazar `Proforma_Header.objects.select_related(...).get(pk=proforma_id)` por el mismo mecanismo de scoping que ya usa `ProformaAdmin.get_queryset`: `Proforma_Business().get_proforma_queryset_by_role(user=request.user, qs=Proforma_Header.objects.select_related('sucursal', 'car_model_id'))`, y sobre ese resultado `.get(pk=proforma_id)`. Si el método devuelve `None` (usuario staff sin sucursal asignada) o el `.get()` no encuentra la fila dentro del queryset ya acotado (`DoesNotExist`), la vista responde **404** — sin distinguir "no existe" de "existe pero es de otra sucursal", para no revelar a un staff sin acceso que una proforma ajena existe.
- Esto reutiliza código ya probado (mismo método que protege hoy la página del admin de proformas) en vez de escribir una segunda implementación de la regla "`Admin` ve todo, el resto solo su sucursal" — evita el mismo tipo de duplicación de lógica que ya documenta `docs/integration-and-backlog.md` sección 2 como un riesgo recurrente del proyecto.
- Efecto secundario aceptado y correcto: `get_proforma_queryset_by_role` también excluye `is_delete=True` — una proforma borrada deja de ser visible para la nota de trabajo, consistente con cómo ya se comporta el admin.

No se propone tocar `get_inventory_window_film_reel_widths(request.user)` (la llamada interna que ya filtra por `sucursal__empleado=user`) ni el manejo de excepciones más allá de lo necesario para devolver 404 en el caso de acceso no autorizado — ambos quedan fuera de alcance de este ADR (ver Consecuencias).

## Alternativas consideradas

- **`get_proforma_car_part_info` con solo `is_authenticated and is_staff` (igual que `get_bobina`, sin scoping por sucursal)**: más simple (una línea), pero deja abierto que cualquier staff de cualquier sucursal vea proformas, precios e inventario de otra sucursal a la que no pertenece — exactamente el mismo tipo de problema que backlog #10 ya identificó para `PagosAdmin`/`ReportDailySellAdmin` y que el propio `ProformaAdmin` ya resuelve para su página. Descartada: dejaría una brecha de IDOR "más chica" (entre sucursales, no entre cualquiera) en vez de cerrarla, cuando la función para cerrarla ya existe y es una línea de más reusarla.
- **Escribir una función nueva de scoping específica para esta vista** (en vez de reusar `get_proforma_queryset_by_role`): descartada por duplicar una regla de negocio que ya vive en `business/proforma.py` y que se comprobó correcta en producción vía el admin — sobreingeniería innecesaria cuando el método existente ya recibe exactamente `(user, qs)` y devuelve lo que se necesita.
- **Migrar `get_proforma_car_part_info` a `APIView` de DRF con `SessionAuthentication`+`IsAdminUser`**: mismo argumento que ADR-005 descartó para `get_bobina` — el único consumidor es jQuery/AJAX desde una página ya autenticada por sesión de admin, no un cliente DRF. Introducir DRF aquí agregaría una cuarta forma de "endpoint protegido" sin un consumidor real que la necesite.
- **`InvoiceView.get` devolviendo `403` en vez de `404` para una proforma ajena**: se descarta a favor de `404` (ya es el comportamiento que produce el `except ObjectDoesNotExist` existente sin tocarlo) para no confirmarle a un cliente que un `pk` ajeno corresponde a una proforma real — mismo criterio de no-revelar-existencia aplicado a `get_proforma_car_part_info`.

## Estrategia de rollback / mitigación

Cambia autorización en dos endpoints de producción con consumidores reales (clientes Angular y staff del admin), así que aplica una estrategia explícita:

- **Riesgo principal (`InvoiceView.get`)**: si el filtro se aplicara mal (p. ej. comparando contra el `id` incorrecto), un cliente legítimo podría dejar de ver su propia proforma (falso negativo) en vez de solo bloquear el acceso ajeno.
  - **Mitigación previa**: test de caracterización con dos usuarios (A y B, cada uno con su propia proforma vía `create_full_proforma` de `tests/helpers.py`) que verifique tanto que A puede ver la suya como que A no puede ver la de B; verificación manual en el navegador logueado como cliente real, abriendo `proforma/<propio-id>`.
  - **Rollback**: cambio de código puro sin migraciones — `git revert` restaura el comportamiento anterior de inmediato.
- **Riesgo principal (`get_proforma_car_part_info`)**: si `get_proforma_queryset_by_role` devuelve `None`/vacío para un staff legítimo (p. ej. por un problema de asignación de sucursal ya documentado como posible en `ProformaAdmin.get_queryset`, que hoy maneja ese caso con un mensaje de error en el admin), la pantalla de nota de trabajo se quedaría sin poder cargar items para ese staff — rompería una herramienta operativa interna (instalación), no el flujo de clientes.
  - **Mitigación previa**: test con al menos tres escenarios (staff del grupo `Admin` viendo cualquier sucursal; staff de la sucursal correcta viendo su propia proforma; staff de otra sucursal recibiendo 404 sobre una proforma ajena) más verificación manual en el admin real: abrir la nota de trabajo de una proforma de la propia sucursal logueado como staff no-admin, confirmar que los items siguen cargando igual que antes del cambio.
  - **Rollback**: mismo mecanismo — cambio de código puro, revertible con `git revert` sin efectos secundarios en datos (no hay migración involucrada).
- **Riesgo transversal**: ambos endpoints pasan de "sin control" a "con control" en el mismo PR/ventana de despliegue — si algo sale mal, revertir ambos commits por separado es preferible a uno solo combinado, para poder aislar cuál de los dos causó el problema si aparece.

## Consecuencias

- **Más fácil**: se cierra el acceso cruzado a proformas ajenas por parte de clientes (`InvoiceView.get`) y el acceso sin ninguna sesión ni scoping a datos de precio/inventario/tipo de venta de cualquier proforma (`get_proforma_car_part_info`), reusando exclusivamente mecanismos que ya existían y estaban probados (`ListUserInvoice`'s filtro, `get_proforma_queryset_by_role`, el chequeo manual de `get_bobina`) — sin introducir ningún concepto nuevo de autenticación/autorización al proyecto.
- **Más difícil**: ninguna adicional a la ya aceptada en ADR-005 — este ADR no suma una cuarta forma de "endpoint protegido", reusa las tres ya existentes (token para clientes, chequeo manual de staff para vistas de función del admin, y ahora explícitamente el scoping por sucursal/rol para esa misma categoría cuando el dato es sensible por sucursal).
- **Deuda técnica aceptada conscientemente**: `get_inventory_window_film_reel_widths(request.user)` sigue recibiendo `request.user` sin relación con la sucursal de la proforma consultada (podría no coincidir con `proforma.sucursal` si algún día un staff de una sucursal atiende una nota de trabajo de otra por excepción) — no se toca en este ADR por ser un comportamiento preexistente e independiente del IDOR, fuera del alcance de backlog #4.
- **No resuelto por este ADR**: la distinción exacta entre `ObjectDoesNotExist` (404 limpio) y cualquier otra excepción inesperada dentro del `except Exception` amplio de `get_proforma_car_part_info` — se deja como detalle de implementación para `delivery-plan`/`delivery-engineer`, con la única restricción de que el caso "no autorizado o no existe" debe resultar en 404, no en el 500 genérico actual.
- **No resuelto por este ADR**: `get_car_part_info` (la otra vista pública sin auth mencionada en el backlog original SEC-03) sigue fuera de alcance — no forma parte de backlog #4.
