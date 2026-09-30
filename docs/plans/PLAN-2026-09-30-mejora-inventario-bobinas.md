# PLAN-2026-09-30-mejora-inventario-bobinas (v1)

**Task:** TASK-mejora-inventario-bobinas
**DDRs relacionados:** Ninguno (backend puro, Diseño requerido: NO)
**ADRs relacionados:**
- [ADR-mejora-inventario-bobinas-asignacion-y-movimientos](../adr/ADR-mejora-inventario-bobinas-asignacion-y-movimientos.md)
- [ADR-mejora-inventario-bobinas-regla-ancho-y-precio](../adr/ADR-mejora-inventario-bobinas-regla-ancho-y-precio.md)
- Contexto vigente: [ADR-estados-proforma-nota-trabajo-nota-venta-maquina-de-estados](../adr/ADR-estados-proforma-nota-trabajo-nota-venta-maquina-de-estados.md), [ADR-modulo-ordenes-proforma-nota-trabajo-api-y-calculo](../adr/ADR-modulo-ordenes-proforma-nota-trabajo-api-y-calculo.md), [ADR-modulo-almacen-modelo-datos-imagen-soft-delete](../adr/ADR-modulo-almacen-modelo-datos-imagen-soft-delete.md)

## Objective
Que lo que la proforma ofrece (metros y precio de una bobina en una sucursal) sea exactamente lo que la aprobación puede descontar, sin carreras entre órdenes y con rastro auditable de qué fila de inventario aportó cuántos metros.

## Context
Ver investigación en `docs/tasks/TASK-mejora-inventario-bobinas.md`. Resumen: el catálogo suma filas de `inventario` pero el descuento usa una sola; el precio se resuelve con ancho `>=` mientras stock y descuento exigen ancho exacto; el bloqueo actual es por proforma, no por inventario; la devolución tiene dos implementaciones y el vínculo `detalle.inventario` se borra al anular.

## Current behavior
- Descuento: `Orden_Estado_Business.aprobar_proforma` (`business/orden_estado.py:83-141`) → `Inventario_Business.reduce_inventory` (`business/inventario.py:52-70`): una fila, ancho exacto, `to_install >= necesidad`, lectura-resta-guarda sin bloqueo, sin filtrar `is_active`.
- Devolución: `_cancelar_orden` (`orden_estado.py:198-229`) y `delete_work_note` (`business/orden_trabajo.py:76-117`), ambos vía `detalle.inventario`; omiten en silencio los detalles con `inventario` nulo.
- Precio: `resolve_unit_price` (`business/pricing.py:70-81`) reutiliza `get_total_meters_window_film_in_inventory` (`inventario.py:92-126`, `width__gte`, agrupa por precio, `.first()`).
- Catálogo del panel: `get_reel_catalog` (`pricing.py:20-55`), una consulta de precio por fila. Vista `OrdenesBobinasView` (`custom_views/ordenes_admin.py:410`).
- `build_line_pricing` (`pricing.py:99-176`) solo comprueba `to_install > 0`.
- `precio_venta_sucursal` (`models.py:328`) sin unicidad en BD.
- Consumidores del FK `Proforma_Detail.inventario`: `helper/pdf.py:299` (`nro_lote`) y `admin_config/report_utilidad.py:63-68` (ingresos por fila vía `lamina_inventario`).

## Expected behavior
- Aprobar una proforma reparte la necesidad FIFO entre las filas elegibles de la bobina (activas, sucursal habilitada, ancho exacto) bajo bloqueo; si la suma no alcanza, falla sin descontar nada.
- Cada descuento y devolución deja movimientos; anular devuelve exactamente lo descontado, fila por fila, tanto desde la API/servicio como desde el borrado físico del Django Admin.
- El precio de una línea es el override de sucursal o el precio de la fila FIFO que se consumiría, siempre con ancho exacto.
- Armar una línea en la API del panel rechaza (400) si los metros elegibles no alcanzan.
- El catálogo del panel se resuelve sin N+1 y con el mismo contrato.
- Sólo un precio por (sucursal, lámina, ancho) en base de datos.

## Architecture considerations
Resumen de los ADR (no se re-decide aquí):
- **Bloqueo:** proforma primero (ya existe, `orden_estado.py:60-65`), luego filas de inventario con `select_for_update()` ordenadas por `date`, `id`. Base PostgreSQL (`settings.py:155`).
- **Modelo:** tabla nueva aditiva `Inventario_Movimiento`; se conservan `to_install`/`installed` y `Proforma_Detail.inventario` (primera fila usada) por compatibilidad.
- **Un solo punto de devolución** en `Inventario_Business`, usado por `_cancelar_orden` y `delete_work_note`; fallback para órdenes previas a la migración (sin movimientos, con FK); log de error si no hay ninguno.
- **Criterio de elegibilidad único** de filas en `Inventario_Business`, reutilizado por asignación, validación de metros, precio y catálogo.
- **Contrato API:** no cambia (catálogo `ReelCatalogSerializer`, `get_inventory` público con `width__gte` y misma forma de respuesta). Sin despliegue coordinado con Angular.
- **Dinero/precisión:** todo en `Decimal`; se elimina `float(width)` en `resolve_unit_price`.
- **Migraciones:** dos, independientes y reversibles, posteriores a `0111_estados_orden` (el número exacto lo toma el engineer al implementar, por si entra otra migración antes): (A) `Inventario_Movimiento`; (B) `UniqueConstraint` de `precio_venta_sucursal` con verificación previa de duplicados que aborta con listado, sin borrar datos.
- **Permisos:** sin cambios.
- **Integración con PR #51:** los cambios de estado siguen exclusivamente en `Orden_Estado_Business`; el inventario se modifica sólo desde `Inventario_Business`.

## Proposed solution
Implementar los dos ADR sobre el flujo de órdenes actual, en fases pequeñas donde cada una deja la suite verde: (1) modelo de movimientos; (2) lógica de asignación/devolución en `Inventario_Business`; (3) conectar los tres llamadores; (4) regla de ancho, precio y validación de metros; (5) unicidad de precios; (6) limpieza de código muerto. Se descartaron (ver ADR): reservas al crear proforma, `F()` condicional, ledger puro y parchear las dos devoluciones por separado.

## Files/components affected
**Backend (`praxsa_manager/product/`)**
- `models.py` — nuevo `Inventario_Movimiento`; `Meta.constraints` en `precio_venta_sucursal`.
- `migrations/` — dos migraciones nuevas (A y B), con reverso.
- `business/inventario.py` — elegibilidad, `reduce_inventory` (nuevo contrato: asignaciones), devolución por detalle, consulta de precio exacto, metros disponibles.
- `business/orden_estado.py` — `aprobar_proforma` (`:102-119`), `_cancelar_orden` (`:211-219`).
- `business/orden_trabajo.py` — `delete_work_note` (`:89-100`).
- `business/pricing.py` — `resolve_unit_price`, `has_stock_for_reel`/nueva validación de metros, `get_reel_catalog`, `build_line_pricing`.
- `views.py` — quitar `print` de `get_inventory` (`:246`).
- `helper/inventory.py` (eliminar), `Forms/car_model_part.py` (`is_inventory_valid`, `update_inventory`, imports del helper), `business/bobina.py` (eliminar), métodos muertos de `business/inventario.py`.
- `tests/` — ver estrategia.
**Frontend:** ninguno.
**Sólo lectura/verificación:** `helper/pdf.py:299`, `admin_config/report_utilidad.py:63-68`, `admin_config/report_storage.py`.

## Implementation steps
**Fase 0 — Prerrequisitos**
0.1. Correr en la base de desarrollo/producción una consulta que liste duplicados de `precio_venta_sucursal` por (`sucursal`, `lamina`, `width`); resolver a mano antes de la fase 5.
0.2. Confirmar con el usuario los supuestos de negocio (ver "Out of scope / preguntas abiertas").

**Fase 1 — Modelo de movimientos**
1.1. Agregar `Inventario_Movimiento` (`inventario` FK, `proforma_detail` FK nullable, `tipo` egreso/devolucion, `metros` Decimal > 0, `created_on`, `created_by` nullable) con `on_delete=DO_NOTHING` como el resto y índice por `proforma_detail`.
1.2. Migración A aditiva; verificar `migrate` adelante y atrás en Postgres.

**Fase 2 — Lógica en `Inventario_Business`**
2.1. Un método/queryset de elegibilidad: sucursal + lámina + ancho exacto + `is_active` (inventario y bobina) + sucursal habilitada + `to_install > 0`, orden `date`, `id`.
2.2. `reduce_inventory`: bloquear filas elegibles (`select_for_update`), repartir FIFO, actualizar `to_install`/`installed`, crear un `egreso` por fila, devolver las asignaciones; `NoHayLaminasDisponibles` sin efectos parciales si no alcanza.
2.3. Operación única de devolución por detalle: neto por fila desde movimientos (con bloqueo en el mismo orden); fallback a `detalle.inventario` si no hay movimientos; log de error si no hay nada. Crea `devolucion` por fila.
2.4. Metros disponibles elegibles (suma) para la validación de la línea.

**Fase 3 — Conectar llamadores**
3.1. `aprobar_proforma`: adaptar al nuevo retorno; `detalle.inventario` = primera fila usada; el resumen de la nota de trabajo sigue agrupando por lámina y ancho.
3.2. `_cancelar_orden` y `delete_work_note`: usar la operación única; mantener `detalle.inventario = None` y el orden de estados de la máquina de estados.

**Fase 4 — Ancho, precio y validación**
4.1. `resolve_unit_price`: consulta propia con ancho exacto; precio = override de `precio_venta_sucursal` o `precio_venta_mtr_lineal` de la primera fila elegible FIFO; `Decimal` sin `float`.
4.2. `build_line_pricing`: rechazar con `ProformaException` si los metros elegibles < `length * quantity` (para metro lineal, `quantity` vale 0 → usar `length`, igual que el descuento).
4.3. `get_reel_catalog`: resolver overrides y precios por defecto en un número constante de consultas.
4.4. `get_inventory` público: conserva `width__gte` y respuesta; sólo se quita el `print`.

**Fase 5 — Unicidad de precios**
5.1. Migración B: verificación previa de duplicados (aborta con listado) y `UniqueConstraint(sucursal, lamina, width)`; reverso elimina la constraint.
5.2. Mantener el chequeo del admin (`admin_config/precio_venta_sucursal.py:35-47`) como mensaje amigable.

**Fase 6 — Limpieza**
6.1. Eliminar `helper/inventory.py`, `Forms/car_model_part.py:is_inventory_valid/update_inventory` (sin llamadores externos verificados por búsqueda), `business/bobina.py`, y los métodos muertos de `Inventario_Business` (`get_inventory_film_available_film_by_sucursal`, `is_window_film_available`, `available_window_film_reel_in_inventory_to_sell`, `get_inventory_window_film`) tras confirmar otra vez con búsqueda que no tienen llamadores. Se conservan `get_inventory_by_sucursal`, `get_inventory_window_film_reel_widths` y `get_user_inventory_window_films` (usados por `views.py` y `proforma_admin.py`).

**Fase 7 — Verificación**
7.1. Suite completa de backend en verde.
7.2. Prueba manual en vivo (panel + Django Admin): aprobar con stock repartido en dos filas, anular, re-aprobar, borrar nota de trabajo desde admin; comprobar saldos, movimientos, PDF de proforma y reporte de utilidades.

## Test strategy
Patrón existente: `praxsa_manager/product/tests/` con `helpers.py` (`create_inventario`, `create_full_proforma`, `create_precio_venta_sucursal`, etc.) y la suite de `test_orden_estado_service.py`.

**Unitarios/integración (Django, Postgres real):**
- Asignación: una fila suficiente; stock repartido en 2–3 filas (FIFO por `date`,`id`); suma insuficiente → `NoHayLaminasDisponibles` y saldos intactos; fila `is_active=False`, bobina inactiva o sucursal deshabilitada excluidas; ancho distinto excluido; metro lineal (`quantity=0`) y venta-instalación (`length*quantity`).
- Movimientos: un `egreso` por fila tocada con metros correctos; suma de egresos = necesidad.
- Devolución: revierte exactamente lo descontado fila por fila (vía `_cancelar_orden` y vía `delete_work_note`); doble anulación no devuelve dos veces; fallback para detalle con `inventario` sin movimientos; detalle sin nada → log de error, sin devolver ni fallar.
- Ciclo aprobar → anular → re-aprobar deja saldos idénticos a los iniciales (regresión de `test_orden_estado_service.py`, actualizando el assert de `:315` sólo si cambia el contrato).
- Precio: ancho exacto (no toma una bobina más ancha); override tiene prioridad; con dos lotes de precio distinto usa el de la fila FIFO; sin coincidencia → `None`; `Decimal` sin pérdida (actualizar `tests/test_invoice_pricing.py` donde asuma el `>=`).
- Validación de línea: metros suficientes/insuficientes en `build_line_pricing` para ambos tipos de venta; paridad con `tests/test_ordenes_price_parity.py`.
- Catálogo: número constante de consultas (`assertNumQueries` con 1 y con N bobinas); mismo contenido y orden que antes; filtra inactivas.
- Endpoint público `get_inventory`: contrato sin cambios (`tests/test_public_catalog_endpoints.py`).
- Migraciones: A adelante/atrás; B con y sin duplicados (aborta con listado sin modificar datos), reverso.
- Concurrencia (`TransactionTestCase` con dos hilos, Postgres): dos aprobaciones de proformas distintas sobre las mismas filas → nunca saldo negativo ni descuento doble; el total descontado nunca excede el stock; una de ellas puede fallar por falta de stock.
- Sin duplicar: reportes (`report_storage`, `report_utilidad`) sólo se comprueba que siguen ejecutando sobre datos con reparto multi-fila.

**E2E (Playwright): NO corresponde.** El cambio es backend y de modelo de datos; el contrato de la API del panel y de la calculadora pública no cambia, no hay pantallas ni flujos de navegación nuevos, y la integración real front-back de aprobar/anular ya la cubren `test_orden_flujo_completo.py` y los tests de API existentes. Además Playwright no está instalado en el proyecto. La verificación en vivo del paso 7.2 es manual.

## Acceptance criteria
1. Con stock repartido (p. ej. 30 m + 30 m), aprobar una necesidad de 50 m tiene éxito, descuenta FIFO y deja dos movimientos `egreso`; si la suma es insuficiente, falla sin cambios de saldo.
2. Anular la nota de trabajo o de venta, o borrar la nota desde el Django Admin, devuelve exactamente los metros descontados a cada fila y deja los movimientos `devolucion` correspondientes; el ciclo aprobar/anular/re-aprobar es idempotente en saldos.
3. Dos aprobaciones concurrentes sobre las mismas filas no producen saldo negativo ni descuento doble.
4. Precio, stock y descuento usan ancho exacto; el precio de una línea nunca proviene de una bobina de otro ancho; con lotes de distinto precio se usa el de la fila FIFO; el override de sucursal tiene prioridad.
5. La API del panel rechaza con 400 una línea cuyos metros elegibles no alcanzan.
6. El catálogo de bobinas mantiene su contrato y su consulta ya no crece con el número de bobinas.
7. `precio_venta_sucursal` no admite duplicados (sucursal, lámina, ancho) en base de datos; la migración no borra datos y explica cómo limpiar.
8. `get_inventory` público mantiene su respuesta y ya no imprime en consola.
9. Sin código muerto listado en la fase 6; suite completa en verde.
10. Migraciones reversibles verificadas; PDF de proforma y reportes siguen funcionando con datos multi-fila.

## Risks
- **Reporte de utilidades** (`report_utilidad.py:63-68`) atribuye los ingresos de un detalle a una sola fila de inventario (la primera usada) y por tanto usa el costo de compra de esa fila; con reparto multi-fila la utilidad por lote queda imprecisa. Mitigación: se acepta en este task y se documenta; corregirlo requiere decidir el criterio de atribución (fuera de alcance).
- **PDF de proforma** (`helper/pdf.py:299`) toma `nro_lote` de `detail.inventario` (primera fila); con reparto sólo mostraría un lote. Mitigación: aceptado y documentado; alternativa futura: leer lotes desde los movimientos.
- **Cambio de comportamiento observable:** cotizaciones que hoy salen con el precio de una bobina más ancha pasarán a dar 400 ("no hay precio"). Mitigación: tests explícitos y aviso al usuario.
- **Locks y latencia:** filas bloqueadas durante la aprobación. Mitigación: alcance acotado, orden fijo, test de concurrencia.
- **Revertir sólo el código** con órdenes ya repartidas en varias filas sobre-acredita la primera fila al devolver. Mitigación: antes de revertir código, listar y anular esas órdenes (consulta sobre movimientos) o corregir saldos a mano.
- **Migración B** puede abortar por duplicados en producción. Mitigación: fase 0.1 previa; no borra nada.
- **Números de migración** podrían colisionar si otro PR entra antes; el engineer usa el siguiente libre al implementar.
- Cambios en `orden_estado.py` (recién estabilizado por el PR #51): mitigado por la suite de ese PR como regresión obligatoria.

## Out of scope
- Registrar como movimientos los ajustes manuales del `PATCH almacen/inventario`.
- Unificar las tres fuentes de precio (`Window_Film_Reel.price` no participa del cálculo y se deja como está).
- Ledger puro / reservas de stock al crear la proforma.
- Validación de stock en el formulario del Django Admin (sigue comentada).
- Backfill de movimientos históricos.
- Cambios de frontend (Angular `proforma/` y `panel_admin/`).
- Corregir la atribución de utilidad por lote y los lotes múltiples en el PDF (ver riesgos).

**Preguntas abiertas para el usuario (no resolubles desde el código):**
1. ¿Una misma necesidad puede cubrirse con cortes de varios lotes/rollos de la misma bobina?
2. Con lotes de precio de venta distinto, ¿corresponde el precio del lote más antiguo?
3. ¿Se aceptan las imprecisiones de utilidad por lote y de `nro_lote` en el PDF cuando hay reparto, o se quiere incluirlas en este task?
4. ¿Hay duplicados hoy en `precio_venta_sucursal` en producción?

## Dependencias nuevas
Ninguna.
