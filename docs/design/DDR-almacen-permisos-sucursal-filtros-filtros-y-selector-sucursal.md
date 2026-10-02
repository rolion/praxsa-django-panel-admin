# DDR-almacen-permisos-sucursal-filtros-filtros-y-selector-sucursal: Filtros de lámina/sucursal y comportamiento del selector de sucursal en Bobinas e Inventario

**Estado:** Propuesto
**Task relacionado:** TASK-almacen-permisos-sucursal-filtros
**Fecha:** 2026-10-02

## Actualización de alcance (2026-10-02)

Por indicación del usuario se **omite Bobinas**: este DDR aplica solo a **Inventario**. Quedan sin efecto las referencias a Bobinas de abajo (pantalla 1 y 2, columna Sucursal en Bobinas, filas de bobina en la tabla de privilegios, dependencia "bobinas de mi sucursal"); el listado y el modal de Bobinas no cambian. El select de Bobina del alta de inventario sigue mostrando el catálogo global.

## Contexto

`TASK-almacen-permisos-sucursal-filtros` pide (1) que quien no es admin solo vea/agregue/edite bobinas e inventario de sus sucursales, y (2) filtros de **lámina** y **sucursal** en los listados de Bobinas e Inventario, con el selector de sucursal fijado cuando el usuario tiene una sola.

Hechos de la investigación que condicionan el diseño:
- Ambos listados son `ngx-datatable` con búsqueda de texto **en cliente** (`bobinas-list.component.ts:70-78`, `inventario-list.component.ts:54-66`). Ninguno tiene filtros de lámina/sucursal. Bobinas hoy ni siquiera tiene dato de sucursal por fila (la bobina es un catálogo global, `models.py:74-88`).
- Acciones de escritura hoy visibles solo con `hasGroup('admin')` (`canManage`, `bobinas-list.component.html:35-43,71-84`, `inventario-list.component.html:35-43,76-89`), decisión del DDR previo `DDR-modulo-almacen-listado-y-flujo-almacen` (tabla "Comportamiento por privilegio/estado") que este task relaja.
- El formulario de alta de inventario carga sucursales con `listSucursales()` → `GET /product/sucursales`, que devuelve todas (`user_admin.py:134-138`).
- Patrón ya en el módulo para filtrar por sucursal: `PrecioVentaSucursal` (`almacen_admin.py:241-243`, `?sucursal=`).
- Pregunta abierta del task (bobina global vs. por sucursal) **no está resuelta**; este DDR define el comportamiento visual de modo que no dependa de la respuesta, y marca dónde sí depende.

## Pantallas/flujos afectados

1. **Bobinas — listado** (`/almacen/bobinas`): agrega barra de filtros (Lámina, Sucursal) sobre la tabla; las acciones Crear/Editar se muestran según alcance.
2. **Bobinas — modal crear/editar/ver**: si la arquitectura asocia bobina↔sucursal (opción b), el modal gana un select de Sucursal acotado al alcance del usuario; si no (opción a), no cambia.
3. **Inventario — listado** (`/almacen/inventario`): misma barra de filtros (Lámina, Sucursal); acciones por fila según alcance.
4. **Inventario — crear** (`/almacen/inventario/create`): el select de Sucursal solo ofrece las sucursales del usuario; si es una, queda preseleccionada y bloqueada.
5. **Inventario — ver / editar**: sin cambio visual; solo accesibles para filas dentro del alcance.

No se agregan pantallas nuevas.

## Componentes/patrones elegidos

- **Barra de filtros**: dos `<select class="form-select form-control">` (Lámina, Sucursal) en la cabecera de la tarjeta del listado, junto al buscador existente (`ngxTableHeader` / `table-search-area`, mismo marcado que `bobinas-list.component.html:26-45`), con estilos de formularios de la plantilla (`panel_admin_doc/form-elements.html`, `docs/frontend/panel_admin/reference.md`, tabla "Formularios"). No se agrega componente nuevo ni dependencia; se mantiene `ngx-datatable` (`reference.md`, tabla "Tablas") como en el resto del módulo.
- **Filtrado por servidor para Lámina y Sucursal** (`?window_film=<id>&sucursal=<id>`), manteniendo la búsqueda de texto libre en cliente tal como está. Se aleja del criterio "todo en cliente" del DDR previo por dos motivos de diseño: (i) los filtros por sucursal deben respetar el alcance del usuario, que el backend ya calcula, y reutilizan el patrón `?sucursal=` de Precios por sucursal; (ii) la fila de Bobina no trae sucursal y la de Inventario trae `window_film_name` pero no el id de lámina, así que filtrar por id en cliente exigiría ampliar los datos de todos modos. El contrato exacto de los parámetros es decisión de `delivery-architect`.
- **Opciones del selector de Lámina**: `listLaminas()` (activas), con primera opción "Todas las láminas".
- **Opciones del selector de Sucursal**: lista de **sucursales en alcance del usuario** (no `GET /product/sucursales`, que hoy no está acotado), con la regla de la sección siguiente. Qué endpoint la provee es decisión de arquitectura.
- **Reglas del selector de Sucursal (la regla pedida)**:
  - Usuario con **una** sucursal: el select aparece **preseleccionado con esa sucursal y deshabilitado** (`[attr.disabled]`, mismo recurso que el modo "ver" en `bobinas-list.component.html:107`), sin opción "Todas". El listado siempre se pide con esa sucursal.
  - Usuario con **varias**: opción "Todas mis sucursales" (valor por defecto) + cada una de las suyas.
  - **Admin** (ve todas): opción "Todas las sucursales" + todas.
  - Usuario con **cero** sucursales: select vacío y deshabilitado y mensaje informativo "No tienes sucursales asignadas" (patrón `alert alert-info` ya usado en `inventario-list.component.html:52-54`); sin botones de alta.
- **Cambio de filtro**: recarga el listado (`load()`) y reinicia la paginación (`table.offset = 0`, ya hecho en `filterDatatable`). Los filtros se combinan entre sí y con el buscador de texto.
- **Formulario de alta de Inventario**: mismo select de Sucursal con las mismas reglas (una → preseleccionada y bloqueada; varias → elegir entre las suyas; admin → todas). El select de Bobina no cambia.
- **Columna Sucursal en Bobinas**: solo si la arquitectura define bobina↔sucursal (b), o si el listado pasa a mostrar la sucursal de la que proviene cada bobina (a); queda como decisión dependiente. La tabla actual (Lámina, Ancho, Largo, Precio) es suficiente si el filtro solo acota filas.

## Alternativas consideradas

- **Filtros en cliente sobre `data` ya descargada** (extender `filterDatatable`): menor esfuerzo y consistente con el DDR previo, pero obliga a ampliar los datos de cada fila (id de lámina; sucursal en bobinas) y deja que la lista completa viaje al navegador antes de filtrarse. Descartada como mecanismo para lámina/sucursal; se conserva para el texto libre.
- **Ocultar el selector de Sucursal cuando el usuario tiene una sola**: más limpio, pero el pedido dice explícitamente "no puede seleccionar otra", lo que se cumple mejor mostrándolo fijo; además deja visible en qué sucursal está operando. Descartada.
- **Deshabilitar botones fuera de alcance con tooltip** en vez de ocultarlos: se mantiene el criterio del DDR previo (ocultar), porque un botón deshabilitado sin explicación es peor UX; ahora el criterio es por fila/alcance, no solo por rol.
- **Una sola caja de búsqueda que cubra todo** (sin selects): no permite expresar "solo esta sucursal" de forma verificable ni bloquearla. Descartada.

## Comportamiento por privilegio/estado

| Situación | Selector de Sucursal | Crear/Editar bobina o inventario |
|---|---|---|
| Admin | Todas + cada sucursal | Visible |
| Usuario con 1 sucursal | Fijo y deshabilitado | Visible solo para filas de su sucursal |
| Usuario con varias | "Todas mis sucursales" + suyas | Visible solo para filas de sus sucursales |
| Usuario sin sucursales | Deshabilitado + mensaje | Oculto |

- Ya no se usa `hasGroup('admin')` como único criterio de `canManage`; el criterio nuevo es "tiene permiso de escritura y la fila/sucursal está en su alcance". Los botones **se ocultan**, no se deshabilitan.
- Eliminar/Activar: el pedido no los menciona; se asume que mantienen su visibilidad actual (admin) hasta que arquitectura decida lo contrario (pregunta abierta).
- **Esto es solo UX, no la barrera de seguridad.** Requiere que `delivery-architect` defina cómo se verifica del lado servidor, para listado, detalle por id, alta, edición y toggle, que la sucursal esté dentro del alcance del usuario y cómo el frontend se entera de ese alcance y de sus permisos de escritura (lista de sucursales en alcance, capacidad de escritura). El selector bloqueado y los botones ocultos no impiden llamar al API directamente.

## Consecuencias

- Los dos listados quedan consistentes entre sí y con Precios por sucursal (filtro `?sucursal=`); el módulo pasa a tener filtros servidor-side en esas tres pantallas y búsqueda de texto cliente-side.
- Se rompe conscientemente el criterio "todo se filtra en cliente" del DDR previo para lámina/sucursal; los volúmenes siguen siendo pequeños, pero las llamadas se repiten al cambiar un filtro.
- Quedan inconsistentes hasta una iteración posterior: Láminas y Precios por sucursal (Precios ya tiene alcance por sucursal pero no un selector fijo por cantidad de sucursales) — no se tocan en este task.
- El DDR previo `DDR-modulo-almacen-listado-y-flujo-almacen` sigue vigente salvo su tabla de privilegio de Bobinas/Inventario, que este DDR modifica para el caso de usuarios con sucursal asignada.
- Dependencias abiertas hacia arquitectura: semántica de "bobinas de mi sucursal", forma de exponer el alcance al frontend, contrato de los filtros, y si Eliminar/Activar también se abren a usuarios con sucursal.
