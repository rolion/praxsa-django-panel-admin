# REV-2026-10-01-vehiculo-detalle-partes-ui-01: La imagen del modelo desborda la card en pantallas angostas

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-01-vehiculo-detalle-partes-ui.md (v1)
**Suggested owner:** delivery-engineer

## Description
La imagen del modelo conserva el estilo en línea `max-width: 320px` (`model-view.component.html`, bloque de cabecera) sin `max-width: 100%`. En un viewport de 375px el contenido de la card mide menos de 320px y la imagen sobresale unos píxeles del borde derecho de la card.

## Expected behavior
Plan/DDR: "Se ve correcto en ancho móvil" (acceptance criteria). La imagen debería ajustarse al ancho disponible.

## Actual behavior
Verificado en el navegador a 375x812: la imagen (320px de ancho) sobresale del contenido de la card. No hay scroll horizontal de página (`scrollWidth` 375 = `innerWidth` 375). El estilo fijo ya existía antes del cambio (mismo `max-width: 320px`), pero el contenedor fue reescrito en este PR.

## Evidence
Captura a 375px con la API simulada (stub local): borde derecho de la imagen más allá de la card; `document.documentElement.scrollWidth` = 375, `window.innerWidth` = 375.
