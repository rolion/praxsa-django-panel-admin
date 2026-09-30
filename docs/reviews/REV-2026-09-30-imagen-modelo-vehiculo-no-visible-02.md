# REV-2026-09-30-imagen-modelo-vehiculo-no-visible-02: `imageFailed` de `model-view` no se resetea al recargar el modelo

**Status:** Resolved (plan v2, commit b509b68; verificado por spec de reintento en model-view)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-09-30-imagen-modelo-vehiculo-no-visible.md (v1)
**Suggested owner:** delivery-engineer

## Description
El plan (paso 3) pide "resetear al cargar el modelo". `ModelViewComponent.load()` se vuelve a llamar tras agregar/editar/quitar items (`model-view.component.ts:146,179,196`) pero nunca pone `imageFailed = false`.

## Expected behavior
Al recargar el modelo, una imagen que antes falló se reintenta.

## Actual behavior
Tras un fallo puntual (p. ej. error de red transitorio) el placeholder queda fijo hasta recargar la página. Impacto mínimo (misma URL, sin reintento).

## Evidence
`grep -n imageFailed model-view.component.ts` → solo la declaración (línea 36); `.html` la asigna a `true`. Ninguna asignación a `false`.
