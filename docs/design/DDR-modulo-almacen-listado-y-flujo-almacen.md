# DDR-modulo-almacen-listado-y-flujo-almacen: Menú, listados y flujos de Láminas, Bobinas e Inventario en `panel_admin/`

**Estado:** Propuesto
**Task relacionado:** TASK-modulo-almacen
**Fecha:** 2026-09-26

## Contexto

`TASK-modulo-almacen` investigó que Láminas (`Window_Film`), Bobinas (`Window_Film_Reel`) e Inventario (`inventario`) ya existen como modelos de dominio, pero sin ningún CRUD administrativo en `panel_admin/` — solo Django admin y un par de endpoints públicos de solo lectura para `proforma/`. El precedente más cercano y más reciente es `TASK-modulo-vehiculos` (PR #48, ya mergeado), que resolvió imagen + soft delete + `ngx-datatable` para otro conjunto de modelos de catálogo (`Car_Brand`/`Car_Model`/`Car_Part`) con dos patrones de pantalla ya distinguidos en el código real:

1. **Entidad simple** (Marca, Item): una sola página de listado con modal de crear/ver/editar inline, sin rutas separadas (`panel_admin/src/app/vehicles/brands/brands-list.component.html:88-117`, `vehicles.routes.ts:10,15`).
2. **Entidad rica** (Modelo: tiene imagen y asociaciones a Items): páginas separadas `list` / `create` / `view` / `edit` con rutas propias (`vehicles.routes.ts:11-14`), y un componente compartido `app-image-upload` (`panel_admin/src/app/shared/image-upload/image-upload.component.ts`) para carga/preview/reemplazo de imagen vía `ControlValueAccessor`.

Esta es la primera decisión de diseño del proyecto que necesita distinguir dos roles reales (`admin` vs `almacen`) en la UI de un mismo módulo — ni Usuarios ni Vehículos lo necesitaron (cualquier `is_staff` podía gestionar todo). La investigación del task ya deja constancia de que el frontend hoy no tiene ningún dato de rol/grupo disponible tras el login — este DDR define el comportamiento deseado, pero esa brecha (cómo el frontend se entera del rol) queda explícitamente para `delivery-architect`.

## Pantallas/flujos afectados

1. **Menú principal** — nuevo grupo "Almacén" con 3 submenús: Láminas, Bobinas, Inventario. Visible para ambos roles (`admin` y `almacen`); ningún submenú se oculta a nivel de menú, la diferencia está dentro de cada pantalla.
2. **Láminas — listado** (`/almacen/laminas`): tabla con miniatura, nombre, y acciones. `admin` ve botones Ver/Editar/Eliminar y "Nueva lámina"; `almacen` solo ve el botón Ver (o ninguna acción, ver sección de privilegio).
3. **Láminas — crear** (`/almacen/laminas/create`, solo `admin`): formulario con nombre, descripción/contenido, carga de imagen.
4. **Láminas — ver** (`/almacen/laminas/view/:id`, ambos roles): detalle de solo lectura con imagen grande o placeholder.
5. **Láminas — editar** (`/almacen/laminas/edit/:id`, solo `admin`): mismo formulario que crear, con imagen actual precargada y reemplazable.
6. **Bobinas — listado** (`/almacen/bobinas`): tabla con lámina asociada, ancho, largo, precio y acciones. `admin` ve Ver/Editar/Eliminar y "Nueva bobina" con modal inline (sin imagen, sin ruta separada); `almacen` solo ve Ver.
7. **Inventario — listado** (`/almacen/inventario`): tabla de solo consulta para ambos roles (sucursal, lámina/bobina, cantidades, fechas). `admin` ve además una acción "Gestionar"/"Editar" (modal inline) sobre los campos editables de una fila existente; `almacen` no ve esa acción. No hay pantalla de "crear inventario" en esta iteración (ver Hipótesis/pregunta abierta abajo).

## Componentes/patrones elegidos

- **Menú**: editar `panel_admin/src/assets/data/routes.json` agregando un grupo nuevo con la misma forma que "Usuarios" (`routes.json:14-58`) y "Vehículos" (`routes.json:59-103`): `{"path": "", "title": "Almacén", "class": "menu-toggle", "submenu": [...]}` con 3 entradas `"class": "ml-menu"`. Sin alternativa real a evaluar — es el único patrón de menú multinivel que usa el proyecto y ya está probado dos veces.
- **Tabla**: `ngx-datatable` con filtrado **client-side** vía `filterDatatable($event)` sobre un array `data`/`rows` cargado completo — el mismo patrón que cita literalmente el pedido (`advance-table.component.html`) y que replican `models-list.component.ts:45-56`, `brands-list.component.html:31-33`. Se descarta el filtro `?search=` server-side que sí existe en el backend de Vehículos (`vehicle_admin.py:32-34`) como mecanismo *principal* de UI, porque el patrón que el pedido pide explícitamente citar es el client-side de `advance-table`; el volumen esperado de Láminas/Bobinas/Inventario (catálogo interno, no miles de filas) hace que cargar todo y filtrar en cliente sea consistente con lo ya construido, sin necesitar paginación server-side.
- **Miniatura de Lámina en el listado**: misma solución que `models-list.component.html:60-68` — columna `ngx-datatable-column` con `<img [src]="row.image" class="data-table-img">` si hay imagen, o `<i class="fas fa-image text-muted">` si no. Mismo criterio para el placeholder "sin imagen" en la vista de detalle (`model-view.component.html:20-27`, círculo/caja con borde y el ícono más grande).
- **Carga/reemplazo de imagen de Lámina (crear/editar)**: reutilizar tal cual el componente compartido `app-image-upload` (`panel_admin/src/app/shared/image-upload/image-upload.component.ts`), ya extraído a `shared/` por `TASK-modulo-vehiculos` (contradice la nota vieja de `docs/frontend/panel_admin/reference.md:49`, que decía que `shared/` no existía — ya existe, verificado). No se evalúa construir un componente nuevo: haría exactamente lo mismo que éste ya hace (preview con `FileReader`, validación de tipo/tamaño de UX, distinción `dirty` para "reemplazar" vs "quitar" vs "no tocar", multipart en el service).
- **Formulario de Lámina (crear/editar)**: página propia con `ReactiveFormsModule`, mismo layout de card que `model-create.component.html`/`model-edit.component.html` (breadcrumb, `card-body`, `form-select`/`form-control` de Bootstrap). Se elige el patrón de **página separada** (no modal), igual que Modelo, porque Lámina también tiene imagen — la señal usada por Vehículos para decidir "página separada vs modal" es "¿tiene imagen o asociaciones?", y Lámina la cumple.
- **Formulario de Bobina (crear/editar)**: modal inline sobre el propio listado, igual que Marca/Item (`brands-list.component.html:88-117`) — Bobina no tiene imagen ni pantalla de detalle propia con contenido adicional, así que no se justifica una página separada. Los campos (lámina asociada vía select, ancho, largo, precio) entran cómodos en un modal simple.
- **Selector de Lámina dentro del formulario de Bobina**: `<select>` poblado con `listLaminas({includeInactive: false})` (o el equivalente del endpoint de Almacén), mismo patrón que el selector de Marca en `model-create.component.html:16-25` — solo laminas activas, para no poder asociar una bobina nueva a una lámina eliminada (mismo criterio que `ADR-modulo-vehiculos-soft-delete.md` punto 4: los selectores solo ofrecen registros activos).
- **Inventario — listado + "Gestionar"**: listado igual a los anteriores (`ngx-datatable` + búsqueda client-side). La acción "Gestionar" (solo `admin`) abre un modal inline (patrón Marca/Item) con los campos editables que arquitectura confirme (candidatos, según la investigación: `to_install`, `installed`, `precio_compra_mtr_lineal`, `precio_venta_mtr_lineal`, `nro_lote`) — no un formulario de alta completo, porque el pedido no lista "Crear" para Inventario y el dato de investigación es que las filas de `inventario` se generan hoy principalmente vía lógica de negocio (`Inventario_Business`), no alta manual.

## Alternativas consideradas

- **Reutilizar el componente `AdvanceTableComponent` como dependencia (import directo)** en vez de replicar su patrón visual/de filtrado en componentes propios de Almacén. Se descarta por lo mismo que ya se descartó implícitamente en Usuarios y Vehículos: `AdvanceTableComponent` es una página de ejemplo autocontenida de la plantilla, no un componente parametrizable pensado para recibir columnas/acciones por `@Input()` — envolverlo obligaría a refactorizarlo primero (fuera de alcance de este task, y no pedido) o a que Almacén sea el primer módulo en hacerlo distinto a los dos módulos ya construidos, generando inconsistencia. Replicar el patrón (como ya hicieron Usuarios/Vehículos) es más barato y mantiene consistencia real con lo existente.
- **Página separada también para Bobina** (en vez de modal). Se descarta: Bobina no tiene imagen ni contenido adicional que justifique una vista de detalle propia — usar el patrón "rico" para una entidad simple sería sobreingeniería, y rompería la consistencia con Marca/Item, que son el precedente de forma más parecida (entidad de catálogo simple con 2-4 campos).
- **Ocultar la miniatura de Lámina en el listado y mostrarla solo en el detalle.** Se descarta: el pedido exige explícitamente miniatura en el listado ("En el listado de láminas debe mostrarse una miniatura cuando exista una imagen"), y ya hay un patrón idéntico probado (`models-list.component.html:60-68`) sin costo adicional de construir algo nuevo.
- **Modal para "Gestionar Inventario" con todos los campos del modelo editables.** Se descarta por ahora: sin confirmación de qué campos debe poder tocar `admin` desde el panel (pregunta abierta de la investigación), abrir todo el modelo a edición libre arriesga permitir sobrescribir campos que hoy solo cambian por lógica de negocio (`quantity`, `original_length`, `date`), rompiendo la consistencia de datos que alimenta proformas/instalaciones. Se deja explícitamente que la lista de campos editables es una decisión de `delivery-architect`/`delivery-plan`, no de este DDR.

## Comportamiento por privilegio/estado

| Pantalla | `admin` | `almacen` |
|---|---|---|
| Menú Almacén (3 submenús) | Visible | Visible |
| Listado Láminas | Ve todas las acciones + "Nueva lámina" | Ve el listado y el botón Ver; sin Crear/Editar/Eliminar |
| Crear/Editar Lámina | Acceso completo | Sin acceso (botón oculto; si se navega directo a la URL, la pantalla debe redirigir o mostrar error, no solo ocultar el botón) |
| Ver Lámina | Acceso | Acceso |
| Listado Bobinas | Ve todas las acciones + "Nueva bobina" | Ve el listado y Ver; sin Crear/Editar/Eliminar |
| Crear/Editar Bobina (modal) | Acceso completo | Sin acceso (modal/botones no se renderizan) |
| Listado Inventario | Ve el listado + acción "Gestionar" | Ve solo el listado, sin acción "Gestionar" |
| "Gestionar" Inventario (modal) | Acceso completo | Sin acceso |

Los botones **se ocultan**, no se deshabilitan con tooltip — mismo comportamiento visual que ya establecieron los toggles `is_active`/`is_staff` de Usuarios y Vehículos (aunque esos son por *estado*, no por *rol*; se elige ocultar en vez de deshabilitar porque un botón deshabilitado sin explicación es peor UX que no mostrarlo, y el pedido ya dice explícitamente "no deben estar disponibles en la UI", no "deshabilitados").

**Nota explícita de seguridad — esto es solo UX, no la barrera real**: ocultar botones en Angular para el rol `almacen` es una decisión de presentación. La aplicación real del permiso (que un usuario `almacen` no pueda crear/editar/eliminar Láminas/Bobinas ni modificar Inventario aunque manipule la UI, el DOM, o llame al endpoint directo) depende de que `delivery-architect` defina y `delivery-plan`/`delivery-engineer` implementen la verificación de permisos en el backend (candidato natural, ya usado en Usuarios/Vehículos: `IsStaffUser` + `permissions.DjangoModelPermissions`, sin asignar `add`/`change`/`delete` de `Window_Film`/`Window_Film_Reel`/`inventario` al grupo `almacen`). Este DDR no decide ese mecanismo.

**Dependencia declarada hacia arquitectura**: para que la tabla anterior sea implementable, el frontend necesita alguna forma de saber si el usuario logueado es `admin` o `almacen` (ver brecha documentada en `## Investigación` del task: `PanelAdminAuthToken` no devuelve grupos hoy). Este DDR asume que existirá una fuente de verdad consultable desde el frontend (ej. un booleano o lista de grupos en el objeto de sesión) pero no decide cuál — es explícitamente responsabilidad de `delivery-architect`.

## Consecuencias

- Almacén queda visualmente consistente con Usuarios y Vehículos: mismas clases de botón (`btn-tbl-view`/`btn-tbl-edit`/`btn-tbl-delete`/`btn-tbl-activate`), mismo patrón de búsqueda client-side, mismo componente de imagen compartido, mismos breadcrumbs/cards.
- Se introduce el primer caso de ocultamiento de UI por *rol* (no por *estado*) del proyecto — si el mecanismo que arquitectura decida para exponer el rol al frontend termina siendo genérico (ej. un `AuthService.hasGroup(name)` o `currentUser.groups`), los módulos Usuarios y Vehículos podrían beneficiarse después del mismo mecanismo sin haberlo necesitado hoy; este DDR no les exige ningún cambio.
- Bobina no gana pantalla de detalle propia — si el negocio pide más adelante ver el historial de inventario de una bobina puntual desde su propia ficha, sería una ampliación de este DDR, no algo ya cubierto.
- La lista de campos editables de "Gestionar Inventario" queda pendiente de una decisión explícita fuera de este DDR — si `delivery-architect`/`delivery-plan` no la fijan, la pantalla de "Gestionar" no puede implementarse con precisión.
