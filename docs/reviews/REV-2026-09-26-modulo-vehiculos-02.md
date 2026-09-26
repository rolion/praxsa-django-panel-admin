# REV-2026-09-26-modulo-vehiculos-02: Faltan los specs Angular de `models-create`/`models-edit`/`models-view` definidos en el plan

**Status:** Open
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-09-26-modulo-vehiculos.md (v2)
**Suggested owner:** delivery-engineer

## Description

El plan (`## Test strategy`, sección Frontend) define explícitamente casos de test para `models-create`/`models-edit` ("formulario inválido sin marca seleccionada, envío con y sin imagen, reemplazo de imagen dispara el nuevo `FormData`") y para `models-view` ("modal 'Agregar item' en sus dos modos... validación de los campos numéricos antes de confirmar"). Ninguno de los tres componentes tiene un archivo `.spec.ts`. El propio `delivery-engineer` lo dejó explícitamente registrado como deuda técnica en `## Implementación` del TASK, así que no es un hallazgo oculto — pero sigue siendo una brecha real contra lo que el plan aprobado se comprometió a probar, y es precisamente la superficie más compleja del módulo (formularios multi-campo + `FormData` + lógica de dos modos en el modal de asociación), la misma zona donde apareció el bug crítico de REV-01. Un test de `model-create.component` que hiciera `expect(formData.get('is_active'))` o que inspeccionara la respuesta esperada de creación no habría atrapado REV-01 tampoco (es un problema de contrato del backend), pero un test de `models-view` sobre el modo "crear nuevo item" sí hubiera sido la oportunidad más directa de ejercitar el flujo de creación con `FormData` real contra `HttpTestingController` y notar la ausencia de manejo de `is_active`.

## Expected behavior

Según el plan, la suite de tests Angular debería cubrir los 3 componentes de Modelo listados en `## Test strategy`, no solo `vehicles.service`, `image-upload` y las 3 listas.

## Actual behavior

`git diff origin/master...HEAD --stat` no incluye ningún archivo `model-create.component.spec.ts`, `model-edit.component.spec.ts` ni `model-view.component.spec.ts`. Confirmado también corriendo `ng test --watch=false --browsers=ChromeHeadless` de forma fresca: 69 tests totales (24 nuevos, ninguno de ellos referencia a `ModelCreateComponent`, `ModelEditComponent` ni `ModelViewComponent`).

## Evidence

```
$ git diff --stat origin/master...HEAD | grep -i "model-create\|model-edit\|model-view"
.../vehicles/models/model-create.component.html    |  49 ++
.../vehicles/models/model-create.component.ts       |  50 ++
.../vehicles/models/model-edit.component.html       |  52 ++
.../vehicles/models/model-edit.component.ts         |  74 +++
.../vehicles/models/model-view.component.html       | 142 +++++
.../vehicles/models/model-view.component.ts         | 158 +++++
```
(solo `.html`/`.ts` de implementación, sin `.spec.ts` correspondiente — a diferencia de `brands-list`, `parts-list`, `models-list`, `image-upload` y `vehicles.service`, que sí tienen su spec en el mismo diff).
