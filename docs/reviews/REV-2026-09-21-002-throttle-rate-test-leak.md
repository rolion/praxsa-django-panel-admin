# REV-2026-09-21-002: El monkeypatch de tasa de throttling en los tests contamina el resto de la suite

**Status:** Open
**Severity:** High
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-09-21-public-endpoints-protection.md (v1)
**Suggested owner:** delivery-engineer

## Description

`PublicCatalogThrottleTest` (`praxsa_manager/product/tests/test_public_catalog_endpoints.py:49-92`) sobreescribe `DEFAULT_THROTTLE_RATES['public_catalog']` a `'2/min'` vía `@override_settings` a nivel de clase, y fuerza a `SimpleRateThrottle.THROTTLE_RATES` (un atributo de clase mutable y global, compartido por *todas* las subclases de throttle del proceso, incluida `PublicCatalogThrottle`) a releer ese valor en `setUp`/`tearDown`, porque `SimpleRateThrottle.THROTTLE_RATES` se resuelve una sola vez al importar el módulo y no reacciona solo por la señal `setting_changed` de `override_settings`.

El problema es que `tearDown` intenta "restaurar" el valor real leyendo `api_settings.DEFAULT_THROTTLE_RATES` — pero `tearDown` todavía se ejecuta **dentro** del `@override_settings` de nivel de clase (ese decorador envuelve `setUpClass`/`tearDownClass`, no cada método), así que en ese momento `api_settings.DEFAULT_THROTTLE_RATES` sigue devolviendo `{'public_catalog': '2/min'}`, no el `'60/min'` real de `settings.py`. El "restore" termina re-aplicando el mismo valor de test. Cuando la clase completa termina y `override_settings` sí revierte `settings.py`, nada vuelve a sincronizar `SimpleRateThrottle.THROTTLE_RATES` — queda contaminado con `'2/min'` para el resto del proceso de test.

## Expected behavior

Después de que `PublicCatalogThrottleTest` termina, cualquier otro test del proceso que golpee `get_inventory`/`get_layer_info` debería seguir viendo la tasa real (`60/min`), sin necesidad de saber que en algún momento corrió un test de throttling con una tasa distinta.

## Actual behavior

Confirmado de forma reproducible agregando un test de verificación (`ZZScratchLeakCheckTest`, no comiteado — se removió después de confirmar el bug) definido *después* de `PublicCatalogThrottleTest` en el mismo archivo: hace solo 5 peticiones anónimas normales a `get_inventory` (muy por debajo del límite real de `60/min`), y 3 de las 5 devuelven `429` en vez de `200`, porque `SimpleRateThrottle.THROTTLE_RATES` quedó en `{'public_catalog': '2/min'}`.

Hoy esto no rompe ningún test **real** de la suite porque, por casualidad de orden de definición de clases en el archivo (Python conserva el orden de declaración, no alfabético), ningún otro test que golpee estos dos endpoints corre después de `PublicCatalogThrottleTest` en este módulo. Pero es un bug latente de aislamiento: cualquier test nuevo que se agregue después (en este archivo o en otro que corra después en el mismo proceso, incluido bajo `--parallel` o con un orden de descubrimiento distinto) puede empezar a fallar con `429` de forma aparentemente inexplicable, sin que su propio código haya cambiado — exactamente el tipo de falla intermitente y difícil de diagnosticar que socava la confianza en la suite de tests que el propio backlog #8 busca construir.

## Evidence

```
$ python manage.py test product.tests.test_public_catalog_endpoints --verbosity 2
...
test_get_inventory_returns_429_after_exceeding_rate (...PublicCatalogThrottleTest...) ... ok
test_get_layer_info_returns_429_after_exceeding_rate (...PublicCatalogThrottleTest...) ... ok
test_rate_after_throttle_test_class (...ZZScratchLeakCheckTest...) ... ok
----------------------------------------------------------------------
Ran 8 tests in 1.876s
OK

SimpleRateThrottle.THROTTLE_RATES after throttle test class: {'public_catalog': '2/min'}
codes with real 60/min rate (expect all 200): [200, 200, 429, 429, 429]
```

`SimpleRateThrottle.THROTTLE_RATES` debería mostrar `{'public_catalog': '60/min'}` en ese punto (o, mejor, no necesitar inspeccionarse porque cada throttle debería resolver su tasa de forma aislada) — en cambio muestra la tasa de test, y la request #3 en adelante de un test completamente ajeno recibe `429`.

## Sugerencia de arreglo (no vinculante, la implementa delivery-engineer)

Capturar el valor original de `SimpleRateThrottle.THROTTLE_RATES` como constante de módulo, evaluada al importar el archivo de test (antes de que cualquier `override_settings` se aplique), y restaurar exactamente ese valor capturado en `tearDown` — en vez de re-derivarlo de `api_settings`, que sigue contaminado mientras el `override_settings` de la clase sigue activo. Alternativa más simple: mover el `override_settings`/parche a nivel de método (no de clase) para que `tearDown` corra después de que el `override_settings` de settings.py se revierta method-by-method, si el runner lo permite; o usar `self.addCleanup(...)` registrado en `setUp` para asegurar el orden correcto de restauración respecto al override.
