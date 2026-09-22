# REV-2026-09-21-003: Sin test para la suma de `total_price` con más de un ítem en `carPartItems`

**Status:** Resolved (2026-09-22) — se agregó `test_recalculates_total_price_as_the_sum_of_multiple_items` (commit `cee126f`). Ver `## Resolución` para la evidencia de esta segunda pasada de review.
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-09-21-price-recalculation-serializer.md (v1)
**Suggested owner:** delivery-engineer

## Description

`SalesHeaderSerializer.validate()` acumula `total_price` sumando el `sub_total` recalculado de **cada** ítem de `carPartItems` (`total_price += item['sub_total']` dentro del `for`, [invoice_serializer.py:44-69](../../praxsa_manager/product/serializer/invoice_serializer.py)). Es la lógica de negocio central de este cambio para el caso real de uso: una proforma típica de este dominio cotiza **varias** partes del auto a la vez (parabrisas, ventanas, etc. — así lo describe `docs/CLAUDE.md`: "elige... la lámina para cada parte del auto"), no una sola.

Ningún test de `test_invoice_pricing.py` ejercita este camino. `build_invoice_payload` (el helper que arman todos los tests del archivo) construye siempre `'carPartItems': [ {...un solo ítem...} ]` — nunca dos o más. La regla del proyecto (`docs/CLAUDE.md`: "Todo cambio de lógica de negocio lleva su test") no se cumple para esta rama específica del cambio.

No encontré evidencia de que la suma esté mal — la lógica (`Decimal('0')` acumulado en un loop) es correcta por inspección — pero es exactamente el tipo de caso donde una regresión futura (alguien reordena el loop, cambia `total_price` de una asignación a una acumulación mal ubicada, etc.) pasaría sin que ningún test lo detecte hoy.

## Expected behavior

Según el plan (Test strategy y Acceptance criteria), la cobertura de tests debería ejercitar el comportamiento real del endpoint. Un caso con 2+ ítems, cada uno con su propio `Car_Model_Part`/lámina/ancho, verificando que `Proforma_Header.total_price` es la suma de los `Proforma_Detail.sub_total` recalculados de cada uno (y que cada `Proforma_Detail` individual tiene su propio precio correcto, no uno mezclado con el otro).

## Actual behavior

`test_invoice_pricing.py` no tiene ningún test con más de un ítem en `carPartItems`. Verificado leyendo el archivo completo y buscando `carPartItems` — todas las instancias vienen de `build_invoice_payload`, que arma una lista de un solo elemento.

## Evidence

```
$ grep -n "carPartItems" praxsa_manager/product/tests/test_invoice_pricing.py
20:        'carPartItems': [
...
# build_invoice_payload es la única función que arma carPartItems en todo el archivo,
# y siempre construye una lista de exactamente un ítem.
```

## Resolución

Resuelto el 2026-09-22 (commit `cee126f`): se agregó `test_recalculates_total_price_as_the_sum_of_multiple_items` a `test_invoice_pricing.py` — arma una proforma con 2 ítems, cada uno con su propio `Car_Part`/`Car_Model_Part`/lámina/bobina/inventario en la misma sucursal (`installation_price` 50.00 y 30.00; `precio_venta_mtr_lineal` 120.00 y 90.00), con `sub_total`/`total_price` manipulados en el payload. Verifica que cada `Proforma_Detail` tiene su propio `sub_total` recalculado por separado (170.00 y 420.00, sin mezclarse entre ítems) y que `Proforma_Header.total_price` es la suma de ambos (590.00), no el valor manipulado.

Re-ejecutado en esta segunda pasada de review (entorno independiente, contenedor Postgres descartable en el puerto 5433, evitando el conflicto con el Postgres nativo del host en 5432 — mismo mecanismo que la resolución de REV-002):

```
$ cd praxsa_manager
$ POSTGRES_USER=admin POSTGRES_PASSWORD=example POSTGRES_DB=praxsa \
  DB_HOST=127.0.0.1 DB_PORT=5433 ENV=dev DEBUG=1 SECRET_KEY=test-secret-key \
  py manage.py test product
Found 18 test(s).
Creating test database for alias 'default'...
...............15
...
----------------------------------------------------------------------
Ran 18 tests in 4.068s

OK
Destroying test database for alias 'default'...
```

18/18 en verde (subió de 17 a 18, el nuevo test de multi-ítem incluido), sin regresión en el resto de la suite. Confirmado además por inspección directa del diff que la implementación (`total_price += item['sub_total']` dentro del loop de `validate()`, [invoice_serializer.py:44-69](../../praxsa_manager/product/serializer/invoice_serializer.py)) coincide con la aserición del test nuevo.
