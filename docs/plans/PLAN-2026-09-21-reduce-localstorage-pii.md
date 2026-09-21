# PLAN-2026-09-21-reduce-localstorage-pii (v1)

**Task:** TASK-004
**ADRs relacionados:** [ADR-003](../adr/ADR-003-reduce-localstorage-pii.md)

## Objective

Reducir el PII persistido en `localStorage` (backlog #6, paso 2, frontend SEC-01) a solo `token` + `name`, moviendo `lastname`/`email`/`phone_number` a memoria de sesión (vía el `BehaviorSubject` ya existente) y dejando de persistir `ci_nit` por completo, sin agregar un endpoint de perfil nuevo en el backend.

## Context

`docs/tasks/TASK-004.md` (investigación + arquitectura) y [ADR-003](../adr/ADR-003-reduce-localstorage-pii.md) documentan el problema y la decisión completos. Resumen relevante:

- `AutheticationService.login()` persiste hoy 6 claves en `localStorage`: `token`, `name`, `lastname`, `phone_number`, `email`, `ci_nit`.
- `getUser()` reconstruye el `User` completo leyendo `localStorage` en cada llamada — no hay estado en memoria real hoy, a pesar de que ya existe un `BehaviorSubject` (`userLoginSource`) actualizado en cada `login()`/`logout()`.
- Verificado a pedido del usuario: `name`/`email`/`phone_number` sí llegan a la proforma creada, pero vía un formulario editable y obligatorio (`ng-modal-content`) — no un envío silencioso. Esto acota el costo real de la reducción a "el formulario aparece vacío tras un refresh" en vez de "se rompe la creación de la proforma".
- `ci_nit` es código muerto confirmado — ni siquiera prellena el campo C.I. del propio formulario que lo pediría.
- Coordinación con TASK-003 (fix de `logout()` para limpiar `email`, TRIVIAL_FIX, vía `delivery-engineer` directo): si TASK-003 se implementa antes que este plan, no genera conflicto — remover una clave que ya no se guarda es un no-op inofensivo. Este plan de todas formas deja `logout()` limpiando explícitamente las 6 claves legacy (ver Implementation steps, paso 4) para cubrir usuarios que ya tenían PII persistido de antes de este cambio.

## Current behavior

- `login()` — [authetication.service.ts:44-58](../../proforma/src/app/service/pybackend/authentication/authetication.service.ts) — guarda las 6 claves con `this.local.saveData(...)` tras un `POST /product/api-token-auth/` exitoso, y publica el `User` completo en `userLoginSource.next(user)`.
- `logout()` — [authetication.service.ts:59-68](../../proforma/src/app/service/pybackend/authentication/authetication.service.ts) — limpia `token`, `name`, `lastname`, `phone_number`, `ci_nit` de `localStorage` (falta `email`, ver TASK-003) y publica `null`.
- `getUser()` — [authetication.service.ts:69-81](../../proforma/src/app/service/pybackend/authentication/authetication.service.ts) — reconstruye el `User` leyendo las 6 claves de `localStorage` en cada llamada, ignorando el valor actual de `userLoginSource`.
- Constructor — [authetication.service.ts:27-33](../../proforma/src/app/service/pybackend/authentication/authetication.service.ts) — siembra `userLoginSource` llamando a `this.getUser()` una vez, al arrancar el servicio.
- Consumidores directos de `getUser()` (no vía suscripción al observable): `AuthGuard` ([auth.guard.ts:12](../../proforma/src/app/guards/auth.guard.ts)), `ng-modal-content.component.ts:58,75`, `lista.component.ts:15`, `proforma.component.ts:38`, `create-user.component.ts:36`, `login-page.component.ts:31`.
- Consumidores vía suscripción a `isUserLoged` (ya en memoria, no requieren cambios): `top-menu.component.ts:22`.

## Expected behavior

- `login()` solo persiste `token` y `name` en `localStorage`. `lastname`/`email`/`phone_number` quedan disponibles en memoria (vía `userLoginSource`) mientras dura la sesión del SPA (sin recargar la página).
- `getUser()` deja de leer `localStorage` en cada llamada — devuelve el valor sincrónico actual de `userLoginSource` (`userLoginSource.value`).
- Al arrancar la app (o tras un refresh), el usuario reconstruido solo tiene `token`+`name`; `lastname`/`email`/`phone_number`/`ci_nit` quedan como cadena vacía hasta el próximo `login()` en esa sesión de navegador.
- `logout()` limpia las 6 claves legacy de `localStorage` (para cubrir a usuarios que ya tenían PII persistido de antes de este cambio) y publica `null`.
- `ci_nit` nunca vuelve a escribirse en `localStorage`.

## Architecture considerations

Resumen de ADR-003 (ver documento completo para alternativas descartadas y rollback):
- **Contrato API**: sin cambios — el backend no se toca, `POST /product/invoice` sigue recibiendo los mismos campos cuando el usuario los completa en el formulario.
- **Riesgo aceptado explícitamente**: sesiones abiertas en varias pestañas dejan de sincronizarse automáticamente entre sí (hoy `getUser()` releía `localStorage` en cada llamada, lo que de facto sincronizaba pestañas al navegar; con el cambio, cada pestaña tiene su propio `BehaviorSubject` en memoria). No se mitiga en este plan — señalado en el ADR como deuda de UX aceptada, no de seguridad.
- **No se agrega infraestructura ni dependencias** — cambio acotado a `AutheticationService` y sus consumidores.

## Proposed solution

1. `AutheticationService.login()`: seguir construyendo el `User` completo y publicándolo en `userLoginSource.next(user)` (sin cambios ahí), pero reducir las llamadas a `this.local.saveData(...)` a solo `token` y `name`.
2. `AutheticationService.getUser()`: cambiar el cuerpo para devolver `this.userLoginSource.value` en vez de reconstruir desde `localStorage`.
3. Agregar un método privado nuevo (p. ej. `restoreMinimalSession()`) que arma un `User` parcial leyendo solo `token`+`name` de `localStorage`, usado **únicamente** en el constructor para sembrar el valor inicial de `userLoginSource` al arrancar la app — reemplaza el uso actual de `getUser()` para ese propósito.
4. `AutheticationService.logout()`: limpiar las 6 claves (`token`, `name`, `lastname`, `phone_number`, `email`, `ci_nit`) — aunque ya no todas se escriban en `login()`, limpiar las 6 cubre a usuarios con sesiones/localStorage de antes de este cambio.
5. `ng-modal-content.component.ts:62,77`: ajustar la concatenación `${this.currentUser.name} ${this.currentUser.lastname}` para no dejar un espacio final visible cuando `lastname` esté vacío (p. ej. `.trim()` sobre el resultado, o construir el string condicionalmente).

## Files/components affected

**Frontend (ningún cambio de backend):**
- `proforma/src/app/service/pybackend/authentication/authetication.service.ts` — `login`, `logout`, `getUser`, constructor.
- `proforma/src/app/service/pybackend/authentication/authetication.service.spec.ts` — reemplazar el test boilerplate (`toBeTruthy`) por los casos reales listados abajo.
- `proforma/src/app/components/ng-modal-content/ng-modal-content.component.ts` — ajuste cosmético de concatenación de nombre.

No se tocan `AuthGuard`, `AuthInterceptor`, `top-menu`, ni ningún otro componente — todos siguen funcionando igual porque consumen `getUser()`/`isUserLoged` por su interfaz pública, no por cómo se implementa internamente.

## Implementation steps

1. Escribir los tests nuevos en `authetication.service.spec.ts` primero, en rojo (describen el comportamiento esperado antes de tocar el servicio) — ver Test strategy.
2. Modificar `login()` para persistir solo `token`+`name`.
3. Agregar `restoreMinimalSession()` (o el nombre que se decida) y usarlo en el constructor en vez de `getUser()`.
4. Modificar `getUser()` para devolver `userLoginSource.value`.
5. Modificar `logout()` para limpiar las 6 claves legacy.
6. Correr los tests del paso 1 y confirmar que pasan en verde.
7. Ajuste cosmético en `ng-modal-content.component.ts` (concatenación de nombre sin espacio final).
8. Verificación manual en navegador: (a) login → crear una proforma sin refrescar la página → el formulario debe aparecer prellenado igual que hoy; (b) login → refrescar la página → abrir el modal de crear proforma → el formulario debe aparecer con nombre completo pero email/teléfono vacíos, editable y enviable igual; (c) confirmar en devtools que `localStorage` solo tiene `token`+`name` tras login; (d) logout → confirmar que `localStorage` queda sin ninguna de las 6 claves.

## Test strategy

Nivel: **Angular `TestBed` + `HttpClientTestingModule`**, mismo patrón que ya usan `authetication.service.spec.ts` y `auth.guard.spec.ts` (que ya tiene tests reales más allá de `toBeTruthy`, útil como referencia de estilo). No hace falta `HttpTestingController` explícito para el login en sí si se opta por invocar el flujo con un mock del `HttpClient`/spy en `http.post`, siguiendo lo que ya exista en el proyecto para simular la respuesta del backend.

Casos concretos:
- `login()` exitoso → `localStorage.getItem('token')` y `localStorage.getItem('name')` tienen valor; `localStorage.getItem('lastname')`, `'email'`, `'phone_number'`, `'ci_nit')` son `null`.
- `login()` exitoso → `getUser()` devuelve inmediatamente un `User` con `email`/`lastname`/`phone_number` poblados (en memoria, vía `userLoginSource`).
- Simular un "reload" (crear una nueva instancia del servicio, p. ej. reconfigurando `TestBed` o llamando al constructor manualmente con `token`+`name` ya en `localStorage` pero sin los demás) → `getUser()` de esa nueva instancia devuelve un `User` con `email`/`lastname`/`phone_number`/`ci_nit` vacíos.
- `logout()` → limpia las 6 claves de `localStorage` (incluyendo las que pudieran haber quedado de una sesión anterior al cambio, simulado seteándolas manualmente antes del test) y `getUser()` devuelve `null` después.
- Regresión: tras `login()`, `localStorage.getItem('ci_nit')` nunca es distinto de `null`.

**¿Corresponde E2E (Playwright)? No.** El cambio es enteramente de manejo de estado en `AutheticationService`, sin tocar el contrato con el backend ni introducir navegación/flujos nuevos. El caso más "end-to-end" (¿sobrevive el autocompletado a un refresh real de página?) se puede verificar con un test de integración de Angular simulando la reconstrucción del servicio desde `localStorage` sin necesidad de un browser real y una recarga real — y de todas formas se verifica una vez a mano en el paso 8 antes de dar el cambio por terminado. Instalar Playwright (no está en `proforma/package.json` hoy) para esto sería desproporcionado.

## Acceptance criteria

- [ ] Tras `login()`, `localStorage` contiene solo `token` y `name` (no `lastname`/`phone_number`/`email`/`ci_nit`).
- [ ] Sin recargar la página, `getUser()` sigue devolviendo el usuario completo (incluido `email`/`phone_number`) inmediatamente después de un login exitoso, y el formulario de `ng-modal-content` se sigue prellenando igual que hoy.
- [ ] Tras un refresh simulado, `getUser()` devuelve un usuario con `token`+`name` pero `email`/`lastname`/`phone_number` vacíos, sin que la app rompa (el formulario de proforma sigue siendo enviable, solo aparece vacío).
- [ ] `logout()` limpia las 6 claves legacy de `localStorage`, incluida `email`.
- [ ] `ci_nit` nunca se escribe en `localStorage`.
- [ ] Todos los tests nuevos y existentes de `proforma/` pasan (`ng test`).
- [ ] Verificación manual completa (paso 8) sin errores de consola nuevos.

## Risks

- **Usuarios ya logueados antes de este despliegue conservan PII legacy en `localStorage`** (`lastname`/`phone_number`/`email`/`ci_nit` de una sesión anterior) hasta que hagan `logout()` explícito — este plan no fuerza un logout global al desplegar. Mitigación parcial: `logout()` limpia las 6 claves, así que el primer logout de cada usuario después del despliegue deja todo limpio; hasta ese momento, el riesgo de seguridad original persiste para esas sesiones ya abiertas. Aceptado como residual, consistente con que este ADR no incluye una migración forzada de sesiones.
- **Desincronización entre pestañas** (ver Architecture considerations) — riesgo de UX aceptado explícitamente en ADR-003, no de seguridad.
- **El helper de simular "reload" en los tests de Angular no es un reload real de navegador** — mitigado por la verificación manual explícita del paso 8 antes de cerrar la implementación.

## Out of scope

- Migrar el token a cookie `httpOnly`/`secure` (paso 3 del backlog #6) — épica separada, ya marcada como fuera de alcance en la investigación original.
- Sincronizar sesión entre pestañas abiertas simultáneamente — no pedido, y agregar un listener de `storage` event sería una ampliación de alcance no solicitada.
- Forzar el logout de sesiones activas al desplegar este cambio (para limpiar PII legacy de inmediato) — pregunta abierta para el usuario si le importa mitigar la ventana residual descrita en Risks; no se implementa salvo que lo pida explícitamente.

## Dependencias nuevas

Ninguna.
