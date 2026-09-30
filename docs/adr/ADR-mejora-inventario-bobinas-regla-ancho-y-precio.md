# ADR-mejora-inventario-bobinas-regla-ancho-y-precio: Regla única de ancho exacto, precio determinista y validación de metros

**Estado:** Propuesto
**Task relacionado:** TASK-mejora-inventario-bobinas
**Fecha:** 2026-09-30 (revisado el mismo día tras integrar master con el PR #51; ver "Actualización")

## Contexto
Tres reglas distintas de ancho conviven hoy: el precio se resuelve con `bobina__width__gte` (`business/inventario.py:100-103`, reutilizado por `resolve_unit_price`, `pricing.py:70-81`), mientras que el stock (`has_stock_for_reel`, `pricing.py:57-68`) y el descuento (`reduce_inventory`) exigen ancho exacto, como ya decidió `ADR-modulo-ordenes-proforma-nota-trabajo-api-y-calculo` (punto de validación de línea). Además:

- `get_total_meters_window_film_in_inventory` agrupa también por `precio_venta_mtr_lineal`, y `resolve_unit_price` toma `.first()`: con lotes de distinto precio el resultado depende del orden por nombre/ancho, no del lote que se va a consumir.
- `precio_venta_sucursal` no tiene constraint de unicidad (solo se valida en `save_model` del admin, alta únicamente, `admin_config/precio_venta_sucursal.py:35-47`); la subquery `[:1]` puede elegir un precio arbitrario si hay duplicados.
- `get_reel_catalog` ejecuta `resolve_unit_price` por fila (N+1, `pricing.py:40-47`).
- `build_line_pricing` solo valida `to_install > 0`, no que alcancen los metros de la línea (`pricing.py:122-125`).
- El endpoint público `get_inventory` (`views.py:219-250`) lo consume `proforma/` y lista bobinas con ancho `>=` al pedido; su contrato debe conservarse (`ADR-005`).

## Decisión
1. **Ancho exacto en precio, stock y descuento.** `resolve_unit_price` deja de reutilizar la consulta con `width__gte` y usa una consulta propia con ancho exacto. El listado público `get_inventory` **conserva** `width__gte` y su forma de respuesta; solo se le quita el `print` de depuración.
2. **Precio determinista.** Precio de la línea = override de `precio_venta_sucursal` (sucursal + lámina + ancho) si existe; si no, `precio_venta_mtr_lineal` de la **fila que `reduce_inventory` consumiría primero** (mismo criterio FIFO: `date`, `id`, activa, con saldo). El precio de venta por sucursal sigue siendo el precio vigente; no se congela por lote.
3. **Unicidad de override en base de datos.** Nuevo `UniqueConstraint(sucursal, lamina, width)` en `precio_venta_sucursal`, precedido de una verificación de duplicados existentes que **aborta la migración con un listado** en vez de borrar datos; la limpieza es manual y previa.
4. **Validación de metros suficientes al armar la línea.** `build_line_pricing` suma los metros disponibles (mismas condiciones que la asignación del ADR `...-asignacion-y-movimientos`) y rechaza con `ProformaException` (400) si son menores a `length * quantity`. Sigue sin reservar stock.
5. **Catálogo sin N+1.** `get_reel_catalog` resuelve el precio en la misma consulta (o en una segunda consulta única para todos los overrides de la sucursal), sin consulta por fila. Mismo resultado observable y mismo contrato de `ReelCatalogSerializer`.
6. **Limpieza de código muerto/duplicado dentro del mismo módulo:** `helper/inventory.py`, `is_window_film_available`, el código inalcanzable de `get_inventory_film_available_film_by_sucursal` y `business/bobina.py` vacío se eliminan o se enrutan a la implementación única, previa verificación de que no tienen llamadores (la investigación solo lo verificó por búsqueda de texto). `Forms/car_model_part.py` mantiene su validación de stock comentada para el Django Admin (fuera de alcance; el panel es la vía objetivo).

Supuestos de negocio a confirmar: (a) que el precio por lote más antiguo es el criterio correcto cuando hay lotes con distinto `precio_venta_mtr_lineal`; (b) que ninguna consulta actual depende de que el precio de una bobina más ancha se aplique a un pedido de ancho menor.

## Alternativas consideradas
- **Mantener `>=` en el precio y alinear stock/descuento a `>=`.** Permitiría usar una bobina más ancha que la pedida, lo cual cambia el cálculo de merma/inventario y contradice el ADR de órdenes; descartada.
- **Congelar el precio en la fila de inventario y no usar override por sucursal.** Simplificaría a una sola fuente, pero los precios por sucursal ya se administran en su propia pantalla y el negocio los usa; descartada.
- **Unificar `Window_Film_Reel.price`, `inventario.precio_venta_mtr_lineal` y `precio_venta_sucursal` en una sola tabla de precios.** Mejor a largo plazo, pero es una migración de datos y de UI mayor que el problema actual; queda como camino futuro. Se documenta que `Window_Film_Reel.price` no participa del cálculo.
- **Dejar la validación de duplicados solo a nivel admin.** Es lo que existe hoy y no cubre la API ni la carga directa; descartada.

## Estrategia de rollback / mitigación
- Ancho exacto, precio determinista y validación de metros son cambios de lógica sin cambio de esquema: se revierten con el código (sin datos que restaurar). Riesgo a vigilar: cotizaciones que hoy salen con precio de una bobina más ancha pasarán a dar 400 "no hay precio"; se cubre con tests y aviso en el plan.
- El `UniqueConstraint` es reversible (`migrate` hacia atrás lo elimina). Si existen duplicados, la migración se detiene sin modificar nada; el despliegue se posterga hasta limpiar los datos. Se recomienda ejecutar la verificación de duplicados en producción antes de desplegar.
- El contrato del endpoint público y del catálogo del panel no cambia, por lo que no hay despliegue coordinado con el frontend.

## Consecuencias
- Una sola regla de ancho: lo que se cotiza es lo que se descuenta.
- Precio predecible con varios lotes; catálogo más rápido (una consulta en lugar de N+1).
- La base de datos garantiza un solo override por (sucursal, lámina, ancho).
- Se acepta que tres fuentes de precio sigan existiendo (una de ellas sin uso en el cálculo) y que el Django Admin siga sin validar stock al crear detalles.

## Actualización (2026-09-30, integración con PR #51)
Revisado contra master sin cambios de fondo: `inventario.py`, `pricing.py` y `views.py` no fueron tocados por el PR #51, por lo que el diagnóstico y las decisiones 1 a 6 se mantienen. Ajustes:
- El catálogo del panel es `OrdenesBobinasView` (`custom_views/ordenes_admin.py:410`); su contrato no cambia.
- La validación de metros suficientes de la decisión 4 y la asignación de `ADR-mejora-inventario-bobinas-asignacion-y-movimientos` deben usar **el mismo criterio de filas elegibles** (activas, sucursal habilitada, ancho exacto, `to_install > 0`), definido una sola vez en `Inventario_Business`; así lo que la proforma valida es lo que `aprobar_proforma` (`orden_estado.py:83-141`) puede descontar. La validación de la proforma sigue siendo informativa: la garantía real la da la asignación bajo bloqueo al aprobar.
- La migración del `UniqueConstraint` es independiente de la de `Inventario_Movimiento` (dos migraciones, cada una reversible por separado), ambas posteriores a `0111_estados_orden`, para poder desplegar/revertir una sin la otra y para que un fallo por duplicados no bloquee la tabla de movimientos.
