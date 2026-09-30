# PLAN-2026-09-30-dashboard-taller-laminas (v1)

**Task:** TASK-dashboard-taller-laminas
**DDRs relacionados:** [DDR-dashboard-taller-laminas-pantalla-dashboard](../design/DDR-dashboard-taller-laminas-pantalla-dashboard.md)
**ADRs relacionados:** [ADR-dashboard-taller-laminas-api-agregados-alcance](../adr/ADR-dashboard-taller-laminas-api-agregados-alcance.md), [ADR-dashboard-taller-laminas-definiciones-metricas](../adr/ADR-dashboard-taller-laminas-definiciones-metricas.md)

## Objective
Reemplazar el dashboard demo de `panel_admin/` (`/dashboard/main`) por un tablero real del taller de láminas: 4 KPIs, gráficas de proformas vs ventas y consumo de lámina, ítems más solicitados, alerta de stock crítico de rollos, cola de taller y últimas proformas con "Convertir a venta". Se sirve con siete endpoints de solo lectura, sin migraciones, y reutiliza el cálculo, el alcance y el permiso de ventas de Reportes.

## Context
Ver `docs/tasks/TASK-dashboard-taller-laminas.md` (investigación, hipótesis, y la revisión tras el PR #54). El usuario resolvió: venta = nota de venta pagada; categoría = por nombre de lámina; servicio = ítems más solicitados; stock = regla fija por metros. La rama parte de `origin/master` (`c21814d`), que ya trae Reportes.

## Current behavior
- `/dashboard/main` es la plantilla demo con datos inventados: `panel_admin/src/app/dashboard/main/main.component.html:1-754`, series hardcodeadas en `main.component.ts`; no consume ningún servicio. Rutas en `dashboard/dashboard.routes.ts:6-21`; menú `assets/data/routes.json:4`; el login redirige ahí (`authentication/signin/signin.component.ts:50`).
- No existe ningún endpoint de agregados del dashboard (`praxsa_manager/product/urls.py`). Los listados del panel devuelven listas completas (`custom_views/ordenes_admin.py:96-127`).
- Reportes (PR #54) ya calcula ventas cobradas: `business/reportes.py:99-130` (`pagos_cobrados`, `filtrar_pagos`), permiso `product.view_proxy_pagos` con `TienePermisoReporte` (`permissions.py:14`), alcance con `get_panel_pago_queryset` (`business/pago.py:26`) y `get_panel_inventario_queryset` (`business/inventario.py:17`), indicador `sin_sucursal` (`custom_views/reportes_admin.py:56`).
- "Convertir a venta" equivale a "Aprobar y generar orden": `POST ordenes/proformas/{id}/generar-nota-trabajo/` (`ordenes_admin.py:154`), acción del listado en `ordenes/proformas/proformas-list.component.ts:113-126` con `confirmGenerateNota` (`ordenes/proforma-actions.ts:14-20`).

## Expected behavior
- Al entrar a `/dashboard/main` se ven los 7 widgets con datos reales del alcance del usuario, cada uno con carga, vacío y error propios (`Reintentar`).
- Quien tiene `view_proxy_pagos` (Admin y Caja) ve Ventas del mes y la serie "vendido"; los demás no reciben ese dato (`null`) y esos elementos se ocultan.
- Ninguna respuesta incluye costo, utilidad ni margen. Una sucursal ajena responde 404; un usuario sin sucursal ve un aviso.
- "Convertir a venta" aparece solo en proformas `proforma` y con permiso `add_nota_trabajo`, reutiliza la confirmación y los errores del listado, y al terminar recarga los widgets.
- El total de ventas del mes coincide con `totales.cobrado` de Ventas diarias para el mismo rango y sucursal.

## Architecture considerations
Resumen de los ADR (no se re-decide):
- **Contrato:** siete `GET` bajo `product/dashboard/` (`kpis`, `proformas-vs-ventas`, `consumo-laminas`, `items-solicitados`, `stock-critico`, `cola-taller`, `proformas-recientes`); importes string decimal, porcentajes string o `null`, meses `YYYY-MM` completos, `null` = sin permiso (distinto de 0), `generado` y `sucursal` en cada respuesta, 400 por parámetros inválidos, 404 por sucursal ajena. Es contrato **nuevo y aditivo**: no rompe nada de Angular; backend y frontend pueden desplegarse juntos sin coordinación especial (el frontend nuevo falla por widget si el backend no está).
- **Permisos y seguridad:** staff + alcance en todo; `product.view_proxy_pagos` solo para lo que muestra ventas cobradas (`kpis.ventas`, `proformas-vs-ventas.vendido`), verificado en la vista con `has_perm`, sin permisos ni comandos nuevos (ya los asigna `asignar_permisos_reportes`). Serializers con campos explícitos, sin costo/utilidad. Es lo único sensible del cambio y lleva prueba de equivalencia con el reporte y verificación en vivo (ver Test strategy).
- **Dinero:** todo `Decimal`; `Sum('monto')` en base de datos; el frontend solo formatea (`bs()` de `reportes/reportes.filtros.ts`).
- **Fechas:** `USE_TZ=False` → `date.today()`/`timezone.now()` naive, nunca `localdate()`; las funciones de negocio reciben `hoy` como parámetro para poder probarlas sin mockear el reloj.
- **Rendimiento:** consultas agregadas con rangos acotados (12 meses, 6/10 filas); sin N+1 (listas con `select_related`/`prefetch_related` o agregación); limpiar el `order_by` heredado antes de `values().annotate()` (notas de venta ordenan `-id`, `business/pago.py:21`). Sin caché hasta medir.
- **Acoplamiento:** el dashboard depende de `Reportes_Business` (`pagos_cobrados`/`filtrar_pagos`); la prueba de equivalencia avisa si ese cálculo cambia.
- **Consistencia visual (DDR):** ApexCharts (ya instalado), tarjetas KPI de la plantilla sin banners, tabla Bootstrap para la cola, badges de `ordenes.status.ts`, `bs()`/`hoyIso()` de `reportes.filtros.ts`. Estilos en `assets/scss/_dashboard.scss` importado desde `style.scss` (patrón de `_ordenes`/`_reportes`, `style.scss:37-38`).

## Proposed solution
Backend: un servicio `Dashboard_Business` que compone los querysets con alcance existentes y produce diccionarios simples; una vista por endpoint que valida parámetros y alcance y serializa con serializers explícitos. Frontend: un `DashboardService` (un método por endpoint), un contenedor `MainComponent` reescrito que carga los 7 widgets en paralelo con un estado `{loading, error, data}` por widget, y funciones puras de configuración de gráficas (`dashboard.charts.ts`) para poder probarlas sin renderizar. La alternativa de un único endpoint, de agregar en el navegador o de recalcular ventas con `calcular_ventas` se descartó en los ADR.

**Ajustes conocidos frente al DDR (a confirmar, ver preguntas):**
1. El selector de período del DDR ("Este mes / Mes anterior / Últimos 12 meses") se reduce a **"Últimos 6 / 12 meses"** para las gráficas y el donut: el ADR no define un parámetro de mes para los KPIs (siempre mes actual y previo). "Mes anterior" para KPIs queda fuera.
2. El selector de sucursal se muestra cuando el usuario tiene **más de una sucursal en alcance** (mismo criterio que Reportes, `reporte-base.ts` `showSucursalSelector`), no solo para admin; coincide con lo que el servidor permite.
3. La visibilidad de widgets por `view_*` del DDR fue reemplazada por "ocultar solo lo que llega `null`" (actualización del DDR).

## Files/components affected

**Backend (`praxsa_manager/product/`)**
- Nuevo `helper/dashboard.py`: constantes (`STOCK_CRITICO_METROS=10`, `STOCK_BAJO_METROS=30`, provisionales; límites de filas y meses; permiso de ventas).
- Nuevo `business/dashboard.py`: `Dashboard_Business` (kpis, serie proformas-vs-ventas, consumo, ítems, stock, cola, recientes).
- Nuevo `serializer/dashboard_serializer.py`: `DashboardParamsSerializer` (`sucursal`, `meses`, `todos`) y serializers de salida con campos explícitos; `ProformaListSerializer` reutilizado para recientes.
- Nuevo `custom_views/dashboard_admin.py`: base `_DashboardView` + 7 vistas.
- Modificado `urls.py`: 7 rutas `dashboard/...`.
- Tests nuevos: `tests/test_dashboard_calculo.py`, `tests/test_dashboard_api.py`, `tests/dashboard_helpers.py` (fábricas para notas de trabajo, proformas con ítems e inventario por lámina; reutiliza `reportes_helpers.create_venta_cobrada`).
- Sin migraciones; no se toca `models.py`, `orden_estado.py` ni la máquina de estados.

**Frontend (`panel_admin/src/app/dashboard/`, `assets/scss/`)**
- Nuevos `dashboard.model.ts`, `dashboard.service.ts`, `dashboard.service.spec.ts`, `dashboard.charts.ts` (+ spec).
- Reescrito `main/main.component.{ts,html,scss}` y su `main.component.spec.ts`.
- Nuevo `assets/scss/_dashboard.scss` + `@use "_dashboard";` en `assets/scss/style.scss`.
- Sin cambios: `dashboard.routes.ts`, `assets/data/routes.json` (Dashboard sigue visible a todo staff), `dashboard2` (queda como está), `OrdenesService`, `proforma-actions.ts` (se reutilizan).

## Implementation steps

**Fase 0 — Preparación (verificable)**
1. Confirmar la rama `task/TASK-dashboard-taller-laminas` sobre `origin/master` y traer cualquier cambio posterior (`sync_with_base_branch` del app si existe; si no, `git merge origin/master`).
2. Entorno local según la memoria del proyecto: copiar `praxsa_manager/.env` del checkout principal al worktree, crear `praxsa_manager/logs/` vacío; instalar dependencias de `panel_admin/` (`npm install`) sin agregar paquetes. Correr la suite backend base (`python manage.py test product`) y `ng test`/`ng lint` en `panel_admin/` para tener una línea base.

**Fase 1 — Núcleo de cálculo (backend, con tests primero)**
3. `helper/dashboard.py` con las constantes.
4. `Dashboard_Business.ventas(user, hoy, sucursal_id)`: mes y mes previo, sobre `Pago_Business.get_panel_pago_queryset(user, Reportes_Business().pagos_cobrados())` + `filtrar_pagos` + `Sum('monto')`; variación `null` si el previo es 0.
5. `proformas_activas`, `conversion` (por cohorte de emisión, excluye `anulada`), `instalaciones` (en taller + terminadas hoy por `salida_vehiculo`), con `get_panel_proforma_queryset` / `get_panel_nota_queryset`.
6. `serie_proformas_vs_ventas(meses)`: `cotizado` por `TruncMonth('proforma_created_on')`, `vendido` con la misma consulta de pagos por `TruncMonth('created_on')`; relleno de meses con 0.
7. `consumo_laminas(meses)`: `Detalle_Nota_Trabajo.length` por lámina y mes de `nota_venta_created_on`, excluye notas `cancelada`, alcance por `get_panel_nota_queryset`; top 6 + "Otras".
8. `items_solicitados(meses)`: líneas de `Proforma_Detail` por `car_part`, proformas en alcance no anuladas; top 5 + "Otros".
9. `stock_critico(todos)`: `get_panel_inventario_queryset` + activos/habilitados, agrupado por sucursal + lámina + ancho, `metros`, `rollos`, estado por umbrales; orden por metros ascendente.
10. `cola_taller` (en proceso + terminadas hoy, máx. 10, láminas de `Detalle_Nota_Trabajo`, técnico `instaladar`) y `proformas_recientes` (6 por `-id`).

**Fase 2 — API (backend)**
11. `DashboardParamsSerializer` y serializers de salida explícitos (sin campos de costo).
12. `_DashboardView` (`TokenAuthentication`, `IsAuthenticated`, `IsStaffUser`), validación de `?sucursal=` contra `get_sucursales_in_scope` (404) y parámetros (400), `sin_sucursal` en `kpis`, verificación de `product.view_proxy_pagos` que deja `ventas`/`vendido` en `null`.
13. Siete vistas + rutas en `urls.py`. Verificar con `makemigrations --check --dry-run` que no hay migración.

**Fase 3 — Frontend: modelo y servicio**
14. `dashboard.model.ts` con los tipos de cada respuesta (importes `string`, `ventas: … | null`); `DashboardService` con un método por endpoint y `?sucursal`/`?meses`; reutiliza `OrdenesService.listSucursales`.

**Fase 4 — Frontend: pantalla**
15. `dashboard.charts.ts`: funciones puras que arman las opciones de ApexCharts (línea con 1 o 2 series según `vendido`, barras apiladas con colores estables por lámina, donut con total central), aptas para tema claro/oscuro.
16. `MainComponent`: barra superior (selector de meses 6/12, selector de sucursal si >1, "Actualizar" y "Actualizado hh:mm"), carga en paralelo con estado por widget, aviso `sin_sucursal`, KPIs con chip ▲/▼ + texto, tarjeta de ventas oculta si `null`, stock crítico con ícono + texto + barra, cola con `statusClass()`, panel de proformas.
17. "Convertir a venta": botón solo si `status === 'proforma'` y `hasPermission('add_nota_trabajo')`; `confirmGenerateNota` → `generarNotaTrabajo` → recarga de widgets; error 409 con `showErrorAlert`/`extractApiError`; botón deshabilitado con spinner en curso.
18. `_dashboard.scss` (grilla, esqueletos, semáforo, responsive: KPIs 2×2 en tablet, una columna en móvil con el stock crítico antes de la cola) y `@use` en `style.scss`. Quitar del `main.component` los imports y assets de la demo que ya no se usen (banners, productos) sin borrar recursos que use `dashboard2`.

**Fase 5 — Verificación**
19. Suite backend completa (`python manage.py test product`), `makemigrations --check --dry-run`, `ng test`, `ng lint`, `ng build` en `panel_admin/`.
20. Verificación en vivo (servidor de desarrollo): Admin, Caja, un usuario sin `view_proxy_pagos`, un empleado de una sucursal y otro de dos; comparar el total del mes con Reportes → Ventas diarias; probar "Convertir a venta" con éxito y con error de stock; revisar tema claro/oscuro y móvil.

## Test strategy

**Backend — unit/integración (Django `TestCase`, patrones de `tests/`)**
- `test_dashboard_calculo.py` (llamando a `Dashboard_Business` con `hoy` fijo y datos con importes conocidos vía `reportes_helpers.create_venta_cobrada` y `helpers`):
  - Ventas del mes: solo pagos con nota de venta `pagada` y proforma no borrada; un pago de otro mes no cuenta; variación vs mes previo, y `null` si el previo es 0; cruce de año (enero → diciembre).
  - Proformas activas: solo `status='proforma'`, no borradas; monto = `total_price − discount`.
  - Conversión: numerador/denominador, exclusión de `anulada`, denominador 0 → `null`.
  - Instalaciones: en proceso cualquier fecha; terminadas hoy por `salida_vehiculo`; una terminada ayer no cuenta; canceladas no cuentan.
  - Serie: 12 meses completos con ceros; `cotizado` excluye anuladas; `vendido` coincide con la suma de pagos.
  - Consumo: suma por lámina y mes; una nota `cancelada` no cuenta; más de 6 láminas → "Otras".
  - Ítems: cuenta por `car_part`; más de 5 → "Otros"; las líneas de metro lineal (sin `car_part`) no cuentan.
  - Stock: límites exactos (9,99 → crítico; 10 → bajo; 29,99 → bajo; 30 → ok), 0 m → crítico, `rollos` cuenta filas con metros > 0, filas inactivas excluidas, `todos` incluye `ok`.
  - Cola: orden (en proceso primero), máximo 10, sin instalador → `null`.
  - Recientes: 6 más recientes, todos los estados.
- `test_dashboard_api.py` (cliente HTTP con Token, como `test_ordenes_scope_permissions.py`, `test_reportes_api.py`):
  - **Alcance:** admin ve todo; empleado solo su sucursal; empleado de dos sucursales ve ambas; sin sucursal → vacío + `sin_sucursal`; `?sucursal=` ajena → 404; `meses`/`sucursal` inválidos → 400; sin token → 401; usuario no staff → 403.
  - **Permisos de ventas:** con `view_proxy_pagos` (Admin/Caja) `ventas` y `vendido` presentes; sin él, `null` y ningún importe de ventas en el JSON (búsqueda en todo el cuerpo); el resto de los widgets sigue respondiendo 200.
  - **Sin costos:** ningún endpoint contiene claves de costo/utilidad/margen.
  - **Equivalencia con el reporte:** `kpis.ventas.mes.total` y la suma de `vendido` del mes igual a `totales.cobrado` de `reportes/ventas-diarias` para el mismo rango y sucursal.
  - **Solo lectura:** `POST/PUT/PATCH/DELETE` a estas rutas → 405.
  - **Sin N+1:** `assertNumQueries` acotado en cola y recientes.
- `makemigrations --check --dry-run` sin cambios.

**Frontend — unit (Angular `TestBed` + `HttpTestingController`, patrón de `proformas-list.component.spec.ts`)**
- `dashboard.service.spec.ts`: URL y parámetros de cada método (`sucursal`, `meses`, `todos`), y que no se envían parámetros vacíos.
- `dashboard.charts.spec.ts`: la línea tiene 1 serie si `vendido` es `null` y 2 si no; el donut y las barras respetan el máximo y "Otras/Otros"; los importes se leen como string sin cálculo en float.
- `main.component.spec.ts`: carga cada widget de forma independiente (uno en error no bloquea a los demás y muestra `Reintentar`); tarjeta de ventas oculta con `ventas: null`; aviso con `sin_sucursal`; selector de sucursal solo con más de una; botón "Convertir a venta" visible solo con `proforma` + `add_nota_trabajo`; al confirmar llama a `generarNotaTrabajo` y recarga; al cancelar la confirmación no llama; un 409 muestra el mensaje del servidor; estados vacíos por widget; indicadores del semáforo con texto además de color.

**E2E (Playwright): NO corresponde.** Es una pantalla de consulta sin un flujo multi-paso nuevo; la única acción de escritura reutiliza una ya cubierta (`ordenes.service.spec.ts`, `proformas-list.component.spec.ts`, `test_orden_flujo_completo.py`). La integración real frontend-backend se valida con los tests de API (contrato) y con la verificación en vivo del paso 20. Además Playwright no está instalado y sumarlo sería una dependencia nueva injustificada para este cambio.

## Acceptance criteria
1. `/dashboard/main` muestra los 4 KPIs, línea proformas vs ventas, barras de consumo por lámina, donut de ítems, alerta de stock crítico, cola de taller y últimas proformas con datos reales; ya no queda contenido demo.
2. Cada widget carga y falla de forma independiente, con esqueleto, vacío y `Reintentar`.
3. Con `view_proxy_pagos` se ven Ventas del mes y la serie "vendido"; sin él el servidor responde `null` y la UI los oculta; ninguna respuesta contiene costo, utilidad ni margen.
4. Ventas del mes y la serie `vendido` coinciden con `totales.cobrado` de Ventas diarias para el mismo rango y sucursal (prueba automática y verificación en vivo).
5. Un empleado solo ve datos de sus sucursales; una sucursal ajena responde 404; un usuario sin sucursal ve el aviso y ceros.
6. "Convertir a venta" solo aparece en proformas `proforma` con permiso `add_nota_trabajo`, reutiliza la confirmación y los mensajes de error del listado, y refresca el tablero.
7. El semáforo de stock usa ícono + texto + color; los umbrales están en una constante de módulo.
8. Importes como `Decimal`/string end to end; sin `float` en el cálculo de dinero.
9. Sin migraciones ni dependencias nuevas; `python manage.py test product`, `ng test`, `ng lint` y `ng build` pasan.
10. Responsive: KPIs 2×2 en tablet y una columna en móvil sin scroll horizontal de página; legible en tema claro y oscuro.

## Risks
- **Sobre-permisividad de ventas** (alguien sin `view_proxy_pagos` ve importes) o **sub-permisividad** (Admin/Caja con `null` porque `asignar_permisos_reportes` no se ejecutó en el ambiente). Mitigación: pruebas de JSON sin importes, prerrequisito operativo con `--dry-run`, verificación en vivo con Admin/Caja/otro rol.
- **Umbrales de stock provisionales** (10 m / 30 m) sin respaldo en el código: pueden dar semáforo engañoso. Mitigación: constante única fácil de cambiar; confirmar con negocio antes de publicar.
- **`proforma_created_on` es `auto_now`** (`models.py:170`): una proforma editada cambia de mes y distorsiona "cotizado" y la conversión. Sin mitigación en este alcance (requeriría migración); se documenta como limitación.
- **Nombres de láminas no normalizados** dan barras poco legibles (sin categoría). Mitigación: top 6 + "Otras".
- **Ruido en stock crítico:** lotes agotados que siguen activos aparecen en rojo. Mitigación: se pueden desactivar en Almacén; `todos=false` por defecto.
- **Contrato con Reportes:** si cambia `Reportes_Business`, el dashboard puede divergir; la prueba de equivalencia lo detecta.
- **Tareas paralelas:** el PR abierto `TASK-filtros-busqueda-reportes` (#55) puede tocar `urls.py` o reportes; conflicto previsible y pequeño; se resuelve integrando master antes de implementar.
- **Tema oscuro:** las gráficas de la demo usan `foreColor` fijo; hay que verificar contraste (paso 20).
- **Sin medición de volumen:** siete llamadas por carga; si resultara lento se evalúa caché (fuera de alcance).

## Out of scope
- Migraciones o campos nuevos: categoría de lámina, servicio (Completo/Solo laterales/Parabrisas), umbral de stock por lámina, estado "En espera"/programación, fecha de emisión inmutable de proforma.
- Costos, utilidad y márgenes en el dashboard.
- Filtro "Mes anterior" para KPIs, polling automático, caché, exportaciones, comparación entre sucursales.
- Retirar `dashboard2` o sus assets; cambios de menú (`routes.json`), del sidebar o de `OrdenesService`.
- Portal `proforma/` (Angular 16).

**Preguntas abiertas para el usuario (con el valor por defecto que se usaría):**
1. ¿Umbrales de stock crítico? Por defecto **crítico < 10 m, bajo < 30 m** (provisionales).
2. ¿Una fila de inventario equivale a un rollo (`rollos` = filas con metros > 0)? Por defecto **sí**.
3. ¿"Técnico asignado" = `instaladar` (el instalador)? Por defecto **sí**.
4. ¿Se acepta que el selector de período sea solo "Últimos 6 / 12 meses" (sin "Mes anterior" para KPIs)? Por defecto **sí**.
5. ¿Etiqueta del botón "Convertir a venta" (con `title` "Aprobar y generar orden")? Por defecto **sí**.
6. ¿Confirmas que el entregable es un componente Angular integrado en `panel_admin/` y no HTML/Tailwind (hipótesis H1)? Por defecto **sí**.

## Dependencias nuevas
Ninguna. Se usan `ng-apexcharts`, `@ng-bootstrap/ng-bootstrap`, `sweetalert2` y `@swimlane/ngx-datatable` ya instalados en `panel_admin/`. No se instala Playwright.
