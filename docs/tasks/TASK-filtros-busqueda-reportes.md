# TASK-filtros-busqueda-reportes: Filtros de búsqueda en reportes Proforma, Nota Trabajo y Nota Venta

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** SI
**Rama:** `task/TASK-filtros-busqueda-reportes`
**Pull Request:** https://github.com/rolion/praxsa-django-panel-admin/pull/55

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-09-30 | (nuevo) → INVESTIGATION | Task creado | delivery-investigate |
| 2026-09-30 | INVESTIGATION → INVESTIGATION | Aclaraciones del solicitante incorporadas | delivery-investigate |
| 2026-09-30 | INVESTIGATION → PLANNING | Plan v1 escrito y PR abierto | delivery-plan |
| 2026-09-30 | PLANNING → ENGINEERING | Plan listo para implementar (pendiente de aprobación humana) | delivery-plan |
| 2026-09-30 | ENGINEERING → REVIEW | Implementación completa según plan v1 | delivery-engineer |
| 2026-09-30 | REVIEW → DESIGN | DESIGN_REVIEW_REQUIRED: el solicitante indica que las pantallas objetivo son las listas del panel Angular (Órdenes), no el Django Admin | delivery-engineer |
| 2026-09-30 | DESIGN → PLANNING | DDR de filtros en listados del panel Angular emitido; veredicto NEEDS_PLAN se mantiene (plan v2 requerido) | delivery-design |
| 2026-09-30 | PLANNING → PLANNING | Plan v2: agrega Fase 2 (panel Angular) tras DESIGN_REVIEW_REQUIRED | delivery-plan |
| 2026-09-30 | PLANNING → ENGINEERING | Plan v2 listo para implementar (pendiente de aprobación humana) | delivery-plan |
| 2026-09-30 | ENGINEERING → REVIEW | Fase 2 (panel Angular) implementada según plan v2 | delivery-engineer |
| 2026-09-30 | REVIEW → PUBLISH | Quality Gate PASS (2 observaciones Low abiertas; verificación manual en navegador pendiente) | delivery-review |

## Investigación

### Requerimiento
> necesitamos agregar filtros de busqueda en los reportes
>
> en proforma necesitamos: filtros sucursal (solo los que tiene disponible el usuario), marca, modelo, rango de fecha, estado
> en nota trabajo necesitamos: filtros sucursal (solo los que tiene disponible el usuario), marca, modelo, instalador, estado, cobro
> en nota de venta: filtros sucursal (solo los que tiene disponible el usuario), rango de fecha, trabajo, cobro

### Aclaraciones del solicitante (2026-09-30)
- **Nota de venta** = la pantalla `NotaVentaAdmin` (lista las notas de venta y su estado de pago), no un reporte. "Ventas Diaria" es otra vista y **no debe ser afectada** por este cambio.
- **Cobro** = estado de la nota de venta (`Nota_Venta.status`: por cobrar / pagada / anulada, `helper/estados.py:20-24`), no el tipo de pago. Solo aplica a la pantalla de Nota de Venta.
- **Trabajo** (en nota de venta): el solicitante se refiere a la tabla Nota Trabajo (`Nota_trabajo`, la nota asociada vía `Nota_Venta.nota_trabajo`); falta precisar si el filtro es por su estado (en proceso / terminado / cancelada) o por número.
- **Estado en Nota Trabajo**: el reporte debe permitir los tres estados (en proceso, terminado, cancelada, `helper/estados.py:10-14`). Hecho verificado: `get_finish_nota_queryset` solo lo usa `ReportNotaTrabajoAdmin` (`report_nota_trabajo.py:103`) y sus tests (`tests/test_sucursal_scope_admin.py:175-210`), y hoy fuerza `status=NT_TERMINADO` (`business/orden_trabajo.py:50`); habrá que quitar/relajar ese filtro para ese reporte y actualizar esos tests.

### Hechos encontrados

**Dónde viven hoy los "reportes"**
- Los reportes de Proforma y Nota Trabajo son admins de Django de solo consulta sobre modelos proxy: `Proxy_Proforma` ("Reporte Proforma", `praxsa_manager/product/models.py:196-200`) y `Proxy_Nota_trabajo` ("Reporte Nota Trabajo", `models.py:240-244`), registrados en `praxsa_manager/product/admin.py:47-48` con `ReportNotaTrabajoAdmin` y `ReportProformaAdmin`.
- No existe un reporte de "Nota de Venta" propiamente dicho: no hay `Proxy_Nota_venta` (`models.py:297-320` solo define `Nota_Venta`). Lo más cercano son (a) `NotaVentaAdmin`, la pantalla operativa registrada en `admin.py:56` (`praxsa_manager/product/admin_config/nota_venta.py:26-`), que **no tiene `list_filter`** (solo `search_fields`, línea 37), y (b) "Reporte Ventas Diaria" (`Proxy_Pagos`, `models.py:351-355`, `ReportDailySellAdmin`, `admin.py:50`), que lista pagos (cada pago cuelga de una `Nota_Venta`, `models.py:322-330`).
- El menú "Reportes" del panel Angular solo tiene dos rutas, `ventas-diarias` y `utilidad` (`panel_admin/src/app/reportes/reportes.routes.ts:5-8`); no hay pantallas Angular de reporte de Proforma / Nota Trabajo / Nota Venta. Las listas Angular de Órdenes (`panel_admin/src/app/ordenes/proformas/proformas-list.component.ts:64-110`, `notas-trabajo/`, `notas-venta/`) filtran en el cliente (búsqueda de texto + estado en proformas, `ordenes.service.ts:35-46`, `93-95`, `119-127`); no son "reportes".

**`ReportProformaAdmin`** (`admin_config/reporte_proforma.py`)
- `list_filter` actual (líneas 35-42): `sales_type` (ChoiceDropdown), `sucursal` (`RelatedDropdownFilter`), `proforma_created_on` (rango fecha-hora con default "hoy"). Faltan marca, modelo y estado.
- `RelatedDropdownFilter` sobre `sucursal` lista todas las sucursales existentes, no solo las del usuario (comportamiento estándar del filtro; el queryset restringe filas, no las opciones). Ver hipótesis.
- El queryset lo arma `Proforma_Business.get_proforma_queryset_by_role` (`business/proforma.py:136-155`): Admin (chequeo inline del string `'Admin'`) ve todo; el resto solo `sucursales[0]` (una sola sucursal aunque tenga varias); sin sucursal → `None` y mensaje "Asigne una sucursal al usuario" (`reporte_proforma.py:87-92`). Ya hace `select_related` de `car_model_id__car_brand_id`.
- Campos disponibles: `Proforma_Header.car_model_id` → `Car_Model.car_brand_id` (`models.py:26-29`, `166-195`), `status` con opciones proforma/en_trabajo/por_cobrar/finalizado/anulada (`helper/proforma.py:16-22`).
- `proforma_created_on` es `auto_now=True` (`models.py:169`): se sobrescribe en cada `save()`, así que el "rango de fecha" filtra por última modificación, no por creación.
- `search_fields` incluye `'sales_type'` y `'proforma_created_on'` (línea 43), campos poco útiles para búsqueda de texto (estado actual, sin cambios).

**`ReportNotaTrabajoAdmin`** (`admin_config/report_nota_trabajo.py`)
- `list_filter` actual (líneas 36-45): `proforma__sales_type`, `entrada_vehiculo` (rango con default 2020–2030), `proforma__sucursal` (`RelatedDropdownFilter`). Faltan marca, modelo, instalador, estado y cobro.
- El queryset viene de `Orden_Trabajo_Business.get_finish_nota_queryset` (`business/orden_trabajo.py:47-62`), que **fuerza `status=NT_TERMINADO` y `proforma__is_delete=False`** (línea 50). Con eso, un filtro de "estado" de nota de trabajo (`NT_STATUS_CHOICES`: en_proceso / terminado / cancelada, `helper/estados.py:10-14`) solo podría devolver "terminado". Además usa `sucursales[0]` para usuarios no-Admin (línea 56).
- Campos: `Nota_trabajo.instaladar` (FK a `instalador`, `models.py:210`), `car_model` (FK a `Car_Model`, `models.py:213`), `status` (`models.py:215`). `instalador.sucursal` es M2M a Sucursal (`models.py:134`).
- "Cobro" no es un campo de `Nota_trabajo`: se alcanzaría vía `Nota_Venta` (`nota_trabajo` es OneToOne inverso, `models.py:298`) → `Nota_Venta.status` (`por_cobrar`/`pagada`/`anulada`, `helper/estados.py:20-24`) y/o `pago` (`models.py:322-345`, `tipo_pago` efec/trans `helper/pagos.py:7`).
- Bug visible: `get_nota_trabajo_id` muestra `obj.proforma.id` como texto del link de la nota de trabajo (línea 92); no es parte del pedido.

**Reporte de Nota Venta / Ventas Diaria**
- `ReportDailySellAdmin` (`admin_config/report_daily_sell.py:38-44`) ya tiene filtros: `created_on` (rango, default hoy), sucursal (`RelatedDropdownFilter` sobre `nota_venta__nota_trabajo__proforma__sucursal`), `sales_type` (etiqueta "Tipo Venta", que es el "tipo de trabajo" venta con instalación / metro lineal, `helper/proforma.py:26-27`) y `tipo_pago`. Su queryset solo incluye pagos cobrados (`Reportes_Business.pagos_cobrados`, línea 96) y está acotado por sucursal vía `Pago_Business.get_panel_pago_queryset` (línea 104), con una lógica de alcance distinta a la de los otros dos reportes (`User_Helper.can_view_all_sucursales`/`has_assigned_sucursal`, líneas 99-101).
- `NotaVentaAdmin.get_queryset` (`nota_venta.py:110-116`) usa `get_nota_venta_queryset_by_role` (`business/proforma.py:170-183`): **no tiene atajo Admin** (filtra siempre por `sucursales[0]`; un Admin sin sucursal recibe `None`), bug ya conocido y declarado fuera de alcance en `docs/adr/ADR-002-filtrado-sucursal-pagos-reportes-admin.md`. Además ante `None` hace `qs.filter(sucursal = -1)` (línea 115), campo que `Nota_Venta` no tiene (sería `FieldError` en runtime).
- `Nota_Venta` tiene `created_on` (`models.py:307`, nullable) y `status` (`models.py:308`).

**Infraestructura de filtros disponible**
- Ya se usan `django_admin_listfilter_dropdown` (`RelatedDropdownFilter`, `ChoiceDropdownFilter`) y `rangefilter` (`DateTimeRangeFilterBuilder`, `DateTimeRangeFilter`), `django-admin-rangefilter==0.12.4` en `requirements-3.8.10.txt:9`, Django 4.2.1 (`requirements-3.8.10.txt:6`).
- `ReportDailySellAdmin` ya tiene el patrón de default de rango dinámico por request (`get_rangefilter_created_on_default`, líneas 50-52), mientras `ReportProformaAdmin`/`ReportNotaTrabajoAdmin` calculan `datetime.now()` una sola vez al importar el módulo (definición de clase, `reporte_proforma.py:38-41`), por lo que el "hoy" por defecto de Proforma queda congelado al día en que arrancó el servidor.
- Precedente de tests de alcance por sucursal para estos admins: `praxsa_manager/product/tests/test_sucursal_scope_admin.py:293-305` (`test_report_nota_trabajo_admin_filtra_por_sucursal`).
- Última migración: `0114_precio_venta_sucursal_unico.py`. Las tareas descritas no requieren cambios de modelo.

### Hipótesis / supuestos no confirmados
- **"Trabajo" en nota de venta**: aclarado que se refiere a Nota Trabajo, pero sigue sin definirse si se filtra por su estado o por número (pregunta abierta para `delivery-plan`; por defecto, estado).
- **"Solo los que tiene disponible el usuario"**: se asume que aplica a las opciones del desplegable (no solo a las filas), y que un Admin ve todas las sucursales habilitadas; no se verificó cómo se comporta `RelatedDropdownFilter` en la versión instalada (posiblemente lista todas las sucursales por defecto salvo que el `ModelAdmin` restrinja `limit_choices_to`/el queryset del filtro).
- **"Modelo" y "marca"**: se asume que el filtro de modelo debería depender de la marca elegida (o listar todos); no definido.
- "Cobro" en Nota Trabajo (aparece en el pedido) se supone también estado de la nota de venta asociada; no confirmado.
- Se supone que el alcance es solo el Django Admin (donde existen estos reportes hoy) y no una pantalla nueva del panel Angular; el pedido no menciona el panel Angular.

### Módulos y dependencias relacionadas
- Backend `praxsa_manager/product/`: `admin_config/reporte_proforma.py`, `report_nota_trabajo.py`, `report_daily_sell.py`, `nota_venta.py`; `business/proforma.py`, `business/orden_trabajo.py`, `business/pago.py`, `business/reportes.py`; `helper/user.py` (alcance por sucursal), `helper/estados.py`, `helper/proforma.py`; `models.py`.
- Sin impacto aparente en `custom_views/`, `serializer/` ni en el frontend Angular (`proforma/`, `panel_admin/`), salvo que se decida ampliar el alcance.

### Implementaciones similares existentes
- `ReportDailySellAdmin.list_filter` (`report_daily_sell.py:38-44`) combina sucursal, tipo de venta, tipo de pago y rango con default dinámico: patrón a seguir.
- `django_admin_listfilter_dropdown` ya provee `RelatedDropdownFilter`/`ChoiceDropdownFilter` para FK/choices, usados en los tres reportes.
- `User_Helper.get_sucursales_in_scope` (`helper/user.py:41-47`) ya devuelve las sucursales habilitadas visibles para el usuario (todas para Admin, las suyas para el resto): base natural para "solo las que tiene disponible el usuario".

### Comportamiento actual
- Reporte Proforma: filtros tipo de venta, sucursal (todas las opciones) y fecha; lista acotada a la sucursal del usuario (primera), Admin todo. Sin marca, modelo ni estado.
- Reporte Nota Trabajo: filtros tipo de venta, fecha de entrada y sucursal; solo notas terminadas; sin marca, modelo, instalador, estado ni cobro.
- Ventas Diaria: fecha, sucursal, tipo de venta y tipo de pago; solo pagos cobrados.
- `NotaVentaAdmin`: sin filtros laterales.

### Restricciones
- `docs/CLAUDE.md`: cambios pequeños, un objetivo por cambio; el proyecto tiene deuda técnica conocida, no asumir buenas prácticas.
- ADR-002 (`docs/adr/ADR-002-filtrado-sucursal-pagos-reportes-admin.md`): solo el grupo `Admin` ve todas las sucursales (`User_Helper.can_view_all_sucursales`); el bug "Admin sin sucursal ve lista vacía" en `NotaVentaAdmin` quedó explícitamente fuera de alcance de ese cambio.
- ADR/DDR de reportes de utilidad y ventas diarias (`docs/adr/ADR-reportes-utilidad-ventas-diarias-*.md`, `docs/design/DDR-reportes-utilidad-ventas-diarias-pantallas-reportes.md`): los importes de Ventas Diaria salen de `Reportes_Business` (cálculo único); el pedido actual no debería tocar el cálculo.
- Estado del reporte de nota de trabajo condicionado por `get_finish_nota_queryset`, usado también por otros consumidores (pendiente de confirmar con Grep en la etapa de plan).

### Riesgos identificados
- Queda una ambigüedad menor ("trabajo" por estado o por número; "cobro" en Nota Trabajo).
- El filtro de "estado" en Nota Trabajo choca con el `status=NT_TERMINADO` fijo del queryset; cambiarlo altera qué filas muestra el reporte a todos los usuarios.
- Filtros de sucursal con opciones acotadas al usuario: hoy la lógica de alcance está repetida y es distinta entre proforma (`sucursales[0]`, string `'Admin'`), nota trabajo (`can_view_all_sucursales`, `sucursales[0]`) y nota venta (sin atajo Admin, `sucursales[0]`); una sola sucursal aunque el usuario tenga varias, mientras el helper nuevo `get_sucursales_in_scope` sí contempla varias: posible inconsistencia entre opciones del filtro y filas visibles.
- Filtros por relaciones (`proforma__car_model_id__car_brand_id`, `nota_venta`, `pago`) pueden encarecer consultas y "Cobro" en Nota Trabajo depende de una relación inversa OneToOne opcional (una nota trabajo sin nota de venta).
- `NotaVentaAdmin.get_queryset` con `qs.filter(sucursal=-1)` (línea 115) falla si un usuario sin sucursal abre la lista; hoy no es parte del pedido pero se toparía al probar el filtro de sucursal.
- Cobertura de tests en el área: existen tests de alcance por sucursal para `ReportNotaTrabajoAdmin`; no se encontraron tests específicos de `list_filter` de estos reportes (no verificado exhaustivamente).
- Default de fecha del reporte de Proforma congelado al arranque del servidor (ver Hechos).

### Veredicto de complejidad
**NEEDS_PLAN** — Es un cambio acotado a la capa de admin de Django (filtros de lista y, quizá, ajustar el queryset de un reporte), sin cambios de modelos, migraciones, API ni autorización nueva; existe un patrón local (`ReportDailySellAdmin`) que seguir. Las ambigüedades principales quedaron aclaradas; lo que resta es detalle de `delivery-plan`.

### Diseño requerido
**NO** — Los filtros se agregan como filtros laterales estándar del Django Admin ya usado en los mismos reportes, sin pantallas ni flujos nuevos. Si se decidiera llevar estos reportes al panel Angular (`panel_admin/`), habría que reabrir esta decisión.

## Diseño
[DDR-filtros-busqueda-reportes-filtros-listados-ordenes](../design/DDR-filtros-busqueda-reportes-filtros-listados-ordenes.md): tarjeta "Filtros" sobre los listados de Proformas, Notas de Trabajo y Notas de Venta del panel Angular, con filtrado en el cliente (mismo patrón visual de Reportes), sin dependencias nuevas.

## Arquitectura
_No aplica según veredicto_

## Plan
[docs/plans/PLAN-2026-09-30-filtros-busqueda-reportes.md](../plans/PLAN-2026-09-30-filtros-busqueda-reportes.md) — versión vigente: **v2** (Fase 1 Django Admin ya implementada; Fase 2 panel Angular pendiente).

## Implementación
Implementado según plan v1, sin desvíos de alcance.

- `admin_config/filtros_reportes.py` (nuevo): `sucursal_en_alcance_filter(path)` (opciones desde `User_Helper.get_sucursales_in_scope`) y `estado_filter(titulo)` (títulos "Estado"/"Cobro"/"Trabajo").
- `reporte_proforma.py`: filtros sucursal, marca, modelo, estado y rango de fecha; el default de fecha ("hoy") ahora se calcula por request.
- `report_nota_trabajo.py`: filtros sucursal, marca, modelo, instalador, estado y cobro (`nota_venta__status`); sin rango de fecha por defecto; llama a `get_finish_nota_queryset(..., solo_terminadas=False)`.
- `business/orden_trabajo.py`: `get_finish_nota_queryset(user, qs, solo_terminadas=True)` (default conserva el comportamiento anterior).
- `nota_venta.py`: filtros sucursal, fecha, trabajo (estado de la nota de trabajo) y cobro; `get_queryset` devuelve `qs.none()` en vez de `qs.filter(sucursal=-1)`.
- Ventas Diaria sin cambios.
- Tests: `tests/test_reportes_filtros_admin.py` (17 casos, integración con el cliente de admin). Corrida propia de `manage.py test product`: 478 tests OK (no es el Quality Gate).

**Hallazgos durante la implementación**
- Django solo acepta parámetros con rutas relacionadas si están en `list_filter` como campo; por eso el filtro de sucursal usa el parámetro simple `sucursal` en vez de `<ruta>__id__exact`.
- Al listar notas sin `entrada_vehiculo` (ahora visibles), `get_entrada_vehiculo_date_format` fallaba con `None`; se corrigió mostrando `-` (cambio mínimo necesario, no estaba en el plan).

**Deuda técnica / pendiente:** alcance por sucursal legado (`sucursales[0]`) y Admin sin sucursal en `NotaVentaAdmin` siguen fuera de alcance (ADR-002). Sin verificación manual en el admin real todavía (recomendada en el plan).

### Fase 2 — Panel Angular (plan v2)
- **Backend (aditivo):** `car_brand_name` en `NotaTrabajoListSerializer` y `car_model__car_brand_id` en el `select_related` de `Orden_Trabajo_Business.get_panel_nota_queryset` (sin N+1 nuevo; cubierto por test de conteo de queries). Tests en `tests/test_ordenes_notas_trabajo.py` (3 casos).
- **Frontend:** nuevo `panel_admin/src/app/ordenes/ordenes.filtros.ts` (utilidades puras: `opcionesUnicas`, `opcionesPorId`, `dentroDeRango`, `rangoFechasInvalido`, opciones de estado/cobro) y su spec. Tarjeta "Filtros" (patrón `section-card` de Reportes) en `proformas-list`, `notas-trabajo-list` y `notas-venta-list` con los filtros del DDR, botón "Limpiar", mensaje "No hay resultados con los filtros aplicados." y sucursal única como texto. El select de estado de Proformas pasó del encabezado a la tarjeta (`onStatusChange` se conserva). `AppNotaTrabajo.car_brand_name?` opcional en `ordenes.model.ts`.
- **Tests Angular:** +31 casos (`ordenes.filtros.spec.ts` y bloques "filtros" en los tres specs de lista). Corrida propia de `ng test`: 294 OK / 15 FAILED; los 15 son specs "should create" de la plantilla (`FeatherModule`: AdvanceTable, Blank, Dashboard2, First1-3, Footer, Main, Page404/500, Second1-2, Sidebar, Signup, Third1) y **fallan igual en `origin/master`** (263 OK / 15 FAILED), no relacionados con este cambio. `manage.py test product`: 481 OK. `ng build` (development) compila. No es el Quality Gate.

**Desvío menor del plan (implementación, no cambia alcance):** las opciones del filtro de sucursal se derivan de las filas cargadas (`sucursal_id`/`sucursal_name`, ya acotadas por el backend a las sucursales del usuario), en vez de llamar a `listSucursales()`. Mismo resultado observable para el usuario (solo ve sucursales con filas dentro de su alcance), evita una petición extra por lista y es consistente con marca/modelo/instalador. Una sucursal del usuario sin filas no aparece como opción.

**Deuda técnica / pendiente**
- Verificación manual en el navegador contra el backend local (plan, paso 6) **no realizada**: requiere iniciar sesión en el panel con un usuario real y no se ingresaron credenciales; recomendada antes de mergear.
- Filtrado en cliente (se migra a servidor si crece el volumen); `proforma_created_on` es `auto_now` (filtra por última modificación).
- Los 15 specs rotos de la plantilla son deuda preexistente.

## Review
**Resultado: PASS** (con verificación manual pendiente y dos observaciones de severidad baja).

Limitación: esta revisión corrió en la **misma sesión** que implementó el código; el aislamiento es solo procedimental.

**Plan compliance (v2)**
- Fase 1 (Django Admin): filtros de Proforma, Nota Trabajo y Notas de Venta implementados; Nota Trabajo lista los tres estados; Ventas Diaria intacto (`test_list_filter_de_ventas_diaria_intacto`).
- Fase 2 (panel Angular): tarjeta de filtros en las tres listas con los filtros del DDR, "Limpiar", mensaje de sin resultados, sucursal única como texto, `car_brand_name` en la API sin N+1 (test de conteo de queries).
- Acceptance criteria: cumplidos por tests automatizados (DOM real en Chrome Headless). Tests del plan presentes; el caso de alcance por sucursal de Notas de Trabajo ya estaba cubierto por `test_ordenes_scope_permissions.py`.
- Fuera de lo previsto en el plan (documentado en el TASK): columna de fecha de entrada nula muestra `-` en el reporte de Nota Trabajo; `qs.none()` en `NotaVentaAdmin`. Ambos mínimos y necesarios.
- ADR-002 respetado: el alcance por sucursal sigue aplicándose en el backend; los filtros son solo de opciones/UX.

**Issues abiertos (no bloquean)**
- [REV-2026-09-30-filtros-busqueda-reportes-01](../reviews/REV-2026-09-30-filtros-busqueda-reportes-01.md) — Low, PLAN: opciones de sucursal desde las filas vs. `listSucursales()` en DDR/plan.
- [REV-2026-09-30-filtros-busqueda-reportes-02](../reviews/REV-2026-09-30-filtros-busqueda-reportes-02.md) — Low, IMPLEMENTATION: getters de opciones recalculados en cada ciclo de detección.

**Fallos ignorados:** los 15 specs de plantilla que ya fallaban en `origin/master` se tratan como deuda preexistente fuera del alcance (evidencia de línea base en `## Testing`); no hubo autorización del usuario para ignorar fallos nuevos porque no los hay.


## Publicación
_Pendiente_

## Hallazgo post-implementación (DESIGN_REVIEW_REQUIRED / PLAN_UPDATE_REQUIRED)
Al probar, el solicitante confirmó que **no ve los filtros porque las pantallas que quería filtrar son las listas del panel Angular** (`panel_admin/src/app/ordenes/proformas`, `notas-trabajo`, `notas-venta`), no los reportes del Django Admin. La investigación asumió el Django Admin (hipótesis sin confirmar: "el alcance es solo el Django Admin", ver Hipótesis) y el plan v1 se construyó sobre eso.

Hechos relevantes para replanificar:
- Las listas Angular filtran en el cliente: texto + estado (`proformas-list.component.ts:64-110`), texto (notas de trabajo y venta); el servicio ya envía `search`, `sales_type`, `status` en proformas y `search`, `status` en notas de venta (`ordenes.service.ts:35-46`, `93-95`, `119-127`). No hay filtros de sucursal, marca, modelo, fecha, instalador ni cobro.
- Ya existe `OrdenesService.listSucursales()` (usado en `proformas-list.component.ts`, `checkSucursal`) con alcance por usuario (`get_sucursales_in_scope`).
- Habrá que revisar los endpoints y serializers de listas (`custom_views/`, `serializer/`) para ver qué campos (marca, instalador, estado de cobro) exponen.
- Los cambios ya hechos en Django Admin (PR #55, commits de implementación) siguen vigentes y probados; queda por decidir si se conservan en este mismo PR.

Siguiente paso: `/delivery-design TASK-filtros-busqueda-reportes` (UI de filtros en listas) y luego `/delivery-plan` (plan v2, incluye ajuste de alcance, contrato API y tests Angular).
