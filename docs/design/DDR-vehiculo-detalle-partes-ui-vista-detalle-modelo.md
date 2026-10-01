# DDR-vehiculo-detalle-partes-ui-vista-detalle-modelo: Vista de detalle de Modelo con lista de Partes en tarjetas

**Estado:** Propuesto
**Task relacionado:** TASK-vehiculo-detalle-partes-ui
**Fecha:** 2026-10-01

## Contexto

La vista `Ver modelo` (`panel_admin/src/app/vehicles/models/model-view.component.html`) ya existe y es funcional (imagen, datos, Editar, items con Editar/Quitar, modales, estado vacío). El pedido llegó redactado para React/Tailwind/Lucide y con una imagen de referencia que no se recibió; `panel_admin/` es Angular 21 + Bootstrap 5.3 (`docs/frontend/panel_admin/reference.md`, tabla de versiones) sin Tailwind ni Lucide. Siguiendo el precedente `DDR-credencial-detalle-layout-vista-detalle-chips`, se traduce el look pedido a Bootstrap sin dependencias nuevas. Es un DDR solo de UI: sin cambios de API ni modelo (`items_count`, `car_brand_name`, `is_active`, items con `width/length/quantity` ya llegan).

## Pantallas/flujos afectados

- **Ver modelo** (`/vehicles/models/view/:id`, existente): la persona revisa marca/modelo/estado e imagen, va a editar el modelo, y administra sus partes (agregar, editar medidas, quitar). Los modales de agregar/editar item y la confirmación SweetAlert para quitar **no cambian**. No se crean pantallas nuevas.

## Componentes/patrones elegidos

- **Traducción Tailwind → Bootstrap:** utilidades y componentes de Bootstrap 5.3; no se agrega Tailwind/Lucide. Íconos Font Awesome, como el resto del panel.
- **Contenedor:** `card` de la plantilla con `shadow-sm` y `rounded-3` (equivalente a `rounded-xl`/`shadow-sm`), ancho `col-12 col-xl-10`. El fondo de página `#F8FAFC` **no se fuerza**: lo define el tema de la plantilla (claro/oscuro); forzarlo rompería el tema oscuro.
- **Breadcrumb:** se mantiene tal cual (`Ver modelo › ícono fa-car › Modelos`, ya cumple lo pedido).
- **Cabecera (flex, columna bajo `md`, fila desde `md`, `gap-4`):**
  - Izquierda: imagen (conserva fallback `imageFailed` → placeholder `fa-image`, requisito del PR #58) y **debajo de la imagen** el botón `btn btn-primary` con ícono `fa-pen` + "Editar" (hoy está bajo toda la cabecera y sin ícono).
  - Derecha: `dl` Marca / Modelo (el nombre del modelo como título `h4`) y estado como **pill** `badge rounded-pill bg-success-subtle text-success-emphasis` "Activo" / `bg-secondary-subtle text-secondary-emphasis` "Inactivo".
- **Encabezado de sección (`border-top`, `mt-4 pt-4`, flex `justify-content-between align-items-center`):** `h4.fw-bold` "Partes del Modelo", debajo `text-muted small` "N Ítems Asociados" (`items.length`, singular "1 Ítem Asociado"); a la derecha `btn btn-primary btn-sm` con `fa-plus` "Agregar Item" (mantiene la acción que abre el modal existente).
- **Lista de items:** `d-flex flex-column gap-3` (una sola columna, sin `list-group`); cada item es una tarjeta `border rounded-3 p-3 d-flex justify-content-between align-items-center bg-body`:
  - Izquierda: nombre `fw-semibold`; debajo `text-muted small`: `Dimensiones: Ancho: 1.20m x Largo: 0.80m | Cantidad: 2`. Ancho/largo se formatean con `number:'1.2-2'` + `m` (el backend manda strings tipo `'1.2'`).
  - Derecha: dos botones compactos de solo ícono, reutilizando `btn-tbl-edit` (`fa-pen`) y `btn-tbl-delete` (`far fa-trash-alt`) de `assets/scss/override/_table.scss:434-470`, los mismos de Credenciales. Con `title`/`aria-label` "Editar" y "Quitar" (el botón sigue desasociando, no borra del catálogo).
- **Modularización:** se extrae `ModelItemCardComponent` (standalone, en `vehicles/models/`, inputs `item`, outputs `edit`/`remove`) porque es la pieza repetida; la cabecera y el badge quedan inline en la vista. No se crean `VehicleHeader`/`Badge` genéricos ni carpeta `shared/` (no existe en `panel_admin/src/app/`, ver `reference.md`): serían abstracciones de un solo uso. La lista consume el array `items` ya cargado por la API (el requisito de "array JSON").
- **Estados:** carga, error y vacío se mantienen (vacío: "Este modelo todavía no tiene items asociados.", dentro de un recuadro punteado `border-dashed`/`text-muted` centrado, junto con el botón "Agregar Item" del encabezado).
- **Responsive:** bajo `sm` el botón "Agregar Item" pasa debajo del título; la tarjeta mantiene acciones a la derecha y el texto de dimensiones puede envolver.

## Alternativas consideradas

1. **Agregar Tailwind + Lucide** (literal al pedido): descartada por las mismas razones que en el DDR de credenciales: nueva dependencia de build, solape de utilidades con Bootstrap, riesgo para el resto de la plantilla.
2. **Extraer también `VehicleHeader` y `Badge` como componentes:** descartada; un solo consumidor, sin `shared/` existente. Se reconsideraría si otra pantalla (p. ej. detalle de marca) reutiliza el pill.
3. **Dejar todo inline sin `ItemCardComponent`:** más simple, pero el pedido pide modularidad y la tarjeta tiene markup suficiente para justificarla; costo bajo.
4. **Forzar `#F8FAFC` y `rounded-xl` con SCSS propio:** descartada; rompe el tema oscuro/colores de la plantilla (`config.service.ts`).
5. **Límite de 5-6 items:** descartada; se interpreta como el ejemplo de datos, no un límite funcional (un modelo puede tener más partes). Pendiente de confirmar con el usuario.

## Comportamiento por privilegio/estado

- Estado Activo/Inactivo cambia el pill (verde / gris). Sin imagen o imagen rota: placeholder. Sin items: estado vacío.
- Editar, Agregar Item, Editar item y Quitar se muestran siempre, como hoy; este DDR no introduce ocultarlos por privilegio. Si se ocultan o deshabilitan por permiso en el futuro, eso es solo UX: arquitectura/backend debe definir cómo se verifica el permiso del lado servidor. El frontend no debe ser la única barrera.

## Consecuencias

- La vista queda alineada con el look pedido y consistente con Credenciales, sin dependencias nuevas.
- Se acepta que el pedido en React/Tailwind/Lucide no se cumple a la letra, ni el color de fondo exacto.
- Los colores "azul/púrpura oscuro" y "naranja/rojo" del pedido se resuelven con los `btn-primary`/`btn-tbl-*` del tema; **no se verificó contra la imagen de referencia (no recibida)**. Si difiere, ajustar tras verla.
- Los specs actuales de `model-view` (imagen, `.fa-image`, modales, add/edit/remove) deben seguir pasando; el plan debe agregar specs para el contador (singular/plural), el formato de dimensiones y `ModelItemCardComponent`.
- Falta verificar en vivo el render de los `*-subtle` con el tema oscuro y colores de acento.
