# PLAN-2026-09-21-price-recalculation-serializer (v1)

**Task:** TASK-005
**ADRs relacionados:** [ADR-004](../adr/ADR-004-server-side-price-recalculation.md)

## Objective

Cerrar, para el camino REST que usa la calculadora Angular (`POST /product/invoice`), el hallazgo BIZ-01 (precio no validado server-side): primero documentar con tests el comportamiento actual (el servidor persiste el precio tal como lo manda el cliente, sin verificarlo), y luego hacer que `SalesHeaderSerializer` recalcule siempre el precio real y lo persista, ignorando lo recibido.

## Context

Resumen de [TASK-005](../tasks/TASK-005.md) (investigación) y [ADR-004](../adr/ADR-004-server-side-price-recalculation.md) (arquitectura). Puntos clave a tener presentes durante la implementación:
- Este endpoint solo crea proformas `sales_type = venta_instalacion` (el campo ni siquiera llega del cliente) — una sola fórmula de subtotal aplica, sin ambigüedad de negocio pendiente.
- Decisión de negocio confirmada por el usuario: el servidor **siempre sobrescribe** con el precio recalculado, nunca rechaza por discrepancia con lo enviado.
- Sí se rechaza (`400`) cuando el precio real no se puede resolver (dato faltante genuino, no manipulación).
- `length`/`width`/`quantity` del ítem quedan **fuera de alcance** — se siguen confiando del cliente, solo se valida/recalcula precio.
- No se toca `get_inventory`/`get_car_part_info`/admin/`sales_event.js` — quedan intactos, la función de precio nueva es reusable a futuro pero no se retro-adapta aquí.

## Current behavior

- [invoice_serializer.py:33-48](../../praxsa_manager/product/serializer/invoice_serializer.py) — `SalesHeaderSerializer.create()` persiste `total_price` (header) y `sub_total`/`installation_price`/`window_film_price` (por ítem) exactamente como los envía el cliente. No consulta `precio_venta_sucursal`, `inventario` ni `Car_Model_Part`.
- [invoice.py:20-34](../../praxsa_manager/product/custom_views/invoice.py) — `InvoiceView.post` solo valida shape (`serializer.is_valid()`), no reglas de precio.
- `praxsa_manager/product/tests/helpers.py` y `test_smoke.py` ya existen (harness de backlog #8) — `build_full_scenario()` arma un escenario completo con `Car_Model_Part.installation_price=Decimal('50.00')` e `inventario.precio_venta_mtr_lineal=Decimal('120.00')`, pero **no** tiene una factory para `precio_venta_sucursal` (el override por sucursal) — hace falta agregarla para cubrir esa rama del fallback en los tests nuevos.

## Expected behavior

- `POST /product/invoice` con `sub_total`/`total_price`/`installation_price`/`window_film_price` que no coinciden con el precio real responde igual `201`, pero lo que queda persistido en `Proforma_Detail`/`Proforma_Header` es el valor que el servidor calculó, no el enviado.
- Si el precio real no se puede resolver (no existe `Car_Model_Part` para `(car_model_id, car_part)`, o no hay ninguna fila de inventario/sucursal que cubra `(sucursal, lámina, ancho)`), la respuesta es `400` con el shape estándar de errores de DRF (vía `serializer.errors`, ya manejado por `InvoiceView.post` línea 30) — no se crea la proforma.
- `length`/`width`/`quantity` que manda el cliente siguen usándose tal cual en la fórmula — no se validan contra `Car_Model_Part`.

## Architecture considerations

Ver [ADR-004](../adr/ADR-004-server-side-price-recalculation.md) para la decisión completa y las alternativas descartadas. Resumen relevante para la implementación:
- **Dónde vive la lógica nueva**: `praxsa_manager/product/business/pricing.py`, clase `Pricing_Business` (mismo patrón de nombres que `Inventario_Business`/`Proforma_Business`), con `resolve_unit_price(sucursal_id, lamina_id, width) -> Decimal | None` (reusa `Inventario_Business.get_total_meters_window_film_in_inventory` ya existente, toma la primera fila igual que ya hace el frontend con `filmPrices[0]`) y una función pura `calculate_subtotal_venta_instalacion(length, quantity, unit_price, installation_price) -> Decimal`.
- **Dónde se engancha en el serializer**: dentro de `SalesHeaderSerializer.validate(self, data)` (método nuevo, no existe hoy) — no en `create()`. `validate()` corre antes que `create()` dentro de `serializer.is_valid()`/`.save()`, así que si `validate()` resuelve los precios reales y **sobrescribe los valores dentro de `data` antes de devolverlo**, `create()` no necesita ningún cambio: ya persiste `validated_data` tal cual, que para entonces ya trae los valores correctos. Esto mantiene el diff de `create()` en cero y concentra toda la lógica nueva en un solo lugar.
- **Por qué `validate()` y no `create()` para el caso de precio no resoluble**: una excepción/`ValidationError` levantada en `validate()` la captura el `if serializer.is_valid()` que ya existe en `InvoiceView.post` ([invoice.py:27-30](../../praxsa_manager/product/custom_views/invoice.py)) y sale como `400` con el shape estándar de DRF. Si se hiciera en `create()`, caería en el `except Exception` de la vista que hoy responde `500` ([invoice.py:33-34](../../praxsa_manager/product/custom_views/invoice.py)) — no se quiere tocar ese manejo de excepciones en este task (ver ADR-004, Consecuencias).
- **Dinero en `Decimal`**: `resolve_unit_price` y `calculate_subtotal_venta_instalacion` deben trabajar en `Decimal` de punta a punta (los campos del modelo ya son `DecimalField`; los valores que lean de `Car_Model_Part.installation_price`/`precio_venta_sucursal.precio_venta`/`inventario.precio_venta_mtr_lineal` ya vienen como `Decimal` del ORM — no convertir a `float` en ningún punto de este camino nuevo, a diferencia de `get_inventory`/`get_car_part_info` que sí lo hacen).
- **Contrato API**: no cambia el wire format — `SalesHeaderSerializer`/`SaleDetailSerializer.Meta.fields` siguen igual, Angular sigue mandando el mismo payload. Solo cambia qué hace el servidor con esos valores de precio (se ignoran para el cálculo, se sobrescriben antes de persistir). No requiere coordinar un despliegue conjunto con el frontend.
- **Sin migraciones**: no se toca ningún modelo.
- **Rendimiento**: por cada ítem del POST (normalmente pocos, uno por parte del auto) se agrega una consulta a `Car_Model_Part` y una a `Inventario_Business.get_total_meters_window_film_in_inventory` — aceptable para el volumen de este endpoint (una proforma se crea una vez, no en un loop masivo).

## Proposed solution

1. `business/pricing.py` nuevo con `Pricing_Business.resolve_unit_price(...)` y `calculate_subtotal_venta_instalacion(...)`.
2. `SalesHeaderSerializer.validate(self, data)` nuevo: por cada ítem en `data['carPartItems']`, resuelve `Car_Model_Part` (por `data['car_model_id']` + `item['car_part']`) y el precio unitario (por `data['sucursal']` + `item['window_film']` + `item['width']`); si falta cualquiera de los dos, `raise serializers.ValidationError(...)` con un mensaje que identifique el ítem. Si ambos se resuelven, sobrescribe `item['installation_price']`, `item['window_film_price']` y `item['sub_total']` con los valores/calculo reales, acumula el total, y al final sobrescribe `data['total_price']` con la suma. Devuelve `data`.
3. `create()` no se modifica — ya persiste `validated_data`, que a esta altura ya trae los valores correctos.
4. Tests (ver estrategia abajo).

## Files/components affected

**Backend** (nada de frontend — ver justificación de E2E abajo):
- `praxsa_manager/product/business/pricing.py` — nuevo.
- `praxsa_manager/product/serializer/invoice_serializer.py` — `SalesHeaderSerializer.validate()` nuevo.
- `praxsa_manager/product/tests/helpers.py` — agregar `create_precio_venta_sucursal(...)` (falta hoy) para poder testear la rama de override por sucursal.
- `praxsa_manager/product/tests/test_invoice_pricing.py` — nuevo archivo (separado de `test_smoke.py`, que queda como smoke tests puros).

**No tocado** (confirmado en investigación/ADR): `praxsa_manager/product/views.py`, `praxsa_manager/product/admin_config/proforma_admin.py`, `praxsa_manager/product/static/product/sales_event.js`, `praxsa_manager/product/business/proforma.py`, todo `proforma/src/`.

## Implementation steps

1. Agregar `create_precio_venta_sucursal(...)` a `praxsa_manager/product/tests/helpers.py`, siguiendo el patrón de las factories ya existentes.
2. Escribir en `test_invoice_pricing.py` los tests de caracterización del comportamiento **actual**: un `POST /product/invoice` con `sub_total`/`total_price`/`installation_price`/`window_film_price` que no coinciden con `Car_Model_Part.installation_price`/`inventario.precio_venta_mtr_lineal` responde `201` y persiste esos valores manipulados tal cual. Correrlos contra el código sin tocar y confirmar que pasan (evidencia del bug antes del fix).
3. Crear `business/pricing.py` (`Pricing_Business.resolve_unit_price`, `calculate_subtotal_venta_instalacion`) con sus propios tests unitarios: `calculate_subtotal_venta_instalacion` sin DB (función pura, casos con `quantity` > 1); `resolve_unit_price` con DB, cubriendo (a) hay override en `precio_venta_sucursal` → se usa ese, (b) no hay override → cae a `inventario.precio_venta_mtr_lineal`, (c) no hay ninguna fila → devuelve `None`.
4. Implementar `SalesHeaderSerializer.validate()` según la "Proposed solution".
5. **Actualizar las aserciones de los tests del paso 2**: ya no corresponde "se persiste tal cual" — se reemplaza por la aserción de que lo persistido es el valor recalculado por el servidor, sin importar lo que mandó el cliente. Dejar explícito en el mensaje de commit que este test pasa de "documenta el bug" a "prueba de regresión de la corrección" — es un cambio de comportamiento intencional, no una regresión.
6. Agregar tests nuevos para el caso `400`: sin `Car_Model_Part` para `(car_model_id, car_part)` del ítem; sin ninguna fila de inventario/sucursal para `(sucursal, lámina, ancho)`. Confirmar que la proforma **no** se crea (no queda ninguna fila en `Proforma_Header`/`Proforma_Detail`).
7. Agregar un test explícito de que `length`/`width`/`quantity` enviados por el cliente se siguen respetando tal cual en el cálculo (documenta el límite de alcance decidido en el ADR, evita que alguien asuma después que también quedaron validados).
8. Correr `python manage.py test` completo (no solo el archivo nuevo) para confirmar que no se rompió nada de lo existente (`test_smoke.py` incluido — su test de creación de invoice válida debe seguir en `201`).

## Test strategy

Nivel **unitario + integración**, siguiendo el patrón ya usado (`praxsa_manager/product/tests/`, `TestCase` + `helpers.py`). Sin nivel E2E — justificación explícita:
- El contrato de wire format no cambia (Angular sigue mandando el mismo payload que hoy), no hay cambio de navegación ni de formulario multi-paso en el frontend.
- El comportamiento a probar es enteramente server-side (qué hace el backend con los números que recibe) — un test de integración contra el endpoint real (`self.client.post('/product/invoice', ...)`, patrón ya usado en `test_smoke.py`) ya ejercita la ruta completa `InvoiceView.post → SalesHeaderSerializer.validate/create → base de datos` sin necesitar un navegador real.
- `proforma/package.json` no tiene Playwright instalado hoy; agregarlo para este cambio sería sobreingeniería (no hay nada de frontend que verificar).

Casos concretos:
- Caracterización (pre-fix, documentando el bug — paso 2 de implementación).
- Recalculo correcto: unit_price viene de `precio_venta_sucursal` (override) cuando existe.
- Recalculo correcto: unit_price cae a `inventario.precio_venta_mtr_lineal` cuando no hay override.
- `sub_total`/`total_price` recalculados con `quantity > 1` (verifica que la fórmula multiplica correctamente, incluida la parte de instalación).
- Precio manipulado por el cliente (más alto o más bajo que el real) → la proforma se crea igual, pero con el valor recalculado, no el manipulado — el test explícito de "ya no se puede pagar menos manipulando el `sub_total`".
- `400` sin `Car_Model_Part` para el ítem.
- `400` sin inventario/sucursal para la lámina/ancho pedidos.
- `length`/`width`/`quantity` del cliente se respetan tal cual (fuera de alcance validarlos).
- Regresión: el POST válido existente de `test_smoke.py` (`InvoiceCreateEndpointTest`) sigue en `201`.
- Unit tests de `Pricing_Business.calculate_subtotal_venta_instalacion` (sin DB) y `resolve_unit_price` (con DB, las 3 ramas del fallback).

## Acceptance criteria

- [ ] `python manage.py test` pasa completo, incluidos los tests nuevos y los ya existentes (`test_smoke.py`).
- [ ] Un `POST /product/invoice` con precios manipulados por el cliente crea la proforma con el precio recalculado por el servidor, verificado leyendo `Proforma_Header.total_price`/`Proforma_Detail.sub_total` directamente de la base (no solo la respuesta HTTP).
- [ ] Un `POST /product/invoice` con un ítem sin `Car_Model_Part` o sin inventario/sucursal que lo cubra responde `400` y no crea ninguna fila (`Proforma_Header.objects.count()` no cambia).
- [ ] `create()` de `SalesHeaderSerializer` queda sin modificar (el diff se concentra en `validate()` + `business/pricing.py`).
- [ ] Ningún archivo fuera de la lista de "Files/components affected" cambia (en particular, `views.py`, `admin_config/`, `sales_event.js`, `proforma/src/` quedan intactos).

## Risks

- **Riesgo de regresión en producción**: este es el endpoint real que usa la calculadora Angular. Mitigación: cobertura de test explícita en cada rama (fallback de precio, ambas ramas del `400`, `quantity > 1`) antes de mergear — no hay staging activo para probarlo de otra forma (ver ADR-004).
- **`resolve_unit_price` puede devolver más de una fila candidata** (varias bobinas cuyo ancho cubre el pedido) — se decidió tomar la primera, igual que ya hace el frontend hoy (`filmPrices[0]`), para no introducir una regla nueva. Si en el futuro se descubre que esa regla no es la correcta, es un problema preexistente del sistema (ya lo tiene la calculadora), no algo que este cambio introduce.
- **Sin mitigación, aceptado conscientemente**: `length`/`width`/`quantity` manipulados siguen afectando el precio final aunque el precio unitario/instalación ya estén validados — ver ADR-004, fuera de alcance de este task.

## Out of scope

- Retro-adaptar `get_inventory`/`get_car_part_info` a `Pricing_Business.resolve_unit_price` (backlog #2 paso 3, tarea futura separada).
- Validar `length`/`width`/`quantity` contra `Car_Model_Part` (mejora relacionada, no pedida, no decidida).
- Cualquier cambio en `ProformaAdmin`/`sales_event.js` (camino admin, backlog #2 paso 5) o en `convertir_venta_metro_lineal` (backlog #2 paso 6).
- Arreglar el manejo de excepciones de `InvoiceView.post` (`ProformaException` → `500` en vez de `400`) — se evita deliberadamente ese camino en este cambio, no se corrige.

No quedan preguntas abiertas para el usuario — las dos decisiones de negocio pendientes de la investigación (rechazar vs. sobrescribir) ya se resolvieron en ADR-004.

## Dependencias nuevas

Ninguna.
