# ADR-mejora-inventario-bobinas-asignacion-y-movimientos: Descuento atómico multi-fila con registro de movimientos

**Estado:** Propuesto
**Task relacionado:** TASK-mejora-inventario-bobinas
**Fecha:** 2026-09-30 (actualizado el mismo día tras integrar master con el PR #51; ver "Actualización")

## Contexto
`Inventario_Business.reduce_inventory` (`business/inventario.py:52-70`) descuenta de **una sola** fila de `inventario` (la más antigua con `to_install >= necesidad`), leyendo, restando en Python y guardando, sin bloqueo. `return_to_inventory` (`:73-83`) devuelve a la fila guardada en `Proforma_Detail.inventario` (FK única, `models.py:249`).

Desde el PR #51 los llamadores son:
- **Descuento:** solo `Orden_Estado_Business.aprobar_proforma` (`business/orden_estado.py:83-141`), que ya bloquea la proforma con `select_for_update` (`:60-65`) y corre en `transaction.atomic`. `Proforma_Business.create_work_note`, la vista `ProformaGenerateNotaView` y la acción del Django Admin solo delegan.
- **Devolución:** dos caminos con lógica duplicada, ambos sin bloqueo de inventario: `Orden_Estado_Business._cancelar_orden` (`orden_estado.py:198-229`; lo usan anular nota de trabajo, anular nota de venta y `abrir_proforma`) y `Orden_Trabajo_Business.delete_work_note` (`orden_trabajo.py:89-100`, borrado físico desde el Django Admin). Ambos ponen `detalle.inventario = None` tras devolver, y `_cancelar_orden` omite en silencio los detalles con `inventario_id` nulo (`:212-213`).
- `ADR-estados-proforma-nota-trabajo-nota-venta-maquina-de-estados` establece a `Orden_Estado_Business` como único escritor de estados y bloquea por proforma; esta decisión debe respetarlo.

Problemas (ver investigación del task):
- El catálogo suma todas las filas de una bobina en la sucursal (`pricing.py:20-55`) pero el descuento no puede repartir entre filas: se ofrece stock que luego no se puede descontar (`NoHayLaminasDisponibles`).
- El bloqueo por proforma no protege las filas de inventario: dos proformas distintas de la misma sucursal pueden pisarse el saldo.
- No hay historial; como el vínculo `detalle.inventario` se borra al anular, después de una anulación no queda rastro de qué fila y cuántos metros se usaron.
- `reduce_inventory` no filtra `is_active` ni sucursal habilitada; `ADR-modulo-almacen-modelo-datos-imagen-soft-delete` dejó esto fuera "por alcance", aquí se incluye porque este task justamente toca y prueba esa lógica.

## Decisión
1. **Asignación FIFO multi-fila.** `reduce_inventory` reparte la necesidad (`length * quantity`) entre las filas de `inventario` de esa sucursal + lámina + ancho **exacto**, activas (`inventario.is_active`, `bobina.is_active`, sucursal habilitada) y con `to_install > 0`, ordenadas por `date` y luego `id`. Si la suma no alcanza, falla con `NoHayLaminasDisponibles` sin haber descontado nada. Su contrato de retorno pasa de "una fila" a "las asignaciones (fila, metros)"; el único llamador es `aprobar_proforma`, que se adapta (el resumen de la nota de trabajo sigue agrupando por lámina y ancho).
2. **Bloqueo pesimista con orden de bloqueo definido.** Orden único: (a) la proforma (ya existe, `_bloquear`), (b) las filas de inventario candidatas en orden `date`, `id` con `select_for_update()`. Como toda operación de descuento o devolución toma primero la proforma y luego las filas en el mismo orden, no hay ciclos de espera.
3. **Registro de movimientos.** Nuevo modelo aditivo `Inventario_Movimiento`: `inventario` (FK), `proforma_detail` (FK, nullable), `tipo` (`egreso` / `devolucion`), `metros` (Decimal positivo), `created_on`, `created_by` (nullable). Cada descuento genera un `egreso` por fila tocada; cada devolución genera `devolucion` por fila revirtiendo el neto (egresos − devoluciones) de ese detalle.
4. **Un único punto de devolución.** `Inventario_Business` expone una operación de "devolver los metros de un detalle" que usan tanto `_cancelar_orden` como `delete_work_note`, eliminando la duplicación. Esa operación: usa los movimientos del detalle si existen; **si el detalle no tiene movimientos** pero sí `inventario_id` (órdenes aprobadas antes de este cambio), usa el camino anterior (devolver a esa fila con bloqueo); si no tiene ninguno de los dos, no devuelve nada y **registra un log de error** en vez de omitirlo en silencio. Se mantiene `detalle.inventario = None` tras devolver: la trazabilidad pasa a los movimientos.
5. **Compatibilidad.** Se mantienen `inventario.to_install` / `installed` como saldo (lo leen catálogo, reportes y admin) y `Proforma_Detail.inventario` (apunta a la primera fila usada al aprobar) para no romper `report_storage`, `report_utilidad` ni el Django Admin. Saldo y movimientos se escriben en la misma transacción.
6. **Sin reservas al crear la proforma.** El stock se descuenta al aprobar; la proforma solo valida que hoy alcance (ver `ADR-mejora-inventario-bobinas-regla-ancho-y-precio`).
7. **Fuera de alcance:** registrar como movimiento los ajustes manuales del `PATCH almacen/inventario`, que siguen sin dejar rastro. Deuda aceptada.

Supuesto de negocio a confirmar (no inferible del código): una misma necesidad puede cubrirse físicamente con cortes de varios lotes/rollos de la misma bobina. Es coherente con que el catálogo ya los presenta sumados, pero no está documentado.

## Actualización (2026-09-30, integración con PR #51)
La versión inicial de este ADR citaba `business/proforma.py:99-140` y `ordenes_admin.py:135`, y proponía un fallback a `detalle.inventario` para la devolución. Tras el PR #51 se corrige: (a) el descuento y la devolución viven en `orden_estado.py`, (b) existe un segundo camino de devolución (`delete_work_note`) que debe unificarse, (c) `detalle.inventario` ya se anula al devolver, por lo que el fallback aplica solo a órdenes anteriores a la migración que sigan vigentes, y (d) la migración es la siguiente libre tras `0111_estados_orden` y no `0110`.

## Alternativas consideradas
- **Solo `select_for_update` + repartir entre filas, sin tabla de movimientos.** Más simple, pero la devolución multi-fila no sería reconstruible (el FK único no alcanza; además se anula al devolver) y seguiría sin auditoría. Descartada.
- **Actualización condicional con `F()` (`UPDATE ... WHERE to_install >= x`).** Atómica y sin bloqueo, pero difícil de combinar con reparto entre varias filas y orden FIFO; requeriría bucle con reintentos. Descartada.
- **Ledger puro (saldo = suma de movimientos).** Más limpio, pero obliga a reescribir almacén, reportes y admin y a un backfill histórico completo. Sobreingeniería ahora; camino futuro.
- **Reservar stock al crear la proforma.** Evita la sorpresa al aprobar, pero agrega estados, expiraciones y liberación en cada edición/anulación, y choca con la máquina de estados recién definida. Descartada.
- **Dejar las dos devoluciones separadas y parchear ambas.** Menos cambios inmediatos, pero mantiene lógica duplicada que ya divergió (una usa `return_to_inventory`, la otra suma directo). Descartada.

## Estrategia de rollback / mitigación
- Esquema **aditivo** (tabla nueva, sin alterar columnas existentes): la migración se revierte hacia la anterior sin perder `inventario` ni `Proforma_Detail`.
- Sin backfill masivo de movimientos históricos; evita una migración de datos riesgosa. Las órdenes aprobadas antes del cambio se devuelven por el camino de fallback.
- **Riesgo al revertir solo el código:** una orden aprobada con reparto entre varias filas quedaría con `detalle.inventario` apuntando a la primera fila; el código viejo devolvería todos los metros a esa fila (posible sobre-crédito). Mitigación: antes de revertir código, listar las órdenes vigentes con egresos en más de una fila (consulta sobre `Inventario_Movimiento`) y anularlas con el código nuevo, o corregir el saldo manualmente. Se documenta en el plan.
- Bloqueos/latencia: alcance acotado (filas de una bobina en una sucursal), orden de bloqueo fijo; se cubre con test de concurrencia en el plan.

## Consecuencias
- Catálogo y descuento coinciden; desaparece la ventana de doble descuento entre proformas.
- Trazabilidad de qué fila y cuántos metros aportó cada línea, incluso después de anular.
- Una sola implementación de devolución en lugar de dos.
- Se acepta convivir con dos representaciones (saldo + movimientos) y con ajustes manuales sin rastro; riesgo de divergencia mitigado solo escribiendo ambos en la misma transacción.
- Los tests existentes de `test_orden_estado_service.py` (ciclo aprobar/anular) pasan a ser regresión obligatoria.
