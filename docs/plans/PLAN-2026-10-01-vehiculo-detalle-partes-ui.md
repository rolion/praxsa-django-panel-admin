# PLAN-2026-10-01-vehiculo-detalle-partes-ui (v1)

**Task:** TASK-vehiculo-detalle-partes-ui
**DDRs relacionados:** [DDR-vehiculo-detalle-partes-ui-vista-detalle-modelo](../design/DDR-vehiculo-detalle-partes-ui-vista-detalle-modelo.md)
**ADRs relacionados:** Ninguno

## Objective
Rediseñar la vista `Ver modelo` de `panel_admin/` (cabecera con pill de estado, Editar bajo la imagen, sección "Partes del Modelo" con contador y tarjetas por ítem) según el DDR, sin cambiar comportamiento ni API.

## Context
Ver `docs/tasks/TASK-vehiculo-detalle-partes-ui.md`. La pantalla ya existe y funciona; el cambio es visual y de composición. El pedido en React/Tailwind se tradujo a Bootstrap 5 (precedente: TASK-credencial-detalle-layout). La imagen de referencia no se recibió.

## Current behavior
- `panel_admin/src/app/vehicles/models/model-view.component.html:2-8` breadcrumb ya correcto.
- `:19-39` cabecera: imagen con fallback (`:21-27`), `dl` Marca/Modelo/Estado con estado en texto plano (`:36`).
- `:40` botón Editar `btn btn-primary` bajo toda la cabecera, sin ícono.
- `:42-77` `<h5>Items</h5>` + "Agregar item" outline, sin contador; `ul.list-group` con `li.list-group-item`; detalle `Ancho: x · Largo: y · Cantidad: z` (`:55`); botones `btn-tbl-edit` / `btn-tbl-delete` (`:59-66`).
- `model-view.component.ts` expone `items`, `openEditItem(item, tpl)`, `removeItem(item)`, `openAddItem(tpl)`; imports `[ReactiveFormsModule, RouterLink]`.
- `model-view.component.spec.ts:126-130` localiza el botón de editar con el selector `li.list-group-item button[title="Editar"]`.

## Expected behavior
Según el DDR: card `shadow-sm rounded-3`; cabecera con imagen + Editar (ícono `fa-pen`) debajo, título/Marca/Modelo y pill Activo/Inactivo; encabezado "Partes del Modelo" + "N Ítems Asociados" + botón "Agregar Item" con `fa-plus`; lista `d-flex flex-column gap-3` de tarjetas con `Dimensiones: Ancho: 1.20m x Largo: 0.80m | Cantidad: 2` y botones de ícono Editar/Quitar; estados de carga/error/vacío conservados.

## Architecture considerations
- **Contrato API:** sin cambios; `width`/`length` siguen llegando como string y solo se formatean en la vista.
- **Datos / migraciones / dinero / rendimiento:** no aplican (sin backend; las dimensiones no son dinero).
- **Seguridad/permisos:** sin cambios; las acciones se muestran siempre como hoy (el DDR no introduce ocultamiento por privilegio).
- **Acoplamiento:** el componente nuevo es presentacional (inputs/outputs); la lógica (modales, SweetAlert, servicio) permanece en `ModelViewComponent`. El fallback `imageFailed` del PR #58 se conserva.
- **Consistencia visual:** se traduce el DDR; reutiliza `btn-tbl-*` de `assets/scss/override/_table.scss:434-470`. Sin SCSS nuevo salvo que la verificación visual lo exija.

## Proposed solution
1. Nuevo `ModelItemCardComponent` standalone (`vehicles/models/model-item-card.component.ts/.html`), `input() item: AppCarModelPart`, `output() edit` y `output() remove`, con `DecimalPipe` (`'1.2-2'`) para ancho/largo. Selector `app-model-item-card`.
2. Reescribir el template de `model-view.component.html` según el DDR y usar `<app-model-item-card>` dentro de `@for`, enlazando `(edit)="openEditItem(item, editItemModal)"` y `(remove)="removeItem(item)"`.
3. `model-view.component.ts`: agregar `ModelItemCardComponent` a `imports`; sin cambios de lógica (el contador usa `items.length`, singular/plural en el template).
4. Los modales (`#addItemModal`, `#editItemModal`) no se tocan.

Alternativas (Tailwind, `VehicleHeader`/`Badge` genéricos, límite de 5-6 ítems) descartadas en el DDR.

## Files/components affected
- Frontend (`panel_admin/`): `src/app/vehicles/models/model-view.component.html`, `model-view.component.ts`, `model-view.component.spec.ts`; nuevos `model-item-card.component.ts`, `.html`, `.spec.ts`.
- Backend: ninguno.

## Implementation steps
1. Crear `ModelItemCardComponent` + spec.
2. Reescribir el template de `model-view` (cabecera, encabezado con contador, lista de tarjetas, vacío) e importar el componente.
3. Actualizar `model-view.component.spec.ts`: el selector de `clickEditButton` pasa a `app-model-item-card button[title="Editar"]`; agregar los casos nuevos.
4. Correr `npm test` (headless), `npm run lint` y `npm run build` en `panel_admin/`.
5. Verificación manual en vivo con `ng serve` contra el backend local (tema claro/oscuro, ancho móvil, modelo con y sin imagen/items) y dejar constancia en el TASK.

## Test strategy
- **Unit (Karma/Jasmine, `TestBed` + `HttpTestingController`, patrón ya usado en `model-view.component.spec.ts`):**
  - `ModelItemCardComponent`: muestra el nombre; formatea `'1.2'`/`'0.8'` como `Ancho: 1.20m x Largo: 0.80m`; muestra `| Cantidad: N`; clic en Editar/Quitar emite el evento correspondiente.
  - `ModelViewComponent`: contador "5 Ítems Asociados" / "1 Ítem Asociado"; pill "Activo"/"Inactivo" según `is_active`; botón Editar enlaza a `/vehicles/models/edit/:id`; estado vacío sin tarjetas; los specs existentes (fallback de imagen, agregar/editar/quitar item) siguen pasando con el selector actualizado.
- **Integración:** cubierta por los specs de `model-view` con `HttpTestingController`; no hay cambios de API.
- **E2E (Playwright): NO.** Es un cambio visual de una sola pantalla sin cambio de flujo, navegación ni integración; agregar/editar/quitar ya tienen specs y no cambian. No se instala Playwright.
- Verificación visual manual (paso 5), porque el resultado es esencialmente estético.

## Acceptance criteria
- La vista muestra imagen con Editar debajo, Marca, Modelo y estado como pill (verde Activo / gris Inactivo).
- Encabezado "Partes del Modelo" con contador correcto y botón "Agregar Item" que abre el modal existente.
- Cada ítem es una tarjeta independiente en una sola columna con `Dimensiones: Ancho: X.XXm x Largo: Y.YYm | Cantidad: Z` y botones Editar/Quitar funcionales (mismos modales y confirmación).
- Estado vacío, carga, error y fallback de imagen rota siguen funcionando.
- Se ve correcto en ancho móvil y en tema claro/oscuro.
- `npm test`, `npm run lint` y `npm run build` en `panel_admin/` sin errores.
- Sin cambios de backend ni dependencias nuevas.

## Risks
- Colores de botones y pill pueden no coincidir con la imagen de referencia (no recibida): se ajusta tras verla; el DDR lo declara.
- `*-subtle` de Bootstrap pueden verse mal en tema oscuro: se verifica manualmente; si falla, estilos mínimos locales.
- Specs acoplados al markup (`li.list-group-item`): se actualizan en el paso 3.
- Un valor nulo o no numérico en `width`/`length` con `DecimalPipe` mostraría vacío; la API los devuelve siempre como decimal, no se añade manejo especial.

## Out of scope
- Cambios de backend/API, ocultar acciones por privilegio, límite de 5-6 ítems, páginas de edición/creación de modelo, `VehicleHeader`/`Badge` genéricos.
- Preguntas abiertas: ¿colores exactos de la imagen de referencia? ¿el "máximo 5-6 ítems" es solo ejemplo?

## Dependencias nuevas
Ninguna.
