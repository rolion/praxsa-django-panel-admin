# ADR-003: Reducir el PII persistido en localStorage a token + name; el resto solo en memoria de sesión

**Estado:** Propuesto
**Task relacionado:** TASK-004
**Fecha:** 2026-09-21

## Contexto

`docs/tasks/TASK-004.md` (investigación) confirmó que `AutheticationService.login()` persiste seis claves en `localStorage` en texto plano — `token`, `name`, `lastname`, `phone_number`, `email`, `ci_nit` ([authetication.service.ts:47-52](proforma/src/app/service/pybackend/authentication/authetication.service.ts:47)) — y que `getUser()` las reconstruye leyendo `localStorage` en cada llamada, sin ningún estado en memoria real.

De esos seis campos, los consumidores reales son:
- `token`: usado por `AuthGuard` ([auth.guard.ts:11-14](proforma/src/app/guards/auth.guard.ts:11)) y por `AuthInterceptor` (adjunta `Authorization` a cada petición) — es el único campo estrictamente necesario para que la sesión funcione.
- `name`: mostrado en el saludo del `top-menu` ([top-menu.component.html:39](proforma/src/app/components/top-menu/top-menu.component.html:39)).
- `name` + `lastname` + `email` + `phone_number`: usados para prellenar el formulario de contacto al crear una proforma ([ng-modal-content.component.ts:57-83](proforma/src/app/components/ng-modal-content/ng-modal-content.component.ts:57)).
- `ci_nit`: **confirmado código muerto** — se guarda pero no se usa para prellenar ni siquiera el campo C.I. del propio formulario que lo pediría (`ng-modal-content.component.ts` inicializa `person.name/email/phonenumber/placa` desde `currentUser`, pero nunca `person.ci`).

A pedido explícito del usuario, se verificó si `name`/`email`/`phone_number` llegan realmente a la proforma creada: sí — `generateProforma()` ([ng-modal-content.component.ts:96-106](proforma/src/app/components/ng-modal-content/ng-modal-content.component.ts:96)) los copia a `this.invoice`, que se envía por `POST /product/invoice`. Pero **es un formulario editable y obligatorio** (`ng-modal-content.component.html:28-93`, campos `required` con validación `ngForm`, botón deshabilitado hasta que el formulario sea válido) — el usuario siempre pasa por esa pantalla y puede corregir cualquier valor. Esto acota el impacto real de reducir la persistencia: no rompe la creación de la proforma, solo hace que el formulario aparezca vacío en vez de prellenado tras un refresh de página.

No existe hoy ningún endpoint de perfil de usuario en el backend (`GET /product/...`) al que recurrir como fuente alternativa — los únicos datos de usuario que el backend expone son los que devuelve `POST /product/api-token-auth/` en el momento del login.

Restricción relevante de `docs/CLAUDE.md`: "antes de cambios que afecten varios archivos, proponer un plan y esperar confirmación" — este ADR define el diseño; la lista concreta de archivos a tocar queda para `delivery-plan`.

## Decisión

Reducir lo persistido en `localStorage` a **`token` + `name`** únicamente. El resto de los datos de sesión (`lastname`, `email`, `phone_number`) vive **solo en memoria**, durante la vida de la pestaña/sesión del SPA — se pierde en un refresh de página o al cerrar la pestaña, igual que si el usuario nunca hubiera hecho login (deberá volver a autenticarse o simplemente re-tipear esos campos en el formulario si aparece). `ci_nit` se deja de guardar por completo (no se usa en ningún lado).

Mecanismo concreto (para que `delivery-plan` lo desarrolle en pasos):

1. `login()` sigue construyendo el `User` completo desde la respuesta del backend y lo sigue publicando en `userLoginSource.next(user)` (ya lo hace hoy) — esa es la única fuente de verdad en memoria de ahora en más. Pero solo llama `this.local.saveData(...)` para `token` y `name`.
2. `getUser()` deja de reconstruir el usuario leyendo `localStorage` en cada llamada. Pasa a devolver `this.userLoginSource.value` (el valor actual y sincrónico del `BehaviorSubject`, que ya existe) — así todos los consumidores que hoy llaman `getUser()` directamente (`AuthGuard`, `ng-modal-content`, `lista`, `proforma`, `create-user`, `login-page`) siguen funcionando igual dentro de la misma sesión de SPA, sin tener que migrarlos a suscribirse al observable.
3. Al arrancar la app (constructor de `AutheticationService`), se necesita sembrar el `BehaviorSubject` inicial a partir de lo que sí sobrevive a un reload: un método separado (p. ej. `restoreMinimalSession()`) que arma un `User` parcial solo con `token`+`name` de `localStorage` (el resto queda `''`) — esto reemplaza el uso actual de `getUser()` para ese propósito específico.
4. `logout()` limpia `token` y `name` de `localStorage` y publica `null`. (El fix de TASK-003 — agregar `removeData('email')` — deja de tener un valor real una vez aplicado este ADR, porque `email` nunca se vuelve a guardar; no genera conflicto porque remover una clave inexistente es un no-op, así que no hace falta revertir TASK-003 si ya se aplicó antes.)
5. En `ng-modal-content.component.ts`, al concatenar `currentUser.name`/`currentUser.lastname` para `person.name` (líneas 62 y 77), verificar que un `lastname` vacío (tras un reload) no deje un espacio final visible feo — detalle menor de implementación, no de diseño.

## Alternativas consideradas

- **Agregar un endpoint de perfil en el backend (`GET /product/me`, protegido por token)** y que el frontend lo consulte al arrancar en vez de depender de `localStorage`: preserva el autocompletado incluso tras un refresh, sin persistir PII en absoluto. Se descarta **por ahora** porque, una vez confirmado que el formulario de `ng-modal-content` es editable y obligatorio (no un envío silencioso), el costo real de no tenerlo es bajo (volver a tipear 3 campos tras un refresh) — agregar un endpoint nuevo, su serializer, y refactorizar el arranque del frontend a una llamada asíncrona es una inversión mayor de la que el problema real justifica hoy (sobreingeniería relativa al beneficio). Si en el futuro se agregan más lugares que necesiten el perfil completo de forma confiable entre sesiones, vale la pena reabrir esta alternativa como ADR separado.
- **No tocar nada (mantener las 6 claves persistidas)**: descartada — no resuelve el hallazgo de seguridad (SEC-01) ni el pedido explícito del backlog.
- **`sessionStorage` en vez de `localStorage`**: se evaluó y se descarta explícitamente — `sessionStorage` sobrevive a un refresh (mejor UX que la opción elegida) pero es igual de legible por un script inyectado vía XSS que `localStorage`; no mitiga la amenaza real que describe SEC-01 (fuga de PII ante XSS), solo reduce la ventana de exposición ante un dispositivo compartido/robado, que es una amenaza distinta a la documentada. No resuelve el problema que este ADR busca resolver.

## Estrategia de rollback / mitigación

Es un cambio de lógica de sesión que toca múltiples componentes (`AutheticationService` y sus consumidores), así que aplica una estrategia explícita:

- **Riesgo principal**: cambiar `getUser()` de "reconstruye desde `localStorage`" a "lee del `BehaviorSubject`" puede introducir una fuente de desincronización si algún caso borde no actualiza `userLoginSource` correctamente (p. ej. dos pestañas abiertas: hoy, gracias a que `getUser()` relee `localStorage` en cada llamada, un login en una pestaña se reflejaría en la otra si esta hace una navegación que vuelva a llamar `getUser()`; con el cambio, la segunda pestaña no se entera hasta que recargue, porque su `BehaviorSubject` en memoria no se actualiza entre pestañas). Este es un cambio de comportamiento real, no solo una optimización — debe documentarse y, si se considera inaceptable, se puede mitigar con un listener de `storage` event (cambios de `localStorage` en otra pestaña), aunque eso agregaría complejidad no pedida hoy.
- **Mitigación previa al despliegue**: `delivery-plan`/`delivery-engineer` deben escribir tests de `AutheticationService` (hoy inexistentes) que cubran: login persiste solo `token`+`name`; `getUser()` devuelve el usuario completo inmediatamente después de un `login()` exitoso; tras un "reload" simulado (nueva instancia del servicio), `getUser()` devuelve solo `token`+`name` con el resto vacío; `logout()` limpia ambas claves y publica `null`. Verificar manualmente en el navegador: crear una proforma sin refrescar (debe prellenar todo) y crear una proforma después de un refresh (debe pedir los datos de nuevo, sin romper el envío).
- **Rollback**: cambio de código puro en el frontend, sin migraciones ni cambios de datos en el backend — `git revert` del commit correspondiente restaura el comportamiento anterior de inmediato. No hay ventana de incompatibilidad con el backend (el contrato de `POST /product/invoice` no cambia).

## Consecuencias

- **Más fácil**: se reduce la superficie real de PII expuesta ante un XSS a `token` + `name` (de seis campos a dos) sin agregar infraestructura nueva ni tocar el backend. `getUser()` deja de recalcular el usuario en cada llamada leyendo `localStorage` — pasa a ser una lectura en memoria, más barata y con una única fuente de verdad (`userLoginSource`) en vez de dos representaciones potencialmente desincronizadas (el `BehaviorSubject` y lo reconstruido de `localStorage`).
- **Más difícil**: el autocompletado de contacto en `ng-modal-content` deja de sobrevivir a un refresh de página — fricción menor aceptada conscientemente, respaldada por el hecho verificado de que el formulario es de todas formas editable y obligatorio. Sesiones abiertas en múltiples pestañas dejan de sincronizarse automáticamente entre sí (ver riesgo arriba) — deuda de UX aceptada, no de seguridad.
- **Deuda técnica aceptada conscientemente**: si en el futuro el negocio pide que el autocompletado sobreviva reloads de forma confiable, la solución correcta es el endpoint de perfil descartado en este ADR — no volver a ampliar lo persistido en `localStorage`.
- **No resuelto por este ADR**: la migración del token a cookie `httpOnly`/`secure` (paso 3 del backlog #6) sigue fuera de alcance, tal como ya lo marcaba la investigación — el `token` sigue en `localStorage`, solo se redujo el PII que lo acompaña.
