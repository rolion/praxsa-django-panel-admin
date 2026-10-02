# PLAN-2026-10-02-theme-switcher-relocation (v1)

**Task:** TASK-theme-switcher-relocation
**DDRs relacionados:** Ninguno
**ADRs relacionados:** Ninguno

## Objective
Retirar el "Setting Panel" (`RightSidebarComponent`) del panel de staff y reemplazarlo por un botón en el menú superior, a la izquierda del dropdown de usuario, que alterna entre modo light y dark. Luna en light (clic → dark), sol en dark (clic → light).

## Context
Ver `docs/tasks/TASK-theme-switcher-relocation.md`. Decisiones del usuario: el botón hace el cambio de modo global completo (lo de "Select Layout"), solo en el header de staff (no en `minimal()`), y se pierde la selección de los 7 colores de tema. Rutas y líneas de la investigación verificadas de nuevo contra el código actual; siguen vigentes.

## Current behavior
- Cambio de modo/color solo desde el engranaje del `RightSidebarComponent` (`layout/right-sidebar/right-sidebar.component.html:2-4`), montado en `main-layout.component.html:3`.
- `lightThemeBtnClick`/`darkThemeBtnClick` (`right-sidebar.component.ts:126-179`) ponen en `body` `light|dark`, `light-sidebar|dark-sidebar`, `theme-white|theme-black` y escriben en `localStorage` las claves **crudas** `theme`, `menuOption`, `choose_skin`.
- **Hallazgo nuevo (verificado leyendo código, no en runtime):** el arranque lee esas claves con `LocalStorageService` (`storage.service.ts:20-47`), que antepone el prefijo `light_`/`dark_` (según `config.layout.variant`, hoy `light`). Es decir, busca `light_theme`, `light_menuOption`, `light_choose_skin`, que nadie escribe (el único `setItem` con prefijo es el propio servicio; el panel escribe crudo). Consecuencia: al recargar, header (`header.component.ts:66-88`), `right-sidebar.component.ts:51-93` y `auth-layout.component.ts:41-49` no encuentran el estado guardado y vuelven al default light. La persistencia del tema hoy no funciona tras recargar.
- El header también aplica al `body` la variante `light` y `light-sidebar` por defecto en `ngAfterViewInit` (mismas líneas), tanto en staff como en `minimal()`.
- `header.component.ts:34,48,141-149` tiene `RightSidebarService`/`toggleRightSidebar()` sin uso en el HTML (código muerto). `RightSidebarService` solo lo usan header y right-sidebar.

## Expected behavior
- El engranaje y el panel lateral desaparecen del layout de staff.
- En el nav derecho del header de staff, entre fullscreen y el dropdown de usuario, hay un botón: en light muestra luna (`fas fa-moon`); al clic pasa a dark (body `dark`, `dark-sidebar`, `theme-black`) y muestra sol (`fas fa-sun`); al clic vuelve a light (`light`, `light-sidebar`, `theme-white`) y muestra luna.
- La elección se guarda y se recupera al recargar (corrige el problema de prefijo anterior para el panel de staff).
- El header de `minimal()` (cliente) no muestra el botón y la app de cliente sigue siempre en light.

## Architecture considerations
- **Contrato API / datos / dinero / permisos:** no aplica; solo frontend, sin backend ni migraciones.
- **Acoplamiento:** hoy la lógica de tema está repartida en header, right-sidebar y auth-layout. Se centraliza solo lo necesario en un `ThemeService` (`providedIn: 'root'`) en `core/service/`, sin refactorizar `auth-layout`.
- **Claves de localStorage:** el servicio lee/escribe las mismas claves crudas que usaba el panel (`theme`, `menuOption`, `choose_skin`) para no invalidar lo ya guardado; no usa `LocalStorageService` (por el prefijo). `choose_skin_active` deja de usarse.
- **Colores legados:** el skin pasa a derivarse del modo (`dark → theme-black`, `light → theme-white`). Quien tuviera guardado otro color (cyan, purple, ...) volvería a blanco/negro; es consecuencia directa de quitar el selector (decisión del usuario). Se limpian de `body` las siete clases `theme-*` al aplicar el modo para evitar clases residuales.
- **Aislamiento de cliente:** el header `minimal()` aplica el modo light sin persistir, para que un dark de staff no se filtre al layout de cliente durante la navegación SPA (hoy no hay nada que quite `dark` del `body`).
- **CSS legado:** las reglas SCSS del panel (`_settingSidebar.scss`, `.settingSidebar` en skins y rtl) y `assets/images/light.png|dark.png` quedan; son estilos inertes compartidos con la plantilla y quitarlos no aporta valor ni es pedido.

## Proposed solution
1. **`ThemeService`** (`panel_admin/src/app/core/service/theme.service.ts`, exportado en `core/index.ts`):
   - `isDark` (signal), inicializado desde `localStorage['theme']` o `config.layout.variant`.
   - `applyMode(mode, persist)`: con un `Renderer2` creado vía `RendererFactory2`, quita `light`/`dark`, `light-sidebar`/`dark-sidebar` y los siete `theme-*` del `body`; agrega `mode`, `mode-sidebar` y `theme-white|black`; actualiza `isDark`; si `persist`, escribe `theme`, `menuOption`, `choose_skin`.
   - `applySaved()`: aplica el modo guardado (o el default) sin escribir.
   - `toggle()`: `applyMode(isDark() ? 'light' : 'dark', true)`.
2. **Header** (`header.component.{ts,html}`):
   - HTML: `<li>` con `<a class="nav-link nav-link-lg collapse-btn" role="button" (click)="toggleTheme()" [attr.aria-label]=... [title]=...>` y `<i class="fas" [class.fa-moon]="!isDark()" [class.fa-sun]="isDark()">`, dentro de `@if (!minimal())`, entre fullscreen y el dropdown de usuario. Los iconos son los mismos FontAwesome de los botones de "Sidebar Color".
   - TS: inyectar `ThemeService`; en `ngAfterViewInit`, si `!minimal()` llamar `applySaved()` en lugar de los bloques de `theme`/`menuOption` actuales (los de `sidebar_status` se mantienen); si `minimal()`, `applyMode('light', false)`. Eliminar `RightSidebarService` de `providers`, `isOpenSidebar` y `toggleRightSidebar()` (código muerto del panel).
3. **Retirar el panel:** borrar `layout/right-sidebar/` (4 archivos), quitar import/uso en `main-layout.component.{ts,html}`, borrar `core/service/rightsidebar.service.ts` y su export en `core/index.ts`.
4. **Docs:** actualizar `docs/frontend/panel_admin/reference.md:44` (ya no existe `right-sidebar/`; mencionar `ThemeService` y el botón en el header).

## Files/components affected
Frontend (`panel_admin/src/app`):
- Nuevo: `core/service/theme.service.ts`, `core/service/theme.service.spec.ts`
- Modificados: `core/index.ts`, `layout/header/header.component.{ts,html,spec.ts}`, `layout/app-layout/main-layout/main-layout.component.{ts,html}`
- Eliminados: `layout/right-sidebar/*` (ts, html, sass, spec), `core/service/rightsidebar.service.ts`
- Docs: `docs/frontend/panel_admin/reference.md`
Backend: ninguno.

## Implementation steps
1. Crear `ThemeService` y su spec; exportarlo en `core/index.ts`.
2. Integrar el botón y la inicialización en el header (HTML + TS), quitando lo muerto del panel.
3. Quitar `app-right-sidebar` del `main-layout` y borrar el componente y `RightSidebarService`.
4. Actualizar specs (`header.component.spec.ts`) y `reference.md`.
5. Compilar (`ng build`) y ejecutar los tests de `panel_admin`; verificar en el navegador el flujo completo.

## Test strategy
- **Unitario `ThemeService`** (nuevo): `applyMode('dark', true)` deja en `body` `dark`, `dark-sidebar`, `theme-black` y sin `light*`/`theme-white`, y escribe `theme=dark`, `menuOption=dark-sidebar`, `choose_skin=theme-black`; `applyMode('light', true)` es simétrico; `toggle()` alterna `isDark`; `applyMode(..., false)` no escribe en localStorage; `applySaved()` respeta `theme=dark` guardado y cae a `config.layout.variant` sin valor guardado; limpia clases `theme-*` residuales (ej. `theme-purple`).
- **Componente `HeaderComponent`** (actualizar spec existente con `TestBed`): en staff hay botón de tema entre fullscreen y user, con `fa-moon` por defecto; tras clic muestra `fa-sun` y el `body` tiene `dark`; segundo clic vuelve a `fa-moon`; `minimal()` no renderiza el botón y deja el `body` en `light`; el test "keeps the sidebar toggle, fullscreen and user menu" (`header.component.spec.ts:86-91`) sigue pasando.
- **MainLayout:** verificar que ya no se renderiza `app-right-sidebar` (el spec de `minimal-layout` ya cubre el caso contrario).
- **Verificación manual en navegador** (según la memoria del proyecto, flujo con efecto visual): alternar varias veces, recargar y confirmar persistencia, navegar a `/calculadora` tras dejar dark y confirmar que sigue light.
- **E2E: no corresponde.** Es un cambio de UI local sin flujo multi-paso, sin integración frontend/backend y sin navegación nueva; los tests de componente más la verificación manual cubren el riesgo. No requiere instalar Playwright.

## Acceptance criteria
- No existe el engranaje ni el panel lateral en el layout de staff, y `RightSidebarComponent`/`RightSidebarService` no están en el código.
- Hay un botón en el header de staff, a la izquierda del dropdown de usuario, con luna en light y sol en dark; el clic alterna modo, sidebar y skin como lo hacía "Select Layout".
- Tras recargar, el modo elegido se mantiene.
- El header de cliente (`minimal()`) no muestra el botón y permanece en light.
- `ng build` y los tests de `panel_admin` pasan sin errores.

## Risks
- Pantallas que dependan de `dark`/`dark-sidebar`/`theme-*` (skins SCSS, logo del sidebar): se mantienen las mismas clases que ponía el panel; se revisan en la verificación manual.
- Usuarios con color de tema legado guardado vuelven a blanco/negro: aceptado por el usuario.
- La persistencia en `auth-layout` (login) sigue leyendo con prefijo y no recupera el tema; el login queda siempre en light. No empeora respecto de hoy.
- Cobertura previa escasa en el área; se mitiga con los tests nuevos.

## Out of scope
- Dar selección de color de tema en otro lugar o fijar un color por defecto distinto de blanco/negro.
- Botón de tema en el layout de cliente (`minimal()`).
- Hacer que `auth-layout` recupere el tema guardado, o corregir el prefijo de `LocalStorageService` en general.
- Eliminar el SCSS inerte del panel y las imágenes `light.png`/`dark.png`.
- Preguntas abiertas: ninguna pendiente.

## Dependencias nuevas
Ninguna.
