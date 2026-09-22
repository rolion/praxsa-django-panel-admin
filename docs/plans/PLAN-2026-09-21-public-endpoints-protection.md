# PLAN-2026-09-21-public-endpoints-protection (v1)

**Task:** TASK-006
**ADRs relacionados:** [ADR-005](../adr/ADR-005-public-catalog-endpoints-protection.md)

## Objective

Cerrar la exposición de datos reales de stock/precio a través de `get_inventory` y de bobina puntual a través de `get_bobina` (backlog #5, backend SEC-03), sin romper la calculadora pública de `proforma` ni el panel de administración, aplicando el mecanismo que decidió `delivery-architect` en ADR-005: `get_inventory`/`get_layer_info` siguen públicos con throttling; `get_bobina` se cierra a staff.

## Context

`docs/tasks/TASK-006.md` (investigación + arquitectura) y [ADR-005](../adr/ADR-005-public-catalog-endpoints-protection.md) documentan el problema y la decisión completos. Resumen relevante para este plan:

- 7 vistas de función plana en `praxsa_manager/product/views.py` no tienen `@api_view`, así que nunca pasan por `REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES']`.
- De esas 7, este task cubre solo 3: `get_inventory`, `get_layer_info`, `get_bobina`. `get_calculator_info`/`get_model_parts` quedan sin cambios (confirmado público). `get_car_part_info`/`get_proforma_car_part_info` quedan fuera (la segunda es backlog #4, IDOR, no investigado aquí).
- `get_inventory` lo consume la calculadora pública de `proforma` sin login; `get_layer_info` lo consume la ruta pública `/windows-film/:id`, también sin login. Ambos deben seguir siendo alcanzables sin autenticación — decisión de negocio confirmada por el usuario.
- `get_bobina` no lo consume `proforma` en absoluto — su único consumidor es `inventario.js`, cargado solo dentro de una página del admin de Django ya protegida por sesión de staff.

## Current behavior

- `get_bobina(request, pk)` — [views.py:37-52](../../praxsa_manager/product/views.py) — función Django plana, sin `@api_view`, devuelve `JsonResponse({'bobina': {...}})` con `window_film`, `width`, `length`, `price`. Alcanzable sin autenticación hoy.
- `get_layer_info(request, layer_id)` — [views.py:187-193](../../praxsa_manager/product/views.py) — devuelve `JsonResponse({'layer': {'name', 'content'}})`. Alcanzable sin autenticación hoy.
- `get_inventory(request, sucursal_id, lamina_id, width)` — [views.py:195-223](../../praxsa_manager/product/views.py) — devuelve `JsonResponse({'inventario': [{'bobina_film_name', 'bobina_film_id', 'bobina_width', 'bobina_metros_disponibles', 'bobina_price', 'bobina_id'}, ...]})`. Alcanzable sin autenticación hoy.
- `praxsa_manager/praxsa_manager/settings.py:119-125` — `REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES']` existe pero nunca corre sobre estas 3 vistas (no son DRF). No hay `DEFAULT_THROTTLE_CLASSES`/`DEFAULT_THROTTLE_RATES` configurados en absoluto.
- `praxsa_manager/product/urls.py:11-24` — rutas `bobina/<pk>`, `layer/<layer_id>`, `get_inventory/<sucursal_id>/<lamina_id>/<width>`, envueltas en `format_suffix_patterns` al final del archivo.
- Precedente ya existente en el mismo archivo: `create_client` ([views.py:305-313](../../praxsa_manager/product/views.py)) usa `@api_view(['POST'])` + `@permission_classes((permissions.AllowAny,))` — mismo estilo de función DRF explícita que se va a replicar aquí.

## Expected behavior

- `get_inventory`/`get_layer_info`: siguen respondiendo 200 con el mismo shape de datos, sin requerir autenticación, pero ahora limitadas a `60` peticiones por minuto por IP (`429 Too Many Requests` al superarlo).
- `get_bobina`: responde 200 igual que hoy **solo** si `request.user.is_authenticated and request.user.is_staff` (sesión de admin de Django); responde `403` con `{'error': True, 'message': 'not allowed'}` en cualquier otro caso.

## Architecture considerations

Resumen de ADR-005 (ver documento completo para alternativas descartadas y rollback):
- **Contrato API**: `get_inventory`/`get_layer_info` deben preservar el shape de respuesta exacto al migrar de `JsonResponse` a `Response` de DRF — es el riesgo principal de este plan.
- **Auth/permisos**: 3 mecanismos distintos coexistiendo a propósito (token+IsAuthenticated para `InvoiceView`, AllowAny+throttle para catálogo público, chequeo manual de staff para `get_bobina`) — reflejan 3 tipos de consumidor reales, no fragmentación arbitraria.
- **Infraestructura**: ninguna — no se agrega dependencia (DRF 3.14.0 ya trae `ScopedRateThrottle`), no se toca Docker/despliegue.
- **Acoplamiento**: `format_suffix_patterns` ya envuelve `urls.py` — verificar en implementación que las nuevas vistas `@api_view` no cambian el comportamiento de esa envoltura (no debería, es el patrón estándar de DRF).

## Proposed solution

1. **`get_inventory` y `get_layer_info`** → `@api_view(['GET'])`, `@permission_classes((permissions.AllowAny,))`, `@throttle_classes((ScopedRateThrottle,))` con `throttle_scope = 'public_catalog'` fijado como atributo de la función (DRF permite setear `.throttle_scope` en la función decorada, o envolver con una vista mínima; a confirmar el mecanismo exacto de function-based view durante la implementación — DRF soporta `throttle_scope` como atributo asignable a la función decorada con `@api_view`). Reemplazar `JsonResponse(data=X, safe=False)` por `Response(data=X)`, preservando las mismas claves/tipos.
2. **`settings.py`**: agregar `'DEFAULT_THROTTLE_RATES': {'public_catalog': '60/min'}` dentro del diccionario `REST_FRAMEWORK` ya existente ([settings.py:119-125](../../praxsa_manager/praxsa_manager/settings.py)).
3. **`get_bobina`**: agregar como primera línea del `try` (o antes de él): `if not (request.user.is_authenticated and request.user.is_staff): return JsonResponse({'error': True, 'message': 'not allowed'}, status=403)`. No se convierte a DRF — sigue siendo una vista Django plana, solo gana el chequeo.
4. Tests de caracterización + del nuevo comportamiento (ver Test strategy).
5. Verificación manual en navegador (calculadora, `/windows-film/:id`, admin de inventario) antes de dar por cerrado el paso de implementación.

## Files/components affected

**Backend:**
- `praxsa_manager/product/views.py` — `get_inventory`, `get_layer_info`, `get_bobina`.
- `praxsa_manager/praxsa_manager/settings.py` — `REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']`.
- `praxsa_manager/product/tests/test_smoke.py` (o un archivo nuevo `test_public_catalog_endpoints.py` en el mismo paquete `praxsa_manager/product/tests/`) — nuevos tests.
- `praxsa_manager/product/tests/helpers.py` — agregar un helper `create_staff_user_with_session` (o similar) si no existe ya forma de crear un usuario staff logueado por sesión para el test de `get_bobina`.

**Frontend:** ninguno — este task no toca `proforma/`, el contrato de respuesta se mantiene idéntico.

## Implementation steps

1. Agregar `'DEFAULT_THROTTLE_RATES': {'public_catalog': '60/min'}` a `REST_FRAMEWORK` en `settings.py`.
2. Escribir un test de caracterización que documente el shape actual de `get_inventory` y `get_layer_info` (antes de tocar las vistas), usando `helpers.build_full_scenario()`.
3. Convertir `get_inventory` a `@api_view(['GET'])` + `AllowAny` + `ScopedRateThrottle(throttle_scope='public_catalog')`, devolviendo `Response` con el mismo shape. Correr el test del paso 2 y confirmar que sigue pasando sin cambios.
4. Repetir el paso 3 para `get_layer_info`.
5. Agregar el chequeo manual de `is_staff` a `get_bobina` (sin convertir a DRF).
6. Escribir los tests nuevos: anónimo obtiene 200 en `get_inventory`/`get_layer_info`; se supera el throttle y se obtiene 429 (con la tasa sobreescrita a un valor bajo en el test); anónimo obtiene 403 en `get_bobina`; usuario autenticado no-staff obtiene 403; usuario staff obtiene 200.
7. Verificación manual: levantar el backend (`python manage.py runserver`) y el frontend (`ng serve`), navegar a la calculadora (`/`) sin login y confirmar que sigue mostrando precios/stock; navegar a `/windows-film/:id` sin login; loguearse en `/admin/`, abrir `InventoryAdmin` y confirmar que la info de bobina se sigue cargando; con `curl`/Postman sin sesión, pegarle directo a `/product/bobina/<pk>` y confirmar 403.

## Test strategy

Nivel: **integración de backend** (Django `TestCase` + `self.client`, mismo patrón que `test_smoke.py`). No corresponde nivel unitario aislado adicional — la lógica es enteramente de la capa de vista/permisos, no hay lógica de negocio compleja que aislar.

Casos concretos:
- `get_inventory` sin autenticación → 200, shape idéntico al actual (`{'inventario': [...]}` con las mismas claves).
- `get_layer_info` sin autenticación → 200, shape idéntico (`{'layer': {'name', 'content'}}`).
- `get_inventory`/`get_layer_info`: al superar la tasa configurada → 429. Para que el test sea determinístico y rápido, sobreescribir `DEFAULT_THROTTLE_RATES['public_catalog']` a un valor bajo (p. ej. `'2/min'`) vía `@override_settings` solo en ese test, y limpiar el cache de throttling (`django.core.cache.cache.clear()`) en `setUp`/`tearDown` para no contaminar otros tests.
- `get_bobina` sin autenticación → 403.
- `get_bobina` con usuario autenticado pero `is_staff=False` → 403.
- `get_bobina` con usuario `is_staff=True` (vía sesión, `self.client.login(...)` o forzando `is_staff=True` en el helper) → 200, shape idéntico al actual.

**¿Corresponde E2E (Playwright)? No.** Este cambio no toca ningún archivo de `proforma/` — es puramente backend (permisos/throttling sobre 3 vistas ya existentes), y el contrato de respuesta que consume el frontend se mantiene idéntico por diseño. Un test de integración de Django que verifique status code + shape cubre completamente el riesgo real (que la respuesta cambie de forma), y la verificación manual del paso 7 cubre la integración real con el frontend sin necesidad de automatizarla con un browser real. Agregar Playwright para esto sería desproporcionado al cambio.

## Acceptance criteria

- [ ] `get_inventory` y `get_layer_info` responden 200 sin autenticación, con el mismo shape de datos que hoy.
- [ ] `get_inventory` y `get_layer_info` responden 429 al superar la tasa configurada.
- [ ] `get_bobina` responde 403 para cualquier request sin sesión de staff, y 200 (shape idéntico al actual) para una sesión de staff válida.
- [ ] La calculadora pública (`/`) y la ruta `/windows-film/:id` de `proforma` siguen funcionando sin login, verificado manualmente en navegador.
- [ ] El panel de administración (`InventoryAdmin`) sigue cargando la info de bobina correctamente, verificado manualmente logueado como staff.
- [ ] Todos los tests nuevos y existentes de `praxsa_manager/product/tests/` pasan.
- [ ] `python manage.py makemigrations --check --dry-run` no reporta migraciones pendientes (este cambio no toca modelos, así que no debería generar ninguna).

## Risks

- **Cambiar `JsonResponse` por `Response` de DRF puede alterar sutilmente el shape/headers de la respuesta** si no se replica con cuidado — mitigado por el test de caracterización del paso 2 (correr antes y después del cambio) y la verificación manual del paso 7.
- **La tasa de throttling (`60/min`) es una estimación sin datos de tráfico real** — puede resultar muy laxa (no frena scraping real) o, menos probable, molestar a un usuario legítimo con una sesión de calculadora inusualmente larga. Mitigación: es un único valor en `settings.py`, ajustable sin tocar código de vistas; revisar logs de 429 en la primera semana post-despliegue (ya documentado en ADR-005).
- **El chequeo manual de `is_staff` en `get_bobina` podría tener un caso borde no cubierto** (p. ej. un superusuario sin `is_staff=True` explícito, aunque en Django `is_superuser` no implica `is_staff` automáticamente salvo que se setee) — mitigado por los tests explícitos de los 3 casos (anónimo, autenticado no-staff, staff).

## Out of scope

- `get_car_part_info` y `get_proforma_car_part_info` (las otras 2 de las 7 vistas del hallazgo SEC-03 original) — la segunda es backlog #4 (IDOR), no cubierta por TASK-006.
- Unificar `get_calculator_info`/`get_model_parts` bajo el mismo `throttle_scope` — mencionado como posible mejora futura en ADR-005, no parte de este plan.
- Ajustar la tasa de throttling con datos reales de producción — se revisa después del despliegue, no antes.

## Dependencias nuevas

Ninguna — `djangorestframework==3.14.0` (ya instalado) incluye `ScopedRateThrottle` de fábrica.
