# REV-2026-09-26-modulo-vehiculos-01: Crear un Modelo desde el panel real lo deja inactivo (`is_active=False`) y desaparece del listado al instante

**Status:** Open
**Severity:** Critical
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-09-26-modulo-vehiculos.md (v2)
**Suggested owner:** delivery-engineer

## Description

`CarModelSerializer` (y también `CarBrandSerializer`/`CarPartSerializer`) expone `is_active` como un campo de escritura auto-generado por `ModelSerializer` (`BooleanField`, `required=False`, sin `default` explícito a nivel de serializer). DRF trata cualquier request `multipart/form-data` como si fuera un envío de formulario HTML: si un `BooleanField` está ausente del payload, lo interpreta como un checkbox sin marcar y lo valida como `False` — **no** como "campo omitido" (que sí respetaría el `default=True` del modelo). Esto solo ocurre en creación (`partial=False`); en `PATCH` (`partial=True`) DRF sí omite el campo correctamente.

El servicio Angular real (`vehicles.service.ts`, método `createModel()`) **siempre** construye un `FormData` (multipart) para crear un Modelo, con o sin imagen — nunca envía JSON. Por lo tanto, **todo Modelo creado desde la pantalla real del panel queda `is_active=False`**, y como el listado (`CarModelListCreateView.get_queryset()`) filtra `is_active=True` por defecto, el Modelo recién creado desaparece del listado inmediatamente después de crearlo, sin ningún error visible para el usuario.

`createBrand`/`createPart` sí usan JSON puro en el frontend real, así que Marca e Item no se ven afectados por esta vía — pero el mismo defecto de serializer existe en sus clases y se activaría igual si alguna vez se llama esos endpoints con `multipart/form-data` (por ejemplo, desde un cliente HTTP distinto, o si en el futuro se agrega upload de archivos a Marca/Item).

## Expected behavior

Según el ADR-modulo-vehiculos-soft-delete (punto 1) y el modelo (`is_active = models.BooleanField(default=True)`), un registro nuevo debe quedar activo por defecto salvo que se indique lo contrario, y debe aparecer inmediatamente en el listado tras crearlo (acceptance criteria del plan: "Crear/editar Modelo permite subir/reemplazar/eliminar la imagen..." implica que el modelo creado queda operable, no oculto).

## Actual behavior

Reproducido en vivo contra el servidor de desarrollo real (`manage.py runserver`), con una marca activa ya existente (id 41, creada vía JSON con `is_active: true`):

```
$ curl -s -X POST http://127.0.0.1:8123/product/vehicles/models -H "Authorization: Token <token>" -F "name=ReviewCheckModel2" -F "car_brand_id=41"
{"id":160,"name":"ReviewCheckModel2","car_brand_id":41,"car_brand_name":"ReviewCheckBrandJSON","image":null,"is_active":false,"items_count":0}
```

Comparación con la misma marca creada vía JSON puro (como hace el frontend real para Marca/Item, que no usan FormData):

```
$ curl -s -X POST http://127.0.0.1:8123/product/vehicles/brands -H "Authorization: Token <token>" -H "Content-Type: application/json" -d '{"name":"ReviewCheckBrandJSON"}'
{"id":41,"name":"ReviewCheckBrandJSON","is_active":true,"models_count":0}

$ curl -s -X POST http://127.0.0.1:8123/product/vehicles/brands -H "Authorization: Token <token>" -F "name=ReviewCheckBrandMultipart"
{"id":40,"name":"ReviewCheckBrandMultipart","is_active":false,"models_count":0}
```

Confirmado además que el mismo Modelo, editado luego con `PATCH` multipart (`partial=True`), **no** reproduce el bug — `is_active` queda intacto en esa vía, aislando el problema específicamente a la creación:

```
$ curl -s -X PATCH http://127.0.0.1:8123/product/vehicles/models/160/ -H "Authorization: Token <token>" -F "name=ReviewCheckModel2Edited" -F "car_brand_id=41"
{"id":160,"name":"ReviewCheckModel2Edited","car_brand_id":41,"car_brand_name":"ReviewCheckBrandJSON","image":null,"is_active":true,"items_count":0}
```//(is_active se había forzado a True manualmente antes de este PATCH, para aislar la variable)

Causa raíz verificada en el código de DRF instalado (`rest_framework/fields.py:416-438`, método base `Field.get_value()`):
```python
def get_value(self, dictionary):
    if html.is_html_input(dictionary):
        if self.field_name not in dictionary:
            if getattr(self.root, 'partial', False):
                return empty
            return self.default_empty_html   # BooleanField.default_empty_html = False
        ...
```
`html.is_html_input()` devuelve `True` para cualquier `QueryDict` (multipart y `application/x-www-form-urlencoded`), y `BooleanField.default_empty_html = False` (`rest_framework/fields.py:672`) — de ahí el `False` silencioso.

Ninguno de los 39 tests nuevos de `test_vehicles_module.py` detectó esto porque los tests que sí crean un Modelo vía multipart (`CarModelImageTest`, que no pasa `content_type='application/json'` porque incluye un archivo) nunca hacen `assert` sobre `is_active` en la respuesta — solo verifican el status code y la imagen.

## Evidence

Ver bloques de comandos/salida arriba (`curl` contra el servidor real de desarrollo, con la migración `0108` ya aplicada). Los registros de prueba y el usuario temporal usados para esta verificación ya fueron eliminados de la base de datos real tras confirmar el hallazgo.
