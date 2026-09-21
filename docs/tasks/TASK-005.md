# TASK-005: Tests de caracterización del precio actual + recálculo server-side en `SalesHeaderSerializer.create()` (backlog #2, pasos 1-2)

**Etapa actual:** PLANNING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Rama:** _sin asignar todavía_
**Pull Request:** _sin abrir todavía_

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-09-21 | (nuevo) → INVESTIGATION | Task creado a partir de `docs/integration-and-backlog.md`, ítem #2, "pasos 1-2" según la sección 5 (Orden de ataque, línea 229) | delivery-investigate |
| 2026-09-21 | INVESTIGATION → PLANNING | Decisión arquitectónica tomada: recalcular y sobrescribir siempre el precio server-side en `SalesHeaderSerializer.create()` (nunca rechazar por discrepancia, decisión confirmada explícitamente por el usuario); rechazar (400) solo cuando el precio real no se puede resolver; centralizar la resolución de precio unitario en `business/pricing.py::Pricing_Business`, sin retro-adaptar `get_inventory`/`get_car_part_info` en este task | delivery-architect |

## Investigación

### Requerimiento

Tal como lo pidió el usuario: *"tests de caracterización del precio actual (POST con `sub_total` manipulado se persiste tal cual) + recálculo server-side en `SalesHeaderSerializer.create()`"*, identificado como backlog #2, "pasos 1-2".

Dos entregables:
1. Tests que documenten el comportamiento **actual**: un POST a `/product/invoice` con un `sub_total`/`total_price` que no coincide con el precio real (`precio_venta_sucursal`/`inventario.precio_venta_mtr_lineal` + `Car_Model_Part.installation_price`) se persiste tal cual, sin ser corregido ni rechazado.
2. Cambiar `SalesHeaderSerializer.create()` para que el precio se recalcule/valide en el servidor en vez de confiar en lo que envía el cliente.

### Hechos encontrados

**El backend no recalcula ni valida el precio hoy:**
- [invoice_serializer.py:33-48](praxsa_manager/product/serializer/invoice_serializer.py) — `SalesHeaderSerializer.create()` hace `Proforma_Header.objects.create(proforma_created_on=timezone.now(), origen=self.helper.origen_calculadora, **validate_data)`, donde `validate_data` incluye `total_price` tal como lo envió el cliente. Cada ítem se persiste con `Proforma_Detail(proforma_header=invoice, **item)`, donde `item` incluye `sub_total`, `installation_price` y `window_film_price` tal como los envió el cliente. No hay ninguna consulta a `precio_venta_sucursal`, `inventario` ni `Car_Model_Part` en todo el método.
- [invoice.py:20-34](praxsa_manager/product/custom_views/invoice.py) — `InvoiceView.post` valida solo con `serializer.is_valid()` (shape/tipos de campo, no reglas de negocio de precio) y llama `serializer.save()` directo, dentro de una transacción atómica.

**Todo POST a `/product/invoice` crea siempre `sales_type = venta_instalacion` — dato clave para el alcance:**
- [invoice_serializer.py:29-31](praxsa_manager/product/serializer/invoice_serializer.py) — `SalesHeaderSerializer.Meta.fields` no incluye `sales_type`, así que ese campo nunca llega desde el cliente vía este endpoint.
- [models.py:146](praxsa_manager/product/models.py) — `Proforma_Header.sales_type` tiene `default=helper.tipo_venta_instalacion`.
- [helper/proforma.py:13-15](praxsa_manager/product/helper/proforma.py) — confirma que `tipo_venta_instalacion = 'venta_instalacion'` es el default.
- Consecuencia directa: **toda proforma creada por `POST /product/invoice` es siempre `venta_instalacion`**. Esto es específico de este endpoint REST — no es una limitación general del sistema (ver corrección más abajo sobre el admin de Django).

**Corrección a una afirmación de `docs/integration-and-backlog.md` (línea 67): el admin de Django SÍ permite crear una proforma `venta_metro_lineal` desde cero, no solo convertir una existente.** El documento fuente afirma que "el tipo `venta_metro_lineal` solo se alcanza a través de una acción masiva del admin de Django (`ProformaAdmin`, que invoca `convertir_venta_metro_lineal`)". Verificado directamente en el código, esto es incompleto:
  - [proforma_admin.py:117](praxsa_manager/product/admin_config/proforma_admin.py) — `sales_type` está en el `fieldset` del formulario de alta/edición de `ProformaAdmin`.
  - [proforma_admin.py:199-205](praxsa_manager/product/admin_config/proforma_admin.py) — `get_readonly_fields` devuelve `[]` cuando `obj is None` (formulario de **alta**, creación nueva) y recién marca `sales_type`/`sucursal` como readonly cuando `obj` ya existe (edición). Es decir, **al crear una proforma nueva desde el admin, `sales_type` es un `<select>` editable**, no queda fijo en `venta_instalacion`.
  - [sales_event.js:16-23](praxsa_manager/product/static/product/sales_event.js) — `get_sale_type_element()` lee `$('#id_sales_type').val()` cuando el campo es un `<select>` (formulario de alta), y solo cae al texto de solo-lectura (`.field-sales_type .readonly`) cuando ya no es editable (formulario de edición).
  - [sales_event.js:373](praxsa_manager/product/static/product/sales_event.js) — hay un listener `.change()` sobre `select[name="sales_type"]` que dispara `calculate_subtotal`, la cual ([sales_event.js:270-292](praxsa_manager/product/static/product/sales_event.js)) lee el `sales_type` actual y aplica en vivo la fórmula `venta_instalacion` o la rama `else` (metro lineal, sin multiplicar por `quantity`) según lo seleccionado — mismo mecanismo de eventos JS que describió el usuario.
  - Consecuencia: un usuario del admin puede armar una proforma `venta_metro_lineal` de punta a punta en el formulario de alta (no solo convirtiendo una `venta_instalacion` ya creada), y en ese camino el subtotal por ítem se calcula client-side con la fórmula de `sales_event.js` (rama `else`, sin `quantity`) — **distinta** de la que usa `convertir_venta_metro_lineal` (que sí multiplica por `quantity`, [business/proforma.py:148](praxsa_manager/product/business/proforma.py)). La divergencia de fórmulas de la sección 2.1 del backlog es alcanzable por dos caminos de creación reales, no por uno "correcto" (alta) y uno "de conversión" (bulk action) como sugiere el documento fuente.
  - Esto **no cambia el alcance ni el veredicto de este task** (que se limita a `SalesHeaderSerializer.create()`/`InvoiceView`, camino REST usado por Angular, donde `sales_type` nunca llega del cliente — hecho verificado independientemente arriba). Pero si una tarea futura toca `ProformaAdmin`/`sales_event.js` (backlog #2, pasos 5-6), debe partir de esta corrección y no de la afirmación original del documento.

**La fórmula de `venta_instalacion` es consistente entre las dos implementaciones cliente existentes (no hay ambigüedad de negocio para el caso que este task toca):**
- [formulario.component.ts:238](proforma/src/app/pages/formulario/formulario.component.ts) (Angular): `totalPrice = (carPartLength * itemQuantity * filmPrice.bobina_price) + (carPartInstallationPrice * itemQuantity)`.
- [sales_event.js:272-281](praxsa_manager/product/static/product/sales_event.js) (JS del admin, rama `venta_instalacion`): `subtotal = ((length * quantity) * film_price) + (installation_price * quantity)` — misma fórmula.
- [formulario.component.ts:248-249](proforma/src/app/pages/formulario/formulario.component.ts) — el `total_price` de cabecera que arma Angular es la suma de los `sub_total` de cada ítem (`this.invoiceItem.reduce((acc, current) => acc += current.sub_total, 0)`), sin descuento.
- `Proforma_Header.discount` tampoco está en `SalesHeaderSerializer.Meta.fields` ([invoice_serializer.py:31](praxsa_manager/product/serializer/invoice_serializer.py)) — siempre queda en su default `0` al crear vía este endpoint, así que un recálculo no necesita considerar descuento en este camino.

**El precio unitario ("¿cuánto cuesta el metro de esta lámina en esta sucursal?") no tiene una única función reusable — está duplicado en al menos 3 lugares, ninguno pensado para devolver un único precio Decimal dado `(sucursal, lamina, width)`:**
- [views.py:195-223](praxsa_manager/product/views.py) `get_inventory` — resuelve `precio = precio_sucursal if precio_sucursal is not None else precio_venta_mtr_lineal` en Python puro sobre el resultado de `Inventario_Business.get_total_meters_window_film_in_inventory` ([business/inventario.py:75-109](praxsa_manager/product/business/inventario.py)); devuelve una lista (agrupada por lámina+ancho), y convierte el precio a `float(...)` antes de responder ([views.py:216](praxsa_manager/product/views.py)).
- [views.py:54-141](praxsa_manager/product/views.py) `get_car_part_info` — misma regla pero con `Coalesce(F('precio_sucursal'), F('precio_venta_mtr_lineal'))` directamente en el ORM ([views.py:75-78](praxsa_manager/product/views.py)); también devuelve `float(inv.precio_final or 0)` ([views.py:121](praxsa_manager/product/views.py)).
- [business/inventario.py:19-33](praxsa_manager/product/business/inventario.py) `Inventario_Business.get_inventory_film_available_film_by_sucursal` — un tercer uso del mismo patrón de subquery sobre `precio_venta_sucursal`, pero **sin** el fallback a `precio_venta_mtr_lineal` (deja `None` si no hay override de sucursal); tiene además código muerto después de un `return` (líneas 32-33, un segundo `return result` con `result` nunca asignado — nunca se ejecuta, no es un bug activo).
- Ninguno de los tres métodos de `business/inventario.py` expone una función tipo `resolve_unit_price(sucursal, lamina, width) -> Decimal` para un solo ítem — todos devuelven querysets/listas agregadas pensadas para poblar catálogos en la UI, no para validar un ítem puntual de una proforma que se está creando.

**El precio de instalación real por (modelo, ítem) sí tiene una fuente única, pero tampoco se reutiliza en `create()`:**
- [models.py:41-47](praxsa_manager/product/models.py) — `Car_Model_Part.installation_price`, con `UniqueConstraint(['car_model_id', 'car_part_id'])` ([models.py:48-52](praxsa_manager/product/models.py)), así que `(car_model_id, car_part_id) → installation_price` es una relación 1:1 bien definida.
- [views.py:94-102](praxsa_manager/product/views.py) — ya se consulta así en `get_car_part_info` para poblar la calculadora, pero `SalesHeaderSerializer.create()` no vuelve a consultarlo — confía en el `installation_price` que manda el cliente por ítem.

**Los precios viajan como `float` de ida y vuelta con el cliente, aunque el modelo los guarda como `Decimal`:**
- Todos los campos de precio son `DecimalField` (`Car_Model_Part.installation_price` [models.py:47], `Window_Film_Reel.price` [models.py:74], `Proforma_Header.total_price` [models.py:160], `Proforma_Detail.sub_total/installation_price/window_film_price` [models.py:232-234]).
- Pero `get_inventory` y `get_car_part_info` convierten el precio resuelto a `float(...)` antes de responder al cliente ([views.py:216](praxsa_manager/product/views.py), [views.py:121](praxsa_manager/product/views.py)), y tanto Angular (`filmPrice.bobina_price` es un `number` JS) como el JS del admin (`parseFloat(...)`, [sales_event.js:274-278](praxsa_manager/product/static/product/sales_event.js)) operan en punto flotante antes de mandar `sub_total`/`total_price` de vuelta como JSON. `docs/CLAUDE.md` exige `Decimal` para dinero, y el servidor sí lo respeta en su propio cálculo — pero el valor que hoy llega del cliente ya pasó por al menos una conversión a `float` en el camino, incluso cuando el cliente "no manipula" nada intencionalmente.

**El camino de admin (`ProformaAdmin`) tampoco recalcula al crear, y está fuera del alcance de este task:**
- [admin_config/proforma_admin.py:149-160](praxsa_manager/product/admin_config/proforma_admin.py) — `save_related` solo ajusta `total_price` restando el `sub_total` de ítems **eliminados**; no recalcula nada al crear una proforma nueva desde el admin.
- Backlog #2 (`docs/integration-and-backlog.md:149`) ya separa esto como su propio paso 5, distinto de los pasos 1-2/1-4 de esta tarea.

**Ya existe un harness de tests backend reusable (backlog #8, paso 1, ya hecho):**
- `praxsa_manager/product/tests/helpers.py` y `praxsa_manager/product/tests/test_smoke.py` (commit `493c982`, ya en esta rama). `helpers.build_full_scenario()` arma usuario+token, sucursal, marca/modelo, `Car_Model_Part` (con `installation_price=Decimal('50.00')`), lámina, bobina e `inventario` (con `precio_venta_mtr_lineal=Decimal('120.00')`) — listo para usarse como base de los tests de caracterización sin escribir fixtures nuevas.
- `InvoiceCreateEndpointTest.test_invoice_post_returns_201_and_created_id` ([test_smoke.py:56-92](praxsa_manager/product/tests/test_smoke.py)) ya muestra el shape exacto de un POST válido a `/product/invoice`, incluida la forma de `carPartItems`.

### Hipótesis / supuestos no confirmados

- No se confirmó si `ProformaAdmin.save_model` (código no revisado en profundidad, fuera del alcance de esta tarea) recalcula algo al crear — no es relevante porque este task solo toca `SalesHeaderSerializer.create()`/`InvoiceView`, pero se marca como no verificado por si una futura tarea lo necesita.
- No se confirmó con negocio si, ante una discrepancia entre el precio recalculado en el servidor y el enviado por el cliente, el comportamiento esperado es **rechazar** la request (400) o **sobrescribir silenciosamente** con el valor recalculado y persistir igual. `docs/integration-and-backlog.md` recomienda recalcular ("ignorando/validando `sub_total`/`total_price` recibidos", línea 148) pero no decide entre ambas opciones — es una decisión de producto, no solo técnica, y no está resuelta en ningún documento existente.
- No se confirmó si algún otro cliente (aparte de la Angular actual) consume `POST /product/invoice` y podría verse afectado si el servidor empieza a rechazar/corregir precios que hoy acepta tal cual.

### Módulos y dependencias relacionadas

- **Serializer a modificar**: `praxsa_manager/product/serializer/invoice_serializer.py` (`SalesHeaderSerializer.create()`, `SaleDetailSerializer`).
- **Vista que lo invoca**: `praxsa_manager/product/custom_views/invoice.py` (`InvoiceView.post`).
- **Lógica de negocio de precio a reusar/centralizar**: `praxsa_manager/product/business/inventario.py` (resolución de precio unitario, hoy sin una función de "un solo precio"), `praxsa_manager/product/models.py` (`Car_Model_Part.installation_price`, `precio_venta_sucursal`, `inventario.precio_venta_mtr_lineal`).
- **Vistas con lógica de precio duplicada, no tocadas por este task pero relevantes como referencia**: `praxsa_manager/product/views.py` (`get_inventory`, `get_car_part_info`).
- **Harness de tests a reusar**: `praxsa_manager/product/tests/helpers.py`, `praxsa_manager/product/tests/test_smoke.py` (o un archivo nuevo, p. ej. `test_invoice_pricing.py`, siguiendo el mismo patrón).
- **No tocado por este task** (explícitamente fuera de alcance, según backlog #2 pasos 5-6): `admin_config/proforma_admin.py`, `static/product/sales_event.js`, `business/proforma.py::convertir_venta_metro_lineal`.

### Implementaciones similares existentes

- No existe hoy una función de negocio que resuelva un único precio unitario Decimal para `(sucursal, lamina, width)` — lo más cercano son los tres patrones duplicados descritos arriba (`get_inventory`, `get_car_part_info`, `get_inventory_film_available_film_by_sucursal`), cada uno con una variante ligeramente distinta de la misma regla `precio_venta_sucursal` → fallback `precio_venta_mtr_lineal`.
- El harness de tests de `product/tests/helpers.py` es el patrón a seguir para los tests de caracterización — evita reinventar fixtures.

### Comportamiento actual

Hoy, `POST /product/invoice` con un `sub_total`/`total_price`/`installation_price`/`window_film_price` arbitrario (sin relación con `precio_venta_sucursal`/`inventario.precio_venta_mtr_lineal`/`Car_Model_Part.installation_price` reales) responde `201` y persiste exactamente esos valores en `Proforma_Header.total_price` y `Proforma_Detail.sub_total`/`installation_price`/`window_film_price`, sin ninguna verificación server-side. Esto ya está confirmado como hallazgo (BIZ-01 en ambas auditorías, sección 2.3 y 3.2 de `docs/integration-and-backlog.md`) y se reconfirmó línea por línea en esta investigación.

### Restricciones

- `docs/CLAUDE.md`: "El dinero se maneja con `Decimal`, nunca con `float`" — el modelo ya lo cumple; el recálculo debe seguir usando `Decimal` de punta a punta (cuidado con reintroducir `float` al comparar contra lo recibido).
- `docs/CLAUDE.md`: "Todo cambio de lógica de negocio lleva su test" — aplica directamente; el paso 1 (caracterización) ya es, en sí mismo, la base de test para el paso 2.
- `docs/CLAUDE.md`: "Cambios pequeños: un objetivo por cambio, pensado para un PR" — el propio backlog ya divide el ítem #2 en 6 pasos por esta razón; este task cubre solo "pasos 1-2" según lo pidió el usuario.
- `docs/CLAUDE.md`: "Antes de cambios que afecten varios archivos, proponer un plan y esperar confirmación" — aplica si el recálculo termina extrayendo/centralizando la resolución de precio unitario (toca `business/inventario.py` además del serializer).
- `docs/integration-and-backlog.md:92` (sección 2.3, recomendación) — sugiere expresamente no resolver esto duplicando la lógica de precio una cuarta vez, sino centralizarla en `business/` antes de usarla en `create()`.

### Riesgos identificados

- **Inconsistencia dentro del propio documento fuente**: `docs/integration-and-backlog.md` describe el ítem #2 de dos formas distintas para la etiqueta "pasos 1-2". La sección 4 (líneas 144-150, la definición canónica del backlog #2) dice: paso 1 = tests de caracterización, paso 2 = **resolver con negocio la fórmula de `venta_metro_lineal`** (bloqueante), paso 3 = centralizar el precio unitario, paso 4 = crear el cálculo de subtotal centralizado y usarlo en `SalesHeaderSerializer.create()`. La sección 5 (línea 229, "orden de ataque") en cambio llama "pasos 1-2" a *"tests de caracterización + recálculo server-side de precio en `SalesHeaderSerializer.create()`"* — que en términos de la sección 4 es más parecido a los pasos 1 + 3 + 4 que a los pasos 1+2 literales. El pedido del usuario cita textualmente la frase de la sección 5, así que se interpretó el alcance como esa frase literal (tests + recálculo en `create()`), no como los dos primeros ítems numerados de la sección 4.
- Gracias al hallazgo de que `SalesHeaderSerializer` nunca acepta `sales_type` (ver arriba), **la pregunta de negocio bloqueante sobre `venta_metro_lineal` (sección 6, línea 251) no bloquea este task** — solo aplica a `convertir_venta_metro_lineal`, que este task no toca. Esto reduce el riesgo real de "pasos 1-2" frente a lo que una lectura superficial del backlog sugeriría.
- Sí queda abierta una decisión de diseño no trivial: **cómo resolver el precio unitario dentro de `create()` sin crear una cuarta implementación duplicada** de la regla `precio_venta_sucursal` → fallback `precio_venta_mtr_lineal`. Extraerla a una función reusable en `business/inventario.py` toca ese archivo además del serializer, y decidir su forma (firma, dónde vive, si la reusan también `get_inventory`/`get_car_part_info` en el mismo cambio o se deja para después) es una decisión de arquitectura, no de implementación directa.
- **Decisión de producto no resuelta**: ¿rechazar (400) o sobrescribir con el valor recalculado cuando el precio del cliente no coincide? Afecta directamente el contrato del endpoint que ya consume el frontend Angular en producción — un `400` inesperado rompería el flujo de creación de proformas si el cliente y el servidor difieren aunque sea por redondeo de `float`.
- El riesgo de `float` en el camino cliente (ver hallazgo arriba) significa que una comparación estricta `Decimal(cliente) == Decimal(recalculado)` puede fallar por ruido de redondeo aun sin manipulación maliciosa — el diseño del recálculo necesita decidir una tolerancia o, más simple, no comparar y simplemente sobrescribir siempre con el valor recalculado (evita el problema de tolerancia, pero es en sí una decisión de producto, ver punto anterior).
- Este es el endpoint real que usa la calculadora en producción (`origen_calculadora`) — un error en el recálculo puede bloquear la creación de proformas legítimas, no es un cambio de bajo riesgo como el de TASK-001.

### Veredicto de complejidad

**NEEDS_ARCHITECTURE** — El paso de tests de caracterización (mitad 1) es, por sí solo, `NEEDS_PLAN` o incluso casi trivial: ya existe el harness (`product/tests/helpers.py`) y el shape del POST está confirmado. Pero la segunda mitad pedida explícitamente por el usuario ("recálculo server-side en `SalesHeaderSerializer.create()`") no es un cambio acotado: (a) requiere decidir cómo resolver el precio unitario sin sumar una cuarta implementación duplicada de una regla de negocio que ya está repetida tres veces (`views.py` x2, `business/inventario.py` x1) — coincide con el indicador "problemas con la arquitectura existente"; (b) toca potencialmente más de un módulo (`serializer/`, `business/`) si se centraliza como recomienda el propio backlog; y (c) deja abierta una decisión de producto no documentada (rechazar vs. sobrescribir ante discrepancia, y cómo tratar el ruido de `float`) que condiciona el diseño técnico y afecta el contrato de un endpoint usado en producción. Ninguno de estos tres puntos se resuelve solo leyendo el código existente — encajan con los criterios que `delivery-architect` evalúa, y es más barato confirmar ahí "alcanza con una función simple" que descubrirlo a mitad de un PR de implementación.

## Arquitectura

**[ADR-004: Recalcular el precio server-side en `SalesHeaderSerializer.create()`, ignorando siempre el enviado por el cliente](../adr/ADR-004-server-side-price-recalculation.md)**

Decisión: `SalesHeaderSerializer.create()` deja de confiar en `total_price`/`sub_total`/`installation_price`/`window_film_price` enviados por el cliente. En `validate()`, por cada ítem, resuelve el precio unitario real de la lámina (`(sucursal, lámina, ancho)`) y el `installation_price` real (`Car_Model_Part`), y calcula `sub_total`/`total_price` con la fórmula única de `venta_instalacion` (el único `sales_type` alcanzable desde este endpoint). El servidor **siempre sobrescribe** con el valor recalculado — nunca rechaza por discrepancia con lo enviado por el cliente (decisión de negocio confirmada explícitamente por el usuario en esta sesión). Solo rechaza (`400`, vía `ValidationError` en `validate()`) cuando el precio real no se puede resolver (datos faltantes genuinos, no manipulación). La resolución de precio unitario se centraliza en una función nueva (`business/pricing.py::Pricing_Business.resolve_unit_price`), reusando `Inventario_Business.get_total_meters_window_film_in_inventory` ya existente — sin retro-adaptar `get_inventory`/`get_car_part_info` en este task (queda para el paso 3 del backlog #2, ya planificado por separado). `length`/`width`/`quantity` del ítem siguen confiándose del cliente (fuera de alcance, ver ADR). Ver el ADR para las alternativas descartadas y la estrategia de rollback/mitigación.

## Plan
_Pendiente_

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
