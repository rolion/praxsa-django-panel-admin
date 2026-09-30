# PLAN-2026-09-30-credencial-detalle-layout (v1)

**Task:** TASK-credencial-detalle-layout
**DDRs relacionados:** [DDR-credencial-detalle-layout-vista-detalle-chips](../design/DDR-credencial-detalle-layout-vista-detalle-chips.md)
**ADRs relacionados:** Ninguno

## Objective
Rediseñar la vista `Ver credencial` de `panel_admin/` con una card de dos columnas: identidad y estado a la izquierda, grupos y sucursales como chips (con límite de 3 y contador `+N más`) a la derecha.

## Context
Ver `## Investigación` de TASK-credencial-detalle-layout. Cambio solo de frontend, sin API ni modelo. El pedido original venía en Tailwind; el DDR decidió implementarlo con Bootstrap 5.3, que es lo que usa `panel_admin/`.

## Current behavior
`panel_admin/src/app/users/view/user-view.component.html:1-56`: una card `col-lg-8` con un `<dl>` de una columna. El estado es texto plano (línea 26); grupos y sucursales se muestran con `join(', ')` (líneas 28-43); botón "Editar" a `/users/edit/:id` (línea 51). `user-view.component.ts:1-46` resuelve IDs a nombres con `forkJoin` y expone `groupNames` y `sucursalNames`. No hay spec del componente. Verificado que los archivos siguen en esas rutas.

## Expected behavior
- Card `col-12` con `shadow-sm` y bordes redondeados; dos `col-md-6` (una columna bajo `md`).
- Izquierda: título con nombre completo (fallback a `username`), badge Activo/Inactivo (`badge bg-success` / `bg-secondary`), Usuario, Correo, Teléfono (`—` si no hay).
- Derecha: bloques Grupos (chips `bg-primary-subtle text-primary-emphasis`) y Sucursales (chips `bg-info-subtle text-info-emphasis` con icono `fa-store`). Vacío: "Sin grupos" / "Sin sucursales".
- Más de 3 elementos: 3 chips más un botón `+N más` que expande; luego "Ver menos". Con 3 o menos no hay contador.
- Botón primario "Editar" abajo a la izquierda, separado por `border-top`.

## Architecture considerations
- **Contrato API:** sin cambios; se sigue usando `getUser`, `listGroups`, `listSucursales`.
- **Datos/migraciones:** ninguno.
- **Permisos:** el botón "Editar" sigue visible siempre; la barrera real es el backend, sin cambios.
- **Acoplamiento:** solo cambia `users/view/`; `user-edit`/`user-create` no se tocan.
- **Consistencia visual:** se traducen los patrones del DDR; no se agrega Tailwind ni SCSS nuevo salvo que la verificación con tema oscuro lo exija.

## Proposed solution
Mover la lógica de presentación al componente: `fullName`, `visibleGroups`/`hiddenGroupCount`, `visibleSucursales`/`hiddenSucursalCount` y dos flags `showAllGroups` / `showAllSucursales` con métodos de toggle, constante `MAX_CHIPS = 3`. La plantilla solo pinta. Se usan las utilidades de Bootstrap ya instaladas.

## Files/components affected
- Backend: ninguno.
- Frontend:
  - `panel_admin/src/app/users/view/user-view.component.html` (reescribir la plantilla)
  - `panel_admin/src/app/users/view/user-view.component.ts` (getters y flags de expansión)
  - `panel_admin/src/app/users/view/user-view.component.spec.ts` (nuevo)

## Implementation steps
1. En `user-view.component.ts`: agregar `MAX_CHIPS = 3`, getter `fullName`, flags `showAllGroups`/`showAllSucursales`, getters de chips visibles y de restantes para cada bloque, y `toggleGroups()` / `toggleSucursales()`.
2. Reescribir `user-view.component.html`: card `col-12` de dos columnas responsivas, título, badge de estado, `dl` de datos, bloques de chips con contador y estados vacíos, botón "Editar" abajo. Conservar breadcrumb, `Cargando...` y `alert-danger`.
3. Crear `user-view.component.spec.ts` (ver estrategia de testing).
4. Correr `npm test` (sin fallas nuevas respecto de las 15 preexistentes), `npm run lint` y `npm run build` en `panel_admin/`.
5. Verificación manual en el navegador: usuario con 0, 2, 3 y 5+ grupos/sucursales; usuario inactivo; ancho móvil; tema claro y oscuro.

## Test strategy
- **Unitario (`TestBed` + `HttpTestingController`, mismo patrón que `users-list.component.spec.ts`):**
  - `fullName` usa nombre y apellido, y cae a `username` si ambos están vacíos.
  - Con 2 grupos, se muestran los 2 chips y no hay contador.
  - Con exactamente 3, se muestran 3 y no hay contador.
  - Con 5, se muestran 3 más `+2 más`; al activar el toggle se ven 5 y aparece "Ver menos".
  - Sin grupos / sin sucursales, se muestra "Sin grupos" / "Sin sucursales".
  - Badge "Activo" (`bg-success`) o "Inactivo" (`bg-secondary`) según `is_active`.
  - Teléfono `null` muestra `—`.
- **E2E: no corresponde.** Es una pantalla de solo lectura, sin flujo multi-paso ni cambio de navegación, y el contrato con el backend no cambia; los tests con `HttpTestingController` cubren la integración. Además Playwright no está instalado.
- **Manual:** paso 5 de implementación (responsive y tema oscuro no se pueden cubrir con tests unitarios).

## Acceptance criteria
- La vista muestra card de dos columnas en `md`+ y una columna en móvil.
- El nombre completo es el título; el estado es un badge verde/gris.
- Grupos y sucursales se muestran como chips de estilo distinto; vacíos muestran el texto neutro.
- Con más de 3 elementos aparece `+N más`, que expande y contrae.
- "Editar" navega a `/users/edit/:id`.
- El spec nuevo pasa; `ng lint` y `ng build` limpios; sin fallas nuevas en `npm test`.
- No se agregan dependencias.

## Risks
- Los chips `*-subtle` podrían renderizar con bajo contraste en el tema oscuro o con colores de acento de la plantilla (no verificado). Mitigación: verificación manual; si falla, ajustar con SCSS mínimo.
- `_badge.scss` da a `.badge` un `padding` y `border-radius` propios; el botón `+N más` podría verse distinto del resto. Mitigación: revisar en el navegador.

## Out of scope
- Cambios en `user-edit`, `user-create` o el listado.
- Ocultar "Editar" por permiso.
- Tailwind.
- Popover para listas muy largas.
- Preguntas abiertas: ninguna que bloquee; se asumió que "Usuario" es `username` y "Correo" es `email`.

## Dependencias nuevas
Ninguna.
