# ADR-005: Proteger get_inventory/get_layer_info con throttling (siguen públicos) y get_bobina con chequeo de staff

**Estado:** Propuesto
**Task relacionado:** TASK-006
**Fecha:** 2026-09-21

## Contexto

`docs/tasks/TASK-006.md` (investigación) confirmó que 7 vistas de función plana en `praxsa_manager/product/views.py` no tienen `@api_view`, por lo que nunca pasan por `REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES']` ([settings.py:119-125](praxsa_manager/praxsa_manager/settings.py:119)). De ese grupo, este ADR cubre las tres que el usuario pidió resolver explícitamente:

- **`get_calculator_info`/`get_model_parts`** quedan fuera de este ADR — el usuario ya confirmó que se mantienen públicos sin cambios.
- **`get_inventory`** ([views.py:195-223](praxsa_manager/product/views.py:195)) expone stock real (`bobina_metros_disponibles`) y precio real (`bobina_price`) por sucursal. Lo consume hoy la calculadora pública de `proforma` (`data.service.ts:69-71`, invocada desde `formulario.component.ts`, ruta raíz `''`, **sin** `AuthGuard`). El usuario confirmó en el chat: este endpoint debe **seguir siendo público**, no requerir login — "necesitamos que estos endpoint sean públicos pero solo de lectura". Se descartó explícitamente un esquema de "guest token" por no aportar control de acceso real (cualquiera lo obtendría igual, sin credenciales).
- **`get_layer_info`** ([views.py:187-193](praxsa_manager/product/views.py:187)) devuelve solo `name`/`content` (texto descriptivo, sin precio/stock) y también lo consume `proforma` sin login (`windows-film.service.ts:31`, ruta `/windows-film/:id`, sin `AuthGuard`). El usuario delegó esta decisión explícitamente a esta etapa.
- **`get_bobina`** ([views.py:37-52](praxsa_manager/product/views.py:37)) devuelve precio/ancho/largo de una bobina puntual. A diferencia de los otros dos, **no lo consume `proforma`** — su único consumidor es `inventario.js:32`, JS que solo se carga dentro de una página del admin de Django (`InventoryAdmin`, [admin_config/inventory.py:24](praxsa_manager/product/admin_config/inventory.py:24)) que ya exige sesión de staff para poder verse. El usuario delegó esta decisión a esta etapa también.

No existe throttling configurado hoy en el proyecto (sin `DEFAULT_THROTTLE_CLASSES`/`DEFAULT_THROTTLE_RATES` en `settings.py`). `djangorestframework==3.14.0` ([requirements-3.8.10.txt:15](praxsa_manager/requirements-3.8.10.txt:15)) incluye `AnonRateThrottle`/`ScopedRateThrottle` de fábrica, sin dependencia nueva. El propio `views.py` ya tiene un precedente de vista pública explícita hecha con DRF: `create_client` usa `@api_view(['POST'])` + `@permission_classes((permissions.AllowAny,))` ([views.py:305-313](praxsa_manager/product/views.py:305)) — mismo archivo, mismo estilo de función, declarando el acceso público de forma explícita en vez de depender del comportamiento por omisión de no tener `@api_view`.

Restricciones de `docs/CLAUDE.md` relevantes: cambios pequeños con un objetivo por cambio; todo cambio de lógica de negocio lleva su test; no agregar dependencias sin avisar.

## Decisión

Tres mecanismos distintos, uno por cada endpoint, según quién es su consumidor real:

### 1. `get_inventory` y `get_layer_info` → siguen públicos, se convierten a `@api_view` con `AllowAny` explícito + throttling

- Convertir ambas vistas de función plana a `@api_view(['GET'])`, devolviendo `Response(...)` de DRF en vez de `JsonResponse`, **preservando exactamente el mismo shape de datos** que ya consume `proforma` (mismas claves, mismos tipos) — esto es responsabilidad de verificación explícita en `delivery-plan`/`delivery-engineer`, no un detalle menor.
- Declarar `@permission_classes((permissions.AllowAny,))` explícitamente (mismo patrón que `create_client`) — documenta la intención de "público a propósito" en vez de depender de que la vista no tenga `@api_view`.
- Agregar `throttle_classes = (ScopedRateThrottle,)` con `throttle_scope = 'public_catalog'` a ambas vistas, y en `settings.py`: `REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {'public_catalog': '60/min'}`. Se elige `ScopedRateThrottle` (en vez de `AnonRateThrottle` genérico) para que el límite quede acotado a este grupo de endpoints y no se acople por accidente a la tasa `anon` global si en el futuro otra vista distinta también usa `AnonRateThrottle`.
- `60/min` por IP es un punto de partida conservador (una sesión normal de calculadora hace un puñado de llamadas, no docenas por minuto) pensado para frenar scraping/loops automatizados sin afectar el uso normal — **valor a ajustar con datos reales una vez desplegado**, no una cifra validada contra tráfico de producción.
- `get_calculator_info`/`get_model_parts` **no** se tocan en este ADR (fuera del alcance confirmado por el usuario), aunque conceptualmente podrían sumarse al mismo `throttle_scope` en un ADR/PR futuro si se decide.

### 2. `get_bobina` → sigue siendo una vista Django plana, se le agrega un chequeo explícito de staff

- No se convierte a DRF: su único consumidor real es una petición AJAX disparada desde una página del admin de Django ya protegida por sesión de staff — introducir `TokenAuthentication`/DRF ahí sería un mecanismo nuevo sin ningún cliente real que lo necesite.
- Se agrega, como primera línea de la vista: `if not (request.user.is_authenticated and request.user.is_staff): return JsonResponse({'error': True, 'message': 'not allowed'}, status=403)`. Se elige este chequeo manual en vez del decorador `staff_member_required` de Django porque ese decorador responde con una **redirección** (302 a `/admin/login/`) en vez de una respuesta JSON, lo cual no encaja con el resto del archivo — todas las demás vistas de `views.py` (incluida la propia `get_bobina`) ya devuelven errores como `JsonResponse`/`HttpResponseBadRequest` con un status code, nunca una redirección. El chequeo manual mantiene ese mismo idioma.
- Esto no cambia el flujo real hoy (un staff logueado en el admin sigue viendo la info exactamente igual); solo cierra el acceso directo a la URL sin esa sesión.

## Alternativas consideradas

- **Cerrar `get_inventory`/`get_layer_info` con `TokenAuthentication` + `IsAuthenticated`** (mismo patrón que `InvoiceView`): es el patrón ya probado en el proyecto, pero **rota el requerimiento de negocio confirmado** — la calculadora pública (`FormularioComponent`, sin `AuthGuard`) dejaría de funcionar para visitantes sin cuenta. Descartada por incompatible con el requerimiento, no por complejidad.
- **"Guest token" emitido automáticamente para visitantes anónimos**: evaluada y descartada en el chat con el usuario antes de esta etapa — no es control de acceso real (cualquiera lo obtiene sin credenciales), solo agregaría complejidad (emitir/almacenar/renovar un token) por una ganancia de solo trazabilidad, que el throttling por IP ya cubre de forma más simple para el problema real (scraping/abuso).
- **`get_bobina` con `APIView` + `SessionAuthentication` + `IsAdminUser`** (patrón DRF): técnicamente resolvería el mismo problema, pero introduce una segunda forma de "vista protegida" en el archivo sin ningún consumidor DRF real (el llamador es jQuery/AJAX desde una página del admin, no un cliente token-based). El chequeo manual `is_staff` logra el mismo resultado con una línea, sin nueva superficie de conceptos (autenticación DRF) para un endpoint que en la práctica solo sirve al propio admin de Django. Se prefiere por consistencia con el resto del archivo y por ser la opción más simple que resuelve el problema real (regla del proyecto de evitar sobreingeniería).
- **`get_bobina` con el decorador `staff_member_required` de Django**: descartada porque responde con una redirección HTML en vez de JSON ante un 401/403, inconsistente con el resto de las respuestas de error del archivo (ver Decisión).

## Estrategia de rollback / mitigación

Cambia autenticación/autorización en 3 endpoints de producción, así que aplica una estrategia explícita:

- **Riesgo principal (get_inventory/get_layer_info)**: convertir de `JsonResponse` a `Response` de DRF puede cambiar sutilmente el shape de la respuesta (headers, formato de errores no capturados, content negotiation vía `format_suffix_patterns` ya presente en `urls.py`) si no se replica con cuidado — rompería la calculadora pública en producción, el flujo de mayor tráfico del sitio.
  - **Mitigación previa**: `delivery-plan`/`delivery-engineer` deben escribir un test que capture el shape exacto de la respuesta actual (`inventario: [...]` / `layer: {...}`) antes de tocar código, y verificar manualmente en el navegador (calculadora y `/windows-film/:id`) que el comportamiento visible no cambia tras el fix.
  - **Rollback**: cambio de código puro, sin migraciones ni datos — `git revert` del commit correspondiente restaura el comportamiento anterior de inmediato.
- **Riesgo principal (get_bobina)**: si el chequeo de `is_staff` tiene algún error (p. ej. falla también para un staff legítimo, o la sesión no llega como se espera desde la petición AJAX), se rompería la carga de información de bobina dentro del admin de inventario — una herramienta operativa interna, no el flujo de clientes.
  - **Mitigación previa**: probar manualmente en el navegador que `InventoryAdmin` sigue mostrando la información de la bobina correctamente logueado como staff, y que un usuario no logueado (pestaña de incógnito) recibe 403 al pegarle directo a la URL.
  - **Rollback**: mismo mecanismo — cambio de código puro, revertible con `git revert` sin efectos secundarios en datos.
- **Riesgo transversal (throttling)**: una tasa mal calibrada (`60/min`) podría bloquear a un usuario legítimo con mala conexión que reintenta la calculadora varias veces, o resultar insuficiente para frenar abuso real.
  - **Mitigación**: el valor vive en `DEFAULT_THROTTLE_RATES`, un único punto de configuración en `settings.py` — ajustarlo no requiere tocar código de las vistas ni redesplegar lógica, solo cambiar el valor y reiniciar el proceso. Se recomienda revisar logs/métricas de 429 (`Too Many Requests`) en la primera semana post-despliegue.

## Consecuencias

- **Más fácil**: se cierra la exposición de datos real de stock/precio (`get_inventory`) y de bobina puntual (`get_bobina`) a scraping trivial, sin romper ningún flujo existente — ni la calculadora pública ni el admin.
- **Más difícil**: el proyecto pasa a tener tres formas distintas de "endpoint protegido" (`TokenAuthentication`+`IsAuthenticated` para clientes con cuenta, `AllowAny`+throttle para catálogo público, chequeo manual de `is_staff` para vistas de admin) en vez de una sola — se acepta conscientemente porque reflejan tres tipos de consumidor genuinamente distintos que ya existían en el código, no una fragmentación arbitraria.
- **Deuda técnica aceptada conscientemente**: la tasa de throttling (`60/min`) es una estimación inicial sin datos de tráfico real; puede necesitar ajuste. `get_calculator_info`/`get_model_parts` quedan sin throttling por ahora (fuera de alcance de este ADR) aunque son del mismo tipo de endpoint — candidatos a unificar en un ADR futuro si se decide.
- **No resuelto por este ADR**: `get_car_part_info` y `get_proforma_car_part_info` (las otras 2 de las 7 vistas del hallazgo original SEC-03) quedan fuera — `get_proforma_car_part_info` es backlog #4 (IDOR), no investigado en este task.
