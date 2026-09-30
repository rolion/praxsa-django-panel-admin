# ADR-reportes-utilidad-ventas-diarias-calculo-y-api: Cálculo único de ventas/utilidad y API de solo lectura para los reportes del panel

**Estado:** Propuesto
**Task relacionado:** TASK-reportes-utilidad-ventas-diarias
**Fecha:** 2026-09-30

## Contexto

La investigación encontró que los reportes actuales (`admin_config/report_daily_sell.py`, `admin_config/report_utilidad.py`) calculan mal o de forma incompleta:
- "Utilidad Lámina" es venta bruta de lámina, no resta `precio_compra_mtr_lineal` (`report_utilidad.py:62-69`).
- Ventas Diaria toma importes de la proforma, no del pago, y se rompe con proformas sin ítems (`report_daily_sell.py:107-113`).
- Ninguno da totales ni distingue con/sin instalación.

El usuario pidió (2026-09-30): utilidad = venta − costo de compra; solo ventas **pagadas**; cifras **con y sin descuento**; distinguir venta con instalación (`venta_instalacion`) de sin instalación (`venta_metro_lineal`); totales; que el cálculo refleje la realidad; y llevar los reportes al panel (DDR `DDR-reportes-utilidad-ventas-diarias-pantallas-reportes`). Decidió además que la instalación va **aparte** de la utilidad de lámina (no hay costo de compra de la instalación en los modelos). Como hay dos superficies (Django Admin y panel), el riesgo principal es tener **dos verdades** para la misma cifra.

Hechos del código que condicionan la decisión:
- Subtotal de una línea: `venta_instalacion` = `largo × cantidad × precio_lámina + precio_instalación × cantidad`; `venta_metro_lineal` = `largo × precio_lámina`, con `quantity` prohibida (`business/pricing.py:84-96`). Por tanto la rama "metro lineal ignora quantity" que la investigación señaló como inconsistencia **no es un error**: en metro lineal `quantity` es 0 por regla. (Corrección a esa observación del TASK.)
- Metros consumidos de inventario por línea: `largo × cantidad` si `cantidad > 0`, si no `largo` (`business/orden_estado.py:103-104`). Cada línea guarda el lote de inventario del que salió (`Proforma_Detail.inventario`, `models.py:250`), con su `precio_compra_mtr_lineal` (`models.py:149`, `default=0.0`). Al anular la orden, `inventario` vuelve a `None` (`orden_estado.py:218`).
- Una venta está **cobrada** si existe su `pago` (los pagos anulados se borran, `orden_estado.py:300`) y su nota de venta está `pagada` (`helper/estados.py:18`). El monto del pago lo fija el servidor con el total congelado de la nota de venta (`orden_estado.py:270`), que ya descuenta `proforma.discount` (`orden_estado.py:144`).
- `USE_TZ = False`, `TIME_ZONE = 'America/La_Paz'` (`settings.py:189-193`): las fechas son locales, sin conversión.
- No hay paginación global de DRF (`ADR-estados-...-api-y-permisos`, "Consecuencias") y el panel ya trae listados completos.

## Actualización 1 (2026-09-30, al planificar: la base ya integró la mejora de inventario)

Al planificar se verificó contra `origin/master`, que ya incluye el PR #52 (`TASK-mejora-inventario-bobinas`). Cambia la fuente del costo de compra, no la decisión de fondo:
- Una línea de proforma puede ahora consumir metros de **varias filas de inventario** (asignación FIFO, `business/inventario.py:64-99`); cada consumo queda en `Inventario_Movimiento` (`models.py`, tipos `egreso`/`devolucion`), y `Proforma_Detail.inventario` apunta solo a la **primera** fila usada (`business/orden_estado.py`, comentario "FK legado").
- Por eso el costo de una línea **no** es `metros × precio_compra del lote de la línea`. Regla vigente: **costo = Σ por fila de inventario de (egresos − devoluciones) × `precio_compra_mtr_lineal` de esa fila**. Solo si la línea **no tiene movimientos** (venta aprobada antes de #52) se usa el fallback legado `metros × precio_compra_mtr_lineal` de `detalle.inventario`.
- `costo_incompleto` se marca cuando: la línea no tiene movimientos ni `inventario`; los movimientos netos suman 0 en una venta cobrada (inconsistencia); o alguna fila consumida tiene `precio_compra_mtr_lineal = 0`.
- La sección 1 dice que los totales salen "por agregación en base de datos": se precisa que el cálculo se hace **en Python con `Decimal` sobre filas ya filtradas y en un número constante de consultas** (líneas, movimientos y precios de lote traídos en bloque), porque la regla de costo con fallback no se expresa limpiamente en un solo `annotate`. La API y los admins llaman a la misma función, que recibe un queryset de `pago` ya filtrado (rango, sucursal, alcance). Cada venta se redondea a centavos y los totales son la suma de las ventas redondeadas, de modo que la tabla siempre cuadra con las tarjetas.
- El detalle "por lámina" se agrupa por los atributos de la **línea** (sucursal, lámina, ancho), no por fila de inventario, así que una línea repartida entre lotes no se duplica. En el Django Admin, "Reporte Utilidades" conserva su fila por lote de inventario, calculada con los **tramos** (línea × fila de inventario) de las ventas cobradas, acumulados (sin filtro de fecha, como hoy).

## Decisión

### 1. Una sola implementación del cálculo, en `business/`

Nuevo módulo `business/reportes.py` con el único lugar donde se definen las fórmulas. La API del panel y los dos `ModelAdmin` **consumen ese módulo**; ninguno recalcula por su cuenta. El resto de este ADR fija qué calcula, no cómo se escribe.

Se calcula en dos niveles separados, y **nunca se suman importes de la cabecera sobre un queryset unido a los ítems** (produciría multiplicación de filas y totales inflados):
- **Nivel venta (cabecera):** una fila por `pago` cobrado: `pago.monto` (= **cobrado**), `proforma.discount` (= **descuento**), tipo de pago, `registro_contable`, `cerrado`, tipo de venta, sucursal, cliente, vehículo, fecha del pago.
- **Nivel línea (ítems):** una fila por `Proforma_Detail` de una venta cobrada, con: `metros` (regla de arriba), `venta_lamina = metros × window_film_price`, `instalacion = installation_price × quantity`, `costo_compra = metros × inventario.precio_compra_mtr_lineal`.

Las cifras por venta salen de agregar las líneas por `pago` y unirlas a la cabecera; los totales se obtienen por agregación en base de datos, no sumando páginas en el cliente.

### 2. Definiciones (todas en `Decimal`, redondeo a 2 decimales al final)

| Cifra | Definición |
|---|---|
| Venta lámina | Σ `metros × window_film_price` de las líneas |
| Instalación | Σ `installation_price × quantity` (0 en metro lineal) |
| **Bruto** | Venta lámina + Instalación (= Σ `sub_total`) |
| **Descuento** | `proforma.discount` |
| **Cobrado** | `pago.monto` |
| Costo de compra | Σ `metros × precio_compra_mtr_lineal` del lote de cada línea |
| **Utilidad antes de descuento** | Venta lámina − Costo de compra |
| **Utilidad después de descuento** | Utilidad antes de descuento − Descuento |
| Margen % | Utilidad después de descuento ÷ (Bruto − Descuento) |

- **Instalación aparte (decisión del usuario):** el ingreso por instalación se reporta como línea propia y **no** entra en ninguna utilidad.
- **El descuento se resta íntegro de la utilidad de lámina, sin prorratear** entre lámina e instalación. Es el criterio conservador y el más simple; queda como decisión de negocio revisable (ver Alternativas). Puede dar utilidad negativa y es válido mostrarla.
- Tipo de venta: se toma de `Proforma_Header.sales_type`; los desgloses "con instalación / sin instalación" agrupan por ese campo.
- **Fecha del reporte = fecha del pago** (`pago.created_on`, fecha local, inclusive en ambos extremos).
- Solo ventas cobradas: existe `pago` + nota de venta `pagada` + proforma no borrada (`is_delete=False`). Las por cobrar y las anuladas **no** cuentan (a diferencia del reporte de utilidad actual, `report_utilidad.py:63`).
- **Costo incompleto explícito:** una venta cuyo lote de alguna línea no existe (`inventario` nulo) o tiene `precio_compra_mtr_lineal = 0` se marca `costo_incompleto = true`, y los totales devuelven `ventas_costo_incompleto` (conteo). El costo de esas líneas se toma como 0 en el cálculo, por lo que la utilidad de esas ventas está **sobreestimada**; la UI debe advertirlo (pendiente para el plan; requiere un elemento visual que el DDR no contempló: un aviso/marca en la fila y en las tarjetas).

### 3. API de solo lectura

Dos endpoints `GET` bajo el mismo prefijo y estilo que Órdenes (`TokenAuthentication`, `IsAuthenticated` + `IsStaffUser`, más permiso explícito por reporte definido en `ADR-reportes-utilidad-ventas-diarias-permisos`):

| Endpoint | Parámetros | Respuesta |
|---|---|---|
| `reportes/ventas-diarias` | `desde`, `hasta` (ISO `YYYY-MM-DD`, obligatorios), `sucursal`, `sales_type`, `tipo_pago` (opcionales) | `rows` (una por pago), `totales`, `por_tipo_venta`, `por_tipo_pago`, `sin_sucursal` |
| `reportes/utilidad` | `desde`, `hasta` (obligatorios), `sucursal`, `sales_type` | `ventas` (una por nota de venta), `por_lamina`, `totales`, `por_tipo_venta`, `sin_sucursal` |

- **Sin costos en Ventas Diarias:** el serializer de `ventas-diarias` no contiene ningún campo de costo, utilidad ni margen; solo el de `utilidad` los incluye. Es lo que permite dar Ventas Diarias a Caja sin exponer márgenes.
- Validación: `desde` y `hasta` obligatorios y válidos, `desde ≤ hasta`, **rango máximo de 366 días** (400 con mensaje si no). `sales_type` y `tipo_pago` solo con valores conocidos (400 si no).
- **Alcance por sucursal:** el definido en `ADR-modulo-ordenes-proforma-nota-trabajo-alcance-permisos` (Admin ve todas; el resto, **todas** sus sucursales habilitadas vía `User_Helper.get_enabled_sucursal_ids`, `helper/user.py:31-39`; sin sucursal → respuesta vacía con `sin_sucursal: true`, no `None`). Un `sucursal` fuera de alcance responde **404**. El selector de sucursal del panel reutiliza el catálogo ya acotado `ordenes/catalogo/sucursales`.
- Sin paginación en servidor: la respuesta trae todas las filas del rango (tope por los 366 días). Los totales son del rango completo, independientes de cómo pagine la tabla en el cliente.
- Los importes se serializan como los demás recursos monetarios de la API (`DecimalField`); el formato `1.234,00 Bs` es responsabilidad del frontend (DDR).

### 4. Los reportes del Django Admin se reescriben sobre el mismo módulo

- `ReportDailySellAdmin` y `ReportUtilidadAdmin` obtienen sus columnas de `business/reportes.py`, con las mismas definiciones que la API (utilidad = venta − costo de compra; solo cobradas). Se eliminan los errores documentados (`reduce` sin inicial, `admin_order_field` con typo, filtros duplicados, default de fecha evaluado al importar).
- Su **alcance por sucursal** pasa al de la API (todas las sucursales habilitadas) en vez de `sucursales[0]`, para que una misma persona vea las mismas cifras en ambas superficies. Es un cambio acotado a estos dos reportes; `PagosAdmin` y los demás admins no cambian.
- Se sobreescribe `has_delete_permission` a `False` en ambos (solo lectura real; cierra la brecha señalada en la investigación).
- Cualquier cambio futuro a una fórmula se hace una sola vez en `business/reportes.py`.

## Alternativas consideradas

- **Calcular en Python en cada superficie** (API por un lado, Admin por otro): más rápido de escribir, pero es justamente el origen de las "dos verdades"; se descarta.
- **Reutilizar los `annotate` actuales de `report_utilidad.py` y corregirlos in situ**: no sirve para la API y no separa nivel venta / línea, lo que obligaría a sumar descuento sobre filas unidas a ítems (totales inflados).
- **Un modelo/tabla de agregados persistida (materializada) o vista SQL**: precisión y velocidad para rangos enormes, pero exige migraciones y sincronización sin que el volumen lo justifique; se descarta por sobreingeniería (los rangos están acotados a 366 días).
- **Prorratear el descuento entre lámina e instalación según su peso en el bruto**: más "justo" contablemente, pero introduce una regla que negocio no definió y hace que la utilidad dependa de la instalación que el usuario quiso dejar aparte. Se difiere; el módulo la centraliza si negocio la pide después.
- **Sumar la instalación a la utilidad** (o restarle un costo estimado): se descarta por decisión del usuario; no existe un costo real de instalación.
- **Paginación server-side** (`?page=`): la UI del DDR usa paginación de `ngx-datatable` en cliente y los totales ya vienen del servidor; se difiere hasta que el volumen lo exija (deuda anotada).
- **Reportes por rango libre sin tope**: se descarta; sin paginación un rango de años podría devolver decenas de miles de filas.
- **Dejar el alcance legado (`sucursales[0]`) en los admins**: mantendría la divergencia Admin vs. panel para usuarios con varias sucursales; se descarta solo para estos dos reportes.

## Estrategia de rollback / mitigación

Cambio **aditivo y de solo lectura**: no hay migraciones, modelos ni estados nuevos; los endpoints son nuevos y no alteran contratos existentes. La reescritura de los dos `ModelAdmin` cambia lo que muestran (cifras corregidas), pero no escribe datos.
- Riesgos: (a) cifras distintas a las que el negocio veía hasta hoy (por diseño, la utilidad baja porque ahora resta el costo); (b) utilidad sobreestimada donde falte el costo de compra (mitigado con `costo_incompleto`); (c) totales mal calculados por multiplicación de filas; (d) rangos muy grandes lentos.
- Mitigación: tests con datos conocidos que verifiquen cada definición (con/sin descuento, con/sin instalación, venta por cobrar excluida, pago anulado excluido, línea sin lote, sin ítems, varias sucursales) y una **prueba de conciliación**: la suma de cobrado del reporte = suma de `pago.monto` del rango, y bruto − descuento = cobrado por venta. Comparación en vivo contra algunas ventas reales antes de publicar (práctica ya usada en el proyecto para cambios de autorización/negocio).
- Reversión: `git revert` del PR; los endpoints desaparecen y los admins vuelven a su código anterior, sin datos que deshacer.

## Consecuencias

**Más fácil:** una sola definición de venta, descuento, cobrado, costo y utilidad; el panel y el Django Admin muestran la misma cifra; agregar una columna o cambiar una regla es un cambio en un solo módulo; el panel obtiene totales sin cargar ni sumar en el navegador.

**Más difícil / deuda aceptada:**
- Las cifras históricas cambian de significado ("Utilidad" ya no es venta bruta); hay que comunicarlo al usuario.
- La calidad de la utilidad depende de que `precio_compra_mtr_lineal` esté cargado en cada lote; `costo_incompleto` lo hace visible pero no lo corrige.
- El tratamiento del descuento (íntegro contra lámina) y el de la instalación (aparte) son decisiones de negocio explícitas y revisables.
- Sin paginación server-side ni exportación; tope de 366 días por consulta.
- Coexisten aún dos criterios de alcance (legado en el resto de admins, nuevo en el panel y en estos dos reportes); unificar el resto es trabajo posterior ya anotado en `ADR-modulo-ordenes-proforma-nota-trabajo-alcance-permisos`.
- Cambia la vista de "Reporte Utilidades" en el Django Admin: hoy agrupa por lote de inventario; el detalle por lote/lámina deberá conservarse como agrupación del mismo cálculo (decisión de presentación para el plan).
