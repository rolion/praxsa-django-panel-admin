# DDR-modulo-ordenes-proforma-nota-trabajo-listado-y-flujo-ordenes: Menú, listados y formularios de Proformas y Notas de Trabajo en `panel_admin/`

**Estado:** Propuesto
**Task relacionado:** TASK-modulo-ordenes-proforma-nota-trabajo
**Fecha:** 2026-09-29

## Actualización (2026-09-29, layout del detalle)

Tras ver el formulario implementado, el usuario pidió que cada línea del detalle ocupe **una sola fila** de una **tabla**, con el **total al final alineado con la columna Subtotal**. Reemplaza lo descrito antes como "recuadros repetibles por línea":
- Columnas con instalación: Item, Lámina (bobina), Ancho, Largo, Cantidad, Precio lámina, Precio instalación, Subtotal y quitar. Metro lineal omite Item, Cantidad y Precio instalación.
- Ancho, precios y subtotal son de solo lectura (texto); Item, bobina, largo y cantidad son controles compactos.
- Los avisos de ancho/stock van en una fila debajo de la línea afectada; el pie de la tabla muestra el Total bajo Subtotal. Descuento y "Total a pagar" quedan debajo de la tabla.

## Actualización 2 (2026-09-29, rediseño visual del formulario)

El usuario pidió mejorar UX/UI del formulario: secciones en tarjetas (Venta, Cliente, Vehículo, Detalle de items, Descuento y totales) con encabezado e ícono, sombras suaves y bordes redondeados; íconos en los campos (usuario, correo, teléfono, CI/NIT, vehículo, placa); campos bloqueados/solo lectura en gris con candado (tipo de venta y sucursal al editar; ancho, precios y subtotal); alertas por línea (amarillo = stock insuficiente, rojo = "Ancho insuficiente: mínimo requerido X m"); resumen destacado a la derecha con Total, Descuento y Total a pagar; botones primario (Crear proforma) y secundarios (Cancelar, Agregar item) con hover. Se mantiene la tabla de una fila por línea con el total bajo Subtotal. Solo cambia presentación (`proforma-form.component.html/.scss`); no cambia contrato de API ni reglas.

## Actualización 3 (2026-09-29, detalle de la vista con ngx-datatable)

En "Ver proforma" el detalle deja de ser una tabla Bootstrap simple y pasa a `ngx-datatable` (mismo componente que los listados). Las columnas con importes van alineadas a la derecha y el **resumen (Total, Descuento, Total a pagar)** se muestra en la fila de resumen de la propia tabla: los importes quedan justo debajo de la columna Subtotal y las etiquetas en la columna anterior. El formulario de crear/editar mantiene su tabla editable (los controles de entrada no encajan en `ngx-datatable`).

## Actualización 4 (2026-09-29, rediseño de "Ver proforma")

La vista de consulta se alinea con el formulario: tarjetas independientes **Datos de venta**, **Datos del cliente**, **Datos del vehículo** y **Detalle de items**; los datos van en grid de 2 a 4 columnas (etiqueta pequeña gris en mayúsculas, valor en negrita). La fecha se muestra como `27/02/2026 - 00:55 h`. El estado es un badge: azul "Proforma", verde "Nota de trabajo generada", ámbar "Por cobrar", verde oscuro "Finalizado". El detalle sigue en `ngx-datatable` (Actualización 3) y el bloque de totales queda abajo a la derecha, bajo Subtotal, con **Total a pagar** en un recuadro de fondo diferenciado. Barra de acciones al pie: "Editar" (secundario con borde), "Generar nota de trabajo" (verde, primario de éxito) y "Descargar PDF" (neutro con ícono), más un enlace "Volver al listado". En metro lineal se omiten Marca y Modelo con una nota aclaratoria.

## Actualización 5 (2026-09-29, modelo opcional en metro lineal y medidas de referencia)

Corrige lo decidido antes ("metro lineal no lleva modelo"): en **venta por metro lineal** el selector de **Modelo** se muestra como **(Opcional)** junto a **Placa (opcional)**, y si se elige se guarda en la proforma (sin efecto en el precio). Al elegir un modelo, en cualquier tipo de venta, aparece bajo el detalle un panel colapsable de solo lectura **"Medidas de referencia del modelo"**, con fondo tenue y la nota "Medidas de referencia del vehículo seleccionado. Utiliza estos datos para calcular los metros a vender.", con una tabla Item / Pieza, Ancho requerido, Largo sugerido y un botón "Copiar medida" (copia "ancho x largo" al portapapeles). En "Ver proforma" se muestran Marca y Modelo en metro lineal cuando existen. No cambia el contrato de la API: el backend ya aceptaba `car_model_id` opcional en metro lineal.

## Actualización 6 (2026-09-29, rediseño de "Ver nota de trabajo")

La vista de la nota de trabajo adopta el mismo sistema visual que "Ver proforma" (estilos en `ordenes/orden-view.shared.scss`): tarjetas **Datos de la orden** (Proforma Nº con enlace, tipo de venta, sucursal, estado, código de garantía), **Datos del cliente y vehículo** (cliente, modelo, placa) y **Control operativo y tiempos** (entrada y salida como `05/08/2025 - 04:16 h`, responsable, instalador, observaciones), en grid etiqueta gris / valor en negrita. Los vacíos se muestran tenues y en cursiva ("Sin código", "Aún no registrada", "No asignado", "Sin observaciones"). Badge de estado: ámbar "En ejecución" y verde "Finalizado". Debajo, dos tablas `ngx-datatable` independientes: **Resumen de láminas usadas** (Lámina, Ancho, Metros; fondo tenue) y **Detalle de la proforma** (Item, Lámina, Ancho, Largo/Metros, Cantidad; Item y Cantidad solo con instalación), con cabeceras grises y números a la derecha. Acciones al pie: "Editar nota de trabajo" (primario, según permiso y estado), "Ver proforma" (secundario) y "Volver al listado". Solo presentación.

## Contexto

La investigación del task confirmó que Proformas y Notas de Trabajo solo se gestionan hoy desde Django Admin (`ProformaAdmin`, `NotaTrabajoAdmin`) y que `panel_admin/` no tiene pantallas ni API para ellas. Las reglas de negocio ya existen (dos tipos de venta con fórmulas distintas, pipeline proforma → nota de trabajo → nota de venta → pago); este DDR solo define **qué ve y hace la persona**, no cómo se expone.

Se resolvieron con el usuario las preguntas abiertas de la investigación que condicionaban el diseño:

1. **Crear proforma desde el panel: SÍ** (listar, ver, editar y crear).
2. **Selección de bobina**: la proforma carga las bobinas **disponibles en la sucursal**; al elegir una bobina se carga su ancho (y sus metros disponibles). Al elegir el item del vehículo (venta con instalación) se precargan el **largo a cortar** y la **cantidad** necesarios, y con eso se calcula el subtotal. Esto resuelve la duda "¿de dónde sale el ancho en metro lineal?": sale de la bobina elegida.
3. **Nota de Trabajo**: listado + Ver + Editar campos operativos (instalador, código de garantía, salida del vehículo, observaciones). No se crea a mano; nace de la proforma.
4. **Acciones extra en la tabla de proformas**: **Generar nota de trabajo** y **PDF de la proforma**, además de Ver y Editar. Eliminar y Reabrir **no** entran.

## Pantallas/flujos afectados

1. **Menú principal**: nuevo grupo "Órdenes" con 2 submenús: Proforma, Nota de Trabajo.
2. **Proformas — listado** (`/ordenes/proformas`): tabla con todas las proformas visibles para el usuario. Acciones por fila: Ver, Editar, Generar nota de trabajo, PDF. "Nueva proforma" en el header.
3. **Proformas — crear** (`/ordenes/proformas/create`): formulario con selector de tipo de venta y detalle según el tipo (ver abajo).
4. **Proformas — ver** (`/ordenes/proformas/view/:id`): detalle de solo lectura (cabecera, cliente, vehículo, líneas, descuento y total a pagar, estado, nota de trabajo asociada si existe).
5. **Proformas — editar** (`/ordenes/proformas/edit/:id`): mismo formulario que crear, precargado.
6. **Notas de Trabajo — listado** (`/ordenes/notas-trabajo`): tabla de solo consulta con Ver y Editar por fila.
7. **Notas de Trabajo — ver** (`/ordenes/notas-trabajo/view/:id`): detalle de solo lectura (datos de la proforma, vehículo, resumen de láminas usadas, campos operativos).
8. **Notas de Trabajo — editar** (`/ordenes/notas-trabajo/edit/:id`): formulario acotado a los campos operativos.

### Columnas de las tablas

- **Proformas**: Nº, Tipo de venta, Cliente, Sucursal (para quien ve varias), Modelo (vacío en metro lineal), Total a pagar (`total_price - discount`), Fecha, Estado (`proforma` / `nota_trabajo` / `por_cobrar` / `finalizado`), Acciones.
- **Notas de Trabajo**: Nº (el de la proforma), Fecha ingreso, Cliente, Modelo, Placa, Instalador, Finalizado (Sí/No), Sucursal, Acciones.

### Formulario de proforma (crear / editar)

Cabecera común: tipo de venta, sucursal, cliente (nombre, email, CI/NIT, teléfono), descuento y motivo. La lista de líneas cambia según el tipo de venta:

**Venta con instalación**
- Vehículo: placa y **modelo** (selector, con marca).
- Por línea: **item** del modelo (solo los items asociados al modelo elegido) → al elegirlo se precargan **largo** y **cantidad**; **bobina/lámina** (solo las disponibles en la sucursal) → al elegirla se carga el **ancho**. Se muestran precio de lámina, precio de instalación y **subtotal** calculado. Se avisa en la línea si el ancho de la bobina es menor que el del item.
- Fórmula que la persona ve reflejada: `largo × cantidad × precio lámina + precio instalación × cantidad`.

**Venta por metro lineal**
- **Sin** modelo de vehículo ni item (placa opcional).
- Por línea: **bobina/lámina** (disponibles en la sucursal; al elegirla se carga el ancho y se muestran los metros disponibles) y **metros** (campo numérico, con tope visible en los metros disponibles). Subtotal = `metros × precio lámina`. Sin cantidad ni precio de instalación.
- Este flujo es una interpretación de lo respondido: la precarga de "largo y cantidad" por item es del tipo con instalación; en metro lineal los metros los escribe la persona.

**Ambos tipos**: total de la proforma = suma de subtotales; total a pagar = total − descuento. Los importes mostrados son una **vista previa**: el valor definitivo lo recalcula y persiste el servidor.

**Edición**: el tipo de venta y la sucursal se muestran pero no se pueden cambiar (mismo criterio que `proforma_admin.py:187-193`). Una proforma cerrada (con nota de trabajo) no ofrece Editar.

### Acciones de la tabla de proformas

- **Ver** y **Editar**: mismos botones que el resto del panel (`btn-tbl-view`, `btn-tbl-edit`).
- **Generar nota de trabajo**: botón con ícono propio, visible solo si la proforma aún no tiene nota de trabajo. Pide confirmación con SweetAlert2 explicando que **descuenta inventario y cierra la proforma**; si el servidor rechaza (p. ej. sin stock) se muestra el mensaje devuelto. Tras el éxito la fila pasa a estado "Nota Trabajo" y el botón se oculta (el de Editar también).
- **PDF**: descarga el PDF de la proforma (`helper/pdf.py:378`, hoy disponible solo como acción de Django Admin).

## Componentes/patrones elegidos

- **Menú**: nuevo grupo en `panel_admin/src/assets/data/routes.json` con la misma forma que "Usuarios", "Vehículos" y "Almacén" (`"class": "menu-toggle"`, submenús `"ml-menu"`, ícono feather). Sin alternativa: es el único patrón de menú multinivel del proyecto (`docs/frontend/panel_admin/reference.md:92` menciona el patrón multinivel de la plantilla).
- **Tablas**: `ngx-datatable` con búsqueda client-side, mismo markup que `almacen/inventario/inventario-list.component.html:26-64` (`table-search-area`, ícono `search`, `filterDatatable($event)`, `[limit]="10"`) y la columna Acciones de las líneas 71-91 (botones `btn-tbl-view`/`btn-tbl-edit`, `h-auto`). Es el ejemplo real citado en `docs/frontend/panel_admin/reference.md:85` (`advance-table/`).
- **Botón "Nueva proforma"**: mismo `btn-primary rounded-button` con ícono `add` que `inventario-list.component.html:35-43`.
- **Formularios**: páginas separadas con `ReactiveFormsModule`, mismo layout de card/breadcrumb y clases `form-select form-control`, `fw-bold`, mensaje `text-danger` tras intentar enviar y `alert alert-danger` para el error del servidor que `almacen/inventario/inventario-create.component.html:9-96` ya usa (patrón de validación de `form-validation.html`, `reference.md:87`). Se usa el patrón de "entidad rica" (páginas `list`/`create`/`view`/`edit`) porque la proforma tiene líneas y detalle propio.
- **Líneas de proforma**: filas repetibles dentro del formulario (alta/baja de línea con botones), sin componente nuevo de la plantilla — la plantilla no trae un editor de líneas y los formularios existentes no lo necesitaron. Es la pieza nueva más grande del módulo.
- **Vista de detalle**: layout `dl`/`dt`/`dd` de las vistas `*-view` existentes (mismo criterio que `DDR-modulo-almacen-listado-y-flujo-almacen`).
- **Confirmaciones**: SweetAlert2, como el resto de acciones del panel.
- **Selectores dependientes** (modelo → items; sucursal → bobinas disponibles): reutilizar los servicios de Vehículos y Almacén ya existentes para poblar catálogos; el diseño solo exige que los selectores ofrezcan **registros activos** (mismo criterio que `ADR-modulo-vehiculos-soft-delete`).

## Alternativas consideradas

- **Un único formulario con todos los campos siempre visibles** (item, cantidad, instalación aunque sea metro lineal). Se descarta: el propio backend prohíbe `quantity` e `installation_price` en metro lineal (`Forms/car_model_part.py:112-118`); mostrar campos que se rechazan solo genera errores.
- **Modal en vez de páginas separadas** para crear/editar proforma. Se descarta: cabecera + varias líneas con campos dependientes no caben en un modal sin volverlo el más denso del proyecto; mismo argumento que se usó para pasar Inventario a páginas.
- **Generar la nota de trabajo desde un formulario aparte**. Se descarta: en el Django Admin es una acción sobre filas de la tabla (`proforma_admin.py:248-253`) y no pide datos adicionales; un botón con confirmación es suficiente y más consistente.
- **Permitir crear Notas de Trabajo a mano desde su listado**. Se descarta por decisión del usuario y porque el negocio las genera desde la proforma (`Proforma_Business.create_work_note`).
- **Incluir Eliminar y Reabrir en la tabla**. Se descarta por decisión del usuario (alcance); quedan como posible ampliación.
- **Reusar `AdvanceTableComponent` como dependencia**. Se descarta por lo ya decidido en los DDR de Usuarios/Vehículos/Almacén: es una página de ejemplo autocontenida, no un componente parametrizable.

## Comportamiento por privilegio/estado

| Situación | Comportamiento visual |
|---|---|
| Proforma **abierta** (sin nota de trabajo) | Ver, Editar, Generar nota de trabajo y PDF visibles |
| Proforma **con nota de trabajo** (cerrada) | Solo Ver y PDF; Editar y Generar nota **ocultos** |
| Nota de Trabajo con nota de venta (Finalizado = Sí) | Editar oculto; solo Ver |
| Usuario sin sucursal asignada | El listado muestra el mensaje "Asigne una sucursal al usuario" (hoy lo hace Django Admin, `proforma_admin.py:179-185`) en vez de una tabla vacía sin explicación |
| Usuario que ve varias sucursales | Columna y selector de Sucursal visibles; con una sola, la sucursal se fija y se muestra como solo lectura |

Los botones no autorizados **se ocultan** (no se deshabilitan), igual que en Almacén.

**Nota explícita de seguridad — esto es solo UX, no la barrera real.** Ocultar botones no impide que alguien llame al endpoint directamente. La aplicación real de: (a) qué proformas/notas ve cada rol o sucursal (hoy con criterios inconsistentes en `Proforma_Business`/`Orden_Trabajo_Business`), (b) quién puede editar, generar nota de trabajo o descargar el PDF, y (c) que una proforma cerrada no se pueda editar, es responsabilidad de `delivery-architect` y del backend. Requiere que arquitectura defina cómo se verifican esos permisos del lado servidor — el frontend no debe ser la única barrera. Este DDR tampoco decide qué rol exacto puede cada acción.

## Consecuencias

- Órdenes queda visualmente consistente con Usuarios, Vehículos y Almacén (mismas clases de botón, búsqueda client-side, breadcrumbs y cards).
- Se introduce el primer **formulario con líneas repetibles y campos dependientes** del panel; será la pieza de mayor esfuerzo y de mayor riesgo de UX (precarga por item, ancho por bobina, avisos de ancho insuficiente).
- El subtotal mostrado en pantalla es una vista previa; **puede diferir del valor final** que persiste el servidor (ADR-004/ADR-006: el servidor sobrescribe siempre). Arquitectura debe definir cómo el frontend obtiene los precios/stock de bobina por sucursal y cómo se informa al usuario si el servidor ajusta un importe.
- Bobina y ancho pasan a ser el eje de la línea en ambos tipos de venta; el selector debe mostrar solo bobinas con stock en la sucursal, lo que exige que el backend exponga esa lista (decisión de arquitectura).
- Queda pendiente y fuera de este DDR: paginación de la tabla (sin paginación DRF global), rol exacto por acción, qué hace el PDF para proformas de metro lineal (el helper actual asume item), y una eventual ampliación con Eliminar/Reabrir/Crear nota de venta.
- Otras pantallas quedarían inconsistentes solo si se decide después ocultar/deshabilitar por rol de otra forma; no se les exige ningún cambio.
