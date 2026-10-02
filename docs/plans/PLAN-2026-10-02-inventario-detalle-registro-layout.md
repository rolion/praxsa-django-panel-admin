# PLAN-2026-10-02-inventario-detalle-registro-layout (v1)

**Task:** TASK-inventario-detalle-registro-layout
**DDRs relacionados:** [DDR-inventario-detalle-registro-layout-vista-detalle-registro](../design/DDR-inventario-detalle-registro-layout-vista-detalle-registro.md)
**ADRs relacionados:** Ninguno (el task no requirió arquitectura; contexto en `docs/adr/ADR-modulo-almacen-modelo-datos-imagen-soft-delete.md`, que limita la edición a 5 campos y no cambia)

## Objective
Rediseñar la vista `Ver inventario` de `panel_admin/` a dos columnas con tarjetas (Información General, Métricas de Stock, Valores Financieros), cabecera con título, nombre del producto y único botón "Editar", según el DDR. Solo frontend.

## Context
Ver `docs/tasks/TASK-inventario-detalle-registro-layout.md` (investigación y diseño). `AppInventario` ya trae todos los datos; no hay cambios de API, modelo ni permisos.

## Current behavior
- `panel_admin/src/app/almacen/inventario/inventario-view.component.html:1-54`: una `card` en `col-lg-8` con `<dl class="row">` de 14 filas, valores crudos, `date` sin pipe (`:34` región de fecha), estado como texto, botón "Gestionar" al pie (`:46-48`).
- `inventario-view.component.ts:9-13`: componente standalone con `imports: [RouterLink]`; `canManage` = `hasPermission('change_inventario')` (`:20-22`).
- `inventario-view.component.spec.ts:1-73`: 3 pruebas (carga, error, `canManage`); ninguna sobre el HTML renderizado.
- `assets/scss/_ordenes.scss:11,87-111`: `section-card`/`section-header` e `info-*` solo bajo `.orden-view`; importado en `assets/scss/style.scss` (`@use "_ordenes"`).
- Verificado vigente al planificar: los archivos y rutas citados siguen en su lugar; el árbol de trabajo solo tiene los docs nuevos del task.

## Expected behavior
Según DDR: contenedor gris translúcido; cabecera `h4` "Detalle de Registro" + subtítulo `window_film_name` + botón "Editar" (solo con `change_inventario`); columna izquierda `col-lg-8` con Información General (grid de 2 columnas, Fecha justo tras Estado, badge verde "Activo"); columna derecha `col-lg-4` con Métricas de Stock (mosaicos 2×2, "Disponible" destacado) y Valores Financieros (`Bs`). Una columna bajo `lg`.

## Architecture considerations
- **Contrato API:** sin cambios; no hay coordinación de despliegue backend/frontend.
- **Datos/migraciones:** ninguna.
- **Dinero:** solo presentación. Los valores vienen como strings decimales del API; se formatean con `Number()` únicamente para mostrar (sin cálculos, sin escribir de vuelta), por lo que no hay riesgo de precisión.
- **Permisos:** "Editar" sigue condicionado por `canManage`; es UX, el backend ya valida (`InventarioUpdateSerializer`). El frontend no es la barrera.
- **Acoplamiento:** el SCSS nuevo es un parcial con raíz `.inventario-view`, sin tocar `_ordenes.scss`; reutilizar `.orden-view` significa que un cambio futuro a `.info-*`/`section-*` afecta también esta vista (precedente: reportes). `formatBs` vive en `calculadora/calculadora.helpers.ts:43`, cuyo módulo importa tipos de `vehicles` y `ordenes`; importarlo desde `almacen` crea una dependencia entre módulos, aceptada para no duplicar el formato (decisión del DDR). Si resulta incómodo en review, alternativa: helper local equivalente.
- **Consistencia visual:** patrones decididos en el DDR; este plan solo los traduce a pasos.
- **Formato numérico (pendiente que dejó el DDR):** se decide aquí usar `Intl.NumberFormat('es-BO', {minimumFractionDigits: 0, maximumFractionDigits: 2})` mediante un método `formatMeters(value)` del componente, para quedar coherente con `formatBs` (es-BO). Cantidad (entero) se muestra sin formato adicional. No se usa `DecimalPipe` porque el locale de la app (`LOCALE_ID`) no está configurado y saldría en `en-US`.
- **Fecha:** `DatePipe` con `'dd/MM/yyyy - HH:mm'`. La zona horaria del API (naive vs. `Z`) no está confirmada; se verifica con datos reales en review, no se resuelve en este plan.

## Proposed solution
Reescribir la plantilla de `inventario-view` con la estructura del DDR, agregar `DatePipe` a los `imports`, exponer `formatBs` y `formatMeters` en el componente, y añadir un parcial SCSS `_inventario.scss` con el contenedor gris y los mosaicos. Se mantiene el breadcrumb existente. Se mantienen `Cargando...`/`alert-danger`.

## Files/components affected
**Backend:** ninguno.

**Frontend (`panel_admin/src/`):**
- `app/almacen/inventario/inventario-view.component.html` — reescritura.
- `app/almacen/inventario/inventario-view.component.ts` — imports (`DatePipe`), `formatBs`, `formatMeters`.
- `app/almacen/inventario/inventario-view.component.spec.ts` — nuevas pruebas de render.
- `assets/scss/_inventario.scss` — nuevo; `assets/scss/style.scss` — `@use "_inventario";` junto a `_ordenes`.

## Implementation steps
1. Crear `_inventario.scss` con raíz `.inventario-view`: `.inventario-container` (fondo `rgba(128,128,128,0.08)`, `border-radius: 12px`, `padding: 1.25rem`), `.stat-tile` (fondo translúcido, `border-radius: 10px`, `padding: .75rem`), `.stat-value` (`1.5rem`, `font-weight: 700`), `.stat-tile.featured .stat-value` (color `#4f6bed`), `.stat-unit` (pequeño, tenue). Importarlo en `style.scss` tras `_ordenes`. Verificable: `ng build` compila el SCSS.
2. Actualizar el componente: `imports: [RouterLink, DatePipe]`, `readonly formatBs = formatBs` (import desde `../../calculadora/calculadora.helpers`) y `formatMeters(value: string | number): string` con `Intl.NumberFormat('es-BO', …)`. Verificable: build y lint.
3. Reescribir la plantilla: raíz `main-content orden-view inventario-view`, breadcrumb sin cambios, `section-body` con `.inventario-container`, cabecera (título, subtítulo, "Editar" bajo `@if (canManage)` con ícono `fa-pen`), `row g-4` con `col-lg-8`/`col-lg-4`, tarjetas según DDR; Fecha inmediatamente después de Estado; lote nulo → `—` con `empty-value`; `data-test` en título, subtítulo, estado, fecha, lote, métricas y precios para los specs. Verificable en `ng serve`.
4. Escribir/actualizar los specs (ver Test strategy) y ejecutarlos.
5. Verificación manual en navegador con un registro real: escritorio, ancho móvil, tema claro/oscuro, usuario con y sin `change_inventario`, registro inactivo y con lote vacío; revisar la fecha mostrada frente al valor del API.
6. `ng lint` y `ng build` limpios.

## Test strategy
- **Unitario/componente (`TestBed`, patrón ya usado en el spec existente):**
  - Se renderiza "Detalle de Registro" y `window_film_name` como subtítulo tras cargar.
  - Información General muestra Sucursal, Lámina, Ancho, Nro. de Lote, Nro. de Referencia, Estado y Fecha, y la Fecha aparece después del Estado en el DOM.
  - Estado Activo → badge `bg-success` "Activo"; `is_active: false` → `bg-secondary` "Inactivo".
  - `nro_lote: null` → muestra `—`.
  - Fecha con formato `dd/MM/yyyy - HH:mm h` (usar un valor sin `Z` para que el test no dependa de la zona horaria de la máquina).
  - Métricas: Disponible, Cantidad, Instalado y Longitud Inicial con su valor; Valores Financieros con prefijo `Bs`.
  - Botón "Editar": presente con `change_inventario` (con `href` a `/almacen/inventario/edit/7`), ausente sin él; no existe botón "Gestionar", imprimir ni historial.
  - `formatMeters` con `'50.00'` → `50`, `'1234.5'` → agrupación/decimales es-BO (afirmar contra `Intl` en el mismo test para no depender de la versión de ICU).
  - Se mantienen las 3 pruebas existentes (carga, error, `canManage`).
- **E2E (Playwright): NO corresponde.** Es una vista de solo lectura, sin cambio de navegación, formularios ni integración nueva con el backend; los specs de componente con `HttpTestingController` cubren el contrato. Playwright no está instalado y no se agrega.
- **Backend:** sin cambios, sin tests nuevos.
- **Manual:** paso 5 (visual, responsive, tema oscuro, fecha), no automatizable con el costo razonable.

## Acceptance criteria
- La vista muestra el layout de dos columnas del DDR en `lg+` y una columna debajo de `lg`.
- Cabecera con "Detalle de Registro", nombre de la lámina y solo el botón "Editar" a la derecha, visible únicamente con `change_inventario`.
- Información General con los 7 datos pedidos en grid de 2 columnas, Fecha inmediatamente tras Estado, badge verde para Activo.
- Métricas de Stock y Valores Financieros con los campos pedidos; "Disponible" visualmente destacado; precios con `Bs`.
- Sin regresión: carga, error y permisos siguen funcionando; no se tocan listado, edición ni creación.
- Specs nuevos y existentes pasan; sin fallas nuevas respecto de la línea base de la suite; `ng lint` y `ng build` limpios.
- Se ve correctamente en tema claro y oscuro y en ancho móvil (verificación manual).

## Risks
- **Zona horaria/formato de `date`:** no confirmado; mitigación: verificar con respuesta real del endpoint en el paso 5; si hay desfase, tratarlo como hallazgo (no se arregla en backend dentro de este task sin avisar).
- **Tema oscuro:** fondos translúcidos deberían funcionar, no verificado; mitigación: paso 5.
- **Dependencia `almacen` → `calculadora`** por `formatBs`; mitigación: helper local si molesta en review.
- **Cambios futuros a `.orden-view`** afectan esta vista; sin mitigación más allá del parcial propio.
- **Rótulo "Editar" vs "Gestionar"** inconsistente con listado y pantalla destino (aceptado en DDR); sin mitigación en este task.
- Suite de `panel_admin` con fallas previas conocidas en otros tasks (15 en la línea base de master según TASK-credencial-detalle-layout): comparar contra línea base, no exigir 0.

## Out of scope
- Cambiar rótulos del listado o de la pantalla de edición ("Gestionar"), y ampliar los campos editables.
- Cambios de API, modelo o permisos; configurar `LOCALE_ID` global.
- Rediseñar otras vistas de Almacén (`lamina-view`, etc.).
- Preguntas abiertas para el usuario: (1) ¿"nombre del producto" = solo el nombre de la lámina (asumido) o lámina + ancho? (2) ¿Basta el prefijo `Bs` para los precios (asumido por el resto del panel)?

## Dependencias nuevas
Ninguna.
