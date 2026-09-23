# REV-2026-09-23-003: `CarModelPartForm.clean()` crashea con `ValueError` (500) si `width` llega vacío

**Status:** Open
**Severity:** High
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-09-23-admin-price-recalculation-venta-instalacion.md (v1)
**Suggested owner:** delivery-engineer

## Description

Mismo patrón que [REV-2026-09-23-001](REV-2026-09-23-001-crash-on-blank-required-numeric-field.md) (ya resuelto para `quantity`/`installation_price`), pero en un campo distinto que la corrección anterior no cubrió: la primera línea de la rama `venta_instalacion` reactivada, [Forms/car_model_part.py:67](../../praxsa_manager/product/Forms/car_model_part.py), llama:

```python
if self.item_width_lte_film_width(cc_car_part_id, sale_header.car_model_id, cc_width) == False:
```

`item_width_lte_film_width` ([Forms/car_model_part.py:47-49](../../praxsa_manager/product/Forms/car_model_part.py)) hace `Car_Model_Part.objects...filter(..., width__lte=width)`. Si `cc_width` es `None` (campo "Ancho" vacío/ausente en el POST — mismo mecanismo que `quantity`/`installation_price`: el campo es requerido a nivel de modelo, así que un valor vacío hace que Django lo excluya de `cleaned_data` en vez de dejarlo con un valor falsy), Django ORM lanza `ValueError: Cannot use None as a query value` para el lookup `__lte` — no captado, se propaga como 500.

Esta es la **primera línea** que se ejecuta dentro de la rama `venta_instalacion` reactivada por el fix del bug `sales_header`→`proforma_header` — antes de este PR, con `sale_header` siempre `None`, esta línea nunca corría. Es exactamente el mismo tipo de riesgo que REV-2026-09-23-001 (código dormante desde 2023 reactivado sin las guardas de `None` que nunca necesitó mientras estuvo muerto), solo que en el campo `width` en vez de `quantity`/`installation_price` — la corrección anterior no lo cubrió porque el hallazgo original solo citó esos dos campos.

## Expected behavior

Un `width` vacío en un ítem `venta_instalacion` debería producir un error de validación del form (p. ej. en el campo `window_film`, reusando el mensaje ya existente de "ancho insuficiente", o uno específico de "campo requerido") — no un 500.

## Actual behavior

`form.is_valid()` lanza `ValueError` sin capturar cuando `width` no se envía. Reproducido con un test ad hoc (no incluido en el PR, descartado después de esta verificación):

```python
data = {
    'proforma_header': header.pk,
    'inventario': scenario['inventario'].pk,
    'car_part': scenario['car_part'].pk,
    'window_film': scenario['window_film'].pk,
    # width omitido
    'length': '1.00',
    'quantity': '1',
    'installation_price': '50.00',
    'window_film_price': '120.00',
    'sub_total': '170.00',
}
form = CarModelPartForm(data=data)
form.is_valid()  # ValueError, no False
```

## Evidence

```
$ python manage.py test product.tests.test_crash_check_tmp2 -v 2 --noinput
...
Traceback (most recent call last):
  File "...\praxsa_manager\product\tests\test_crash_check_tmp2.py", line 29, in test_missing_width_does_not_crash
    is_valid = form.is_valid()
  File "...\.venv\lib\site-packages\django\forms\forms.py", line 434, in full_clean
    self._clean_form()
  File "...\.venv\lib\site-packages\django\forms\forms.py", line 455, in _clean_form
    cleaned_data = self.clean()
  File "...\praxsa_manager\product\Forms\car_model_part.py", line 67, in clean
    if self.item_width_lte_film_width(cc_car_part_id, sale_header.car_model_id, cc_width) == False:
  File "...\praxsa_manager\product\Forms\car_model_part.py", line 48, in item_width_lte_film_width
    query = Car_Model_Part.objects.select_related('car_part_id', 'car_model_id').filter(car_model_id = model, car_part_id = item, width__lte = width)
  ...
  File "...\.venv\lib\site-packages\django\db\models\sql\query.py", line 1280, in build_lookup
    raise ValueError("Cannot use None as a query value")
ValueError: Cannot use None as a query value
----------------------------------------------------------------------
Ran 1 test in 0.350s
FAILED (errors=1)
```

Ninguno de los 15 tests de `test_admin_price_recalculation.py` (incluidos los 4 agregados para cerrar REV-2026-09-23-001/002) cubre un `width` ausente/vacío.

## Sugerencia de fix (no aplicada — corresponde a `delivery-engineer`)

Guardar antes de llamar a `item_width_lte_film_width`, mismo criterio ya aplicado a `quantity`/`installation_price`:

```python
if cc_width is None or self.item_width_lte_film_width(cc_car_part_id, sale_header.car_model_id, cc_width) == False:
    self.add_error('window_film','el ancho de la bobina es menor que el ancho del item')
```

Agregar un test (`test_missing_width_is_rejected_not_a_crash` o similar) para que quede protegido contra regresión, siguiendo el mismo patrón que los tests ya agregados para REV-2026-09-23-001.
