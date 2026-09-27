# PLAN-2026-09-26-modulo-almacen (v2)

**Task:** TASK-modulo-almacen
**DDRs relacionados:** [DDR-modulo-almacen-listado-y-flujo-almacen](../design/DDR-modulo-almacen-listado-y-flujo-almacen.md)
**ADRs relacionados:** [ADR-modulo-almacen-modelo-datos-imagen-soft-delete](../adr/ADR-modulo-almacen-modelo-datos-imagen-soft-delete.md), [ADR-modulo-almacen-permisos-rol-frontend](../adr/ADR-modulo-almacen-permisos-rol-frontend.md)

## Objective

Agregar el módulo Almacén (Láminas, Bobinas, Inventario) a `panel_admin/`, con permisos diferenciados por rol (`admin` CRUD completo, `almacen` solo lectura) validados en backend y reflejados en frontend, reutilizando en todo lo posible el patrón ya probado por `TASK-modulo-usuarios` y `TASK-modulo-vehiculos`. **v2**: Inventario pasa de "listado + Gestionar" a CRUD completo (Ver/Crear/Editar/Eliminar), al mismo nivel que Láminas/Bobinas — ver `## Changelog`.

## Context

Ver `## Investigación`, `## Diseño` y `## Arquitectura` de `TASK-modulo-almacen`. El plan v1 (Láminas, Bobinas, e Inventario con solo listado+"Gestionar") ya está implementado y pusheado al PR #49, verificado manualmente en navegador. Esa misma verificación manual (usuario real, grupos `admin`+`almacen`) encontró que el negocio necesita CRUD completo de Inventario — confirmado explícitamente por el usuario. El DDR y el ADR ya se actualizaron para definir el diseño y la arquitectura de esa ampliación; este plan v2 solo traduce esas decisiones a pasos de implementación concretos sobre el código ya existente.

## Current behavior

**Ya implementado (plan v1, en el PR #49)**:
- `Window_Film`/`Window_Film_Reel`: CRUD completo con imagen (Lámina) y soft-delete (`is_active`), páginas separadas (Lámina) o modal (Bobina) — sin cambios en v2.
- `inventario` (`praxsa_manager/product/models.py:138-146`): sin `is_active`. Expone hoy `GET almacen/inventario` (`custom_views/almacen_admin.py:115-133`, `InventarioListView(generics.ListAPIView)`, filtrado por sucursal vía `Inventario_Business.get_inventario_queryset_by_role`, sin filtro de estado) y `GET/PATCH almacen/inventario/<pk>/` (`InventarioUpdateView`, líneas 136-158, con `InventarioUpdateSerializer` acotado a 5 campos).
- `serializer/almacen_serializer.py:54-88`: `InventarioSerializer` (lectura, sin `is_active` porque el modelo no lo tiene todavía) e `InventarioUpdateSerializer` (los 5 campos editables).
- Frontend: `panel_admin/src/app/almacen/inventario/inventario-list.component.ts/html` — listado + modal inline "Gestionar" (mismo patrón que Bobina), sin Ver/Crear/Eliminar. `almacen.routes.ts:15` solo registra `{ path: 'inventario', component: InventarioListComponent }`. `almacen.model.ts:20-44` (`AppInventario` sin `is_active`, `InventarioUpdatePayload`) y `almacen.service.ts:111-118` (`listInventario`, `updateInventario`) sin métodos de creación/eliminación/detalle.

## Expected behavior

Además de lo ya implementado en v1 (sin cambios):
- Inventario gana Ver (detalle de solo lectura), Crear (formulario nuevo) y Eliminar (soft-delete restringido) para `admin`; `almacen` sigue viendo solo el listado y el detalle.
- "Eliminar" un Inventario solo es posible cuando `to_install == 0` — en cualquier otro caso, el backend responde `400` con un mensaje explícito, y el frontend lo muestra como error, no como éxito silencioso.
- Crear un Inventario exige sucursal, bobina (solo activas), cantidad, metros disponibles y ambos precios; el resto tiene default de servidor.
- Backend rechaza con `403` cualquier intento de `POST`/`PATCH toggle-active` de Inventario por un usuario sin `add_inventario`/`change_inventario`, igual que ya pasa con Lámina/Bobina.

## Architecture considerations

Resumen operativo de la actualización de `ADR-modulo-almacen-modelo-datos-imagen-soft-delete.md` (ver el ADR completo para el detalle y las alternativas descartadas):

- **Modelo de datos**: `inventario` gana `is_active = models.BooleanField(default=True)`. Migración aditiva nueva (partiendo de `0109_window_film_image_is_active_window_film_reel_is_active.py`, la última real ya aplicada por v1).
- **Eliminar con protección real de integridad**: el `toggle-active` de Inventario **solo permite pasar a `is_active=False` cuando `to_install == 0`** — se verificó que toda la lógica de venta/instalación real (`business/inventario.py:33,57,87,93,132`) ya filtra `to_install__gt=0`/`to_install__gte=<algo positivo>`, así que una fila con `to_install == 0` ya es invisible para esa lógica de todos modos. Esto evita que "eliminar" desde el panel oculte stock que el sistema todavía pudiera vender, **sin tocar `Inventario_Business`** (código sensible y ya probado, fuera de alcance de este cambio).
- **Creación manual**: campos obligatorios `sucursal`, `bobina` (solo `is_active=True`, mismo criterio que el selector de Bobina→Lámina), `quantity`, `to_install`, `precio_compra_mtr_lineal`, `precio_venta_mtr_lineal`. Campos opcionales con default de servidor: `installed=0`, `original_length=to_install` (si se omite), `date=timezone.now()` (si se omite), `numero_referencia=0` (default ya del modelo), `nro_lote=None`.
- **Permisos**: el `toggle-active` de Inventario verifica `change_inventario` (no `delete_inventario`) — misma convención que todos los `toggle-active` ya implementados (`WindowFilmToggleActiveView`, `WindowFilmReelToggleActiveView`, ambos verifican `change_*`, no `delete_*`, porque la operación HTTP es un `PATCH` sobre un campo de estado). Esto significa que el grupo `admin` **ya tiene** el permiso que hace falta para "eliminar" Inventario (asignado desde v1); el único permiso operativo nuevo a asignar es `add_inventario` para poder crear.
- **Dinero**: igual que v1, todos los campos de precio usan `Decimal`/`serializers.DecimalField`, nunca `float`, incluyendo el default `original_length=to_install` (asignación directa de `Decimal`, no conversión).
- **Sin cambios** en `Inventario_Business`, en el contrato de `PATCH .../inventario/<pk>/` (Gestionar, ya acotado a 5 campos desde v1), ni en el resto del módulo (Láminas/Bobinas).

## Proposed solution

Backend: extender `InventarioSerializer` con `is_active` (read-only, misma razón que Lámina/Bobina), agregar `InventarioCreateSerializer` nuevo, convertir `InventarioListView` de `ListAPIView` a `ListCreateAPIView` (mismo patrón que `WindowFilmListCreateView`, serializer distinto por método), agregar `InventarioToggleActiveView` con la restricción `to_install == 0`.

Frontend: Inventario pasa del patrón "entidad simple" (modal, como Bobina) al patrón "entidad rica" (páginas separadas, como Lámina) — se agregan `inventario-create`, `inventario-view`, `inventario-edit` (esta última reemplaza el modal "Gestionar" ya implementado, migrándolo a página) y se reescribe `inventario-list` para navegar por rutas en vez de abrir un modal.

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

## Implementation steps

Continúa la numeración del plan v1 (pasos 1-19 ya completados e implementados en el PR #49).

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

## Test strategy

**Backend (unitario/integración)** — mismos niveles y patrón que v1 (`praxsa_manager/product/tests/test_almacen_module.py`):
- Creación: campos obligatorios ausentes → `400`; defaults de servidor aplicados correctamente (`installed=0`, `original_length=to_install`, `date` ≈ ahora si se omite); bobina inactiva rechazada en el selector (`400`, mismo patrón que `test_inactive_lamina_not_offered_as_choice_for_new_bobina`).
- Eliminar: `to_install > 0` → `400` con mensaje explícito, la fila sigue `is_active=True`; `to_install == 0` → `200`, fila queda `is_active=False`; reactivar (`is_active=True`) sin restricción.
- Listado: filtra `is_active=True` por defecto, `?include_inactive=true` las muestra todas — mismo patrón que Lámina/Bobina.
- Permisos: `almacen` (sin `add_inventario`/`change_inventario` nuevos si aplica) recibe `403` en `POST` y en `toggle-active`; `admin` con esos permisos puede ambos — extiende `AlmacenRolePermissionTest` ya existente.

**Frontend (unitario, Angular `TestBed`)**: specs de los 3 componentes nuevos siguiendo el patrón ya usado por los de Lámina (`lamina-create.component.spec.ts`, `lamina-view.component.spec.ts` si existiera, `lamina-edit.component.spec.ts`) — carga de selects (Sucursal/Bobina), envío del formulario de creación con los campos obligatorios, manejo del error `400` de "Gestionar"/Eliminar, y el spec reescrito de `inventario-list` cubriendo `canManage` y la navegación a las 3 rutas nuevas (mismo patrón que `laminas-list.component.spec.ts`).

**E2E: sigue sin corresponder**, mismo motivo que v1 (no es un flujo crítico de punta a punta, Playwright no instalado) — la ampliación de Inventario es del mismo tipo de cambio (CRUD administrativo) que ya se decidió no requiere E2E. La verificación manual del paso 34 cubre el riesgo de integración real que un test aislado no puede validar (en particular, que el `400` de "no se puede eliminar con stock" se vea como error legible en la UI, no como una operación silenciosamente fallida).

## Acceptance criteria

Además de las ya cumplidas por v1 (ver PR #49):
- [ ] Migración de `inventario.is_active` aplicada, `makemigrations --check --dry-run` sin cambios pendientes.
- [ ] `admin` puede crear una fila de Inventario nueva (con los campos obligatorios) y verla en el listado.
- [ ] `admin` puede ver el detalle de solo lectura de una fila de Inventario.
- [ ] Intentar eliminar una fila de Inventario con `to_install > 0` falla con un mensaje claro, sin cambiar el estado de la fila.
- [ ] Eliminar una fila de Inventario con `to_install == 0` la oculta del listado por defecto (sigue en la base de datos, visible con `?include_inactive=true`).
- [ ] `almacen` no ve ninguna acción de Crear/Editar/Eliminar en el listado de Inventario, y un intento directo de `POST`/`toggle-active` devuelve `403` (verificado con test automático).
- [ ] `python manage.py test` completo en verde; `ng build`/`ng lint`/`ng test` sin errores nuevos.

## Risks

- **Permiso operativo nuevo (`add_inventario`)**: el grupo `admin` de cada ambiente necesita este permiso asignado para poder crear Inventario — no se automatiza (mismo criterio que el resto de permisos del módulo). Mitigación: documentado explícitamente en el PR y en el paso 34 de verificación manual, para no asumir que ya está configurado en ningún ambiente.
- **Restricción `to_install == 0` para eliminar podría resultar muy estricta en la práctica** (p. ej. el negocio quiere eliminar un lote dañado con stock residual, sin pasar primero por "Gestionar" para poner `to_install=0`). Mitigación: es una condición de una línea en la vista, no un cambio de modelo ni de contrato — ajustable rápido si el negocio lo pide tras usar el módulo.
- **Migrar el modal de "Gestionar" a una página separada** cambia la experiencia de uso de algo que ya está implementado y verificado (v1). Mitigación: el endpoint `PATCH almacen/inventario/<pk>/` no cambia (mismos 5 campos, mismo serializer) — el riesgo es puramente de frontend/UX, no de contrato; se verifica con specs nuevos + la verificación manual del paso 34.

## Out of scope

- Guard de ruta por permiso en el frontend — sigue sin corresponder, mismo motivo que v1.
- Cascada de soft-delete — sigue sin aplicar a este módulo.
- Cualquier protección de integridad para eliminar más allá de `to_install == 0` (p. ej. bloquear si ya existe un `Proforma_Detail` histórico apuntando a la fila) — decisión explícita del ADR: no aplica, ver "Alternativas consideradas" ahí.
- Creación automática de permisos/grupos — sigue siendo configuración manual por ambiente.

## Dependencias nuevas

Ninguna — mismo motivo que v1, esta ampliación no introduce ninguna librería nueva.

## Changelog
- **v2** (2026-09-27): Inventario se amplía de "listado + Gestionar" a CRUD completo (Ver/Crear/Editar/Eliminar), tras verificación manual real que confirmó la necesidad de negocio. Motivado por hallazgo del usuario durante pruebas manuales del PR #49 (ver historial de `TASK-modulo-almacen`), formalizado en la actualización de `docs/design/DDR-modulo-almacen-listado-y-flujo-almacen.md` y `docs/adr/ADR-modulo-almacen-modelo-datos-imagen-soft-delete.md`.
