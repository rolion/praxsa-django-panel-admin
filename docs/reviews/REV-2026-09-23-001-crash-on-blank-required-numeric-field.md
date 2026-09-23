# REV-2026-09-23-001: `CarModelPartForm.clean()` crashea con `TypeError`/`AttributeError` (500) si `quantity`/`installation_price` llegan vacíos

**Status:** Open
**Severity:** High
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-09-23-admin-price-recalculation-venta-instalacion.md (v1)
**Suggested owner:** delivery-engineer

## Description

El fix del bug `sales_header` → `proforma_header` ([Forms/car_model_part.py:66](../../praxsa_manager/product/Forms/car_model_part.py)) reactiva, por primera vez desde 2023, las ramas condicionales de `CarModelPartForm.clean()` para `venta_instalacion` (líneas 66-95) y `venta_metro_lineal` (líneas 97-102). Esas ramas contienen comparaciones sin proteger contra `None`:

- Línea 69: `if cc_quantity < 1:` — `cc_quantity = cleaned_data.get('quantity')`.
- Línea 71: `if cc_installation_price < 1:` — mismo patrón.
- Línea 99 (rama `venta_metro_lineal`): `if cc_installation_price.compare(0) == 1:`.

Si el POST no incluye un valor válido para `quantity` o `installation_price` (campo vacío, o ausente del payload — ambos casos hacen que Django deje esa clave fuera de `cleaned_data` porque el campo falló su propia validación de "requerido" antes de llegar a `clean()`), `cleaned_data.get(...)` devuelve `None`, y estas comparaciones lanzan una excepción no capturada (`TypeError: '<' not supported between instances of 'NoneType' and 'int'` para `quantity`/`installation_price` en `venta_instalacion`; `AttributeError: 'NoneType' object has no attribute 'compare'` para `installation_price` en `venta_metro_lineal`). El admin de Django no envuelve `form.is_valid()` en un `try/except` genérico, así que esto se propaga como un error 500 sin manejar, en vez del mensaje de validación amigable que la propia línea pretendía mostrar ("campo requerido").

Antes de este PR, estas ramas nunca se ejecutaban (bug `sales_header`, ver TASK-007) — el riesgo era 100% latente. Ahora que `sale_header` resuelve correctamente, cualquier fila de `Proforma_Detail` donde el operador deje "Cantidad" o "Costo Instalación" en blanco (un error de captura de datos plausible a diario — p. ej. si el usuario agrega una fila manualmente antes de que el AJAX de `sales_event.js` la autocomplete, o si edita una fila existente y borra el valor) tira abajo el guardado completo con un 500, en vez de simplemente marcar el error en el campo correspondiente.

## Expected behavior

Según el plan v1 (paso 3): "reactiva las validaciones existentes de ancho/`quantity`/`installation_price` tal como ya estaban escritas, sin modificar esas reglas" — la intención es que estas reglas **vuelvan a funcionar como validación**, no que introduzcan una vía de crash nueva. Un campo requerido vacío debería producir un error de formulario visible (`self.add_error(...)`), igual que ya ocurre para `sub_total`/`length` (que sí tienen sus propios `clean_<field>` con manejo seguro) — no un 500.

## Actual behavior

`form.is_valid()` lanza `TypeError` sin capturar cuando `quantity` no se envía, verificado con un test ad hoc (no incluido en el PR, construido y ejecutado solo para esta verificación, luego descartado):

```python
data = {
    'proforma_header': header.pk,
    'inventario': scenario['inventario'].pk,
    'car_part': scenario['car_part'].pk,
    'window_film': scenario['window_film'].pk,
    'width': '1.50',
    'length': '1.00',
    # quantity omitido
    'installation_price': '50.00',
    'window_film_price': '120.00',
    'sub_total': '170.00',
}
form = CarModelPartForm(data=data)
form.is_valid()  # TypeError, no False
```

## Evidence

```
$ python manage.py test product.tests.test_crash_check_tmp -v 2 --noinput
...
ERROR: test_missing_quantity_does_not_crash (product.tests.test_crash_check_tmp.QuantityMissingCrashCheck)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "...\praxsa_manager\product\tests\test_crash_check_tmp.py", line 33, in test_missing_quantity_does_not_crash
    is_valid = form.is_valid()
  File "...\.venv\lib\site-packages\django\forms\forms.py", line 201, in is_valid
    return self.is_bound and not self.errors
  File "...\.venv\lib\site-packages\django\forms\forms.py", line 196, in errors
    self.full_clean()
  File "...\.venv\lib\site-packages\django\forms\forms.py", line 434, in full_clean
    self._clean_form()
  File "...\.venv\lib\site-packages\django\forms\forms.py", line 455, in _clean_form
    cleaned_data = self.clean()
  File "...\praxsa_manager\product\Forms\car_model_part.py", line 69, in clean
    if cc_quantity < 1:
TypeError: '<' not supported between instances of 'NoneType' and 'int'
----------------------------------------------------------------------
Ran 1 test in 0.352s
FAILED (errors=1)
```

Ninguno de los 11 tests nuevos de `test_admin_price_recalculation.py` cubre el caso de un campo numérico requerido ausente/vacío — todos los tests que ejercitan las ramas `venta_instalacion`/`venta_metro_lineal` siempre envían `quantity`/`installation_price` con un valor numérico válido (`'0'`, `'1'`, `'2'`, nunca ausente).

## Sugerencia de fix (no aplicada — corresponde a `delivery-engineer`)

Guardar antes de comparar, por ejemplo:

```python
if cc_quantity is None or cc_quantity < 1:
    self.add_error('quantity', 'campo requerido')
if cc_installation_price is None or cc_installation_price < 1:
    self.add_error('installation_price', 'campo requerido')
```

y el equivalente en la rama `venta_metro_lineal` (línea 99) para `cc_installation_price.compare(0)`. Agregar un test por cada campo requerido omitido (mínimo: `quantity` e `installation_price` en `venta_instalacion`) para que quede protegido contra regresión.
