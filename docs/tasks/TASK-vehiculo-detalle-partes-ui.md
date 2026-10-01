# TASK-vehiculo-detalle-partes-ui: Rediseño UI de la vista Detalle de Vehículo (Modelo) y su lista de Partes

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** SI
**Rama:** claude/vehicle-detail-parts-ui-9c9dc9 (asignada por el entorno)
**Pull Request:** [#61](https://github.com/rolion/praxsa-django-panel-admin/pull/61)

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-01 13:20 UTC | (nuevo) → INVESTIGATION | Task creado | delivery-investigate |
| 2026-10-01 13:45 UTC | INVESTIGATION → DESIGN → PLANNING | Diseño resuelto en DDR (Bootstrap en vez de Tailwind, cabecera con pill y Editar bajo la imagen, tarjetas por ítem con `ModelItemCardComponent`); veredicto NEEDS_PLAN, sin arquitectura | delivery-design |
| 2026-10-01 14:10 UTC | PLANNING → ENGINEERING | Plan v1 escrito (sin E2E, sin dependencias nuevas); PR abierto, pendiente de aprobación humana antes de implementar | delivery-plan |
| 2026-10-01 14:50 UTC | ENGINEERING → REVIEW | Implementación completa según plan v1 (componente de tarjeta, rediseño de la vista, specs); empujada al PR #61 | delivery-engineer |

## Investigación

### Requerimiento
Prompt "Implementación UX/UI: Vista Detalle de Vehículo y Partes" (basado en una imagen de referencia que **no se adjuntó** al invocar el skill; solo se recibió el texto). Pide, escrito para "React, Tailwind y Lucide/Shadcn":
- Layout: lienzo `#F8FAFC`, tarjeta blanca `rounded-xl` con `shadow-sm`; breadcrumbs `Ver modelo > 🚘 > Modelos`.
- Cabecera: imagen del vehículo a la izquierda con botón **Editar** (azul/púrpura oscuro, ícono lápiz) debajo; a la derecha Marca, Modelo y Estado como pill verde "Activo".
- Sección "Partes del Modelo" (`text-xl font-bold`), subtítulo "N Ítems Asociados", botón "+ Agregar Item" azul claro a la derecha.
- Lista de una sola columna (`flex flex-col gap-3`) de tarjetas por ítem: nombre (semibold) + `Dimensiones: Ancho: X.XXm x Largo: Y.YYm | Cantidad: Z`; a la derecha botones compactos Editar (azul oscuro/púrpura) y Eliminar (naranja/rojo) solo ícono.
- Componentes modulares (`VehicleHeader`, `ItemCard`, `Badge`), lista alimentada por un array JSON, estado vacío, responsive.

### Hechos encontrados
- **La pantalla ya existe**, no se crea desde cero: `panel_admin/src/app/vehicles/models/model-view.component.html` / `.ts`, registrada en `panel_admin/src/app/vehicles/vehicles.routes.ts:5`. Ya tiene cabecera con imagen + datos, botón Editar, lista de items con Editar/Quitar, modales de agregar/editar item y confirmación SweetAlert para quitar.
- **El pedido de stack no coincide con el proyecto.** El "vehículo" vive en `panel_admin/` (Angular 21 standalone, Bootstrap 5 + plantilla admin, Font Awesome/Material Icons — `docs/frontend/panel_admin/reference.md`), no en React. No hay Tailwind ni Lucide en `panel_admin/package.json` (grep sin resultados). `proforma/` (Angular 16) tampoco tiene pantallas de modelos de vehículo (grep de `vehic|modelo` en `proforma/src/app/app-routing.module.ts` sin resultados).
- **Breadcrumb actual** (`model-view.component.html:2-8`): "Ver modelo" (page-title) › ícono `fa-car` enlazado a `/vehicles/models` › "Modelos". Ya replica el `Ver modelo > 🚘 > Modelos` pedido, con el ícono de la plantilla.
- **Cabecera actual** (`model-view.component.html:19-39`): fila con imagen (máx. 320px, placeholder `fa-image` si no hay imagen o falla la carga, `:21-27`) y `<dl>` Marca/Modelo/Estado; el estado es **texto plano** `Activo/Inactivo` (`:36`), no un pill. El botón Editar (`:40`) es `btn btn-primary` **debajo de toda la cabecera** (`mb-4`), no debajo de la imagen y sin ícono.
- **Sección de items actual** (`:42-77`): encabezado `<h5>Items</h5>` con botón `btn-outline-primary` "Agregar item" (`:43-46`); **sin contador** de ítems asociados (el modelo ya trae `items_count`, `vehicles.model.ts:25`, y `items.length` está disponible); lista Bootstrap `list-group` (`:49-51`), no tarjetas separadas con `gap`; detalle como `Ancho: {{ item.width }} · Largo: {{ item.length }} · Cantidad: {{ item.quantity }}` (`:55`) — sin prefijo "Dimensiones:", sin unidad `m`, sin separador `|`, y `width`/`length` son strings del backend (`'1.00'`, `vehicles.model.ts:34-35`).
- **Botones de acción por item** (`:59-66`): ya existen `btn-tbl-edit` y `btn-tbl-delete` con íconos `fa-pen` / `fa-trash-alt` (definidos en `panel_admin/src/assets/scss/override/_table.scss:434-470`), los mismos que usa "Credenciales". El de eliminar dice "Quitar" (title) y llama `removeItem` (desasocia el item del modelo, no lo borra del catálogo).
- **Card contenedora actual**: `col-lg-8 col-md-12` + `.card` de la plantilla (`:11-13`); el fondo de página/tema lo define la plantilla, no la pantalla.
- **Estado vacío ya existe**: `Este modelo todavía no tiene items asociados.` (`:74-76`), y estados de carga y error (`:15-18`).
- **Precedente directo de rediseño de una vista de detalle**: `TASK-credencial-detalle-layout` (PR #57) — mismo pedido "en Tailwind", resuelto en `docs/design/DDR-credencial-detalle-layout-vista-detalle-chips.md` con Bootstrap 5 en lugar de Tailwind, badge de estado (`badge bg-success` / `bg-secondary`, `panel_admin/src/app/users/view/*.html:23-25`) y chips (`bg-primary-subtle`, `bg-info-subtle`). Es el patrón a seguir.
- **Specs existentes que dependen del markup actual**: `model-view.component.spec.ts` consulta `img`, `.fa-image` y la carga de modelo/items; cualquier cambio de clases de la imagen/placeholder puede romperlos. Hay también specs de agregar/editar/quitar item (misma `spec`).
- **Backend sin cambios necesarios aparentes**: la API ya devuelve `car_brand_name`, `image`, `is_active`, `items_count` (`vehicles.model.ts:19-27`) y los items con `width/length/quantity/car_part_name` (`:29-38`). `installation_price` está oculto a propósito (`TASK-modulo-vehiculos.md`, historial 2026-09-26 12:00). Última migración: `0114_precio_venta_sucursal_unico.py`; no se prevé migración.
- Tarea adyacente ya publicada: `TASK-imagen-modelo-vehiculo-no-visible` (PR #58) añadió el fallback de imagen rota (`imageFailed`) en esta misma vista; hay que conservarlo.

### Hipótesis / supuestos no confirmados
- La imagen de referencia no llegó; las especificaciones visuales (colores exactos azul/púrpura, naranja/rojo) se infieren solo del texto. Habría que confirmarlas con el usuario o con la imagen en `delivery-design`.
- Se asume que "implementar" significa adaptar la pantalla Angular/Bootstrap existente al look pedido, no introducir React/Tailwind/Shadcn (por analogía con el precedente de `TASK-credencial-detalle-layout`). No confirmado con el usuario.
- "Máximo de 5 a 6 elementos" parece describir el dato de ejemplo (5 partes del Audi A1), no un límite funcional; hoy la lista no pagina ni limita. No confirmado.
- El nombre del botón "Eliminar" del prompt vs. "Quitar" actual: se asume que mantiene la semántica de desasociar con confirmación; no verificado con el usuario.
- Sobre `shadow-sm`, `rounded-xl` y `#F8FAFC`: no se verificó cómo se ven con los temas claro/oscuro de la plantilla.

### Módulos y dependencias relacionadas
- Frontend: `panel_admin/src/app/vehicles/models/model-view.component.{html,ts,spec.ts}`, `vehicles.model.ts`, `vehicles.service.ts`, `panel_admin/src/assets/scss/override/_table.scss` (botones `btn-tbl-*`).
- Pantalla vecina con patrón de detalle: `panel_admin/src/app/users/view/`.
- Backend: solo lectura de contrato (`product/serializer/vehicle_serializer.py`, `product/custom_views/vehicle_admin.py`); sin cambios aparentes.

### Implementaciones similares existentes
- `users/view` (badge de estado, chips, botón Editar) y su DDR `DDR-credencial-detalle-layout-vista-detalle-chips.md`.
- No existe carpeta `panel_admin/src/app/shared/` salvo `image-upload`; no hay componentes `Badge`/`ItemCard` genéricos. Los componentes modulares pedidos serían nuevos.

### Comportamiento actual
La vista carga modelo y items y muestra una card con imagen/datos, un botón Editar bajo la cabecera, y una lista Bootstrap de items con acciones Editar/Quitar; agregar/editar item van por modales NgbModal y quitar por SweetAlert. Funcionalmente cubre lo pedido; las diferencias son visuales y de composición (estado como pill, Editar bajo la imagen con ícono, subtítulo con contador, tarjetas por ítem con formato `Dimensiones: … m x … m | Cantidad`, "+ Agregar Item" en la cabecera de sección).

### Restricciones
- `docs/CLAUDE.md`: deuda técnica conocida; seguir patrones existentes en vez de introducir nuevos.
- `docs/frontend/panel_admin/reference.md`: stack Angular 21 + Bootstrap; agregar Tailwind implicaría nueva dependencia de build con posible conflicto de utilidades con Bootstrap (no verificado empíricamente, ya señalado en TASK-credencial-detalle-layout).
- Conservar la lógica y los `data-test`/selectores que usan los specs actuales, o actualizar los specs.

### Riesgos identificados
- Conflicto de tecnología pedida (React/Tailwind/Lucide) vs. stack real.
- Imagen de referencia ausente: riesgo de divergir del diseño esperado.
- Specs actuales de `model-view` acoplados al markup; el formato de dimensiones (`m`, decimales) no tiene cobertura.
- Consistencia con los temas/tema oscuro de la plantilla y contraste del pill verde y botones.
- `width`/`length` llegan como string; formatear `X.XXm` requiere decidir si se normaliza a 2 decimales en la vista.

### Veredicto de complejidad
**NEEDS_PLAN** — Cambio acotado a un componente frontend existente y su spec; sin cambios de API, modelo, permisos ni otros módulos, y con un precedente directo (credencial-detalle-layout) que cubre la decisión de stack. No requiere decisión arquitectónica nueva.

### Diseño requerido
**SI** — Es un rediseño visual de una pantalla con componentes nuevos (pill de estado, tarjetas de ítem, encabezado de sección con contador) que debe resolverse con Bootstrap/plantilla de `panel_admin/` y mantenerse consistente con el resto del panel; además hay que reconciliar el pedido en React/Tailwind con el stack real y confirmar los detalles visuales de la imagen de referencia no recibida.

## Diseño
- [DDR-vehiculo-detalle-partes-ui-vista-detalle-modelo](../design/DDR-vehiculo-detalle-partes-ui-vista-detalle-modelo.md) — Bootstrap 5 (no Tailwind/Lucide), cabecera con pill de estado y Editar bajo la imagen, encabezado "Partes del Modelo" con contador y "Agregar Item", lista en tarjetas (`ModelItemCardComponent`) con `Dimensiones: Ancho: X.XXm x Largo: Y.YYm | Cantidad: Z` y botones `btn-tbl-*`.

## Arquitectura
_Pendiente / No aplica según veredicto_

## Plan
- [PLAN-2026-10-01-vehiculo-detalle-partes-ui](../plans/PLAN-2026-10-01-vehiculo-detalle-partes-ui.md) — v1

## Implementación
Según plan v1, sin desvíos de alcance:
- Nuevo `panel_admin/src/app/vehicles/models/model-item-card.component.{ts,html,spec.ts}` (standalone, `input` item, outputs `edit`/`remove`, `DecimalPipe '1.2-2'`).
- `model-view.component.html` reescrito según el DDR (card `shadow-sm rounded-3`, Editar con ícono bajo la imagen, pill de estado, "Partes del Modelo" + contador + "Agregar Item", lista `flex-column gap-3` de tarjetas, vacío en recuadro); `model-view.component.ts` solo suma el import del componente; modales y lógica intactos.
- `model-view.component.spec.ts`: selector actualizado a `app-model-item-card button[title="Editar"]` y 4 casos nuevos (contador, pill, enlace Editar, vacío).
- Autoverificación (no es el Quality Gate): `ng lint` limpio, `ng build` ok; `ng test` 453 OK / 14 FALLAN, todos `should create` de componentes de la plantilla demo (AdvanceTable, Blank, Dashboard2, First*/Second*/Third*, Footer, Page404/500, Sidebar, Signup) por falta de provider `ActivatedRoute`; no tocan vehículos ni este cambio (no se contrastó contra master). Los specs de `vehicles/models` pasan.
- Para correr los tests en este worktree se enlazó `panel_admin/node_modules` (junction, ignorado por git) al de otro worktree con `package-lock.json` idéntico; no se instaló ni cambió ninguna dependencia.
- **Pendiente:** verificación visual en vivo (tema claro/oscuro, móvil, con y sin imagen/items) del paso 5 del plan; no se ejecutó en esta etapa.
- Deuda/notas: sin imagen de referencia, colores de botones/pill vienen del tema (ver DDR).

## Review
_Pendiente_

## Publicación
_Pendiente_
