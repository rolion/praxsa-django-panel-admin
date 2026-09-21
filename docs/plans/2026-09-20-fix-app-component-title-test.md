# Corregir el test `AppComponent should render title`, que nunca pudo pasar

## Objetivo
Corrección de tercera ronda sobre el mismo esfuerzo de [docs/plans/2026-09-19-fix-frontend-testbed-providers.md](2026-09-19-fix-frontend-testbed-providers.md) y su corrección [docs/plans/2026-09-19-fix-fix-frontend-testbed-providers.md](2026-09-19-fix-fix-frontend-testbed-providers.md) (ya implementada, commit `85ffae7`). Tras aplicar esa corrección la suite bajó a `1 FAILED, 27 SUCCESS`. El único test que sigue fallando, `AppComponent should render title`, no es un problema de `TestBed` ni de texto de aserción — verifica una estructura de DOM (`.content span`) que **nunca existió** en el template real de `AppComponent`.

## Alcance
Solo `proforma/src/app/app.component.spec.ts`. No se toca ningún archivo de producción.

## Contexto relevante encontrado
Se corrió `cd proforma && npx ng test --watch=false --browsers=ChromeHeadless --code-coverage` sobre el resultado de la corrección anterior. Salida real: `TOTAL: 1 FAILED, 27 SUCCESS`.

```
AppComponent should render title FAILED
  Expected undefined to contain 'calculadora app is running!'.
```

`compiled.querySelector('.content span')?.textContent` da `undefined` porque ese selector no matchea nada. [app.component.html](../../proforma/src/app/app.component.html) completo es:

```html
<router-outlet></router-outlet>
```

`git log --oneline -- src/app/app.component.html` muestra un único commit (`4daf717`, el mismo que creó `app.component.ts`) — este template **nunca** tuvo un `<div class="content">` ni un `<span>` con el texto `"{title} app is running!"`. Es el layout por defecto que genera `ng new`, reemplazado por completo por un `<router-outlet>` desde el primer commit de este archivo, porque `AppComponent` en esta app es solo el shell de ruteo — no renderiza el título en ningún lado (confirmado también con `grep` sobre `app.component.ts`/`.html`/`.css`: no hay ninguna referencia a `.content` ni a `Title` de `@angular/platform-browser`).

A diferencia de las dos rondas anteriores, esto no es una causa apilada de configuración de `TestBed` — ninguna cantidad de imports/providers hace que aparezca un elemento que el template no tiene. El test en sí verifica un comportamiento que el componente nunca tuvo.

## Pasos de implementación
1. `proforma/src/app/app.component.spec.ts` — eliminar el caso `it('should render title', ...)` completo (líneas 28-33 en la versión actual del archivo). Se conservan los otros dos tests (`should create the app` y `` should have as title 'calculadora' ``), que sí verifican comportamiento real del componente.

   Justificación: igual que la aserción de texto corregida en la ronda anterior, este es boilerplate de scaffolding de Angular CLI nunca adaptado a esta app — el componente jamás renderizó ese `<span>`, así que no hay una regresión real que este test esté protegiendo. Mantenerlo forzaría a inventar un elemento en el template de producción solo para satisfacer un test, lo cual sería un cambio de comportamiento no pedido por nadie (fuera del alcance declarado en el plan original: "no se modifica ningún componente... de producción").

   **Alternativa descartada**: reescribir el test para que verifique otra cosa que sí exista hoy (p. ej. que `<router-outlet>` se renderiza). Se descarta en este plan porque sería agregar cobertura nueva con una intención de test inventada por quien corrige, no restaurar una aserción rota — decisión de diseño de test que le corresponde al equipo, no a esta corrección mecánica.

## Pruebas para validar la solución
No hay comportamiento nuevo que cubrir; el conteo total de tests baja de 28 a 27 porque se elimina un test que nunca pudo pasar (no se reduce cobertura real: ese test jamás protegió nada, porque su aserción no correspondía al DOM real desde su creación).

| Test | Qué corrige este paso |
|---|---|
| `AppComponent should render title` | Se elimina — verificaba un `<span>` que nunca existió en `app.component.html`. |

Validación: correr `cd proforma && npx ng test --watch=false --browsers=ChromeHeadless` y confirmar `TOTAL: 27 SUCCESS, 0 FAILED`.

## Riesgos y complicaciones de arquitectura
- **Ninguno de producción**: solo se edita el spec, eliminando un caso de test.
- **Reducción visible del conteo de tests** (28 → 27): es intencional y se documenta acá con su motivo; no es una pérdida de cobertura real, ya que la aserción eliminada nunca reflejó el comportamiento del componente.

## Dependencias nuevas
Ninguna.

## Fuera de alcance / preguntas abiertas
- Si el equipo quiere una prueba real de que `AppComponent` renderiza correctamente su shell de ruteo (p. ej. que `<router-outlet>` está presente, o algo relacionado con el título de la pestaña vía el servicio `Title` de Angular), eso es cobertura nueva a diseñar aparte — no se agrega acá porque este esfuerzo se limitó a restaurar tests rotos, no a decidir qué debería probarse de cero.
