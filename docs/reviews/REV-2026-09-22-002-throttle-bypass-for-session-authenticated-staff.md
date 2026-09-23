# REV-2026-09-22-002: PublicCatalogThrottle no aplica a usuarios autenticados por sesión de Django (staff)

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-09-21-public-endpoints-protection.md (v1) / docs/adr/ADR-005-public-catalog-endpoints-protection.md
**Suggested owner:** delivery-engineer (opcional, ver "Sugerencia" abajo)

## Description

`REV-2026-09-21-002` (ronda anterior de esta misma revisión) investigó una hipótesis de bypass del throttle y la descartó: "`get_inventory`/`get_layer_info` no declaran `authentication_classes`, por lo que `TokenAuthentication` nunca reconoce el token del cliente... `request.user` siempre es `AnonymousUser`". Esa conclusión es correcta **para `TokenAuthentication`**, pero `PublicCatalogThrottle` hereda de `AnonRateThrottle`, cuyo `allow_request()` no aplica ningún límite cuando `request.user.is_authenticated` es `True` (ver `rest_framework/throttling.py`, `SimpleRateThrottle.get_cache_key` retorna `None` para usuarios autenticados en `AnonRateThrottle`).

`settings.py` no define `REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES']`, así que DRF usa su default de fábrica: `SessionAuthentication` + `BasicAuthentication`. Como las vistas tampoco declaran `authentication_classes` propio, `SessionAuthentication` sí corre sobre `get_inventory`/`get_layer_info` — y **sí** reconoce una cookie de sesión de Django válida (la que emite el login de `/admin/`), autenticando a `request.user` como ese usuario y, por lo tanto, dejando a `PublicCatalogThrottle` sin efecto para esa request.

## Expected behavior

Según ADR-005 y el hallazgo de la ronda anterior, el mecanismo de throttling debería "proteger a todos los llamadores por igual, sin excepción" dentro del público objetivo (visitantes anónimos que podrían scrapear el catálogo).

## Actual behavior

Un usuario con sesión de Django activa (en la práctica: staff logueado en `/admin/`, dado que no existe ningún flujo de login por sesión para clientes de `proforma` — confirmado, no hay `django.contrib.auth.login`/`LoginView` fuera del admin de Django) queda exento del límite de `60/min` al pegarle directo a `get_inventory`/`get_layer_info` en la misma pestaña/sesión de navegador.

## Evidence

Lectura de código (no requiere ejecución):
- `praxsa_manager/praxsa_manager/settings.py:119-127` — sin `DEFAULT_AUTHENTICATION_CLASSES`, sin `authentication_classes` en las vistas → DRF aplica `SessionAuthentication` por default de fábrica.
- `praxsa_manager/product/views.py:197-199,208-210` — `PublicCatalogThrottle(AnonRateThrottle)` sin restricción adicional de `authentication_classes = ()`.
- `grep -rn "contrib.auth import login\|auth.login(\|LoginView" praxsa_manager/` → sin resultados: no existe un flujo de sesión para clientes finales, solo el login del admin de Django.

## Riesgo real (por qué es Low, no bloqueante)

- El único actor que puede obtener una cookie de sesión válida es un usuario `is_staff` (el login del admin de Django exige `is_active` y `is_staff`) — ya es un rol de confianza elevada en este proyecto, con acceso directo a `get_bobina` y a los datos vía el propio panel de admin. No es una vía de bypass para el público anónimo que el throttle busca frenar (scraping externo).
- No cambia el resultado de ningún test existente ni del acceptance criteria del plan (que habla de limitar a "60 peticiones por minuto por IP", sin distinguir explícitamente el caso de sesión de staff).

## Sugerencia (no vinculante, no bloquea PASS)

Si se quiere cerrar esta brecha explícitamente: agregar `authentication_classes = ()` (o `(SessionAuthentication,)` combinado con throttle adicional) a `get_inventory`/`get_layer_info`, o documentar en ADR-005 que el throttle está pensado solo para el público anónimo y que las sesiones de staff quedan exentas por diseño (dado que ya tienen acceso privilegiado). Queda a criterio del usuario si amerita una tercera ronda de `delivery-engineer` o se acepta como está.
