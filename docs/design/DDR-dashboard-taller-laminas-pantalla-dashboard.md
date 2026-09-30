# DDR-dashboard-taller-laminas-pantalla-dashboard: Pantalla Dashboard del panel (KPIs, gráficas, stock crítico, cola de taller, últimas proformas)

**Estado:** Propuesto
**Task relacionado:** TASK-dashboard-taller-laminas
**Fecha:** 2026-09-30

## Actualización (2026-09-30, arquitectura tras integrar Reportes)

`delivery-architect` ajustó el comportamiento por privilegio (ver `ADR-dashboard-taller-laminas-api-agregados-alcance`, Actualización): el servidor solo restringe lo que muestra **ventas cobradas** (permiso `product.view_proxy_pagos`, Admin y Caja) devolviendo ese bloque en `null`. Por eso, en "Comportamiento por privilegio/estado":
- La tarjeta **Ventas del mes** y la serie **Ventas reales** de la línea se ocultan cuando el servidor devuelve `null`; en la línea queda solo la serie "Cotizado". No se decide en el cliente por permiso.
- Los demás widgets **ya no se ocultan por permisos `view_*`**: el servidor no los exige y los grupos pueden no tenerlos. Se muestran a todo staff.
- El aviso "Tu usuario no tiene una sucursal asignada" se dispara con el indicador `sin_sucursal` de `dashboard/kpis`.
- Estado vacío general ("sin permisos para ver datos") deja de aplicar; el caso relevante es solo "sin sucursal".
- El sidebar ya filtra por permiso (`layout/sidebar/sidebar.metadata.ts`); el ítem Dashboard queda sin `permission` y visible a todo staff.

## Contexto

La investigación confirmó que `/dashboard/main` es contenido demo de la plantilla (`panel_admin/src/app/dashboard/main/main.component.html:1-754`) y que el backend no tiene endpoints de agregados. El usuario pidió una pantalla con 4 KPIs, 2 gráficas principales, donut de servicios, alerta de stock crítico, cola de instalaciones y panel lateral de últimas proformas con "Convertir a Venta".

Este DDR decide **qué ve y hace la persona** y con qué piezas se resuelve. No decide el contrato de API, el modelo de datos ni la verificación de permisos en el servidor (eso es `delivery-architect`).

Hechos de la investigación que condicionan el diseño:
- Varias piezas pedidas no tienen respaldo hoy en el modelo: categoría de lámina, "servicio" (Completo/Solo Laterales/Parabrisas), umbral de stock crítico y estado "En Espera"/instalación programada. El diseño debe funcionar **con o sin** esas piezas (ver "Variantes por disponibilidad de dato").
- "Convertir a Venta" ya existe como "Aprobar y generar orden" (`ordenes/proformas/proformas-list.component.html:103-104`, `.ts:50`, `ordenes/proforma-actions.ts:14-20`): visible solo con permiso `add_nota_trabajo` y proforma en estado `proforma`.
- Los estados reales de la nota de trabajo son `en_proceso`, `terminado`, `cancelada`; hay clases de badge ya definidas (`ordenes/ordenes.status.ts`, `assets/scss/_ordenes.scss:132-161`).
- El pedido menciona "Tailwind/React/Vue"; el stack real es Angular 21 standalone + Bootstrap 5 + `ng-apexcharts` (`docs/frontend/panel_admin/reference.md:8-16`), así que el entregable es un componente Angular en `panel_admin/`, no otra tecnología (hipótesis H1 del TASK, a confirmar por el usuario).

`docs/frontend-audit.md` describe deuda de `proforma/` (Angular 16) y no contiene hallazgos sobre dashboards; no aplica a esta pantalla.

## Pantallas/flujos afectados

1. **Dashboard** (`/dashboard/main`, ya es el destino post-login en `authentication/signin/signin.component.ts:50` y la primera entrada del menú en `assets/data/routes.json:4`): la persona ve el estado del taller de un vistazo y puede convertir una proforma a venta sin salir. Reemplaza el contenido demo. Sin cambios en menú ni rutas.
2. **`/dashboard/dashboard2`**: no forma parte de este diseño; queda como está (no está en el menú). Su destino (retirarlo o no) se decide en el plan, no acá.
3. **Navegación de salida** desde el dashboard hacia pantallas ya existentes: `/ordenes/proformas`, `/ordenes/proformas/view/:id`, `/ordenes/notas-trabajo`, `/ordenes/notas-trabajo/view/:id`, `/almacen/inventario`. No se crean pantallas nuevas.

### Distribución (desktop ≥ 1200 px)

```
[ Barra: título · selector de período · selector de sucursal (solo admin) · Actualizar ]
[ KPI Ventas ] [ KPI Proformas activas ] [ KPI Conversión ] [ KPI Instalaciones hoy ]   col-xl-3 c/u
[ Línea: Proformas vs Ventas (col-lg-6) ] [ Barras apiladas: consumo de metros (col-lg-6) ]
[ Donut: servicios (col-lg-5) ] [ Alerta stock crítico de rollos (col-lg-7) ]
[ Cola de instalaciones / órdenes en taller (col-lg-8) ] [ Últimas proformas (col-lg-4) ]
```

- Tablet (768–1199): KPIs 2×2; gráficas y módulos a ancho completo apilados (una por fila); cola y proformas apiladas.
- Móvil (< 768): una columna. Orden: KPIs, stock crítico (lo más accionable), cola, proformas, luego gráficas. Las tablas usan `table-responsive` con scroll horizontal dentro de la tarjeta (sin scroll horizontal de página).

### Contenido por widget

**Barra superior**
- Selector de período con opciones "Este mes" (por defecto), "Mes anterior", "Últimos 12 meses" (este último solo afecta a las dos gráficas históricas). Los KPIs siempre son mensuales/del día, según su definición.
- Selector de sucursal: solo se muestra a quien ve todas las sucursales (admin), con opción "Todas" por defecto, poblado con `ordenes/catalogo/sucursales` (ya existe). Quien no es admin ve un texto fijo "Sucursal: <nombre>" sin selector. Es una decisión visual; el alcance real lo aplica el backend.
- Botón "Actualizar" y texto "Actualizado hh:mm". No hay polling automático (evita sobreingeniería y carga); se refresca al entrar, con el botón, y tras convertir una proforma.

**KPIs (4 tarjetas)** — patrón de tarjeta `card-statistic-4` de la plantilla (`main.component.html:14-106`), pero **sin las imágenes de banner** (`assets/images/banner/*.png`, son de la demo) y con un ícono `feather`/`fas` a la derecha, coherente con el menú (`iconType: feather`).
- *Ventas del mes*: monto en Bs (valor principal, tipografía grande), chip de variación vs. mes anterior (▲ +12 % / ▼ −5 %) y línea auxiliar "vs. Bs X mes anterior". La variación usa color **y** flecha **y** texto (no solo color). Si el mes previo es 0, muestra "Sin datos del mes anterior" en lugar de un porcentaje.
- *Proformas activas*: monto cotizado sin cerrar y cantidad ("12 proformas"). Sin variación.
- *Tasa de conversión*: porcentaje y aclaración "X de Y proformas del período". Barra fina de progreso (`ngb-progressbar`, ya usado en la demo).
- *Instalaciones del día*: número principal y desglose "N en taller · M terminadas hoy". El texto "programadas" solo aparece si arquitectura habilita la programación (ver variantes).
- Cada KPI es clicable hacia el listado correspondiente (Ventas → `/ordenes/notas-venta`; Proformas activas → `/ordenes/proformas`; Instalaciones → `/ordenes/notas-trabajo`; Conversión → sin enlace). Si el listado soporta filtro por estado por query param se pasa; **no verificado** que lo soporte (se decide en el plan); si no, navega sin filtro.

**Gráfica de línea "Proformas cotizadas vs. Ventas reales"** — `ng-apexcharts` tipo `line`, dos series (cotizado / vendido, en Bs) por mes, tooltip compartido con ambos montos y la diferencia; leyenda visible arriba; eje Y con abreviatura (k) y separadores; eje X mes abreviado. 12 meses por defecto.

**Gráfica de barras apiladas "Consumo de lámina (metros)"** — `ng-apexcharts` tipo `bar` con `stacked: true`, un segmento por categoría (o por lámina en la variante de fallback), eje X mes, eje Y metros lineales; tooltip con metros por segmento y total del mes. Colores **fijos por categoría/lámina** (misma serie = mismo color en todas las visitas). Máximo 6 series visibles + "Otras" para evitar leyendas ilegibles.

**Donut "Servicios más solicitados"** — `ng-apexcharts` tipo `donut`; el total al centro ("N servicios"); leyenda a la derecha/abajo con cantidad y porcentaje. Máximo 5 porciones + "Otros".

**Alerta "Stock crítico de rollos"** — tarjeta con lista ordenada de más crítico a menos, mostrando solo lo que no está en verde por defecto (con interruptor "Ver todos"). Cada fila: nombre de lámina + ancho, sucursal (si se ve más de una), "N rollos · X,X m disponibles", una barra de nivel y un indicador de estado con **ícono + texto + color**: verde "OK", amarillo "Bajo", rojo "Crítico". Encabezado de la tarjeta con contadores (ej. "2 críticos · 3 bajos"). Clic en una fila lleva a `/almacen/inventario`. El criterio de umbral **no se define acá** (pregunta abierta 5 del TASK); el diseño solo consume el estado que entregue la API.

**Tabla "Cola de instalaciones / Órdenes en taller"** — tabla Bootstrap simple (`table table-striped`, patrón de `main.component.html:347-664`), no `ngx-datatable`, porque es un widget acotado sin paginación. Columnas: Cliente, Vehículo/Placa (modelo arriba, placa debajo en tenue), Lámina instalada (nombre de la lámina; si hay varias, la principal + "+N"), Estado (badge), Técnico asignado, y un enlace "Ver" a la nota de trabajo. Orden: en proceso primero, luego terminadas de hoy, más antiguas arriba dentro de cada grupo. Máximo 10 filas y pie "Ver todas las notas de trabajo". Técnico vacío: "No asignado" en gris cursivo (mismo criterio que la vista de nota de trabajo, `DDR-modulo-ordenes-...` Actualización 6). Tabla con encabezado fijo dentro de `ng-scrollbar` (ya importado en la demo) solo si supera la altura.

**Panel "Últimas proformas emitidas"** — lista vertical de las 6 más recientes: Nº, cliente, modelo/placa, monto a pagar (`total_a_pagar`), fecha corta y badge de estado. **Solo las filas en estado `proforma`** muestran el botón "Convertir a venta". Ver flujo abajo.

### Flujo "Convertir a venta"

1. La persona pulsa "Convertir a venta" en una fila (botón `btn-tbl-activate`, mismo estilo del listado).
2. Se abre la confirmación existente `confirmGenerateNota(id)` (SweetAlert; texto ya explica que descuenta inventario, crea nota de trabajo y nota de venta). No se escribe un mensaje nuevo: se reutiliza para no divergir.
3. Mientras se procesa, el botón queda deshabilitado con spinner (evita doble clic).
4. Éxito: mensaje "Orden generada" y recarga de los widgets afectados (KPIs, cola, proformas, stock). La fila pasa a badge "En trabajo".
5. Error (409 por falta de stock, ancho, etc.): `showErrorAlert` con el mensaje del servidor, sin recargar; mismo tratamiento que el listado de proformas.
6. Etiqueta: "Convertir a venta" (lenguaje del usuario) con `title="Aprobar y generar orden"` para que quien conoce el listado reconozca la acción.

## Componentes/patrones elegidos

| Necesidad | Elección | Justificación (referencia) |
|---|---|---|
| Gráficas (línea, barras apiladas, donut) | `ng-apexcharts` | Ya instalado y usado en `dashboard/main` y `dashboard2` (`main.component.ts:1-40`, `dashboard2.component.ts:1-60`); `reference.md:89` lista `apex.html` entre las páginas de ejemplo de Charts. Sin dependencia nueva. |
| KPIs | Tarjeta `card-statistic-4` sin banner | Patrón visual de la propia pantalla actual (`main.component.html:14-106`); coherente con el resto del panel. |
| Tabla de cola | Tabla Bootstrap (`bootstrap-table.html`, `reference.md:84`) | Widget acotado a 10 filas sin paginación server-side; `ngx-datatable` (`reference.md:85`) es para listados completos y aportaría peso sin beneficio. |
| Barras de nivel del stock | `ngb-progressbar` | Ya importado en la demo (`main.component.ts`), sin dependencia nueva. |
| Badges de estado | `statusClass()` + `_ordenes.scss` | Reutiliza los estados/colores ya vigentes en Ordenes (`ordenes.status.ts`, `_ordenes.scss:132-161`); los estados de la cola son los del backend. |
| Acción de conversión | `confirmGenerateNota`, `showErrorAlert`, `OrdenesService.generarNotaTrabajo` | Reutilización literal de `ordenes/proforma-actions.ts` y `ordenes/ordenes.service.ts`; evita reglas duplicadas. |
| Tema claro/oscuro | Colores desde variables/tokens de la plantilla y `foreColor` de ApexCharts según tema | La plantilla centraliza tema en `config/config.service.ts` (`reference.md:94-96`); las gráficas de la demo usan `foreColor` fijo `#9aa0ac`, hay que verificar contraste en ambos temas (ver Consecuencias). |

## Variantes por disponibilidad de dato

El diseño de cada widget tiene una **variante completa** (lo pedido) y una **variante de respaldo** con lo que existe hoy. Qué variante se construye depende de las decisiones de `delivery-architect` (preguntas 3–6 del TASK). No se diseñan estados imposibles: cada widget declara qué muestra si su dato no existe.

| Widget | Variante completa | Variante de respaldo (dato actual) |
|---|---|---|
| Barras apiladas | Segmentos por **categoría** de lámina (Cerámica, Seguridad 8mil, Térmico…) | Segmentos por **lámina** (`Window_Film.name`), título "Consumo por lámina" |
| Donut | **Servicios** (Completo / Solo Laterales / Parabrisas) | **Ítems del vehículo más solicitados** (`Car_Part`), título "Ítems más solicitados" |
| Estados de la cola | "En espera", "En proceso", "Completado" | "En proceso", "Terminado" (y "Cancelada" fuera de la cola); etiquetas iguales a las del resto del panel |
| KPI Instalaciones | "N programadas · M en taller · K listas" | "N en taller · M terminadas hoy" |
| Stock crítico | Semáforo con umbral configurable | Semáforo con regla fija que defina arquitectura |

En todos los casos el título del widget dice lo que **realmente** muestra; nunca se usa un título que prometa más que el dato.

## Alternativas consideradas

1. **Librería de gráficas.** `ng-apexcharts` (elegida) vs. `ngx-echarts` / `ng2-charts` (Chart.js) / `@swimlane/ngx-charts`, todas ya instaladas. Se descartan por consistencia: las dos pantallas demo existentes ya usan Apex y las cuatro gráficas pedidas (line, stacked bar, donut) están cubiertas. Mezclar dos librerías en una pantalla duplica estilos y temas.
2. **Tablas del dashboard.** `ngx-datatable` (consistente con los listados de Ordenes) vs. tabla Bootstrap simple (elegida). El costo de `ngx-datatable` (paginación, medidas, sort) no se justifica para 10 filas fijas; se acepta la inconsistencia visual menor, mitigada usando los mismos badges y estilos de fila.
3. **Panel lateral de proformas.** Lista de tarjetas compactas (elegida) vs. tabla completa. Con el ancho `col-lg-4` una tabla de 6 columnas no cabe; la lista permite mostrar el botón sin scroll horizontal.
4. **Un selector de sucursal global (elegido, solo admin) vs. tarjetas por sucursal.** Un selector mantiene un solo tablero simple. Comparar sucursales lado a lado queda fuera de alcance (no pedido).
5. **Actualización automática (polling) vs. manual.** Manual elegido: el pedido no exige tiempo real y el backend aún no tiene endpoints agregados; se puede sumar después sin rediseño.
6. **Botón "Convertir a venta" con modal propio vs. reutilizar confirmación existente.** Se reutiliza para no divergir de las reglas y textos del flujo de Ordenes.

## Comportamiento por privilegio/estado

**Por privilegio (decisión de UX, no de seguridad)**
- El dashboard es visible para todo usuario staff autenticado (misma puerta que el resto del panel).
- Cada widget se **oculta** (no se deshabilita) si la persona no tiene el permiso de ver su dato, siguiendo `authService.hasPermission()` (`core/service/auth.service.ts:71-81`): Ventas y Conversión → ver notas de venta; Proformas activas y panel lateral → ver proformas; Cola e Instalaciones → ver notas de trabajo; Stock crítico y consumo de metros → ver inventario. Ocultar evita tarjetas vacías con tooltip que no aportan; el grid se reacomoda sin huecos.
- El botón "Convertir a venta" se oculta sin permiso `add_nota_trabajo` o si la proforma no está en `proforma`, igual que en el listado.
- Sin ningún permiso visible: estado vacío "No tienes datos para mostrar en el dashboard. Contacta al administrador."
- **Requiere que arquitectura defina cómo se verifica del lado servidor** el permiso y el alcance por sucursal de cada agregado (admin ve todo, el resto su sucursal, sin sucursal nada) — **el frontend no debe ser la única barrera**: ocultar un widget no evita que se llame al endpoint.

**Por estado de carga (cada widget es independiente)**
- *Cargando*: esqueleto (placeholder gris) del tamaño final; sin saltos de layout.
- *Vacío*: mensaje específico por widget ("Aún no hay ventas este mes", "Sin órdenes en taller", "Sin proformas recientes", "Sin alertas de stock: todo en nivel OK" con ícono verde).
- *Error*: mensaje dentro de la tarjeta con botón "Reintentar"; un widget que falla no bloquea a los demás.
- *Sin sucursal asignada* (usuario no admin): un aviso único arriba "Tu usuario no tiene una sucursal asignada" y ningún widget con datos (coincide con el comportamiento del alcance en el backend).

**Accesibilidad**
- El semáforo y los deltas nunca dependen solo del color: siempre ícono + texto.
- Los gráficos tienen un resumen textual accesible (`aria-label`/texto oculto con los valores clave) y los datos de la serie disponibles en el tooltip; los colores de series se eligen con contraste suficiente en ambos temas.
- Todos los botones y filas clicables son focalizables por teclado.

## Consecuencias

- **Queda más simple:** una sola pantalla, sin rutas/menú nuevos, sin dependencias nuevas, y la acción "Convertir a venta" no duplica reglas de negocio.
- **Deuda visual aceptada:** la cola usa tabla Bootstrap y no `ngx-datatable` como los listados; los colores de las series de gráfica son propios del dashboard (no hay guía de paleta de charts en la plantilla) y hay que revisarlos contra el tema oscuro.
- **Deuda pendiente en otras pantallas:** el filtro por estado vía query param (`/ordenes/proformas?status=...`) no está verificado en el listado; si se quiere que los KPIs lleven a listados ya filtrados, habrá que soportarlo en el listado (decisión del plan).
- **`dashboard2`** y sus imágenes de demo quedan sin uso real; retirarlo se decide en el plan.
- **Dependencias con arquitectura (no decididas acá):** contrato de los agregados y definición de "venta"; categoría de lámina; modelado de "servicio"; umbral de stock crítico; estado "En espera"/programación; alcance por sucursal y cómo se verifica; permisos de servidor para cada widget. Hasta que se resuelvan, se construyen las variantes de respaldo de la tabla anterior.
- **Pendiente de confirmación por el usuario:** que el entregable sea un componente Angular integrado (H1) y que la etiqueta "Convertir a venta" se use en lugar de "Aprobar y generar orden".
