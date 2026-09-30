# PLAN-2026-09-30-reportes-utilidad-ventas-diarias (v1)

**Task:** TASK-reportes-utilidad-ventas-diarias
**DDRs relacionados:** [DDR-reportes-utilidad-ventas-diarias-pantallas-reportes](../design/DDR-reportes-utilidad-ventas-diarias-pantallas-reportes.md)
**ADRs relacionados:** [ADR-reportes-utilidad-ventas-diarias-calculo-y-api](../adr/ADR-reportes-utilidad-ventas-diarias-calculo-y-api.md) (con Actualización 1), [ADR-reportes-utilidad-ventas-diarias-permisos](../adr/ADR-reportes-utilidad-ventas-diarias-permisos.md)

## Objective

Que "Reporte Ventas Diaria" y "Reporte Utilidades" muestren cifras correctas de ventas cobradas y utilidad (venta de lámina − costo de compra, con y sin descuento, con y sin instalación, con totales), calculadas en un solo lugar, y que además existan como pantallas de solo lectura en `panel_admin/`, con acceso por permiso (Ventas: Admin y Caja; Utilidad: Admin).

## Context

Ver TASK-reportes-utilidad-ventas-diarias. Los reportes actuales del Django Admin calculan "utilidad" sin restar el costo, se rompen con proformas sin ítems y no dan totales; no existen en el panel. Decisiones ya tomadas: DDR (menú "Reportes", filtros de servidor, tarjetas, tablas) y dos ADR (cálculo único + API; permisos `view_proxy_pagos` / `view_utilidades`). Respuestas del usuario: instalación aparte de la utilidad; descuento restado íntegro de la utilidad de lámina; roles Ventas = Admin+Caja, Utilidad = Admin.

**Nota de verificación (el código cambió desde la investigación):** la investigación se hizo sobre una base que estaba 11 commits detrás de `origin/master`. La rama de trabajo se creó desde `origin/master` (que ya incluye #52, mejora de inventario) y se re-verificó lo citado. Diferencias relevantes: una línea de venta ahora puede consumir metros de **varias filas de inventario** (`business/inventario.py:64-99`), registradas en `Inventario_Movimiento` (`models.py`); `Proforma_Detail.inventario` solo apunta a la primera fila. Esto obligó a corregir la fuente del costo en el ADR (Actualización 1). Las citas `archivo:línea` de la investigación sobre `report_daily_sell.py`, `report_utilidad.py` y `pago.py` no cambiaron.

## Current behavior

- `admin_config/report_daily_sell.py:41-51,93-121` — una fila por `pago`; importes de la proforma (no del pago); sin totales; `get_costo_instalacion` usa `reduce` sin valor inicial (`:107-113`); typo en `admin_order_field` (`:98`); filtro de sucursal duplicado y default de fecha evaluado al importar (`:52-60`).
- `admin_config/report_utilidad.py:41-70` — "Utilidad Lámina" = `precio × largo (× cantidad)`, sin restar `precio_compra_mtr_lineal`; cuenta ventas por cobrar; sin filtro de fecha.
- Ninguno de los dos define `has_delete_permission` (`report_daily_sell.py:148-152`, `report_utilidad.py:72-76`).
- Alcance por sucursal legado: `Pago_Business.get_pago_queryset_by_role` (`business/pago.py:26-39`) e `Inventario_Business.get_inventario_queryset_by_role` (`business/inventario.py:17-27`) usan solo la primera sucursal habilitada; la API del panel usa todas (`business/pago.py:14-24`, `helper/user.py`).
- `panel_admin/` no tiene reportes; el sidebar no filtra ítems por permiso (`layout/sidebar/sidebar.component.ts:96-97`, `sidebar.metadata.ts`, `routes.json` sin campo de permiso).

## Expected behavior

- Ventas Diarias y Utilidad (Django Admin y panel) muestran las mismas cifras, calculadas con las definiciones del ADR: solo ventas cobradas, fecha = fecha del pago, `Cobrado = pago.monto`, `Bruto = lámina + instalación`, `Utilidad antes = venta lámina − costo`, `Utilidad después = antes − descuento`, instalación aparte.
- Totales del período, desglose con/sin instalación y por tipo de pago.
- Aviso visible donde falte el costo de compra (`costo_incompleto`).
- Endpoints `GET product/reportes/ventas-diarias` y `GET product/reportes/utilidad` con 403 sin permiso, 404 para sucursal ajena y 400 con parámetros inválidos.
- Los admins de Django quedan de solo lectura real (sin borrar).

## Architecture considerations

Resumen de los ADR (no se re-deriva):
- **Contrato API:** solo endpoints nuevos y aditivos; ningún consumidor existente cambia. `proforma/` no los consume.
- **Datos existentes / migraciones:** ninguna migración ni cambio de modelo. Ventas anteriores a #52 no tienen `Inventario_Movimiento`: se usa el fallback legado (`detalle.inventario`) y, si falta, se marca `costo_incompleto`.
- **Dinero y precisión:** todo en `Decimal`; cada venta se redondea a centavos (`ROUND_HALF_UP`, como `business/pricing.py`) y los totales suman las ventas redondeadas.
- **Rendimiento:** número constante de consultas por reporte (pagos, líneas, movimientos, precios de lote; sin N+1); rango máximo 366 días; sin paginación server-side (deuda aceptada). Las listas `IN` se acotan por el rango.
- **Seguridad:** permisos Django `view` por reporte verificados en servidor (403); Ventas Diarias no lleva campos de costo; alcance por sucursal del panel; `has_delete_permission=False` en los admins.
- **Acoplamiento:** el cálculo se centraliza en `business/reportes.py`; los admins legados de `pago`/`inventario` (`PagosAdmin`, `ReportStorageAdmin`, etc.) no cambian; los métodos de alcance legado tampoco (se agregan métodos nuevos al lado).
- **Consistencia visual:** los componentes están decididos en el DDR (tarjetas `_ordenes.scss`, `ngx-datatable`, alertas); solo se traducen a pasos.

## Proposed solution

**Seam único:** `Reportes_Business` (`business/reportes.py`) expone funciones que reciben un **queryset de `pago` ya filtrado** (alcance + rango + filtros) y devuelven ventas calculadas; la API arma ese queryset desde los parámetros, y los admins desde su `ChangeList`. Con eso hay una sola implementación aunque las superficies difieran.

Detalle de cálculo por línea (`Proforma_Detail`), todo `Decimal`:
- `metros = length × quantity` si `quantity > 0`, si no `length` (misma regla que `orden_estado.py:103-104`).
- `venta_lamina = metros × window_film_price`; `instalacion = installation_price × quantity`; `bruto = venta_lamina + instalacion`.
- `costo = Σ_fila (egresos − devoluciones) × precio_compra_mtr_lineal` de esa fila; fallback si no hay movimientos: `metros × precio_compra` de `detalle.inventario`; si no hay nada → 0 y `costo_incompleto`. También `costo_incompleto` si alguna fila consumida tiene precio 0 o si el neto de movimientos es 0.
- Por venta: `descuento = proforma.discount`, `cobrado = pago.monto`, `utilidad_antes = venta_lamina − costo`, `utilidad_despues = utilidad_antes − descuento`, `margen = utilidad_despues ÷ (bruto − descuento)` (nulo si el divisor es 0).
- Agrupaciones: por tipo de venta (`Proforma_Header.sales_type`), por tipo de pago, y por lámina (sucursal + lámina + ancho de la **línea**).
- Django Admin "Reporte Utilidades": fila por lote de inventario, con **tramos** (línea × fila de inventario) de ventas cobradas, acumulados (sin filtro de fecha; el filtro por período vive en el panel).

## Files/components affected

**Backend (`praxsa_manager/product/`)**
- Nuevo `business/reportes.py` — cálculo único, agrupaciones y validación de rango.
- `business/pago.py`, `business/inventario.py` — métodos **nuevos** de alcance del panel (`get_panel_pago_queryset`, `get_panel_inventario_queryset`); los legados no se tocan.
- Nuevo `serializer/reportes_serializer.py` — parámetros y respuestas (dos esquemas separados; el de ventas sin costos).
- Nuevo `custom_views/reportes_admin.py` — `ReporteVentasDiariasView`, `ReporteUtilidadView`.
- `permissions.py` — permiso reutilizable `TienePermisoReporte` (verificación `has_perm` explícita).
- `urls.py` — rutas `reportes/ventas-diarias` y `reportes/utilidad`.
- `admin_config/report_daily_sell.py`, `admin_config/report_utilidad.py` — reescritura sobre `Reportes_Business`; sin borrar.
- Nuevo `management/commands/asignar_permisos_reportes.py`.
- `tests/`: nuevos `test_reportes_calculo.py`, `test_reportes_api.py`, `test_reportes_admin.py`, `test_asignar_permisos_reportes.py`; ajustes en `tests/helpers.py` (fábricas de línea con cantidad/instalación/movimientos).

**Frontend (`panel_admin/src/`)**
- Nuevo módulo `app/reportes/`: `reportes.routes.ts`, `reportes.model.ts`, `reportes.service.ts`, `ventas-diarias/ventas-diarias.component.{ts,html}`, `utilidad/utilidad.component.{ts,html}` y specs.
- `app/app.routes.ts` — ruta `reportes`.
- `assets/data/routes.json` — grupo "Reportes" con permiso por submenú.
- `app/layout/sidebar/sidebar.metadata.ts`, `sidebar.component.ts` — campo opcional `permission` y filtrado por `AuthService.hasPermission`; spec.
- `assets/scss/_reportes.scss` + `@use` en `style.scss`.
- `docs/design/DDR-...`: Actualización 1 (marca/aviso de `costo_incompleto`).

## Implementation steps

**Fase 0 — verificación previa (sin código de producto)**
1. Preparar el entorno del worktree (`.env` copiado, carpeta `logs/`, ver memoria del proyecto) y correr la suite actual como línea base: `python manage.py test`. Anotar fallos previos.
2. Confirmar en la base de pruebas que existen los permisos `view_proxy_pagos` y `view_utilidades` bajo `product` (hipótesis del ADR de permisos); si los codenames difieren, ajustar el ADR y este plan antes de seguir.

**Fase 1 — cálculo (backend)**
3. `business/reportes.py`: función que, dado un queryset de `pago`, trae en bloque pagos (+proforma/sucursal/cliente/vehículo), líneas, movimientos netos y precios de lote, y devuelve ventas calculadas según las reglas de arriba. Sin tocar el ORM por venta.
4. Agrupaciones y totales (`por_tipo_venta`, `por_tipo_pago`, `por_lamina`, `totales` con `ventas_costo_incompleto`), con redondeo por venta y totales = suma de ventas redondeadas.
5. Validación de parámetros compartida (rango ISO, `desde ≤ hasta`, máximo 366 días, valores válidos de `sales_type`/`tipo_pago`).
6. Función de tramos por lote para el Django Admin (`calcular_por_lote`), reutilizando la misma regla de costo.

**Fase 2 — alcance, API y permisos (backend)**
7. `get_panel_pago_queryset` / `get_panel_inventario_queryset`: Admin todas; el resto todas sus sucursales habilitadas; sin sucursal → `qs.none()` (patrón de `business/pago.py:14-24`, `business/inventario.py:17-27`).
8. Serializers de parámetros y de respuesta; el de Ventas Diarias sin campos de costo/utilidad/margen.
9. `TienePermisoReporte` + dos vistas; sucursal ajena → 404; sin permiso → 403; `sin_sucursal` en respuesta vacía. Rutas en `urls.py`.
10. Comando `asignar_permisos_reportes` (mismo patrón que `asignar_permisos_estados.py`: `--dry-run`, idempotente, no crea grupos, error claro si falta grupo/permiso): `view_proxy_pagos` → Admin y Caja; `view_utilidades` → Admin.

**Fase 3 — Django Admin (backend)**
11. Reescribir `ReportDailySellAdmin`: columnas del ADR calculadas por página con una llamada al servicio (sin N+1; sin `admin_order_field` en columnas calculadas), filtros de sucursal (uno solo) y rango de fecha con default **calculado por request** (no al importar), tipo de venta; totales en `changelist_view` (`extra_context`) sobre el queryset filtrado, al estilo de `aggregated_result` de `report_storage.py`; conservar el mensaje "Asigne una sucursal al usuario" (tests existentes en `test_sucursal_scope_admin.py:308+`).
12. Reescribir `ReportUtilidadAdmin`: fila por lote con venta/costo/utilidad por tramos; alcance del panel; mismo mensaje sin sucursal.
13. Ambos: `has_add/change/delete_permission` → `False`; quitar imports y `form` sin uso.

**Fase 4 — frontend**
14. `reportes.model.ts` y `reportes.service.ts` (`getVentasDiarias(filtros)`, `getUtilidad(filtros)`, reutiliza `listSucursales` de `OrdenesService`); rutas y `loadChildren` en `app.routes.ts`.
15. `ventas-diarias.component`: filtros (fechas por defecto hoy, sucursal, tipo de venta, tipo de pago), botón Aplicar/Limpiar, validación de rango, tarjetas de totales, desglose por tipo de venta y de pago, `ngx-datatable` con búsqueda client-side, estados de carga/error/vacío/sin sucursal/403.
16. `utilidad.component`: mismos filtros (rango por defecto: mes en curso), tarjetas (con y sin descuento, costo, margen, ingreso por instalación aparte), tabla por venta y tabla resumen por lámina, aviso de `costo_incompleto` (fila y tarjeta).
17. `assets/scss/_reportes.scss` (bloque `.reporte-*` extendiendo lo de `_ordenes.scss`) y `@use` en `style.scss`.
18. Sidebar: campo `permission?` en `RouteInfo`, filtrado por `hasPermission` (un grupo se oculta si todos sus submenús se ocultan) y grupo "Reportes" en `routes.json` (`view_proxy_pagos`, `view_utilidades`). Las pantallas muestran "No tiene permiso para ver este reporte" si el usuario entra por URL sin permiso, sin consultar la API.
19. Agregar Actualización 1 al DDR (aviso de costo incompleto y filtrado del menú por permiso).

**Fase 5 — cierre**
20. Suite backend completa, `python manage.py makemigrations --check --dry-run` (debe no generar nada), `npm test` y `npm run build` de `panel_admin/`, `npm run lint`.
21. Verificación manual en vivo (ver Test strategy).

## Test strategy

**Backend — unitarios (`test_reportes_calculo.py`), con datos de importes conocidos:**
- Venta con instalación: bruto, descuento, cobrado, costo, utilidad antes/después, margen calculados a mano.
- Venta metro lineal (cantidad 0): metros = largo; instalación 0.
- Con y sin descuento (utilidad antes ≠ después); descuento mayor a la utilidad → utilidad negativa.
- Costo con línea repartida en dos filas de inventario con **precios de compra distintos** (movimientos egreso); con devolución parcial; fallback legado (sin movimientos, con `detalle.inventario`); sin movimientos ni inventario → `costo_incompleto`; fila con precio 0 → `costo_incompleto`.
- Venta por cobrar, venta anulada y proforma borrada excluidas; pago anulado (borrado) excluido.
- Proforma sin ítems no rompe (fila con ceros).
- Redondeo por venta y totales = suma de filas; conciliación: Σ `cobrado` = Σ `pago.monto` del rango y `bruto − descuento = cobrado` por venta.
- Agrupaciones: por tipo de venta, por tipo de pago, por lámina (una línea repartida en dos lotes cuenta una sola vez).
- Fronteras de fecha (inicio y fin del día inclusive; fecha del pago).

**Backend — integración API (`test_reportes_api.py`):**
- 403 sin permiso; 200 para Admin en ambos reportes; Caja: 200 en Ventas Diarias y 403 en Utilidad; Vendedor 403; no-staff 403; sin token 401.
- **La respuesta de Ventas Diarias no contiene ninguna clave de costo/utilidad/margen** (test explícito de claves).
- Alcance: Admin ve todas; empleado de la sucursal A no ve B ni con `?sucursal=B` (404); usuario con dos sucursales ve ambas; sin sucursal → vacío con `sin_sucursal: true`.
- Validación: falta `desde`/`hasta`, formato inválido, `desde > hasta`, rango > 366 días, `sales_type`/`tipo_pago` desconocidos → 400.
- Número de consultas acotado y constante al crecer el número de ventas (`assertNumQueries` / `CaptureQueriesContext`).

**Backend — Django Admin (`test_reportes_admin.py`):** columnas calculadas por página; totales de `changelist_view`; ningún usuario (ni superusuario) tiene `add/change/delete`; el mensaje "Asigne una sucursal al usuario" se conserva; los tests existentes de `test_sucursal_scope_admin.py` siguen pasando.

**Backend — comando (`test_asignar_permisos_reportes.py`):** idempotencia, `--dry-run` sin escribir, error si falta un grupo o permiso, grupos resueltos sin distinguir mayúsculas.

**Frontend (Karma/Jasmine, patrón de `ordenes.service.spec.ts` y specs de listados con `TestBed` + `HttpTestingController`):**
- Servicio: URL y parámetros de cada endpoint.
- Componentes: filtros por defecto (hoy / mes en curso), validación de rango, render de tarjetas y desglose, badge de tipo de venta, aviso de `costo_incompleto`, estados vacío/sin sucursal/error/403, botón Limpiar.
- Sidebar: oculta submenús sin permiso y oculta el grupo cuando no queda ninguno.

**¿E2E con Playwright? No.** Son pantallas de solo lectura sin formulario de varios pasos ni flujo crítico de escritura; la integración frontend–backend queda cubierta por los tests de API (contrato y permisos) y los specs de componentes con `HttpTestingController`. Playwright no está instalado en el proyecto y agregarlo sería una dependencia nueva sin beneficio proporcional.

**Verificación manual en vivo (obligatoria antes de publicar, práctica del proyecto para cambios de negocio/autorización):** con la base de desarrollo, tomar 3-4 ventas reales (con y sin instalación, con descuento, una con lote repartido) y comparar a mano cobrado/costo/utilidad contra el reporte; entrar como Admin, como Caja y como Vendedor en dos sucursales; confirmar que Caja no ve Utilidad ni recibe costos en la respuesta de red; confirmar que no hay botón ni URL de borrado en los admins.

## Acceptance criteria

- [ ] Existe una sola implementación del cálculo (`business/reportes.py`); API y ambos admins la usan; ninguna fórmula duplicada.
- [ ] Solo ventas cobradas; fecha del pago; `Cobrado = pago.monto`; `Bruto − Descuento = Cobrado` por venta y en los totales.
- [ ] Utilidad = venta de lámina − costo de compra, mostrada antes y después de descuento; instalación aparte, sin entrar en la utilidad.
- [ ] Costo correcto con líneas repartidas entre varias filas de inventario y con ventas anteriores a #52 (fallback); `costo_incompleto` visible en fila y tarjeta cuando falte.
- [ ] Desgloses por tipo de venta (con/sin instalación), por tipo de pago y por lámina; tarjetas y fila de resumen coinciden con la suma de las filas.
- [ ] Ventas Diarias: Admin y Caja (200); Utilidad: solo Admin (403 a los demás); la respuesta de Ventas Diarias no contiene costos ni márgenes.
- [ ] Alcance por sucursal: Admin todas; resto todas las suyas; sin sucursal → aviso; sucursal ajena → 404.
- [ ] Rango obligatorio, máx. 366 días, 400 ante parámetros inválidos.
- [ ] Django Admin: solo lectura real (sin agregar, cambiar ni borrar), sin los errores documentados (proforma sin ítems, typo de ordenamiento, filtro duplicado, default de fecha).
- [ ] Panel: menú "Reportes" con submenús filtrados por permiso, pantallas según el DDR, estados de carga/error/vacío/403.
- [ ] `asignar_permisos_reportes` ejecutado (con `--dry-run` previo) y documentado como paso por ambiente.
- [ ] Suite backend, `makemigrations --check`, `npm test`, `npm run build` y lint sin fallos nuevos; verificación manual en vivo hecha y anotada en el TASK.

## Risks

- **Cifras distintas a las que se veían** (por diseño: la utilidad baja al restar el costo). Mitigación: comunicarlo; comparación manual con ventas reales antes de publicar.
- **Utilidad sobreestimada donde falte el costo de compra** (`precio_compra_mtr_lineal` tiene default 0). Mitigación: `costo_incompleto` explícito; no se puede corregir desde el reporte.
- **Tratamiento del descuento (íntegro contra lámina) y de la instalación (aparte)** son decisiones de negocio; si cambian, se modifican en un solo módulo. Sin mitigación adicional.
- **Fallback legado con datos previos a #52** puede no reflejar de qué lote salió realmente cada metro; se marca `costo_incompleto` si falta el dato.
- **Rendimiento con rangos grandes** (sin paginación server-side): mitigado por el tope de 366 días y las consultas constantes; sin mitigación si el volumen real lo supera.
- **Permisos no asignados en un ambiente** → 403 para usuarios legítimos: mitigado con el comando y el paso explícito en despliegue.
- **Nombres reales de grupos** (`Admin`/`admin`, `Caja`) o de los permisos proxy pueden diferir de lo asumido: se verifica en el paso 2 y en la prueba en vivo.
- **Base de trabajo:** la rama parte de `origin/master` con #52 integrado; si otro PR toca `inventario.py`/`orden_estado.py` antes del merge, hay que rebasar.
- **Django Admin sin ordenamiento por columnas calculadas:** se acepta (las columnas de base de datos siguen ordenables).

## Out of scope

- Exportación (CSV/Excel/PDF), gráficos, paginación server-side.
- Filtro por fecha en el "Reporte Utilidades" del Django Admin (se ve acumulado por lote; el período está en el panel).
- Prorrateo del descuento entre lámina e instalación; costo de compra de la instalación.
- Unificar el alcance por sucursal del resto de los admins (`PagosAdmin`, `ReportStorageAdmin`, etc.), que siguen con el criterio legado.
- Dar los reportes a otros grupos (Vendedor u otros): es solo asignar permisos como datos.
- Corregir o cargar `precio_compra_mtr_lineal` faltante en el inventario histórico.

**Preguntas abiertas:** ninguna bloqueante. Se asume (ya reflejado en los ADR) que el descuento va íntegro contra la utilidad de lámina; avísanos si prefieres otro criterio antes de implementar.

## Dependencias nuevas

Ninguna (sin Playwright, sin datepicker ni librería de gráficos).
