# ADR-dashboard-taller-laminas-definiciones-metricas: Definición y fuente de cada métrica del dashboard con los datos existentes

**Estado:** Propuesto
**Task relacionado:** TASK-dashboard-taller-laminas
**Fecha:** 2026-09-30

## Actualización (2026-09-30, integración con PR #54 — Reportes)

`origin/master` trajo `Reportes_Business` (`business/reportes.py`), que ya define la venta cobrada y declara que ninguna otra parte recalcula esas cifras. Cambia el punto 1: **Ventas del mes y la serie `vendido` reutilizan `pagos_cobrados()` y `filtrar_pagos()` del reporte** (más `Pago_Business.get_panel_pago_queryset` para el alcance) en vez de una consulta propia, y se muestran solo a quien tiene `product.view_proxy_pagos` (ver `ADR-dashboard-taller-laminas-api-agregados-alcance`). El resto de las métricas no depende del reporte y se mantiene.

## Contexto

La investigación mostró que varias métricas pedidas admitían más de una definición o no tenían respaldo en el modelo. El usuario resolvió cuatro de ellas (`/delivery-architect`, 2026-09-30):

1. **Venta** = nota de venta **pagada**.
2. **Categoría de lámina**: **agrupar por nombre de lámina** (sin campo nuevo).
3. **Servicio**: **ítems más solicitados** (sin campo nuevo).
4. **Stock crítico**: **regla fija por metros** (sin campo nuevo).

Las tres primeras corresponden a las variantes de respaldo del DDR (`DDR-dashboard-taller-laminas-pantalla-dashboard`, "Variantes por disponibilidad de dato"). Este ADR fija la fuente exacta de cada métrica; el contrato de endpoints y el alcance están en `ADR-dashboard-taller-laminas-api-agregados-alcance`.

Hechos del código que fundamentan las definiciones:
- `business/reportes.py:1-8, 99-130` (origen: PR #54): cálculo único de ventas cobradas, `pagos_cobrados()` y `filtrar_pagos()`; el permiso de ver ventas es `view_proxy_pagos` (`ADR-reportes-utilidad-ventas-diarias-permisos`).
- `pago` se elimina al anular el pago (`business/orden_estado.py:298-310`, `pago_obj.delete()`), por lo que las filas `pago` existentes son cobros vigentes; la nota de venta queda `pagada` mientras exista el pago (`helper/estados.py:16-21`).
- `Nota_Venta.created_on` es nullable (`models.py:306`); `pago.created_on` es `auto_now_add` (`models.py:335`).
- `Proforma_Header.proforma_created_on` es `auto_now=True` (`models.py:170`) y las transiciones de estado guardan con `update_fields` (`orden_estado.py:53-56, 252`), por lo que la fecha se congela al aprobar pero cambia si la proforma se edita antes.
- `Nota_trabajo.nota_venta_created_on` es `auto_now_add` y no nula (`models.py:213`); `entrada_vehiculo` y `salida_vehiculo` son nullable (`models.py:205-206`).
- `Detalle_Nota_Trabajo` guarda por nota una fila por lámina y ancho con los metros consumidos (`business/orden_trabajo.py:127-135`; el resumen usa `length × quantity`, `orden_estado.py:96-118`). Cualquier anulación cancela la nota, lo que permite excluir consumo devuelto.
- `Inventario_Movimiento` (migración `0113`) existe solo desde el PR #52 y no se rellenó para órdenes anteriores (`ADR-mejora-inventario-bobinas-asignacion-y-movimientos`, decisión 4, compatibilidad).
- `Proforma_Detail.car_part` referencia `Car_Part` (`models.py:248-259`); `Proforma_Header.status` incluye `anulada` (`helper/proforma.py:16-24`).

## Decisión

Todas las métricas parten de los querysets con alcance (ver ADR de API). Periodo por defecto = mes calendario en curso; "mes previo" = mes calendario anterior.

1. **Ventas del mes** = suma de `pago.monto` (= `cobrado` del reporte) de los pagos que devuelve `Reportes_Business.pagos_cobrados()` (pago existente, nota de venta `pagada`, proforma no borrada), acotados por `Pago_Business.get_panel_pago_queryset` y `filtrar_pagos` (fecha local del pago, sucursal). Agrupada por mes de `pago.created_on` para la serie. Comparativa vs mes previo con la misma consulta; variación porcentual `null` si el mes previo es 0. `pago.cerrado` no filtra. **No** se usa `calcular_ventas`/`resumir` (calculan costos): la cifra debe coincidir con `totales.cobrado` de `reportes/ventas-diarias` para el mismo rango y sucursal (prueba de equivalencia). Solo se entrega a quien tenga `product.view_proxy_pagos`; si no, el bloque va `null`.

2. **Proformas activas** = proformas con `status = proforma` (aún no aprobadas), `is_delete=False`; monto = suma de `total_price − discount` (mismo cálculo que `total_a_pagar`, `ordenes_serializer.py`); se devuelve también la cantidad. Sin tope por mes: es el pendiente actual.

3. **Cotizado del mes (gráfica de línea)** = suma de `total_price − discount` de las proformas no borradas y **no anuladas** (`status ≠ anulada`), agrupadas por mes de `proforma_created_on`. Incluye las ya convertidas. **Limitación conocida y aceptada:** al ser `auto_now`, una proforma editada cambia de mes; se acepta porque agregar una fecha de emisión inmutable exigiría migración y no se puede reconstruir para lo histórico.

4. **Tasa de conversión del período** = proformas del período (mismo criterio y mes que "cotizado") que hoy tienen orden (`status` en `en_trabajo`, `por_cobrar`, `finalizado`) ÷ proformas del período no anuladas. Se devuelven numerador, denominador y porcentaje (1 decimal; `null` si el denominador es 0). Las anuladas se excluyen de ambos lados. Es una tasa por cohorte de emisión: una proforma emitida a fin de mes y convertida el siguiente cuenta en su mes de emisión.

5. **Instalaciones del día** (variante de respaldo del DDR): "en taller" = notas de trabajo con `status = en_proceso` (cualquier fecha de ingreso; es el estado actual del taller); "terminadas hoy" = `status = terminado` con `salida_vehiculo` de hoy. No hay "programadas" porque no existe el concepto (no se agrega estado "En espera": no se toca la máquina de estados de `ADR-estados-proforma-nota-trabajo-nota-venta-maquina-de-estados`). El KPI muestra "N en taller · M terminadas hoy".

6. **Consumo de lámina por mes (barras apiladas)** = suma de `Detalle_Nota_Trabajo.length` por `window_film`, agrupada por mes de `Nota_trabajo.nota_venta_created_on`, **excluyendo notas `cancelada`** (una anulación devuelve el inventario). Se prefiere esta fuente sobre `Inventario_Movimiento` porque cubre el historial completo y no depende de que exista movimiento (los movimientos empiezan con la migración `0113`). Metros en Decimal a 2 decimales. Series = nombre de la lámina, máximo 6 por total del rango + "Otras". Título del widget: "Consumo por lámina" (no "por categoría").

7. **Servicios más solicitados (donut)** (variante de respaldo) = cantidad de líneas de `Proforma_Detail` por `car_part`, de proformas no borradas ni anuladas en el rango de `?meses=`, máximo 5 ítems + "Otros". Solo cuenta ventas con instalación (las líneas de metro lineal no tienen `car_part`, `models.py:253`). Título: "Ítems más solicitados".

8. **Stock crítico (regla fija)** — por grupo sucursal + lámina + ancho de bobina, sobre filas de `inventario` activas (`is_active`, bobina activa, sucursal habilitada):
   - `metros` = suma de `to_install`; `rollos` = cantidad de filas del grupo con `to_install > 0`.
   - Estado: `critico` si `metros` < `STOCK_CRITICO_METROS`; `bajo` si `metros` < `STOCK_BAJO_METROS`; si no, `ok`. Las constantes viven en `helper/dashboard.py` (fuera de `.env` y de la base). Los valores iniciales **provisionales** son 10 m y 30 m y **deben confirmarse con el negocio** antes de publicar (no hay dato en el código que los fundamente).
   - Se incluyen los grupos en `critico` y `bajo` por defecto; `?todos=true` devuelve también los `ok`. Un grupo con 0 m (agotado) es `critico`. Orden: metros ascendente.
   - Se asume que una fila de `inventario` equivale a un rollo/lote físico (hipótesis: `quantity` no se usa para contar rollos porque su semántica no está documentada); confirmar con el negocio.

9. **Cola de taller** = notas de trabajo en alcance con `status = en_proceso` más las `terminado` con `salida_vehiculo` de hoy; en proceso primero, luego por `entrada_vehiculo` ascendente; máximo 10. "Lámina instalada" = láminas de `Detalle_Nota_Trabajo` de la nota (la principal por metros + conteo del resto). "Técnico" = `Nota_trabajo.instaladar` (`instalador`), `null` si no hay (hipótesis H7 del TASK; `responsable` es el usuario que la generó, no el técnico).

10. **Proformas recientes** = las 6 más recientes por `id` descendente de las proformas en alcance, todos los estados, con el botón de conversión decidido en el frontend según `status = proforma`.

## Alternativas consideradas

1. **Venta = nota de venta creada (orden generada)**. Más simple y con `Nota_Venta.total_price`, pero incluye dinero no cobrado; el usuario eligió lo cobrado.
2. **Fuente de consumo `Inventario_Movimiento`** (egresos − devoluciones). Exacta por rollo, pero solo desde la migración `0113`; los meses previos saldrían vacíos hasta acumular historia. Se descarta como fuente única; queda disponible si más adelante se quiere el consumo por lote.
3. **Fecha de proforma inmutable (`created_on auto_now_add` + backfill)**. Corrige la limitación del punto 3 pero exige migración y no se puede reconstruir el pasado; contradice la decisión de no tocar el modelo. Se registra como mejora futura.
4. **Umbral por lámina en base de datos o porcentaje de `original_length`.** Más flexible pero requiere migración/pantalla o ignora el consumo real de cada lámina; el usuario eligió la regla fija.
5. **Derivar "servicio" por palabras del nombre del ítem** (parabrisas, laterales). Frágil (nombres capturados a mano, no verificados); se descarta.
6. **Estado "En espera"**: no se agrega para no alterar la máquina de estados ni la migración.

## Estrategia de rollback / mitigación

Solo lectura y sin cambios de esquema: las definiciones viven en `business/dashboard.py` y `helper/dashboard.py`. Revertir el PR restaura el estado anterior sin datos que reparar. Mitigación de definiciones discutibles: cada métrica está aislada en un método con pruebas de datos fijos (ver ADR de API, punto 6), de modo que cambiar una definición (p. ej. a nota de venta creada) es un cambio local y testeado; los umbrales de stock se ajustan en una constante.

## Consecuencias

- **Más fácil:** las cifras salen de fuentes ya vigentes y testeadas; el historial de consumo y ventas está disponible desde el primer día; no se toca la máquina de estados ni el modelo.
- **Más difícil / limitaciones aceptadas:** (a) la línea "cotizado" y la conversión pueden desplazar una proforma editada de mes; (b) sin categoría los colores por lámina se asignan por nombre y el gráfico depende de cómo estén nombradas; (c) "servicios" no distingue "Completo"/"Solo laterales" (solo ítems, y solo en ventas con instalación); (d) sin "programadas" ni "En espera"; (e) el semáforo no distingue el consumo típico por lámina.
- **A confirmar con el negocio (no inferible del código):** los umbrales provisionales de 10 m / 30 m, que una fila de inventario equivale a un rollo, y que "técnico" = `instaladar`.
- **Deuda registrada:** fecha de emisión inmutable de proforma, categoría de lámina, modelado de servicio y estado "En espera" quedan como mejoras futuras (cada una exige migración).
