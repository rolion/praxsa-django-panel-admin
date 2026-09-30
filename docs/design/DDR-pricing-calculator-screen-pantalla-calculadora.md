# DDR-pricing-calculator-screen-pantalla-calculadora: Pantalla "Calculadora de precios" (layout sin sidebar, stepper, tabla de ítems y resumen sticky) en `panel_admin/`

**Estado:** Propuesto
**Task relacionado:** TASK-pricing-calculator-screen
**Fecha:** 2026-09-30

## Contexto

El asesor hoy cotiza creando directamente una proforma (`/ordenes/proformas/create`), un formulario denso que pide datos del cliente antes de ver un precio. Se pide una pantalla de **cotizar primero**: elegir vehículo, elegir lámina por cristal, ver el total y recién entonces crear la proforma o consultar por WhatsApp. La investigación confirmó que la plantilla real es `panel_admin/` (Angular 21 standalone, Bootstrap 5 + SCSS, sin Tailwind), que no existe un layout sin sidebar, que el header no tiene logo, y que no existen en el código los conceptos de lámina "Recomendada", subtítulo ni ícono por cristal. Este DDR define **qué ve y hace la persona**; cómo se cablea (layout, cálculo, API, paso de datos a la proforma) es de `delivery-architect`.

Adaptaciones del prompt al repo, por coherencia con la plantilla (`docs/frontend/panel_admin/reference.md`, "Versiones reales instaladas" y `utilities.html`):
- Grid `col-lg-8` / `col-lg-4` de Bootstrap en lugar de `grid-cols-12` / `col-span-*` de Tailwind.
- Se usa el header de la plantilla (`app-header`), no un `app-navbar`.
- Componentes standalone con `@if` / `@for`, `ReactiveForms`, `FormArray` (mismo patrón que `ProformaFormComponent`).

## Pantallas/flujos afectados

1. **Calculadora de precios** (pantalla nueva, ruta propia, p. ej. `/calculadora`; el nombre exacto lo fija el plan). La persona:
   1. elige Sucursal, Marca y Modelo;
   2. ve los cristales del modelo y elige una lámina para cada uno;
   3. ve el total y decide **Crear Proforma** o **Consultar por WhatsApp**.
2. **Header de esta pantalla** (variante sin sidebar): logo PRAXSA a la izquierda, menú de perfil (nombre + Logout) a la derecha; sin toggle del sidebar ni right-sidebar.
3. **Entrada al flujo** desde el menú lateral de las demás pantallas y/o el botón del listado de proformas: decisión de ubicación en el plan. No se crean otras pantallas.
4. **Paso 3 "Proforma"**: no es una pantalla nueva; es el formulario existente `/ordenes/proformas/create`, al que se llega con los datos de la cotización ya cargados (ver "Crear Proforma").

## Componentes/patrones elegidos

| Zona | Elección | Base |
|---|---|---|
| Layout/header | Header de la plantilla en variante mínima: logo (`assets/images/praxsa-admin-logo.png`, hoy en sidebar y login) + dropdown de usuario (`ngbDropdown`, ya en el header) + fullscreen opcional. Sin toggle de sidebar (depende del sidebar). | `reference.md` estructura `layout/header`; header actual `header.component.html:1-30` |
| Título y stepper | Título "Calculadora de precios" con ícono de auto (Feather/FontAwesome ya cargados) y stepper **propio, ligero**, en Bootstrap/SCSS: 3 pasos (1 Vehículo, 2 Láminas, 3 Proforma), el activo se deriva del estado del formulario. No se usa `angular-archwizard` (está en `package.json` pero sin uso verificado y modela pasos como páginas separadas, acá es una sola pantalla). | `reference.md`, sección páginas de ejemplo (sin stepper dedicado) |
| Filtros | `card section-card` blanca con 3 `form-select` en fila (`row` / `col-md-4`), con íconos como en el formulario de proforma. Cascada: Marca filtra Modelo; Modelo habilita la tabla. Con una sola sucursal asignada se fija y se muestra en gris (mismo comportamiento que `proforma-form`). | `reference.md` → `form-elements.html`; `proforma-form.component.ts` (`onSucursalesLoaded`) |
| Tabla de ítems | Lista en **tabla Bootstrap** dentro de `section-card` (una fila por cristal) porque cada fila lleva un `select` editable; `ngx-datatable` no encaja con controles de entrada (criterio ya adoptado en el DDR de Órdenes, Actualización 3). | `reference.md` → tablas; DDR Órdenes |
| Resumen | `summary-card` existente como base, con `position: sticky` bajo el header, en `col-lg-4`. | `assets/scss/_ordenes.scss` (`.summary-card`, `.section-card`) |
| Estados | Skeletons con `.placeholder` / `placeholder-glow` de Bootstrap 5.3 (sin dependencias nuevas); estado inicial y vacío con ícono tenue + texto. | Bootstrap 5.3 ya instalado (`panel_admin/package.json:45`) |
| Estilos | Un bloque SCSS global acotado (`.pricing-calculator`) en `assets/scss/` siguiendo el patrón de `_ordenes.scss`, por el presupuesto de estilos de componente (REV-01 del módulo Órdenes). | TASK Órdenes, Quality Gate corrida 1 |

## Diseño de cada zona

**Stepper.** Paso 1 activo hasta elegir modelo; paso 2 activo con el modelo elegido; paso 3 se marca solo al pulsar "Crear Proforma" (momento en que se sale hacia el formulario). Pasos completados con check, pendientes en gris.

**Tabla de ítems.** Columnas: Ítem (ícono + nombre + subtítulo) · Lámina (select) · Subtotal (`Bs`) · acción. 
- *Ícono*: genérico de cristal, con mapeo por palabra clave del nombre del ítem (parabrisas, puerta, luneta…) y un ícono por defecto; es solo decoración, no dato.
- *Subtítulo*: se arma con datos reales del ítem del modelo: `Ancho × Largo m · Cantidad N`. No se inventa un campo nuevo.
- *Select de lámina*: lista solo láminas/anchos **aptos** para ese ítem y con stock en la sucursal, mostrando nombre, ancho y precio por metro; las no aptas no aparecen (evita el error "ancho insuficiente" del servidor). Primera opción: "Seleccionar lámina".
- *Badge "Recomendada"*: el espacio existe en la opción y en la fila seleccionada, pero **la regla que decide cuál es la recomendada no existe en el código ni en la documentación** (ver "Decisiones de negocio pendientes"). No se muestra ningún badge inventado.
- *Subtotal*: `Bs` + importe con formato es-BO (`Bs 2.090`); "—" si no hay lámina elegida.
- *Quitar*: el botón **excluye** el ítem del total (fila atenuada, subtotal "—", select deshabilitado) y cambia a "Restaurar"; no borra la fila (misma semántica que `removeReportItem` de `proforma/`). Sirve, por ejemplo, para un cliente que solo quiere parabrisas.
- *Alertas por fila*: reutiliza `.line-alert` (ámbar: metros justos/stock bajo; rojo: sin stock o sin lámina apta para ese ítem).
- *Pie de tabla*: alerta informativa "Los precios pueden variar según la disponibilidad de láminas…" (texto final a confirmar con negocio).

**Resumen sticky** (`col-lg-4`, `sticky` bajo el header):
1. Imagen del modelo (`AppCarModel.image`), con placeholder de auto si es `null`.
2. Título "Marca Modelo" y sucursal.
3. Desglose en texto pequeño: una línea por ítem activo con lámina (`Parabrisas · Lámina X — Bs 450`); los ítems sin lámina se listan como "pendiente".
4. **Total** destacado (recuadro de fondo diferenciado, como "Total a pagar" en Ver proforma).
5. **Crear Proforma** (primario) y **Consultar por WhatsApp** (secundario verde con ícono). Ambos deshabilitados hasta que exista al menos un ítem con lámina.

**Crear Proforma.** Lleva al formulario existente con sucursal, modelo y líneas (ítem + lámina/ancho + largo + cantidad) precargados; la persona completa los datos del cliente (obligatorios hoy) y guarda. Así no se duplican los campos ni las validaciones del cliente y el paso 3 del stepper queda coherente. Cómo viajan los datos entre pantallas es decisión de arquitectura.

**Consultar por WhatsApp.** Abre `wa.me` en pestaña nueva con un mensaje prearmado (vehículo, ítems con lámina y total). El número actual (`+59178181012`) está fijo en `proforma/`; si debe ser por sucursal queda como pregunta abierta.

**Estados** (mutuamente excluyentes, alternados con `@if`):
| Estado | Cuándo | Qué se ve |
|---|---|---|
| Inicial | Falta sucursal, marca o modelo | Ícono de auto tenue + "Selecciona sucursal, marca y modelo para cotizar"; resumen sticky vacío con total `Bs 0` y botones deshabilitados. |
| Cargando | Esperando ítems/bobinas | Skeletons: 5–6 filas de tabla y bloque de resumen; selects de filtros deshabilitados. |
| Sin resultados | Modelo sin ítems configurados, o sucursal sin bobinas con stock | Mensaje específico por causa ("Este modelo no tiene ítems configurados" / "No hay láminas con stock en esta sucursal") y acción de cambiar filtros. |
| Error | Falla la carga de catálogos | Alerta roja con "Reintentar" (no contemplado en el prompt; evita una pantalla muda). |
| Activo | Hay ítems | Tabla + resumen completos. |

**Responsive.** Desde `lg` hacia abajo las columnas se apilan: tabla primero y resumen debajo sin sticky; se añade una barra inferior fija con Total y "Crear Proforma" en móvil para no obligar a bajar. El stepper colapsa a solo números.

## Alternativas consideradas

- **Stepper con `angular-archwizard`** (ya instalado): descartada; impone una página/contenido por paso y las dependencias sin uso verificado; un stepper visual derivado del estado es más simple.
- **Crear la proforma dentro de la calculadora con un modal de datos del cliente**: descartada; duplicaría el formulario y sus validaciones (email, CI/NIT, teléfono, placa). Se prefiere reutilizar el formulario existente como paso 3.
- **`ngx-datatable` para la lista de ítems**: descartada; cada fila necesita un select editable, igual que en la tabla de líneas de `proforma-form`.
- **Badge "Recomendada" calculado en el front con una regla propia** (p. ej. la más barata): descartada; es una regla de negocio sin respaldo y mostraría una recomendación falsa. Queda como decisión pendiente.
- **Quitar ítem = borrar la fila**: descartada; impide restaurar y no refleja el comportamiento actual de `proforma/`.
- **Dejar el sidebar colapsado en lugar de quitarlo**: descartada por el requerimiento explícito de no mostrarlo.

## Comportamiento por privilegio/estado

- La pantalla la ve cualquier usuario staff autenticado con sucursal asignada. Sin sucursal asignada: alerta "Asigne una sucursal al usuario…" (mismo texto del formulario de proforma).
- **Crear Proforma** se **oculta** (no se deshabilita) a quien no tiene el permiso de crear proformas; la calculadora y WhatsApp siguen disponibles. Las sucursales del selector son solo las de su alcance.
- Esto es **decisión de UX, no de seguridad**. Requiere que arquitectura defina cómo se verifica del lado servidor el permiso de crear proforma y el alcance por sucursal de catálogos y cotización — el frontend no debe ser la única barrera. Los importes en pantalla son **vista previa**; el servidor recalcula al crear la proforma (ADR-004 y `ADR-modulo-ordenes-proforma-nota-trabajo-api-y-calculo`).

## Decisiones de negocio pendientes (no resolubles desde el código)

1. **Regla de "Recomendada"**: ¿qué lámina se recomienda por ítem y con qué criterio (stock, margen, más vendida, configurada por modelo)? Si requiere un dato nuevo, sería un cambio de modelo/API (arquitectura).
2. **Número de WhatsApp**: ¿uno global o por sucursal?
3. **Texto final de la alerta de precios** y formato de importes (`Bs 2.090` del prompt vs. `2090.00 Bs` de las pantallas de Órdenes).
4. **Ubicación de la entrada** a la calculadora (menú lateral, botón en el listado de proformas o ambos).

## Consecuencias

- **Más simple:** el asesor ve el precio antes de capturar datos del cliente; se reutiliza el formulario de proforma como paso 3 y sus estilos (`section-card`, `line-alert`, `summary-card`).
- **Deuda/consistencia aceptada:** la calculadora coexiste con la del cliente final en `proforma/` (Angular 16) y con el cálculo en `ProformaFormComponent`; el riesgo de triplicar la fórmula se debe cerrar en arquitectura reutilizando `ordenes.calc.ts`. El formato de importes puede diferir de las pantallas de Órdenes hasta decidir el punto 3.
- **Inconsistencias si no se actualizan después:** el header de las demás pantallas conserva el toggle del sidebar y no muestra logo; solo esta variante lo lleva.
- **Sin dependencias nuevas:** Tailwind no se adopta (ajeno a la plantilla y exigiría avisar antes, según `docs/CLAUDE.md`).
