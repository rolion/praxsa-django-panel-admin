# REV-2026-10-02-almacen-permisos-sucursal-filtros-01: Error al cargar sucursales en el listado se muestra como "No tienes sucursales asignadas"

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-02-almacen-permisos-sucursal-filtros.md (v1)
**Suggested owner:** delivery-engineer

## Description
En `InventarioListComponent.ngOnInit`, si `listSucursalesAlcance()` falla, el handler `error` marca `sucursalesLoaded = true` con `sucursales = []`. El getter `withoutSucursales` pasa a `true`, por lo que la plantilla muestra el aviso informativo "No tienes sucursales asignadas", deshabilita el select de sucursal y oculta "Crear" (`canCreate`), aunque el problema real sea un fallo de red/servidor.

## Expected behavior
El plan define el aviso solo para "sin sucursales" (cero sucursales en alcance). Un error de carga debería mostrar el mensaje de error de carga, no afirmar que el usuario no tiene sucursales.

## Actual behavior
Un 5xx/timeout en `GET almacen/sucursales` produce un aviso engañoso y oculta el botón Crear. El listado igual se carga (`load()` se invoca), con el alcance aplicado en el servidor, así que no hay filtración de datos.

## Evidence
`panel_admin/src/app/almacen/inventario/inventario-list.component.ts` (ngOnInit, rama `error`; getter `withoutSucursales`). Revisión de código; los specs de almacén (48 OK) no cubren la rama de error de `listSucursalesAlcance`. No bloquea el PR.
