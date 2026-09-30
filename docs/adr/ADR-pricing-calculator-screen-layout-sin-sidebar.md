# ADR-pricing-calculator-screen-layout-sin-sidebar: Layout mínimo (header con logo, sin sidebar) como ruta hermana, reutilizando `app-header` con una variante

**Estado:** Propuesto
**Task relacionado:** TASK-pricing-calculator-screen
**Fecha:** 2026-09-30

## Contexto

El DDR (`docs/design/DDR-pricing-calculator-screen-pantalla-calculadora.md`) pide que la calculadora se vea **sin sidebar**, con logo PRAXSA a la izquierda y menú de perfil a la derecha. Hechos de la investigación:
- Todas las rutas autenticadas cuelgan de `MainLayoutComponent`, que monta siempre `app-header`, `app-sidebar` y `app-right-sidebar` (`main-layout.component.html:1-3`, `app.routes.ts:7-67`).
- El header no tiene logo (vive en `sidebar.component.html:4-7`) y su toggle depende del sidebar (`header.component.html:5-6`). El header además aplica el tema al `body` en `ngAfterViewInit` (`header.component.ts`), por lo que conviene seguir usándolo.
- El CSS de la plantilla asume sidebar: `.main-content { padding-left: 285px }` (`assets/scss/layouts/_layout.scss:710-716`) y el footer con 280px; la barra superior también se desplaza por el sidebar.

## Decisión

1. **Nuevo layout `MinimalLayoutComponent`** (standalone, junto a `main-layout` y `auth-layout`) que monta solo `app-header` (variante mínima) + `<router-outlet>`. No monta sidebar ni right-sidebar.
2. **Ruta hermana** en `app.routes.ts`: `{ path: 'calculadora', component: MinimalLayoutComponent, canActivate: [AuthGuard], loadChildren: ... }`, con la pantalla cargada de forma diferida como el resto de módulos. El resto de pantallas sigue usando `MainLayoutComponent` sin cambios.
3. **`HeaderComponent` gana una variante mínima** mediante un `input()` booleano (por defecto `false`, comportamiento actual intacto): en variante mínima muestra el logo (`assets/images/praxsa-admin-logo.png`, enlazado al dashboard) y oculta el toggle del sidebar. Se conserva fullscreen y el menú de usuario con Logout.
4. **Estilos:** el offset por sidebar se neutraliza con una clase contenedora propia del layout mínimo (p. ej. `.layout-minimal`) definida en un SCSS global acotado junto a `_ordenes.scss`, sin editar las reglas existentes de `_layout.scss` (para no alterar las demás pantallas).
5. **Entrada a la pantalla** (menú lateral y/o botón en el listado de proformas): un único ítem nuevo, con `permission` si corresponde ocultarlo, como en `sidebar.metadata.ts:12-25`. La ubicación final es decisión pendiente de negocio y del plan; no cambia esta arquitectura.
6. **Autenticación/autorización:** sin cambios. Mismo `AuthGuard` (solo verifica sesión, ver `docs/frontend/panel_admin/reference.md`); el control real sigue en los endpoints (`IsStaffUser` + alcance por sucursal, `ADR-modulo-ordenes-proforma-nota-trabajo-alcance-permisos`).

## Alternativas consideradas

- **Flag en `MainLayoutComponent`** (ocultar el sidebar según la ruta): menos archivos, pero acopla el layout principal a una pantalla concreta y deja lógica de ruta dentro del layout. Descartada.
- **Reusar `AuthLayoutComponent`**: no incluye header ni el guard esperado; es el layout del login. Descartada.
- **Header nuevo independiente** (copia): duplica la lógica de tema, logout y fullscreen. Descartada; una variante con `input()` reutiliza todo con riesgo bajo.
- **Dejar el sidebar oculto con CSS (`sidebar-gone`)**: mantiene el componente montado y el toggle visible, y no cumple "sin menú lateral" de forma limpia. Descartada.

## Estrategia de rollback / mitigación

Cambio **aditivo**: layout y ruta nuevos; el input del header tiene un default que preserva el comportamiento actual, y las pantallas existentes no se modifican ni comparten reglas CSS nuevas. No toca autenticación, datos ni infraestructura. Rollback = quitar la ruta `calculadora` (y el ítem de menú); el resto del panel no se ve afectado. El spec existente del header (`header.component.spec.ts`) debe seguir en verde como verificación de que el default no cambió.

## Consecuencias

- Más fácil: futuras pantallas "de asesor" sin sidebar pueden colgar del mismo layout.
- Más difícil: hay un tercer layout que mantener. Riesgo a verificar en el plan: que `.layout-minimal` realmente anule el `padding-left: 285px` y el desplazamiento de la barra superior en tema claro/oscuro, y que funcione en móvil.
- Deuda aceptada: el header de las demás pantallas sigue sin logo (solo la variante mínima lo lleva).
