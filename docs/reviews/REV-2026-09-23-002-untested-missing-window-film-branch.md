# REV-2026-09-23-002: Rama `cc_window_film is None` de `CarModelPartForm.clean()` sin test

**Status:** Resolved (2026-09-23) — ver `## Resolución`.
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-09-23-admin-price-recalculation-venta-instalacion.md (v1)
**Suggested owner:** delivery-engineer

## Description

`CarModelPartForm.clean()` ([Forms/car_model_part.py:85-86](../../praxsa_manager/product/Forms/car_model_part.py)) agrega una rama nueva: si existe `Car_Model_Part` pero `cc_window_film is None`, rechaza con `self.add_error('window_film', 'Tiene que seleccionar una lámina.')`. Ninguno de los 11 tests de `test_admin_price_recalculation.py` ejercita este caso — `_valid_data()` siempre incluye `window_film` con un valor válido, y ningún test lo omite u override a vacío.

`docs/CLAUDE.md` pide "todo cambio de lógica de negocio lleva su test", y esta es una rama nueva introducida por este PR.

## Expected behavior

Un test que envíe el form sin `window_film` (o `window_film=''`) para un ítem `venta_instalacion` con `Car_Model_Part` válido, y verifique `form.is_valid() == False` con el error en `window_film`.

## Actual behavior

Rama sin cobertura — no se puede confirmar automáticamente que el mensaje de error se dispare como se espera, ni que quede protegida contra una regresión futura (p. ej. alguien reordena el `elif` y rompe el chequeo sin que ningún test lo note).

**Nota de riesgo (menor):** `window_film` ya es un campo requerido a nivel de modelo/form (sin `blank=True`), así que Django ya agrega su propio error de "campo requerido" antes de que `clean()` corra — esta rama nueva solo agrega un segundo mensaje redundante sobre el mismo campo, no abre una vía de datos inconsistentes. Por eso la severidad es `Low`, a diferencia de REV-2026-09-23-001 (que sí es una vía de crash real). Se documenta igual porque es lógica nueva sin test, no porque el sistema esté hoy en riesgo por esto.

## Evidence

```
$ grep -n "window_film" praxsa_manager/product/tests/test_admin_price_recalculation.py
53:            'window_film': self.scenario['window_film'].pk,
55:            'window_film': self.scenario['window_film'].pk,
192:            'items-0-window_film': self.scenario['window_film'].pk,
200:            'items-1-window_film': self.scenario['window_film'].pk,
246:            'items-0-window_film': self.scenario['car_part'].pk,
...
```
(ningún test omite `window_film` ni lo deja vacío para un ítem `venta_instalacion` con `Car_Model_Part` válido).

## Resolución

Agregado `test_missing_window_film_is_rejected_with_car_model_part_present` a `test_admin_price_recalculation.py` (commit `ecf16c7`, PR #36) — envía un ítem `venta_instalacion` con `Car_Model_Part` válido pero sin `window_film`, y verifica `form.is_valid() == False` con el error en `window_film`. Verificado en la misma corrida que REV-2026-09-23-001: `python manage.py test product --noinput` → 61/61 en verde.
