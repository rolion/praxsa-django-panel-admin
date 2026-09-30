# DDR-reportes-utilidad-ventas-diarias-pantallas-reportes: Menú "Reportes" con Ventas Diarias y Utilidad en `panel_admin/`

**Estado:** Propuesto
**Task relacionado:** TASK-reportes-utilidad-ventas-diarias
**Fecha:** 2026-09-30

## Contexto

La investigación del task confirmó que "Reporte Ventas Diaria" y "Reporte Utilidades" solo existen en el Django Admin (`report_daily_sell.py`, `report_utilidad.py`) y que `panel_admin/` no tiene pantallas de reportes. El usuario pidió (2026-09-30) llevarlos al panel en esta misma tarea, de solo lectura, con estas reglas:

- Utilidad = venta − costo de compra.
- Solo ventas **pagadas**, mostradas **con y sin descuento**.
- Poder **distinguir venta con instalación vs. sin instalación** (metro lineal).
- Agregar columnas y **totales**; que las cifras reflejen la realidad.

Este DDR define solo qué ve y hace la persona. No define contrato de API, fórmulas contables (cómo se reparte el descuento, cómo entra la instalación en la utilidad) ni permisos de servidor: eso es de `delivery-architect`.

Diseño de partida: los reportes son **tableros de consulta con filtros + totales + tabla**, distintos de los listados CRUD del panel (`ordenes/notas-venta/notas-venta-list.component.html`). Por eso los filtros son **del servidor** (el rango de fechas define qué se suma) y no la búsqueda client-side de los listados.

## Pantallas/flujos afectados

1. **Menú principal**: nuevo grupo **"Reportes"** con 2 submenús: *Ventas Diarias* y *Utilidad*.
2. **Ventas Diarias** (`/reportes/ventas-diarias`): la persona elige día/rango, sucursal y tipo de venta; ve totales del período y el detalle de cada cobro.
3. **Utilidad** (`/reportes/utilidad`): la persona elige rango, sucursal y tipo de venta; ve la utilidad del período y su detalle por venta y por lámina.

Solo consulta: sin crear, editar ni borrar; sin enlaces de acción salvo "Ver" hacia la nota de venta existente. No se tocan los reportes del Django Admin en este DDR.

### Ventas Diarias

**Filtros** (barra sobre las tarjetas, botón **Aplicar**; no consulta en cada cambio):
- Desde / Hasta (fecha). Por defecto **hoy**–**hoy** (es el reporte "diario"). Rango invertido → aviso "La fecha inicial no puede ser mayor que la final" sin consultar.
- Sucursal: selector con "Todas" visible solo si la persona ve varias sucursales; con una sola, se muestra fija y en solo lectura (mismo criterio que la sucursal en el formulario de proformas, DDR de Órdenes).
- Tipo de venta: Todos / Con instalación / Metro lineal.
- Tipo de pago: Todos / Efectivo / Tarjeta-QR (propuesto: el reporte hoy no lo muestra y es el dato más útil para cuadrar caja; confirmar con el usuario).

**Tarjetas de totales** (del período filtrado, todas las páginas): Nº de ventas, **Venta bruta**, **Descuentos**, **Total cobrado** (neto).
**Desglose por tipo de venta** (2 filas: Con instalación, Metro lineal → Nº, bruta, descuento, cobrado) y **por tipo de pago** (Efectivo, Tarjeta-QR → Nº, cobrado). Es lo que resuelve "distinguir con y sin instalación" a nivel de totales.

**Tabla de detalle** (una fila por pago). Columnas: Fecha/hora de pago, Nº nota de venta (enlace a `/ordenes/notas-venta/view/:id`), Nº proforma, Cliente, Vehículo (vacío en metro lineal), Tipo de venta (badge), Sucursal (solo si ve varias), Tipo de pago, Registro contable, **Lámina**, **Instalación** (vacío/"—" en metro lineal), **Bruto**, **Descuento**, **Cobrado**. Importes alineados a la derecha, formato `1.234,00 Bs` consistente con las demás tablas (`{{ value }} Bs` en `notas-venta-list.component.html:70`; el formato final lo fija el plan). Búsqueda client-side por Nº, cliente o CI/NIT como en los listados, sobre las filas ya traídas.

### Utilidad

**Filtros**: mismos que Ventas Diarias salvo Tipo de pago; el rango por defecto es el **mes en curso** (utilidad se lee por período, no por día).

**Tarjetas** (con y sin descuento, como pidió el usuario): Venta bruta, Descuentos, Venta neta, **Costo de compra**, **Utilidad antes de descuento**, **Utilidad después de descuento**, y **Margen %** (sobre venta neta). Debajo, el mismo desglose por tipo de venta (con instalación vs. metro lineal). El **ingreso por instalación** se muestra como línea propia y **no se mezcla** con la utilidad de lámina hasta que arquitectura/negocio definan su tratamiento (los modelos no tienen costo de compra de la instalación).

**Tabla 1 — Utilidad por venta** (una fila por nota de venta pagada): Fecha de pago, Nº nota de venta (enlace), Cliente, Tipo de venta (badge), Sucursal (si ve varias), Venta lámina, Instalación, Descuento, Costo de compra, **Utilidad** y **Margen %**. Se elige la venta como fila principal porque el descuento existe por proforma (`Proforma_Header.discount`), no por lámina: solo así "con y sin descuento" es legible sin repartir importes.

**Tabla 2 — Resumen por lámina** (tarjeta secundaria debajo): Sucursal, Lámina/bobina, Metros vendidos, Venta lámina, Costo de compra, Utilidad antes de descuento. Sin columna de descuento (no es atribuible a una lámina); una nota al pie lo aclara.

## Componentes/patrones elegidos

- **Menú**: nuevo grupo en `panel_admin/src/assets/data/routes.json` con la misma forma que Usuarios/Vehículos/Almacén/Órdenes (`"class": "menu-toggle"`, submenús `"ml-menu"`, ícono feather, p. ej. `bar-chart-2`). Patrón multinivel de la plantilla: `docs/frontend/panel_admin/reference.md:92`.
- **Rutas**: nuevo `reportes.routes.ts` cargado con `loadChildren` como los demás módulos (`app.routes.ts`), bajo el `AuthGuard` existente.
- **Tablas**: `ngx-datatable` (`class="material"`, `[limit]="10"`, `columnMode="force"`), mismo markup que `notas-venta-list.component.html:41-95`; es el ejemplo real de `advance-table/` (`reference.md:85`). Números alineados a la derecha y fila de resumen con los totales, igual que la tabla de detalle de "Ver proforma" (DDR de Órdenes, Actualización 3). Los totales de la fila de resumen y de las tarjetas son **los mismos valores del servidor**, no una suma de la página visible.
- **Tarjetas de totales**: `card` de la plantilla con el sistema de tarjetas de `assets/scss/_ordenes.scss` (`.section-card`, `.section-header`, grid etiqueta-gris/valor-en-negrita de `.info-label`/`.info-value`, `_ordenes.scss:13-108`), extendiendo `_ordenes.scss` con un bloque `.reporte-*` en vez de copiar las tarjetas demo `card-statistic-4` del dashboard (que llevan imágenes y barras de progreso decorativas: `dashboard/main/main.component.html:12-31`). Se prefiere consistencia con Órdenes sobre reutilizar la tarjeta demo.
- **Filtros**: controles `form-select form-control` y `<input type="date">` como en `almacen/inventario/inventario-create.component.html` (patrón de `form-elements.html`, `reference.md:86`); botón primario `btn-primary rounded-button` **Aplicar** y secundario **Limpiar** (vuelve a los valores por defecto). Sin datepicker nuevo: no se agrega dependencia (regla de `docs/CLAUDE.md`).
- **Badge de tipo de venta**: reutiliza `.status-badge` de `_ordenes.scss:132` con dos clases existentes de color (una por tipo), sin sistema de color nuevo.
- **Estados de carga/error/vacío**: `loadingIndicator` de `ngx-datatable`, `alert alert-danger` para error y `alert alert-info` "No hay ventas pagadas en el período seleccionado", y `alert alert-warning` "Asigne una sucursal al usuario" para quien no tiene sucursal (mismos textos y patrón que `notas-venta-list.component.html:46-53`; paridad con el mensaje del reporte de Django Admin).
- **Sin gráficos** en esta entrega (ver alternativas).

## Alternativas consideradas

- **Tarjetas demo `card-statistic-4` del dashboard**: se descartan por las imágenes y barras decorativas y por romper consistencia con las tarjetas de Órdenes; la plantilla trae ECharts/ApexCharts/Chart.js (`reference.md:89`) pero un gráfico no es necesario para cuadrar ventas y utilidad y sumaría una decisión de librería.
- **Utilidad con una sola tabla por lámina/lote** (como hoy en `report_utilidad.py`): se descarta como vista principal porque el descuento no se puede mostrar sin repartirlo; se conserva como Tabla 2 secundaria.
- **Dos pestañas (`NgbNav`) Por venta / Por lámina** en vez de dos tarjetas apiladas: viable (ng-bootstrap está instalado, `reference.md:12`), pero oculta la mitad de la información tras un clic y agrega estado de UI; con solo dos tablas apiladas se ve todo a la vez.
- **Filtrar en cliente** (traer todo y filtrar como los listados): se descarta; los totales deben cubrir todo el período y sin paginación DRF global (pendiente en el DDR de Órdenes) el volumen de un rango largo no debe viajar al navegador.
- **Un solo reporte con selector "Ventas / Utilidad"**: se descarta; tienen filtros, públicos (utilidad expone costos) y permisos distintos.
- **Botón Exportar (CSV/Excel/PDF)**: no fue pedido y no existe hoy en los reportes; queda fuera del alcance y como posible ampliación.
- **Reusar `AdvanceTableComponent`**: descartado por lo ya decidido en los DDR de Usuarios/Vehículos/Almacén/Órdenes (es una página de ejemplo, no un componente parametrizable).

## Comportamiento por privilegio/estado

| Situación | Comportamiento visual |
|---|---|
| Persona con acceso a Ventas Diarias | Ve el submenú "Ventas Diarias" y la pantalla completa |
| Persona **sin** acceso a Utilidad | El submenú "Utilidad" se **oculta**; si entra por URL, la pantalla muestra "No tiene permiso para ver este reporte" (no una tabla vacía) |
| Usuario que ve varias sucursales | Selector con "Todas" y columna Sucursal |
| Usuario con una sola sucursal | Sucursal fija, solo lectura; sin columna Sucursal |
| Usuario sin sucursal asignada | Aviso "Asigne una sucursal al usuario"; sin tabla ni totales |
| Período sin ventas | Tarjetas en `0,00 Bs` y aviso de vacío |
| El servidor rechaza (403/error) | Se muestra el mensaje del servidor; nunca cifras parciales |

Los elementos no autorizados **se ocultan** (no se deshabilitan), igual que en Almacén y Órdenes. Hoy el menú lateral **no oculta ítems por permiso** (no hay `hasPermission`/`hasGroup` en `app/layout/` ni en `core/guard/`; solo `AuthService.hasPermission` en `core/service/auth.service.ts:81`, usado dentro de las pantallas), así que ocultar el submenú requiere un cambio en el sidebar que este DDR solo pide, sin decidir cómo.

**Nota explícita de seguridad — esto es solo UX, no la barrera real.** Ocultar el submenú o mostrar un aviso no impide llamar al endpoint directamente. Requiere que arquitectura defina cómo se verifica del lado servidor: (a) qué rol/permiso puede ver cada reporte — Utilidad expone `precio_compra_mtr_lineal` y márgenes, mucho más sensible que Ventas Diarias; (b) el alcance por sucursal (hoy `sucursales[0]` en `Pago_Business.get_pago_queryset_by_role`, `business/pago.py:26-39`, frente a "todas las sucursales habilitadas" en la API del panel); (c) que el reporte sea de solo lectura. Este DDR no decide qué rol exacto puede ver cada uno, y el frontend no debe ser la única barrera.

## Consecuencias

- Reportes queda visualmente consistente con Órdenes (tarjetas, badges, `ngx-datatable`, alertas) y no agrega dependencias.
- Es el primer módulo del panel con **filtros de servidor y totales agregados**: los listados actuales filtran en cliente. Arquitectura debe definir el contrato de filtros, totales y paginación; un rango grande sin paginación puede ser pesado.
- Las cifras del panel y del Django Admin **deben coincidir**; si el Django Admin se corrige aparte con otra lógica, habría dos verdades. Se pide una única lógica de cálculo (decisión de arquitectura).
- Pendientes que este DDR **no cierra** y quedan para arquitectura/negocio: cómo se reparte el descuento entre láminas e instalación; si el ingreso por instalación entra en la utilidad y cómo; qué cuenta como "fecha" del reporte (fecha de pago `pago.created_on`); el rol exacto de cada reporte; el formato numérico final.
- Deuda aceptada: sin gráficos ni exportación; el menú seguirá mostrando ítems no permitidos en el resto de grupos aunque se oculten en Reportes (inconsistencia visual menor hasta unificar el sidebar).
- Otras pantallas (Notas de Venta) no requieren cambio; solo se enlaza a su vista existente.

## Actualización 1 (2026-09-30, al planificar)

Dos pendientes que el ADR de cálculo y el de permisos dejaron para el diseño, resueltos de forma mínima con clases ya existentes:
- **Costo de compra faltante (`costo_incompleto`)**: en la tabla "Utilidad por venta" la fila afectada lleva un ícono de advertencia con `title` "Falta el costo de compra: la utilidad de esta venta está sobreestimada"; sobre las tarjetas de Utilidad aparece un `alert alert-warning` con el número de ventas afectadas ("N ventas sin costo de compra completo; su utilidad está sobreestimada") cuando el total es mayor que 0. No se agrega columna ni color nuevos.
- **Menú filtrado por permiso**: los submenús "Ventas Diarias" (`view_proxy_pagos`) y "Utilidad" (`view_utilidades`) se ocultan sin el permiso, y el grupo "Reportes" se oculta si no queda ninguno. Solo cambia el sidebar para este grupo; el resto del menú se mantiene como está (deuda ya anotada arriba).
