# Corregir auth.guard.spec.ts: falta HttpClientTestingModule

## Objetivo
Corregir una falla introducida por [docs/plans/2026-09-19-auth-guard-refactor.md](2026-09-19-auth-guard-refactor.md): los dos tests de `AuthGuard` fallan al ejecutarse porque el `TestBed` no provee `HttpClient`, dependencia transitiva de `AutheticationService`.

## Alcance
Solo `proforma/src/app/guards/auth.guard.spec.ts`. No se toca `auth.guard.ts` (el guard en sí funciona correctamente; el problema es la configuración del test).

## Contexto relevante encontrado
Al correr `ng test --watch=false --browsers=ChromeHeadless` en la rama `claude/auth-guard-refactor-e3e35b` (verificación de `delivery-publish`): 24 de 30 tests fallan. Para distinguir fallas preexistentes de regresiones, se corrió la misma suite contra `origin/master` en un worktree temporal: ahí ya fallan 22 de 28 tests, todos por `NullInjectorError` de `HttpClient`/`ActivatedRoute` faltantes en distintos componentes (`ListaComponent`, `ProformaComponent`, `FormularioComponent`, `TopMenuComponent`, `AppComponent`, etc.) — un problema de infraestructura de tests preexistente en el proyecto, no relacionado con este plan, y fuera de su alcance.

Las únicas 2 fallas nuevas que aparecen en la rama (no están en `origin/master`) son:

```
AuthGuard usuario autenticado: canActivate devuelve true y no navega FAILED
AuthGuard usuario no autenticado: canActivate devuelve false y redirige a /login FAILED
```

Ambas con el mismo error:

```
NullInjectorError: R3InjectorError(DynamicTestModule)[AuthGuard -> AutheticationService -> HttpClient -> HttpClient]:
  NullInjectorError: No provider for HttpClient!
```

Causa: `auth.guard.spec.ts` importa `RouterTestingModule` en `TestBed.configureTestingModule` pero no `HttpClientTestingModule`. `AutheticationService` inyecta `HttpClient` en su constructor ([authetication.service.ts:27](../../proforma/src/app/service/pybackend/authentication/authetication.service.ts#L27)), y `AuthGuard` inyecta `AutheticationService` ([auth.guard.ts:8](../../proforma/src/app/guards/auth.guard.ts#L8)), así que `TestBed.inject(AuthGuard)` falla al resolver esa cadena sin el provider. `app-http-interceptor.spec.ts` ya resuelve esto mismo importando `HttpClientTestingModule` ([app-http-interceptor.spec.ts:2](../../proforma/src/app/app-http-interceptor.spec.ts#L2)) — mismo patrón a seguir aquí.

## Pasos de implementación
1. En `proforma/src/app/guards/auth.guard.spec.ts`, importar `HttpClientTestingModule` desde `@angular/common/http/testing`.
2. Agregar `HttpClientTestingModule` al array `imports` de `TestBed.configureTestingModule`, junto a `RouterTestingModule`.

No se modifica la lógica de los dos casos de prueba ya escritos (spies sobre `getUser()` y `router.navigate`), solo la configuración del módulo de test.

## Pruebas para validar la solución
Los mismos dos casos ya existentes en `auth.guard.spec.ts`, que deben pasar a estar en verde tras el fix:
1. Usuario autenticado (`getUser()` devuelve un `User`) → `canActivate()` devuelve `true` y `router.navigate` no fue llamado.
2. Usuario no autenticado (`getUser()` devuelve `null`) → `canActivate()` devuelve `false` y `router.navigate` fue llamado con `['/login']`.

Validar corriendo `ng test --watch=false --browsers=ChromeHeadless` desde `proforma/` y confirmando que ambos casos de `AuthGuard` aparecen en `SUCCESS`, y que el conteo total de `FAILED` vuelve a ser el mismo que en `origin/master` (22, todas preexistentes y fuera de alcance).

## Riesgos y complicaciones de arquitectura
Ninguno — cambio acotado a la configuración de un archivo de test, sin impacto en código de producción ni en el contrato entre backend y frontend.

## Dependencias nuevas
Ninguna. `HttpClientTestingModule` ya es parte de `@angular/common` (usado en `app-http-interceptor.spec.ts`).

## Fuera de alcance / preguntas abiertas
- Las 22 fallas preexistentes en `origin/master` (`NullInjectorError` de `HttpClient`/`ActivatedRoute` en `ListaComponent`, `ProformaComponent`, `FormularioComponent`, `TopMenuComponent`, `AppComponent`, `DataService`, etc.) no se corrigen acá — son un problema de infraestructura de tests general y preexistente del proyecto, sin relación con el `AuthGuard`. Ameritan su propio plan si se decide abordarlas.
