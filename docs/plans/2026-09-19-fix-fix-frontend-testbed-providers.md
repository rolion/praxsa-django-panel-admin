# Corregir 5 fallas nuevas reveladas tras aplicar el plan de TestBed (proforma)

## Objetivo
Este plan corrige lo que quedó pendiente tras implementar [docs/plans/2026-09-19-fix-frontend-testbed-providers.md](2026-09-19-fix-frontend-testbed-providers.md) (ya implementado y comiteado en `51df558`, rama `claude/frontend-testbed-providers-89ac9a`). Ese plan bajó la suite de `22 FAILED, 6 SUCCESS` a `5 FAILED, 23 SUCCESS` — una mejora real — pero no llegó a los `28 SUCCESS` esperados. Los 5 tests que siguen fallando lo hacen por **causas apiladas no visibles en la investigación original**: como Jasmine se detiene en el primer error de cada test, el plan anterior identificó y resolvió la primera causa de cada spec (`HttpClient`/`ActivatedRoute`/hijos no declarados), pero eso destapó una segunda causa en 3 de los 20 specs tocados, más una discrepancia de aserción preexistente en `AppComponent` que nunca se había visto porque el test ni siquiera llegaba a ejecutarse.

## Alcance
Solo `proforma/`. Se tocan 4 archivos `*.spec.ts` (3 ya tocados por el plan anterior, para completar su configuración de `TestBed`, y 1 — `app.component.spec.ts` — para corregir una aserción que nunca coincidió con el componente real). No se modifica ningún componente, servicio o guard de producción.

## Contexto relevante encontrado
Se corrió `cd proforma && npm install && npx ng test --watch=false --browsers=ChromeHeadless --code-coverage` sobre el resultado del plan anterior. Salida real: `TOTAL: 5 FAILED, 23 SUCCESS`. Detalle de cada falla, con causa raíz confirmada leyendo el componente/template real (no solo el mensaje de error):

**1-2. `AppComponent` — `should have as title 'calculadora13'` y `should render title`** — Fallan con `Expected 'calculadora' to equal 'calculadora13'` y `Expected undefined to contain 'calculadora13 app is running!'`. La causa **no es de `TestBed`**: [app.component.ts:11](../../proforma/src/app/app.component.ts#L11) fija `title = 'calculadora'`. `git log --follow` sobre ese archivo muestra un único commit (`4daf717`, "feat: added proforma form with ng 16") que ya creó el archivo con ese valor — el spec nunca coincidió con el componente real, es boilerplate de Angular CLI sin actualizar (probablemente el proyecto se generó con `ng new calculadora13` y luego se renombró el título del componente sin tocar el test). No hay ninguna otra referencia a `'calculadora13'` en el proyecto: el `<title>` de [index.html](../../proforma/src/index.html) es `"Proforma"` y `"name"` en [package.json](../../proforma/package.json) es `"proforma"`. Antes del plan anterior, estos 3 tests de `AppComponent` fallaban los 3 por `NullInjectorError: No provider for HttpClient!` (causa A), lo que ocultaba esta discrepancia de aserción por completo — Jasmine nunca llegaba a evaluar el `expect`.

**3. `ListProformaComponent should create`** — Falla con `NG0303: Can't bind to 'dtOptions' since it isn't a known property of 'table'`. Causa: [list-proforma.component.html:2](../../proforma/src/app/components/invoiceTable/list-proforma.component.html#L2) usa el atributo `datatable` y el binding `[dtOptions]`, provistos por `DataTablesModule` de `angular-datatables` (importado en producción en `app.module.ts`, no en el `TestBed` de este spec). El plan anterior (paso 7) solo agregó `HttpClientTestingModule`/`RouterTestingModule` porque la investigación original clasificó este componente en el grupo "sin hijos no declarados" — no detectó que el `<table>` usa una propiedad desconocida (`NG0303`), un síntoma distinto al de "elemento hijo no declarado" (`NG0304`) que sí se buscó. `NO_ERRORS_SCHEMA` sí resuelve este caso: es exactamente el tipo de error para el que existe (property binding desconocido en un elemento conocido).

**4. `FormularioComponent should create`** — Falla con `NG0301: Export of name 'ngForm' not found`. Causa: [formulario.component.html:6](../../proforma/src/app/pages/formulario/formulario.component.html#L6) usa `#reportForm="ngForm"`; `ngForm` es el `exportAs` de `NgForm`, provisto por `FormsModule` (importado en producción en `app.module.ts`, no en el `TestBed` de este spec). El plan anterior (paso 15) ya agregó `schemas: [NO_ERRORS_SCHEMA]` a este spec (por el `<app-top-menu>`/`<fa-icon>` no declarados, causa C), pero `NO_ERRORS_SCHEMA` **no** silencia `NG0301`: ese error ocurre al resolver una variable de plantilla local (`#var="exportAs"`) contra directivas registradas, no al reconocer un elemento o atributo desconocido — son dos mecanismos de validación distintos en Angular. El resto del template (`routerLink`, `<fa-icon>`, `[dtOptions]`-like bindings) ya queda cubierto por el `NO_ERRORS_SCHEMA` existente.

**5. `TopMenuComponent should create`** — Falla con `NG0301: Export of name 'ngbCollapse' not found`. Misma causa raíz que el punto anterior: [top-menu.component.html:14](../../proforma/src/app/components/top-menu/top-menu.component.html#L14) usa `#collapse="ngbCollapse"`, el `exportAs` de `NgbCollapseDirective` de `@ng-bootstrap/ng-bootstrap` (agrupado en `NgbModule`, importado en producción en `app.module.ts`). El plan anterior (paso 8) solo agregó `HttpClientTestingModule`/`RouterTestingModule` porque este componente no tenía hijos Angular no declarados (causa C) — el `NG0301` de `ngbCollapse` no forma parte de los patrones A/B/C/D documentados en el plan original. El mismo template también usa `ngbDropdown`/`ngbDropdownToggle`/`ngbDropdownMenu`/`ngbDropdownItem` ([top-menu.component.html:29-35](../../proforma/src/app/components/top-menu/top-menu.component.html#L29)), también provistos por `NgbModule`; importar `NgbModule` completo cubre ambos de una vez.

No se investigó nada nuevo en `docs/backend-audit.md`/`docs/frontend-audit.md`/`docs/integration-and-backlog.md` — sigue sin haber nada relevante sobre infraestructura de tests ahí.

## Pasos de implementación

1. `proforma/src/app/app.component.spec.ts` — corregir la aserción, no el componente: cambiar `'calculadora13'` por `'calculadora'` en el test `` `should have as title 'calculadora13'` `` (incluyendo el nombre del test, ya que describe el valor esperado) y el texto esperado en `should render title` de `'calculadora13 app is running!'` a `'calculadora app is running!'`. Justificación: ver "Contexto" — el componente nunca tuvo ese título, el spec estaba mal desde su creación.

2. `proforma/src/app/components/invoiceTable/list-proforma.component.spec.ts` — agregar `schemas: [NO_ERRORS_SCHEMA]` (importar `NO_ERRORS_SCHEMA` de `@angular/core`) al mismo `TestBed.configureTestingModule` que ya tiene `imports: [HttpClientTestingModule, RouterTestingModule]`.

3. `proforma/src/app/pages/formulario/formulario.component.spec.ts` — agregar `FormsModule` (de `@angular/forms`) a la lista `imports` existente, junto a `HttpClientTestingModule`.

4. `proforma/src/app/components/top-menu/top-menu.component.spec.ts` — agregar `NgbModule` (de `@ng-bootstrap/ng-bootstrap`) a la lista `imports` existente, junto a `HttpClientTestingModule`/`RouterTestingModule`.

**Recomendación de orden**: aplicar los 4 pasos (son independientes entre sí) y correr `ng test --watch=false --browsers=ChromeHeadless` una vez al final — a diferencia del plan original, acá ya se investigó cada causa leyendo el componente/template completo (no solo el primer error), así que no se espera una tercera causa apilada. Aun así, confirmar con la suite completa antes de dar el fix por cerrado.

## Pruebas para validar la solución
Igual que el plan anterior, no hay comportamiento nuevo ni casos de prueba nuevos que escribir — la validación es que los 5 tests que hoy fallan (tras aplicar el plan original) pasen a estar en verde, sin relajar sus aserciones más allá de lo descrito en el paso 1:

| Test | Qué corrige este paso |
|---|---|
| `AppComponent should have as title 'calculadora13'` (paso 1) | La aserción pasa a verificar el título real del componente (`'calculadora'`) en vez de un valor que nunca existió. |
| `AppComponent should render title` (paso 1) | Ídem, sobre el texto renderizado. |
| `ListProformaComponent should create` (paso 2) | El `TestBed` deja de fallar por el binding `[dtOptions]` no reconocido. |
| `FormularioComponent should create` (paso 3) | El `TestBed` deja de fallar por el `exportAs="ngForm"` no resuelto. |
| `TopMenuComponent should create` (paso 4) | El `TestBed` deja de fallar por el `exportAs="ngbCollapse"` no resuelto. |

Validación: correr `cd proforma && npx ng test --watch=false --browsers=ChromeHeadless` y confirmar `TOTAL: 28 SUCCESS, 0 FAILED` (mismo criterio de éxito que el plan original, con la misma salvedad sobre `auth.guard.spec.ts` si esa rama ya está mergeada).

## Riesgos y complicaciones de arquitectura
- **Ninguno de producción**: los pasos 2-4 son configuración de `TestBed` (mismo patrón que el plan anterior). El paso 1 solo edita aserciones de test para que coincidan con el comportamiento real y ya documentado de `AppComponent` — no cambia `app.component.ts` ni ningún otro archivo de producción.
- **Alternativa descartada para el paso 1**: cambiar `app.component.ts` para que `title = 'calculadora13'` en vez de ajustar el test. Se descarta porque no hay evidencia de que `'calculadora13'` sea el título correcto en ningún lugar del proyecto (ni `index.html`, ni `package.json`, ni el propio commit que creó el componente) — cambiar el título cambiaría comportamiento visible de la app sin que nada lo pida, mientras que el spec es boilerplate de scaffolding nunca actualizado. Si el equipo de producto sí quiere `'calculadora13'` como título visible, eso es una decisión de negocio nueva y aparte, no una corrección de test.
- **`NgbModule` completo en vez de un módulo más chico**: `@ng-bootstrap/ng-bootstrap` no expone un `NgbCollapseModule` standalone separado en la versión usada por este proyecto (`app.module.ts` ya importa el `NgbModule` agregador para todo el árbol), así que se usa el mismo import que producción en vez de buscar un submódulo más granular — consistente con el resto de specs de este mismo esfuerzo, que ya usan `NO_ERRORS_SCHEMA`/imports "amplios" en vez de mocks quirúrgicos por componente.

## Dependencias nuevas
Ninguna. `NO_ERRORS_SCHEMA` (`@angular/core`), `FormsModule` (`@angular/forms`) y `NgbModule` (`@ng-bootstrap/ng-bootstrap`) ya son dependencias existentes del proyecto, usadas en producción en `app.module.ts`.

## Fuera de alcance / preguntas abiertas
- Si en el futuro se decide que `AppComponent` sí debería mostrar `'calculadora13'` como título (en vez de `'calculadora'`), eso es un cambio de producto/UX que requeriría su propio plan — no se investigó ese ángulo acá, solo se confirmó que el valor actual del componente (`'calculadora'`) es intencional y estable desde su creación.
- No se re-investigó si, más allá de crearse sin error, `ListProformaComponent`/`FormularioComponent`/`TopMenuComponent` deberían verificar comportamiento real (que la tabla de datatables reciba los datos esperados, que el formulario reactivo valide correctamente, que el collapse del menú funcione) — igual que en el plan original, eso sería cobertura nueva, no corrección de la existente.
