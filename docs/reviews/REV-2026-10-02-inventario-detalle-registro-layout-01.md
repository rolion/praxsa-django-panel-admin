# REV-2026-10-02-inventario-detalle-registro-layout-01: Título "Detalle de Registro" ilegible en tema oscuro

**Status:** Open
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-02-inventario-detalle-registro-layout.md (v1)
**Suggested owner:** delivery-engineer

## Description
El `h4` "Detalle de Registro" de la cabecera (`inventario-view.component.html`, `data-test="title"`) no hereda un color de tema: en tema oscuro se renderiza en negro sobre el fondo oscuro del contenedor y casi no se lee. El subtítulo (nombre de la lámina), las tarjetas y el resto de textos sí se adaptan.

## Expected behavior
Criterio de aceptación del plan: "Se ve correctamente en tema claro y oscuro y en ancho móvil (verificación manual)". El título debe ser legible en ambos temas.

## Actual behavior
Con `body.dark`, `getComputedStyle(h4).color` es `rgb(0, 0, 0)` (igual que `body`, `rgb(0, 0, 0)`), sobre un contenedor `rgba(128,128,128,0.08)` encima del fondo oscuro de la plantilla. Tema claro y todo lo demás (tarjetas, mosaicos, badge, botón, precios) se ven bien en escritorio y móvil.

## Evidence
Verificación en el stack local (`localhost:8086`, rama integrada con master), registro `/panel/almacen/inventario/view/1`:

```
bodyClass: "sidebar-gone dark dark-sidebar theme-black"
title color: rgb(0, 0, 0)        bodyColor: rgb(0, 0, 0)
product-name color: rgb(100, 120, 154)   containerBg: rgba(128, 128, 128, 0.08)
```

Captura en tema oscuro (escritorio y 375x812): "Detalle de Registro" casi invisible; el resto legible. Nota: el breadcrumb `page-title` sí es legible porque la plantilla le asigna color; el `h4` propio no.
