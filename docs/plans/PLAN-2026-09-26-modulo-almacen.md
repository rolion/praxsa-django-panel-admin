# PLAN-2026-09-26-modulo-almacen (v3)

**Task:** TASK-modulo-almacen
**DDRs relacionados:** [DDR-modulo-almacen-listado-y-flujo-almacen](../design/DDR-modulo-almacen-listado-y-flujo-almacen.md)
**ADRs relacionados:** [ADR-modulo-almacen-modelo-datos-imagen-soft-delete](../adr/ADR-modulo-almacen-modelo-datos-imagen-soft-delete.md), [ADR-modulo-almacen-permisos-rol-frontend](../adr/ADR-modulo-almacen-permisos-rol-frontend.md)

## Objective

Agregar el módulo Almacén (Láminas, Bobinas, Inventario) a `panel_admin/`, con permisos diferenciados por rol (`admin` CRUD completo, `almacen` solo lectura) validados en backend y reflejados en frontend, reutilizando en todo lo posible el patrón ya probado por `TASK-modulo-usuarios` y `TASK-modulo-vehiculos`. **v2**: Inventario pasa de "listado + Gestionar" a CRUD completo (Ver/Crear/Editar/Eliminar), al mismo nivel que Láminas/Bobinas. **v3**: corrige los 2 issues del Quality Gate (FAIL) — `nro_lote` pasa a obligatorio con sus validadores reales espejados en frontend y backend, y los 2 admins de Django que consumían `get_inventario_queryset_by_role` recuperan el mensaje que el cambio de contrato había silenciado — ver `## Changelog`.

## Context

Ver `## Investigación`, `## Diseño` y `## Arquitectura` de `TASK-modulo-almacen`. El plan v1 (Láminas, Bobinas, e Inventario con solo listado+"Gestionar") ya está implementado y pusheado al PR #49, verificado manualmente en navegador. Esa misma verificación manual (usuario real, grupos `admin`+`almacen`) encontró que el negocio necesita CRUD completo de Inventario — confirmado explícitamente por el usuario. El DDR y el ADR ya se actualizaron para definir el diseño y la arquitectura de esa ampliación; el plan v2 tradujo esas decisiones a pasos de implementación concretos, también ya implementados y pusheados.

**v3**: `delivery-review` corrió el Quality Gate sobre v2 y devolvió `FAIL` con 2 issues (ver `docs/tasks/TASK-modulo-almacen.md`, `## Review`, corrida 1):
- [REV-2026-09-27-modulo-almacen-01](../reviews/REV-2026-09-27-modulo-almacen-01.md) (High, IMPLEMENTATION) — `InventarioCreateSerializer` redeclara `nro_lote`/`numero_referencia` sin los `validators`/`max_length` del modelo, permitiendo que un `nro_lote` demasiado largo pase la validación del serializer y falle al guardar con una excepción de base de datos no controlada (`500` en vez de `400`). Al reportar este hallazgo, el usuario corrigió además una regla de negocio: **`nro_lote` es obligatorio** (el panel anterior ya lo exigía en la práctica, aunque el modelo lo declare `null=True`), y pidió que el frontend replique las validaciones del modelo, no solo `required` — ver la actualización de `ADR-modulo-almacen-modelo-datos-imagen-soft-delete.md` ("Corrección (2026-09-27)").
- [REV-2026-09-27-modulo-almacen-02](../reviews/REV-2026-09-27-modulo-almacen-02.md) (Medium, PLAN) — la investigación había declarado "sin otros consumidores" para `Inventario_Business.get_inventario_queryset_by_role`, pero existen 2 consumidores reales no detectados (`ReportStorageAdmin`, `ReportUtilidadAdmin`) cuyo mensaje "Asigne una sucursal al usuario" queda inalcanzable tras el cambio de contrato (`None` → `qs.none()`). El usuario eligió explícitamente la resolución: actualizar los 2 admins para que sigan mostrando el mensaje con el nuevo contrato, sin revertir el cambio en `Inventario_Business`.

Este plan v3 cubre exclusivamente estos 2 fixes — no reabre ninguna otra parte de v1/v2 ya aceptada.

## Current behavior

**Ya implementado (plan v1, en el PR #49)**:
- `Window_Film`/`Window_Film_Reel`: CRUD completo con imagen (Lámina) y soft-delete (`is_active`), páginas separadas (Lámina) o modal (Bobina) — sin cambios en v2.
- `inventario` (`praxsa_manager/product/models.py:138-146`): sin `is_active`. Expone hoy `GET almacen/inventario` (`custom_views/almacen_admin.py:115-133`, `InventarioListView(generics.ListAPIView)`, filtrado por sucursal vía `Inventario_Business.get_inventario_queryset_by_role`, sin filtro de estado) y `GET/PATCH almacen/inventario/<pk>/` (`InventarioUpdateView`, líneas 136-158, con `InventarioUpdateSerializer` acotado a 5 campos).
- `serializer/almacen_serializer.py:54-88`: `InventarioSerializer` (lectura, sin `is_active` porque el modelo no lo tiene todavía) e `InventarioUpdateSerializer` (los 5 campos editables).
- Frontend: `panel_admin/src/app/almacen/inventario/inventario-list.component.ts/html` — listado + modal inline "Gestionar" (mismo patrón que Bobina), sin Ver/Crear/Eliminar. `almacen.routes.ts:15` solo registra `{ path: 'inventario', component: InventarioListComponent }`. `almacen.model.ts:20-44` (`AppInventario` sin `is_active`, `InventarioUpdatePayload`) y `almacen.service.ts:111-118` (`listInventario`, `updateInventario`) sin métodos de creación/eliminación/detalle.

**Ya implementado (plan v2, en el PR #49, con 2 defectos encontrados por `delivery-review`)**:
- `serializer/almacen_serializer.py::InventarioCreateSerializer` redeclara `nro_lote` como `serializers.CharField(required=False, allow_null=True, allow_blank=True)` y `numero_referencia` como `serializers.IntegerField(required=False)` — ninguno de los dos hereda los `validators`/`max_length` que el campo del modelo `inventario` ya define (`nro_lote`: `max_length=15`, `validators=[alphanumeric]`; `numero_referencia`: `validators=[MaxValueValidator(9999999999)]`). Confirmado ejecutando el serializer (`REV-2026-09-27-modulo-almacen-01`): un `nro_lote` con guion pasa `is_valid()`, y uno de 50 caracteres pasa `is_valid()` pero falla al guardar con `value too long for type character varying(15)` (excepción de base de datos no controlada, no un `400`).
- `praxsa_manager/product/business/inventario.py::Inventario_Business.get_inventario_queryset_by_role` devuelve `qs.none()` en vez de `None` cuando el usuario no tiene sucursal (cambio de v1). `praxsa_manager/product/admin_config/report_storage.py:69` y `report_utilidad.py:52` tienen una rama `if base_qs is None:` que mostraba `self.message_user(..., 'Asigne una sucursal al usuario', level=messages.ERROR)` — con el nuevo contrato esa rama quedó inalcanzable (confirmado ejecutando `ReportStorageAdmin.get_queryset()` con un usuario sin sucursal: `qs.count() == 0`, pero `message_user` nunca se invoca). No hay ningún test que cubra este caso para ninguno de los 2 admins.

## Expected behavior

Además de lo ya implementado en v1 (sin cambios):
- Inventario gana Ver (detalle de solo lectura), Crear (formulario nuevo) y Eliminar (soft-delete restringido) para `admin`; `almacen` sigue viendo solo el listado y el detalle.
- "Eliminar" un Inventario solo es posible cuando `to_install == 0` — en cualquier otro caso, el backend responde `400` con un mensaje explícito, y el frontend lo muestra como error, no como éxito silencioso.
- Crear un Inventario exige sucursal, bobina (solo activas), cantidad, metros disponibles y ambos precios; el resto tiene default de servidor.
- Backend rechaza con `403` cualquier intento de `POST`/`PATCH toggle-active` de Inventario por un usuario sin `add_inventario`/`change_inventario`, igual que ya pasa con Lámina/Bobina.

**v3**:
- `POST almacen/inventario` sin `nro_lote` responde `400` (pasa a obligatorio). Con un `nro_lote` no alfanumérico o de más de 15 caracteres, responde `400` con un mensaje legible — nunca una excepción no controlada.
- El formulario de creación en Angular valida `nro_lote` (requerido, patrón alfanumérico, máximo 15 caracteres) **antes** de enviar el formulario, con el mismo criterio de "el frontend refleja las reglas del modelo" aplicado a cualquier campo futuro que las tenga.
- `POST almacen/inventario` con un `numero_referencia` mayor a 9999999999 responde `400` (recupera la validación perdida); sigue siendo opcional.
- Un usuario `is_staff` sin sucursal asignada (y sin rol `admin`) que entra a "Reporte Inventario" o "Reporte Utilidades" en el Django admin vuelve a ver el mensaje "Asigne una sucursal al usuario".

## Architecture considerations

Resumen operativo de la actualización de `ADR-modulo-almacen-modelo-datos-imagen-soft-delete.md` (ver el ADR completo para el detalle y las alternativas descartadas):

- **Modelo de datos**: `inventario` gana `is_active = models.BooleanField(default=True)`. Migración aditiva nueva (partiendo de `0109_window_film_image_is_active_window_film_reel_is_active.py`, la última real ya aplicada por v1).
- **Eliminar con protección real de integridad**: el `toggle-active` de Inventario **solo permite pasar a `is_active=False` cuando `to_install == 0`** — se verificó que toda la lógica de venta/instalación real (`business/inventario.py:33,57,87,93,132`) ya filtra `to_install__gt=0`/`to_install__gte=<algo positivo>`, así que una fila con `to_install == 0` ya es invisible para esa lógica de todos modos. Esto evita que "eliminar" desde el panel oculte stock que el sistema todavía pudiera vender, **sin tocar `Inventario_Business`** (código sensible y ya probado, fuera de alcance de este cambio).
- **Creación manual**: campos obligatorios `sucursal`, `bobina` (solo `is_active=True`, mismo criterio que el selector de Bobina→Lámina), `quantity`, `to_install`, `precio_compra_mtr_lineal`, `precio_venta_mtr_lineal`. Campos opcionales con default de servidor: `installed=0`, `original_length=to_install` (si se omite), `date=timezone.now()` (si se omite), `numero_referencia=0` (default ya del modelo), `nro_lote=None`.
- **Permisos**: el `toggle-active` de Inventario verifica `change_inventario` (no `delete_inventario`) — misma convención que todos los `toggle-active` ya implementados (`WindowFilmToggleActiveView`, `WindowFilmReelToggleActiveView`, ambos verifican `change_*`, no `delete_*`, porque la operación HTTP es un `PATCH` sobre un campo de estado). Esto significa que el grupo `admin` **ya tiene** el permiso que hace falta para "eliminar" Inventario (asignado desde v1); el único permiso operativo nuevo a asignar es `add_inventario` para poder crear.
- **Dinero**: igual que v1, todos los campos de precio usan `Decimal`/`serializers.DecimalField`, nunca `float`, incluyendo el default `original_length=to_install` (asignación directa de `Decimal`, no conversión).
- **Sin cambios** en `Inventario_Business`, en el contrato de `PATCH .../inventario/<pk>/` (Gestionar, ya acotado a 5 campos desde v1), ni en el resto del módulo (Láminas/Bobinas).

**v3 (ver `ADR-modulo-almacen-modelo-datos-imagen-soft-delete.md`, sección "Corrección (2026-09-27)")**:
- **`nro_lote` pasa a obligatorio** en `InventarioCreateSerializer`, con los mismos `validators=[alphanumeric]`/`max_length=15` que el campo del modelo — no una redeclaración plana. Principio general adoptado: cuando un campo del formulario tiene una regla de negocio ya codificada en `models.py`, el serializer de creación debe conservarla explícitamente (nunca asumir que basta con `required=True/False`), y el frontend debe espejarla en el `FormGroup` (no solo confiar en el rechazo del backend).
- **`numero_referencia` recupera `validators=[MaxValueValidator(9999999999)]`** en el serializer — sigue opcional (confirmado por el usuario), el cambio es solo restaurar la validación perdida.
- **`ReportStorageAdmin.get_queryset`/`ReportUtilidadAdmin.get_queryset`** cambian su chequeo de `if base_qs is None:` a una condición equivalente bajo el nuevo contrato de queryset vacío (p. ej. `if not base_qs.exists():`), sin tocar `Inventario_Business` — resolución elegida explícitamente por el usuario entre las 2 alternativas de `REV-2026-09-27-modulo-almacen-02` (la otra era revertir el contrato de `get_inventario_queryset_by_role`, descartada).

## Proposed solution

Backend: extender `InventarioSerializer` con `is_active` (read-only, misma razón que Lámina/Bobina), agregar `InventarioCreateSerializer` nuevo, convertir `InventarioListView` de `ListAPIView` a `ListCreateAPIView` (mismo patrón que `WindowFilmListCreateView`, serializer distinto por método), agregar `InventarioToggleActiveView` con la restricción `to_install == 0`.

Frontend: Inventario pasa del patrón "entidad simple" (modal, como Bobina) al patrón "entidad rica" (páginas separadas, como Lámina) — se agregan `inventario-create`, `inventario-view`, `inventario-edit` (esta última reemplaza el modal "Gestionar" ya implementado, migrándolo a página) y se reescribe `inventario-list` para navegar por rutas en vez de abrir un modal.

**v3**: corregir `InventarioCreateSerializer` (`nro_lote` obligatorio con sus validadores reales, `numero_referencia` recupera su validador), espejar esas mismas reglas en el `FormGroup` de `inventario-create.component.ts` y en el `<input>` de su template, y actualizar los 2 admins de Django (`report_storage.py`, `report_utilidad.py`) para que sigan mostrando su mensaje de error con el nuevo contrato de `get_inventario_queryset_by_role`.

## Files/components affected

**Backend (`praxsa_manager/product/`)**
- `models.py` — agregar `is_active` a `inventario`.
- `migrations/0110_inventario_is_active.py` — nueva, aditiva.
- `serializer/almacen_serializer.py` — `InventarioSerializer` gana `is_active` (read-only); `InventarioCreateSerializer` nuevo (campos de la tabla del ADR, `create()` con los defaults de servidor).
- `custom_views/almacen_admin.py` — `InventarioListView` pasa a `ListCreateAPIView` (`get_serializer_class` por método, filtro `is_active`/`?include_inactive=true`, mismo `?search=` ya existente); `InventarioToggleActiveView` nuevo (`has_perm('product.change_inventario')`, valida `to_install == 0` antes de desactivar).
- `urls.py` — agregar `almacen/inventario/<pk>/toggle-active/`.
- `tests/test_almacen_module.py` — casos nuevos de creación (campos obligatorios, defaults de servidor, bobina inactiva rechazada), `toggle-active` (bloqueado si `to_install > 0`, permitido si `== 0`, filtro `is_active`/`include_inactive` en el listado), y extender `AlmacenRolePermissionTest` con los casos nuevos (`almacen` recibe `403` en `POST`/`toggle-active` de Inventario; `admin` puede ambos).

**Frontend (`panel_admin/src/app/almacen/`)**
- `almacen.model.ts` — `AppInventario` gana `is_active: boolean`; `InventarioCreatePayload` nuevo.
- `almacen.service.ts` — `getInventario(id)`, `createInventario(payload)`, `toggleInventarioActive(id, isActive)`; `listInventario` ya soporta `includeInactive` (sin cambios); `listSucursales()` nuevo (reutiliza el endpoint ya existente `GET /product/sucursales` del módulo Usuarios, sin duplicar su CRUD).
- `almacen.routes.ts` — agregar `inventario/create`, `inventario/view/:id`, `inventario/edit/:id`.
- `inventario/inventario-list.component.ts/html` — se reescribe: quita el modal "Gestionar", agrega navegación a Ver/Crear/Editar (mismo layout que `laminas-list`), botón "Nuevo inventario", acción Eliminar con confirmación (SweetAlert2, mismo patrón que Lámina/Bobina) y manejo explícito del `400` cuando `to_install > 0`.
- `inventario/inventario-create.component.ts/html` — nuevo: formulario con selects de Sucursal y Bobina (solo activas) y los campos numéricos/fecha/lote.
- `inventario/inventario-view.component.ts/html` — nuevo: detalle de solo lectura, mismo layout `dl`/`dt`/`dd` que `lamina-view`.
- `inventario/inventario-edit.component.ts/html` — nuevo: migra el formulario "Gestionar" del modal actual a una página propia (mismos 5 campos, sin cambios de comportamiento).
- Specs: reescribir `inventario-list.component.spec.ts` (quita los casos de modal, agrega navegación/`canManage`, mismo patrón que `laminas-list.component.spec.ts`); specs nuevos para `inventario-create`/`inventario-view`/`inventario-edit` (mismo patrón que los de Lámina).

**v3 — Backend (`praxsa_manager/product/`)**
- `serializer/almacen_serializer.py` — `InventarioCreateSerializer`: `nro_lote` pasa a `serializers.CharField(required=True, max_length=15, validators=[alphanumeric])` (importar `alphanumeric` desde `..models`, ya definido ahí); `numero_referencia` gana `validators=[MaxValueValidator(limit_value=9999999999, message='solo se aceptan valores con 10 digitos')]` (mismo mensaje que el modelo).
- `admin_config/report_storage.py` — `ReportStorageAdmin.get_queryset`: cambiar `if base_qs is None:` por una condición que siga siendo verdadera bajo el nuevo contrato (`if not base_qs.exists():`), manteniendo el mismo `self.message_user(...)` y el mismo fallback (`qs.filter(sucursal=-1)`, ya redundante con un queryset vacío pero sin motivo para quitarlo en este fix acotado).
- `admin_config/report_utilidad.py` — mismo cambio en `ReportUtilidadAdmin.get_queryset`.
- `tests/test_almacen_module.py` — `InventarioCreateTest`: `nro_lote` ausente → `400`; `nro_lote` no alfanumérico (p. ej. `'L-999'`) → `400`; `nro_lote` de más de 15 caracteres → `400` (nunca una excepción de servidor); `numero_referencia` mayor a 9999999999 → `400`. Actualizar `test_create_with_required_fields_applies_server_defaults` (que hoy omite `nro_lote`) para incluirlo, ya que pasa a obligatorio.
- `tests/test_sucursal_scope_admin.py` (o un archivo nuevo si el patrón de request+messages no encaja ahí) — nuevo caso para `ReportStorageAdmin`/`ReportUtilidadAdmin`: usuario `is_staff` sin sucursal y sin rol `admin` → `get_queryset()` no lanza excepción, devuelve queryset vacío, y `messages.get_messages(request)` incluye el mensaje "Asigne una sucursal al usuario" con nivel `ERROR` (requiere adjuntar `django.contrib.messages.storage.fallback.FallbackStorage` a un `request` de `RequestFactory`, primer caso del proyecto que testea `message_user` — no hay un patrón previo que copiar).

**v3 — Frontend (`panel_admin/src/app/almacen/inventario/`)**
- `inventario-create.component.ts` — `nro_lote` pasa a `['', [Validators.required, Validators.pattern(/^[0-9a-zA-Z]*$/), Validators.maxLength(15)]]` en el `FormGroup`.
- `inventario-create.component.html` — el `<label>` de "Nro. lote" gana el asterisco `<span class="text-danger">*</span>` (mismo patrón visual que los demás campos obligatorios de este formulario), el `<input>` gana `maxlength="15"` y un mensaje de error bajo el campo cuando `invalid && touched` (mismo patrón que `name`/`description` en `lamina-create.component.html`).
- `inventario-create.component.spec.ts` — actualizar el test que crea con "los campos obligatorios" para incluir `nro_lote` (ya no puede omitirse sin que el formulario quede inválido); agregar un caso que confirme que el formulario es inválido con `nro_lote` vacío o con un valor no alfanumérico.

## Implementation steps

Continúa la numeración del plan v1/v2 (pasos 1-34 ya completados e implementados en el PR #49).

20. Migración: agregar `is_active` a `inventario`; correr `makemigrations`/`migrate` local; verificar `makemigrations --check --dry-run` limpio.
21. `serializer/almacen_serializer.py`: agregar `is_active` (read-only) a `InventarioSerializer`; crear `InventarioCreateSerializer` con los campos obligatorios/opcionales del ADR y los defaults de servidor (`installed=0`, `original_length=to_install` si se omite, `date=timezone.now()` si se omite), `bobina` restringida a `is_active=True`.
22. `custom_views/almacen_admin.py`: convertir `InventarioListView` a `ListCreateAPIView` (`get_serializer_class` por método, filtro `is_active=True` por defecto + `?include_inactive=true`); agregar `InventarioToggleActiveView` (`has_perm('product.change_inventario')`, `400` explícito si `to_install != 0` al desactivar, sin restricción al reactivar).
23. `urls.py`: agregar `path('almacen/inventario/<int:pk>/toggle-active/', InventarioToggleActiveView.as_view())`.
24. Tests backend: creación (obligatorios, defaults, bobina inactiva rechazada con `400`), `toggle-active` (bloqueado con `to_install > 0`, permitido con `== 0`, reactivar sin restricción), filtro `is_active`/`?include_inactive=true` en el listado, extender `AlmacenRolePermissionTest` (403 para `almacen` en `POST`/`toggle-active` de Inventario, 200/201 para `admin` con `add_inventario`/`change_inventario`).
25. Correr `python manage.py test` completo y `makemigrations --check --dry-run` antes de pasar a frontend.
26. Frontend: `almacen.model.ts` (`is_active`, `InventarioCreatePayload`) y `almacen.service.ts` (`getInventario`, `createInventario`, `toggleInventarioActive`, `listSucursales`).
27. `almacen.routes.ts`: agregar las 3 rutas nuevas de Inventario.
28. Reescribir `inventario-list.component.ts/html`: layout de `laminas-list` (botón "Nuevo inventario", columna Acciones con Ver/Editar/Eliminar condicionadas a `canManage`), quitar el modal y su `FormGroup` de "Gestionar" del propio listado.
29. Construir `inventario-create.component.ts/html` (selects de Sucursal/Bobina activa, campos numéricos/fecha/lote).
30. Construir `inventario-view.component.ts/html` (detalle de solo lectura).
31. Construir `inventario-edit.component.ts/html` (migra el formulario del modal actual, mismos 5 campos).
32. Specs: reescribir el de `inventario-list`, agregar los de `inventario-create`/`view`/`edit`.
33. Correr `ng build`, `ng lint`, `ng test` completos.
34. Verificación manual end-to-end en navegador: como `admin`, crear un Inventario nuevo, verlo, gestionarlo, intentar eliminarlo con `to_install > 0` (debe fallar con mensaje claro), bajar `to_install` a `0` vía "Gestionar" y recién ahí eliminarlo con éxito; como `almacen`, confirmar que no ve ninguna de las 3 acciones nuevas y que un `POST`/`toggle-active` directo devuelve `403`. Asignar `add_inventario` al grupo `admin` de prueba (paso operativo, ver Risks) antes de esta verificación.

**v3 — fixes de `delivery-review` (REV-2026-09-27-modulo-almacen-01 y -02)**

35. `serializer/almacen_serializer.py`: en `InventarioCreateSerializer`, cambiar `nro_lote` a `required=True` con `max_length=15` y `validators=[alphanumeric]` (reutilizar el `alphanumeric` ya definido en `..models`, no redefinirlo); agregar `validators=[MaxValueValidator(limit_value=9999999999, message='solo se aceptan valores con 10 digitos')]` a `numero_referencia` (mismo mensaje que el modelo, importar `MaxValueValidator` de `django.core.validators`).
36. `tests/test_almacen_module.py`: actualizar `test_create_with_required_fields_applies_server_defaults` para incluir `nro_lote` (ya no se puede omitir); agregar `test_create_without_nro_lote_returns_400`, `test_create_with_invalid_nro_lote_format_returns_400`, `test_create_with_nro_lote_too_long_returns_400` (confirmar que responde `400`, no una excepción), `test_create_with_numero_referencia_too_large_returns_400`.
37. `admin_config/report_storage.py` y `admin_config/report_utilidad.py`: cambiar `if base_qs is None:` por `if not base_qs.exists():` en ambos `get_queryset`, sin tocar el resto del método.
38. Test nuevo (en `tests/test_sucursal_scope_admin.py` o un archivo dedicado si el patrón de `messages` no encaja bien ahí) para ambos admins: usuario `is_staff` sin sucursal y sin rol `admin` → `get_queryset()` devuelve queryset vacío sin excepción, y el mensaje "Asigne una sucursal al usuario" (nivel `ERROR`) sí se agrega al request (vía `django.contrib.messages.storage.fallback.FallbackStorage` sobre un `request` de `RequestFactory`).
39. Correr `python manage.py test` completo (verificar que los tests existentes de `test_sucursal_scope_admin.py` que sí pasan sucursal/rol admin siguen en verde, sin regresión).
40. Frontend: `inventario-create.component.ts` — agregar `Validators.pattern(/^[0-9a-zA-Z]*$/)` y `Validators.maxLength(15)` a `nro_lote`, junto con `Validators.required` (reemplaza `['']`); `inventario-create.component.html` — agregar el asterisco de obligatorio al label, `maxlength="15"` al input, y el mensaje de error condicional (mismo patrón que `name`/`description`).
41. `inventario-create.component.spec.ts`: actualizar el test de creación exitosa para incluir `nro_lote`; agregar un caso que confirme `form.invalid` con `nro_lote` vacío y con un valor no alfanumérico.
42. Correr `ng build`, `ng lint`, `ng test` completos.
43. Verificación manual: intentar crear un Inventario sin lote (el botón "Crear inventario" debe quedar deshabilitado, sin llegar a pegarle al backend) y con un lote inválido (mismo resultado); confirmar que un usuario sin sucursal en el Django admin (`/admin/product/inventario_proxy/` o `/admin/product/utilidades/`) vuelve a ver el mensaje "Asigne una sucursal al usuario".

## Test strategy

**Backend (unitario/integración)** — mismos niveles y patrón que v1 (`praxsa_manager/product/tests/test_almacen_module.py`):
- Creación: campos obligatorios ausentes → `400`; defaults de servidor aplicados correctamente (`installed=0`, `original_length=to_install`, `date` ≈ ahora si se omite); bobina inactiva rechazada en el selector (`400`, mismo patrón que `test_inactive_lamina_not_offered_as_choice_for_new_bobina`).
- Eliminar: `to_install > 0` → `400` con mensaje explícito, la fila sigue `is_active=True`; `to_install == 0` → `200`, fila queda `is_active=False`; reactivar (`is_active=True`) sin restricción.
- Listado: filtra `is_active=True` por defecto, `?include_inactive=true` las muestra todas — mismo patrón que Lámina/Bobina.
- Permisos: `almacen` (sin `add_inventario`/`change_inventario` nuevos si aplica) recibe `403` en `POST` y en `toggle-active`; `admin` con esos permisos puede ambos — extiende `AlmacenRolePermissionTest` ya existente.

**Frontend (unitario, Angular `TestBed`)**: specs de los 3 componentes nuevos siguiendo el patrón ya usado por los de Lámina (`lamina-create.component.spec.ts`, `lamina-view.component.spec.ts` si existiera, `lamina-edit.component.spec.ts`) — carga de selects (Sucursal/Bobina), envío del formulario de creación con los campos obligatorios, manejo del error `400` de "Gestionar"/Eliminar, y el spec reescrito de `inventario-list` cubriendo `canManage` y la navegación a las 3 rutas nuevas (mismo patrón que `laminas-list.component.spec.ts`).

**E2E: sigue sin corresponder**, mismo motivo que v1 (no es un flujo crítico de punta a punta, Playwright no instalado) — la ampliación de Inventario es del mismo tipo de cambio (CRUD administrativo) que ya se decidió no requiere E2E. La verificación manual del paso 34 cubre el riesgo de integración real que un test aislado no puede validar (en particular, que el `400` de "no se puede eliminar con stock" se vea como error legible en la UI, no como una operación silenciosamente fallida).

**v3**: mismo criterio, sin corresponder E2E — son 2 fixes acotados (validación de un campo, un mensaje de admin de Django), no un flujo nuevo. Nivel unitario/integración en ambos lados alcanza: los 4 tests backend nuevos (`test_create_without_nro_lote_returns_400`, etc.) cubren exactamente el caso que causaba el `500` no controlado, y el test de `messages` cubre exactamente la rama que quedó inalcanzable — ambos son la evidencia mínima suficiente de que el fix funciona, sin necesitar un test de más alto nivel.

## Acceptance criteria

Además de las ya cumplidas por v1/v2 (ver PR #49):
- [ ] Migración de `inventario.is_active` aplicada, `makemigrations --check --dry-run` sin cambios pendientes.
- [ ] `admin` puede crear una fila de Inventario nueva (con los campos obligatorios) y verla en el listado.
- [ ] `admin` puede ver el detalle de solo lectura de una fila de Inventario.
- [ ] Intentar eliminar una fila de Inventario con `to_install > 0` falla con un mensaje claro, sin cambiar el estado de la fila.
- [ ] Eliminar una fila de Inventario con `to_install == 0` la oculta del listado por defecto (sigue en la base de datos, visible con `?include_inactive=true`).
- [ ] `almacen` no ve ninguna acción de Crear/Editar/Eliminar en el listado de Inventario, y un intento directo de `POST`/`toggle-active` devuelve `403` (verificado con test automático).
- [ ] `python manage.py test` completo en verde; `ng build`/`ng lint`/`ng test` sin errores nuevos.
- [ ] **(v3)** `POST almacen/inventario` sin `nro_lote`, con `nro_lote` no alfanumérico, o con `nro_lote` de más de 15 caracteres responde `400` con un mensaje legible — nunca una excepción no controlada (verificado con test automático, no solo manual).
- [ ] **(v3)** `POST almacen/inventario` con `numero_referencia` mayor a 9999999999 responde `400`.
- [ ] **(v3)** El formulario de creación de Inventario en Angular no permite enviar sin `nro_lote` o con un valor inválido (botón deshabilitado, mismo patrón que los demás campos obligatorios).
- [ ] **(v3)** Un usuario sin sucursal asignada en "Reporte Inventario"/"Reporte Utilidades" del Django admin ve el mensaje "Asigne una sucursal al usuario" (verificado con test automático, no solo manual).
- [ ] **(v3)** Los 2 issues de la corrida 1 de `delivery-review` (`REV-2026-09-27-modulo-almacen-01`, `-02`) quedan `Resolved`, verificado de forma independiente en la corrida 2.

## Risks

- **Permiso operativo nuevo (`add_inventario`)**: el grupo `admin` de cada ambiente necesita este permiso asignado para poder crear Inventario — no se automatiza (mismo criterio que el resto de permisos del módulo). Mitigación: documentado explícitamente en el PR y en el paso 34 de verificación manual, para no asumir que ya está configurado en ningún ambiente.
- **Restricción `to_install == 0` para eliminar podría resultar muy estricta en la práctica** (p. ej. el negocio quiere eliminar un lote dañado con stock residual, sin pasar primero por "Gestionar" para poner `to_install=0`). Mitigación: es una condición de una línea en la vista, no un cambio de modelo ni de contrato — ajustable rápido si el negocio lo pide tras usar el módulo.
- **Migrar el modal de "Gestionar" a una página separada** cambia la experiencia de uso de algo que ya está implementado y verificado (v1). Mitigación: el endpoint `PATCH almacen/inventario/<pk>/` no cambia (mismos 5 campos, mismo serializer) — el riesgo es puramente de frontend/UX, no de contrato; se verifica con specs nuevos + la verificación manual del paso 34.
- **(v3) Filas de Inventario ya creadas antes de este fix con `nro_lote` inválido o vacío** (creadas mientras el bug de `REV-01` estaba presente, si el PR llegó a mergearse — no es el caso, sigue en review) — no aplica en este momento porque el defecto se corrige antes de mergear a `master`; si hipotéticamente ya hubiera datos así en algún ambiente, este plan no incluye una migración de datos para corregirlos retroactivamente (fuera de alcance, no hay evidencia de que exista tal dato hoy).
- **(v3) El test nuevo de `messages` es el primero del proyecto que verifica `message_user`** — sin patrón previo que copiar, hay que armar el `request`+`FallbackStorage` a mano. Mitigación: es un patrón estándar de Django (documentado en su propia guía de testing de `contrib.messages`), no algo específico de este proyecto a inventar desde cero.

## Out of scope

- Guard de ruta por permiso en el frontend — sigue sin corresponder, mismo motivo que v1.
- Cascada de soft-delete — sigue sin aplicar a este módulo.
- Cualquier protección de integridad para eliminar más allá de `to_install == 0` (p. ej. bloquear si ya existe un `Proforma_Detail` histórico apuntando a la fila) — decisión explícita del ADR: no aplica, ver "Alternativas consideradas" ahí.
- Creación automática de permisos/grupos — sigue siendo configuración manual por ambiente.
- **(v3)** Cualquier otro campo del modelo `inventario` que pudiera tener una regla de validación no espejada en el frontend, más allá de `nro_lote`/`numero_referencia` — este plan corrige específicamente los 2 campos que `REV-01` encontró rotos, no hace una auditoría exhaustiva de los demás campos del formulario de creación (que ya declaran explícitamente sus propios `DecimalField`/`required=True` sin redeclaración plana problemática, ver `almacen_serializer.py`).
- **(v3)** Revertir el contrato de `get_inventario_queryset_by_role` — descartado explícitamente por el usuario, ver `## Context`.

## Dependencias nuevas

Ninguna — mismo motivo que v1/v2, esta corrección no introduce ninguna librería nueva.

## Changelog
- **v2** (2026-09-27): Inventario se amplía de "listado + Gestionar" a CRUD completo (Ver/Crear/Editar/Eliminar), tras verificación manual real que confirmó la necesidad de negocio. Motivado por hallazgo del usuario durante pruebas manuales del PR #49 (ver historial de `TASK-modulo-almacen`), formalizado en la actualización de `docs/design/DDR-modulo-almacen-listado-y-flujo-almacen.md` y `docs/adr/ADR-modulo-almacen-modelo-datos-imagen-soft-delete.md`.
- **v3** (2026-09-27): Corrige 2 issues de la corrida 1 de `delivery-review` (Quality Gate `FAIL`) — `InventarioCreateSerializer` recupera los `validators`/`max_length` del modelo en `nro_lote` (que además pasa a obligatorio, corrección de regla de negocio pedida directamente por el usuario) y `numero_referencia`; `ReportStorageAdmin`/`ReportUtilidadAdmin` recuperan el mensaje "Asigne una sucursal al usuario" bajo el nuevo contrato de `get_inventario_queryset_by_role`. Solicitado por `delivery-review`, referenciando `REV-2026-09-27-modulo-almacen-01` (High, IMPLEMENTATION) y `REV-2026-09-27-modulo-almacen-02` (Medium, PLAN).
