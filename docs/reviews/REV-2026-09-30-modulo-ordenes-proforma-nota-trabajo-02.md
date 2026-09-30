# REV-2026-09-30-modulo-ordenes-proforma-nota-trabajo-02: el catálogo de bobinas devuelve números (float), no strings; en edición se pierden las bobinas guardadas

**Status:** Open
**Severity:** High
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-09-29-modulo-ordenes-proforma-nota-trabajo.md (v2)
**Suggested owner:** delivery-engineer

## Description
`GET ordenes/catalogo/bobinas` (`custom_views/ordenes_admin.py`, `OrdenesBobinasView`, respuesta de `Pricing_Business.get_reel_catalog`) devuelve `width`, `available_meters` y `unit_price` como **números JSON** (`1.5`, `50.0`, `120.0`) porque el `Response` de DRF codifica `Decimal` como `float` cuando no pasa por un serializer. El resto de la API del módulo (líneas, totales) devuelve strings con dos decimales (`"1.50"`, `"388.00"`), y el frontend (`ordenes.model.ts`, `ReelCatalogItem`) declara esos campos como `string`.

Consecuencia real, reproducida contra el servidor: la clave con la que el formulario identifica una bobina (`window_film|width`) no coincide entre el catálogo y las líneas guardadas:
- catálogo → `1|1.5`
- línea de una proforma guardada → `1|1.50`

Al **editar una proforma existente** (`ProformaFormComponent.loadCatalog`), las líneas cuyo `reel` no está en el catálogo se limpian y se muestra "Algunas bobinas ya no están disponibles en la sucursal": la persona pierde la bobina de cada línea y tiene que reelegirla, y el precio/subtotal de vista previa queda en 0 hasta entonces. Los tests no lo detectaron porque los specs del frontend usan strings en los mocks y los tests backend convierten con `Decimal(...)` antes de comparar.

Además, importes de dinero cruzan la frontera JSON como `float` (`120.0` en vez de `"120.00"`), contra la regla del proyecto ("el dinero se maneja con `Decimal`, nunca con `float`") y contra lo declarado en el plan ("los importes viajan como strings en JSON").

## Expected behavior
Plan, sección Architecture considerations: "Los importes viajan como strings en JSON". Los tipos del frontend (`string`) y las líneas guardadas (`"1.50"`) exigen el mismo formato en el catálogo. Editar una proforma debe conservar las bobinas de sus líneas.

## Actual behavior
Catálogo con números; en edición, las bobinas guardadas no se reconocen.

## Evidence
Servidor real (`runserver` + Postgres descartable, ver `## Review` del PR), sucursal con 50 m de "Carbon 20%" ancho 1.50 y precio 120:
```
$ probe: GET /product/ordenes/catalogo/bobinas?sucursal=1  y  GET /product/ordenes/proformas/<id>/
catalogo width: 1.5 float | unit_price: 120.0 | meters: 0.3
linea width  : '1.50' str
reelKey catalogo: 1|1.5 | reelKey linea guardada: 1|1.50 | coinciden: False
```
(`meters: 0.3` corresponde al momento de la sonda, con el stock ya consumido por otras pruebas; lo relevante es el tipo `float`.)

Tests que enmascaran el problema: `product/tests/test_ordenes_scope_permissions.py::CatalogTest::test_bobinas_catalog_has_meters_and_resolved_price` compara `Decimal(rows[0]['width'])`, que acepta tanto `1.5` como `"1.50"`.

## Notas para quien corrija
- Serializar el catálogo con strings cuantizados a 2 decimales (mismo formato que las líneas), y hacer que el test lo verifique con comparación de strings, no con `Decimal(...)`.
- Considerar que el frontend compare/arme la clave de bobina con el ancho normalizado (`Number(width).toFixed(2)`) para no depender del formato del servidor, y agregar un spec de edición cuyo catálogo y líneas usen los formatos reales de la API.
