# Referencia: plantilla `panel_admin/` (Angular Admin Dashboard, ex-"Oreva")

Resumen destilado de la plantilla comprada, para que `delivery-design` y `delivery-architect` puedan citarla sin releer toda la doc de venta cada vez. **A diferencia de la primera versión de este archivo, la plantilla ya está en el repo** (mergeada a `master` en `panel_admin/` y `panel_admin_doc/`), así que todo acá cita rutas reales del repo — `archivo:línea` como cualquier otra investigación.

- **Código fuente de la plantilla:** `panel_admin/` — proyecto Angular standalone completo (`angular.json`, `package.json` propios). No es un componente que se importe en `proforma/`, es otra app Angular.
- **Documentación de la plantilla:** `panel_admin_doc/*.html` — sitio de docs de venta (ThemeForest), mismo contenido que antes pero ahora versionado en el repo. Sigue siendo doc de marketing (tiene botones "Buy Now"), así que verificar contra el código fuente real cuando algo importa (ver ejemplo de `shared/` abajo).

## Versiones reales instaladas (`panel_admin/package.json`)

| Paquete | `panel_admin/` (real) | `proforma/` (actual) |
|---|---|---|
| `@angular/core` | `^21.0.8` | `^16.1.0` |
| `@ng-bootstrap/ng-bootstrap` | `20.0.0` | versión más vieja |
| `bootstrap` | `^5.3.8` | versión más vieja |
| Componentes | Standalone (Angular moderno) | Ninguno, todo eager en `app.module.ts` |
| SSR | No usa Angular Universal | Sí (`server.ts`, `@nguniversal/*`) |

**La brecha de versión (16 → 21) y el modelo de componentes (eager → standalone) siguen siendo lo primero que resolver antes de mezclar `panel_admin/` con `proforma/`.** Es una decisión de `delivery-architect`, no algo que se resuelva copiando archivos: opciones típicas son migrar `proforma/` a Angular 21+, extraer solo SCSS/tokens visuales y reconstruir componentes a mano en Angular 16, o mantener `panel_admin/` como app separada (ej. panel interno) sin fusionar el código con `proforma/`.

## Estructura real de `panel_admin/src/app/`

Verificado por Glob, no por la doc de venta (que menciona una carpeta `shared/` que **no existe** en este checkout — ver nota abajo):

```
panel_admin/src/app/
├── advance-table/       # página de ejemplo: tabla avanzada
├── authentication/       # signin, signup, forgot, reset, page404, page500
├── config/               # config.service.ts — tema (light/dark, color, sidebar)
├── core/
│   ├── guard/              # auth.guard.ts, module-import.guard.ts
│   ├── interceptor/         # error.interceptor.ts, jwt.interceptor.ts
│   ├── models/               # user.ts, config.interface.ts
│   └── service/               # auth.service.ts, storage.service.ts, direction.service.ts, language.service.ts, rightsidebar.service.ts
├── dashboard/
│   ├── main/
│   └── dashboard2/
├── extra-pages/
│   └── blank/
├── layout/
│   ├── app-layout/          # auth-layout (login) vs main-layout (resto)
│   ├── footer/
│   ├── header/                # incluye el botón luna/sol light/dark (ThemeService, core/service/theme.service.ts)
│   ├── page-loader/          # spinner (ngx-spinner)
│   └── sidebar/                # menú lateral principal
└── multilevel/               # demo de menú anidado (first1/first2/first3/secondlevel/thirdlevel)
```

**Nota (hecho verificado vs. doc de venta):** `panel_admin_doc/folder-structure.html` describe una carpeta `shared/` para componentes reutilizables entre módulos; en `panel_admin/src/app/` **no existe tal carpeta** en este checkout. No asumir que algo descrito en `panel_admin_doc/*.html` existe realmente sin verificarlo contra `panel_admin/src/`.

## Hecho verificado — el módulo de auth de `panel_admin/` es un demo, no un sistema de roles

`panel_admin/src/app/core/models/user.ts`:
```ts
export class User {
  id!: number;
  username!: string;
  password!: string;
  firstName!: string;
  lastName!: string;
  token!: string;
}
```
Sin campo de rol ni de privilegios.

`panel_admin/src/app/core/guard/auth.guard.ts`:
```ts
canActivate() {
  if (this.authService.currentUserValue) {
    return true;
  }
  this.router.navigate(['/authentication/signin']);
  return false;
}
```
Solo verifica que haya sesión (`currentUserValue`), no rol ni permiso. El login usa `jwt.interceptor.ts` con JWT — distinto del `Token` auth de Django REST que ya usa `proforma/` (`Authorization: Token {token}`, ver `docs/frontend-audit.md` sección 3).

**Consecuencia para cualquier tarea de usuarios/roles/privilegios:** `panel_admin/` aporta layout, guard base y patrón de interceptor, pero el modelo de roles/privilegios, un guard con verificación de permiso real, y la integración con Token auth (no JWT) hay que construirlos — no vienen resueltos por la plantilla. Esto es decisión de `delivery-architect`, no de `delivery-design`.

## Páginas de ejemplo / componentes de UI (`panel_admin_doc/*.html`, verificar contra `panel_admin/src/app/` cuando aplique)

| Categoría | Página de doc | Nota |
|---|---|---|
| Tablas | `bootstrap-table.html` | Tabla HTML + estilos Bootstrap, sin paginación server-side. |
| Tablas | `ngx-datatable.html`, y el ejemplo real en `panel_admin/src/app/advance-table/` | `ngx-datatable` con paginación/sort/filter — alternativa a `angular-datatables` que ya usa `proforma/` hoy (ver `docs/frontend-audit.md` sección 5). Al elegir uno u otro para el listado de usuarios, comparar consistencia con lo existente vs. beneficio del componente nuevo. |
| Formularios | `form-elements.html` | Inputs, selects, checks con estilos de la plantilla. |
| Formularios | `form-validation.html` | Patrones de validación reactiva con mensajes de error estilizados. |
| Formularios | `editors.html` | Editores de texto enriquecido — no aplica a un módulo de usuarios simple. |
| Charts | `echart.html`, `apex.html`, `chartjs.html`, `gauge-chart.html`, `ngx-chart.html` | No aplican a listado/edición de usuarios. |
| Calendario | `calendar.html` | No aplica. |
| Utilidades | `utilities.html` | Clases de spacing/color/tipografía del sistema visual (SCSS). |
| Multinivel | `panel_admin/src/app/multilevel/` | Patrón de menú anidado, útil si el sidebar de usuarios necesita submenús (ej. Usuarios > Roles). |

## Configuración de tema

`panel_admin/src/app/config/config.service.ts` centraliza tema claro/oscuro, color de acento y estado del sidebar en `localStorage`. Si se adopta, tener en cuenta el hallazgo `SEC-01` de `docs/frontend-audit.md` (ya hay PII/token en `localStorage` de `proforma/`).

## Comandos (proyecto Angular independiente, no reemplaza los de `proforma/`)

Desde `panel_admin/`:
- Instalar: `npm install`
- Levantar: `npm start` (alias de `ng serve`)
- Tests: `npm test`
- Build: `npm run build`
- Lint: `npm run lint`
