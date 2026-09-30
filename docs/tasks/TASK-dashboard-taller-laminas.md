# TASK-dashboard-taller-laminas: Dashboard del panel para el taller de láminas (KPIs, gráficas, stock crítico, cola de instalaciones, últimas proformas)

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-dashboard-taller-laminas
**Pull Request:** [#56](https://github.com/rolion/praxsa-django-panel-admin/pull/56)

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-09-30 | (nuevo) → INVESTIGATION | Task creado | delivery-investigate |
| 2026-09-30 | INVESTIGATION → DESIGN → ARCHITECTURE | DDR de la pantalla Dashboard escrito (layout, widgets, variantes por disponibilidad de dato, flujo Convertir a venta); pendientes de dato/permiso pasan a arquitectura | delivery-design |
| 2026-09-30 | ARCHITECTURE → PLANNING | ADR de API/alcance y de definiciones de métricas registrados; usuario resolvió venta=pagada, categoría=por nombre de lámina, servicio=ítems, stock=regla fija; sin migraciones | delivery-architect |
| 2026-09-30 | PLANNING → ARCHITECTURE | El plan no se escribió: master trajo el PR #54 (módulo de reportes) que contradice dos decisiones de los ADR (cálculo único de ventas cobradas y permiso `view_proxy_pagos` para ver ventas). Requiere revisar los ADR con `/delivery-architect` | delivery-plan |
| 2026-09-30 | ARCHITECTURE → PLANNING | ADR de API/alcance y de métricas revisados tras el PR #54 (ventas cobradas y permiso `view_proxy_pagos` reutilizados de Reportes; alcance con `get_panel_pago_queryset`/`get_panel_inventario_queryset`; `sin_sucursal`); DDR ajustado | delivery-architect |
| 2026-09-30 | PLANNING → ENGINEERING | Plan v1 escrito y PR #56 abierto; queda a la espera de la aprobación humana del plan y de las 6 preguntas abiertas antes de implementar | delivery-plan |
| 2026-09-30 | ENGINEERING → REVIEW | Implementación completa de las fases 1 a 5 del plan v1 (backend, API, servicio, pantalla); la verificación en vivo contra el backend real (paso 20) queda para review/usuario | delivery-engineer |
| 2026-09-30 | REVIEW → ENGINEERING | Quality Gate FAIL: 1 issue High (valores KPI ilegibles en tema oscuro) y 1 Low (contraste del botón Convertir a venta), ambos IMPLEMENTATION; `view_proxy_pagos`, equivalencia con Reportes y alcance verificados en vivo | delivery-review |
| 2026-09-30 | ENGINEERING → REVIEW | Corregidos REV-01 (contraste de cifras y enlaces en tema oscuro) y REV-02 (contraste del botón Convertir a venta) | delivery-engineer |
| 2026-09-30 | REVIEW → PUBLISH | Quality Gate PASS en el re-review sobre `02e9153`: REV-01 y REV-02 resueltos; queda abierto REV-03 (Low) | delivery-review |
| 2026-09-30 | PUBLISH → ENGINEERING → REVIEW | A pedido del usuario se corrige REV-03 (`.text-muted` en tema claro) antes de publicar | delivery-engineer |
| 2026-09-30 | REVIEW → PUBLISH | Quality Gate PASS sobre `1c830f6`: REV-01, REV-02 y REV-03 resueltos; sin issues abiertos | delivery-review |

## Investigación

### Requerimiento
Pedido literal (resumido): actuar como diseñador UX/UI y desarrollador web experto en tableros SaaS y estructurar/generar la maqueta o componentes del **Dashboard** para el taller de instalación de láminas de seguridad/polarizado, adaptado al flujo Inventario de Rollos → Cotizaciones/Proformas → Ventas → Instalaciones. Distribución pedida:

1. **4 KPIs**: Ventas del Mes (monto + comparativa vs. mes previo), Proformas Activas (monto cotizado sin cerrar), Tasa de Conversión (% de cotizaciones concretadas), Instalaciones del Día (vehículos programados/listos).
2. **Gráficas**: línea "Proformas cotizadas vs. Ventas reales" (histórico mensual); barras apiladas "Consumo de metros de lámina por categoría" (Cerámica, Seguridad 8mil, Térmico, etc.).
3. **Inventario/servicios**: donut "Servicios más solicitados" (Completo, Solo Laterales, Parabrisas); tarjeta de alerta de **stock crítico de rollos** con semáforo verde/amarillo/rojo.
4. **Tablas**: cola de instalaciones/órdenes en taller (Cliente, Vehículo/Placa, Lámina instalada, Estado En Espera/En Proceso/Completado, Técnico asignado); panel lateral "Últimas proformas emitidas" con botón "Convertir a Venta".

El formato de entrega quedó sin especificar (el pedido trae el placeholder `[especificar lo que necesitas: HTML/Tailwind, React/Vue o especificación de props/JSON]`). Ver hipótesis H1: el proyecto ya define su stack, así que no aplica Tailwind/React/Vue.

### Hechos encontrados

**Frontend actual (`panel_admin/`, Angular 21)**
- `panel_admin/src/app/dashboard/dashboard.routes.ts:6-21` — el módulo `dashboard` expone `main` (`MainComponent`) y `dashboard2` (`Dashboard2Component`); `''` redirige a `main`.
- `panel_admin/src/app/dashboard/main/main.component.html:1-754` — el "Dashboard" actual es **contenido demo de la plantilla** con datos inventados en el HTML (New Booking, Customers, Revenue, Traffic Sources, Top 5 Products, Assign Project List, Documents). No consume ningún servicio ni endpoint.
- `panel_admin/src/app/dashboard/main/main.component.ts:1-40` — usa `ng-apexcharts` (`NgApexchartsModule`), `NgScrollbar` y `NgbProgressbar`; las series de las gráficas están hardcodeadas.
- `panel_admin/src/app/dashboard/dashboard2/dashboard2.component.ts:1-60` — segunda pantalla demo con `lineChartOptions`, `pieChartOptions`, `gaugeChartOptions` (útil como referencia de donut/gauge con ApexCharts ya montado).
- `panel_admin/src/assets/data/routes.json:4-5` — el menú tiene una sola entrada `/dashboard/main` ("MENUITEMS.DASHBOARD.TEXT").
- `panel_admin/src/app/authentication/signin/signin.component.ts:50` — tras el login siempre navega a `/dashboard/main`.
- `panel_admin/package.json` — ya instaladas `apexcharts ^5.3.6` / `ng-apexcharts ^2.0.4`, además de `chart.js`/`ng2-charts`, `echarts`/`ngx-echarts`, `@swimlane/ngx-charts`, `bootstrap ^5.3.8`, `@ng-bootstrap/ng-bootstrap`. No hay Tailwind, React ni Vue.
- `panel_admin/src/app/ordenes/proformas/proformas-list.component.html:103-104` y `.ts:50` — acción existente **"Aprobar y generar orden"** (`generateNota(row)`), visible solo si `canGenerateNota` (`authService.hasPermission('add_nota_trabajo')`) y `row.status === 'proforma'`; confirma con `confirmGenerateNota` (`ordenes/proforma-actions.ts:14-20`) y llama a `OrdenesService.generarNotaTrabajo` (`ordenes/ordenes.service.ts`, `POST ordenes/proformas/{id}/generar-nota-trabajo/`). Es el equivalente real del botón "Convertir a Venta" pedido.
- `panel_admin/src/app/ordenes/ordenes.model.ts:27-45` — `AppProforma` (id, name, sucursal_name, car_model/brand_name, car_plate, total_price, discount, total_a_pagar, proforma_created_on, status, nota_trabajo_id) ya trae casi todo lo que necesita la lista "Últimas proformas".
- `panel_admin/src/app/ordenes/ordenes.status.ts` — `statusClass()` y `ORDER_STATUS_OPTIONS` ya mapean los estados a clases de badge (`assets/scss/_ordenes.scss`).
- `panel_admin/src/app/core/models/user.ts` y `core/service/auth.service.ts:71-81` — el usuario guarda `groups` y `permissions` (`hasGroup`, `hasPermission`).

**Backend actual (`praxsa_manager/product/`)**
- `urls.py` — **no existe ningún endpoint de dashboard/estadísticas/agregados**. Los endpoints del panel son CRUD por módulo (`ordenes/proformas`, `ordenes/notas-trabajo`, `ordenes/notas-venta`, `almacen/inventario`, `almacen/bobinas`, catálogos `ordenes/catalogo/*`); todos devuelven listas planas sin paginar (`custom_views/ordenes_admin.py:96-127`).
- `models.py:166-194` — `Proforma_Header`: `total_price`, `discount`, `status` (`proforma/en_trabajo/por_cobrar/finalizado/anulada`, `helper/proforma.py:16-24`), `sucursal`, `car_plate`, `car_model_id`, `is_delete`. `proforma_created_on` es `auto_now=True` (`models.py:170`): se pisa en cada `save()` completo. El servicio de estados evita el problema usando `save(update_fields=[...])` (`business/orden_estado.py:53-56, 252`), pero el campo sigue siendo frágil como "fecha de emisión" histórica.
- `models.py:202-221` — `Nota_trabajo`: `entrada_vehiculo`/`salida_vehiculo` (nullable), `instaladar` (FK `instalador`, nullable), `car_plate`, `car_model`, `nota_venta_created_on` (auto_now_add), `status`. Se crea con `entrada_vehiculo = timezone.now()` (`business/orden_trabajo.py:123`).
- `helper/estados.py:8-13, 16-21` — estados de nota de trabajo: `en_proceso`, `terminado`, `cancelada`; de nota de venta: `por_cobrar`, `pagada`, `anulada`. **No existe el estado "En Espera"** ni un concepto de instalación "programada".
- `models.py:297-314` — `Nota_Venta`: `total_price`, `status`, `created_on` (nullable). `models.py:318-349` — `pago`: `monto`, `created_on` (auto_now_add), `cerrado`.
- `custom_views/ordenes_admin.py:154-183` — `ProformaGenerateNotaView`: requiere `product.add_nota_trabajo`, la proforma debe estar en `proforma`, y delega en `Proforma_Business().create_work_note` (descuenta inventario, crea nota de trabajo y nota de venta por cobrar, `business/orden_estado.py:95-140`). Responde 409 con mensaje legible si falta stock o ancho.
- `models.py:140-154` — `inventario` (bobina en sucursal): `quantity`, `to_install` (metros disponibles), `installed`, `original_length`, `is_active`. `models.py:74-88` — `Window_Film_Reel` (lámina + ancho + largo + precio). **No hay campo de umbral mínimo de stock** (búsqueda de `stock_minimo|min_stock|umbral` sin resultados en `product/`).
- `models.py:62-72` — `Window_Film` solo tiene `name`, `description`, `content`, `image`, `is_active`. **No hay categoría/tipo de lámina** (Cerámica, Seguridad 8mil, Térmico); la búsqueda de `categoria|category` sin resultados.
- `models.py:37-44` — `Car_Part` ("Item": nombre + `is_active`); `Proforma_Detail` (`models.py:248-259`) referencia `car_part`, `window_film`, `width`, `length`, `quantity`. **No existe el concepto "servicio" (Completo / Solo Laterales / Parabrisas)**; solo hay ítems del vehículo por línea de proforma.
- `models.py:269-294` — `Inventario_Movimiento` (`tipo` egreso/devolución, `metros`, `created_on`, FK `inventario` y `proforma_detail`): es la fuente histórica natural de "consumo de metros por lámina en el tiempo" (mergeado por el PR #52, `TASK-mejora-inventario-bobinas`).
- Alcance por sucursal: `business/proforma.py:157-168`, `business/orden_trabajo.py:34-45`, `business/pago.py:14-24` (`get_panel_*_queryset`): admin (grupo `admin`, `helper/user.py:7-10, 28-29`) ve todo; el resto solo sus sucursales habilitadas; sin sucursal, nada. Cualquier agregado del dashboard debe respetar este alcance o filtraría datos de otras sucursales.
- Permisos de los endpoints del panel: `_STANDARD_PERMISSIONS` (`IsAuthenticated + IsStaffUser + DjangoModelPermissions`) o `_STAFF_ONLY` (`custom_views/ordenes_admin.py:44-45`), con `TokenAuthentication`.
- Agregaciones existentes que podrían inspirar/reutilizarse: `admin_config/report_utilidad.py:63-70` (utilidad por lámina con `Sum(Case(When))` sobre notas de venta), `admin_config/report_storage.py:80-84` (`Sum('to_install')` por sucursal/lámina/ancho), `business/inventario.py:164-166` (metros totales por lámina/ancho con precio por sucursal). Son reportes del Django Admin, no API.
- Migraciones: la última es `0114_precio_venta_sucursal_unico.py`.
- Tests: `praxsa_manager/product/tests/` con 25 archivos; hay patrón de tests de alcance (`test_ordenes_scope_permissions.py`, `test_sucursal_scope_admin.py`).

**Correspondencia pedido → dato disponible hoy**
| Widget pedido | ¿Dato existe hoy? | Fuente / brecha |
|---|---|---|
| KPI Ventas del mes + vs. mes previo | Parcial | `Nota_Venta.total_price` + `created_on` (nullable) o `pago.monto`/`created_on`; falta definir qué es "venta" (ver preguntas). |
| KPI Proformas activas (monto sin cerrar) | Sí | `Proforma_Header` con `status='proforma'`, monto `total_price - discount`. |
| KPI Tasa de conversión | Sí (con definición) | Proformas que pasaron a orden / proformas emitidas en el periodo; `proforma_created_on` es frágil (ver arriba). |
| KPI Instalaciones del día | Parcial | `Nota_trabajo` con `entrada_vehiculo` del día y `status`; **no hay "programadas"**. |
| Línea proformas vs. ventas mensual | Parcial | Mismas fuentes que arriba agrupadas por mes. |
| Barras apiladas consumo por categoría | **No** | Consumo sí (`Inventario_Movimiento`, `Detalle_Nota_Trabajo`); **categoría de lámina no existe**. |
| Donut servicios más solicitados | **No** | El "servicio" no está modelado. |
| Stock crítico de rollos con semáforo | Parcial | Metros y rollos disponibles sí (`inventario.to_install`, `quantity`); **no hay umbral de "crítico"**. |
| Cola de instalaciones | Parcial | `Nota_trabajo` (cliente, placa, modelo, instalador, status) + `Detalle_Nota_Trabajo.window_film`; **falta estado "En Espera"**. |
| Últimas proformas + Convertir a Venta | Sí | `GET ordenes/proformas` + `POST .../generar-nota-trabajo/` ya existen con su permiso. |

### Hipótesis / supuestos no confirmados
- **H1**: el entregable correcto es un componente Angular (standalone, `ng-apexcharts`, Bootstrap 5, estilo de la plantilla `panel_admin/`) con un servicio y un contrato JSON, no HTML/Tailwind ni React/Vue; se infiere de que el pedido pide "especificar" el formato y el repo ya fija el stack. No confirmado con el usuario.
- **H2**: "Ventas" probablemente debería medirse con notas de venta **pagadas** (`Nota_Venta.status = 'pagada'`, monto de `pago.monto`) y no con órdenes por cobrar; el criterio no está documentado. No verificado con negocio.
- **H3**: la "categoría" de lámina (Cerámica, Seguridad 8mil, Térmico) probablemente hoy solo existe como convención en el nombre de `Window_Film.name`; no se inspeccionó la base real, así que no se puede afirmar cómo están nombradas.
- **H4**: "servicio" (Completo / Solo Laterales / Parabrisas) podría derivarse de los `Car_Part` de las líneas de la proforma (p. ej. presencia de parabrisas/laterales), pero los nombres de los ítems son datos cargados por el usuario y no se pudo verificar que exista una convención.
- **H5**: probablemente ningún otro cliente consume un endpoint de estadísticas (no existe ninguno); el portal `proforma/` no fue revisado en esta investigación porque el dashboard vive en `panel_admin/`.
- **H6**: el volumen de datos por sucursal es probablemente pequeño (los listados actuales devuelven listas sin paginar), pero no se midió; afecta si conviene agregar en base de datos o en memoria.
- **H7**: el requerimiento asume "técnico asignado" = `Nota_trabajo.instaladar` (modelo `instalador`), no `responsable` (`User`); parece lo correcto por el nombre, no confirmado con negocio.

### Módulos y dependencias relacionadas
- Frontend (`panel_admin/src/app/`): `dashboard/` (pantalla a reemplazar/reestructurar), `ordenes/` (servicio, modelos, estados, acción de aprobar), `almacen/` (`almacen.service.ts`, `almacen.model.ts`: inventario/bobinas), `core/service/auth.service.ts` (permisos), `layout/sidebar` + `assets/data/routes.json` (menú), `assets/scss/_ordenes.scss` (badges de estado).
- Backend: `custom_views/ordenes_admin.py` (patrón de vistas y permisos), `business/proforma.py`, `business/orden_trabajo.py`, `business/pago.py`, `business/inventario.py` (alcance y agregados), `helper/estados.py`, `helper/proforma.py`, `helper/user.py`, `models.py`, `urls.py`, `serializer/ordenes_serializer.py`.
- Documentación aplicable: `docs/frontend/panel_admin/reference.md` (referencia de componentes de la plantilla), `docs/design/DDR-modulo-ordenes-proforma-nota-trabajo-listado-y-flujo-ordenes.md`, `docs/adr/ADR-modulo-ordenes-proforma-nota-trabajo-alcance-permisos.md`, `docs/adr/ADR-estados-proforma-nota-trabajo-nota-venta-maquina-de-estados.md`, `docs/adr/ADR-mejora-inventario-bobinas-asignacion-y-movimientos.md`.

### Implementaciones similares existentes
- **Listados con badge de estado y acciones por permiso**: `ordenes/proformas/proformas-list.component.*` es el patrón a seguir para la tabla de proformas y la acción "Aprobar y generar orden" (confirmación con SweetAlert, manejo de error 409 con `showErrorAlert`).
- **Gráficas**: `dashboard/main/main.component.ts` y `dashboard2.component.ts` ya montan line, stacked bar, donut y gauge con `ng-apexcharts`; sirven como base de configuración visual (colores, `foreColor`, grid).
- **Tarjetas KPI**: `main.component.html:14-106` (`card-statistic-4` con `ngb-progressbar`) y sus clases de plantilla.
- **Alcance por sucursal en el backend**: los tres `get_panel_*_queryset` (proforma, nota de trabajo, nota de venta) son el mecanismo a reutilizar; hay tests de alcance como modelo.
- **Endpoints de catálogo/solo lectura** (`OrdenesSucursalesView`, `OrdenesBobinasView`, `custom_views/ordenes_admin.py:390-423`) son el precedente más cercano de una vista `APIView` de solo lectura para el panel.
- **Agregados de inventario**: `business/inventario.py:164-166` y `admin_config/report_storage.py:80-84`.

### Comportamiento actual
Al iniciar sesión el usuario aterriza en `/dashboard/main`, que muestra datos ficticios de la plantilla sin relación con el negocio (incluye imágenes de `assets/images/banner/*.png` y `products/*.png`). Para ver cifras reales hoy hay que abrir los listados de Ordenes/Almacén o los reportes del Django Admin (`Reporte Utilidades`, `Reporte Inventario`, `Reporte Ventas Diaria`). El flujo real de la orden es: proforma (`proforma`) → "Aprobar y generar orden" crea a la vez nota de trabajo (`en_proceso`, con `entrada_vehiculo=now`) y nota de venta (`por_cobrar`) descontando inventario → "Terminar trabajo" (`terminado`, registra salida) → cobro (`pagada`, proforma `finalizado`); anular devuelve el inventario (`business/orden_estado.py:95-140`, `helper/estados.py`).

### Restricciones
- `docs/CLAUDE.md`: cambios pequeños con un objetivo por PR; dinero con `Decimal`, nunca `float`; todo cambio de lógica de negocio lleva test; no editar migraciones ya aplicadas; **no agregar dependencias sin avisar** (todas las librerías de gráficas necesarias ya están instaladas); antes de cambios en varios archivos proponer un plan y esperar confirmación; no inventar lo que no se pueda verificar.
- El dashboard debe respetar el alcance por sucursal y los permisos del usuario (admin ve todo; resto solo su sucursal); un objeto ajeno responde 404, no 403 (`ordenes_admin.py:1-8`).
- "Convertir a Venta" no es una operación nueva: debe reutilizar la aprobación existente (permiso `add_nota_trabajo`, proforma en `proforma`, transacción con bloqueo y manejo de 409). Duplicar esa lógica rompería la máquina de estados (ADR de estados).
- Las etiquetas de estado de la UI deben coincidir con los estados reales del backend; los pedidos "En Espera / En Proceso / Completado" no coinciden con `en_proceso / terminado / cancelada`.
- `docs/backend-audit.md`, `docs/frontend-audit.md` e `docs/integration-and-backlog.md` existen; no se revisaron a fondo en esta pasada por no haber hallazgo previo sobre dashboard (ver hipótesis H5).

### Riesgos identificados
- **Brechas de modelo de datos** (tabla arriba): categoría de lámina, tipo de servicio, umbral de stock crítico, estado "En Espera"/programación. Cada una implica migración y/o convención de datos nueva, o bien recortar/redefinir el widget.
- **Fecha de proforma frágil**: `proforma_created_on` es `auto_now=True` (`models.py:170`); si algún flujo hace `save()` completo, el histórico mensual y la tasa de conversión se distorsionan. No se auditó cada llamador.
- **Definición de "venta" ambigua**: tres candidatos (`Nota_Venta.created_on` nullable, `pago.created_on`, nota `pagada`) dan cifras distintas para el KPI y la línea.
- **Costo de agregación**: hoy no hay endpoints agregados ni paginación; hacer N llamadas a los listados existentes desde el navegador y agregar en el cliente traería listas completas y rompería el alcance por sucursal si se agrega server-side sin reutilizar los `get_panel_*`.
- **Consistencia de multi-sucursal**: `Sucursal.empleado` M2M; usuarios con varias sucursales (`get_enabled_sucursal_ids`) vs. lógica legada que usa `sucursales[0]`; el dashboard nuevo debe elegir una sola semántica.
- **Estado 'proforma' y anuladas**: "activas", "cerradas", `is_delete`, `is_close` y `anulada` deben excluirse/incluirse de forma consistente en los KPIs (varios flags conviven en `Proforma_Header`).
- **Seguridad**: un endpoint agregado nuevo es superficie de fuga de datos entre sucursales (IDOR/alcance); las ADR ya reportan hallazgos previos de este tipo (`ADR-006-idor-invoice-and-proforma-car-part-info`).
- **Sin tests del área**: no existe cobertura de dashboard; los tests de alcance existentes son de otros endpoints.
- **Datos demo actuales**: `dashboard2` queda huérfano del menú (solo `/dashboard/main` está en `routes.json`); decidir su destino corresponde a etapas posteriores.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — Hay que introducir un contrato de API de agregación nuevo (ningún endpoint lo cubre hoy) con reglas de alcance por sucursal y permisos, y varias piezas del pedido no tienen respaldo en el modelo de datos (categoría de lámina, servicio, umbral de stock, estado "En Espera"), lo que exige decisiones de base de datos y de definición de negocio antes de planificar. Encaja en "cambios importantes de base de datos", "impacto en múltiples módulos" y "nuevo bounded context" de los indicadores de `delivery-architect`.

### Diseño requerido
**SI** — Es una pantalla nueva de alta densidad (4 KPIs, 4 gráficas/tarjetas, tabla y panel lateral) que reemplaza el dashboard demo y debe integrarse con la plantilla `panel_admin/`, los estados/badges existentes y el flujo "Aprobar y generar orden"; requiere decidir jerarquía visual, responsive, estados vacío/cargando/error, semántica de color del semáforo (accesible) y qué hacer con los widgets sin dato.

### Preguntas abiertas para el usuario (a resolver en design/architect/plan)
1. **Formato de entrega**: ¿componente Angular real integrado a `panel_admin/` (recomendado por el stack) o solo maqueta/especificación JSON?
2. **Definición de "venta"** para el KPI y la línea: ¿nota de venta pagada (`pago`), o cualquier orden generada?
3. **Categoría de lámina**: ¿se agrega un campo/catálogo en `Window_Film` (migración) o se agrupa por nombre?
4. **"Servicio"**: ¿se modela (campo en la proforma o derivación desde los ítems `Car_Part`) o se recorta el donut a "ítems más solicitados"?
5. **Stock crítico**: ¿umbral por bobina/lámina (campo nuevo) o regla fija (p. ej. metros restantes y/o % de `original_length`)?
6. **"En Espera" / "Programadas"**: ¿se agrega un estado/fecha programada a la nota de trabajo (toca la máquina de estados) o la cola se limita a los estados actuales (`en_proceso`, `terminado`, `cancelada`)?
7. **Alcance**: ¿el dashboard es por sucursal (con selector para admin) o consolidado?

## Diseño
- [DDR-dashboard-taller-laminas-pantalla-dashboard](../design/DDR-dashboard-taller-laminas-pantalla-dashboard.md) — Estado: Propuesto. Reemplaza el contenido demo de `/dashboard/main` por un componente Angular con `ng-apexcharts` (línea, barras apiladas, donut), 4 KPIs, alerta de stock crítico, cola de taller (tabla Bootstrap, 10 filas) y panel de últimas proformas con "Convertir a venta" (reutiliza `confirmGenerateNota`/`generarNotaTrabajo`). Widgets con variante completa y de respaldo según lo que decida arquitectura (categoría de lámina, servicio, umbral de stock, estado "En espera"). Widgets ocultos por permiso; el frontend no es la barrera de seguridad.

## Arquitectura
Respuestas del usuario que fijan el alcance (2026-09-30): venta = nota de venta pagada; categoría = agrupar por nombre de lámina; servicio = ítems más solicitados; stock crítico = regla fija por metros. Consecuencia: **sin migraciones**.
- [ADR-dashboard-taller-laminas-api-agregados-alcance](../adr/ADR-dashboard-taller-laminas-api-agregados-alcance.md) — Estado: Propuesto. 7 endpoints `GET dashboard/*` de solo lectura (uno por widget), `IsStaffUser` + alcance reutilizando los `get_panel_*` y `get_sucursales_in_scope`, `?sucursal=` ajena → 404, importes string decimal, sin caché ni dependencias. Rollback: revertir el PR.
- [ADR-dashboard-taller-laminas-definiciones-metricas](../adr/ADR-dashboard-taller-laminas-definiciones-metricas.md) — Estado: Propuesto. Fuente exacta de cada métrica (ventas = `pago.monto` de notas pagadas; consumo = `Detalle_Nota_Trabajo` sin canceladas; stock por metros con umbrales provisionales 10/30 m; instalaciones = en taller + terminadas hoy; sin "En espera").
- **Revisión 2026-09-30 (PR #54):** ambos ADR se actualizaron en su propio archivo (sección Actualización, mismo criterio que `ADR-mejora-inventario-bobinas-*`). Cambios: ventas = `Reportes_Business.pagos_cobrados` + `filtrar_pagos` + `Sum('monto')` (equivale a `totales.cobrado` de Ventas Diarias, con prueba de equivalencia); `kpis.ventas` y `proformas-vs-ventas.vendido` van `null` sin `product.view_proxy_pagos` (Admin y Caja, ya asignado por `asignar_permisos_reportes`); no hay permiso ni migración nuevos; el dashboard nunca devuelve costo, utilidad ni margen; los demás widgets siguen en staff + alcance; `sin_sucursal` viaja en `dashboard/kpis`. El DDR se ajustó (ocultar solo lo que llega `null`).
- **Abiertos para el plan / negocio:** confirmar umbrales de stock (provisionales), que una fila de `inventario` = un rollo y que técnico = `instaladar`; verificar en vivo con Admin, Caja y un usuario sin `view_proxy_pagos` que ven/no ven las ventas y que el total coincide con Reportes → Ventas diarias; confirmar que `asignar_permisos_reportes` se ejecutó en cada ambiente; `"En espera"` no se agrega (decisión de arquitectura, revisable).

### Revisión requerida tras integrar master (PR #54, `TASK-reportes-utilidad-ventas-diarias`) — detectada en `delivery-plan` el 2026-09-30
La rama de trabajo de este task está atrás de `origin/master` (`c21814d`). Ese merge trajo `business/reportes.py`, `custom_views/reportes_admin.py`, `permissions.py` y dos métodos de alcance nuevos. Hechos verificados en `origin/master`:
- `praxsa_manager/product/business/reportes.py:1-8` declara el "cálculo único" de ventas cobradas ("ninguna otra parte recalcula estas cifras") y `Reportes_Business.pagos_cobrados()` (`:99-106`) es la definición de venta = pago con nota de venta `pagada` y proforma no borrada, fechada por el pago. El ADR de métricas de este task la recalculaba por separado (punto 1 y 3), lo que duplicaría la regla.
- `praxsa_manager/product/permissions.py:13-20` agrega `TienePermisoReporte` (`has_perm` explícito en `GET`) y `custom_views/reportes_admin.py` exige `product.view_proxy_pagos` para ventas cobradas (Admin y Caja, por decisión del usuario en ese task, `docs/adr/ADR-reportes-utilidad-ventas-diarias-permisos.md`). El ADR de API de este task decidió lo contrario para el dashboard (solo `IsStaffUser` + alcance, sin `view_*`), lo que dejaría ver a cualquier staff, p. ej. un vendedor, el total de ventas cobradas que el negocio restringió.
- Ya existen `Pago_Business.get_panel_pago_queryset` (`business/pago.py`) y `Inventario_Business.get_panel_inventario_queryset` (`business/inventario.py`): el ADR de API proponía un scope de inventario propio con `get_sucursales_in_scope`; hay ahora un método del proyecto que hace lo mismo.
- `panel_admin/src/app/layout/sidebar/sidebar.metadata.ts` ya filtra ítems por `permission` (el DDR asumía que el sidebar no lo hacía) y `assets/data/routes.json` tiene el grupo Reportes nuevo.

**Decisiones que `delivery-architect` debe revisar** (los ADR actuales quedan a reemplazar, no borrar): (1) fuente de "Ventas del mes" y "vendido" del dashboard: reutilizar `Reportes_Business` en vez de recalcular; (2) permiso en servidor de los widgets con ventas cobradas (`view_proxy_pagos`, con 403 o bloque `null` por widget) frente a los de solo proformas/taller; (3) reutilizar `get_panel_pago_queryset` y `get_panel_inventario_queryset`; (4) confirmar que el dashboard no expone costo ni utilidad (Utilidad es solo Admin); (5) si el comando `asignar_permisos_reportes` cubre lo que el dashboard necesita. El DDR necesita solo un ajuste menor (el sidebar ya soporta permisos; los widgets de ventas se ocultan por `view_proxy_pagos`).

## Plan
- [PLAN-2026-09-30-dashboard-taller-laminas](../plans/PLAN-2026-09-30-dashboard-taller-laminas.md) — **v1**. 5 fases: núcleo de cálculo con tests, API (7 `GET dashboard/*`), servicio y modelos Angular, pantalla, verificación en vivo. Sin migraciones ni dependencias nuevas; E2E: NO. Preguntas abiertas (umbrales 10/30 m, fila = rollo, técnico = `instaladar`, selector 6/12 meses, etiqueta del botón, entregable Angular) con valor por defecto.

## Implementación
Implementado el plan v1 (fases 0 a 5) con los valores por defecto de las preguntas abiertas (umbrales 10/30 m, fila de inventario = rollo, técnico = `instaladar`, selector de 6/12 meses, etiqueta "Convertir a venta", entregable Angular).

**Backend** (commit `09ffde5`): `helper/dashboard.py`, `business/dashboard.py`, `serializer/dashboard_serializer.py`, `custom_views/dashboard_admin.py` y 7 rutas en `urls.py`. Sin migraciones (`makemigrations --check` sin cambios). Las ventas reutilizan `Reportes_Business.pagos_cobrados` + `filtrar_pagos` y solo se entregan con `product.view_proxy_pagos`; sin el permiso el bloque va `null`. Tests: `test_dashboard_calculo.py` (25) y `test_dashboard_api.py` (14: acceso, solo lectura, parámetros, alcance, permiso de ventas, sin costos, equivalencia con `reportes/ventas-diarias`, consultas acotadas).

**Frontend** (commit `028a3ad`): `dashboard.model.ts`, `dashboard.service.ts`, `dashboard.charts.ts`, `main.component.{ts,html}` reescrito, `assets/scss/_dashboard.scss` (+ `@use` en `style.scss`), specs del servicio, las gráficas y el componente (27 en verde). "Convertir a venta" reutiliza `confirmGenerateNota` y `OrdenesService.generarNotaTrabajo`.

**Desvíos frente al plan/DDR (a revisar):**
- `angular.json`: se agregó `@angular/localize/init` a los polyfills del target `test` (una línea). Sin eso `ngb-progressbar` no se puede instanciar en tests (`$localize is not defined`); la build ya lo tenía. No estaba en el plan.
- El botón "Convertir a venta" usa `btn btn-sm btn-success` y no `btn-tbl-activate`: esa clase de la plantilla es un botón circular de solo ícono y recortaba el texto.
- Los badges de estado se replicaron en `_dashboard.scss` porque los de `_ordenes.scss` solo aplican dentro de `.orden-view`.
- Selector de período "Últimos 6/12 meses" y selector de sucursal con más de una sucursal en alcance (ya anunciados en el plan).

**Verificación propia (no es el Quality Gate):** `python manage.py test product` → 500 tests OK; `makemigrations --check --dry-run` sin cambios; `ng lint` sin errores; `ng build` compila; `ng test` completo → 290 OK y 14 fallas, **todas** specs "should create" de componentes que no se tocaron (Sidebar, Footer, Page404, Page500, Signup, Blank, AdvanceTable, Dashboard2, First1-3, Second1-2, Third1; faltan providers de router/HTTP). Revisión visual con una API simulada (no con el backend real): desktop 1280 px, móvil 375 px (una columna, sin scroll horizontal, orden stock → cola → proformas → gráficas) y las cuatro tarjetas KPI, líneas, barras, donut, stock, cola y proformas; el tema oscuro de la plantilla **no** se revisó.

**Pendiente de review/usuario:** verificación en vivo con el backend real (Admin, Caja y un usuario sin `view_proxy_pagos`; empleado de una y de dos sucursales; total del mes contra Reportes → Ventas diarias; "Convertir a venta" con éxito y con error de stock); confirmar los umbrales de stock con negocio; ejecutar `asignar_permisos_reportes --dry-run` en cada ambiente.

**Deuda técnica señalada:** las 14 specs "should create" rotas son previas y no se arreglaron (fuera de alcance); `dashboard2` y sus assets de demo siguen sin uso.

**Corrección tras Quality Gate FAIL (2026-09-30):** solo `panel_admin/src/assets/scss/_dashboard.scss`.
- REV-01: bloque `body.dark .dashboard` (cifras de KPI, links, textos secundarios y `btn-link` con colores claros) y el gris secundario base pasa de `#8a93a2` a `#5f6b7d`.
- REV-02: `.dash-convert` con verde `#1e7e34` y texto blanco (contraste 5.1:1 medido en el navegador).
- Verificación propia (no es el Quality Gate): `ng build`, `ng lint` y `ng test` igual que antes (14 fallos previos, 290 OK); medición de contraste en el dashboard real en tema oscuro: 0 textos bajo 4.5:1. Observación sin corregir (fuera de alcance): en tema claro los textos `.text-muted` y links de la plantilla quedan en 2.5–3.8:1; es el estilo global de la plantilla.

**Corrección de REV-03 (a pedido del usuario, antes de publicar):** solo `panel_admin/src/assets/scss/_dashboard.scss`: `.dashboard .text-muted { color: #5f6b7d !important; }` (5.4:1 sobre blanco; el `!important` es necesario porque la plantilla fija el color con él). El bloque `body.dark` sigue ganando en tema oscuro (8.3:1). Verificación propia (no es el Quality Gate): `ng build` OK; `getComputedStyle` sobre el CSS compilado da `rgb(95,107,125)` en claro y `rgb(170,180,200)` en oscuro. Requiere nuevo review para cerrar REV-03 y reconfirmar PASS.

## Review
**Resultado: PASS** (2026-09-30, delivery-review, sobre `1c830f6`). Aislamiento de contexto procedimental: esta revisión corrió en la misma sesión que `delivery-engineer`. Evidencia completa en `## Testing` y `## Review` del [PR #56](https://github.com/rolion/praxsa-django-panel-admin/pull/56). Historial: FAIL sobre `0aec4e4`, PASS con REV-03 abierto sobre `02e9153`, PASS final sobre `1c830f6`.

- Resueltos: [REV-01](../reviews/REV-2026-09-30-dashboard-taller-laminas-01.md), [REV-02](../reviews/REV-2026-09-30-dashboard-taller-laminas-02.md) y [REV-03](../reviews/REV-2026-09-30-dashboard-taller-laminas-03.md). Sin issues abiertos.
- Backend `python manage.py test product`: 500 OK; `makemigrations --check`: sin cambios. Frontend `ng test`: 290 OK / 14 FAILED (los mismos `should create` previos, también en `origin/master`); `ng lint` y `ng build` OK.
- Contraste medido sobre el CSS compilado real y el markup del dashboard en una página de prueba: todos los textos >= 4.5:1 en tema claro y oscuro (mínimo 4.5 en el enlace "Ver mas" del tema claro).
- No verificado: la app con login (se usó la página de prueba), "Convertir a venta" de extremo a extremo, usuario sin permiso de ventas, empleado con dos sucursales, herramientas de lint/seguridad de backend (no instaladas).

## Publicación
_Pendiente_
