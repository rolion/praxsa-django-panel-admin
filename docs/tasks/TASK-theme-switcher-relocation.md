# TASK-theme-switcher-relocation: Mover el cambio light/dark del Setting Panel a un botón en el header

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** NO
**Rama:** `claude/theme-switcher-relocation-4d2c5c` (asignada por el entorno)
**Pull Request:** [#65](https://github.com/rolion/praxsa-django-panel-admin/pull/65)

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-02 | (nuevo) → INVESTIGATION | Task creado | delivery-investigate |
| 2026-10-02 | INVESTIGATION (sin cambio) | Usuario resolvió dos preguntas abiertas: modo global completo; botón solo en staff | delivery-investigate |
| 2026-10-02 | INVESTIGATION → PLANNING | Veredicto NEEDS_PLAN, diseño NO; sin arquitectura requerida | delivery-plan |
| 2026-10-02 | PLANNING → ENGINEERING | Plan v1 escrito (ThemeService nuevo, botón en header, retiro del panel, specs y doc); PR abierto sobre la rama asignada por el entorno | delivery-plan |

## Investigación

### Requerimiento
"Hay un componente en el panel admin, el panel setting, con el cual se puede cambiar entre modo light y modo dark y también se puede cambiar los colores del tema. Me gustaría quitarlo de donde está, y agregar un botón en el menú superior a la izquierda del dropdown de usuario, usando los botones del panel setting sidebar color. Cuando esté en el light theme se muestra el icono de luna que al hacer click cambia al dark mode y se muestra el icono del sol, que al hacer click se cambia a light mode y se muestra el icono de la luna."

### Hechos encontrados
- El "Setting Panel" es `RightSidebarComponent` (`panel_admin/src/app/layout/right-sidebar/right-sidebar.component.ts:19`, selector `app-right-sidebar`). Se monta solo en el layout principal: `layout/app-layout/main-layout/main-layout.component.html:3` e import en `main-layout.component.ts:4,17`. El layout mínimo no lo monta (`minimal-layout.component.spec.ts:38` verifica `app-right-sidebar` nulo).
- Contenido del panel (`right-sidebar.component.html`): "Select Layout" light/dark con imágenes `assets/images/light.png`/`dark.png` (`:10-29`, handlers `lightThemeBtnClick`/`darkThemeBtnClick`); "Sidebar Color" con dos botones radio: sol `fas fa-sun` "Light Sidebar" (`:33-38`) y luna `fas fa-moon` "Dark Sidebar" (`:39-44`); "Color Theme" con 7 colores (white, cyan, black, purple, orange, green, red) (`:47-76`). Se abre con el engranaje `settingPanelToggle` (`:2-4`).
- Lógica de modo en el panel:
  - `lightThemeBtnClick()` (`right-sidebar.component.ts:126-152`): quita `dark`/`dark-sidebar` y la clase de skin previa del `body`, agrega `light`, `light-sidebar`, `theme-white`; persiste en localStorage `choose_skin=theme-white`, `theme=light`, `menuOption=light-sidebar`.
  - `darkThemeBtnClick()` (`:153-179`): simétrico con `dark`, `dark-sidebar`, `theme-black`; persiste `choose_skin=theme-black`, `theme=dark`, `menuOption=dark-sidebar`.
  - `lightSidebarBtnClick()`/`darkSidebarBtnClick()` (`:114-125`) solo cambian `light-sidebar`/`dark-sidebar` y `menuOption`, **no** el modo del tema (`dark`/`light`). Es decir, los "botones de Sidebar Color" (sol/luna) controlan solo el color del sidebar, no el modo global.
  - `selectTheme(e)` (`:104-113`) cambia el color de skin (`theme-*`, `choose_skin`, `choose_skin_active`).
- **Lógica de arranque dentro del panel que hoy aplica el estado guardado:** `ngAfterViewInit` (`right-sidebar.component.ts:51-94`) agrega al `body` la clase `choose_skin` guardada (o `theme-<config.layout.theme_color>`), e inicializa `isDarkSidebar`/`isDarTheme` leyendo `menuOption`/`theme`. Si el componente se elimina, esta aplicación del skin al arrancar desaparece.
- El header ya aplica al arrancar `theme` y `menuOption` guardados (`header/header.component.ts:66-88`); el `auth-layout` aplica `theme` (`auth-layout.component.ts:41-49`). Ninguno aplica `choose_skin`/`theme-*`.
- Header: `layout/header/header.component.html`. Nav derecho (`:34-54`): botón fullscreen (`:35-41`, solo si `!minimal()`), luego `<li ngbDropdown>` del usuario (`:42-53`) con ícono `i-feather name="user"`. El botón nuevo iría entre ambos (a la izquierda del dropdown de usuario). Los botones del header usan `<a class="nav-link nav-link-lg collapse-btn"> <i-feather ...>` (`:36-39`). El header se usa también con `minimal()` (cliente) que muestra el dropdown de usuario pero no fullscreen (`header.component.html:28-55`).
- Config por defecto: `config/config.service.ts:17-21` (`variant: 'light'`, `theme_color: 'white'`, `sidebar.backgroundColor: 'light'`).
- El header inyecta `RightSidebarService` y tiene `toggleRightSidebar()` (`header.component.ts:34,48,141-149`), pero `header.component.html` no lo invoca (código muerto). `RightSidebarService` se exporta de `core/index.ts:6`; solo lo usan header y right-sidebar.
- Tests: `right-sidebar.component.spec.ts` (19 líneas) existe; `header.component.spec.ts:86-91` verifica que el header mantiene toggle, fullscreen y menú de usuario (iconos feather `menu`, `maximize`, `user`).
- Docs que mencionan el panel: `docs/frontend/panel_admin/reference.md:44` (árbol de carpetas), `docs/tasks/TASK-credencial-detalle-layout.md:50`.
- SCSS del panel: `assets/scss/components/_settingSidebar.scss`; skins por tema en `assets/scss/skins/_{white,black,cyan,purple,orange,green,red,dark}.scss`.

### Decisiones confirmadas por el usuario (2026-10-02)
- El botón cambia el **modo global completo**, es decir la lógica de "Select Layout" (`lightThemeBtnClick`/`darkThemeBtnClick`: clases `light`/`dark`, sidebar y skin `theme-white`/`theme-black`, con su persistencia en localStorage), no solo el color del sidebar. Los iconos son los del panel "Sidebar Color": luna en light (clic → dark), sol en dark (clic → light).
- El botón aparece **solo en el header de staff** (layout principal). La variante `minimal()` (layout de cliente) queda sin cambios.
- Quitar el panel implica perder la elección de los 7 colores de tema (intencional, "quitarlo de donde está").

### Hipótesis / supuestos no confirmados
- No se verificó visualmente cómo se ve la app en modo dark con un `choose_skin` de un color distinto guardado de antes (p. ej. `theme-purple`) si el panel se elimina.
- No se confirmó si debe fijarse algún color por defecto al retirar la selección de color (hoy el toggle fija `theme-white` / `theme-black`).

### Módulos y dependencias relacionadas
- Frontend `panel_admin/` (Angular): `layout/header/`, `layout/right-sidebar/`, `layout/app-layout/main-layout/`, `core/service/rightsidebar.service.ts`, `core/service/storage.service.ts` (`LocalStorageService`, usa prefijo en `storage.service.ts:25-50`), `core/index.ts`, SCSS de skins. Sin impacto en backend ni migraciones.

### Implementaciones similares existentes
- Los handlers `lightThemeBtnClick`/`darkThemeBtnClick` (`right-sidebar.component.ts:126-179`) ya implementan el cambio completo y su persistencia. El header ya replica el patrón de "aplicar tema guardado al arrancar" (`header.component.ts:66-88`) y de botón con `i-feather` + `Renderer2` sobre `document.body`.
- Los iconos del panel son FontAwesome (`fas fa-sun`/`fa-moon`); el header usa mayormente `i-feather` (`menu`, `maximize`, `user`) con un `fas fa-sign-out-alt` en el menú (`header.component.html:48-49`).

### Comportamiento actual
- El cambio de modo y de color se hace abriendo el engranaje lateral derecho en las pantallas del panel. El estado se guarda en localStorage (`theme`, `menuOption`, `choose_skin`, `choose_skin_active`) y se reaplica al recargar: `theme`/`menuOption` por el header, `choose_skin` por el right-sidebar.
- El header no tiene control de tema.

### Restricciones
- `docs/CLAUDE.md`: el proyecto tiene deuda técnica conocida; no asumir por nombres. Tests existentes de header (`header.component.spec.ts`) y right-sidebar deben actualizarse si cambian.
- `docs/frontend/panel_admin/reference.md:44` describe la carpeta `right-sidebar/`; debería reflejar el cambio.

### Riesgos identificados
- Perder la aplicación de `choose_skin`/`theme-*` al arrancar si se elimina el panel sin mover esa lógica (el skin deja de aplicarse tras recargar).
- Estado inconsistente: usuarios con `choose_skin` de un color distinto (p. ej. `theme-purple`) guardado; el toggle fijaría `theme-white`/`theme-black` pisando esa elección.
- Duplicación de la lógica de tema entre header, auth-layout y la nueva ubicación (hoy repartida en tres componentes).
- Cobertura de tests escasa en el área (spec del right-sidebar de 19 líneas, sin pruebas de los handlers).
- Pantallas que dependen de la clase `dark`/`dark-sidebar` en `body` (ej. skins SCSS y el logo del sidebar de TASK-favicon-sidebar-icons) deben seguir respondiendo igual.

### Veredicto de complejidad
**NEEDS_PLAN** — Cambio acotado a `panel_admin/` (header, layout, un componente a retirar, specs y doc), sin backend, contrato de API ni decisión arquitectónica nueva; requiere decidir en el plan dónde vive la lógica de tema/arranque.

### Diseño requerido
**NO** — Un único botón de icono con patrón visual ya existente en el header (mismo estilo que fullscreen) y iconos definidos por el usuario; no hay pantalla ni flujo nuevo que comparar.

## Diseño
_No aplica_

## Arquitectura
_No aplica según veredicto_

## Plan
[PLAN-2026-10-02-theme-switcher-relocation.md](../plans/PLAN-2026-10-02-theme-switcher-relocation.md) (v1)

Hallazgo adicional del plan: `LocalStorageService` antepone el prefijo `light_`/`dark_` al leer, pero el panel escribe claves crudas (`theme`, `menuOption`, `choose_skin`), por lo que hoy el tema no se recupera al recargar. El `ThemeService` nuevo lee y escribe las claves crudas de forma consistente.

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
