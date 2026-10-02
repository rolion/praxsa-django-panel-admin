# PLAN-2026-10-02-panel-admin-vulnerabilidades-npm (v1)

**Task:** TASK-panel-admin-vulnerabilidades-npm
**DDRs relacionados:** Ninguno
**ADRs relacionados:** Ninguno

## Objective
Eliminar las vulnerabilidades que reporta `npm audit` en `panel_admin/` retirando dependencias sin uso y actualizando/forzando las que sí se usan, dejando `npm ci` y `ng build` funcionando igual que hoy. Meta: `npm audit` en 0 para producción (`--omit=dev`) y el menor número posible en total.

## Context
Ver `docs/tasks/TASK-panel-admin-vulnerabilidades-npm.md`. Línea base: 81 vulnerabilidades (3 en runtime: `xlsx`, `echarts`, `lodash-es`); `npm ci` + `ng build` OK.

## Current behavior
- `panel_admin/package.json:67` declara `xlsx@^0.18.5` (sin fix en npm, sin imports en `src`); `:49` `echarts@~6.0.0` y `:57` `ngx-echarts@^21.0.0` (sin imports en `src`).
- `panel_admin/package.json:79-80` declara `@types/ckeditor__ckeditor5-build-classic` y `@types/ckeditor__ckeditor5-watchdog`, que arrastran `ckeditor5@41.4.2` y ~60 paquetes `@ckeditor/*` vulnerables (más `turndown@6`/`jsdom`).
- `package-lock.json` fija `@angular/cli@21.0.6` y `piscina@5.2.0` (dependencia **exacta** de `@angular/build@21.2.24`, verificado con `npm view @angular/build@21.2.24 dependencies.piscina` → `5.2.0`).
- `lodash-es@4.17.21` en lock; `ng2-charts@8.0.0` lo pide como `^4.17.15`, así que acepta `4.18.1` (última publicada).
- `panel_admin/angular.json:31,42` lista `echarts` y `@ckeditor/ckeditor5-build-classic` en `allowedCommonJsDependencies`.
- `.npmrc` con `legacy-peer-deps=true`; `Dockerfile.v2:44-50` hace `npm ci --no-audit` y build de producción.

## Expected behavior
- `package.json` sin `xlsx`, `echarts`, `ngx-echarts` ni los dos `@types/ckeditor__*`.
- Lock con `@angular/cli` ≥ 21.2.24 (y `@angular-devkit/*`, `@schematics/angular` resueltos en consecuencia), `lodash-es` 4.18.x, `picomatch`/`ajv` anidados corregidos por la actualización del CLI, `piscina` ≥ 5.3.2 vía `overrides`.
- `npm ci`, `ng build` (dev y producción como en el Dockerfile) y `ng test` sin regresiones respecto a la línea base; las pantallas con gráficas (dashboard) siguen renderizando.

## Architecture considerations
- **Contrato API / backend:** sin impacto; solo manifiestos del frontend `panel_admin/`. No requiere coordinar despliegue con `praxsa_manager/`.
- **Datos, dinero, permisos:** no aplica.
- **Rendimiento:** retirar `xlsx`/`echarts`/`ckeditor` no afecta el bundle actual (no se importan); el bundle no debería crecer.
- **Acoplamiento / riesgo principal:** (a) `overrides` de `piscina` fuerza una versión menor (5.2.0 → 5.3.2) que `@angular/build` pinea exacta; es un parche mismo-major, se verifica con build; (b) retirar paquetes "sin uso" — se verifica por grep ampliado (templates, `angular.json`, `scripts`, imports dinámicos) antes de quitar.
- **Qué NO se hace:** no se ejecuta `npm audit fix --force` (propone downgrade de `@angular/build` a 19.x) ni se sube Angular a 22 (cambio mayor fuera de alcance). No se sube `ng2-charts` a 11 (cambio mayor; solo se refresca `lodash-es` en el lock).
- **`xlsx`:** al no usarse se retira, lo que resuelve la vulnerabilidad sin depender de la distribución fuera de npm. Si algún día se necesita exportar Excel, deberá decidirse entonces (fuera de alcance).

## Proposed solution
1. Confirmar que los paquetes a retirar no se usan (grep en `src`, `angular.json`, `*.html`, `*.scss`, imports dinámicos).
2. Desinstalar con `npm uninstall xlsx echarts ngx-echarts @types/ckeditor__ckeditor5-build-classic @types/ckeditor__ckeditor5-watchdog` y limpiar las entradas muertas de `allowedCommonJsDependencies` en `angular.json`.
3. Subir `@angular/cli` a `~21.2.24` (y alinear `@angular/build` con `^21.2.24`) en `package.json` y regenerar el lock.
4. Añadir `"overrides": { "piscina": "^5.3.2" }` en `package.json`.
5. Refrescar `lodash-es` (`npm update lodash-es`) y otros transitivos moderados que se resuelvan sin cambio de major (`npm audit fix` **sin** `--force`, revisando el diff del lock).
6. Re-auditar y documentar lo que quede (con severidad y motivo) en la sección Implementación del TASK.

## Files/components affected
**Frontend (`panel_admin/`):** `package.json`, `package-lock.json`, `angular.json` (solo `allowedCommonJsDependencies`).
**Backend:** ninguno.
**Docs:** `docs/tasks/TASK-panel-admin-vulnerabilidades-npm.md`.

## Implementation steps
1. Grep ampliado de uso de `xlsx`, `echarts`, `ngx-echarts`, `ckeditor` (todos los tipos de archivo bajo `src/` y `angular.json`). Si aparece algún uso real, parar y replantear ese paquete (volver al plan).
2. Ejecutar `ng test --watch=false --browsers=ChromeHeadless` **antes** de cambiar nada para fijar la línea base de specs (66 archivos); si Chrome no está disponible, registrarlo y usar solo build como criterio.
3. Retirar los 5 paquetes; limpiar `angular.json`; `npm ci` limpio + `ng build`.
4. Actualizar `@angular/cli`/`@angular/build`; añadir `overrides`; regenerar lock; `npm ci` + `ng build --configuration production --base-href /panel/` (mismo comando que `Dockerfile.v2:50`).
5. Refrescar `lodash-es` y aplicar `npm audit fix` sin `--force`; inspeccionar `git diff package-lock.json` por cambios de major inesperados.
6. `npm audit` y `npm audit --omit=dev`; registrar resultado final y vulnerabilidades remanentes.
7. `ng lint` y `ng test` de nuevo y comparar con la línea base.
8. Humo funcional: levantar `ng serve`, abrir login y dashboard (gráficas `ng2-charts` y `apexcharts`), revisar consola sin errores nuevos.
9. Si es posible en la máquina, validar `docker build -f Dockerfile.v2 --target panel` (o equivalente) para confirmar que `npm ci` bajo `.npmrc` funciona en Node 22-alpine.

## Test strategy
- **Unitario:** no se escriben tests nuevos: no cambia lógica de negocio ni código de aplicación. Se usa la suite existente (`ng test`, 66 specs) como detector de regresiones, comparando contra la línea base del paso 2.
- **Integración / build:** `npm ci`, `ng build` dev y producción, `ng lint`, `npm audit` / `npm audit --omit=dev`.
- **E2E (Playwright): NO corresponde.** El cambio no toca flujos de usuario, navegación ni formularios; es mantenimiento de dependencias, y Playwright no está instalado. El riesgo de regresión visual se cubre con el humo funcional manual del paso 8 (login + dashboard).

## Acceptance criteria
- `npm ci` termina OK con `.npmrc` actual y `ng build --configuration production --base-href /panel/` termina OK.
- `npm audit --omit=dev` reporta **0** vulnerabilidades.
- `npm audit` total baja de 81 a una cifra documentada; ninguna `critical` ni `high` queda sin justificación escrita (si `piscina`/toolchain no se puede corregir, se explica por qué).
- `package.json` sin `xlsx`, `echarts`, `ngx-echarts`, `@types/ckeditor__*`; sin referencias muertas en `angular.json`.
- `ng test` y `ng lint` no empeoran frente a la línea base.
- Dashboard y login cargan sin errores nuevos en consola.
- No se usa `npm audit fix --force` ni cambios de major de Angular/`ng2-charts`.

## Risks
- `overrides` de `piscina` sobre un pin exacto de `@angular/build`: podría fallar en build → mitigación: probar build dev y producción; si falla, dejar documentada la `critical` remanente (herramienta de build, no llega al bundle) y reportar al usuario.
- Un uso indirecto de los paquetes retirados no detectado por grep → mitigación: paso 1 ampliado y build/tests; revertir ese paquete en el lock si aparece.
- Actualizar el CLI cambia mensajes/optimizaciones del build → mitigación: comparar tamaño de bundle y avisos con la línea base.
- Sin cobertura de pruebas funcionales automáticas: la verificación de "funcionamiento no afectado" depende de specs + humo manual.
- Mitigación de rollback: todo el cambio vive en `package.json`, `package-lock.json` y `angular.json`; `git revert` del commit restaura el estado anterior.

## Out of scope
- Subir Angular a 22 o `ng2-charts` a 11.
- Vulnerabilidades de `proforma/` (podrían ser análogas; se sugiere un task aparte).
- Quitar `--no-audit` del Dockerfile o añadir `npm audit` a CI.
- Reemplazo de `xlsx` por otra librería (hoy no se usa).
- Pregunta abierta: ¿se quiere un task de seguimiento para `proforma/` y para añadir `npm audit` al pipeline?

## Dependencias nuevas
Ninguna. Solo se retiran paquetes y se actualizan versiones menores/patch de herramientas ya instaladas.
