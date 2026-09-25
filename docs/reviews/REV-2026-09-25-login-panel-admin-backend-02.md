# REV-2026-09-25-login-panel-admin-backend-02: Fix de `app.component.spec.ts` fuera del alcance declarado en `Files/components affected`

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-09-25-login-panel-admin-backend.md (v1)
**Suggested owner:** delivery-engineer (informativo — no requiere acción de seguimiento)

## Description

`delivery-engineer` modificó `panel_admin/src/app/app.component.spec.ts`, un archivo que no aparece en la sección `Files/components affected` del plan. El propio TASK (`## Implementación`) lo documenta explícitamente como "fix incidental" necesario para poder ejecutar `ng test`.

## Expected behavior

Por regla general del flujo (`delivery-review`, paso 4: "Alcance: ¿el diff toca archivos que el plan no mencionaba? Es un hallazgo aunque el cambio en sí parezca razonable"), cualquier archivo tocado fuera de lo declarado en el plan debe señalarse como hallazgo, incluso si está justificado.

## Actual behavior

Se verificó de forma independiente (no solo se aceptó la afirmación del TASK) que el fix es necesario y correcto: se creó un worktree temporal en `origin/master`, se corrió `ng test` sin el fix → falla de compilación total (`TS2339: Property 'title' does not exist on type 'AppComponent'`, 0 tests ejecutados). Sin este archivo corregido, ni siquiera los tests que el propio plan pedía escribir (`auth.service.spec.ts`, `signin.component.spec.ts`, `header.component.spec.ts`) se podían ejecutar ni en `origin/master` ni en esta rama. El cambio es mínimo (quita 2 tests obsoletos que ya no aplican al `AppComponent` real, arregla el `TestBed` para un componente standalone) y no introduce ningún riesgo.

## Evidence

```
# origin/master, sin el fix:
X [ERROR] TS2339: Property 'title' does not exist on type 'AppComponent'. [plugin angular-compiler]
    src/app/app.component.spec.ts:24:15:
      24 │     expect(app.title).toEqual('oreva');

# origin/master, con el mismo fix aplicado temporalmente (solo para esta verificación, no comiteado ahí):
TOTAL: 17 FAILED, 6 SUCCESS

# Esta rama (task/TASK-login-panel-admin-backend), con el fix ya comiteado:
TOTAL: 15 FAILED, 20 SUCCESS
```

Los 17 fallos de `origin/master` incluyen los mismos 15 que siguen fallando en esta rama (deuda técnica preexistente de la plantilla, no tocada por este cambio) **más** `SigninComponent` y `HeaderComponent`, que este PR corrige como parte de su propio alcance. No hay regresión; el fix incidental es correcto y necesario. Se documenta como hallazgo de bajo impacto solo por disciplina de alcance (el archivo no estaba listado en el plan), no porque requiera revertirse o corregirse.
