# TASK-favicon-sidebar-icons: Favicon, titulo de pestana y logos del menu lateral

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** NO
**Rama:** claude/favicon-sidebar-icons-290108
**Pull Request:** _sin abrir todavía_

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-01 | (nuevo) → INVESTIGATION | Task creado | delivery-investigate |
| 2026-10-01 | INVESTIGATION → PLANNING → ENGINEERING | Plan v1 listo, PR abierto para aprobacion humana | delivery-plan |

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
`docs/plans/PLAN-2026-10-01-favicon-sidebar-icons.md` (v1)

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
