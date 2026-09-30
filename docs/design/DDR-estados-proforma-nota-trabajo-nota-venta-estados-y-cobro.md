# DDR-estados-proforma-nota-trabajo-nota-venta-estados-y-cobro: Estados visibles, acciones de trabajo terminado y pantallas de Nota de Venta / Cobro en `panel_admin/`

**Estado:** Propuesto
**Task relacionado:** TASK-estados-proforma-nota-trabajo-nota-venta
**Fecha:** 2026-09-30

## Actualización 1 (2026-09-30, anulaciones por rol)

- Desaparece el botón **"Reabrir"** de la proforma. Su lugar lo toma **"Anular nota de trabajo"** (vista de la nota de trabajo; visible con `delete_nota_trabajo`, es decir Almacen y Admin; solo con NT `En proceso` y NV `Por cobrar`). Su confirmación (SweetAlert2) explica que cancela la nota de trabajo y la de venta, devuelve el inventario y deja la proforma **Vigente** para editarla o reaprobarla.
- Se agrega **"Anular nota de venta"** en el listado y la vista de la nota de venta (visible con `delete_nota_venta`: Caja, Vendedor y Admin). Solo habilitado con NV `Por cobrar` y trabajo `En proceso`; con trabajo `Terminado` queda **deshabilitado con tooltip** "El trabajo ya está terminado; corrija el trabajo antes de anular" (es una precondición de negocio, no un permiso). Misma confirmación y mismo efecto que anular la nota de trabajo.
- **"Aprobar y generar orden"** se muestra a quien tiene `add_nota_trabajo` (Vendedor y Admin) y **"Anular"** (proforma vigente) a quien tiene `delete_proforma_header` (Vendedor y Admin). Almacen no ve esos dos botones.
- La nota explícita de seguridad sigue vigente: la barrera real es el servidor (ver ADR de API y permisos).

## Contexto

La investigación del task mostró que "Finalizado" significa tres cosas distintas según la pantalla (proforma = existe un pago; nota de venta = pago cerrado; nota de trabajo = existe la nota de venta), que el panel muestra el estado de la proforma como texto plano en el listado y como badge solo en la vista (`proformas-list.component.html:81` vs. `_ordenes.scss:131-155`), y que **el panel no tiene pantallas de Nota de Venta ni de Pago** (hoy solo existen en Django Admin). La propuesta preliminar del task (no vinculante, la decisión de modelo es de `delivery-architect`) plantea un estado explícito por documento y una nota de venta que nace junto con la nota de trabajo en `por_cobrar`.

Este DDR define **qué ve y hace la persona**, asumiendo el vocabulario de estados de esa propuesta. Si `delivery-architect` cambia los nombres o el modelo, este DDR se actualiza (no se reescribe la UX).

Supuesto sin confirmar (a validar con el usuario antes de arquitectura): **no se puede cobrar antes de que el trabajo esté terminado** (sin anticipos). Si se admitieran anticipos, cambia el comportamiento del botón "Registrar pago" (ver tabla de estados).

## Pantallas/flujos afectados

Solo se tocan las pantallas que ya existen más dos nuevas; no se inventa ninguna otra.

1. **Proformas — listado** (`/ordenes/proformas`): la columna **Estado** pasa de texto plano a **badge** con el vocabulario unificado; se agrega filtro por estado (el backend ya acepta `?status=`, `ordenes_admin.py:91-92`).
2. **Proformas — ver** (`/ordenes/proformas/view/:id`): el badge de estado muestra el **estado global de la orden** (ver abajo) y el botón "Generar nota de trabajo" se rotula **"Aprobar y generar orden"**; se agrega un enlace a la nota de venta cuando existe.
3. **Notas de Trabajo — listado** (`/ordenes/notas-trabajo`): la columna "Finalizado (Sí/No)" se reemplaza por **Estado** (badge `En proceso` / `Terminado` / `Cancelada`) y una columna **Cobro** (`Por cobrar` / `Pagada`).
4. **Notas de Trabajo — ver / editar in-situ** (`/ordenes/notas-trabajo/view/:id`): el badge sigue el estado de la propia nota de trabajo; se agrega la acción **"Marcar trabajo terminado"** (barra inferior, junto a "Editar nota de trabajo") y un bloque **Cobro** de solo lectura con estado y total de la nota de venta.
5. **Notas de Venta — listado** (`/ordenes/notas-venta`, **nueva**): tabla de consulta con acciones Ver y **Registrar pago**.
6. **Notas de Venta — ver** (`/ordenes/notas-venta/view/:id`, **nueva**): detalle de solo lectura (cliente, total congelado, nota de trabajo y proforma de origen, estado) y, si ya hay pago, datos del pago (monto, tipo, registro contable, fecha, cuenta cerrada o no).
7. **Registrar pago** (modal, **nuevo**): se abre desde el listado o la vista de la nota de venta.
8. **Menú**: el grupo "Órdenes" suma el submenú **Nota de Venta** (`routes.json`).

### Vocabulario unificado de estados (lo que la persona ve)

| Documento | Estado | Badge (clases de `_ordenes.scss`) |
|---|---|---|
| Proforma | Vigente | `status-proforma` (azul) |
| Proforma | Aprobada | `status-nota` (verde) |
| Proforma | Anulada | gris (**clase nueva**) |
| Nota de trabajo | En proceso | `status-progress` (ámbar) |
| Nota de trabajo | Terminado | `status-done` (verde) |
| Nota de trabajo | Cancelada | gris (**clase nueva**, la misma que Anulada) |
| Nota de venta | Por cobrar | `status-cobrar` (ámbar) |
| Nota de venta | Pagada | `status-final` (verde oscuro) |
| Nota de venta | Anulada | gris (**clase nueva**) |

**Estado global de la orden** (solo lectura, es el que aparece en la columna Estado del listado de proformas y en la cabecera de la vista): `Proforma` → `En trabajo` → `Por cobrar` (trabajo terminado, sin pagar) → `Finalizado` (terminado y pagado) / `Anulada`. Reutiliza los colores actuales para que la migración visual sea mínima: `Proforma`=`status-proforma`, `En trabajo`=`status-progress`, `Por cobrar`=`status-cobrar`, `Finalizado`=`status-final`.

Regla de rotulado que corrige el problema de la investigación: **la palabra "Finalizado" solo aparece cuando el trabajo está terminado *y* pagado**. En la nota de trabajo nunca se usa "Finalizado" (se usa "Terminado").

## Componentes/patrones elegidos

- **Listados nuevos y modificados**: `ngx-datatable` con búsqueda client-side, mismo markup de `proformas-list.component.html:58-102` (`table-search-area`, `[limit]="10"`, columna Acciones con `btn-tbl-view`/`btn-tbl-edit`/`btn-tbl-activate`, `h-auto`). Cita: `docs/frontend/panel_admin/reference.md:85` (`advance-table/` real). Sin alternativa razonable: es lo que usa todo el módulo Órdenes.
- **Badges de estado**: extender `.status-badge` de `assets/scss/_ordenes.scss:131-155` con una sola clase neutra nueva (`status-void`) para anulados/cancelados; no se crea otro sistema de colores. Cita de tokens/utilidades: `reference.md:91` (`utilities.html`).
- **Vistas de detalle**: el mismo sistema de tarjetas grid etiqueta-gris / valor-negrita del DDR de Órdenes (Actualizaciones 4 y 6), tanto para Nota de Venta como para el bloque Cobro dentro de la nota de trabajo.
- **Registrar pago**: **modal** (patrón `NgbModal` de `@ng-bootstrap/ng-bootstrap`, ya instalado, `reference.md:8-15`) con 3 campos: tipo de pago (select: Efectivo / Tarjeta-QR), registro contable (texto, opcional, 7 caracteres como el modelo `pago`) y monto (**solo lectura**, igual al total de la nota de venta). Validación reactiva con el mismo patrón de mensajes de `form-validation.html` (`reference.md:87`) y `alert alert-danger` para el error del servidor. Confirmación previa con SweetAlert2, como el resto de acciones críticas del panel.
- **Acciones con confirmación** ("Aprobar y generar orden", "Marcar trabajo terminado", "Anular", "Anular nota de trabajo", "Anular nota de venta"): SweetAlert2 explicando el efecto (descuenta inventario / registra salida del vehículo / devuelve inventario), igual que "Generar nota de trabajo" hoy (`proformas-list.component.ts`, `generateNota`).
- **Filtro por estado en el listado de proformas**: un `<select>` compacto al lado del buscador, con el estilo de `form-select` que usan los formularios del módulo (`form-elements.html`, `reference.md:86`).

## Alternativas consideradas

- **Tres pantallas separadas de "cobro"** (nota de venta, pago, caja). Se descarta: el modelo tiene una nota de venta por pago (1:1), separar en dos pantallas duplicaría el listado sin aportar. Una sola pantalla Nota de Venta con acción "Registrar pago" alcanza.
- **Página completa en vez de modal para registrar el pago.** Se descarta: son 3 campos, uno de ellos de solo lectura; una página entera es desproporcionada (mismo criterio que se usó para no usar modal en la proforma, pero al revés: aquí sí cabe).
- **Mostrar los tres estados (proforma, nota de trabajo, nota de venta) como tres badges en cada fila del listado de proformas.** Se descarta: ruido visual y reintroduce el problema de que la persona tenga que interpretar combinaciones; se prefiere **un estado global derivado** en el listado y el detalle por documento en las vistas.
- **Ocultar la columna de estado de la nota de trabajo y dejar solo el de la nota de venta.** Se descarta: el operador de taller necesita saber si el trabajo está en proceso sin abrir cobros.
- **Permitir Registrar pago antes de terminar el trabajo** (anticipos). Se deja como alternativa abierta, pendiente de confirmar con el usuario; por defecto el botón aparece deshabilitado con tooltip "El trabajo aún no está terminado" (ver tabla).
- **Adoptar toda la sección de dashboards/charts de la plantilla para cuentas por cobrar.** Se descarta por sobreingeniería (`reference.md:89`); no lo pidió el requerimiento.

## Comportamiento por privilegio/estado

| Situación | Comportamiento visual |
|---|---|
| Proforma **vigente** | Ver, Editar, "Aprobar y generar orden", PDF, Anular |
| Proforma **aprobada** (con orden) | Solo Ver y PDF; Editar oculto; sin "Reabrir" (se hace anulando la nota de trabajo o la de venta, ver Actualización 1) |
| Nota de trabajo **En proceso** | Ver, Editar in-situ, **Marcar trabajo terminado** (exige garantía e instalador si es venta con instalación; si faltan, el botón queda deshabilitado con tooltip que indica qué falta, y el servidor igual lo rechaza) |
| Nota de trabajo **Terminado** con nota de venta **Por cobrar** | Solo Ver y "Corregir trabajo" (vuelve a En proceso); Editar in-situ oculto hasta corregir |
| Nota de trabajo con nota de venta **Pagada** | Solo Ver; sin Editar ni Corregir |
| Nota de venta **Por cobrar**, trabajo **En proceso** | "Registrar pago" **deshabilitado** con tooltip "El trabajo aún no está terminado" (deshabilitado y no oculto, porque la persona necesita saber por qué no puede cobrar todavía) |
| Nota de venta **Por cobrar**, trabajo **Terminado** | "Registrar pago" habilitado |
| Nota de venta **Pagada** | Sin "Registrar pago"; se muestran los datos del pago; "Anular pago" visible solo si la cuenta contable no está cerrada |
| Usuario sin sucursal asignada | Mismo mensaje "Asigne una sucursal al usuario" del listado de proformas, en los listados de nota de trabajo y nota de venta |

Los botones no autorizados **se ocultan** (no se deshabilitan), igual que en el resto del módulo, con la única excepción de "Registrar pago" y "Marcar trabajo terminado" cuando la causa es una **precondición de negocio** (no un permiso): ahí se deshabilita con tooltip para explicar el motivo.

**Nota explícita de seguridad — esto es solo UX, no la barrera real.** Ocultar o deshabilitar botones no impide llamar al endpoint directamente. La aplicación real de: (a) quién puede aprobar, terminar el trabajo, registrar o anular un pago y cerrar contablemente; (b) que las transiciones inválidas (pagar antes de terminar, editar una nota pagada, reabrir con pago hecho) se rechacen en el servidor; y (c) el alcance por sucursal de cada listado, es responsabilidad de `delivery-architect` y del backend. Requiere que arquitectura defina cómo se verifican esos permisos y precondiciones del lado servidor — el frontend no debe ser la única barrera. Este DDR tampoco decide qué rol exacto puede cada acción.

## Consecuencias

- Desaparece la ambigüedad de "Finalizado": un solo significado (terminado y pagado) y un vocabulario coherente entre listado, vista y nota de trabajo.
- El panel gana por primera vez las pantallas de **Nota de Venta** y **Pago**; hasta ahora solo se podían cobrar desde Django Admin. Son las dos pantallas nuevas de mayor esfuerzo (listado + vista + modal).
- Cambian textos y specs existentes: el botón "Generar nota de trabajo" pasa a "Aprobar y generar orden", la columna "Finalizado" del listado de notas de trabajo se reemplaza y `nota-trabajo-view.component.ts` (`statusText/statusClass/canEdit`, líneas 49-65) deja de derivar el estado de `is_finalizada`; hay que actualizar `notas-trabajo.components.spec.ts`, `proformas-list.component.spec.ts`, `proforma-view.component.spec.ts` y `proforma-form.component.spec.ts`.
- Se acepta conscientemente una clase de color nueva (`status-void`) y el uso de modal solo para el pago; el resto reutiliza patrones existentes.
- Queda pendiente y fuera de este DDR: nombres finales de estados y endpoints (arquitectura), si hay anticipos, permisos por rol, migración de datos existentes, paginación server-side de los nuevos listados, y el diseño de un eventual reporte de cuentas por cobrar.
- Django Admin seguirá mostrando sus propios rótulos hasta que se actualice; si conviven ambos, pueden aparecer nombres distintos para el mismo estado (inconsistencia transitoria que debe decidir arquitectura/plan).
