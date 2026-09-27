# REV-2026-09-27-modulo-almacen-01: `InventarioCreateSerializer` pierde los validadores del modelo en `nro_lote` y `numero_referencia`, causa un `500` no controlado

**Status:** Open
**Severity:** High
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-09-26-modulo-almacen.md (v2)
**Suggested owner:** delivery-engineer

## Description

`InventarioCreateSerializer` (`praxsa_manager/product/serializer/almacen_serializer.py`) redeclara explícitamente `nro_lote` y `numero_referencia` como campos de serializer planos (`serializers.CharField(...)`, `serializers.IntegerField(...)`) para poder marcarlos `required=False` con un default de servidor. Al redeclararlos explícitamente, DRF deja de heredar los `validators`/`max_length` que el campo del modelo `inventario` ya define:

- `nro_lote = models.CharField(max_length=15, validators=[alphanumeric], ...)` — el serializer nuevo lo declara como `serializers.CharField(required=False, allow_null=True, allow_blank=True)`, **sin** `max_length=15` ni el `RegexValidator` alfanumérico.
- `numero_referencia = models.PositiveIntegerField(..., validators=[MaxValueValidator(limit_value=9999999999, ...)])` — el serializer nuevo lo declara como `serializers.IntegerField(required=False)`, **sin** el `MaxValueValidator`.

Esto solo afecta a la creación (`POST almacen/inventario`); `InventarioUpdateSerializer` no redeclara `nro_lote` (queda auto-generado por `ModelSerializer`), así que en "Gestionar" el mismo campo sí valida correctamente — confirma que la pérdida es específica de este serializer nuevo, no una limitación general del proyecto.

## Expected behavior

Según el plan v2 (`## Architecture considerations`, tabla de campos) y el ADR actualizado, `nro_lote` es "Opcional" y `numero_referencia` tiene "default `0` (modelo)" — ninguno de los dos documentos dice explícitamente "sin las restricciones que ya tiene el campo en el modelo". Lo esperable es que un valor que el modelo rechazaría (lote con caracteres no alfanuméricos, o más de 15 caracteres; referencia de más de 10 dígitos) sea rechazado con un `400` legible, igual que ya pasa al editar la misma fila vía `PATCH .../inventario/<pk>/`.

## Actual behavior

- Un `POST almacen/inventario` con `nro_lote` conteniendo un guion (`"L-999"`) es aceptado como válido por el serializer (`is_valid() == True`), pese a que el modelo lo rechazaría.
- Un `POST almacen/inventario` con un `nro_lote` de 50 caracteres también pasa `is_valid()`, pero **falla al guardar con una excepción de base de datos no controlada** (`value too long for type character varying(15)`) — es decir, un `POST` con ese payload devolvería un `500 Internal Server Error` en vez de un `400` con el error de validación, porque nada en la vista (`InventarioListView.create`) ni en el serializer captura esa excepción.
- `numero_referencia` tiene el mismo problema de raíz (validador de modelo no heredado), aunque no se confirmó un crash equivalente — solo que el límite deja de aplicarse.

## Evidence

Verificado ejecutando el serializer directamente (no solo leyendo el código):

```
$ python manage.py shell -c "
from product.serializer.almacen_serializer import InventarioCreateSerializer
...
data = {..., 'nro_lote': 'L-999'}
s = InventarioCreateSerializer(data=data)
print('is_valid:', s.is_valid())   # -> True
print('errors:', s.errors)          # -> {}
"
```

```
$ python manage.py shell -c "
...
data = {..., 'nro_lote': 'X'*50}
s = InventarioCreateSerializer(data=data)
print('is_valid:', s.is_valid())   # -> True
obj = s.save()                      # -> excepción:
# save failed: value too long for type character varying(15)
"
```

Contraste con `InventarioUpdateSerializer` (mismo campo `nro_lote`, no redeclarado explícitamente), que sí rechaza el mismo valor con un `400` limpio:

```
$ python manage.py shell -c "
from product.serializer.almacen_serializer import InventarioUpdateSerializer
...
data = {'nro_lote': 'L-999', ...}
s = InventarioUpdateSerializer(inv, data=data)
print('is_valid:', s.is_valid())   # -> False
print('errors:', s.errors)          # -> {'nro_lote': ['Solo se permiten letras y numeros']}
"
```

Ningún test de `tests/test_almacen_module.py::InventarioCreateTest` ejercita `nro_lote` con un valor inválido o largo — por eso la suite completa (189/189) pasa sin detectar esto.
