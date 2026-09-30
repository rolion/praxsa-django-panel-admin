# PLAN-2026-09-30-filtros-busqueda-reportes (v2)

**Task:** TASK-filtros-busqueda-reportes
**DDRs relacionados:** [DDR-filtros-busqueda-reportes-filtros-listados-ordenes](../design/DDR-filtros-busqueda-reportes-filtros-listados-ordenes.md)
**ADRs relacionados:** [ADR-002](../adr/ADR-002-filtrado-sucursal-pagos-reportes-admin.md) (alcance por sucursal: solo `Admin` ve todas); ADR-modulo-ordenes-proforma-nota-trabajo-alcance-permisos (alcance del API `ordenes/*` del panel)

> **Nota v2 (2026-09-30).** El solicitante aclaró que las pantallas a filtrar son las **listas del panel Angular** (Órdenes), no el Django Admin (ver TASK, "Hallazgo post-implementación"). El plan queda en dos fases: **Fase 1 — Django Admin** (plan v1, *ya implementada* y probada en este PR; las secciones siguientes la describen) y **Fase 2 — Panel Angular** (nueva; al final de este documento).

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

---

# Fase 2 — Filtros en las listas del panel Angular (nueva en v2)

## Objective (Fase 2)
Agregar a las listas de Proformas, Notas de Trabajo y Notas de Venta de `panel_admin/` una tarjeta "Filtros" con los filtros pedidos, según el DDR: filtrado en el cliente, sin dependencias nuevas.

## Current behavior (Fase 2)
- Las tres listas cargan todas las filas del usuario y filtran en el cliente: `panel_admin/src/app/ordenes/proformas/proformas-list.component.ts:99-112` (texto + estado), `notas-trabajo/notas-trabajo-list.component.ts:58-72` (texto) y `notas-venta/notas-venta-list.component.ts:78-90` (texto). Solo Proformas tiene select de estado, en el encabezado (`proformas-list.component.html:32-38`).
- Datos ya disponibles por fila: Proforma → `sucursal`, `sucursal_name`, `car_brand_name`, `car_model_name`, `proforma_created_on`, `status` (`ordenes.model.ts:27-45`). Nota de Trabajo → `sucursal_id`, `car_model_name`, `instaladar`, `instalador_name`, `status`, `nota_venta{status}` (`ordenes.model.ts:80-97`); **no trae marca**. Nota de Venta → `sucursal_id`, `created_on`, `status`, `work_status` (`ordenes.model.ts:146-160`).
- `NotaTrabajoListSerializer` (`praxsa_manager/product/serializer/ordenes_serializer.py:283-`) no expone `car_brand_name`; `ProformaListSerializer` sí (`ordenes_serializer.py:61,80`).
- El queryset del panel `Orden_Trabajo_Business.get_panel_nota_queryset` (`business/orden_trabajo.py:34-46`) hace `select_related('car_model')` pero no de la marca.
- `OrdenesService.listSucursales()` (`ordenes.service.ts:147-149`) devuelve las sucursales habilitadas en el alcance del usuario; el alcance del panel usa **todas** las sucursales del usuario (no `sucursales[0]`).

## Expected behavior (Fase 2)
Ver la tabla de filtros del DDR. Resumen: Proformas → sucursal, marca, modelo, desde/hasta, estado; Notas de Trabajo → sucursal, marca, modelo, instalador, estado, cobro (incluye "Sin nota de venta"); Notas de Venta → sucursal, desde/hasta, trabajo, cobro. Todo se combina con AND y con el buscador de texto; "Limpiar" restablece; el estado vacío diferencia "sin datos" de "sin resultados con los filtros".

## Architecture considerations (Fase 2)
- **Contrato API**: un solo cambio aditivo, `car_brand_name` en la lista de Notas de Trabajo (campo nuevo, no rompe consumidores). Sin despliegue coordinado: el frontend nuevo tolera `car_brand_name` ausente (Marca queda vacía) por si sale antes que el backend.
- **Rendimiento**: `car_brand_name` requiere `select_related('car_model__car_brand_id')` en `get_panel_nota_queryset` para no agregar N+1. Filtrado en cliente sobre las filas ya cargadas (mismo volumen que hoy).
- **Seguridad**: los filtros son UX; el alcance real sigue en el backend (`get_panel_nota_queryset` y equivalentes). Las opciones de sucursal salen de `listSucursales()`.
- **Migraciones / dinero**: ninguna.
- **Consistencia visual**: DDR (tarjeta `section-card` con ícono de filtro, `form-select form-control`, `<input type="date">`, botón "Limpiar"); sin datepicker ni dependencias.
- **Acoplamiento**: la lógica de filtrado se extrae a un módulo TypeScript puro (`ordenes.filtros.ts`) reutilizable por las tres listas, en vez de copiar las mismas funciones tres veces.

## Proposed solution (Fase 2)
1. **Backend** (aditivo): `car_brand_name` en `NotaTrabajoListSerializer` (`obj.car_model.car_brand_id.name` o `None`) y `car_model__car_brand_id` en el `select_related` de `get_panel_nota_queryset`.
2. **Frontend, módulo puro** `panel_admin/src/app/ordenes/ordenes.filtros.ts`: `opcionesUnicas(rows, getter)` (valores únicos ordenados, sin vacíos), `dentroDeRango(fecha, desde, hasta)` (compara la parte `YYYY-MM-DD`; con rango activo excluye fechas nulas), `rangoInvalido(desde, hasta)` (mensaje si desde > hasta), y las constantes de opciones de estado de nota de trabajo y de cobro (`en_proceso`, `terminado`, `cancelada`; `por_cobrar`, `pagada`, `anulada`, más `sin_nota_venta` solo en Notas de Trabajo).
3. **Cada lista**: un objeto `filtros` (valores vacíos por defecto), `applyFilters()` que combina buscador + filtros con AND y reinicia `table.offset = 0`, handlers de `change`, `limpiarFiltros()`, y carga de `sucursales` con `listSucursales()` (si es una sola se muestra como texto). Marca/Modelo/Instalador con `opcionesUnicas`; Modelo se acota a la marca elegida y se reinicia al cambiar la marca. Template: tarjeta "Filtros" entre el breadcrumb y la tabla, según el DDR; el select de estado de Proformas se mueve allí.
4. **Mensaje sin resultados**: "No hay resultados con los filtros aplicados." cuando hay filas cargadas pero `rows` queda vacío.
5. **Estilos**: reutilizar clases existentes (`section-card`, `section-header`, `info-label`); solo si falta algo, un ajuste mínimo en `assets/scss/_ordenes.scss`.

Alternativas descartadas: filtros de servidor con parámetros de API (ver DDR); un componente "barra de filtros" genérico configurable (sobreingeniería para tres pantallas con controles distintos).

## Files/components affected (Fase 2)
**Backend** (`praxsa_manager/product/`): `serializer/ordenes_serializer.py`, `business/orden_trabajo.py`, `tests/test_ordenes_notas_trabajo.py`.
**Frontend** (`panel_admin/src/app/ordenes/`): `ordenes.filtros.ts` (nuevo) y `ordenes.filtros.spec.ts` (nuevo), `ordenes.model.ts` (campo `car_brand_name?` en `AppNotaTrabajo`), `proformas/proformas-list.component.{ts,html}` y su spec, `notas-trabajo/notas-trabajo-list.component.{ts,html}` y `notas-trabajo.components.spec.ts`, `notas-venta/notas-venta-list.component.{ts,html}` y `notas-venta.components.spec.ts`; posible ajuste en `assets/scss/_ordenes.scss`.

## Implementation steps (Fase 2)
1. Backend: `car_brand_name` en el serializer de lista de Notas de Trabajo + `select_related`; test de contrato.
2. Crear `ordenes.filtros.ts` con sus pruebas unitarias.
3. Proformas: tarjeta y lógica de filtros (mover el select de estado); actualizar `proformas-list.component.spec.ts`.
4. Notas de Trabajo: tarjeta y lógica (sucursal, marca, modelo, instalador, estado, cobro); spec.
5. Notas de Venta: tarjeta y lógica (sucursal, fechas, trabajo, cobro); spec.
6. Verificación en el navegador contra el backend local (Admin y usuario de una sola sucursal), en escritorio y ancho móvil.
7. Correr `ng test` del panel y `manage.py test product`.

## Test strategy (Fase 2)
- **Backend (integración, `TestCase` + cliente API, patrón de `tests/test_ordenes_notas_trabajo.py`)**: la lista de Notas de Trabajo incluye `car_brand_name` (con modelo → nombre de marca; sin modelo → `null`); el alcance por sucursal no cambia (usuario de otra sucursal no ve la nota).
- **Unit (`ordenes.filtros.spec.ts`)**: `opcionesUnicas` (únicos, ordenados, ignora vacíos/null); `dentroDeRango` (límites inclusivos, solo desde, solo hasta, fecha nula con rango activo/inactivo); `rangoInvalido`.
- **Componente (`TestBed` + `HttpTestingController`, patrón de los specs existentes)**, por lista: cada filtro reduce las filas como se espera; combinación de dos filtros + buscador (AND); "Limpiar" restaura; en Proformas Modelo se acota a la Marca y se reinicia al cambiar la marca; las opciones de sucursal salen de `listSucursales()` y con una sola se muestra texto; mensaje "sin resultados con los filtros" vs. "no hay ..."; Notas de Trabajo: filtro "Sin nota de venta"; Notas de Venta: fecha nula excluida con rango activo; Desde > Hasta muestra el error y no filtra por fecha.
- **E2E (Playwright): No corresponde.** Es filtrado local en tres listas, sin flujo multi-paso ni integración frontend-backend nueva más allá de un campo aditivo cubierto por test de contrato; Playwright no está instalado y no se agrega. Se cubre con la verificación manual (paso 6).

## Acceptance criteria (Fase 2)
- Proformas muestra filtros de sucursal, marca, modelo, desde/hasta y estado; Notas de Trabajo, sucursal, marca, modelo, instalador, estado y cobro; Notas de Venta, sucursal, desde/hasta, trabajo y cobro.
- El desplegable de sucursal muestra solo las sucursales disponibles para el usuario.
- Los filtros se combinan entre sí y con el buscador; "Limpiar" restablece; cada cambio vuelve a la página 1.
- Con filtros que no coinciden se ve "No hay resultados con los filtros aplicados." (no el aviso de falta de sucursal).
- `GET ordenes/notas-trabajo` incluye `car_brand_name`; el resto del contrato no cambia; sin N+1 nuevo.
- Ventas Diarias y Utilidad no cambian.
- Tests nuevos y existentes (Angular y `product`) pasan.

## Risks (Fase 2)
- Las opciones de marca/modelo/instalador salen de las filas cargadas, no del catálogo: un valor sin filas no aparece (decisión consciente del DDR).
- Filtrado en el cliente: si el volumen de filas crece mucho, habrá que migrar a filtros de servidor (sin mitigación en este cambio).
- `proforma_created_on` es `auto_now` (última modificación): "Desde/Hasta" en Proformas filtra por esa fecha, no por la creación real (preexistente, fuera de alcance).
- Repetir el patrón en tres componentes puede divergir; se mitiga con el módulo compartido `ordenes.filtros.ts`.
- `car_brand_name` ausente si el frontend se despliega antes que el backend: se tolera (Marca vacía), no rompe.

## Out of scope (Fase 2)
- Filtros de servidor/paginación, exportación, guardar filtros entre sesiones.
- Cambios en Reportes (Ventas Diarias, Utilidad) y en la lógica de alcance del backend.
- **Supuesto abierto**: la Fase 1 (Django Admin, ya implementada y probada) **se conserva en este mismo PR** por defecto; si se prefiere retirarla, se revierte por separado. "Trabajo" en Notas de Venta sigue siendo el estado de la nota de trabajo.

## Changelog
- **v2** (2026-09-30): el solicitante aclaró que las pantallas objetivo son las listas del panel Angular, no el Django Admin. Se agrega la Fase 2 (panel Angular, según DDR-filtros-busqueda-reportes-filtros-listados-ordenes) y la Fase 1 (Django Admin) queda como ya implementada. Solicitado por delivery-engineer (DESIGN_REVIEW_REQUIRED, registrado en el TASK).
