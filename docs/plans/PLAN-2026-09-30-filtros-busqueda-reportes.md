# PLAN-2026-09-30-filtros-busqueda-reportes (v1)

**Task:** TASK-filtros-busqueda-reportes
**DDRs relacionados:** Ninguno
**ADRs relacionados:** [ADR-002](../adr/ADR-002-filtrado-sucursal-pagos-reportes-admin.md) (alcance por sucursal: solo `Admin` ve todas)

## Objective
Agregar filtros laterales de búsqueda al Reporte Proforma, al Reporte Nota Trabajo y a la pantalla de Notas de Venta del Django Admin, con el filtro de sucursal mostrando solo las sucursales disponibles para el usuario.

## Context
Ver `docs/tasks/TASK-filtros-busqueda-reportes.md`. Los tres son `ModelAdmin` de solo `list_filter` estándar; no hay cambios de modelos, API ni frontend. "Ventas Diaria" **no se toca**.

## Current behavior
- `ReportProformaAdmin.list_filter` (`praxsa_manager/product/admin_config/reporte_proforma.py:35-42`): tipo de venta, sucursal (`RelatedDropdownFilter`, lista todas las sucursales), rango de `proforma_created_on` con default calculado al importar el módulo (línea 38-41: queda fijo al día de arranque del servidor). Sin marca, modelo ni estado.
- `ReportNotaTrabajoAdmin.list_filter` (`report_nota_trabajo.py:36-45`): tipo de venta, rango de `entrada_vehiculo` (default 2020-2030) y sucursal (todas). El queryset viene de `Orden_Trabajo_Business.get_finish_nota_queryset` (`business/orden_trabajo.py:47-62`) que fuerza `status=NT_TERMINADO`. Sin marca, modelo, instalador, estado ni cobro.
- `NotaVentaAdmin` (`admin_config/nota_venta.py:26-`): sin `list_filter`. `get_queryset` (línea 110-116) usa `qs.filter(sucursal = -1)` cuando el usuario no tiene sucursal, campo que `Nota_Venta` no tiene (`FieldError`).
- `entrada_vehiculo` es nullable (`models.py:208`) y solo se completa desde `NotaTrabajoAdmin` (`admin_config/nota_trabajo.py`), no desde el flujo del panel.

## Expected behavior
- **Reporte Proforma**: filtros sucursal (solo las del usuario), marca, modelo, rango de fecha, estado (`Proforma_Header.status`). Se conserva tipo de venta.
- **Reporte Nota Trabajo**: filtros sucursal (solo las del usuario), marca, modelo, instalador, estado (en proceso / terminado / cancelada, las tres visibles) y cobro (estado de la nota de venta: por cobrar / pagada / anulada). Se conservan tipo de venta y fecha de entrada.
- **Notas de Venta**: filtros sucursal (solo las del usuario), rango de fecha (`created_on`), trabajo (estado de la nota de trabajo asociada) y cobro (`Nota_Venta.status`).
- "Sucursales disponibles": todas las habilitadas para `Admin` y las habilitadas donde el usuario es empleado para el resto (`User_Helper.get_sucursales_in_scope`, `helper/user.py:41-47`).

## Architecture considerations
- **Contrato API / Angular**: sin impacto (solo Django Admin). No hay coordinación de despliegue.
- **Datos / migraciones**: ninguna.
- **Dinero**: no se tocan cálculos.
- **Permisos**: el filtro de sucursal solo restringe opciones; el alcance real de las filas sigue en los `get_queryset` (ADR-002). No se cambia autorización.
- **Rendimiento**: filtros por FK (`car_model_id__car_brand_id`, `nota_venta__status`, `nota_trabajo__status`) hacen JOIN; los querysets ya usan `select_related`. Al agregar `nota_venta__status` sobre `Nota_trabajo` (relación inversa OneToOne) se excluyen las notas de trabajo sin nota de venta solo cuando el filtro está activo.
- **Acoplamiento**: `get_finish_nota_queryset` solo lo usan `ReportNotaTrabajoAdmin` y sus tests (verificado con Grep). Se agrega un parámetro con default que conserva el comportamiento actual.
- **Consistencia**: se sigue el patrón de `ReportDailySellAdmin` (`report_daily_sell.py:38-52`): filtros de `django_admin_listfilter_dropdown`/`rangefilter` y defaults de fecha dinámicos por request.

## Proposed solution
1. Nuevo módulo `praxsa_manager/product/admin_config/filtros_reportes.py` con dos fábricas pequeñas:
   - `sucursal_en_alcance_filter(path)` → `SimpleListFilter` (título "Sucursal") cuyo `lookups` devuelve `User_Helper.get_sucursales_in_scope(request.user)` y cuyo `queryset` filtra por `<path>__id`.
   - `estado_filter(titulo)` → subclase de `ChoiceDropdownFilter` con título fijo ("Estado", "Cobro", "Trabajo"), necesaria porque varios filtros comparten el nombre de campo `status` y el título por defecto sería "Estado" en todos.
2. `ReportProformaAdmin`: `list_filter` = tipo de venta, sucursal en alcance (`sucursal`), marca (`RelatedDropdownFilter` sobre `car_model_id__car_brand_id`), modelo (`RelatedDropdownFilter` sobre `car_model_id`), estado (`status`), rango de fecha. Default de fecha dinámico con `get_rangefilter_proforma_created_on_default(request)` (hoy 00:00-23:59:59, mismo patrón que Ventas Diaria).
3. `Orden_Trabajo_Business.get_finish_nota_queryset(user, qs, solo_terminadas=True)`; `ReportNotaTrabajoAdmin` lo llama con `solo_terminadas=False` para poder listar en proceso / terminado / cancelada. Los tests y demás usos existentes quedan igual (default `True`).
4. `ReportNotaTrabajoAdmin`: `list_filter` = tipo de venta, fecha de entrada, sucursal en alcance (`proforma__sucursal`), marca (`car_model__car_brand_id`), modelo (`car_model`), instalador (`instaladar`), estado (`status`), cobro (`nota_venta__status`, choices de `NV_STATUS_CHOICES`). El filtro de fecha de entrada deja de aplicar el default 2020-2030 (que esconde las notas con `entrada_vehiculo` nulo, típicas de "en proceso"), quedando sin restricción hasta que el usuario elija un rango.
5. `NotaVentaAdmin`: `list_filter` = sucursal en alcance (`nota_trabajo__proforma__sucursal`), rango de fecha (`DateTimeRangeFilterBuilder`, título "Fecha", sobre `created_on`, sin default), trabajo (`nota_trabajo__status`) y cobro (`status`). Corrección mínima necesaria: `get_queryset` devuelve `qs.none()` en vez de `qs.filter(sucursal=-1)` cuando el usuario no tiene sucursal (sin ella el admin lanza `FieldError` al usar la pantalla).

Alternativas descartadas: reutilizar `RelatedDropdownFilter` para sucursal y confiar en el queryset (muestra opciones ajenas al usuario, incumple el pedido); crear un servicio genérico de filtros (sobreingeniería, ver ADR-002).

## Files/components affected
**Backend** (`praxsa_manager/product/`)
- `admin_config/filtros_reportes.py` (nuevo)
- `admin_config/reporte_proforma.py`
- `admin_config/report_nota_trabajo.py`
- `admin_config/nota_venta.py`
- `business/orden_trabajo.py` (`get_finish_nota_queryset`, parámetro nuevo)
- `tests/test_reportes_filtros_admin.py` (nuevo) y, si corresponde, ajuste en `tests/test_sucursal_scope_admin.py`

**Frontend**: ninguno (`proforma/` y `panel_admin/` sin cambios).

## Implementation steps
1. Crear `filtros_reportes.py` con `sucursal_en_alcance_filter` y `estado_filter` + tests unitarios de ambos.
2. Agregar `solo_terminadas` a `get_finish_nota_queryset` (default `True`) + tests: con `False` devuelve las tres.
3. Actualizar `ReportProformaAdmin` (filtros y default de fecha dinámico).
4. Actualizar `ReportNotaTrabajoAdmin` (filtros, `solo_terminadas=False`, fecha sin default).
5. Actualizar `NotaVentaAdmin` (filtros y `qs.none()`).
6. Verificar en el admin real contra el Postgres local (ver memoria de entorno) con un usuario Admin y uno de una sola sucursal: opciones de sucursal, cada filtro y combinación.
7. Correr la suite de `product/tests` completa.

## Test strategy
- **Unitario/integración (Django `TestCase`, `helpers.py`)**, en `tests/test_reportes_filtros_admin.py`:
  - Sucursal en alcance: Admin ve todas las habilitadas; usuario normal solo las suyas; sucursal deshabilitada excluida; el filtro restringe filas por sucursal.
  - Proforma: filtrar por marca, modelo, estado y rango de fecha devuelve solo las filas esperadas (usar `admin.get_changelist_instance` con `RequestFactory` y `request.GET`).
  - Nota Trabajo: con `solo_terminadas=False` aparecen las tres; filtros marca, modelo, instalador, estado y cobro (nota trabajo sin nota de venta no aparece al filtrar por cobro; sí sin filtro); nota con `entrada_vehiculo` nulo visible sin filtro de fecha.
  - Nota Venta: filtros sucursal, fecha, trabajo y cobro; usuario sin sucursal no revienta y ve lista vacía con el mensaje.
  - Regresión: `ReportDailySellAdmin.list_filter` sin cambios; `get_finish_nota_queryset` con default sigue devolviendo solo terminadas (tests existentes en `test_sucursal_scope_admin.py:160-215`).
- **E2E (Playwright): No corresponde.** Es una pantalla del Django Admin renderizada por el servidor, sin flujo multi-paso ni integración frontend-backend; los tests de changelist de Django cubren el comportamiento. Playwright no está instalado en el proyecto y no se agrega.
- **Verificación manual** (paso 6) por el tipo de cambio (autorización/alcance): sugerida antes de mergear.

## Acceptance criteria
- Reporte Proforma muestra filtros: sucursal, marca, modelo, fecha, estado (y tipo de venta).
- Reporte Nota Trabajo muestra filtros: sucursal, marca, modelo, instalador, estado, cobro (y tipo de venta, fecha entrada) y lista notas en proceso, terminadas y canceladas.
- Notas de Venta muestra filtros: sucursal, fecha, trabajo, cobro.
- En los tres, el desplegable de sucursal solo ofrece las sucursales habilitadas disponibles para el usuario (todas para `Admin`).
- El reporte Ventas Diaria queda idéntico.
- Un usuario sin sucursal ve la pantalla de Notas de Venta vacía con el mensaje "Asigne una sucursal al usuario", sin error.
- Los tests nuevos y la suite existente de `product` pasan.

## Risks
- Usuarios con varias sucursales: los queryset legados solo muestran la primera (`sucursales[0]`, `business/proforma.py:148`, `orden_trabajo.py:56`), pero el filtro ofrecerá todas las suyas; elegir una que no sea la primera devolverá 0 filas. Mitigación: ninguna en este cambio (unificar el alcance es otro objetivo); queda documentado.
- Quitar el filtro `terminado` amplía lo que ve el reporte de Nota Trabajo para todos los usuarios (ahora también en proceso y canceladas). Es lo pedido; se refleja en criterios de aceptación.
- Quitar el default de fecha en Nota Trabajo cambia el listado inicial (ya no excluye notas sin `entrada_vehiculo`). Mitigación: test dedicado.
- El `RelatedDropdownFilter` de marca/modelo sobre rutas anidadas (`car_model_id__car_brand_id`) debe verificarse en el admin real; si el widget no resuelve la ruta, se cae a un filtro propio con la misma fábrica.
- Título del filtro de fecha en Proforma sigue basado en `proforma_created_on` (`auto_now`): filtra por última modificación, no por creación. No se corrige aquí.

## Out of scope
- Cambiar el alcance por sucursal (multi-sucursal, `sucursales[0]`) y el bug de Admin sin sucursal en `NotaVentaAdmin` (ADR-002).
- `auto_now` de `proforma_created_on`, el texto del link `get_nota_trabajo_id` en Nota Trabajo, y `search_fields` con campos poco útiles.
- Ventas Diaria, Reporte Inventario, Reporte Utilidades, y cualquier pantalla del panel Angular.
- **Preguntas abiertas:** (1) "trabajo" en Notas de Venta se implementó como estado de la nota de trabajo; si se prefiere el número de nota, se cambia el filtro. (2) Un Admin sin sucursal asignada sigue viendo vacía la pantalla de Notas de Venta (bug preexistente); se recomienda un cambio aparte, pero puede incluirse aquí si se prefiere.
