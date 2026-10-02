# TASK-panel-admin-vulnerabilidades-npm: Corregir vulnerabilidades de `npm audit` en panel_admin sin romper el build

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** NO
**Rama:** `claude/panel-admin-vulnerabilities-4a1058` (asignada por el entorno)
**Pull Request:** [#69](https://github.com/rolion/praxsa-django-panel-admin/pull/69)

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-02 | (nuevo) → INVESTIGATION | Task creado | delivery-investigate |
| 2026-10-02 | INVESTIGATION → PLANNING | Veredicto NEEDS_PLAN, diseño NO; sin arquitectura requerida | delivery-plan |
| 2026-10-02 | PLANNING → ENGINEERING | Plan v1 escrito (retirar paquetes sin uso, subir CLI, override de piscina, refrescar lock); PR abierto sobre la rama asignada por el entorno | delivery-plan |

## Investigación

### Requerimiento
"Al instalar las dependencias de panel_admin arroja que hay unas vulnerabilidades, revísalas y corrígelas, revisa que el proyecto aún compila y no se ve afectado su funcionamiento."

### Hechos encontrados
Medido con `npm ci` + `npm audit` + `ng build` en este worktree (Node 22.12.0, npm 10.9.0), sin modificar código.

**Línea base**
- `panel_admin/package-lock.json` (lockfileVersion 3) instala limpio con `npm ci` (exit 0) y `npx ng build` termina OK (36 s, salida en `dist/oreva`, ignorada por git). Solo emite avisos CSS `Unmatched selector: %` (ruido preexistente, no es error).
- `npm audit` total: **81** (2 critical, 6 high, 70 moderate, 3 low).
- `npm audit --omit=dev` (lo que llega a producción): **3** (1 moderate, 2 high) → `echarts` (moderate, XSS GHSA-fgmj-fm8m-jvvx), `lodash-es` (high, code injection `_.template` / prototype pollution), `xlsx` (high, prototype pollution GHSA-4r6h-8v6p-xvw6 y ReDoS GHSA-5pgg-2g8v-p4x9; **sin fix publicado en npm**, `fixAvailable: false`, rango `*`).

**Origen de los 81, agrupados**
1. **CKEditor (~63 de los 70 moderate):** ningún `@ckeditor/*` ni `ckeditor5` está en `dependencies`. Entran solo por los devDependencies de tipos `@types/ckeditor__ckeditor5-build-classic@^37.0.4` y `@types/ckeditor__ckeditor5-watchdog@^37.0.3` (`panel_admin/package.json:79-80`), que arrastran `ckeditor5@41.4.2` y todos los paquetes `@ckeditor/ckeditor5-*@41.4.2` (verificado en `package-lock.json`: `ckeditor5@41.4.2` es requerido por `@types/ckeditor__ckeditor5-build-classic`). `npm audit` los marca por XSS en `clipboard`/`html-support` y por `lodash-es`.
2. **Toolchain Angular (dev):** `@angular/cli` (high), `@angular-devkit/{core,architect,schematics}`, `@schematics/angular`, `@modelcontextprotocol/sdk` (high), `pacote` (high), `picomatch@4.0.3` anidado (high), `ajv@8.17.1` anidado (moderate). En el lock, `@angular/cli` está en **21.0.6** (`package.json:77` pide `~21.0.5`) y `@angular/build` en **21.2.24** (`package.json:76` pide `^21.0.5`). Para `@angular/cli` npm reporta `fixAvailable: 21.2.24`, `isSemVerMajor: false`.
3. **`piscina@5.2.0` (critical, RCE por prototype pollution GHSA-67c8-pqhq-4rmx, rango 5.0.0–5.3.1):** es dependencia de `@angular/build@21.2.24` (build-time). npm propone como "fix" `@angular/build@19.2.27` (`isSemVerMajor: true`, es decir un downgrade de major), que no es una vía válida con Angular 21.
4. **Cadena jsdom/`@tootallnate/once`/`http-proxy-agent` (3 low):** `jsdom` entra vía `turndown@6.0.0` (dependencia transitiva, no declarada en `package.json`).
5. `lodash-es@4.17.21` (high) en runtime lo trae `ng2-charts@8.0.0` (`package.json:54`).

**Uso real en el código**
- `xlsx`: declarado en `package.json:67`, **sin ningún import** en `panel_admin/src` (`grep -rniE "xlsx|echarts|ckeditor" src` solo devuelve `src/app/app.config.ts`, que importa `ng2-charts`, no `xlsx`).
- `echarts` y `ngx-echarts`: declarados en `package.json:49,57`; sin imports `.ts` en `src`. `echarts` solo aparece en la lista `allowedCommonJsDependencies` de `panel_admin/angular.json:31`.
- `@ckeditor/ckeditor5-build-classic`: figura en `allowedCommonJsDependencies` (`panel_admin/angular.json:42`) pero no está instalado como dependencia directa ni se importa en `src`.
- Gráficas realmente usadas: `ng2-charts`/`chart.js` en `src/app/app.config.ts:13,38`; `apexcharts`/`ng-apexcharts` en `src/app/dashboard/{dashboard.charts,dashboard2/dashboard2.component,main/main.component}.ts`.

**Entorno de instalación/build**
- `panel_admin/.npmrc` fija `legacy-peer-deps=true`. `Dockerfile.v2:44-50` copia `package.json`, `package-lock.json` y `.npmrc` y corre `npm ci --no-audit --no-fund` y `npx ng build --configuration production --base-href /panel/` (Node 22-alpine). El comentario del Dockerfile dice que sin `.npmrc` `npm ci` falla por peer deps de `angular-datetime-picker`.
- Hay 66 archivos `*.spec.ts` en `panel_admin/src` (no se ejecutaron en esta investigación).

### Hipótesis / supuestos no confirmados
- `xlsx`, `echarts`, `ngx-echarts` y `ng-pick-datetime`/otros paquetes sin import probablemente son restos de la plantilla y se pueden retirar sin efecto; no se verificó que ningún HTML/template, `angular.json` `scripts` o carga dinámica (`import()` con string armado) los use. El grep en `.ts` no encontró nada.
- Que los `@types/ckeditor__*` sean innecesarios (sin código que use CKEditor) es probable pero no se confirmó con `ng build`/tests tras quitarlos.
- No se confirmó si un `overrides` de npm para `piscina` (>5.3.1) es compatible con `@angular/build@21.2.24`; tampoco si existe una versión de `@angular/build` 21.x que ya traiga `piscina` corregido.
- No se confirmó si hay versión corregida de `lodash-es` aplicable (rango afectado `<=4.17.23`) compatible con `ng2-charts@8`, ni si `echarts@6.1.0` (npm lo indica como fix no major) es compatible con `ngx-echarts@21`.
- No se ejecutó la suite `ng test` (requiere Chrome/Karma) ni el servidor de desarrollo; el criterio "no se ve afectado su funcionamiento" hoy solo está respaldado por `ng build` y no por pruebas funcionales.

### Módulos y dependencias relacionadas
Solo frontend `panel_admin/` (Angular 21): `package.json`, `package-lock.json`, `.npmrc`, `angular.json` (listas de dependencias CommonJS permitidas). Impacto de despliegue: `Dockerfile.v2` (stage `panel`). No toca `praxsa_manager/` ni `proforma/`.

### Implementaciones similares existentes
No se encontró un task previo sobre auditoría de dependencias en `docs/tasks/`. (Hipótesis: `proforma/` podría tener vulnerabilidades análogas; está fuera del alcance pedido.)

### Comportamiento actual
La instalación y el build funcionan; `npm audit` reporta 81 vulnerabilidades, de las cuales solo 3 afectan dependencias de runtime y de esas 2 (`xlsx`, `echarts`) no tienen imports en `src`. El resto es toolchain de desarrollo/tipos.

### Restricciones
- `docs/CLAUDE.md` indica que el proyecto no se construyó con buenas prácticas: no asumir nada por nombres de archivo.
- Hay que mantener `legacy-peer-deps=true` (`panel_admin/.npmrc`) para que `npm ci` del Dockerfile siga funcionando.
- `npm audit fix --force` propone downgrades de major (p. ej. `@angular/build@19.2.27`) que no son aceptables con Angular 21.
- `xlsx` en npm no tiene versión corregida (el fix upstream se distribuye fuera de npm).

### Riesgos identificados
- Actualizar `@angular/cli`/`@angular/build` en el lock puede cambiar comportamiento del build (ya hay avisos CSS preexistentes); `ng test` y `ng lint` no se han usado como línea base.
- Un `overrides` para `piscina` o `lodash-es` fuerza versiones no probadas por los mantenedores del paquete padre.
- Quitar dependencias "sin uso" puede romper si hay uso indirecto no detectado por grep (templates, `angular.json`).
- `dist/` no queda versionado, por lo que la verificación de funcionamiento real (navegación, gráficas del dashboard) requiere levantar la app; hoy no hay evidencia automatizada más allá del build.
- El Dockerfile usa `--no-audit`, así que las vulnerabilidades no bloquean el despliegue ni se ven en CI.

### Veredicto de complejidad
**NEEDS_PLAN** — Cambio acotado a manifiestos/lock de un solo paquete frontend, sin decisiones arquitectónicas nuevas ni cambios de modelos, APIs o autenticación de la aplicación. Requiere un plan porque hay varias decisiones por vulnerabilidad (retirar vs actualizar vs `overrides`), una vulnerabilidad sin fix en npm (`xlsx`) y una estrategia de verificación (build, specs, humo funcional) que definir.

### Diseño requerido
**NO** — No hay superficie de UI nueva ni cambios visuales; es mantenimiento de dependencias.

## Diseño
_No aplica_

## Arquitectura
_No aplica según veredicto_

## Plan
[docs/plans/PLAN-2026-10-02-panel-admin-vulnerabilidades-npm.md](../plans/PLAN-2026-10-02-panel-admin-vulnerabilidades-npm.md) (v1)

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
