# PLAN-2026-10-01-favicon-sidebar-icons (v1)

**Task:** TASK-favicon-sidebar-icons
**DDRs relacionados:** Ninguno
**ADRs relacionados:** Ninguno

## Objective
Que la app `panel_admin` se identifique como "Praxsa Admin": favicon y titulo de la pestana propios, logo completo en el menu lateral abierto y solo el simbolo Rx cuando el menu esta cerrado.

## Context
Ver `docs/tasks/TASK-favicon-sidebar-icons.md`. Verificado de nuevo contra el codigo actual: las rutas y lineas citadas en la investigacion siguen vigentes.

## Current behavior
- `panel_admin/src/index.html:6` titulo "Oreva - Angular 21+ Admin Dashboard Template"; `:8` icono `assets/images/favicon.ico` (el de la plantilla). `panel_admin/angular.json:47,126` tambien publica `src/favicon.ico` (plantilla).
- `panel_admin/src/app/layout/sidebar/sidebar.component.html:4-6` un unico `<img class="header-logo" src="assets/images/praxsa-admin-logo.png">` (358x100) dentro de `.sidebar-brand`.
- `panel_admin/src/assets/scss/layouts/_layout.scss:441-470`: `.sidebar-brand` 70px de alto, `.header-logo` 30px.
- Menu colapsado = `body.side-closed` (60px, `_layout.scss:23`); al pasar el mouse se agrega `side-closed-hover` y se expande a 260px (`sidebar.component.ts:136-143`, `_sidebar.scss:1048`).

## Expected behavior
- Pestana: titulo "Praxsa Admin" y el `favicon.ico` entregado por el usuario.
- Menu abierto (y colapsado con hover): logo PRAXSA ADMIN (imagen 2).
- Menu colapsado sin hover: solo el Rx (imagen 3), centrado en los 60px.

## Architecture considerations
Cambio solo de frontend (assets + markup + SCSS); sin contrato API, datos, dinero, permisos ni dependencias nuevas. Acoplamiento: el alternado se hace solo con CSS sobre las clases de `<body>` que ya existen (`side-closed`, `side-closed-hover`), asi que no se toca `sidebar.component.ts` ni `header.component.ts`. Se reutiliza el patron de assets reales del usuario ya aplicado al login (commit `efa1d46`). Los dos `<img>` quedan en el DOM y se muestra uno u otro con CSS (sin logica Angular).

## Proposed solution
1. **Favicon**: copiar `proforma/src/assets/img/favicon.ico` (16x16, 1150 bytes) sobre `panel_admin/src/favicon.ico` y `panel_admin/src/assets/images/favicon.ico` (ambos se referencian: uno por `index.html`, otro por `angular.json`).
2. **Titulo**: `<title>Praxsa Admin</title>` en `panel_admin/src/index.html`.
3. **Assets de logo** (en `panel_admin/src/assets/images/`): `praxsa-admin-logo-full.webp` (imagen 2, reducida de 1281x1228 a ~400px de ancho para no cargar 1.2 MP en cada pagina) y `praxsa-rx-mark.png` (imagen 1/3, Rx, reducida a ~128x128). Se conserva `praxsa-admin-logo.png` sin tocar porque lo usa el login.
4. **Markup** del sidebar: dentro del mismo `<a>` dos imagenes, `.logo-full` y `.logo-mark`.
5. **SCSS** en `_layout.scss`: `.logo-mark {display:none}`; `.side-closed:not(.side-closed-hover) .main-sidebar .sidebar-brand` oculta `.logo-full` y muestra `.logo-mark`. Ajustar altura de `.sidebar-brand` (el logo es casi cuadrado, en 30px de alto quedaria ilegible) y tamano del Rx para 60px de ancho; revisar tambien la skin oscura (`_darksidebar.scss:87-93`, fondo oscuro con logo azul).

## Files/components affected
Frontend (`panel_admin`):
- `src/index.html`, `src/favicon.ico`, `src/assets/images/favicon.ico`
- `src/assets/images/praxsa-admin-logo-full.webp` (nuevo), `src/assets/images/praxsa-rx-mark.png` (nuevo)
- `src/app/layout/sidebar/sidebar.component.html`, `sidebar.component.spec.ts`
- `src/assets/scss/layouts/_layout.scss` (posible ajuste en `skins/_darksidebar.scss`)
Backend: ninguno. `proforma/`: ninguno (ver Out of scope).

## Implementation steps
1. Generar los dos assets de logo desde los adjuntos (`images/2.webp` y `images/1.png` de la sesion) con Pillow y guardarlos en `panel_admin/src/assets/images/`.
2. Copiar el `favicon.ico` en las dos ubicaciones y cambiar el `<title>` en `index.html`.
3. Actualizar el markup del sidebar con `.logo-full` / `.logo-mark`.
4. Agregar el SCSS de alternancia y ajustar alturas.
5. Agregar/actualizar la prueba unitaria del sidebar.
6. Verificacion manual con `preview_start` de `panel_admin`: menu abierto, colapsado, colapsado + hover, tema claro y oscuro, y titulo/favicon de la pestana (recargando sin cache).

## Test strategy
- **Unitario** (`sidebar.component.spec.ts`, TestBed): el DOM contiene `img.logo-full` con `assets/images/praxsa-admin-logo-full.webp` y `img.logo-mark` con `assets/images/praxsa-rx-mark.png`.
- **Verificacion manual en vivo** de la alternancia (la visibilidad depende de CSS real sobre clases del `<body>`, que un test unitario con jsdom/karma no valida de forma fiable) y del titulo/favicon.
- **E2E: no** — no cambia flujos de usuario, navegacion ni integracion front/back; es presentacion estatica. Tampoco se instala Playwright.

## Acceptance criteria
- La pestana muestra "Praxsa Admin" y el favicon entregado.
- Menu abierto: logo PRAXSA ADMIN completo y legible.
- Menu colapsado: solo el Rx, centrado, sin recortes; con hover se expande y vuelve el logo completo.
- Se ve bien en tema claro y oscuro.
- El login sigue mostrando `praxsa-admin-logo.png` sin cambios.
- Tests de `panel_admin` pasan y el build no agrega warnings nuevos.

## Risks
- El favicon entregado es solo 16x16: se vera pixelado en pantallas HiDPI y en accesos directos. Mitigacion: ninguna dentro de este alcance; se puede pedir una version de mayor resolucion.
- La plantilla ya tiene reglas de `.sidebar-brand` por skin; un ajuste de altura podria desalinear el menu. Mitigacion: verificar visualmente en ambos temas.
- Cache del navegador puede mostrar el favicon viejo al verificar.

## Out of scope
- `proforma/src/index.html` ("Proforma") y titulos/iconos de las paginas Django (`admin/base.html`, `client.html`).
- Cambiar el logo del login.
- Generar favicons en otros tamanos (PNG/apple-touch).
- Preguntas abiertas: ¿se quiere que `proforma` tambien diga "Praxsa Admin"? ¿Hay un favicon de mayor resolucion?

## Dependencias nuevas
Ninguna (Pillow solo se usa localmente para preparar los assets, no entra al proyecto).
