# DDR-inventario-alcance-sucursal-django-admin-sucursales-inactivas-y-filtro-reportes: Sucursales inactivas en solo lectura y filtro de sucursal multiselect en reportes

**Estado:** Propuesto
**Task relacionado:** TASK-inventario-alcance-sucursal-django-admin
**Fecha:** 2026-10-02

## Contexto

El task establece que el alcance por sucursal rige para todos los grupos (el admin deja de ver todo; solo el superusuario de Django conserva visión global) y en todo el sistema. Decisiones de negocio que condicionan la interfaz:

- Sucursal **inactiva** (`enable_to_install_windows_film=False`): se puede **ver** su información, pero **no agregar ni modificar** (inventario; proformas, notas de trabajo y notas de venta). Aplica a todos los grupos.
- El filtro de sucursal de los **reportes** pasa de selector único a **multiselect**.
- Admin sin sucursales: 0 filas, 0 datos.
- Módulo Usuarios: fuera de alcance.

Hechos del panel que condicionan el diseño (verificados):
- Listados de Órdenes (`proformas-list`, `notas-trabajo-list`, `notas-venta-list`) ya tienen filtro de sucursal: selector con "Todas" o texto fijo si hay una sola (`proformas-list.component.html:18-24`, `notas-venta-list.component.html:18-24`, `notas-trabajo-list.component.html:18-24`) y alerta `alert-warning` "Asigne una sucursal al usuario…" cuando no hay sucursales (`proformas-list.component.html:111-112`).
- Las acciones de escritura de Órdenes se muestran con banderas `canCreate`, `canEdit`, `canAnular`, `canGenerateNota`, `canPay`, `canCorregir`, `canTerminar`, etc. (`proformas-list.component.html:94,151-161`, `proforma-view.component.html:163-183`, `nota-trabajo-view.component.html:237-252`, `nota-venta-view.component.html:126-136`). Hoy se calculan por permiso y estado, no por sucursal.
- El formulario de proforma tiene un select de Sucursal con patrón de bloqueo visual `is-locked` + icono candado (`proforma-form.component.html:35-41`).
- El alta de inventario tiene el select de Sucursal con las sucursales en alcance (`inventario-create.component.html:16-21`) y el listado de inventario ya fija el selector con una sola sucursal (`inventario-list.component.html:51-58`, DDR `almacen-permisos-sucursal-filtros-filtros-y-selector-sucursal`).
- Reportes: `reporte-base.ts:31` define `sucursal` como `FormControl<number | null>`; `ventas-diarias.component.html:30-40` y `utilidad.component.html:30-40` muestran un `<select>` con "Todas" cuando hay más de una sucursal y un texto fijo cuando hay una.
- Ni `panel_admin/package.json` ni `src/app/` usan una librería de multiselect (`ng-select`, `ngx-mat-select` o similar; búsqueda sin resultados). `@ng-bootstrap/ng-bootstrap` 20.0.0 ya está instalado (`panel_admin/package.json:31`) y se importa en `bobinas-list.component.ts` y `precios-sucursal-list.component.ts`.

## Pantallas/flujos afectados

1. **Inventario — listado, ver, editar, crear** (`/almacen/inventario*`): filas de una sucursal inactiva se ven pero sin acciones de editar/eliminar/activar; el alta no ofrece sucursales inactivas.
2. **Proformas — listado, ver, crear/editar** (`/ordenes/proformas*`): proformas de una sucursal inactiva se ven pero sin Editar/Anular/Generar nota; el formulario de alta no ofrece sucursales inactivas.
3. **Notas de trabajo — listado y ver**: sin Editar/Terminar/Corregir/Anular para una sucursal inactiva.
4. **Notas de venta — listado y ver**: sin Cobrar/Anular/Anular pago para una sucursal inactiva.
5. **Reportes — Ventas diarias y Utilidad**: filtro de sucursal pasa a multiselect.
6. **Filtros de sucursal de los listados** (Inventario, Proformas, Notas): deben listar también las sucursales inactivas del usuario para poder consultarlas (lectura).

No se agregan pantallas nuevas.

## Componentes/patrones elegidos

- **Indicador de sucursal inactiva (todas las pantallas):** badge `badge badge-solid-orange`/`bg-warning` con el texto "Inactiva" junto al nombre de la sucursal en la columna Sucursal del listado, en el detalle (`info-label`/`info-value` ya usados) y en las opciones de los selectores ("La Paz (inactiva)"). Se usa solo marcado Bootstrap/estilos de la plantilla (`panel_admin_doc/utilities.html`, `reference.md` sección "Utilidades"); sin componente ni dependencia nuevos. Los nombres exactos de clases se fijan en implementación contra los estilos reales de la plantilla.
- **Acciones de escritura sobre filas de sucursal inactiva:** se **ocultan** (no se deshabilitan), el mismo criterio de los DDR previos. Se agrega una condición por fila (p. ej. `row.sucursal_activa` o una bandera equivalente) a las banderas existentes (`canEdit && row.status === 'proforma' && row.sucursal_activa`). En las vistas de detalle se muestra un aviso `alert alert-info` "Esta sucursal está inactiva: solo lectura" (patrón ya usado en `inventario-list.component.html:72-73`) en lugar de los botones.
- **Formularios de alta:** el select de Sucursal (`inventario-create`, `proforma-form`) ofrece solo sucursales **activas** del usuario; con una sola activa queda preseleccionado y bloqueado con el patrón `is-locked` + candado ya existente (`proforma-form.component.html:36-37`); con ninguna activa se muestra `alert alert-warning` "No tienes sucursales activas para registrar" y el formulario queda deshabilitado (el botón "Crear/+" del listado se oculta si no hay ninguna sucursal activa).
- **Selectores de filtro de sucursal de los listados:** incluyen las sucursales en alcance de lectura (activas e inactivas, estas marcadas "(inactiva)"). Con una sola sucursal se mantiene el texto fijo actual.
- **Reportes — multiselect:** menú desplegable con casillas, construido con `NgbDropdown` de `@ng-bootstrap/ng-bootstrap` (ya instalado; ver alternativas) y `form-check` de la plantilla (`panel_admin_doc/form-elements.html`). Contenido: casilla "Todas" + una casilla por sucursal del usuario; las inactivas aparecen con la etiqueta "(inactiva)". Texto del botón: "Todas las activas", el nombre si hay una, o "N sucursales". Con una sola sucursal se mantiene el texto fijo (sin menú), como hoy. El control del formulario pasa de `number | null` a una lista de ids (`number[]`); la lista vacía se trata como "todas las activas".
- **Qué significa "Todas" y cuáles quedan marcadas por defecto (propuesta a confirmar):** por defecto quedan marcadas **solo las sucursales activas**; las inactivas aparecen desmarcadas y se pueden marcar para consultar su histórico. Esto concilia las dos frases del pedido ("solo seleccionar las activas" y "se puede leer datos de una sucursal inactiva"). Si el negocio prefiere que los reportes ofrezcan solo las activas, basta con dejar de incluir las inactivas en la lista; el componente no cambia.

## Alternativas consideradas

- **`<select multiple>` nativo:** cero dependencias y trivial de implementar, pero exige Ctrl+clic para seleccionar varias, es difícil de usar en móvil y no tiene un "Todas" claro. Descartada.
- **Librería `ng-select` (u otra) para el multiselect:** mejor experiencia (búsqueda, chips), pero añade una dependencia nueva que `docs/CLAUDE.md` pide avisar antes y para tres o cuatro sucursales no se justifica. Descartada por ahora.
- **Menú con `NgbDropdown` + casillas (elegida):** usa una dependencia ya instalada, es consistente con Bootstrap 5 y escala bien a pocas sucursales; menos pulido que `ng-select` pero suficiente.
- **Deshabilitar botones con tooltip en vez de ocultarlos:** mostraría que existe una acción bloqueada, pero los DDR previos fijaron ocultar y un botón deshabilitado en una vista de solo lectura confunde. Se mantiene ocultar, con el aviso "sucursal inactiva: solo lectura" en el detalle para explicar el porqué.
- **No marcar visualmente las sucursales inactivas:** más limpio, pero el usuario no entendería por qué desaparecen botones en unas filas. Descartada.
- **Ocultar por completo las filas de sucursales inactivas:** contradice la decisión "se puede leer". Descartada.

## Comportamiento por privilegio/estado

| Situación | Ver datos | Crear / editar / anular / cobrar | Selector en altas | Filtro del listado |
|---|---|---|---|---|
| Sucursal activa y asignada | Sí | Según permiso Django | Ofrecida | Ofrecida |
| Sucursal inactiva y asignada (cualquier grupo) | Sí, con badge "Inactiva" | No: botones ocultos y aviso en el detalle | No ofrecida | Ofrecida, marcada "(inactiva)" |
| Sucursal no asignada (cualquier grupo, incluido admin) | No | No | No | No |
| Usuario sin sucursales (incluido admin) | 0 filas, aviso existente "Asigne una sucursal…" | Botones de alta ocultos | — | — |
| Solo sucursales inactivas asignadas | Sí | Botones de alta ocultos; aviso "No tienes sucursales activas" | Vacío | Ofrecida |
| Superusuario de Django | Todas | Según arquitectura (sin confirmar en inactivas) | Activas | Todas |

Reportes: multiselect con las sucursales del usuario; por defecto, las activas marcadas.

- **Esto es solo UX, no la barrera de seguridad.** Requiere que `delivery-architect` defina cómo se verifica del lado servidor, para cada operación de escritura de Inventario y de Órdenes (alta, edición, cambio de estado, cobro, anulación), que la sucursal esté asignada y **activa**, y cómo se expone al frontend el estado de la sucursal (bandera por fila o en el catálogo de sucursales) y la lista de sucursales en alcance de lectura y de escritura. Los botones ocultos no impiden llamar al API directamente.
- Pendiente de arquitectura también: contrato del filtro multiselect de reportes (varios ids en un parámetro) y el trato del superusuario en sucursales inactivas.

## Consecuencias

- Todas las pantallas del panel comparten un mismo lenguaje para "sucursal inactiva" (badge + aviso + botones ocultos), a costa de añadir una condición por fila a las banderas `can*` de varios componentes (Inventario, Proformas, Notas de trabajo, Notas de venta).
- El filtro de reportes introduce un componente nuevo (menú de casillas) que quedará distinto de los selectores simples de los listados de Órdenes; si luego se quiere uniformidad, los listados podrían adoptar el mismo componente.
- Queda como deuda aceptada: no hay librería de multiselect; si se necesitan más filtros múltiples (láminas, estados) convendrá reabrir la decisión sobre `ng-select`.
- Pantallas que quedarían inconsistentes si no se actualizan después: Láminas y Precios por sucursal (este último ya acotado por sucursal pero sin marca de inactiva), y el módulo Usuarios (fuera de alcance).
- Los botones reflejan datos del último login/carga; el servidor es la autoridad.
