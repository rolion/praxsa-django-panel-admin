# TASK-modulo-ordenes-proforma-nota-trabajo: Módulo Órdenes (Proformas y Notas de Trabajo) en el panel admin

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-modulo-ordenes-proforma-nota-trabajo
**Pull Request:** [#50](https://github.com/rolion/praxsa-django-panel-admin/pull/50)

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-09-29 | (nuevo) → INVESTIGATION | Task creado | delivery-investigate |
| 2026-09-29 | INVESTIGATION → ARCHITECTURE (via DESIGN) | Diseño de UI resuelto en DDR (listados, formularios por tipo de venta, acciones Generar nota de trabajo y PDF); veredicto de complejidad exige decisiones de API, lógica de precios y alcance por rol | delivery-design |
| 2026-09-29 | ARCHITECTURE → PLANNING | Decisiones tomadas en 2 ADR: API `ordenes/*` nueva con cálculo server-side reutilizando `Pricing_Business` (form del admin intacto, tests de paridad), y alcance por sucursal + permisos Django por acción con `permissions` en el login del panel | delivery-architect |
| 2026-09-29 | PLANNING → ENGINEERING | Plan v1 escrito y PR abierto; queda pendiente de aprobación humana antes de implementar | delivery-plan |
| 2026-09-29 | ENGINEERING → REVIEW | Implementación completa (backend + frontend) según Plan v1; suite backend y specs propios en verde, `ng build`/`ng lint` limpios. Verificación manual en vivo (V2) pendiente | delivery-engineer |
| 2026-09-29 | REVIEW → REVIEW | Ajuste pedido por el usuario tras ver el formulario: detalle de proforma como tabla de una fila por línea con el total alineado bajo Subtotal (DDR actualizado). Solo template/TS del formulario y su spec | usuario |
| 2026-09-29 | REVIEW → REVIEW | Rediseño visual del formulario de proforma pedido por el usuario (tarjetas por sección, íconos, campos bloqueados en gris, alertas amarilla/roja por línea, resumen de totales a la derecha). Solo presentación (HTML/SCSS y texto del aviso de ancho); DDR actualizado | usuario |
| 2026-09-29 | REVIEW → REVIEW | Vista de proforma: el detalle pasa a `ngx-datatable` con Total, Descuento y Total a pagar en la fila de resumen bajo Subtotal (pedido del usuario; DDR actualizado). Solo presentación de `proforma-view` | usuario |
| 2026-09-29 | REVIEW → REVIEW | Rediseño de "Ver proforma" pedido por el usuario: tarjetas (venta, cliente, vehículo, detalle), grid etiqueta/valor, fecha `dd/MM/yyyy - HH:mm h`, badge de estado, totales con Total a pagar destacado y barra de acciones jerarquizada (DDR actualizado). Solo presentación | usuario |
| 2026-09-29 | REVIEW → REVIEW | Metro lineal: el modelo de vehículo pasa a mostrarse como opcional y se guarda si se elige; panel colapsable de medidas de referencia del modelo (solo lectura, con copiar medida) en el formulario; Ver proforma muestra el modelo si existe. Pedido del usuario; DDR actualizado. Sin cambios de API (2 tests backend nuevos que fijan el comportamiento) | usuario |

## Investigación

### Requerimiento

Agregar al menú lateral de `panel_admin/` un grupo **"Órdenes"** con dos submenús: **Proforma** y **Nota de Trabajo**. Antes de implementar, investigar cómo `praxsa_manager` (backend Django) gestiona hoy esas dos órdenes y replicarlas en el panel admin.

Para Proformas se pide:
- Una tabla con la lista de todas las proformas, con botones de acción **Ver** (ver la proforma) y **Editar** (modificar la proforma).
- Una proforma puede ser de 2 tipos: **venta con instalación** y **venta por metro lineal**.
- *Venta con instalación*: el cálculo se hace en base al item de automóvil y la lámina seleccionada.
- *Venta por metro lineal*: no se selecciona automóvil ni item; solo se especifica la lámina que se necesita y la cantidad de metros.

Para Nota de Trabajo el pedido solo dice que es el segundo submenú; no especifica qué pantallas/acciones debe tener (ver "Preguntas abiertas").

### Hechos encontrados

**Modelos (todos existen y están en producción; no hay migraciones nuevas evidentes).** Todo en `praxsa_manager/product/models.py`:
- `Proforma_Header` (`models.py:164-192`): `sales_type` (choices `venta_instalacion` / `venta_metro_lineal`, default instalación), `origen` (`cal`/`port`), `proforma_created_on` (**`auto_now=True`**, o sea se pisa en cada `save()`), datos del cliente (`name`, `email`, `ci_nit`, `phone_number`), `car_plate`, `sucursal` (FK **nullable**), `discount` + `discount_reason`, `car_model_id` (FK **nullable**), `total_price`, `is_delete` (borrado lógico), `created_by` (FK a `User`, obligatorio), `is_close`, `status` (`proforma`/`nota_trabajo`/`por_cobrar`/`finalizado`, `helper/proforma.py:10-19`).
- `Proforma_Detail` (`models.py:245-263`): FK `proforma_header` (`related_name='items'`), `window_film`, `car_part` (**nullable**), `width`, `length`, `quantity`, `sub_total`, `installation_price`, `window_film_price`, `inventario` (FK nullable; se asigna al crear la nota de trabajo).
- `Nota_trabajo` (`models.py:200-218`): `OneToOne` a `Proforma_Header` (nullable), `codigo_garantia` (único), `entrada_vehiculo`/`salida_vehiculo`, `observaciones`, `instaladar` (FK a `instalador`), `responsable` (FK a `User`), copia de `name`/`car_plate`/`car_model`, `is_close`. Su resumen es `Detalle_Nota_Trabajo` (`models.py:220-235`: lámina + ancho + largo agregados).
- `Nota_Venta` (`models.py:266-282`, OneToOne a `Nota_trabajo`) y `pago` (OneToOne a `Nota_Venta`, `models.py:286-317`) completan el pipeline que alimenta `status`.

**Ciclo de vida actual (solo existe en Django Admin + `Proforma_Business`).** Proforma → "crear/actualizar nota trabajo" → nota de venta → pago:
- `Proforma_Business.create_work_note` (`business/proforma.py:96-138`): en una transacción, valida ancho de lámina vs. item (solo `venta_instalacion`, `validate_proforma_detail`, líneas 84-94), **descuenta inventario** por cada detalle (`Inventario_Business.reduce_inventory`, `business/inventario.py:52-70`, lanza `NoHayLaminasDisponibles`), guarda `detalle.inventario`, agrupa en un resumen por (lámina, ancho de bobina), marca `proforma.is_close = True` y delega en `Orden_Trabajo_Business.create_work_note` (`business/orden_trabajo.py:97-124`), que crea la `Nota_trabajo` (o la reutiliza si ya existía) copiando nombre/placa/modelo de la proforma y guardando el `responsable`.
- `Proforma_Business.abrir_proforma` (`business/proforma.py:61-82`): revierte inventario y `is_close=False`.
- `Orden_Trabajo_Business.delete_work_note` (`business/orden_trabajo.py:61-95`): bloquea si ya existe `Nota_Venta`; si no, devuelve inventario, reabre la proforma y recalcula `status`.
- `Proforma_Business.refresh_status` (`business/proforma.py:28-48`): `proforma` → `nota_trabajo` (existe `nota_trabajo`) → `por_cobrar` (existe `nota_venta`) → `finalizado` (existe `pago`).
- `Proforma_Business.crear_nota_venta` (`business/proforma.py:199-221`): exige proforma cerrada y, para `venta_instalacion`, `codigo_garantia` e `instaladar`.
- `Proforma_Business.convertir_venta_metro_lineal` (`business/proforma.py:141-186`): convierte una proforma abierta de instalación a metro lineal, agrupando detalles por (lámina, ancho).

**Cómo se crean/editan hoy las proformas: solo por Django Admin.** `ProformaAdmin` (`admin_config/proforma_admin.py:59-274`) usa `SaleHeaderForm` + inline `SalesDetailInLine` con `CarModelPartForm` (`Forms/car_model_part.py`). Reglas visibles:
- Cabecera: `sales_type`, `sucursal`, `total_price`, descuento, cliente, vehículo (`proforma_admin.py:113-141`). `sucursal` y `sales_type` pasan a solo-lectura al editar (`get_readonly_fields`, líneas 187-193); una proforma cerrada (`is_close`) es totalmente solo-lectura y `has_change_permission` devuelve `False` (líneas 153-158, 187-191).
- **`total_pagar = total_price - discount`** (`proforma_admin.py:86-89`; también en `crear_nota_venta`, `business/proforma.py:212`).
- El borrado es lógico (`is_delete = True`, `proforma_admin.py:199-222`) y bloqueado si ya existe nota de trabajo.
- Acciones disponibles hoy: abrir proforma, crear/actualizar nota de trabajo, imprimir (PDF, `helper/pdf.py:378`), convertir a metro lineal.

**Cálculo de precios, tipo `venta_instalacion`** (`Forms/car_model_part.py:66-110`, `business/pricing.py:27-31`):
- Requiere `car_part` + `window_film` + `width` + `quantity` ≥ 1 + `installation_price` ≥ 1; el ancho de la lámina debe ser ≥ ancho del item en `Car_Model_Part` (`item_width_lte_film_width`, líneas 47-49).
- El servidor **sobrescribe siempre** `installation_price` (de `Car_Model_Part.installation_price`), `window_film_price` (`Pricing_Business.resolve_unit_price`, `business/pricing.py:13-24`: `precio_venta_sucursal` con fallback a `inventario.precio_venta_mtr_lineal`) y `sub_total = length*quantity*unit_price + installation_price*quantity` (ADR-006; el navegador hace lo mismo, `static/product/sales_event.js:270-281`). Si no hay `Car_Model_Part` para (modelo, item) o no hay precio, el form falla con error de validación (líneas 87-98).
- El item trae por defecto `width`, `length`, `quantity`, `installation_price` desde `Car_Model_Part` (`views.py:65-152`, `sales_event.js:294-306`).

**Cálculo de precios, tipo `venta_metro_lineal`** (`Forms/car_model_part.py:112-137`, `business/pricing.py:34-39`):
- **No hay item (`car_part`)** ni `quantity` (el form rechaza `quantity > 0`) ni `installation_price` (rechaza > 0). Se requiere `window_film`, `width` y `length`.
- `sub_total = length * unit_price`, con `unit_price` resuelto igual que arriba (por sucursal, lámina y **ancho**). Ya cerrado como TASK-010 / PR #41.
- `Proforma_Header.car_model_id` no es obligatorio (`models.py:179`) y `Proforma_Detail.car_part` tampoco (`models.py:250`), coherente con lo que se pide.
- **`resolve_unit_price` filtra por `sucursal_id` y `bobina__width__gte=width`** (`business/inventario.py:92-126`) y devuelve `None` si el inventario no cubre el pedido: el `width` y la `sucursal` son necesarios para poder calcular el precio aunque el pedido diga solo "lámina y metros".

**Disponibilidad de inventario al armar la proforma.** `get_total_meters_window_film_in_inventory` (`business/inventario.py:92-126`) agrega metros disponibles (`to_install`) por lámina/ancho para una sucursal; `get_inventory` (`views.py:222-250`) lo expone públicamente. El descuento real ocurre recién al crear la nota de trabajo, no al guardar la proforma.

**API REST existente para proformas: no sirve para el panel admin tal cual.**
- `InvoiceView`/`ListUserInvoice` (`custom_views/invoice.py:15-104`, rutas en `urls.py:56-58`) usan `TokenAuthentication` + `IsAuthenticated` (sin `IsStaffUser`) y **filtran por `created_by = request.user`** — pensado para el cliente final de `proforma/`. No hay listado global ni edición (`put/patch`) ni endpoint de notas de trabajo.
- `SalesHeaderSerializer` (`serializer/invoice_serializer.py:28-88`) solo crea, y sólo calcula la fórmula de `venta_instalacion` (`validate`, líneas 37-71); exige `car_part` implícitamente vía `Car_Model_Part`. No contempla `venta_metro_lineal`.
- `InvoiceView.get` accede a `item.car_part.id` y `invoice.car_model_id.id` sin contemplar `None` (`invoice.py:41-42,62-64`); con una proforma de metro lineal fallaría con `AttributeError` (no capturado, solo se atrapan `ObjectDoesNotExist`/`MultipleObjectsReturned`) → 500.
- No existe ningún serializer, vista ni URL de panel admin para `Proforma_Header`, `Proforma_Detail`, `Nota_trabajo` ni `Detalle_Nota_Trabajo` (`urls.py:45-94`): todo el manejo hoy es Django Admin.

**Alcance por rol / sucursal (ya existente, inconsistente entre métodos).**
- `Proforma_Business.get_proforma_queryset_by_role` (`business/proforma.py:235-254`): grupo `'Admin'` (comparación **sensible a mayúsculas**) ve todas las no borradas; el resto solo las de su primera sucursal habilitada; sin sucursal → `None`.
- `Orden_Trabajo_Business.get_nota_queryset_by_role` (`business/orden_trabajo.py:18-30`): **no** tiene bypass de admin (solo sucursal del empleado; sin sucursal → `None`), a diferencia de `get_finish_nota_queryset` (líneas 32-47), que sí usa `User_Helper.can_view_all_sucursales` (`helper/user.py:28-29`, comparación case-insensitive con `'admin'`).
- Roles en el helper: `admin`, `instalador`, `supervisor`, `caja`, `almacen` (`helper/user.py:7-26`).

**Patrón de referencia en `panel_admin/` (mismo repo, módulos ya mergeados).**
- Menú: JSON estático `panel_admin/src/assets/data/routes.json` (grupos "Usuarios", "Vehículos", "Almacén" ya presentes, con `class: "menu-toggle"` y `submenu`).
- Rutas por módulo, ej. `panel_admin/src/app/almacen/almacen.routes.ts:12-22` (`laminas`, `laminas/create`, `laminas/view/:id`, `laminas/edit/:id`, …) más `*.service.ts`/`*.model.ts` por módulo.
- Backend de módulo: `custom_views/almacen_admin.py` / `vehicle_admin.py` con `TokenAuthentication` + `[IsAuthenticated, IsStaffUser, DjangoModelPermissions]` (`almacen_admin.py:17`), `?search=`, `?include_inactive=true` (líneas 29-36), `toggle-active` con `has_perm` explícito (líneas 47-65), URLs planas con `path()` (`urls.py:72-93`), y `ADR-modulo-almacen-permisos-rol-frontend` para diferenciar roles en frontend/backend.
- Sin paginación DRF global (`docs/backend-audit.md`, ver TASK-modulo-vehiculos); las tablas usan `ngx-datatable` client-side.

**Migraciones**: la última es `praxsa_manager/product/migrations/0110_inventario_is_active.py`. Con los modelos existentes no se ve necesidad de columnas nuevas (hipótesis abajo).

**Tests existentes en el área**: `product/tests/test_admin_price_recalculation.py`, `test_proforma_status_field.py`, `test_invoice_pricing.py`, `test_idor_invoice_and_proforma_car_part_info.py`, `test_sucursal_scope_admin.py` (aparecen en el conteo de referencias a `Proforma`/`Nota_trabajo` del código).

### Hipótesis / supuestos no confirmados

- "praxasa_manager" del pedido se interpreta como `praxsa_manager/` (backend Django); "menú de órdenes" con submenús "Proforma" y "Nota de Trabajo" como un grupo nuevo en `routes.json`, siguiendo a Usuarios/Vehículos/Almacén.
- No se ve necesidad de migraciones (los modelos ya cubren ambos tipos de venta), pero no se verificó contra todos los casos de UI.
- "Editar" una proforma en el panel debería respetar las mismas reglas que el Django Admin (solo si `is_close == False`; `sucursal` y `sales_type` inmutables tras crear). No lo dijo el usuario, es lo que el código hace hoy.
- "Ver la proforma" se asume como pantalla de detalle de solo lectura (cabecera + detalle + total con descuento). No se indicó si debe incluir imprimir/PDF (existe `PDFService`, `helper/pdf.py:378`), aunque no fue pedido.
- La tabla de Nota de Trabajo probablemente sea solo listado/vista (su alta ocurre desde una proforma), pero no está especificado (ver preguntas).
- No se verificó qué consumidores adicionales tienen `InvoiceView`/`ListUserInvoice` fuera de `proforma/`; se asume solo el frontend de cliente.
- No se ejecutó el sistema en vivo; todo lo anterior proviene de lectura de código.

### Preguntas abiertas (a resolver en diseño/plan; no se decidieron aquí)

1. **¿La proforma se puede crear desde el panel, o solo listar/ver/editar?** El pedido menciona lista + Ver + Editar, pero no "Crear". Sin crear desde el panel, no hay forma de mantener las 2 variantes desde ahí.
2. **Venta por metro lineal: ¿y el ancho de bobina?** El pedido dice "solo la lámina y los metros", pero el precio unitario se resuelve por (sucursal, lámina, **ancho**) y falla sin ancho/sucursal (`Forms/car_model_part.py:124-131`).
3. **¿Qué debe tener el submenú "Nota de Trabajo"?** ¿Listado + ver solamente? ¿Acciones (crear desde proforma, asignar instalador/garantía, imprimir, crear nota de venta)?
4. **¿Qué reglas de rol/sucursal aplicar?** Hoy hay 2 criterios distintos (con y sin bypass de admin, ver arriba) y dependen de nombres de grupo.
5. **¿"Eliminar" (borrado lógico) forma parte del alcance?** No se pidió, pero el Django Admin lo tiene (`is_delete`).
6. **¿Pasos de negocio como "crear nota de trabajo", "abrir proforma", "convertir a metro lineal"** deben exponerse en el panel? Impactan inventario.

### Módulos y dependencias relacionadas

- **Backend** (`praxsa_manager/product/`): `models.py`, `business/` (`proforma.py`, `orden_trabajo.py`, `pricing.py`, `inventario.py`), `Forms/car_model_part.py` (reglas de validación por `sales_type`), `admin_config/proforma_admin.py` y `nota_trabajo.py` (comportamiento de referencia), `serializer/invoice_serializer.py`, `custom_views/invoice.py`, `views.py` (endpoints de catálogo/inventario), `helper/proforma.py`, `helper/user.py`, `permissions.py`, `urls.py`.
- **Frontend `panel_admin/`**: `assets/data/routes.json` (menú), módulos nuevos análogos a `almacen/` y `vehicles/`, componente compartido de subida de imágenes en `shared/image-upload/` (no aplica aquí), reutilización de `vehicles.service.ts`/`almacen.service.ts` para catálogos (modelos, items, láminas).
- **Frontend `proforma/`** (Angular 16, cliente final): calcula el precio con la misma fórmula (`pages/formulario/formulario.component.ts:231-249`); no es parte del cambio, pero es consumidor de `InvoiceView`.
- **Módulos ya mergeados que este depende de**: Vehículos (Marcas/Modelos/Items, `Car_Model_Part`) y Almacén (Láminas/Bobinas/Inventario) — la venta con instalación consume ambos.

### Implementaciones similares existentes

- Los módulos **Vehículos** y **Almacén** de `panel_admin/` + sus vistas DRF (`vehicle_admin.py`, `almacen_admin.py`) son el patrón de referencia para CRUD/listado/permisos, incluida la relación padre-hijo (`CarModelItemsView`, `urls.py:79-80`).
- `SalesHeaderSerializer` (`serializer/invoice_serializer.py:28-88`) es la única implementación REST de creación de proforma con recálculo de precio en servidor (ADR-004), pero limitada a instalación.
- El Django Admin (`ProformaAdmin` + `CarModelPartForm`) contiene **todas** las reglas de negocio del flujo, incluida `venta_metro_lineal`; es la fuente de verdad del comportamiento hoy.

### Comportamiento actual

Hoy, quien quiere crear, editar o consultar proformas y notas de trabajo lo hace únicamente en Django Admin (`/admin/`), con lógica de negocio repartida entre `admin_config/`, `Forms/`, y `business/`. El panel admin nuevo (`panel_admin/`) no tiene ninguna pantalla ni API para estas entidades; el frontend `proforma/` solo permite al cliente crear (instalación) y ver *sus* proformas por API.

### Restricciones

- `docs/CLAUDE.md`: dinero siempre en `Decimal`, cambios de lógica de negocio con tests, no editar migraciones aplicadas, no agregar dependencias sin avisar, proponer plan antes de cambios multi-archivo, no inventar lo que no se pueda verificar (por eso las preguntas abiertas de arriba).
- ADR-004 / ADR-006 (precio nunca confiable desde el cliente; el servidor recalcula y sobrescribe siempre; ajustes manuales solo vía `discount`), extendido a metro lineal por TASK-010 / PR #41.
- La creación de nota de trabajo modifica inventario y cierra la proforma (`create_work_note`): cualquier exposición debe reutilizar `Proforma_Business` para no duplicar/divergir esa lógica.
- Permisos: patrón `IsStaffUser` + `DjangoModelPermissions` + filtrado por sucursal/rol del proyecto.

### Riesgos identificados

- **Lógica de negocio no reutilizable directamente desde REST**: el cálculo de precios vive dentro de `CarModelPartForm.clean()` (un `ModelForm` de admin, `Forms/car_model_part.py:52-147`); `SalesHeaderSerializer` solo replica instalación. Hay riesgo de duplicar y dejar divergir las fórmulas.
- **Divergencia de scope por rol** entre `get_proforma_queryset_by_role`, `get_nota_queryset_by_role` y `get_finish_nota_queryset` (case-sensitivity de `'Admin'`, presencia/ausencia de bypass de admin), ya descrita arriba.
- **Código con bugs latentes en el área** (solo observados, sin fix propuesto): `Proforma_Business.delete_proforma` usa `proforma.sales_status` (`business/proforma.py:51`), atributo que ya no existe en el modelo (`models.py:164-192`); el mensaje de error en ese método referencia `e` fuera de un `except` (líneas 58-59); `abrir_proforma` también usa `e` en una rama sin `except` (líneas 75-77); `CarModelPartForm.is_proforma_approved/installed` usan `sales_status` (`Forms/car_model_part.py:23-27`).
- **`proforma_created_on` con `auto_now=True`** (`models.py:168`): cada edición desde el panel movería la "fecha de la proforma", lo que puede sorprender al mostrarla en la tabla.
- **`InvoiceView.get` no soporta `venta_metro_lineal`** (500 por `car_part`/`car_model_id` nulos): reutilizarlo tal cual para el panel no es viable.
- **Concurrencia y transacciones sobre inventario** al crear/reabrir/eliminar notas de trabajo (`reduce_inventory` toma la primera bobina que cubra el pedido).
- **Sin paginación DRF global**: una tabla de "todas las proformas" crece sin límite (mismo riesgo señalado para catálogos en TASK-modulo-vehiculos).
- Sin tests de API de panel para estas entidades (no existen); la cobertura actual es de admin/forms/business.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — Es un módulo nuevo (dos entidades con cabecera/detalle, sin API de panel hoy), toca múltiples módulos (modelos, `business/`, `Forms/`, catálogos de Vehículos y Almacén) y su flujo tiene efectos transaccionales sobre inventario, recálculo de precios en servidor para dos tipos de venta con reglas distintas y alcance por rol/sucursal. Hay decisiones estructurales por tomar (dónde extraer la lógica de precios hoy atada a un `ModelForm` de admin, contrato de la API, qué operaciones del pipeline se exponen).

### Diseño requerido
**SI** — Pantallas nuevas (tabla de proformas, ver/editar con dos variantes de formulario según `sales_type`, más la vista de Nota de Trabajo), flujo condicional (campos de vehículo/item solo para instalación; lámina + metros para metro lineal) y consistencia visual con Vehículos/Almacén. El diseño va antes que arquitectura porque el contrato de API depende de qué edita cada pantalla.

## Diseño

Ver [DDR-modulo-ordenes-proforma-nota-trabajo-listado-y-flujo-ordenes](../design/DDR-modulo-ordenes-proforma-nota-trabajo-listado-y-flujo-ordenes.md).

Decisiones tomadas con el usuario (resuelven las preguntas abiertas 1, 2, 3 y 6 de la investigación):
- Proformas: listar, ver, editar **y crear** desde el panel.
- Bobina disponible en la sucursal como eje de la línea: al elegirla se carga el ancho; en venta con instalación, al elegir el item se precargan largo y cantidad y se calcula el subtotal. En metro lineal (sin vehículo ni item) la persona indica los metros.
- Nota de Trabajo: listado + Ver + Editar campos operativos; no se crea a mano.
- Acciones extra en la tabla de proformas: **Generar nota de trabajo** y **PDF**. Eliminar y Reabrir quedan fuera.

Pendiente para arquitectura: pregunta 4 (regla de rol/sucursal), contrato de API, cómo se exponen bobinas con stock y precios por sucursal, reutilización de la lógica de precios hoy en `CarModelPartForm`, y el PDF para metro lineal.

## Arquitectura

- [ADR-modulo-ordenes-proforma-nota-trabajo-api-y-calculo](../adr/ADR-modulo-ordenes-proforma-nota-trabajo-api-y-calculo.md): API REST nueva `ordenes/*` (sin tocar `InvoiceView`), línea identificada por (lámina, ancho) sin cambios de modelo, cálculo server-side reutilizando `Pricing_Business` con `CarModelPartForm` intacto (tests de paridad), reglas de edición/generación de nota/PDF, listados sin paginación servidor.
- [ADR-modulo-ordenes-proforma-nota-trabajo-alcance-permisos](../adr/ADR-modulo-ordenes-proforma-nota-trabajo-alcance-permisos.md): alcance por sucursal con métodos nuevos (legados intactos), 404 fuera de alcance, permisos Django por acción, y `permissions` efectivos en el login del panel para que la UI los use.

Sin migraciones. Sin cambios en `proforma/`. Cambio aditivo, reversible por `git revert`.

## Plan

[PLAN-2026-09-29-modulo-ordenes-proforma-nota-trabajo](../plans/PLAN-2026-09-29-modulo-ordenes-proforma-nota-trabajo.md) — **v1**. Backend (negocio, serializers, vistas, login con `permissions`) → frontend (auth, menú, servicio, pantallas) → verificación manual en vivo. Sin migraciones, sin dependencias nuevas, sin E2E automatizado (justificado en el plan). Pendiente de aprobación humana; preguntas abiertas: grupos que reciben cada permiso, `origen` de las proformas del panel, stock no bloqueante al guardar.

## Implementación

Implementado según el plan v1, sin desvíos de alcance ni arquitectura. Sin migraciones, sin dependencias nuevas.

**Backend** (`praxsa_manager/product/`)
- `business/pricing.py`: `Pricing_Business.get_reel_catalog`, `has_stock_for_reel` y `build_line_pricing` (reutiliza `resolve_unit_price` y las dos `calculate_subtotal_*`; `CarModelPartForm` intacto).
- Alcance: `Proforma_Business.get_panel_proforma_queryset`, `Orden_Trabajo_Business.get_panel_nota_queryset`, `User_Helper.get_enabled_sucursal_ids` / `get_sucursales_in_scope` (métodos legados intactos).
- `serializer/ordenes_serializer.py` y `custom_views/ordenes_admin.py`, rutas `ordenes/*` en `urls.py`; `permissions` en el login del panel.
- Tests: `test_ordenes_proformas.py`, `test_ordenes_notas_trabajo.py`, `test_ordenes_scope_permissions.py`, `test_ordenes_price_parity.py` (+ `ordenes_helpers.py`): 61 tests nuevos.

**Frontend** (`panel_admin/src/`)
- Menú "Órdenes" (`routes.json`), ruta lazy, `AuthService.hasPermission`, módulo `app/ordenes/` (servicio, modelos, cálculo de vista previa, listado/formulario único/vista de proformas, listado/vista/edición de notas) con specs.

**Detalles de implementación a tener en cuenta**
- El indicador de "sin sucursal" del listado es el catálogo `ordenes/catalogo/sucursales` vacío (el listado llega vacío y la UI lo consulta); el ADR hablaba de un "indicador" sin fijar el mecanismo.
- `NotaTrabajoListSerializer` expone además `sucursal_id` (la edición lo necesita para el catálogo de instaladores).
- `DELETE` sobre proforma/nota responde 403 (lo corta `DjangoModelPermissions`) o 405; no borra en ningún caso.
- Preguntas abiertas del plan tomadas con su valor por defecto: `origen` queda en `port`; el stock no bloquea el guardado; los permisos a grupos reales siguen pendientes (paso operativo V3).

**Deuda / observaciones (sin resolver aquí)**
- Orquestación de validación duplicada entre `CarModelPartForm` y `build_line_pricing` (tests de paridad como red).
- Un `Car_Model_Part.installation_price` en 0 (el formulario de Vehículos lo oculta y el default es 0) se acepta en la API con instalación 0; el `CarModelPartForm` del admin pedía `installation_price >= 1` sobre el valor enviado por el navegador. Conviene confirmar con negocio si un item con instalación 0 es válido.
- 15 specs de la plantilla (`should create` de Blank, Dashboard2, Sidebar, Footer, etc.) fallan por falta de provider de `ActivatedRoute`; no tocan archivos de este task.
- **No ejecutado**: la verificación manual en vivo (paso V2 del plan) contra backend real con usuarios de distintas sucursales/permisos; queda pendiente antes de dar el task por bueno.

## Review
_Pendiente_

## Publicación
_Pendiente_
