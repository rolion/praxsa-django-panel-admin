# TASK-favicon-sidebar-icons: Favicon, titulo de pestana y logos del menu lateral

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** NO
**Rama:** claude/favicon-sidebar-icons-290108
**Pull Request:** https://github.com/rolion/praxsa-django-panel-admin/pull/63

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-01 | (nuevo) → INVESTIGATION | Task creado | delivery-investigate |
| 2026-10-01 | INVESTIGATION → PLANNING → ENGINEERING | Plan v1 listo, PR abierto para aprobacion humana | delivery-plan |
| 2026-10-01 | ENGINEERING → REVIEW | Implementación completa | delivery-engineer |
| 2026-10-01 | REVIEW → ENGINEERING | Quality Gate FAIL: REV-01 (Medium, IMPLEMENTATION) | delivery-review |
| 2026-10-01 | ENGINEERING → REVIEW | REV-01 corregido: logos en blanco en skin oscura | delivery-engineer |
| 2026-10-01 | REVIEW → PUBLISH | Quality Gate PASS (re-review), REV-01 resuelto | delivery-review |
| 2026-10-01 | PUBLISH → REVIEW | Alcance ampliado por el usuario: logo del menu superior de /calculadora; requiere re-review | delivery-engineer |
| 2026-10-01 | REVIEW → PUBLISH | Quality Gate PASS (3.a revision) con 2 hallazgos Low abiertos (REV-02, REV-03) | delivery-review |
| 2026-10-01 | PUBLISH → REVIEW | Alcance ampliado por el usuario: logo y layout de la pagina de login; requiere re-review | delivery-engineer |
| 2026-10-01 | REVIEW → PUBLISH | Quality Gate PASS (4.a revision) con REV-02 y REV-03 Low abiertos | delivery-review |
| 2026-10-01 | PUBLISH → PUBLISH | Descripción del PR completada; pendiente de aprobación humana | delivery-publish |
| 2026-10-01 | PUBLISH → REVIEW | Alcance ampliado por el usuario: el sidebar abierto reutiliza el logo del login; plan v2 con changelog; requiere re-review | delivery-engineer |
| 2026-10-01 | REVIEW → PUBLISH | Quality Gate PASS (5.a revision), REV-03 confirmado Resolved, REV-02 Low abierto | delivery-review |

## Investigación

### Requerimiento
Cambiar el icono de la pestana por `favicon.ico` (adjunto, `proforma/src/assets/img/favicon.ico`) y el titulo de la pestana a "Praxsa Admin". El logo del menu lateral debe ser la segunda imagen adjunta (PRAXSA ADMIN con Rx, `2.webp`) con el menu extendido/abierto; con el menu cerrado debe mostrarse la tercera imagen (`praxa-image-fb.jpg-removebg-preview`, el Rx solo).

### Hechos encontrados
- `panel_admin/src/app/layout/sidebar/sidebar.component.html:4-6` — el menu lateral esta en `panel_admin` (no en `proforma`): `.sidebar-brand` con un unico `<img src="assets/images/praxsa-admin-logo.png" class="header-logo">`, sin variante para menu colapsado.
- `panel_admin/src/assets/images/praxsa-admin-logo.png` — PNG 358x100 existente (commit `efa1d46`, "assets reales del usuario"); es el logo actual, distinto de `2.webp`.
- `panel_admin/src/assets/scss/layouts/_layout.scss:441-470` — `.sidebar-brand` 70px de alto; `.header-logo { height: 30px }`; existe un `.sidebar-brand.sidebar-brand-sm { display: none }` (linea 448) y `_layout.scss:73-75` lo muestra (`display:block`) en otro contexto, ninguno usado hoy en el HTML del sidebar.
- `panel_admin/src/assets/scss/layouts/_sidebar.scss:978-1060` y `_layout.scss:23-30` — el menu colapsado se controla con la clase `side-closed` en `<body>` (ancho 60px); `side-closed-hover` lo expande a 260px al pasar el mouse (`sidebar.component.ts:136-143`, `header.component.ts:92-136`). Hay que contemplar ambos estados.
- `panel_admin/src/index.html:6,8` — `<title>Oreva - Angular 21+ Admin Dashboard Template </title>` y `<link rel="icon" href="assets/images/favicon.ico">`. `panel_admin/angular.json:47,126` además publica `src/favicon.ico`. Ambos favicon (`panel_admin/src/favicon.ico`, `panel_admin/src/assets/images/favicon.ico`) son los de la plantilla (difieren byte a byte de `proforma/.../favicon.ico`).
- `proforma/src/index.html:5,8` — `<title>Proforma</title>`, `<link rel="icon" href="favicon.ico">`; `proforma/src/favicon.ico` difiere del adjunto `proforma/src/assets/img/favicon.ico` (1150 bytes). `proforma/src/assets/img/praxa-image-fb.jpg-removebg-preview.png` es PNG RGBA 1024x1024 (candidato a "tercera imagen").
- `praxsa_manager/product/admin.py:5` — Django admin con `site_header = 'Praxsa Panel Admin'`; `praxsa_manager/templates/admin/base.html:7` y `product/templates/product/client.html:4` usan `{% block title %}` sin favicon.
- `panel_admin/src/app/authentication/signin/signin.component.html:12` — el login ya usa `praxsa-admin-logo.png`.

### Hipótesis / supuestos no confirmados
- "Pestana de la pagina" se asume que es la app Angular `panel_admin` (la que tiene el menu lateral y se llama "Admin"); no se confirmó si tambien debe cambiarse `proforma/src/index.html` (hoy "Proforma") ni las paginas Django.
- Se asume que la "segunda imagen" es el adjunto `2.webp` (hoy no existe en el repo) y que reemplaza/complementa `praxsa-admin-logo.png`; si el logo del login debe seguir igual no se confirmó.
- Se asume que la "tercera imagen" es `praxa-image-fb.jpg-removebg-preview.png` de `proforma/src/assets/img` (fondo transparente); el adjunto `1.png` es el Rx solo sobre fondo blanco/favicon.
- No se verifico visualmente el comportamiento de `.sidebar-brand-sm` dentro del layout actual.

### Módulos y dependencias relacionadas
`panel_admin/src/index.html`, `panel_admin/angular.json` (assets), `layout/sidebar/sidebar.component.{html,ts}`, `assets/scss/layouts/_layout.scss` y `_sidebar.scss`, `header.component.ts` (alterna `side-closed`). Posible: `proforma/src/index.html`.

### Implementaciones similares existentes
El login ya se ajusto con assets reales del usuario (TASK-login-panel-admin-backend, commit `efa1d46`), mismo patron de `assets/images/*.png`.

### Comportamiento actual
El sidebar muestra siempre el mismo logo de 30px de alto; al colapsar a 60px (clase `side-closed`) el logo ancho de 358x100 no cabe como marca compacta. La pestana muestra el titulo "Oreva - Angular 21+ Admin Dashboard Template" y el favicon de la plantilla.

### Restricciones
`docs/CLAUDE.md`: proyecto con deuda técnica, seguir patrones existentes; plantilla `panel_admin/` documentada en `docs/frontend/panel_admin/reference.md`.

### Riesgos identificados
- Estado `side-closed-hover` (expandido temporalmente) debe mostrar el logo grande, no el Rx.
- Tamano/proporcion de `2.webp` (casi cuadrado, ~1280x1200) vs. contenedor de 70px de alto: requiere ajustar `.header-logo`.
- Cache de favicon del navegador puede ocultar el cambio al verificar.
- `.webp` vs `.png`: confirmar formato a versionar.

### Veredicto de complejidad
**NEEDS_PLAN** — cambio acotado de frontend (assets, `index.html`, markup y SCSS del sidebar) sin impacto en backend, API ni permisos, pero toca varios archivos y dos estados de UI.

### Diseño requerido
**NO** — son assets proporcionados por el usuario con comportamiento definido (grande abierto, Rx cerrado); no hay alternativas de UI que comparar.

## Diseño
_No aplica_

## Arquitectura
_No aplica según veredicto_

## Plan
`docs/plans/PLAN-2026-10-01-favicon-sidebar-icons.md` (v2 — ver su Changelog)

## Implementación
Implementado según PLAN v1 (actualizado a v2 por las ampliaciones), todo en `panel_admin/`:
- `index.html`: `<title>Praxsa Admin</title>`; `favicon.ico` entregado copiado a `src/favicon.ico` y `src/assets/images/favicon.ico`.
- Assets nuevos: `praxsa-rx-mark.png` (Rx recortado, 128px) y, tras la ampliación 3, el sidebar abierto usa `praxsa-admin-logo-horizontal.webp` (el mismo del login); `praxsa-admin-logo-full.webp` (imagen 2) se retiró.
- `sidebar.component.html`: `img.logo-full` + `img.logo-mark`. `_layout.scss`: `.sidebar-brand` 80px de alto, logo 56px, Rx 34px y regla `.side-closed:not(.side-closed-hover)` que alterna ambos.
- `sidebar.component.spec.ts`: test de los dos `<img>`; además se agregó `provideRouter` y `FeatherModule.pick(allIcons)` porque el spec existente ya fallaba (2/2) por falta de ese provider.
- Verificación propia (no es el Quality Gate): spec del sidebar 2/2 OK; en `ng serve` el título es "Praxsa Admin", menú abierto muestra logo completo, `side-closed` muestra solo el Rx dentro de los 60px, `side-closed-hover` vuelve al logo completo. No se revisó el tema oscuro ni la corrida completa de `ng test`.
- Corrección de REV-01: `skins/_darksidebar.scss` aplica `filter: brightness(0) invert(1)` a `.header-logo` del sidebar oscuro (los logos son de un solo color), de modo que se leen en blanco. Verificado en vivo en skin oscura con menú abierto y cerrado; falta nueva corrida del Quality Gate.
- Ampliacion pedida despues del PASS: el menu superior de `/calculadora` (`header.component.html`, modo `minimal`) usa ahora `praxsa-3m-header-logo.jpg` (PRAXSA + 3M Automotive Window Films, 700px de ancho, desde `3.jpg`) en vez de `praxsa-admin-logo.png`; `.header-brand-logo` con `max-width: 100%` (`_calculadora.scss`). Spec del header actualizado. Verificado en vivo en escritorio y en 375px (sin scroll horizontal); specs header + minimal-layout 17/17 y `ng lint` limpio. Fuera de esta ampliacion el login conserva `praxsa-admin-logo.png`. Pendiente de nuevo Quality Gate.
- Ampliacion 2 (login, pedida despues del PASS): `signin.component.html` usa `praxsa-admin-logo-horizontal.webp` (imagen 4, transparente, 700px) sobre el formulario; la imagen lateral `praxsa-login-hero.png` se quito del markup (queda un comentario y el asset sin tocar) y el formulario queda centrado (`.login-card` max-width 520px; se eliminaron las reglas de `col-md-5/7` del scss). Spec nuevo del signin; specs signin 6/6, `ng lint` limpio, verificado en vivo en escritorio y 375px sin desborde. Pendiente de nuevo Quality Gate. Plan v1 sigue sin changelog de las dos ampliaciones (REV-03).
- Ampliacion 3 (sidebar, pedida despues del PASS): `sidebar.component.html` y su spec usan `praxsa-admin-logo-horizontal.webp` (el logo del login) para el menu abierto; se elimino `praxsa-admin-logo-full.webp`; `.sidebar-brand` pasa a 80px y el logo a 56px (`_layout.scss`). Verificado en vivo (iframe con las llamadas a la API bloqueadas): menu abierto con el logo horizontal (142x56), cerrado con el Rx (60px), skin oscura con logos blancos; spec del sidebar 2/2 y `ng lint` limpio. Plan actualizado a v2 con Changelog y REV-03 marcado `Resolved`. Pendiente de nuevo Quality Gate; no se corrio la suite completa ni `ng build` para este cambio.
- Deuda/limitaciones: favicon de 16x16 (pixelado en HiDPI); `proforma` y páginas Django no se tocaron (fuera de alcance).

## Review
**PASS** (re-review 2026-10-01; REV-01 `Resolved`). Detalle del re-review al final de esta seccion.

Primera revision: **FAIL** (2026-10-01, misma sesion que delivery-engineer: aislamiento solo procedimental).
- Issue abierto: `docs/reviews/REV-2026-10-01-favicon-sidebar-icons-01.md` (Medium, IMPLEMENTATION): logo casi invisible en skin oscura; incumple el criterio "tema claro y oscuro" del plan.
- Pasa: spec del sidebar 2/2, `ng lint` limpio, `ng build` OK, titulo/favicon, alternancia abierto/cerrado/hover en tema claro.
- `ng test` completo: 448 OK, 13 FAILED, todos `should create` de componentes no tocados por este diff (AdvanceTable, Blank, Dashboard2, First1-3, Footer, Page404/500, Second1-2, Signup, Third1); no se comparo contra baseline de master.
- `npm audit --omit=dev`: 3 vulnerabilidades (1 moderada, 2 altas) en dependencias, preexistentes y fuera de alcance.

### Re-review (PASS)
Misma sesion que delivery-engineer (aislamiento procedimental). Diff contra master: solo `panel_admin/` mas docs, dentro del alcance del plan.
- `ng test` completo: 448 OK, 13 FAILED. En master (worktree limpio): 453 OK, 14 FAILED. Los 13 fallos restantes son identicos a los de master (`should create` de AdvanceTable, Blank, Dashboard2, First1-3, Footer, Page404/500, Second1-2, Signup, Third1); la unica diferencia es `SidebarComponent should create`, que este PR corrige.
- `ng lint`: All files pass linting. `ng build`: OK (warning preexistente de reglas SCSS omitidas).
- `npm audit --omit=dev`: 3 vulnerabilidades (1 moderada, 2 altas), preexistentes y fuera de alcance. Cobertura (`--code-coverage`) no ejecutada.
- Verificacion manual en vivo: titulo "Praxsa Admin", REV-01 resuelto (logos blancos en skin oscura abierto/cerrado), tema claro sin filtro.
- Limitaciones: favicon 16x16; `proforma`/Django sin tocar (fuera de alcance).

### 3.a revision (PASS, ampliacion del logo del header de /calculadora)
Misma sesion que delivery-engineer (aislamiento procedimental). Diff de la ampliacion: `header.component.{html,spec.ts}`, `_calculadora.scss`, `praxsa-3m-header-logo.jpg`.
- `ng test` completo: 448 OK, 13 FAILED; los mismos 13 `should create` preexistentes que en master. `ng lint` limpio; `ng build` OK; `npm audit --omit=dev`: 3 vulnerabilidades preexistentes. Cobertura no ejecutada.
- Manual en vivo en `/calculadora`: el logo carga (700x81), sin desborde a 375px.
- Hallazgos abiertos, ambos Low y no bloqueantes: `docs/reviews/REV-2026-10-01-favicon-sidebar-icons-02.md` (IMPLEMENTATION: fondo blanco del JPG visible con la clase `dark`) y `docs/reviews/REV-2026-10-01-favicon-sidebar-icons-03.md` (PLAN: plan v1 sin changelog de la ampliacion).

### 4.a revision (PASS, ampliacion del login)
Misma sesion que delivery-engineer (aislamiento procedimental). Diff: `signin.component.{html,scss,spec.ts}` y `praxsa-admin-logo-horizontal.webp`.
- `ng test` completo: 449 OK, 13 FAILED (los mismos 13 `should create` preexistentes de master). `ng lint` limpio; `ng build` OK; `npm audit --omit=dev`: 3 vulnerabilidades preexistentes. Cobertura no ejecutada.
- Manual en vivo: titulo "Praxsa Admin", logo horizontal cargado, sin imagen lateral, tarjeta de 520px centrada (offset 0), 2 inputs y boton "Ingresar". No se probo el login contra un backend real (solo los specs con `HttpTestingController`).
- Observacion: `praxsa-admin-logo.png` ya no se referencia en `panel_admin/src` y `praxsa-login-hero.png` solo en un comentario; quedan como assets sin uso (no bloqueante).
- Abiertos (Low): REV-02 (fondo blanco del JPG del header en oscuro) y REV-03 (plan v1 sin changelog; ahora cubre dos ampliaciones).

### 5.a revision (PASS, sidebar con el logo del login y plan v2)
Misma sesion que delivery-engineer (aislamiento procedimental). Diff de la ampliacion: `sidebar.component.{html,spec.ts}`, `_layout.scss`, retiro de `praxsa-admin-logo-full.webp`, plan v2 y docs.
- `ng test` completo: 449 OK, 13 FAILED (los mismos 13 `should create` preexistentes de master). `ng lint` limpio; `ng build` OK; `npm audit --omit=dev`: 3 vulnerabilidades preexistentes. Cobertura no ejecutada.
- Manual en vivo (iframe con las llamadas a la API bloqueadas, porque el backend local devuelve 401 al token de prueba): menu abierto con `praxsa-admin-logo-horizontal.webp` (143x56, encabezado 80px); `side-closed` muestra solo el Rx (menu de 60px); `side-closed-hover` vuelve al logo; skin oscura con filtro blanco; tema claro sin filtro; titulo "Praxsa Admin".
- Sin referencias vivas a `praxsa-admin-logo-full.webp` en `panel_admin/src` (solo en docs, como historia).
- REV-03 confirmado `Resolved` (plan v2 con Changelog). Abierto (Low, no bloqueante): REV-02 (fondo blanco del JPG del header de `/calculadora` con la clase `dark`).

## Publicación
PR: https://github.com/rolion/praxsa-django-panel-admin/pull/63 — **Listo para aprobación humana** (no mergeado). Cambio no sensible (sin arquitectura, auth, DB ni infraestructura). Hallazgos Low abiertos: REV-02, REV-03; limitaciones listadas en `## Known limitations` del PR.
