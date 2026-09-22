# TASK-006: Cerrar endpoints públicos que exponen stock/precio (backlog #5)

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Rama:** `claude/public-endpoints-pii-storage-ff52d6` (compartida con TASK-004, por decisión explícita del usuario — ver historial)
**Pull Request:** https://github.com/rolion/praxsa-django-panel-admin/pull/30 (combinado con TASK-004, por decisión explícita del usuario)
**Renombrado de:** TASK-002/ADR-002 → TASK-006/ADR-005 el 2026-09-22, por colisión de IDs contra `master` (ver historial e informe de `delivery-publish` en el PR)

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-09-21 | (nuevo) → INVESTIGATION | Task creado a partir del ítem #5 de docs/integration-and-backlog.md, con decisión de negocio ya tomada por el usuario: mantener `calculator_info`/`model_parts` públicos, cerrar `get_inventory`, y decidir `get_bobina`/`get_layer_info` | delivery-investigate |
| 2026-09-21 | INVESTIGATION → PLANNING | Decisión arquitectónica tomada (ADR-005): `get_inventory`/`get_layer_info` siguen públicos, se agregan `AllowAny` explícito + `ScopedRateThrottle` (`60/min`); `get_bobina` se cierra con chequeo manual de `is_staff` (no se consume desde `proforma`) | delivery-architect |
| 2026-09-21 | PLANNING → ENGINEERING | Plan v1 escrito (PLAN-2026-09-21-public-endpoints-protection.md). Usuario decidió explícitamente reusar la rama existente del worktree en vez de crear `task/TASK-006-...`, y combinar TASK-006+TASK-004 en un único PR (se aparta de la regla de "un PR por task" del skill, por decisión explícita) | delivery-plan |
| 2026-09-21 | ENGINEERING → REVIEW | Implementación completa según el plan v1, commit e4bdf62 empujado al PR #30. Un desvío menor documentado (AnonRateThrottle con scope fijo en vez de ScopedRateThrottle, porque `@api_view` no reenvía `throttle_scope`) — no cambia alcance ni riesgo, resuelto directamente sin escalar | delivery-engineer |
| 2026-09-21 | REVIEW → ENGINEERING | Veredicto FAIL — REV-2026-09-21-002 (IMPLEMENTATION, High): el monkeypatch de `SimpleRateThrottle.THROTTLE_RATES` en `PublicCatalogThrottleTest` no restaura la tasa real al terminar la clase, contamina el resto del proceso de test. Confirmado empíricamente por `delivery-review` con un test temporal (3 de 5 peticiones normales recibieron 429). Se investigó también una hipótesis de bypass del throttle para usuarios autenticados — descartada, no es un problema real | delivery-review |
| 2026-09-21 | ENGINEERING → REVIEW | Fix de REV-2026-09-21-002 aplicado (commit 78c6ebc): la tasa real se captura como constante de módulo al importar el archivo (antes de cualquier `override_settings`) y se restaura desde ahí en `tearDown`, en vez de releerla de `api_settings` mientras el override sigue activo. Verificado con un test temporal (no comiteado): ya no hay fuga, la tasa real (`60/min`) se restaura correctamente. `python manage.py test product` → 13/13 OK | delivery-engineer |
| 2026-09-22 | REVIEW → ENGINEERING | Veredicto FAIL (segunda ronda de review, sesión nueva sin contexto previo) — REV-2026-09-22-001 (Medium, IMPLEMENTATION): verificación manual en navegador de calculadora/windows-film/InventoryAdmin (acceptance criteria del plan) sigue sin ejecutarse, bloqueada en este entorno por la política de acceso a credenciales al intentar levantar runserver+ng serve con datos reales. REV-2026-09-22-002 (Low, IMPLEMENTATION, no bloqueante por sí solo): PublicCatalogThrottle no aplica a sesiones de Django autenticadas (solo afecta a staff vía /admin/, sin vía de bypass para el público anónimo). Confirmado y resuelto de forma independiente: REV-2026-09-21-002 (throttle-rate-test-leak) — re-verificado con test temporal propio, la tasa se restaura correctamente a 60/min sin fuga | delivery-review |
| 2026-09-22 | ENGINEERING → PUBLISH | Veredicto PASS (tercera ronda, misma sesión) — el usuario copió el .env real y asignó el grupo admin a un staff existente; con eso se completó en vivo la verificación manual en navegador que dejaba abierto REV-2026-09-22-001 (ahora Resuelto, evidencia completa en el archivo): calculadora pública, /windows-film/:id y get_bobina (403 anónimo / 200 staff en InventoryAdmin) confirmados con datos reales. REV-2026-09-22-002 (Low) queda abierto pero no bloqueante | delivery-review |
| 2026-09-22 | PUBLISH (renumeración) | delivery-publish detectó PR #30 en mergeable=CONFLICTING: master ya tenia TASK-002/ADR-002 propios (PR #32, tarea no relacionada). Renombrado TASK-002→TASK-006, ADR-002→ADR-005, referencias cruzadas actualizadas (commit 7ac1e56), master mergeado resolviendo el unico conflicto real en tests/helpers.py (commit 57a95b7). Suite completa re-corrida: 46/46 OK. PR ahora mergeable=MERGEABLE | delivery-publish |

## Investigación

### Requerimiento

Ejecutar el ítem #5 del backlog (`docs/integration-and-backlog.md:167-173`, backend SEC-03): 7 vistas de función plana en `praxsa_manager/product/views.py` sin `@api_view`, por lo que nunca pasan por `REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES']` ni por ningún control de autenticación.

El usuario ya resolvió parte de la pregunta de negocio abierta en la sección 6 del backlog ("¿cuáles son intencionalmente públicos?"):
- **Confirmado público**: `get_calculator_info` (ruta `calculator_info`) y `get_model_parts` (ruta `model_parts/<id>`) — quedan como están, sin cambios.
- **`get_inventory`** (ruta `get_inventory/<sucursal>/<lamina>/<width>`) — expone stock y precio real por sucursal. Petición inicial: "cerrar". **Revisado en conversación posterior (2026-09-21)**: el usuario aclaró que `proforma` (el frontend) llama a este endpoint para la calculadora pública y el usuario final **no debe necesitar estar logueado** para obtenerlo — "cerrar" no puede significar `IsAuthenticated` sin romper ese flujo. Pidió explícitamente que el endpoint **siga siendo público, pero de solo lectura**. Se evaluaron dos mecanismos en el chat:
  - **Guest token/sesión de invitado emitida automáticamente**: descartado como control de acceso real — si cualquier visitante puede obtenerlo sin credenciales, el acceso a los datos no cambia respecto a hoy; solo aportaría trazabilidad/revocación individual, no evita que cualquiera consulte precio/stock real.
  - **Throttling (limitar tasa de peticiones)**: mantiene el endpoint público y de solo lectura como pide el usuario, mitigando scraping/abuso masivo sin romper el flujo de la calculadora para un usuario normal. Es la dirección que el usuario aprobó explícitamente ("necesitamos que estos endpoint sean públicos pero solo de lectura").
  
  Nota de alcance: la aclaración del usuario sobre "estos endpoint" surgió a partir de la pregunta sobre `get_inventory`, que es el único de este grupo que hoy consume `proforma` desde una ruta sin login (junto con `get_layer_info`, ver abajo). No se confirmó explícitamente si también aplica a `get_bobina`, que **no** es consumido por `proforma` (ver hechos encontrados) — se mantiene como decisión separada.
- **Pendiente de decidir**: `get_bobina` (ruta `bobina/<pk>`, sin consumidor en `proforma`) y, dado el nuevo criterio de "público pero de solo lectura", confirmar si `get_layer_info` (ruta `layer/<layer_id>`, sí consumido por `proforma` en una ruta sin login) entra en el mismo tratamiento que `get_inventory` (público + throttling) en vez de requerir auth.

Nota: de las 7 vistas listadas en el backlog, `get_car_part_info` y `get_proforma_car_part_info` no forman parte de este task — `get_proforma_car_part_info` ya está cubierto por el backlog #4 (IDOR, no investigado aquí) y `get_car_part_info` no fue mencionado por el usuario en el alcance de este pedido.

### Hechos encontrados

- Las 7 vistas son funciones Django planas que devuelven `JsonResponse`/`HttpResponseBadRequest`, no `Response` de DRF, y ninguna tiene el decorador `@api_view` — [views.py:37](praxsa_manager/product/views.py:37) (`get_bobina`), [views.py:54](praxsa_manager/product/views.py:54) (`get_car_part_info`), [views.py:143](praxsa_manager/product/views.py:143) (`get_proforma_car_part_info`), [views.py:187](praxsa_manager/product/views.py:187) (`get_layer_info`), [views.py:195](praxsa_manager/product/views.py:195) (`get_inventory`), [views.py:226](praxsa_manager/product/views.py:226) (`get_calculator_info`), [views.py:287](praxsa_manager/product/views.py:287) (`get_model_parts`).
- `praxsa_manager/praxsa_manager/settings.py:119-125` — `REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'] = ['rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly']`. Esta config solo se aplica a vistas DRF (`@api_view`/`APIView`); como estas 7 vistas no lo son, el setting nunca corre sobre ellas — confirma el mecanismo exacto que describe SEC-03.
- `praxsa_manager/product/urls.py:11-24` — rutas: `get_car_part_info/<car_model_id>/<sucursal_id>`, `get_proforma_car_part_info/<proforma_id>`, `calculator_info`, `model_parts/<model_id>`, `get_inventory/<sucursal_id>/<lamina_id>/<width>`, `bobina/<pk>`, `layer/<layer_id>` — todas sin ningún middleware/decorador de auth adicional a nivel de URL.
- **Patrón existente de vista autenticada en este mismo módulo**: `InvoiceView`/`ListUserInvoice` en [custom_views/invoice.py:15-18](praxsa_manager/product/custom_views/invoice.py:15-18) usan `APIView` con `authentication_classes = [authentication.TokenAuthentication]` y `permission_classes = [permissions.IsAuthenticated]` — es el único ejemplo de "endpoint cerrado" ya implementado en el proyecto, pensado para clientes del frontend Angular que mandan el token de `localStorage`.
- **`get_inventory` es consumido hoy por la calculadora pública, sin login**: `proforma/src/app/service/data.service.ts:69-71` (`getInventario`) llama a `GET /product/get_inventory/...` sin adjuntar token explícito en `httpOptions` (aunque el `AuthInterceptor` global sí adjunta el header `Authorization` si hay un token guardado, ver más abajo). Es invocado desde [formulario.component.ts:86](proforma/src/app/pages/formulario/formulario.component.ts:86) y [formulario.component.ts:234](proforma/src/app/pages/formulario/formulario.component.ts:234), componente que vive en la ruta raíz `{ path: '', component: FormularioComponent }` ([app-routing.module.ts:18](proforma/src/app/app-routing.module.ts:18)) — **sin `canActivate: [AuthGuard]`**, a diferencia de `/proforma/:id` y `/my-invoice` que sí lo tienen ([app-routing.module.ts:19,24](proforma/src/app/app-routing.module.ts:19)). `FormularioComponent` tampoco hace ningún chequeo manual de `currentUser` en su `ngOnInit` ([formulario.component.ts:120-129](proforma/src/app/pages/formulario/formulario.component.ts:120)).
- `proforma/src/app/app.module.ts` registra `AuthInterceptor` globalmente vía `HTTP_INTERCEPTORS` (confirmado en `docs/frontend-audit.md:62`), que adjunta `Authorization: Token {token}` a **toda** petición saliente si hay un token en `localStorage` — pero un visitante que nunca hizo login no tiene token, por lo que la llamada a `get_inventory` sale sin ese header.
- **`get_bobina` no es consumido por el frontend Angular en absoluto** (sin coincidencias al buscar `bobina/` ni `getBobina` en `proforma/src`). Su único consumidor conocido es `praxsa_manager/product/static/product/inventario.js:32` (`url: '/product/bobina/'+bobina_id`), JS que se carga exclusivamente en el panel de administración Django vía `Media.js` de `InventoryAdmin` — [admin_config/inventory.py:24](praxsa_manager/product/admin_config/inventory.py:24). Ese JS corre en una página que ya requiere sesión de staff de Django (`SessionAuthentication`/login de admin) para poder verla — pero la llamada AJAX en sí misma pega directo al endpoint sin pasar por ningún control adicional, así que hoy es alcanzable sin sesión por cualquiera que conozca la URL.
- **`get_layer_info` es consumido por la ruta pública `/windows-film/:id`**: `proforma/src/app/service/pybackend/film/windows-film.service.ts:31` llama `GET /product/layer/{id}` sin token en `httpOptions`. La ruta `{ path: 'windows-film/:id', component: WindowsFilmComponent }` ([app-routing.module.ts:25](proforma/src/app/app-routing.module.ts:25)) **no tiene** `canActivate: [AuthGuard]`.
- `windows-film.component.ts:38` (`this.windowsFilmDao = res.layer;`) confirma que el frontend **sí** desenvuelve la respuesta bajo la clave `layer` correctamente — el "hallazgo probable" de `docs/integration-and-backlog.md:124` (mismatch `get_layer_info`/`WindowsFilmService` sin confirmar al 100%) queda descartado: no hay mismatch, el componente lee `res.layer` tal como lo devuelve el backend ([views.py:190](praxsa_manager/product/views.py:190)).
- `get_bobina` devuelve `window_film`, `width`, `length`, `price` de una bobina puntual ([views.py:41-47](praxsa_manager/product/views.py:41)); `get_layer_info` devuelve solo `name` y `content` (texto descriptivo de la lámina, [views.py:190](praxsa_manager/product/views.py:190)) — no expone precio ni stock, a diferencia de `get_bobina` y `get_inventory`.
- El `AuthGuard` existente ([guards/auth.guard.ts:8-18](proforma/src/app/guards/auth.guard.ts:8)) solo verifica `this.auth.getUser()` (presencia de `token` en `localStorage`), sin round-trip al backend ni verificación de expiración.
- **No hay throttling configurado hoy**: no existe `DEFAULT_THROTTLE_CLASSES` ni `DEFAULT_THROTTLE_RATES` en `praxsa_manager/praxsa_manager/settings.py:119-125` (ni en ningún otro lado del `REST_FRAMEWORK` config) — ningún endpoint del proyecto tiene límite de tasa hoy. `requirements-3.8.10.txt:15` fija `djangorestframework==3.14.0`, versión que incluye `AnonRateThrottle`/`UserRateThrottle`/`ScopedRateThrottle` de fábrica (`rest_framework.throttling`), sin necesidad de agregar una dependencia nueva. Como las vistas en cuestión hoy son funciones planas (no `@api_view`), el throttling de DRF tampoco se les aplicaría automáticamente sin antes convertirlas a vistas DRF — mismo paso previo que ya haría falta para agregar auth.

### Hipótesis / supuestos no confirmados

- No se confirmó si existe algún otro consumidor de `get_bobina`/`get_layer_info`/`get_inventory` fuera de este repo (p. ej. una app móvil o integración externa) — solo se verificó el uso dentro de `proforma/` y `praxsa_manager/product/static`.
- No se confirmó si cerrar `get_bobina` con autenticación de sesión Django (`SessionAuthentication` + `IsAdminUser`, el mecanismo que ya protege la página del admin donde vive `inventario.js`) es compatible tal cual con cómo jQuery hace la petición AJAX en ese archivo (p. ej. si el navegador ya envía la cookie de sesión sin cambios adicionales) — no se probó en runtime.
- No se confirmó con el usuario si la intención de "decidir get_layer_info" incluye also proteger la ruta `/windows-film/:id` en el frontend con `AuthGuard` (rompería la posibilidad de compartir el link de una lámina sin estar logueado) o si se prefiere mantenerla pública dado que no expone precio/stock.

### Módulos y dependencias relacionadas

- **Backend**: `praxsa_manager/product/views.py` (las 7 vistas), `praxsa_manager/product/urls.py` (rutas), `praxsa_manager/product/custom_views/invoice.py` (patrón de vista autenticada a reusar como referencia), `praxsa_manager/praxsa_manager/settings.py:119-125` (`REST_FRAMEWORK` defaults).
- **Backend, consumidor admin**: `praxsa_manager/product/static/product/inventario.js`, `praxsa_manager/product/admin_config/inventory.py` (`InventoryAdmin.Media`).
- **Frontend**: `proforma/src/app/service/data.service.ts` (`getInventario`), `proforma/src/app/pages/formulario/formulario.component.ts` (calculadora pública), `proforma/src/app/service/pybackend/film/windows-film.service.ts` y `proforma/src/app/pages/windows-film/windows-film.component.ts`, `proforma/src/app/app-routing.module.ts`, `proforma/src/app/guards/auth.guard.ts`.

### Implementaciones similares existentes

`InvoiceView`/`ListUserInvoice` ([custom_views/invoice.py](praxsa_manager/product/custom_views/invoice.py)) son el único patrón ya probado en el proyecto para cerrar un endpoint a clientes del frontend Angular: `APIView` + `TokenAuthentication` + `IsAuthenticated`. Ese patrón encaja para `get_inventory` (mismo tipo de consumidor: Angular con token de usuario final) pero **no** encaja directamente para `get_bobina` (consumido por sesión de staff del admin, no por token de cliente final) — no hay un ejemplo existente en el código de "endpoint DRF protegido por sesión de admin de Django"; el admin de Django resuelve sus propios permisos vía `ModelAdmin`, no vía vistas de función.

### Comportamiento actual

Hoy, cualquiera con la URL (autenticado o no) puede:
- Leer `GET /product/get_inventory/<sucursal>/<lamina>/<width>` y obtener stock disponible (`bobina_metros_disponibles`) y precio de venta real (`bobina_price`) por sucursal.
- Leer `GET /product/bobina/<pk>` y obtener el precio/ancho/largo de una bobina puntual del inventario, iterando `pk` secuencialmente.
- Leer `GET /product/layer/<layer_id>` y obtener nombre y contenido descriptivo de una lámina (sin precio/stock).

`calculator_info` y `model_parts/<id>` también son alcanzables sin auth hoy, pero eso ya fue confirmado como comportamiento intencional por el usuario (son datos de referencia: marcas, modelos, piezas, láminas — no precios por sucursal ni stock).

### Restricciones

- `docs/CLAUDE.md`: "Antes de cambios que afecten varios archivos, proponer un plan y esperar confirmación"; "Todo cambio de lógica de negocio lleva su test"; "No agregar dependencias sin avisar antes".
- El backlog (`docs/integration-and-backlog.md:169`) ya anticipa que cada endpoint necesita "un test que documente si debe seguir siendo público o no".

### Riesgos identificados

- ~~Cerrar `get_inventory` con `IsAuthenticated` rompía el flujo público de la calculadora~~ — **resuelto por decisión de negocio (2026-09-21)**: el usuario confirmó que `get_inventory` debe seguir siendo público/de solo lectura, no requerir login. Queda pendiente para `delivery-architect` diseñar el mecanismo concreto de mitigación (throttling propuesto en el chat; ver hecho sobre `AnonRateThrottle` arriba) y decidir los valores/alcance del límite de tasa — eso sigue siendo una decisión de diseño, no trivial, aunque ya no compite con la necesidad de negocio.
- Mismo razonamiento aplicaría a `get_layer_info` si se confirma que debe recibir el mismo tratamiento que `get_inventory` (pendiente de decidir explícitamente, ver Requerimiento) — evitaría romper la ruta pública `/windows-film/:id`.
- `get_bobina` **no** está confirmado dentro del alcance de "público pero de solo lectura" (no lo consume `proforma`, solo el JS del admin) — sigue necesitando un mecanismo de autenticación distinto al resto (sesión de staff de Django, no token de cliente final), sin precedente en el código para ese patrón específico en una vista de función fuera del admin. Esta sigue siendo la decisión arquitectónica más abierta del task.
- Convertir estas vistas de función plana a `@api_view`/`APIView` (paso previo necesario tanto para aplicar throttling como para cualquier auth) es en sí mismo un cambio de forma de las vistas — a verificar que no rompa el shape de las respuestas (`JsonResponse` vs `Response` de DRF) que ya consume el frontend.
- Ninguna de las 7 vistas tiene tests hoy (`product/tests.py` es boilerplate, según backlog #8) — cualquier cambio de comportamiento no tiene red de seguridad automatizada todavía.

### Veredicto de complejidad

**NEEDS_ARCHITECTURE** — aunque la aclaración de negocio del 2026-09-21 eliminó el conflicto más grave (cerrar `get_inventory` rompiendo la calculadora pública), el task sigue involucrando cambios de autenticación/autorización en múltiples endpoints (indicador explícito de `delivery-architect`): `get_bobina` requeriría un mecanismo de auth sin precedente en el código (sesión de admin vs. token de cliente), y `get_inventory`/`get_layer_info` requieren diseñar un esquema de throttling nuevo en el proyecto (clases, tasas, alcance) además de convertir las vistas de función plana a vistas DRF. No es un simple "agregar `@api_view` + `IsAuthenticated`" como en el patrón ya existente de `InvoiceView`.

## Arquitectura

Decisión registrada en [ADR-005](../adr/ADR-005-public-catalog-endpoints-protection.md):

- `get_inventory` y `get_layer_info`: **siguen públicos** (sin login) — se convierten a `@api_view(['GET'])` con `permission_classes=(AllowAny,)` explícito y `ScopedRateThrottle` (`throttle_scope='public_catalog'`, `60/min` inicial vía `DEFAULT_THROTTLE_RATES`).
- `get_bobina`: se cierra con un chequeo manual `is_authenticated and is_staff` al inicio de la vista (403 JSON si falla) — no se convierte a DRF, dado que su único consumidor es el JS del admin de Django, no `proforma`.
- `get_calculator_info`/`get_model_parts` quedan sin cambios (confirmado público, fuera de alcance).
- `get_car_part_info`/`get_proforma_car_part_info` quedan fuera de este task (la segunda es backlog #4, IDOR).

## Plan

[PLAN-2026-09-21-public-endpoints-protection.md](../plans/PLAN-2026-09-21-public-endpoints-protection.md) (v1)

## Implementación

Resumen (detalle completo en PR #30, sección `## Changes`):

- `get_inventory`/`get_layer_info` convertidas a `@api_view(['GET'])` + `AllowAny` explícito + `PublicCatalogThrottle` (subclase de `AnonRateThrottle`, `scope='public_catalog'`, `60/min` vía `DEFAULT_THROTTLE_RATES`). Siguen públicas, mismo shape de respuesta.
- `get_bobina`: chequeo manual `is_authenticated and is_staff` al inicio (403 JSON si falla), sin convertir a DRF.
- Tests nuevos: `praxsa_manager/product/tests/test_public_catalog_endpoints.py` (7 casos) + helper `create_staff_user()` en `helpers.py`.
- **Desvío del plan, resuelto directamente (no cambia alcance/riesgo)**: `ScopedRateThrottle` no funciona con `@api_view` porque el decorador no reenvía `throttle_scope` de la función a la vista generada (solo copia `renderer_classes`/`parser_classes`/`authentication_classes`/`throttle_classes`/`permission_classes`). Se usó una subclase de `AnonRateThrottle` con `scope` fijo, leyendo el mismo `DEFAULT_THROTTLE_RATES['public_catalog']`.
- **Hallazgo de runtime no anticipado en el plan**: no hay `CACHES` compartido (Redis/Memcached) — el throttle usa cache in-memory por proceso. Hoy `Dockerfile.prod` corre `gunicorn` con 1 worker (sin `--workers` explícito), así que el límite es efectivamente global en el despliegue actual; si se agregan workers en el futuro, cada uno tendría su propio contador. Señalado como deuda/consideración, no bloqueante.

**Verificación propia ejecutada** (no es el Quality Gate formal — eso es `delivery-review`):
- `python manage.py test product` → 13/13 OK (6 preexistentes + 7 nuevos), sin regresiones. Usé credenciales del `.env` local del checkout principal (fuera del worktree) con permiso explícito del usuario en el chat — Postgres real en `localhost:5432`, DB de test creada y destruida por el test runner (`test_praxsa_backup`), sin tocar la DB real `praxsa_backup`.
- `manage.py check` y `makemigrations --check --dry-run` → sin issues nuevos, sin migraciones pendientes.
- Verificación en vivo contra `runserver` con datos reales: `get_calculator_info` sigue 200 (sin cambios); `get_layer_info`/`get_inventory` devuelven el mismo shape con datos reales; `get_bobina` sin sesión → 403; 65 peticiones seguidas a `get_inventory` → 200 hasta la #61, luego 429 (confirma el throttle con la tasa real de producción, `60/min`, no solo con la tasa sobreescrita del test).
- **No verificado**: navegador real contra la calculadora de `proforma` ni `/windows-film/:id` ni el panel `InventoryAdmin` (este PR no toca `proforma/`; el mecanismo de `get_bobina` — sesión de staff — está cubierto por el test automatizado, que ejercita exactamente esa condición). Queda como verificación opcional para `delivery-review` si quiere confirmarlo end-to-end.

### Fix de REV-2026-09-21-002 (segunda ronda de ENGINEERING)

- **Causa raíz**: `PublicCatalogThrottleTest.tearDown` intentaba restaurar `SimpleRateThrottle.THROTTLE_RATES` (atributo de clase global) a su valor real releyendo `api_settings.DEFAULT_THROTTLE_RATES` — pero `tearDown` corre **dentro** del `@override_settings` de nivel de clase, así que en ese momento `api_settings` todavía reflejaba la tasa sobreescrita del test (`2/min`), no la real (`60/min`). El "restore" terminaba re-aplicando el mismo valor de test, dejándolo filtrado para el resto del proceso.
- **Fix**: se captura `_ORIGINAL_THROTTLE_RATES = SimpleRateThrottle.THROTTLE_RATES` como constante de módulo, evaluada al importar el archivo (antes de que cualquier `override_settings` se aplique), y `tearDown` restaura ese valor capturado directamente en vez de releerlo de `api_settings`.
- **Verificación**: se agregó temporalmente (no comiteado) un test después de `PublicCatalogThrottleTest` que hace 5 peticiones normales a `get_inventory` e imprime `SimpleRateThrottle.THROTTLE_RATES`. Antes del fix: mostraba `{'public_catalog': '2/min'}` y 3 de 5 peticiones devolvían 429. Después del fix: mostraba `{'public_catalog': '60/min'}` y las 5 peticiones devolvieron 200. `python manage.py test product` → 13/13 OK; `makemigrations --check --dry-run` → sin cambios.
- Commit: `78c6ebc`.

## Review

### Ronda 3 (2026-09-22, misma sesión que ronda 2, verificación en vivo con el usuario)

**Veredicto: PASS** — 0 issues bloqueantes. 1 issue abierto de severidad Low, no bloqueante ([REV-2026-09-22-002](../reviews/REV-2026-09-22-002-throttle-bypass-for-session-authenticated-staff.md)).

El usuario copió el `.env` real al worktree de revisión (el clasificador de Auto Mode de esta sesión seguía bloqueando esa copia específica vía Bash incluso en la ronda 2) y asignó el grupo `admin` a un usuario staff existente. Con eso se completó, en el navegador embebido, la verificación manual que dejaba abierto [REV-2026-09-22-001](../reviews/REV-2026-09-22-001-manual-browser-verification-pending.md) — **ahora Resuelto**, evidencia completa en ese archivo:

1. Calculadora pública (`/`) sin login → `GET /product/get_inventory/1/0/0` → `200 OK` con datos reales de stock/precio.
2. `/windows-film/:id` sin login → `GET /product/layer/18` → `200 OK`, página renderiza correctamente.
3. `get_bobina` sin sesión → `GET /product/bobina/18` → `403 Forbidden`, body esperado.
4. `InventoryAdmin` logueado como staff con grupo `admin` → `GET /product/bobina/23` → `200 OK`, shape correcto, UI renderiza bien.

Los 4 acceptance criteria del plan que requerían verificación manual en navegador quedan confirmados con evidencia real. `REV-2026-09-22-002` (Low, `PublicCatalogThrottle` no aplica a sesiones de staff de Django) queda abierto pero no bloquea `PUBLISH` — severidad Low, sin vía de bypass para el público anónimo (el objetivo real del throttle), documentado para que quien lo desee lo cierre en una iteración futura.

### Ronda 2 (2026-09-22, sesión nueva sin contexto previo)

**Veredicto: FAIL** — 1 issue bloqueante, 1 adicional no bloqueante por sí solo:

- [REV-2026-09-22-001](../reviews/REV-2026-09-22-001-manual-browser-verification-pending.md) (**Medium / IMPLEMENTATION**): la verificación manual en navegador de la calculadora pública, `/windows-film/:id` e `InventoryAdmin` (paso 7 del plan, acceptance criteria) sigue sin ejecutarse. No es un defecto de código: se intentó completarla en esta revisión levantando `runserver`+`ng serve` con datos reales, pero la política de acceso a credenciales de este entorno de sesión bloqueó copiar el `.env` real para ese fin (sí lo permitió minutos antes para correr la suite de tests). El riesgo principal que esta verificación cubriría (cambio de shape al migrar `JsonResponse`→`Response`) ya está mitigado por los tests de caracterización exactos (`GetInventoryEndpointTest`/`GetLayerInfoEndpointTest`) y por la verificación previa de `delivery-engineer` contra `runserver` real.
- [REV-2026-09-22-002](../reviews/REV-2026-09-22-002-throttle-bypass-for-session-authenticated-staff.md) (**Low / IMPLEMENTATION**, no bloqueante por sí solo): `PublicCatalogThrottle` (subclase de `AnonRateThrottle`) no throttlea requests con sesión de Django válida, porque DRF usa `SessionAuthentication` por default (no hay `DEFAULT_AUTHENTICATION_CLASSES` configurado) y las vistas no restringen `authentication_classes`. En la práctica solo exime a staff logueado en `/admin/` (no existe login por sesión para clientes de `proforma` — confirmado por grep) — no es una vía de bypass para el público anónimo, que es el objetivo real del throttle. La investigación de la ronda anterior (REV-2026-09-21-002) había descartado el bypass solo para `TokenAuthentication`, sin considerar `SessionAuthentication`.

**REV-2026-09-21-002 (throttle-rate-test-leak, High): resuelto y confirmado de forma independiente.** Re-ejecuté un test temporal propio (no comiteado, revertido después) después de `PublicCatalogThrottleTest`: `SimpleRateThrottle.THROTTLE_RATES` se restaura correctamente a `{'public_catalog': '60/min'}` y 5 peticiones normales a `get_inventory` devuelven `200` — el leak ya no ocurre.

Verificación adicional hecha en esta ronda:
- `python manage.py test product` (13/13) y `python manage.py test` (proyecto completo, mismos 13/13) — corrida independiente contra Postgres real de dev, con permiso explícito del usuario en el chat.
- `python manage.py check` y `makemigrations --check --dry-run` — sin issues nuevos, sin migraciones pendientes.
- `flake8` (defaults, sin config en el repo) y `bandit` sobre `views.py`/`settings.py`/tests nuevos — sin hallazgos en el código efectivamente agregado/modificado por este diff.
- Sin scope creep: diff acotado a los archivos que el plan declaraba (backend); los archivos de `proforma/` en el mismo PR pertenecen a TASK-004 (combinado por decisión explícita del usuario).

Detalle completo de evidencia en [REV-2026-09-22-001](../reviews/REV-2026-09-22-001-manual-browser-verification-pending.md), [REV-2026-09-22-002](../reviews/REV-2026-09-22-002-throttle-bypass-for-session-authenticated-staff.md) y en el PR #30 (`## Testing`/`## Review`).

**Nota de aislamiento de contexto**: esta ronda sí corrió en una sesión nueva, sin contexto previo de la implementación ni de la revisión anterior — reconstruida enteramente desde TASK-006.md, el plan, ADR-005, el REV anterior y el diff real (`git diff origin/master...HEAD`), como pide el skill.

### Ronda 1 (2026-09-21, misma sesión que implementó el cambio)

**Veredicto: FAIL** — 1 issue abierto: [REV-2026-09-21-002](../reviews/REV-2026-09-21-002-throttle-rate-test-leak.md) (**High / IMPLEMENTATION**, corresponde a `delivery-engineer`). **Resuelto en la ronda 2** (ver arriba).

Resumen del issue: `PublicCatalogThrottleTest` sobreescribe `DEFAULT_THROTTLE_RATES['public_catalog']` a `2/min` y fuerza a `SimpleRateThrottle.THROTTLE_RATES` (atributo de clase global, compartido por todas las subclases de throttle del proceso) a releer ese valor en `setUp`/`tearDown` — pero `tearDown` corre **dentro** del `@override_settings` de nivel de clase, así que su intento de "restaurar" el valor real en realidad vuelve a leer el valor sobreescrito. Al terminar la clase, `SimpleRateThrottle.THROTTLE_RATES` queda contaminado con `2/min` para el resto del proceso de test — confirmado agregando un test temporal después de esa clase: 3 de 5 peticiones normales a `get_inventory` recibieron `429` en vez de `200`. No rompe la suite actual (por el orden en que están definidas las clases en el archivo), pero es un riesgo real de tests intermitentes a futuro.

Verificación adicional hecha en esta revisión, sin hallazgos:
- Se investigó una hipótesis de bypass del throttle para usuarios autenticados (dado que crear cuenta es público vía `create_client`) — **descartada con evidencia, aunque de forma incompleta** (ver REV-2026-09-22-002 arriba: la investigación cubrió `TokenAuthentication` pero no `SessionAuthentication`): `get_inventory`/`get_layer_info` no declaran `authentication_classes`, por lo que `TokenAuthentication` nunca reconoce el token del cliente para estas vistas y `request.user` siempre es `AnonymousUser` a efectos del throttle para ese mecanismo de auth específico.
- `python manage.py test product` (13/13), `manage.py check`, `makemigrations --check --dry-run`: todo OK, corrida independiente.
- Sin scope creep: diff acotado a los archivos que el plan declaraba.
- Sin lint/security tooling configurado en el proyecto (no ejecutado porque no existe, disclosure explícito).

**Nota de aislamiento de contexto**: esta revisión corrió en la misma sesión que implementó el cambio (`delivery-engineer`) — limitación procedimental señalada explícitamente. Se compensó re-ejecutando todos los comandos de forma independiente y buscando activamente fallas en vez de confirmar lo ya reportado.

## Publicación

**Listo para aprobación humana final.** PR #30 actualizado con trazabilidad completa (Summary, Task, Architecture decisions, Changes, Testing, Review, Known limitations) y verificado como `MERGEABLE` en GitHub tras resolver la colisión de IDs.

- **Renumeración de IDs (2026-09-22)**: este task y su ADR se renombraron de `TASK-002`/`ADR-002` a `TASK-006`/`ADR-005` — `master` ya tenía su propio `TASK-002`/`ADR-002` (PR #32, filtrado por sucursal en admin, tarea no relacionada) mergeado mientras este PR seguía abierto. Se actualizaron todas las referencias cruzadas (plan, los 3 REV, TASK-004, docstring del test) y se commiteó el rename (`7ac1e56`) antes de mergear `master`.
- **Merge de `master` (commit `57a95b7`)**: único conflicto textual real fue `praxsa_manager/product/tests/helpers.py` (`create_staff_user` de esta rama vs. `add_user_to_group` de `master`, ambas agregadas en el mismo punto del archivo) — resuelto conservando ambas funciones, sin pérdida de cobertura de ningún lado.
- **Verificación post-merge**: `python manage.py test` (proyecto completo) → **46/46 OK** (13 de este task + 33 de los otros tasks ya mergeados en `master`), sin regresiones cruzadas. `makemigrations --check --dry-run` → sin migraciones pendientes.
- **Cambio sensible — requiere aprobación humana explícita antes de mergear**: este task modifica autenticación/autorización de 3 endpoints de producción (ver ADR-005) y tiene un issue Low abierto y no bloqueante ([REV-2026-09-22-002](../reviews/REV-2026-09-22-002-throttle-bypass-for-session-authenticated-staff.md)). No se mergea automáticamente — queda a la espera de que el usuario apruebe el merge en GitHub.
