# PLAN-2026-09-29-modulo-ordenes-proforma-nota-trabajo (v2)

**Task:** TASK-modulo-ordenes-proforma-nota-trabajo
**DDRs relacionados:** [DDR-modulo-ordenes-proforma-nota-trabajo-listado-y-flujo-ordenes](../design/DDR-modulo-ordenes-proforma-nota-trabajo-listado-y-flujo-ordenes.md)
**ADRs relacionados:** [ADR-modulo-ordenes-proforma-nota-trabajo-api-y-calculo](../adr/ADR-modulo-ordenes-proforma-nota-trabajo-api-y-calculo.md), [ADR-modulo-ordenes-proforma-nota-trabajo-alcance-permisos](../adr/ADR-modulo-ordenes-proforma-nota-trabajo-alcance-permisos.md)

## Objective

Agregar a `panel_admin/` el grupo de menú **Órdenes** (Proforma, Nota de Trabajo): tabla de proformas con Ver / Editar / Generar nota de trabajo / PDF, alta y edición de proformas de los dos tipos de venta (con instalación y metro lineal), y listado/ver/edición operativa de Notas de Trabajo, sobre una API REST nueva con cálculo de precios server-side y alcance por sucursal/permisos.

**v2**: el plan v1 ya está implementado. Esta versión recoge los ajustes de interfaz pedidos por el usuario después de ver las pantallas (rediseño del formulario, de "Ver proforma" y de "Ver nota de trabajo", modelo opcional en metro lineal, edición in-situ de la nota) tal como quedaron implementados; el detalle de cada decisión está en las "Actualización 1 a 7" del DDR. No cambia la API, los ADR ni el alcance de backend. Ver `## Changelog`.

## Context

Ver `## Investigación`, `## Diseño` y `## Arquitectura` de `TASK-modulo-ordenes-proforma-nota-trabajo`. Hoy todo esto solo existe en Django Admin (`ProformaAdmin`, `NotaTrabajoAdmin`) y en `Proforma_Business`. El plan traduce los 2 ADR y el DDR a pasos; no reabre sus decisiones.

Verificado contra el código actual antes de planificar (nada cambió respecto a la investigación):
- Última migración `0110_inventario_is_active.py`; este plan **no agrega migraciones**.
- `vehicles/models/<id>/items/` sí devuelve `installation_price`, `width`, `length`, `quantity` por item (`serializer/vehicle_serializer.py:92-122`, `custom_views/vehicle_admin.py:172-192`); su `GET` no exige permiso de modelo (`_STANDARD_PERMISSIONS`, solo `IsStaffUser`). El ocultamiento del precio de instalación es solo del formulario de Vehículos, no de la API. **Nota:** ese endpoint no filtra por `Car_Part.is_active`; el formulario de Órdenes debe filtrar/validar items inactivos (ver paso B4).
- `AuthService` ya tiene `hasGroup` (`panel_admin/src/app/core/service/auth.service.ts:69-72`) y el login ya devuelve `groups`/`is_staff` (`custom_views/auth_token.py:47-55`); falta `permissions`.
- Rutas lazy por módulo en `panel_admin/src/app/app.routes.ts:45-54` (`vehicles`, `almacen`).
- Lección de `REV-2026-09-27-modulo-almacen-01`: un serializer que **redeclara** un campo del modelo pierde sus `validators`/`max_length`. Regla para este plan: los campos del modelo (`name`, `email`, `ci_nit`, `phone_number`, `car_plate`, `codigo_garantia`, …) **no se redeclaran** salvo que se copien sus validadores; y el frontend espeja las reglas del modelo, no solo `required`.
- `inventario` ya tiene `is_active` y solo se puede desactivar con `to_install == 0` (TASK-modulo-almacen), así que filas inactivas no aportan metros disponibles.

## Current behavior

- Proformas y notas de trabajo se crean/editan/consultan solo en `/admin/` (`admin_config/proforma_admin.py:59-274`, `admin_config/nota_trabajo.py:46-181`).
- La API REST de proformas (`custom_views/invoice.py:15-104`) es del cliente final: filtra por `created_by`, solo crea `venta_instalacion` (`serializer/invoice_serializer.py:37-71`) y no soporta metro lineal en `GET`.
- No hay serializer/vista/URL de panel para `Proforma_Header`, `Proforma_Detail`, `Nota_trabajo` ni `Detalle_Nota_Trabajo` (`urls.py:45-94`). El menú del panel tiene Usuarios, Vehículos y Almacén (`assets/data/routes.json`).
- El alcance por sucursal legado usa `'Admin'` sensible a mayúsculas y `sucursales[0]` (`business/proforma.py:235-254`, `business/orden_trabajo.py:18-30`).

## Expected behavior

- Menú lateral "Órdenes" → "Proforma" y "Nota de Trabajo".
- **Proforma / listado** (`/ordenes/proformas`): todas las proformas dentro del alcance del usuario, con búsqueda cliente y acciones Ver, Editar, Generar nota de trabajo y PDF según estado y permisos.
- **Crear/Editar proforma**: formulario por tipo de venta. Instalación: modelo + placa + líneas con item, bobina (lámina+ancho con stock en la sucursal), largo y cantidad precargados desde el item. Metro lineal: líneas con bobina y metros, sin item/modelo. Total y total a pagar visibles como vista previa; el servidor devuelve los importes definitivos.
- **Generar nota de trabajo**: confirma, descuenta inventario, cierra la proforma y pasa su estado a "Nota Trabajo".
- **PDF** de la proforma descargable.
- **Nota de Trabajo**: listado, ver (con resumen de láminas) y edición de instalador, código de garantía, salida y observaciones.
- Todo protegido en servidor por staff + permisos Django + alcance por sucursal (404 fuera de alcance).

## Architecture considerations

Resumen de los ADR (no se re-decide nada):
- **API separada** `ordenes/*` con `TokenAuthentication` + `IsAuthenticated` + `IsStaffUser` (+ `DjangoModelPermissions` en alta/edición); `InvoiceView`, `SalesHeaderSerializer` y `CarModelPartForm` **no se tocan**.
- **Sin cambios de modelo**; línea identificada por (lámina, ancho exacto).
- **Dinero**: todo en `Decimal`/`serializers.DecimalField`, cuantizado a 2 decimales con `ROUND_HALF_UP` como ya hace el form (`Forms/car_model_part.py:105-110`); nunca `float`. Los importes viajan como strings en JSON (comportamiento por defecto de `DecimalField`). El preview del frontend usa números JS solo como vista previa no autoritativa, redondeada a 2 decimales.
- **Cálculo**: el servidor ignora precios/subtotales/total del cliente y sobrescribe (ADR-004/006, TASK-010), con `Pricing_Business.resolve_unit_price` y las dos funciones `calculate_subtotal_*` existentes.
- **Alcance/permisos**: métodos nuevos de alcance (legados intactos), 404 fuera de alcance, permisos `add/change_proforma_header`, `add/change_nota_trabajo`, y `permissions` efectivos en el login del panel.
- **Rendimiento**: listados con `select_related` y serializer liviano (sin líneas); detalle con `prefetch`/`select_related` de líneas; catálogo de bobinas con una consulta agregada por sucursal (sin N+1 por lámina). Sin paginación servidor (riesgo aceptado, ver Risks).
- **Concurrencia**: `select_for_update` sobre la proforma al generar la nota; la carrera sobre filas de `inventario` en `reduce_inventory` es preexistente y queda fuera.
- **Acoplamiento**: el catálogo de bobinas agrega filas de `get_total_meters_window_film_in_inventory`, que agrupa también por `precio_venta_mtr_lineal` (`business/inventario.py:105-126`), por lo que puede devolver varias filas para la misma (lámina, ancho) con distinto precio; ver paso B3 y Risks.

## Proposed solution

Implementar en el orden backend → login/permisos → frontend, con cada paso verificable. Backend con una capa de negocio pequeña (función de precio por línea + métodos de alcance) y vistas/serializers delgados; frontend siguiendo los patrones de Almacén (`ngx-datatable`, cards, `ReactiveFormsModule`, SweetAlert2), con **un único componente de formulario** de proforma reutilizado para crear y editar (a diferencia de Almacén, que tiene create/edit separados: aquí el formulario condicional con líneas es la pieza compleja y duplicarla dos veces sería el mayor riesgo de divergencia).

## Files/components affected

**Backend (`praxsa_manager/product/`)**
- Nuevo `custom_views/ordenes_admin.py`, nuevo `serializer/ordenes_serializer.py`.
- `business/pricing.py` (función nueva de precio por línea), `business/proforma.py` (método de alcance), `business/orden_trabajo.py` (método de alcance), `business/inventario.py` (método de catálogo de bobinas), `helper/user.py` (ids de sucursales del usuario).
- `custom_views/auth_token.py` (campo `permissions`), `urls.py` (rutas `ordenes/*`).
- Tests nuevos: `tests/test_ordenes_proformas.py`, `tests/test_ordenes_notas_trabajo.py`, `tests/test_ordenes_scope_permissions.py`, `tests/test_ordenes_price_parity.py`; ampliar `tests/test_panel_admin_auth.py`.
- **No se modifican**: `models.py`, `Forms/*`, `admin_config/*`, `custom_views/invoice.py`, `serializer/invoice_serializer.py`, `helper/pdf.py`.

**Frontend (`panel_admin/src/`)**
- `assets/data/routes.json` (grupo "Órdenes"), `app/app.routes.ts` (ruta lazy `ordenes`).
- `app/core/models/user.ts` y `app/core/service/auth.service.ts` (+ spec): `permissions`, `hasPermission`.
- Nuevo módulo `app/ordenes/`: `ordenes.routes.ts`, `ordenes.model.ts`, `ordenes.service.ts` (+ spec), `proformas/proformas-list.component.*`, `proformas/proforma-form.component.*` (crear y editar), `proformas/proforma-view.component.*`, `notas-trabajo/notas-trabajo-list.component.*`, `notas-trabajo/nota-trabajo-view.component.*` (lectura y edición in-situ; la ruta `edit/:id` abre esta misma vista en modo edición, **ya no hay componente de edición separado**), estilos globales acotados por clase raíz en `assets/scss/_ordenes.scss` (importado desde `assets/scss/style.scss`; **no** son estilos de componente, por el presupuesto `anyComponentStyle` de `angular.json`, ver REV-01) (+ specs).

## Implementation steps

### Fase 1 — Backend: negocio

- **B1. `helper/user.py`**: `get_enabled_sucursal_ids(user)` → ids de sucursales con `enable_to_install_windows_film=True` de las que el usuario es empleado. Sin cambios en los métodos existentes.
- **B2. Alcance**:
  - `Proforma_Business.get_panel_proforma_queryset(user, qs)`: si `User_Helper.can_view_all_sucursales(user)` → `qs.filter(is_delete=False)`; si no → `qs.filter(is_delete=False, sucursal_id__in=<ids>)`; sin sucursales → `qs.none()`. `select_related('sucursal','car_model_id','car_model_id__car_brand_id','nota_trabajo')` cuando aplique.
  - `Orden_Trabajo_Business.get_panel_nota_queryset(user, qs)`: mismo criterio sobre `proforma__sucursal_id` y `proforma__is_delete=False`, con `select_related('proforma','proforma__sucursal','instaladar','car_model','responsable')`.
  - `Inventario_Business`/nuevo helper `get_sucursales_in_scope(user)` para el catálogo de sucursales (admin: todas las habilitadas; resto: sus ids).
- **B3. Catálogo de bobinas** `Inventario_Business.get_reel_catalog(sucursal_id)`: consulta sobre `inventario` de esa sucursal (`is_active=True`, `to_install > 0`, lámina y bobina activas) agrupada por (lámina, ancho) con `Sum('to_install')`; para cada par, `unit_price` sale de `Pricing_Business.resolve_unit_price(sucursal_id, lamina_id, width)` (misma fuente que usará el alta, así el preview coincide con lo que persiste el servidor aun si hay filas con distinto `precio_venta_mtr_lineal`). Devuelve `[{window_film, window_film_name, width, available_meters, unit_price}]`, `Decimal`.
- **B4. `Pricing_Business.build_line_pricing(sales_type, car_model, sucursal, line)`** en `business/pricing.py`: recibe los datos crudos de una línea y devuelve `{installation_price, window_film_price, sub_total}` (cuantizados) o lanza `ProformaException` con mensaje legible:
  - Común: `length > 0`; lámina activa; (lámina, ancho) presente en `get_reel_catalog(sucursal)` con ancho **exacto**; precio resoluble.
  - `venta_instalacion`: `car_part` obligatorio, activo y con `Car_Model_Part` para `car_model`; `quantity >= 1`; ancho de bobina ≥ ancho del item; `installation_price` desde `Car_Model_Part`; subtotal con `calculate_subtotal_venta_instalacion`.
  - `venta_metro_lineal`: `car_part` nulo, `quantity` 0/ausente; `installation_price = 0`; subtotal con `calculate_subtotal_venta_metro_lineal`.
  - Las fórmulas **no se reescriben**: solo se llaman las existentes.
- **B5. Serializers** (`serializer/ordenes_serializer.py`), sin redeclarar campos del modelo salvo copiando validadores:
  - Lectura: `ProformaListSerializer` (id, sales_type, name, sucursal id/name, car_model name/brand, `total_price`, `discount`, `total_a_pagar = total_price - discount`, `proforma_created_on`, `status`, `is_close`, `nota_trabajo_id`), `ProformaDetailSerializer` (+ cliente, vehículo, `discount_reason`, líneas con nombres de item/lámina), `NotaTrabajoListSerializer`, `NotaTrabajoDetailSerializer` (+ resumen `Detalle_Nota_Trabajo`, líneas de la proforma, sucursal, responsable).
  - Escritura de proforma: cabecera (`sales_type`, `sucursal`, `name`, `email`, `ci_nit`, `phone_number`, `car_plate`, `car_model_id`, `discount`, `discount_reason`) + `items` anidados (`car_part`, `window_film`, `width`, `length`, `quantity`). `total_price`, `sub_total`, `installation_price`, `window_film_price`, `created_by`, `status`, `is_close`, `is_delete` son **de solo lectura/ignorados**. Reglas: ≥1 línea; sucursal en alcance; instalación exige `car_model_id` (activo) y `car_plate`; descuento ≤ 50 % del total recalculado y con motivo si > 0 (`Forms/Sale_header.py:13-33`); campos requeridos como en el admin (`name`, `email`, `ci_nit`, `phone_number`); `created_by = request.user`; `origen` queda en el default del modelo (`port`), igual que al crear desde el Django Admin (ver pregunta abierta 2).
  - `create()` y `update()` dentro de `transaction.atomic()`: guardar cabecera → (re)crear líneas con los importes de `build_line_pricing` → `Proforma_Business.recalculate_total_price`. `update()`: rechaza si `is_close`/`is_delete` (409), si `sales_type` o `sucursal` cambian (400); si no vienen `items`, no toca líneas pero revalida el descuento contra el total almacenado.
  - `NotaTrabajoUpdateSerializer`: solo `instaladar`, `codigo_garantia` (`''`→`None`, único, máx. 12), `salida_vehiculo`, `observaciones`; `instaladar` debe pertenecer a la sucursal de la proforma; rechaza con 409 si hay `nota_venta` (`is_close`).
- **B6. Vistas** (`custom_views/ordenes_admin.py`), patrón de `almacen_admin.py`:
  - `ProformaListCreateView`, `ProformaDetailView` (GET/PATCH, `http_method_names` sin `put`/`delete`), filtros `?search=` (id, nombre, placa, modelo), `?sales_type=`, `?status=`; queryset = alcance (B2); sin sucursal → respuesta vacía con un indicador que la UI convierte en "Asigne una sucursal al usuario".
  - `ProformaGenerateNotaView` (POST): `has_perm('product.add_nota_trabajo')`; objeto desde queryset con alcance; en `transaction.atomic()` + `select_for_update()` de la proforma; 409 si `is_close`; llama `Proforma_Business.create_work_note(proforma, request.user)`; mapea `NoHayLaminasDisponibles`/`ProformaException` → 409/400 con mensaje, resto → 500 genérico; responde con el detalle actualizado de la proforma.
  - `ProformaPdfView` (GET): alcance; 409 con mensaje si no hay `sucursal`; `PDFService.create_proforma(detail=…, header=…)` igual que `proforma_admin.py:263-273`; `FileResponse(as_attachment, filename='proforma-<id>.pdf')`.
  - `NotaTrabajoListView`, `NotaTrabajoDetailView` (GET/PATCH, `DjangoModelPermissions` sobre `Nota_trabajo`).
  - `OrdenesSucursalesView`, `OrdenesBobinasView` (`?sucursal=` obligatorio y dentro del alcance, si no 404/403), `OrdenesInstaladoresView` (`?sucursal=`).
- **B7. `urls.py`**: rutas del ADR (`ordenes/proformas`, `ordenes/proformas/<int:pk>/`, `…/generar-nota-trabajo/`, `…/pdf/`, `ordenes/notas-trabajo`, `ordenes/notas-trabajo/<int:pk>/`, `ordenes/catalogo/sucursales|bobinas|instaladores`).
- **B8. Login**: `PanelAdminAuthToken` agrega `permissions: sorted(user.get_all_permissions())`; los campos existentes no cambian.

### Fase 2 — Frontend: infraestructura

- **F1. Auth**: `User` gana `permissions?: string[]`; `PanelAdminLoginResponse.permissions`; `AuthService.hasPermission(codename)` (acepta `add_proforma_header` o `product.add_proforma_header`); spec ampliado. Usuarios ya logueados sin `permissions` (sesión antigua en `localStorage`) → los botones dependientes se ocultan hasta volver a iniciar sesión (los endpoints siguen protegidos).
- **F2. Menú y rutas**: grupo "Órdenes" en `routes.json` (icono feather, `menu-toggle`, submenús `/ordenes/proformas` y `/ordenes/notas-trabajo`, `ml-menu`); `app.routes.ts` ruta lazy `ordenes` → `ORDENES_ROUTE`.
- **F3. Modelo y servicio** (`ordenes.model.ts`, `ordenes.service.ts`): tipos, listados, alta/edición, `generarNotaTrabajo(id)`, `downloadProformaPdf(id)` (`responseType: 'blob'`, disparo de descarga con `URL.createObjectURL`), notas, catálogos. Importes como `string`. Manejo de errores DRF (`{campo: [msg]}` y `{detail}`) reutilizando el helper que use Almacén.

### Fase 3 — Frontend: pantallas

- **F4. Proformas / listado**: `ngx-datatable` + `filterDatatable`, columnas del DDR, botones `btn-tbl-view`/`btn-tbl-edit`, botón Generar nota (ícono propio, visible si `!is_close && hasPermission('add_nota_trabajo')`, confirmación SweetAlert2) y PDF; Editar visible si `!is_close && hasPermission('change_proforma_header')`; "Nueva proforma" si `hasPermission('add_proforma_header')`. Refresca la fila tras generar nota; muestra `errorMessage`/estado "sin sucursal".
- **F5. Proforma / formulario (crear y editar)**: un componente con `FormGroup` + `FormArray` de líneas. *(v2: presentación rediseñada, ver DDR Actualizaciones 1, 2 y 5.)*
  - Layout: cinco tarjetas (Venta, Cliente, Vehículo, Detalle de items, Descuento y totales) con encabezado e ícono, inputs con íconos y bordes redondeados, campos bloqueados en gris con candado (tipo de venta y sucursal al editar; ancho, precios y subtotal), botones primario "Crear proforma" y secundarios "Cancelar" / "Agregar item".
  - Cabecera: tipo de venta (bloqueado en edición), sucursal (select con las del alcance; una sola → fija), cliente (validadores espejo del modelo: `EmailValidator`, patrón teléfono `(\+)*\d{7,11}`, CI/NIT `\d*`, placa máx. 10, nombre máx. 400), descuento y motivo (motivo requerido si descuento > 0; descuento ≤ 50 % del total en vista previa).
  - Al cambiar de sucursal: recarga catálogo de bobinas y limpia líneas incompatibles (con aviso).
  - Detalle: **tabla de una fila por línea** (instalación: Item, Lámina (bobina), Ancho, Largo, Cantidad, Precio lámina, Instalación, Subtotal; metro lineal: sin Item, Cantidad ni Instalación) con el **Total al pie alineado bajo Subtotal**. Alertas por línea: roja "Ancho insuficiente: mínimo requerido X m" y amarilla de stock. Resumen a la derecha con Total, Descuento y Total a pagar destacado.
  - Instalación: modelo (select, activos, con marca, obligatorio) → carga items (`vehicles/models/:id/items/`); por línea: item → precarga largo y cantidad; bobina (lámina + ancho) → precio y ancho.
  - Metro lineal: **el modelo es opcional** ("(Opcional)", se envía y guarda si se elige; no cambia el precio), sin item; por línea bobina + metros; muestra metros disponibles como tope orientativo (el servidor no bloquea, ver ADR). Cambiar de tipo de venta conserva el modelo elegido.
  - Panel colapsable de solo lectura **"Medidas de referencia del modelo"** (cualquier tipo de venta, al elegir un modelo con items): tabla Item / Ancho requerido / Largo sugerido con botón "Copiar medida" (copia "ancho x largo" al portapapeles).
  - Vista previa de subtotal/total/total a pagar con la misma fórmula (instalación: `largo×cantidad×precio + instalación×cantidad`; metro lineal: `metros×precio`), 2 decimales; tras guardar se muestran los importes definitivos devueltos.
  - Modo edición: precarga desde `GET ordenes/proformas/:id`; si `is_close` muestra aviso y redirige a la vista. Errores del servidor por campo/línea en `alert-danger`.
- **F6. Proforma / ver** *(v2, DDR Actualizaciones 3 y 4)*: tarjetas Datos de venta, Datos del cliente, Datos del vehículo (Marca/Modelo también en metro lineal si existen) y Detalle de items, con grid etiqueta gris / valor en negrita; fecha `dd/MM/yyyy - HH:mm h`; badge de estado (azul Proforma, verde Nota de trabajo generada, ámbar Por cobrar, verde oscuro Finalizado); detalle en **`ngx-datatable`** con Total, Descuento y Total a pagar (recuadro destacado) en la fila de resumen bajo Subtotal; acciones: "Editar" (secundario), "Generar nota de trabajo" (verde), "Descargar PDF" (neutro) y "Volver al listado".
- **F7. Notas de trabajo** *(v2, DDR Actualizaciones 6 y 7)*: listado (columnas del DDR, Ver, Editar oculto si finalizada o sin `change_nota_trabajo`). Vista con el mismo sistema visual que "Ver proforma": tarjetas Datos de la orden, Datos del cliente y vehículo, Control operativo y tiempos; badge "En ejecución" / "Finalizado"; vacíos tenues ("Sin código", "Aún no registrada", "No asignado", "Sin observaciones"); tablas `ngx-datatable` Resumen de láminas usadas y Detalle de la proforma. **Edición in-situ**: "Editar nota de trabajo" convierte en inputs código de garantía (máx. 12, único; el modelo no define otro validador, `models.py:202`), instalador (select por sucursal de la proforma), salida del vehículo (`datetime-local`) y observaciones (textarea); el resto queda en lectura; barra inferior "Cancelar" (restaura los valores originales) / "Guardar cambios". La ruta `notas-trabajo/edit/:id` abre la misma vista en modo edición.
- **F8. Specs** de servicio y componentes (ver Test strategy).

### Fase 4 — Verificación

- **V1.** Suite backend completa y `makemigrations --check --dry-run` (debe reportar sin cambios); `ng test`, `ng build`, `ng lint` en `panel_admin/`.
- **V2. Verificación manual en vivo** (no reemplazable por tests, ver Test strategy): backend con `runserver` y `panel_admin` con `ng serve`; usuarios reales: admin, empleado de sucursal A, empleado de sucursal B, usuario sin sucursal, usuario sin permisos.
- **V3.** Asignar los permisos `add/change_proforma_header`, `add/change_nota_trabajo` a los grupos reales que correspondan (paso operativo, no código) y repetir la verificación.

## Test strategy

**Backend (`python manage.py test`, patrón `tests/helpers.py`, `create_staff_user_with_token`, `grant_permission`, `build_full_scenario`)**
- *Paridad de precio (`test_ordenes_price_parity.py`)*: mismo escenario (modelo, item, lámina, inventario, `precio_venta_sucursal` con y sin override) calculado por `CarModelPartForm` y por el serializer → mismo `sub_total`, `window_film_price`, `installation_price`, ambos tipos.
- *Alta/edición*: instalación feliz (importes recalculados aun si el cliente manda otros); metro lineal feliz; metro lineal rechaza `car_part`/`quantity`; instalación rechaza item de otro modelo, `quantity=0`, ancho de bobina < ancho de item, sin `car_model_id`/`car_plate`; ancho no exacto → 400; sin stock/precio → 400 (no 500); lámina/modelo/item inactivos → 400; descuento > 50 % del total recalculado → 400; motivo requerido; `total_price` = suma de líneas; `Decimal` con 2 decimales; validadores heredados del modelo (email inválido, teléfono, placa > 10, nombre > 400 → 400, nunca 500).
- *Edición*: `sales_type`/`sucursal` inmutables (400); proforma cerrada → 409; reemplazo de líneas atómico (si una línea falla no se pierde el estado previo); PATCH solo de cabecera conserva líneas.
- *Generar nota*: descuenta inventario, `is_close=True`, `status='nota_trabajo'`, nota con `responsable`; segunda llamada → 409; sin stock → 409 y sin cambios parciales; sin permiso `add_nota_trabajo` → 403.
- *PDF*: `200`, `application/pdf`, ambos tipos (incluye metro lineal sin item ni modelo); proforma sin sucursal → 409.
- *Notas de trabajo*: listado/detalle; PATCH solo campos permitidos (otros ignorados/400); `codigo_garantia` duplicado → 400, vacío → `null`; instalador de otra sucursal → 400; con nota de venta → 409.
- *Alcance y permisos (`test_ordenes_scope_permissions.py`)*: admin (`admin` en minúsculas) ve todas; empleado de sucursal A no ve/edita/genera/PDF sobre proforma o nota de B (404); usuario con dos sucursales ve ambas; sin sucursal → lista vacía con indicador; usuario no staff → 403; sin token → 401; `is_delete` invisible; catálogos acotados al alcance (`?sucursal=` ajena → error).
- *Login*: `permissions` presente y correcto (superusuario, usuario con permiso asignado por grupo, sin permisos); campos previos intactos.
- *Regresión*: los tests existentes del admin/serializer del cliente (`test_admin_price_recalculation.py`, `test_invoice_pricing.py`, `test_proforma_status_field.py`, `test_idor_invoice_and_proforma_car_part_info.py`) siguen en verde sin modificación.

**Frontend (`ng test`, `TestBed` + `HttpTestingController`)**
- Servicio: URLs/métodos, `blob` del PDF, mapeo de errores.
- Listado: visibilidad de botones por estado y por permisos (`hasPermission`), confirmación y refresco al generar nota, mensaje "sin sucursal", búsqueda.
- Formulario: cambio de tipo de venta muestra/oculta campos; precarga de largo/cantidad al elegir item; carga de ancho al elegir bobina; cálculo de vista previa en ambos tipos; validadores espejo (email, teléfono, placa, motivo del descuento); modo edición precarga y bloquea tipo/sucursal; muestra errores del servidor.
- Notas: listado, vista, edición (campos y validaciones).
- `AuthService.hasPermission` y login con `permissions`.

**E2E (Playwright): NO corresponde en este plan.** Playwright no está instalado (ni en `proforma/` ni en `panel_admin/`) y agregarlo es una dependencia nueva que hay que confirmar antes; el flujo crítico se cubre con (a) tests de API de punta a punta del backend (crear → generar nota → PDF sobre datos reales de prueba) y (b) tests de componentes con `HttpTestingController`. Como el proyecto ya aprendió que los errores de requerimiento en cambios de autorización y de precios los captura la prueba real y no los tests automatizados (ADR-006 y la práctica de TASK-002/005), el paso **V2** es verificación manual obligatoria en navegador con backend real, y **debe ejecutarse antes de pasar a revisión**. Si el usuario prefiere E2E automatizado, se agrega como tarea aparte con confirmación de la dependencia.

## Acceptance criteria

1. El menú lateral muestra "Órdenes" con "Proforma" y "Nota de Trabajo".
2. La tabla de proformas lista todas las del alcance del usuario (admin: todas las sucursales), con Ver, Editar, Generar nota de trabajo y PDF según estado y permisos.
3. Se puede crear y editar una proforma **con instalación** (modelo, placa, items, bobina; largo y cantidad precargados; ancho desde la bobina) y una **por metro lineal** (solo bobina y metros, sin modelo ni item); el total guardado coincide con la fórmula de cada tipo y con lo que calcula el Django Admin para los mismos datos.
4. El servidor ignora cualquier precio/subtotal/total enviado por el cliente.
5. Una proforma cerrada no se puede editar ni volver a generar; `sales_type` y `sucursal` no cambian en edición.
6. "Generar nota de trabajo" crea la nota, descuenta inventario, cierra la proforma y actualiza el estado; con stock insuficiente muestra el mensaje y no deja cambios parciales.
7. El PDF se descarga para ambos tipos de venta.
8. Notas de Trabajo: listado, ver y editar solo instalador, código de garantía, salida y observaciones; no editable si ya tiene nota de venta.
9. Un usuario de la sucursal A no puede ver, editar, generar ni descargar PDF de datos de la sucursal B (404), aunque llame a la API directo; sin permiso Django el servidor responde 403; un usuario no staff no accede.
10. El login del panel devuelve `permissions` sin romper `groups`/`is_staff`; la UI oculta acciones según ellos.
11. Sin migraciones nuevas; `InvoiceView`, `CarModelPartForm` y el Django Admin siguen igual; toda la suite backend y frontend en verde; `ng build` y `ng lint` limpios.
12. Verificación manual V2 realizada y documentada en el PR.

## Risks

- **Divergencia de reglas entre form del admin y serializer**: mitigada con tests de paridad; deuda explícita de unificar después (ADR).
- **Filas de inventario con distinto `precio_venta_mtr_lineal` para la misma (lámina, ancho)**: el catálogo usa `resolve_unit_price` para que preview = servidor, pero el precio que "gana" depende del orden de la consulta preexistente. Se documenta y se cubre con un test; no se cambia esa lógica.
- **Generar nota de trabajo muta inventario**: reutiliza el mismo código que el admin (sin cambios), tras permiso explícito y con bloqueo de fila; la carrera sobre `inventario` es preexistente. Verificación manual con datos de prueba.
- **Permisos sin asignar a los grupos reales**: mientras no se asignen, solo superusuarios pueden crear/editar/generar (403 para el resto). Está en V3; mitigación operativa, no de código.
- **Sesiones antiguas sin `permissions` en `localStorage`**: los botones dependientes quedan ocultos hasta volver a loguearse; no hay riesgo de seguridad.
- **Alcance distinto entre panel y Django Admin** para usuarios con varias sucursales o grupo `Admin` con mayúscula: coexistencia aceptada (ADR); puede confundir a quien compare pantallas.
- **Sin paginación servidor**: la tabla de proformas crece sin límite; se acepta con disparador de revisión (miles de filas o lentitud perceptible). Mitigación futura: `?page`/`limit` y búsqueda en servidor.
- **`proforma_created_on` con `auto_now`** cambia al editar; la columna Fecha del listado mostrará la fecha del último guardado. Sin mitigación en este plan (requeriría migración).
- **Formulario de líneas con campos dependientes** es la pieza de mayor complejidad de UI; se cubre con specs de componente y la verificación manual V2.
- **Item inactivo**: `vehicles/models/:id/items/` no filtra por `is_active`; el formulario y el servidor deben rechazarlos (cubierto en B4 y tests).
- **Bugs latentes preexistentes** (`delete_proforma`, `abrir_proforma`, `InvoiceView.get` con metro lineal): no se tocan y no se exponen en este módulo.

## Out of scope

- Eliminar, Reabrir, Convertir a metro lineal y Crear nota de venta / pagos desde el panel.
- Crear notas de trabajo a mano; imprimir el PDF de la nota de trabajo.
- Paginación en servidor, filtros por rango de fechas.
- Cambiar `proforma_created_on`, unificar los criterios de alcance legado/nuevo, migrar `CarModelPartForm` a la función nueva, arreglar `InvoiceView.get`.
- Modificar el frontend `proforma/` o el Django Admin.
- E2E con Playwright (requeriría confirmar dependencia nueva).

**Preguntas abiertas para el usuario (no bloquean empezar, pero conviene confirmar):**
1. ¿Qué grupos reales deben recibir cada permiso (crear/editar proforma, generar nota, editar nota)? Este plan solo deja el mecanismo.
2. ¿Confirmas que `origen` de las proformas creadas desde el panel quede en el valor por defecto actual (`port`, Portal), sin agregar un valor nuevo "Panel"? Cambiarlo tocaría los `choices` del modelo (migración).
3. ¿Aceptas que el stock no bloquee el guardado de la proforma (solo se valida al generar la nota, como hoy)?

## Dependencias nuevas

Ninguna. SweetAlert2, `ngx-datatable` y Bootstrap ya están en `panel_admin/`. (Playwright no se instala en este plan.)

## Changelog
- **v2** (2026-09-30): se actualizan F5, F6, F7 y "Files/components affected" para reflejar lo implementado tras los ajustes de interfaz pedidos por el usuario después de ver las pantallas: formulario en tarjetas con detalle en tabla de una fila por línea y total bajo Subtotal; modelo de vehículo opcional en metro lineal con panel de medidas de referencia; "Ver proforma" con tarjetas, badge y `ngx-datatable` con resumen de totales; "Ver nota de trabajo" con el mismo sistema visual; edición in-situ de la nota (se elimina el componente `nota-trabajo-edit`). Solicitado por el usuario (no por `delivery-review`). Sin cambios en backend, API, ADR, migraciones ni dependencias; `## Test strategy` y los criterios de aceptación 1 a 12 siguen vigentes (los specs de frontend se ampliaron para los nuevos comportamientos).
- **v2 (nota de la corrida de review 1, 2026-09-30)**: sin cambio de alcance. Correcciones de implementación por REV-01 (estilos movidos a `assets/scss/_ordenes.scss` para que `ng build` de producción compile) y REV-02 (el catálogo de bobinas serializa strings y el frontend normaliza el ancho de la clave de bobina). Se actualiza solo la lista de archivos afectados.
- **v1** (2026-09-29): plan inicial.
