# REV-2026-09-30-agrupacion-menu-instalador-precio-sucursal-01: en "Precios por sucursal" el ícono de búsqueda se superpone al título y la barra se envuelve a 1024px

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-09-30-agrupacion-menu-instalador-precio-sucursal.md (v1)
**Suggested owner:** delivery-engineer

## Description
En la pantalla `/almacen/precios-sucursal` el encabezado de la tabla usa el mismo marcado que Bobinas (`col-lg-6` con título `col-auto` + búsqueda `col-lg-8`). Al ser el título "Precios por sucursal" más largo que "Bobinas", la caja de búsqueda no cabe en la fila y se envuelve debajo, y el ícono de la lupa queda sobre la "P" del título.

## Expected behavior
Encabezado igual de ordenado que en Instaladores y Bobinas (título, búsqueda y botón "+" en una fila, sin superposición).

## Actual behavior
Con viewport de 1024x768 (prueba en vivo con la app real): lupa superpuesta al título, campo de búsqueda y botón "+" en una segunda línea. Funcionalidad intacta (buscar, crear, editar y eliminar funcionan); es solo estético. No bloquea el PR.

## Evidence
Captura en el navegador integrado, usuario `admin`, `http://localhost:4200/#/almacen/precios-sucursal`, 1024x768. Causa probable: `precios-sucursal-list.component.html` líneas 15-30 (columnas del encabezado copiadas de Bobinas sin ajustar al título más largo). Sugerencia: acortar el título (p. ej. "Precios") o ampliar las columnas del encabezado.
