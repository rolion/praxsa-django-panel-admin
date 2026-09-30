# TASK-mejora-inventario-bobinas: Evaluar y mejorar el manejo del inventario de bobinas

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** NO
**Rama:** task/TASK-mejora-inventario-bobinas
**Pull Request:** [#52](https://github.com/rolion/praxsa-django-panel-admin/pull/52)

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-09-30 | (nuevo) → INVESTIGATION | Task creado | delivery-investigate |
| 2026-09-30 | ARCHITECTURE → PLANNING | Decisiones de asignación/movimientos y de regla de ancho/precio registradas como ADR | delivery-architect |
| 2026-09-30 | PLANNING → INVESTIGATION | Re-investigación pedida por el usuario tras traer master (PR #51: máquina de estados de la orden, `orden_estado.py`, migración 0111). Cambian los llamadores del descuento/devolución; los ADR de este task deben revisarse con `/delivery-architect` | delivery-investigate |
| 2026-09-30 | ARCHITECTURE → PLANNING | ADR revisados tras la re-investigación (PR #51): asignación integrada en `Orden_Estado_Business`, devolución unificada, orden de bloqueo definido, migraciones separadas | delivery-architect |
| 2026-09-30 | PLANNING → ENGINEERING | Plan v1 escrito y PR abierto; queda a la espera de la aprobación humana del plan y de la respuesta a las 4 preguntas abiertas antes de implementar | delivery-plan |

## Investigación

### Requerimiento
"Evalúa la forma en la que manejamos nuestro inventario de bobinas. Cada sucursal tiene sus bobinas asignadas y en ese mismo registro tenemos la cantidad de metros disponibles para instalar; cada que tenemos una orden de trabajo se descuenta del inventario; cada sucursal maneja su propio precio. Al generar una proforma se consulta el inventario de la sucursal seleccionada y devolvemos las bobinas que tienen metros disponibles para los items consultados. Creo que este proceso se puede mejorar."

Es una evaluación abierta: el objetivo de esta etapa es documentar cómo funciona hoy y dónde están los puntos débiles observables, sin proponer solución.

### Hechos encontrados

> **Base actualizada (2026-09-30):** master incorporó el PR #51 (`TASK-estados-proforma-nota-trabajo-nota-venta`). `business/inventario.py`, `business/pricing.py`, `views.py`, `helper/inventory.py` y `Forms/car_model_part.py` **no cambiaron** (los hechos sobre ellos siguen vigentes con las mismas líneas). Lo que cambió son los **llamadores** del descuento y la devolución, que ahora viven en un servicio único de transiciones. Las referencias de `business/proforma.py` de la versión anterior quedan obsoletas y se corrigen abajo.

**Modelo de datos**
- `praxsa_manager/product/models.py:73` — `Window_Film_Reel` (bobina) es un catálogo global: lámina + `width` + `length` + `price`. No pertenece a una sucursal.
- `praxsa_manager/product/models.py:138-152` — `inventario` es la fila "bobina en sucursal": FK a `Sucursal` y a `Window_Film_Reel`, con `quantity`, `to_install` (metros disponibles), `installed`, `original_length`, `date`, `nro_lote`, `precio_compra_mtr_lineal`, `precio_venta_mtr_lineal`, `is_active`. Es a la vez lote de compra, saldo y precio por defecto.
- `praxsa_manager/product/models.py:325-331` — `precio_venta_sucursal` (lámina + ancho + sucursal → `precio_venta`) es el override de precio por sucursal. Sin `UniqueConstraint` (ninguna migración lo define; la búsqueda de `unique` en migraciones no lo encontró).
- `praxsa_manager/product/models.py:247-249` — `Proforma_Detail` guarda `window_film`, `width`, `length` y `inventario` (FK nullable). El `inventario` solo se llena al crear la nota de trabajo (`business/orden_estado.py:111`).
- Todas las FK a `inventario`/`Window_Film_Reel` usan `on_delete=DO_NOTHING` (`models.py:139-140`).
- Última migración: `0111_estados_orden.py` (agrega `status` a `Nota_trabajo` y `Nota_Venta`, `models.py:213-214, 279`; no toca inventario).

**Descuento de inventario**
- `business/orden_estado.py:83-141` — `aprobar_proforma` (transacción atómica) es ahora el único camino de descuento: bloquea la proforma (`_bloquear`, `orden_estado.py:60-65`, `select_for_update` sobre `Proforma_Header`), recorre los detalles y llama `reduce_inventory` por cada uno (`:105-110`). Cantidad a descontar = `length * quantity` (si `quantity > 0`). `Proforma_Business.create_work_note` (`business/proforma.py:59-61`) y la vista `ProformaGenerateNotaView` (`custom_views/ordenes_admin.py:154-183`, `select_for_update` en `:168`) solo delegan; el Django Admin también (`admin_config/proforma_admin.py:236-238`).
- `business/inventario.py:52-70` — `reduce_inventory` filtra `inventario` por sucursal + lámina + ancho **exacto** + `to_install >= length_to_reduce`, ordena por `date` y toma **una sola fila** (`[:1]`). Lee, resta en Python y `save()`. No usa `select_for_update` ni `F()` sobre el inventario; el bloqueo de `orden_estado.py:63` serializa operaciones de **la misma proforma**, no protege filas de inventario compartidas entre proformas distintas. No filtra `is_active` ni `sucursal__enable_to_install_windows_film`.
- Consecuencia observable del `[:1]` con `to_install__gte`: si una necesidad de N metros solo se cubre sumando dos filas (p. ej. 30 m + 30 m para 50 m), `reduce_inventory` lanza `NoHayLaminasDisponibles` (`inventario.py:70`) aunque la disponibilidad agregada sea suficiente. El catálogo, en cambio, suma las filas (ver abajo). En `aprobar_proforma` esa excepción se re-lanza como `Exception` genérica (`orden_estado.py:135-136`) y la vista la responde 409 con el mensaje (`ordenes_admin.py:176-179`).
- Devolución: hay **dos** caminos, ambos leyendo `detalle.inventario` y sumando/restando sin bloqueo: (a) `_cancelar_orden` (`orden_estado.py:198-229`, usado por anular nota de trabajo / anular nota de venta / `abrir_proforma`, `business/proforma.py:38-44`), que llama `return_to_inventory` (`inventario.py:73-83`) y luego pone `detalle.inventario = None` (`orden_estado.py:218-219`); (b) `delete_work_note` (borrado físico desde Django Admin, `business/orden_trabajo.py:89-100`), que hace el `+=`/`-=` directamente sobre el objeto `inventario` y también anula el vínculo. Tras anular, la orden se puede volver a aprobar y el descuento vuelve a asignar una fila (`orden_estado.py:143-160` reutiliza NT/NV).
- Anular una orden cuyo `detalle.inventario` es `None` **omite en silencio** la devolución de ese detalle (`orden_estado.py:212-213`), por lo que la devolución depende por completo de ese FK único.

**Consulta de disponibilidad y precio (proforma)**
- `business/inventario.py:92-126` — `get_total_meters_window_film_in_inventory` agrupa por `(sucursal, lámina, nombre, ancho, precio_venta_mtr_lineal)` y suma `to_install`, con subquery a `precio_venta_sucursal`. Filtra `to_install > 0` pero **no** `is_active`. Usa `bobina__width__gte=width` (ancho **mayor o igual**) cuando `width > 0`.
- Como `precio_venta_mtr_lineal` está en el `GROUP BY`, dos filas de la misma bobina con distinto precio por defecto generan dos grupos separados.
- `business/pricing.py:70-81` — `resolve_unit_price` toma `rows.first()` de esa consulta. Al usar `width__gte`, pedir un ancho puede devolver el precio de una bobina **más ancha** (si es la primera según el orden por nombre/ancho) y no el de la bobina exacta; `has_stock_for_reel` (`pricing.py:57-68`) y `reduce_inventory` sí exigen ancho exacto. Inconsistencia entre las tres reglas.
- `business/pricing.py:20-55` — `get_reel_catalog` (endpoint `ordenes/bobinas`, `custom_views/ordenes_admin.py:410` (vista `OrdenesBobinasView`)): sí filtra `is_active`, `bobina__is_active`, `window_film__is_active`; suma metros por lámina+ancho; **ejecuta una consulta `resolve_unit_price` por cada fila del catálogo** (N+1), y descarta las filas sin precio.
- `views.py:219-250` — endpoint público `get_inventory` (`AllowAny`, usado por la calculadora `proforma/`): devuelve `bobina_metros_disponibles`, `bobina_price` y `bobina_id` (que en realidad es el id de la lámina, `views.py:244`). Contiene `print('inventario', inv)` en producción. Convierte a `float`.
- `proforma/src/app/pages/formulario/formulario.component.ts:238` — la calculadora pública calcula el total en cliente; el servidor lo recalcula (`serializer/invoice_serializer.py:37-71`).
- `Forms/car_model_part.py:74-77, 140-145` — la validación de disponibilidad en el formulario del Django Admin está **comentada**: crear un detalle de proforma en el admin no valida stock; el fallo aparece recién al crear la nota de trabajo.
- `business/pricing.py:99-176` — `build_line_pricing` (API del panel, sin cambios) sí valida stock exacto (`has_stock_for_reel`) al armar la línea, pero solo verifica *existencia* de stock (`to_install > 0`), no que los metros alcancen para `length * quantity`.

**Código duplicado / heredado**
- `helper/inventory.py:4-25` — `Inventory_helper.get_bobina_by_sucursal_lamina_width` y `update_inventory` duplican la lógica de descuento (con `width__gte`, `order_by('date')`, atrapan y `print` la excepción); `Forms/car_model_part.py:149-150` mantiene `update_inventory` que lo invoca.
- `business/inventario.py:36-50, 85-90, 128-132` — métodos con código muerto o sin llamadores (`get_inventory_film_available_film_by_sucursal` tiene un `return` seguido de código inalcanzable; `is_window_film_available` compara `width__gte` con un id de bobina y no tiene llamadores según el grep de este análisis). `business/bobina.py` está vacío (2 líneas comentadas).
- `get_inventario_queryset_by_role` (`inventario.py:14-27`) toma solo `sucursales[0]` del usuario, mientras `ordenes_admin` ya migró a múltiples sucursales (`User_Helper.get_enabled_sucursal_ids`).

**Precios por sucursal**
- `admin_config/precio_venta_sucursal.py:35-47` — la unicidad (sucursal, lámina, ancho) se valida solo en `save_model` del Django Admin y solo en alta; no hay constraint en BD. La subquery `[:1]` de `inventario.py:114-120` toma un precio arbitrario si hubiera duplicados.
- Existen tres fuentes de precio de venta: `Window_Film_Reel.price`, `inventario.precio_venta_mtr_lineal` y `precio_venta_sucursal.precio_venta`; `resolve_unit_price` solo usa las dos últimas (override → default de inventario).

### Hipótesis / supuestos no confirmados
- La operación real probablemente tiene varias filas `inventario` por (sucursal, lámina, ancho) (varios lotes); no se consultó la base de datos real, por lo que no se sabe con qué frecuencia ocurre el caso "ninguna fila sola alcanza pero la suma sí".
- Es probable que el `width__gte` en `get_total_meters_window_film_in_inventory` sea intencional para la calculadora (mostrar bobinas que sirven para un item), pero `resolve_unit_price` reutiliza esa consulta para fijar el precio de una línea con ancho exacto; no se confirmó si se busca precio de la bobina exacta o de la más angosta suficiente.
- Se asume que dos usuarios pueden aprobar proformas distintas concurrentemente en la misma sucursal (posible condición de carrera en `reduce_inventory`); el `select_for_update` sobre la proforma no protege filas de inventario compartidas. No se reprodujo.
- No se confirmó si `Window_Film_Reel.price`/`length` se usan en algún cálculo de negocio actual; en los llamadores revisados no aparecen.
- No se confirmó si hay clientes externos del endpoint público `get_inventory` distintos de `proforma/`.
- Cobertura de tests: existen `tests/test_almacen_module.py`, `tests/test_invoice_pricing.py`, `tests/test_orden_estado_service.py` (incluye ciclo aprobar/anular, `:413-415`); `test_proforma_status_field.py` fue eliminado en master; no se revisó si cubren stock repartido en varias filas ni concurrencia.

### Módulos y dependencias relacionadas
- Backend: `praxsa_manager/product/business/{inventario,pricing,proforma,orden_estado,orden_trabajo}.py`, `helper/inventory.py`, `Forms/car_model_part.py`, `serializer/{almacen_serializer,invoice_serializer,ordenes_serializer}.py`, `custom_views/{almacen_admin,ordenes_admin,bobina}.py`, `views.py`, `admin_config/{inventory,precio_venta_sucursal,report_storage,report_utilidad}.py`, `models.py`.
- Frontend: `proforma/src/app/{service/data.service.ts,pages/formulario/formulario.component.ts,model/lamina.ts,model/report.ts}` (calculadora pública); `panel_admin/src/app/almacen/inventario/*` y `panel_admin/src/app/ordenes/*` (panel).
- Reportes que leen `inventario` (utilidades, storage) dependen de `installed`/`to_install`/precios, por lo que cualquier cambio en el modelo los afecta.

### Implementaciones similares existentes
- `Pricing_Business.get_reel_catalog` + `resolve_unit_price` es la fuente de verdad ya adoptada por el panel de Órdenes (`ADR-modulo-ordenes-proforma-nota-trabajo-api-y-calculo`); `ADR-004` y `ADR-006-admin-price-recalculation-venta-instalacion` establecen el recálculo de precio en servidor.
- `ADR-modulo-almacen-modelo-datos-imagen-soft-delete` define `is_active` y soft delete de inventario/bobina.
- `business/orden_estado.py:60-65` (y `custom_views/ordenes_admin.py:168`) ya usan `select_for_update()` con `transaction.atomic` sobre la proforma: patrón local existente de bloqueo, pero a nivel documento, no de inventario.
- `ADR-estados-proforma-nota-trabajo-nota-venta-maquina-de-estados`: define `Orden_Estado_Business` como único lugar que escribe estados; cualquier cambio a descuento/devolución debe integrarse allí y no reintroducir escrituras de estado dispersas.

### Comportamiento actual
0. (Novedad tras PR #51) Aprobar/anular pasan por `Orden_Estado_Business`.
1. Almacén crea filas `inventario` (sucursal, bobina, `to_install`, precios). 2. El panel/calculadora consulta el catálogo de la sucursal: agrupa filas por lámina+ancho, suma metros y resuelve precio (override por sucursal, si no el precio de la fila). 3. La proforma guarda `window_film`+`width`+`length` sin reservar metros. 4. Al aprobar la proforma (crear la nota de trabajo, `aprobar_proforma`) se descuenta de **una** fila de inventario (la más antigua con saldo suficiente) y se enlaza en `Proforma_Detail.inventario`. 5. Anular la nota de trabajo/venta (equivale a reabrir la proforma) devuelve los metros a esa misma fila y borra el vínculo `detalle.inventario`; al re-aprobar se vuelve a asignar una fila. No existe historial de movimientos: el saldo es el único registro (`to_install`/`installed` editables vía `InventarioUpdateSerializer`, `almacen_serializer.py:81-93`).

### Restricciones
- `docs/CLAUDE.md`: el proyecto no se construyó con buenas prácticas; respetar estilo de capas `business/`.
- ADR-004/ADR-006: el precio nunca se confía del cliente.
- ADRs de almacén: soft delete con `is_active`; edición de inventario limitada para no romper trazabilidad.
- Contrato público de `get_inventory` consumido por `proforma/`; `AllowAny` con throttling (`ADR-005`).
- Reportes de utilidades/almacén y el Django Admin siguen en uso y leen estos modelos.

### Riesgos identificados
- Condición de carrera en descuento/devolución entre proformas distintas (el bloqueo por proforma no cubre filas de inventario compartidas) (lectura-modificación-escritura sin bloqueo ni `F()`), con posible saldo negativo/duplicado.
- Reglas de ancho inconsistentes entre precio (`>=`), stock (`==`) y descuento (`==`): puede cotizarse a un precio que no corresponde a la bobina descontada.
- Catálogo y descuento no coinciden cuando el stock está repartido en varias filas.
- El catálogo/precio disponible no valida metros suficientes para lo pedido, solo `> 0`; el error aparece tarde (al crear la nota de trabajo).
- Sin historial de movimientos: no se puede auditar ni reconstruir el saldo; devolver depende de `Proforma_Detail.inventario`, que puede ser `None` y que ahora se **borra** al anular (`orden_estado.py:218`), por lo que tras una anulación no queda rastro de qué fila se usó.
- Dos implementaciones de devolución (`orden_estado.py:198-229` y `orden_trabajo.py:89-100`) con lógica duplicada; cualquier cambio debe cubrir ambas.
- Consulta N+1 en `get_reel_catalog`; precios sin constraint de unicidad; tres fuentes de precio; código duplicado/muerto.
- Modelo mezcla lote, saldo y precio por defecto en una sola fila; cualquier cambio de esquema toca reportes, admin, panel y calculadora pública.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — "Mejorar el proceso" apunta a decisiones de modelo de datos (¿lote vs. saldo?, ¿historial de movimientos?, ¿reservas?, ¿fuente única de precio?, constraints), de concurrencia y de contrato de API que impactan varios módulos (almacén, órdenes, calculadora pública, reportes). Ante la duda entre NEEDS_PLAN y NEEDS_ARCHITECTURE se prefiere ARCHITECTURE.

### Diseño requerido
**NO** — La evaluación es de backend y modelo de datos; no se identificó una pantalla nueva. Si la arquitectura decide exponer nuevas vistas (p. ej. historial de movimientos), se reevalúa.

## Diseño
_No aplica_

## Arquitectura
- [ADR-mejora-inventario-bobinas-asignacion-y-movimientos](../adr/ADR-mejora-inventario-bobinas-asignacion-y-movimientos.md) — descuento FIFO multi-fila con `select_for_update` (orden de bloqueo: proforma, luego filas por `date`,`id`), tabla aditiva `Inventario_Movimiento`, un único punto de devolución para `_cancelar_orden` y `delete_work_note`, fallback para órdenes anteriores a la migración (rollback: migración reversible; ver riesgo de revertir solo el código).
- [ADR-mejora-inventario-bobinas-regla-ancho-y-precio](../adr/ADR-mejora-inventario-bobinas-regla-ancho-y-precio.md) — ancho exacto único, precio determinista por lote FIFO, `UniqueConstraint` en `precio_venta_sucursal` (migración separada), validación de metros suficientes con el mismo criterio de elegibilidad, catálogo sin N+1, limpieza de código muerto.

Ambos ADR se revisaron el 2026-09-30 tras integrar master (PR #51) y permanecen en estado Propuesto (revisión en su lugar, sin reemplazo, porque no habían llegado a implementarse).

Supuestos de negocio pendientes de confirmar (marcados en los ADR): repartir una necesidad entre varios lotes; precio del lote más antiguo cuando difieren; duplicados actuales en `precio_venta_sucursal`.

## Plan
- [PLAN-2026-09-30-mejora-inventario-bobinas](../plans/PLAN-2026-09-30-mejora-inventario-bobinas.md) — **v1**. 7 fases (modelo de movimientos, lógica de asignación/devolución, conectar llamadores, ancho/precio/validación, unicidad de precios, limpieza, verificación en vivo). E2E: no corresponde (backend puro, contrato de API sin cambios). Sin dependencias nuevas.

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
