# PLAN-2026-09-30-appheader-nav-cleanup (v1)

**Task:** TASK-appheader-nav-cleanup
**DDRs relacionados:** Ninguno
**ADRs relacionados:** Ninguno

## Objective
Dejar el header de `panel_admin/` solo con lo que el negocio usa, quitando nombre de usuario del nav izquierdo, buscador, selector de idioma (bandera), dropdown de mensajes (sobre) y dropdown de alertas (campana). Los dos dropdowns son datos de demostración de la plantilla y el buscador no tiene acción.

## Context
Ver `docs/tasks/TASK-appheader-nav-cleanup.md` (veredicto `NEEDS_PLAN`, diseño NO). Solo frontend `panel_admin/`; sin backend, sin API, sin migraciones.

## Current behavior
`panel_admin/src/app/layout/header/header.component.html`:
- Nav izquierdo (`:2-24`): toggle sidebar, nombre (`:9-11`), buscador (`:12-22`).
- Nav derecho (`:25-179`): fullscreen (`:26-30`), idioma (`:31-49`), mensajes (`:50-117`), alertas (`:118-166`), menú de usuario con Logout (`:167-178`).
`header.component.ts` mantiene estado/lógica de idioma (`:39-42,57-61,67-76,127-132`). `header.component.sass:1-4` solo estiliza `.current-user-name`. El spec (`header.component.spec.ts:76`) verifica que el nombre se renderiza en el nav izquierdo.

## Expected behavior
Header con: toggle del sidebar (izquierda); fullscreen y menú de usuario (icono de usuario, nombre como título del dropdown y Logout) a la derecha. Sin nombre en el nav izquierdo, sin buscador, sin bandera, sin sobre, sin campana. El idioma lo sigue resolviendo `LanguageService` (navegador / `localStorage`) sin selector en UI.

## Architecture considerations
- Contrato API, datos, dinero, rendimiento, permisos: no aplican (cambio solo de plantilla Angular).
- Acoplamiento: el SCSS global (`.search-element`, `.lang-toggle`, `.dropdown-list-*`, etc., en `assets/scss/{override,rtl,skins}`) es de la plantilla comercial y se comparte entre skins/RTL; se deja intacto para no arriesgar regresiones visuales. Es estilo muerto inofensivo.
- Los assets `assets/images/flags/*` y `users/user-*.png` se usan también en `advance-table`, `dashboard2` y JSON de datos de ejemplo: no se borran.
- `LanguageService` sigue registrado globalmente (`app.config.ts`), ya que sidebar usa `TranslateModule`; solo se deja de inyectar en el header.
- Decisión previa revertida parcialmente: `TASK-login-panel-admin-backend` puso el nombre en el nav izquierdo (`TASK-login-panel-admin-backend.md:139`). Se mantiene el nombre visible en el dropdown de usuario, por lo que el requerimiento "mostrar el nombre del usuario autenticado" sigue cumplido.

## Proposed solution
Eliminación directa de los bloques del template y del estado/imports del componente que queden sin uso. Sin reemplazos ni componentes nuevos. Se descarta borrar SCSS global e i18n de plantilla por riesgo/beneficio, salvo la clave `HEADER` que queda huérfana (ver pasos).

## Files/components affected
Backend: ninguno.
Frontend (`panel_admin/src/`):
- `app/layout/header/header.component.html`
- `app/layout/header/header.component.ts`
- `app/layout/header/header.component.sass` (quitar `.current-user-name`; el archivo queda vacío, se conserva porque `styleUrls` lo referencia)
- `app/layout/header/header.component.spec.ts`
- `assets/i18n/{de,en,es}.json` (bloque `HEADER.SEARCH`, huérfano tras el cambio)
- `docs/tasks/TASK-appheader-nav-cleanup.md` (estado)

## Implementation steps
1. `header.component.html`: quitar `<li>` del nombre y `<li>` con el `<form>` del buscador del nav izquierdo; dejar solo el toggle del sidebar.
2. `header.component.html`: quitar los tres `<li>` de idioma, mensajes y alertas del nav derecho; conservar fullscreen y menú de usuario.
3. `header.component.ts`: eliminar `flagvalue`, `countryName`, `langStoreValue`, `defaultFlag`, `listLang`, la lógica de idioma en `ngOnInit` y `setLanguage()`; quitar inyección de `languageService`; quitar imports y entradas de `imports: []` que queden sin uso (`NgClass`, `NgScrollbar`, `TranslateModule`, `LanguageService`; revisar `FormsModule`). Mantener `currentUserName`, `storageService` (lo usa `ngAfterViewInit`), `logout`, `callFullscreen`, `mobileMenuSidebarOpen`.
4. `header.component.sass`: eliminar la regla `.current-user-name`.
5. `header.component.spec.ts`: reemplazar el test "renders the username on the left side" por tests negativos (ver Test strategy); conservar los demás.
6. `assets/i18n/{de,en,es}.json`: quitar el bloque `HEADER` solo si un grep confirma que no hay otros usos de `HEADER.` (verificado que solo lo usaba el header).
7. Verificar: `ng lint`, `ng build`, `ng test` (spec del header verde; comparar contra la línea base de 15 fallas preexistentes) y verificación manual en navegador (desktop, móvil, tema oscuro).

## Test strategy
- Unitario (`TestBed`, ya existente en el spec del header), casos:
  - El header no renderiza `.current-user-name`, `input[type=search]`, `.lang-toggle`, `i-feather[name=mail]` ni `i-feather[name=bell]`.
  - Tras iniciar sesión, el nombre aparece solo como título del dropdown de usuario (`.dropdown-title`) y contiene el `firstName`.
  - Siguen presentes: toggle del sidebar, fullscreen y opción Logout.
  - Se conservan los tests de `currentUserName` (firstName y fallback a username) y "no Profile/Settings".
- E2E: **no corresponde**. No cambia un flujo crítico, navegación ni formularios; es quitar elementos de un componente y se cubre con el test de componente más verificación manual. Además no hay Playwright instalado en este frontend.
- Integración: no aplica (sin llamadas HTTP nuevas).

## Acceptance criteria
- El header no muestra nombre de usuario en el nav izquierdo, buscador, bandera/idioma, sobre ni campana.
- El menú de usuario sigue mostrando el nombre y permite cerrar sesión; fullscreen y toggle del sidebar funcionan.
- Sin propiedades/imports muertos en `header.component.ts`; `ng lint` y `ng build` limpios.
- Spec del header verde; sin nuevas fallas respecto a la línea base.
- Sin regresión visual en desktop, móvil y tema oscuro (la barra no queda desalineada al quitar elementos).

## Risks
- Quitar el selector elimina la única vía de cambiar idioma en UI. Mitigación: ninguna adicional; el idioma queda fijado por `LanguageService` (navegador o `localStorage`). Se asume aceptable.
- El layout del navbar (`me-auto`, `navbar-right`) podría verse desbalanceado con menos elementos; se cubre con la verificación manual.
- Borrar la clave i18n `HEADER` podría romper si hay un uso no detectado por grep; mitigación: grep previo al borrado, o dejar las claves si hay duda.

## Out of scope
- Limpieza de SCSS global de plantilla (`.search-element`, `.lang-toggle`, `.dropdown-list-*`), assets de banderas y `RightSidebarService`/`toggleRightSidebar`.
- Cambios en `proforma/` o backend.
- Preguntas abiertas (se planifica con estos defaults, avisar si difieren): (1) se mantiene el nombre como título del dropdown de usuario; (2) fullscreen se conserva.

## Changelog
- **v1** (2026-09-30): plan inicial.
