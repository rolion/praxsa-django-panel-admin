# ADR-dashboard-taller-laminas-api-agregados-alcance: Endpoints de solo lectura por widget, con alcance por sucursal y permisos reutilizados de Reportes, y sin migraciones

**Estado:** Propuesto
**Task relacionado:** TASK-dashboard-taller-laminas
**Fecha:** 2026-09-30

## Actualización (2026-09-30, integración con PR #54 — Reportes)

La versión inicial de este ADR (mismo día) decidió `IsStaffUser` + alcance para todos los widgets, un scope de inventario propio con `get_sucursales_in_scope` y "sin flag de sucursal". Tras traer `origin/master` (PR #54, `TASK-reportes-utilidad-ventas-diarias`) se corrige:
- Las **ventas cobradas ya tienen un permiso y un cálculo únicos** (`product.view_proxy_pagos`: Admin y Caja; `Reportes_Business.pagos_cobrados`). El dashboard no puede mostrar esas cifras a cualquier staff ni recalcularlas.
- Ya existen `Pago_Business.get_panel_pago_queryset` y `Inventario_Business.get_panel_inventario_queryset`; el scope propio de inventario deja de proponerse.
- El patrón vigente de las respuestas incluye `sin_sucursal` (los reportes lo devuelven), así que el dashboard lo adopta en lugar de inferirlo desde `ordenes/catalogo/sucursales`.
- Cambian las decisiones 1 (contrato de `kpis` y `proformas-vs-ventas`), 2 (fuentes de alcance), 3 (permisos) y 4 (contrato); las alternativas 4 y 5 se reformulan.

## Contexto

`DDR-dashboard-taller-laminas-pantalla-dashboard` define un tablero con 7 widgets que deben **cargar y fallar de forma independiente** (esqueleto, vacío y error con "Reintentar" por tarjeta) y que muestran datos de varias sucursales según el usuario. La investigación confirmó que hoy no existe ningún endpoint de agregados del dashboard, que los listados del panel devuelven listas completas sin paginar (`custom_views/ordenes_admin.py:96-127`) y que ya hay alcance por sucursal para proformas, notas de trabajo y notas de venta (`business/proforma.py:157-168`, `business/orden_trabajo.py:34-45`, `business/pago.py:14-24`, `ADR-modulo-ordenes-proforma-nota-trabajo-alcance-permisos`).

Hechos de `origin/master` (PR #54, commit `c21814d`) que condicionan la decisión:
- `business/reportes.py:1-8` declara el cálculo único de ventas cobradas y `Reportes_Business.pagos_cobrados()` (`:99-106`) define venta = `pago` con nota de venta `pagada` y proforma no borrada; `filtrar_pagos` (`:117-130`) filtra por fecha local del pago y sucursal. `cobrado = pago.monto`.
- `custom_views/reportes_admin.py` exige staff + `TienePermisoReporte` (`permissions.py:13-20`, `has_perm` explícito en `GET`) con `product.view_proxy_pagos` para Ventas Diarias (Admin y Caja) y `product.view_utilidades` para Utilidad (solo Admin, muestra costos), según `ADR-reportes-utilidad-ventas-diarias-permisos`. El alcance se aplica siempre en servidor: sucursal ajena → 404; sin sucursal → respuesta vacía con `sin_sucursal`.
- `Pago_Business.get_panel_pago_queryset` (`business/pago.py`) e `Inventario_Business.get_panel_inventario_queryset` (`business/inventario.py`) usan todas las sucursales habilitadas del usuario (sin `sucursales[0]`).
- El comando `asignar_permisos_reportes` (`management/commands/`) ya asigna `view_proxy_pagos` a Admin y Caja.

Restricciones vigentes:
- El usuario descartó los cambios de modelo: **sin migraciones**.
- `settings.py:189-193`: `TIME_ZONE='America/La_Paz'` con `USE_TZ=False` (fechas naive locales).
- Todo importe es `Decimal` y se serializa como string.

## Decisión

1. **Siete endpoints `GET` de solo lectura bajo `product/dashboard/`, uno por unidad de carga del DDR**, en `custom_views/dashboard_admin.py` (`APIView`, `TokenAuthentication`, `IsAuthenticated` + `IsStaffUser`, mismo patrón que `_ReporteView`) y la lógica en `business/dashboard.py`. Ninguno escribe.

   | Endpoint | Alimenta | Contenido |
   |---|---|---|
   | `dashboard/kpis` | 4 tarjetas KPI | `ventas` (mes y mes previo, **o `null` sin permiso**), proformas activas (monto y cantidad), conversión (numerador/denominador/porcentaje), instalaciones (en taller, terminadas hoy), `sin_sucursal` |
   | `dashboard/proformas-vs-ventas` | línea | serie mensual `cotizado` y `vendido` (**`vendido: null` sin permiso**), `?meses=` (1–12, defecto 12), meses rellenados con 0 |
   | `dashboard/consumo-laminas` | barras apiladas | metros por mes y lámina; máx. 6 láminas + "Otras" |
   | `dashboard/items-solicitados` | donut | conteo por ítem, máx. 5 + "Otros", `?meses=` |
   | `dashboard/stock-critico` | alerta | grupos sucursal + lámina + ancho con metros, rollos y estado `ok/bajo/critico`, contadores, `?todos=` |
   | `dashboard/cola-taller` | tabla | hasta 10 notas de trabajo |
   | `dashboard/proformas-recientes` | panel lateral | 6 proformas con `ProformaListSerializer` (tipo `AppProforma` del frontend) |

2. **Alcance por sucursal: solo métodos ya existentes del proyecto.**
   - Proformas, notas de trabajo y notas de venta: `get_panel_proforma_queryset`, `get_panel_nota_queryset`, `get_panel_nota_venta_queryset`.
   - **Ventas cobradas:** `Pago_Business.get_panel_pago_queryset(user, Reportes_Business().pagos_cobrados())` y luego `Reportes_Business.filtrar_pagos(...)` para el rango y la sucursal, con `Sum('monto')` (y `TruncMonth('created_on')` para la serie, limpiando el `order_by` heredado). **No** se usa `calcular_ventas`/`resumir`: calculan líneas y costos que el dashboard no necesita y no debe tocar; `cobrado = pago.monto` por definición, así que las cifras coinciden con `totales.cobrado` de Ventas Diarias para el mismo rango y sucursal.
   - Inventario: `Inventario_Business.get_panel_inventario_queryset` más `is_active`, bobina activa y sucursal habilitada.
   - `?sucursal=<id>` opcional: se valida contra `User_Helper().get_sucursales_in_scope(user)` como en `_ventas` de los reportes; fuera de alcance → **404**. Parámetros inválidos (`meses` fuera de 1–12, `sucursal` no entera) → **400** con un serializer de parámetros (mismo patrón que `ReporteParamsSerializer`). Sin `sucursal`: consolidado del alcance del usuario.
   - `sin_sucursal` (solo en `kpis`) = usuario no admin sin sucursal habilitada asignada (`not can_view_all_sucursales and not has_assigned_sucursal`, igual que los reportes); en ese caso todos los agregados salen vacíos/ceros.

3. **Permisos en servidor.**
   - Todo endpoint: staff autenticado + alcance (un `Client` del portal no entra).
   - **Solo lo que muestra ventas cobradas** (`kpis.ventas` y `proformas-vs-ventas.vendido`) exige `product.view_proxy_pagos` (el mismo permiso de Ventas Diarias: Admin y Caja hoy). Sin ese permiso el servidor **no devuelve el dato**: responde `200` con el bloque en `null` (no `0`, para distinguir "sin acceso" de "sin ventas"). Se verifica con `request.user.has_perm('product.view_proxy_pagos')` dentro de la vista, no con un permiso nuevo ni con nombre de grupo.
   - **No se crea ningún permiso, migración ni comando de asignación**: la asignación ya la hace `asignar_permisos_reportes`. Prerrequisito operativo: ese comando debe haberse ejecutado en cada ambiente; si no, Admin y Caja verían `ventas: null`.
   - El dashboard **nunca devuelve costos, utilidad ni margen** (`view_utilidades` no interviene): los serializers declaran campos explícitos y no comparten serializers con Utilidad.
   - Proformas activas, conversión, cola de taller, proformas recientes, consumo, ítems y stock: mismo criterio que los listados equivalentes (staff + alcance, `GET` sin `view_*`, `ADR-agrupacion-menu-...`). No se agrega permiso de servidor a esos widgets.
   - **Frontend (solo UX):** la tarjeta y la serie de ventas se ocultan cuando el servidor devuelve `null`; los demás widgets se muestran a todo staff. Esto **reemplaza** del DDR la regla "ocultar cada widget por su permiso `view_*`": el servidor no los exige y los grupos pueden no tenerlos, con lo que se ocultarían datos que el backend sí sirve.
   - "Convertir a venta" no cambia: `POST ordenes/proformas/{id}/generar-nota-trabajo/` con `add_nota_trabajo` y su máquina de estados. El dashboard no escribe.

4. **Contrato de datos.**
   - Importes: string decimal con 2 decimales; porcentajes: string con 1 decimal o `null` si el denominador es 0. El frontend solo formatea.
   - `null` en `ventas`/`vendido` significa **sin permiso**; una lista vacía o ceros significa sin datos.
   - Cada respuesta incluye `generado` (fecha-hora local) y `sucursal` (id o `null`).
   - Meses `YYYY-MM` ascendentes, completos hasta el mes actual.
   - Fechas del día y de mes con `timezone.now()` naive / `date.today()`, no `timezone.localdate()`/`localtime()` (fallan con `USE_TZ=False`); rangos de pagos con `desde`/`hasta` de fecha local como `filtrar_pagos`.
   - Al agrupar sobre los querysets con `order_by` heredado (p. ej. `-id` en notas de venta) se limpia el orden antes de `values()/annotate()`.

5. **Sin migraciones, sin caché, sin dependencias nuevas.** Rangos acotados (12 meses; 6/10 filas). Umbrales de stock en constante de módulo (`helper/dashboard.py`), no en `.env` ni en base.

6. **Pruebas obligatorias**, con los helpers existentes (`tests/helpers.py`, `ordenes_helpers.py`, `reportes_helpers.py`): por endpoint, alcance (admin todo; empleado su sucursal; sin sucursal → vacío + `sin_sucursal`; `?sucursal=` ajena → 404; parámetros inválidos → 400; no-staff → 401/403); permisos de ventas (Admin y Caja ven `ventas`; un usuario staff sin `view_proxy_pagos` recibe `null` y ningún importe de ventas en el JSON; ningún campo de costo/utilidad en ninguna respuesta); **equivalencia**: `kpis.ventas` del mes y la serie `vendido` coinciden con `totales.cobrado` del endpoint `reportes/ventas-diarias` para el mismo rango y sucursal; rellenado de meses; ningún endpoint escribe.

## Alternativas consideradas

1. **Un único `GET dashboard/resumen`.** Rompe el requisito de fallo independiente por widget y mezcla datos con permisos distintos en una sola respuesta. Se descarta.
2. **Agregar en el navegador con los listados existentes.** Descarga PII para calcular cuatro números, no da consumo ni stock agrupado y mueve reglas de dinero al cliente (contradice `docs/CLAUDE.md`). Se descarta.
3. **Materializar o cachear resúmenes.** Sobreingeniería sin volumen medido (hipótesis H6 del TASK). Se pospone.
4. **Ventas: reutilizar `calcular_ventas`/`resumir` (totales del reporte).** Garantiza igualdad con el reporte, pero calcula líneas, movimientos y costos de compra por cada venta del rango (más consultas) y mete en el camino del dashboard datos de costo restringidos a Admin. Se descarta a favor de `pagos_cobrados` + `filtrar_pagos` + `Sum('monto')`, que produce el mismo `cobrado` y se protege con una prueba de equivalencia.
5. **Ventas: `403` para todo el endpoint si falta `view_proxy_pagos`, o endpoint separado de ventas.** El `403` rompería `kpis` y la línea para quien solo debe ver el resto; un endpoint aparte sumaría uno más sin ganancia. Se elige el bloque `null` por respuesta.
6. **Exigir `view_*` en servidor para todos los widgets.** Añade una barrera distinta de la de los listados que exponen los mismos datos y puede dejar sin datos a roles sin esos permisos asignados. Se descarta; solo se gatilla lo que el negocio ya restringió (ventas cobradas).
7. **Permiso nuevo `ver_dashboard` o decidir por nombre de grupo.** Contradice el patrón de permisos estándar sin permisos custom ni roles hardcodeados de `ADR-...-reportes-...-permisos`. Se descarta.

## Estrategia de rollback / mitigación

Cambio aditivo y de solo lectura: siete rutas nuevas, un módulo de vista y uno de negocio, sin migración ni cambio de modelos, permisos o autenticación existentes. **Toca autorización** (decide quién ve ventas cobradas en un lugar nuevo), por eso:
- Rollback: revertir el PR devuelve `/dashboard/main` al contenido demo sin datos que reparar; no hay flag. Los permisos siguen siendo los de los reportes y no cambian.
- Riesgos: **sobre-permisividad** (alguien sin `view_proxy_pagos` recibe importes de ventas) y **sub-permisividad** (Admin/Caja con `null` por no haberse asignado el permiso en el ambiente).
- Mitigación: las pruebas del punto 6 (en especial el JSON sin importes cuando falta el permiso y la equivalencia con el reporte); verificación manual en vivo, antes de publicar, con un Admin, un Caja, un vendedor sin `view_proxy_pagos` y un empleado de una sola sucursal frente a uno de dos, comparando el total del mes con la pantalla Reportes → Ventas diarias; ejecutar `asignar_permisos_reportes --dry-run` en cada ambiente como paso previo.
- Cada widget falla aislado: un endpoint defectuoso se apaga quitando su tarjeta sin afectar el resto.

## Consecuencias

- **Más fácil:** una sola definición de venta cobrada y un solo permiso para verla; cada widget es probable por separado; alcance sin lógica nueva; el frontend reutiliza `AppProforma`.
- **Más difícil:** siete llamadas al cargar (en paralelo desde el frontend); la prueba de equivalencia con el reporte acopla el dashboard a `Reportes_Business` (si ese cálculo cambia, la prueba avisa).
- **Deuda aceptada:** el resto de widgets no pide `view_*` en servidor (misma regla que los listados); el DDR debe ajustarse (ocultar solo por `null`); sin paginación ni caché hasta medir.
