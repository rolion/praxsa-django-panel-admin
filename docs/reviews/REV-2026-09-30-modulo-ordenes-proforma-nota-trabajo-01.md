# REV-2026-09-30-modulo-ordenes-proforma-nota-trabajo-01: `ng build` de producción falla por el presupuesto de estilos de componente

**Status:** Closed (verificado en la corrida 2)
**Severity:** High
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-09-29-modulo-ordenes-proforma-nota-trabajo.md (v2)
**Suggested owner:** delivery-engineer

## Description
La compilación de producción de `panel_admin/` (`npx ng build`, configuración por defecto = `production`) **termina con error**: el estilo de `proforma-form.component.scss` supera el presupuesto `anyComponentStyle` (`maximumError: 4kb`, `angular.json:75-78`). Además, otros dos estilos nuevos superan el aviso de 2 kB. El resto de los componentes existentes del panel no disparan ese aviso, así que los estilos de Órdenes son los únicos fuera de la convención del proyecto.

Las verificaciones del ciclo de implementación se hicieron solo con `ng build --configuration development` (que no aplica presupuestos), por eso no se detectó antes. Un despliegue de producción del panel no se puede generar con este PR.

## Expected behavior
Plan, criterio de aceptación 11: "`ng build` y `ng lint` limpios". `ng build` (producción) debe terminar sin errores.

## Actual behavior
`ng build` falla con 1 error y 3 avisos de presupuesto (los 3 en archivos de este PR).

## Evidence
```
$ cd panel_admin && npx ng build
Application bundle generation failed. [8.611 seconds]
▲ [WARNING] src/app/ordenes/orden-view.shared.scss exceeded maximum budget. Budget 2.00 kB was not met by 302 bytes with a total of 2.30 kB.
▲ [WARNING] src/app/ordenes/proformas/proforma-view.component.scss exceeded maximum budget. Budget 2.00 kB was not met by 1.03 kB with a total of 3.03 kB.
▲ [WARNING] src/app/ordenes/proformas/proforma-form.component.scss exceeded maximum budget. Budget 2.00 kB was not met by 2.42 kB with a total of 4.42 kB.
X [ERROR] src/app/ordenes/proformas/proforma-form.component.scss exceeded maximum budget. Budget 4.00 kB was not met by 418 bytes with a total of 4.42 kB.
```
`angular.json` (configuración `production`):
```
{ "type": "anyComponentStyle", "maximumWarning": "2kb", "maximumError": "4kb" }
```
Contexto de código nuevo relacionado (deuda menor, mismo origen): `proforma-view.component.scss` repite las reglas de tarjeta, grid, badge y acciones que ya están en `orden-view.shared.scss`.

## Notas para quien corrija
- Reducir/reorganizar el estilo (p. ej. mover lo común a un único archivo compartido y usarlo desde el formulario y las dos vistas) o, si el equipo lo decide, subir el presupuesto de forma explícita y justificada; no dejar el error abierto.
- Tras el arreglo, volver a correr `npx ng build` (producción), no solo `--configuration development`.

## Verificación (corrida 2 de review, 2026-09-30)
**Resuelto.** Los estilos de Órdenes pasaron a `panel_admin/src/assets/scss/_ordenes.scss` (global, acotado por `.proforma-form` / `.orden-view`) y se eliminaron los tres estilos de componente. Salida real:
```
$ cd panel_admin && npx ng build
Application bundle generation complete. [8.057 seconds]
▲ [WARNING] 23 rules skipped due to selector errors:   (keyframes de la plantilla, ajeno a este PR)
errores: 0   avisos de presupuesto: 0
```
