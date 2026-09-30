# TASK-reportes-utilidad-ventas-diarias: Investigar y mejorar los reportes "Reporte Utilidades" y "Reporte Ventas Diaria" (solo lectura)

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-reportes-utilidad-ventas-diarias
**Pull Request:** https://github.com/rolion/praxsa-django-panel-admin/pull/54

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-09-30 13:04 UTC | (nuevo) → INVESTIGATION | Task creado | delivery-investigate |
| 2026-09-30 | INVESTIGATION (sin cambio de etapa) | Usuario respondió las preguntas abiertas; se registran en "Aclaraciones del usuario". Veredicto sin cambios | delivery-investigate |
| 2026-09-30 | INVESTIGATION (veredicto revisado) | Usuario amplía el alcance: pantallas en panel_admin ahora. NEEDS_PLAN/Diseño NO → NEEDS_ARCHITECTURE/Diseño SI | delivery-investigate |
| 2026-09-30 | DESIGN → ARCHITECTURE | DDR escrito: menú Reportes con Ventas Diarias y Utilidad en panel_admin (filtros de servidor, tarjetas de totales, ngx-datatable). Veredicto NEEDS_ARCHITECTURE | delivery-design |
| 2026-09-30 | ARCHITECTURE → PLANNING | 2 ADR escritos: cálculo único en `business/reportes.py` + API de solo lectura, y permisos (`view_proxy_pagos` Admin/Caja, `view_utilidades` Admin). Decisiones del usuario: instalación aparte de la utilidad; roles indicados | delivery-architect |
| 2026-09-30 | PLANNING (plan v1 escrito) | Plan v1 y PR abiertos; pendiente aprobación humana del plan. Se detectó que la base estaba desactualizada respecto de `origin/master` (#52) y se corrigió la fuente del costo en el ADR | delivery-plan |
| 2026-09-30 | PLANNING → ENGINEERING | Plan aprobado por el usuario al invocar la implementación | delivery-engineer |
| 2026-09-30 | ENGINEERING → REVIEW | Implementación completa (backend + panel_admin); pendiente verificación formal y prueba manual con datos reales | delivery-engineer |

## Investigación

### Requerimiento
"Tenemos unos reportes, reporte de utilidad y ventas diarias, no sé si esto es parte de un flujo de caja chica, investiga y mejóralo, estos son solo de lectura."

Son dos reportes del Django Admin (no del panel Angular): **Reporte Utilidades** (`utilidades`) y **Reporte Ventas Diaria** (`Proxy_Pagos`). El requerimiento no dice qué significa "mejorar" (datos incorrectos, columnas faltantes, rendimiento, usabilidad); esta investigación documenta el estado actual para que `delivery-plan` lo concrete con el usuario.

### Aclaraciones del usuario (2026-09-30)
- **Utilidad = venta − costo de compra** (confirmado).
- Solo cuentan **ventas pagadas**; el reporte debe mostrar las cifras **con y sin descuento** y **distinguir venta con instalación vs. sin instalación** (`Proforma_Header.sales_type`: `venta_instalacion` / `venta_metro_lineal`).
- "Mejorar" = corregir errores, agregar columnas y totales, y que el cálculo refleje la realidad de ventas y utilidad. El usuario no mencionó cerrar el borrado; sigue siendo solo lectura (ver hipótesis sobre `has_delete_permission`).
- **Alcance ampliado:** además de corregir el Django Admin, los reportes se implementan también como pantallas en `panel_admin` (Angular) con endpoints de API de solo lectura, en esta misma tarea.
- Sigue abierto: cómo tratar el costo de instalación dentro de la utilidad (los modelos solo tienen `installation_price`, no un costo de compra de la instalación) y si "sin descuento" significa mostrar bruto y neto lado a lado.

### Hechos encontrados

**Registro y naturaleza (ambos son proxies read-only del Django Admin)**
- `praxsa_manager/product/admin.py:50,52` — `admin.site.register(Proxy_Pagos, ReportDailySellAdmin)` y `admin.site.register(utilidades, ReportUtilidadAdmin)`.
- `praxsa_manager/product/models.py:161-164` — `utilidades` es proxy de `inventario` (verbose_name "Reporte Utilidades"). `models.py:323-327` — `Proxy_Pagos` es proxy de `pago` (verbose_name "Reporte Ventas Diaria", ordering `-id, -created_on`). Migración de `utilidades`: `migrations/0099_utilidades.py`. Última migración del proyecto: `0112_instalador_is_active.py`.
- `admin_config/report_daily_sell.py:148-158` y `admin_config/report_utilidad.py:72-82` — `has_add_permission`/`has_change_permission` devuelven `False` y se elimina la acción `delete_selected`. **Ninguno de los dos sobreescribe `has_delete_permission`.**
- No existe ningún modelo, vista ni pantalla de "caja chica" en el repo: `Grep caja` solo encuentra el grupo/rol `caja` (`helper/user.py`, docs de ADR/TASK). El flujo más cercano a "caja" es el ciclo de cobro: `pago` (`models.py:290-321`) tiene `tipo_pago` (efectivo / tarjeta-QR, `helper/pagos.py:7`), `registro_contable` (único, formato `1234/26`) y `cerrado` (cierre contable). `PagosAdmin` tiene la acción "concluir transaccion" que marca `cerrado=True` (`admin_config/pagos.py:164-172` → `business/orden_estado.py:307-312`); un pago cerrado no se puede anular (`orden_estado.py:294-295`).
- El panel Angular (`panel_admin/src`) no tiene ningún componente/servicio de reportes (Grep sin resultados relevantes); estos reportes solo existen en el Django Admin.

**Reporte Ventas Diaria** (`admin_config/report_daily_sell.py`)
- Una fila por `pago` (`Proxy_Pagos`). Columnas (`:41-51`): id de proforma (enlace a la nota de venta), tipo de venta, nota de trabajo, cliente, vehículo, costo instalación, sub total, descuento, total a pagar. **No muestra `pago.monto`, `tipo_pago`, `registro_contable`, `cerrado` ni el usuario que cobró**; los importes salen de la proforma (`total_price`, `discount`, `:93-105`), no del pago registrado.
- Filtros (`:52-60`): sucursal aparece **dos veces** (`ChoiceDropdownFilter` y `RelatedDropdownFilter` sobre el mismo campo `nota_venta__nota_trabajo__proforma__sucursal`) y un rango de fechas "Pagado en" sobre `created_on` con `default_start=datetime.now()` / `default_end=datetime.now()` — valores evaluados **una vez al importar el módulo**, no por request.
- `get_costo_instalacion` (`:107-113`) usa `functools.reduce(lambda ..., costos)` **sin valor inicial**: con una proforma sin ítems lanza `TypeError` (reduce de secuencia vacía) y rompe el listado completo. No tiene `admin_order_field` (`:114` comentado).
- `get_sub_total.admin_order_field = 'nota_venta__nota_trabajo__proform__total_price'` (`:98`) tiene un typo (`proform__`): ordenar por esa columna lanza `FieldError`. `get_total_pagar` ordena por `total_price` (`:105`), o sea por el subtotal, no por `total_price - discount`.
- No hay fila de totales ni agregados (total del día, por tipo de pago, por sucursal, por tipo de venta). `list_per_page = 10` (`:64`).
- `get_queryset` (`:138-146`) usa `prefetch_related` sobre relaciones uno-a-uno/FK hacia adelante (`nota_venta__nota_trabajo`, `...proforma`) y `select_related` solo para `car_model_id`/`sucursal`; cada fila además dispara `proforma.items.all()` (prefetch de `items` sí está).
- Alcance por sucursal: `Pago_Business.get_pago_queryset_by_role` (`business/pago.py:26-39`) — Admin ve todo; el resto ve solo `sucursales[0]` (la primera sucursal habilitada del usuario), aunque el usuario tenga varias. La API del panel usa en cambio todas las sucursales habilitadas (`business/pago.py:14-24`, `get_enabled_sucursal_ids`).
- Código muerto/confuso: `form = PagosForm` (`:63`) en un admin sin add/change; muchos imports sin uso (`:1-38`); `Forms/daily_sales_form.py:4` importa desde `praxsa_manager.product...` (ruta distinta a la del resto del proyecto) y su import está comentado en `report_daily_sell.py:14`.
- Formato de importes: `f'{total}Bs'` sin espacio (`:96,103,111,118`), distinto de `report_utilidad.py:42` (`" Bs"`).

**Reporte Utilidades** (`admin_config/report_utilidad.py`)
- Una fila por lote de `inventario` (sucursal + bobina + precios de compra/venta por metro lineal, `models.py:140-154`). Columnas (`:28-34`): sucursal, bobina, `precio_compra_mtr_lineal`, `precio_venta_mtr_lineal`, "Utilidad Lamina".
- La "utilidad" (`get_utilidad`, `:41-44`; anotación `sum_film_utilidad`, `:62-69`) es la suma de `window_film_price * length` (venta metro lineal) o `window_film_price * length * quantity` (venta con instalación) sobre los detalles de proforma vinculados al lote y con nota de venta existente. **La fórmula no resta `precio_compra_mtr_lineal`**; y `window_film_price` es el precio de venta por metro del detalle (`sub_total = length * window_film_price * quantity`, `business/proforma.py:87`). Es decir, hoy es venta bruta de lámina, no utilidad.
- El criterio de "vendido" es solo `nota_venta__isnull=False` (`:63`): cuenta ventas **por cobrar** (sin pago) y no toma en cuenta descuentos de la proforma ni el costo de instalación. No hay ningún filtro de fecha (`list_filter`, `:36-39`; sucursal aparece duplicada igual que en Ventas Diaria).
- La rama metro lineal ignora `quantity` mientras la de instalación la multiplica (`:65-68`); el descuento de inventario en `orden_estado.py:103-104` trata `quantity == 0` como "1". **Corrección (delivery-architect):** no es un error; en metro lineal `quantity` es 0 por regla (`business/pricing.py:91-96`).
- Al anular una orden se libera `detalle.inventario = None` (`orden_estado.py:211-219`), por lo que las ventas anuladas dejan de sumarse.
- Alcance por sucursal: `Inventario_Business.get_inventario_queryset_by_role` (`business/inventario.py:14-27`) — igual patrón `sucursales[0]`.
- Al vivir sobre `inventario`, el reporte solo lista lotes con ventas; no hay totales por sucursal ni por lámina.

**Cobertura de pruebas**
- `tests/test_sucursal_scope_admin.py:244-256` (Ventas Diaria) y `:274-291` (Utilidades) solo verifican el filtro por sucursal (`get_queryset`) y el mensaje "Asigne una sucursal" (`:308+`). No hay tests de columnas, cálculos, ordenamiento ni de proformas sin ítems.

### Hipótesis / supuestos no confirmados
- "Caja chica" probablemente se refiere al ciclo cobro → cierre contable (`pago.cerrado`, `registro_contable`, `tipo_pago`), pero no hay un modelo de caja chica ni una definición escrita; el usuario dijo que no está seguro. **Pregunta abierta para el plan.**
- Se asume que "Utilidad Lamina" debía ser margen (venta − compra) y que hoy es un error de fórmula; no está confirmado si el negocio la usa como "venta de lámina". Tampoco se confirmó qué debe entrar en "utilidad" (instalación, descuentos, solo pagadas).
- Se asume que el default `datetime.now()` del rango "Pagado en" queda congelado a la fecha de arranque del servidor; no se ejecutó el admin para comprobar cómo `DateTimeRangeFilterBuilder` interpreta ese default.
- No se verificó (sin ejecutar el admin) que un usuario con permiso `delete_proxy_pagos`/`delete_utilidades` pueda borrar registros entrando por la URL `/delete/`; si fuera así, borrar un `Proxy_Pagos` evitaría `Orden_Estado_Business.anular_pago` (dejaría la nota de venta "pagada" sin pago) y borrar un `utilidades` borraría lotes de inventario. Esto contradice el "solo lectura" pedido.
- No se confirmó si alguien exporta estos reportes (CSV/Excel) o depende de sus columnas actuales; no hay export en el código.
- No se confirmó si en producción existen proformas sin ítems (que harían fallar el reporte de ventas).

### Módulos y dependencias relacionadas
Backend `praxsa_manager/product/`: `admin_config/report_daily_sell.py`, `admin_config/report_utilidad.py`, `admin_config/pagos.py` (admin operativo de pagos), `business/pago.py`, `business/inventario.py`, `business/orden_estado.py` (registrar/anular/cerrar pago), `helper/user.py`, `helper/pagos.py`, `helper/proforma.py`, `models.py` (`pago`, `Proxy_Pagos`, `inventario`, `utilidades`, `Proforma_Detail`), `tests/test_sucursal_scope_admin.py`, `tests/helpers.py`. Frontend Angular: sin relación.

### Implementaciones similares existentes
- `admin_config/report_storage.py` (Reporte Inventario) — expone agregados (`aggregated_result`) en el changelist y aplica el mismo alcance por sucursal (`tests/test_sucursal_scope_admin.py:258-272`); es el precedente de "reporte con totales" en este proyecto.
- `admin_config/pagos.py` — admin operativo de `pago` con cierre contable, filtros de fecha y columnas de `registro_contable`/`tipo_pago` (`:22-27`).
- `admin_config/report_nota_trabajo.py`, `reporte_proforma.py` — otros reportes proxy read-only.

### Comportamiento actual
Ver "Hechos encontrados". En síntesis: Ventas Diaria lista pagos con datos de la proforma (sin datos del cobro ni totales) y puede romperse con proformas sin ítems; Utilidades muestra venta bruta de lámina con la etiqueta "Utilidad" sin restar el costo, sin fecha ni totales.

### Restricciones
- `docs/CLAUDE.md`: antes de cambios que afecten varios archivos, proponer un plan y esperar confirmación (aplica: ≥2 admins + business + tests).
- ADR-002 y su corrección (`docs/adr/ADR-002-filtrado-sucursal-pagos-reportes-admin.md`): solo el grupo `Admin` ve todas las sucursales; el resto queda limitado a su sucursal. Cualquier cambio debe conservarlo (los tests actuales lo cubren).
- Estados: los pagos anulados se borran (`orden_estado.py:300`), por lo que "pagos" ≡ ventas cobradas vigentes; el cierre contable (`cerrado`) no cambia estados (`orden_estado.py:307-312`).
- `docs/tasks/TASK-009.md:63` dejó anotado que ningún reporte se confirmó como dependiente del timing de `cerrado`/`is_close`.

### Riesgos identificados
- Cambiar la fórmula de utilidad cambia cifras que el negocio puede estar usando hoy; falta definición contable.
- Bugs que hacen fallar el listado (proformas sin ítems; ordenamiento por columnas con typo) y que no tienen tests.
- Posible brecha de "solo lectura" por `has_delete_permission` sin restringir (ver hipótesis).
- Alcance por `sucursales[0]` para usuarios con varias sucursales (comportamiento heredado de ADR-002; cambiarlo afecta a los otros admins que comparten el helper).
- El reporte de utilidades se apoya en `inventario`/`Proforma_Detail`; cualquier cambio en el modelo de inventario del módulo almacén (`docs/tasks/TASK-modulo-almacen.md`) lo afecta.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — Con el alcance ampliado (usuario, 2026-09-30) se agregan endpoints de API nuevos para reportes, permisos por rol sobre datos de costo/utilidad, y lógica de cálculo compartida entre Django Admin y API (impacto en varios módulos). Antes del alcance ampliado era NEEDS_PLAN.

### Diseño requerido
**SI** — Hay pantallas nuevas en `panel_admin/` (tablas con filtros de fecha/sucursal/tipo de venta y totales); deben seguir la plantilla (`docs/frontend/panel_admin/reference.md`).

## Diseño
- [DDR-reportes-utilidad-ventas-diarias-pantallas-reportes](../design/DDR-reportes-utilidad-ventas-diarias-pantallas-reportes.md) — Propuesto. Menú "Reportes" (Ventas Diarias, Utilidad) en `panel_admin/`; filtros de servidor (fechas, sucursal, tipo de venta, tipo de pago), tarjetas de totales con y sin descuento, desglose con/sin instalación, tablas `ngx-datatable`. Deja para arquitectura: contrato de API/totales/paginación, permiso por reporte (Utilidad expone costos), reparto del descuento y tratamiento de la instalación en la utilidad, lógica de cálculo única con el Django Admin.

## Arquitectura
- [ADR-reportes-utilidad-ventas-diarias-calculo-y-api](../adr/ADR-reportes-utilidad-ventas-diarias-calculo-y-api.md) — Propuesto. Una sola implementación del cálculo en `business/reportes.py` (nivel venta y nivel línea, sin sumar cabecera sobre ítems unidos), usada por la API (`GET reportes/ventas-diarias`, `GET reportes/utilidad`) y por los dos `ModelAdmin` reescritos. Utilidad = venta lámina − costo de compra; descuento restado íntegro de la utilidad de lámina; instalación aparte; solo ventas cobradas; fecha = fecha del pago; rango máx. 366 días; marca `costo_incompleto` cuando falta el costo de compra.
- [ADR-reportes-utilidad-ventas-diarias-permisos](../adr/ADR-reportes-utilidad-ventas-diarias-permisos.md) — Propuesto. `product.view_proxy_pagos` (Admin, Caja) y `product.view_utilidades` (Admin), verificados en servidor (403), sin campos de costo en Ventas Diarias, alcance por sucursal del panel, comando idempotente `asignar_permisos_reportes` y `has_delete_permission=False` en los admins.
- **Pendientes hacia el plan/diseño:** (1) el DDR no contempló la marca/aviso de `costo_incompleto` (fila y tarjetas); (2) filtrado por permiso del sidebar; (3) verificar los codenames reales de los proxies y los nombres de grupo reales; (4) presentación del detalle por lote/lámina en el Django Admin.

## Plan
- [PLAN-2026-09-30-reportes-utilidad-ventas-diarias](../plans/PLAN-2026-09-30-reportes-utilidad-ventas-diarias.md) — **v1**. 21 pasos en 5 fases (cálculo → alcance/API/permisos → Django Admin → frontend → cierre). Sin E2E (justificado en el plan); sin dependencias nuevas. Ajuste al planificar: la base `origin/master` ya integra #52 (una línea puede consumir varias filas de inventario), por lo que el costo sale de `Inventario_Movimiento` con fallback legado; el ADR de cálculo se actualizó (Actualización 1).

## Implementación
Implementado según el plan v1 (commit `4a658d8` sobre el PR #54). Backend `praxsa_manager/product/` y frontend `panel_admin/`.

**Backend**
- `business/reportes.py` (nuevo): cálculo único. Costo por fila de inventario con movimientos (egresos − devoluciones) y fallback al lote de la línea; `costo_incompleto`; utilidad antes/después de descuento; instalación aparte; desgloses por tipo de venta, tipo de pago y lámina; `calcular_por_lote` para el Django Admin. Número constante de consultas.
- API `GET product/reportes/ventas-diarias` y `reportes/utilidad` (`custom_views/reportes_admin.py`, `serializer/reportes_serializer.py`, `urls.py`): permiso `view_proxy_pagos` / `view_utilidades` (403), alcance por sucursal (404 si es ajena, `sin_sucursal`), rango obligatorio de máx. 366 días. El serializer de Ventas Diarias no tiene campos de costo.
- `permissions.py`: `TienePermisoReporte`. `business/pago.py` y `business/inventario.py`: métodos nuevos de alcance del panel (los legados no se tocaron).
- Django Admin: `report_daily_sell.py` y `report_utilidad.py` reescritos sobre `Reportes_Business`, sin agregar/cambiar/borrar; totales del filtro como mensaje sobre la tabla; el filtro de fecha de Ventas Diaria ahora se calcula por request (hoy) y no al importar.
- Comando `asignar_permisos_reportes` (`--dry-run`, idempotente).

**Frontend**
- Módulo `app/reportes/` (servicio, modelos, base común de filtros, pantallas Ventas Diarias y Utilidad), estilos `_reportes.scss`, ruta `reportes`.
- Sidebar: `permission` opcional por item y `filterByPermission`; grupo "Reportes" en `routes.json`.

**Pruebas escritas (las corrí como verificación propia; la verificación formal es de `delivery-review`)**
- Backend: 58 nuevas (`test_reportes_calculo`, `test_reportes_api`, `test_reportes_admin`, `test_asignar_permisos_reportes`). Suite `product`: 461 tests OK; `makemigrations --check` sin cambios.
- Frontend: 28 nuevas (servicio/filtros, ambas pantallas, `filterByPermission`). `ng lint` y `npm run build` sin errores.
- Comprobación visual con una API falsa local (fixtures, sin tocar ninguna base): Admin ve ambos reportes; Caja ve solo Ventas Diarias y en `/reportes/utilidad` recibe el aviso de sin permiso. **No se hizo la verificación manual con datos reales que pide el plan** (ver más abajo).

**Desvíos del plan (sin cambio de alcance ni de arquitectura)**
- El redondeo a centavos es **por línea** (no por venta): las ventas y los totales son suma de líneas ya redondeadas; sigue cuadrando `bruto − descuento = cobrado`.
- Totales del Django Admin como mensaje (`message_user`) en vez de una plantilla propia.
- "Reporte Utilidades" del Admin solo lista lotes con ventas cobradas.
- El comando aplica los permisos a **todos** los grupos cuyo nombre coincida sin distinguir mayúsculas (en la base de desarrollo existen `Admin` y `admin`, y `Almacen` y `almacen`), a diferencia de `asignar_permisos_estados`, que toma solo el primero.
- Se modificaron dos cosas de tests existentes por cambio de contrato: `create_full_pago_chain` ahora deja la nota de venta `pagada` (un pago existente implica venta cobrada) y `create_inventario` acepta `precio_compra_mtr_lineal`; y `test_reporte_de_utilidades_se_genera` (usaba la anotación `sum_film_utilidad` que ya no existe) se reemplazó por una prueba con flujo real de aprobación, línea repartida en dos lotes (30 + 20 m), pago y cálculo de costo por lote.
- Verificado el paso 2 del plan: los permisos `view_proxy_pagos` y `view_utilidades` existen bajo `product`.

**Deuda técnica / observaciones**
- 15 specs de Angular de la plantilla demo (`should create` de Footer, Dashboard, páginas de ejemplo, `SidebarComponent`, etc.) fallan en la suite completa; no los toqué. Para `SidebarComponent` se comprobó que falla igual sin mis cambios (error de `FeatherModule` sin íconos). Por eso el filtrado del sidebar se prueba solo como función pura (`filterByPermission`), no con el componente montado.
- Sin ordenamiento por columnas calculadas en el Django Admin (las columnas de base de datos sí ordenan).
- Pendiente para el revisor/usuario: verificación manual con ventas reales (comparar cobrado/costo/utilidad a mano con 3-4 ventas: con y sin instalación, con descuento y una con lote repartido) y con usuarios Admin, Caja y Vendedor de dos sucursales; ejecutar `asignar_permisos_reportes --dry-run` y luego el comando real en cada ambiente.

## Review
_Pendiente_

## Publicación
_Pendiente_
