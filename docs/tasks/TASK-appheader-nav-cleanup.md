# TASK-appheader-nav-cleanup: Quitar del header de panel_admin nombre de usuario, buscador, selector de idioma, mensajes y alertas

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** NO
**Rama:** `claude/appheader-nav-cleanup-650d44` (asignada por el entorno)
**Pull Request:** [#59](https://github.com/rolion/praxsa-django-panel-admin/pull/59)

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-09-30 | (nuevo) → INVESTIGATION | Task creado | delivery-investigate |
| 2026-09-30 | INVESTIGATION → PLANNING | Veredicto NEEDS_PLAN, diseño NO; sin arquitectura requerida | delivery-plan |
| 2026-09-30 | PLANNING → ENGINEERING | Plan v1 escrito (4 archivos frontend + i18n, spec actualizado, sin E2E ni dependencias); PR abierto sobre la rama asignada por el entorno | delivery-plan |
| 2026-09-30 | ENGINEERING → REVIEW | Implementación completa según plan v1 | delivery-engineer |

## Investigación

### Requerimiento
"En el appheader nav hay muchos componentes que no necesitamos, como el nombre de usuario, un input de búsqueda, una bandera para cambiar el idioma, un botón de mensajes (icono de sobre) y un botón de alertas (icono de campana), eso no los necesitamos."

### Hechos encontrados
- El `app-header` es el componente de `panel_admin/` (no `proforma/`): selector `app-header` en `panel_admin/src/app/layout/header/header.component.ts:21`, usado en `panel_admin/src/app/layout/app-layout/main-layout/main-layout.component.html:1`. `proforma/src/app/components/top-menu/top-menu.component.html` es otro menú (Praxsa / Calculadora / Mis proformas) sin ninguno de los elementos mencionados.
- Nav izquierdo (`header.component.html:2-24`): toggle del sidebar (`:4-8`), **nombre de usuario** `<span class="nav-link nav-link-lg current-user-name">{{currentUserName}}</span>` (`:9-11`), **input de búsqueda** dentro de `<form>` con `placeholder="{{'HEADER.SEARCH.TEXT' | translate}}"` (`:12-22`).
- Nav derecho (`header.component.html:25-179`): fullscreen (`:26-30`), **bandera/idioma** (`:31-49`, usa `flagvalue`, `defaultFlag`, `listLang`, `setLanguage`), **mensajes (sobre)** dropdown con 6 mensajes hardcodeados de la plantilla (`:50-117`), **alertas (campana)** dropdown con 5 notificaciones hardcodeadas (`:118-166`), menú de usuario con ícono genérico, nombre como título y Logout (`:167-178`).
- TS asociado al contenido a quitar (`header.component.ts`): `flagvalue`, `countryName`, `langStoreValue`, `defaultFlag`, `listLang` (`:39-42,57-61`), lógica de idioma en `ngOnInit` (`:67-76`), `setLanguage` (`:127-132`), getter `currentUserName` (`:133-135`, también lo usa el título del dropdown de usuario en `html:171`, así que se sigue usando). Imports que quedarían sin uso: `NgScrollbar`, `TranslateModule`, `NgClass` (`:11,12,1,25-32`), inyección `languageService` y `storageService` (storageService sí se usa también en `ngAfterViewInit` `:80-95`).
- Estilo propio: `header.component.sass:1-4` define solo `.current-user-name`.
- SCSS global relacionado con los elementos (compartido con la plantilla): `.search-element` en `assets/scss/override/_navbar.scss:88,312,318,359,509`, `rtl/_layout-rtl.scss:98`, `skins/_dark.scss:84`; `.message-toggle`/`.lang-toggle` en `_navbar.scss:255,278`; `.lang-dropdown-list` en `override/_dropdown.scss:57`; `.dropdown-list-icons`/`.dropdown-list-message` en `_dropdown.scss:197,232`, `rtl/_bootstrap-rtl.scss:29,33`, `skins/_dark.scss:546`; `.lang-toggle` en `skins/_white.scss:363`, `rtl/_layout-rtl.scss:107`.
- i18n: `HEADER.SEARCH.TEXT` existe solo en `assets/i18n/{de,en,es}.json:2-5` (bloque `HEADER` contiene únicamente eso). Grep no muestra otros consumidores de `HEADER.SEARCH` fuera del header.
- `LanguageService` se registra globalmente (`app.config.ts:9,31`) y `sidebar.component.ts:18,35` también usa `TranslateModule`; el servicio aplica idioma por navegador/`localStorage` en su constructor (`core/service/language.service.ts:13-22`), independiente del selector del header.
- Spec actual `header.component.spec.ts`: test "renders the username on the left side of the header nav" consulta `.current-user-name` (`:~80-88`), que deberá cambiar; el test de `currentUserName` (`:~45-58`) sigue válido mientras el getter exista; el test "no longer shows Profile/Settings" (`:~68-72`) es independiente.
- Decisión previa relevante: `TASK-login-panel-admin-backend` movió el nombre de usuario del dropdown derecho al nav izquierdo (`docs/tasks/TASK-login-panel-admin-backend.md:139`), y su requerimiento 7 pedía mostrar el nombre del usuario autenticado (`:31`). El pedido actual revierte parcialmente esa decisión.
- Última migración: no aplica (sin cambios de backend/modelos).

### Hipótesis / supuestos no confirmados
- "Nombre de usuario" se interpreta como el `<span>` del nav izquierdo (`html:9-11`). No está confirmado si también debe quitarse el nombre como título del dropdown de usuario (`html:171`); por la lectura literal ("en el nav") se asume que ese permanece, junto con el ícono de usuario y Logout.
- Se asume que fullscreen, toggle del sidebar y el menú de usuario/Logout se conservan (no fueron mencionados).
- Se asume que el selector de idioma se elimina sin reemplazo, quedando solo el idioma por defecto resuelto por `LanguageService`; no se confirmó si la aplicación usa traducciones visibles al usuario (sidebar usa `TranslateModule`).
- No se confirmó si el SCSS global de esos elementos es usado por otras pantallas de la plantilla (ej. `.search-element`, `.dropdown-list-*`); probable que solo el header los use, pero no se verificó exhaustivamente.
- Tampoco se verificó si los assets `assets/images/flags/*` y `assets/images/users/user-*.png` son usados fuera del header.

### Módulos y dependencias relacionadas
Solo frontend `panel_admin/`: `layout/header/*` (html, ts, sass, spec), SCSS global en `assets/scss/{override,rtl,skins}`, i18n `assets/i18n/*.json`, assets de banderas/usuarios. Backend y `proforma/` no involucrados.

### Implementaciones similares existentes
El TASK previo ya redujo el sidebar y el menú de usuario del header a lo mínimo (`docs/tasks/TASK-login-panel-admin-backend.md:113`), mismo criterio de "recortar la plantilla a lo necesario".

### Comportamiento actual
El header muestra: toggle sidebar, nombre del usuario, buscador (sin acción; el form no tiene handler), y a la derecha fullscreen, bandera con dropdown de idiomas (en/es/de), sobre con mensajes ficticios, campana con notificaciones ficticias y menú de usuario con Logout. Mensajes y alertas son datos de demostración de la plantilla, sin conexión al backend.

### Restricciones
- `docs/CLAUDE.md`: proyecto con deuda técnica conocida; no asumir nada por nombres de archivo.
- Suite de tests con 15 fallas preexistentes en specs de la plantilla no relacionadas (`TASK-login-panel-admin-backend.md:148`); el spec del header debe mantenerse verde.

### Riesgos identificados
- Eliminar el nombre del nav izquierdo contradice el requerimiento 7 y la decisión de `TASK-login-panel-admin-backend`; conviene dejar explícito que el nombre sigue visible en el dropdown de usuario.
- Quitar imports/propiedades sin uso debe respetar `ng lint`; riesgo bajo de borrar SCSS global compartido por error.
- Quitar el selector de idioma elimina la única vía de cambiar el idioma en la UI.

### Veredicto de complejidad
**NEEDS_PLAN** — Cambio acotado a un componente y su estilo/spec, sin decisión arquitectónica nueva ni backend, pero toca varios archivos (html, ts, sass, spec, posiblemente SCSS global e i18n) y hay decisiones de alcance (limpieza de código muerto, nombre en dropdown) que conviene fijar en un plan en lugar de tratarlo como fix trivial.

### Diseño requerido
**NO** — Es una eliminación de elementos de UI que no introduce pantallas, flujos ni componentes nuevos; no hay alternativas visuales que comparar.

## Diseño
_No aplica_

## Arquitectura
_No aplica según veredicto_

## Plan
[PLAN-2026-09-30-appheader-nav-cleanup](../plans/PLAN-2026-09-30-appheader-nav-cleanup.md) — versión vigente: v1

## Implementación
Según plan v1, en `panel_admin/src/`:
- `header.component.html`: quitados nombre del nav izquierdo, buscador, idioma, mensajes y alertas; quedan toggle del sidebar, fullscreen y menú de usuario (nombre como título + Logout).
- `header.component.ts`: eliminado estado/lógica de idioma (`flagvalue`, `listLang`, `setLanguage`, etc.) e imports sin uso (`NgClass`, `NgScrollbar`, `TranslateModule`, `FormsModule`).
- `header.component.sass` vaciado; bloque `HEADER` quitado de `assets/i18n/{de,en,es}.json` (grep previo: sin otros usos).
- `header.component.spec.ts`: el test del nombre a la izquierda se reemplazó por 3 tests (widgets quitados ausentes, toggle/fullscreen/usuario presentes, nombre solo en `.dropdown-title` con Logout).

Desvío menor respecto al plan: se **mantuvo** la inyección de `LanguageService` en el header (plan decía dejar de inyectarlo). Es el único lugar que lo instancia, y su constructor aplica el idioma inicial que usa el `translate` pipe del sidebar; quitarlo habría dejado el sidebar sin idioma. Queda con comentario en el código. Deuda técnica: mover esa inicialización a un `APP_INITIALIZER`/`app.config`.

Autoverificación del engineer (no sustituye el Quality Gate): `ng lint` limpio, `ng build` OK, spec del header 7/7 SUCCESS.

## Review
_Pendiente_

## Publicación
_Pendiente_
