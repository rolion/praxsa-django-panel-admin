# DDR-filtros-busqueda-reportes-filtros-listados-ordenes: Barra de filtros en los listados de Proformas, Notas de Trabajo y Notas de Venta de `panel_admin/`

**Estado:** Propuesto
**Task relacionado:** TASK-filtros-busqueda-reportes
**Fecha:** 2026-09-30

## Contexto
El solicitante aclaró (2026-09-30, ver "Hallazgo post-implementación" del TASK) que los filtros pedidos son para las **listas del panel Angular** (Órdenes), no para el Django Admin. Hoy esas listas solo tienen un buscador de texto y, en Proformas, un select de estado; filtran en el cliente sobre todas las filas ya cargadas (`proformas-list.component.ts:99-112`, `notas-trabajo-list.component.ts:58-72`, `notas-venta-list.component.ts:78-`), y no hay paginación de servidor (`ngx-datatable` con `[limit]="10"`).

Filtros pedidos:
- **Proformas**: sucursal (solo las del usuario), marca, modelo, rango de fecha, estado.
- **Notas de Trabajo**: sucursal (solo las del usuario), marca, modelo, instalador, estado, cobro.
- **Notas de Venta**: sucursal (solo las del usuario), rango de fecha, trabajo (estado de la nota de trabajo), cobro (estado de la nota de venta).

## Pantallas/flujos afectados
1. `ordenes/proformas/proformas-list.component` — filtra la tabla de proformas.
2. `ordenes/notas-trabajo/notas-trabajo-list.component` — filtra la tabla de notas de trabajo.
3. `ordenes/notas-venta/notas-venta-list.component` — filtra la tabla de notas de venta.

En cada una la persona elige valores en una barra de filtros sobre la tabla y la tabla se actualiza al instante; puede combinar filtros con el buscador de texto existente y limpiarlos con un botón. No se crean pantallas nuevas. **Ventas Diarias y Utilidad no cambian.**

## Componentes/patrones elegidos
- **Contenedor**: tarjeta `card section-card` con encabezado `section-header` (ícono `fa-filter`, título "Filtros"), el mismo patrón de las pantallas de Reportes (`reportes/ventas-diarias/ventas-diarias.component.html`, DDR-reportes-utilidad-ventas-diarias-pantallas-reportes). Va **entre el breadcrumb y la tarjeta de la tabla**; en pantallas chicas los controles caen a 2 por fila (`col-6 col-md-*`).
- **Controles**: `<select class="form-select form-control">` con primera opción "Todas/Todos" y `<input type="date" class="form-control">` para Desde/Hasta, según el patrón de `form-elements.html` (`docs/frontend/panel_admin/reference.md:86`). **Sin datepicker ni dependencia nueva** (regla de `docs/CLAUDE.md`).
- **Tabla**: se mantiene `ngx-datatable` (`reference.md:85`, ya usado por los tres listados); no se toca.
- **Buscador de texto**: se queda en el encabezado de la tabla, junto al botón "Nueva proforma". El select de estado de Proformas, hoy en ese encabezado (`proformas-list.component.html:32-38`), **se mueve a la barra de filtros** para que todos los filtros vivan en un solo lugar.
- **Botón "Limpiar"** (`btn btn-outline-secondary`) al final de la barra; no hay botón "Aplicar".
- **Resultado vacío**: mensaje `alert alert-info` existente, ajustado a "No hay resultados con los filtros aplicados." cuando hay filas cargadas pero el filtro las oculta (se distingue de "No hay proformas para mostrar" y del aviso de sucursal).

**Filtros por pantalla** (orden izquierda → derecha; título del control entre comillas):

| Pantalla | Controles |
|---|---|
| Proformas | "Sucursal", "Marca", "Modelo", "Desde", "Hasta" (fecha de la proforma), "Estado" |
| Notas de Trabajo | "Sucursal", "Marca", "Modelo", "Instalador", "Estado" (en proceso / terminado / cancelada), "Cobro" (por cobrar / pagada / anulada / sin nota de venta) |
| Notas de Venta | "Sucursal", "Desde", "Hasta" (fecha de creación), "Trabajo" (estado de la nota de trabajo: en proceso / terminado / cancelada), "Cobro" (estado de la nota de venta) |

**Comportamiento de los controles**
- **Sucursal**: opciones = las sucursales del usuario que ya devuelve `OrdenesService.listSucursales()` (solo las habilitadas y en su alcance; Admin ve todas). Si el usuario tiene **una sola**, el select se reemplaza por su nombre en texto (mismo tratamiento que `showSucursalSelector` de Ventas Diarias) para no mostrar un control con una sola opción.
- **Marca / Modelo**: el select de Modelo se llena con los modelos presentes en las filas cargadas y se **acota a la marca elegida**; al cambiar la marca se reinicia Modelo a "Todos". Proformas ya trae `car_brand_name` y `car_model_name`; en Notas de Trabajo la marca no viaja hoy (solo `car_model_name`), ver "Requiere de arquitectura/plan".
- **Instalador**: opciones = instaladores presentes en las filas cargadas, más "Sin instalador".
- **Fechas**: Desde/Hasta inclusivos, comparando solo la parte de fecha (mismo criterio local sin conversión de zona horaria que `reportes.filtros.ts`); si Desde > Hasta se muestra un mensaje `text-danger` y no se filtra por fecha hasta corregirlo. Filas sin fecha (nota de venta con `created_on` nulo) no pasan cuando hay un rango activo.
- **Combinación**: todos los filtros y el buscador se aplican con **AND**; cada cambio actualiza la tabla al instante y devuelve la paginación a la primera página (igual que el buscador actual).
- **Opciones dependientes de datos**: los desplegables de marca, modelo e instalador solo ofrecen valores que existen en las filas cargadas, para que ninguna combinación de un solo filtro dé una tabla vacía por una opción imposible.

## Alternativas consideradas
- **Filtros de servidor con botón "Aplicar"** (como los reportes de Ventas): descartada para esta etapa. Los listados cargan todas las filas de la sucursal y ya filtran en el cliente; pasar a servidor exigiría nuevos parámetros de API, paginación y totales (contrato) sin un problema de volumen demostrado. Trade-off aceptado: si el volumen crece, habrá que migrar a filtros de servidor (el DDR de reportes ya define ese patrón).
- **Filtros en el encabezado de la tabla** (más selects junto al buscador): descartada; con 5-6 controles el encabezado queda desbordado y difícil en móvil. La tarjeta "Filtros" es consistente con Reportes.
- **Panel lateral o modal de filtros**: descartada por sobreingeniería para 5-6 controles.
- **Datepicker de la plantilla**: descartada; `<input type="date">` ya se usa en Reportes y evita dependencia nueva.
- **Pestañas por estado** en lugar de select: descartada; el estado es solo uno de varios filtros combinables.

## Comportamiento por privilegio/estado
- Sin cambios de permisos: quien ve la lista hoy ve la misma barra de filtros. Las opciones de sucursal salen de `listSucursales()`, que ya está acotado al alcance del usuario.
- Usuario **sin sucursal asignada**: se conserva el aviso actual ("Asigne una sucursal al usuario…"); la barra de filtros se oculta o queda deshabilitada porque no hay filas.
- **Nota de seguridad**: esto es solo UX. El alcance real por sucursal (qué filas puede recibir el usuario) lo aplica el backend en cada endpoint (ADR-modulo-ordenes-proforma-nota-trabajo-alcance-permisos); el frontend no es la barrera. Requiere que arquitectura/plan confirme que los endpoints de lista siguen acotando por sucursal y que `listSucursales()` devuelve solo las sucursales del usuario.

## Requiere de arquitectura/plan (fuera de este DDR)
- Confirmar que el listado de **Notas de Trabajo** puede exponer la marca del vehículo (p. ej. `car_brand_name`, como ya hace la proforma) sin romper el contrato de la API que Angular ya consume.
- Confirmar que los filtros por **nombre de marca/modelo** son suficientes o si conviene exponer ids.

## Consecuencias
- Los tres listados quedan con la misma barra de filtros y comportamiento (posible componente/función compartida de filtrado en el plan, sin exigirlo aquí).
- Se acepta deuda: el filtrado sigue en el cliente sobre todas las filas cargadas; las opciones de marca/modelo/instalador salen de los datos cargados (no del catálogo completo) y **Proformas ya no tendrá el select de estado en el encabezado**.
- Las pantallas de Reportes (Ventas Diarias, Utilidad) siguen con su propio patrón de filtros de servidor; la convivencia de dos patrones (cliente en listados, servidor en reportes) es consciente.
- Los filtros ya implementados en el Django Admin (PR #55) no cambian esta decisión de diseño; su permanencia en el PR se decide en el plan.
