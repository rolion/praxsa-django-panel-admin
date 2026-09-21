# TASK-004: Evaluar reducir el PII persistido en localStorage (backlog #6, paso 2)

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Rama:** `claude/public-endpoints-pii-storage-ff52d6` (compartida con TASK-002, por decisión explícita del usuario — ver historial)
**Pull Request:** https://github.com/rolion/praxsa-django-panel-admin/pull/30 (combinado con TASK-002, por decisión explícita del usuario)

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-09-21 | (nuevo) → INVESTIGATION | Task creado a partir del paso 2 del ítem #6 de docs/integration-and-backlog.md, separado del paso 1 (fix de logout(), TASK-003) por tener naturaleza y complejidad distintas | delivery-investigate |
| 2026-09-21 | INVESTIGATION → PLANNING | Decisión arquitectónica tomada (ADR-003), tras verificar a pedido del usuario que `name`/`email`/`phone_number` se envían con la proforma pero vía un formulario editable/obligatorio (no un envío silencioso): persistir solo `token`+`name` en localStorage; el resto vive en memoria vía el `BehaviorSubject` ya existente, sin agregar endpoint de perfil nuevo | delivery-architect |
| 2026-09-21 | PLANNING → ENGINEERING | Plan v1 escrito (PLAN-2026-09-21-reduce-localstorage-pii.md). Usuario decidió explícitamente reusar la rama existente del worktree en vez de crear `task/TASK-004-...`, y combinar TASK-002+TASK-004 en un único PR (se aparta de la regla de "un PR por task" del skill, por decisión explícita) | delivery-plan |
| 2026-09-21 | ENGINEERING → REVIEW | Implementación completa según el plan v1, commit 963afae empujado al PR #30. Verificado end-to-end en navegador contra un backend real (login → localStorage solo con token+name → refresh → saludo/guard sobreviven, resto del formulario vacío pero editable) | delivery-engineer |
| 2026-09-21 | REVIEW → PUBLISH | Veredicto PASS (sin issues) — `ng test` (34/34, corrida independiente) + `ng build` + confirmación independiente por grep de que ningún otro componente lee los campos removidos. Acceptance criteria del plan verificados con evidencia concreta, sin scope creep | delivery-review |

## Investigación

### Requerimiento

Ejecutar el paso 2 del ítem #6 del backlog (`docs/integration-and-backlog.md:180`, frontend SEC-01): "evaluar reducir el PII persistido en `localStorage` a lo estrictamente necesario para la UI (nombre para saludo, nada más), moviendo el resto a estado en memoria". Es una evaluación, no una implementación directa — el backlog explícitamente no fuerza el resultado.

### Hechos encontrados

- `AutheticationService.login()` persiste seis claves en `localStorage` en texto plano — [authetication.service.ts:47-52](proforma/src/app/service/pybackend/authentication/authetication.service.ts:47): `token`, `name`, `lastname`, `phone_number`, `email`, `ci_nit`.
- `getUser()` ([authetication.service.ts:69-81](proforma/src/app/service/pybackend/authentication/authetication.service.ts:69)) reconstruye el objeto `User` completo leyendo esas mismas claves cada vez que se necesita el usuario actual (incluyendo en el constructor del propio servicio, línea 29, para inicializar el `BehaviorSubject` de sesión) — no hay ningún round-trip al backend para refrescar estos datos; todo sale de `localStorage`.
- **`AuthGuard`** ([guards/auth.guard.ts:11-14](proforma/src/app/guards/auth.guard.ts:11)) solo depende de que `getUser()` devuelva no-null, lo cual a su vez solo depende de la presencia de la clave `token` (`getData('token')` en la condición de `getUser()`, línea 71) — **ninguno de los otros cinco campos (`name`, `lastname`, `phone_number`, `email`, `ci_nit`) es necesario para que el guard funcione**.
- **Consumidores reales de cada campo de `currentUser` más allá del guard**:
  - `name`: usado para el saludo en `top-menu.component.html:39` (`{{currentUser.name}}`) — es el único uso que el backlog ya da por válido de mantener.
  - `name` + `lastname`: usados para precargar `person.name` en el formulario de datos del cliente al crear una proforma — [ng-modal-content.component.ts:62,77](proforma/src/app/components/ng-modal-content/ng-modal-content.component.ts:62).
  - `email`: usado para precargar `person.email` en el mismo formulario — [ng-modal-content.component.ts:63,78](proforma/src/app/components/ng-modal-content/ng-modal-content.component.ts:63).
  - `phone_number`: usado para precargar `person.phonenumber` en el mismo formulario — [ng-modal-content.component.ts:64,79](proforma/src/app/components/ng-modal-content/ng-modal-content.component.ts:64).
  - `ci_nit`: **no se encontró ningún lugar que lea `currentUser.ci_nit`** en el frontend — se guarda en `login()` y se reconstruye en `getUser()`, pero no se usó en ningún componente/template revisado. El único `ci_nit` que sí se muestra en pantalla (`proforma.component.html:35`) viene de la respuesta del backend para una proforma puntual, no de `currentUser`.
- `ng-modal-content.component.ts` es el componente que arma el objeto `Invoice` que finalmente se envía en `POST /product/invoice` al crear una proforma — precargar `name`/`email`/`phone_number` desde `currentUser` es lo que le ahorra al usuario reescribir sus propios datos de contacto en cada proforma nueva.
- `AuthInterceptor` (confirmado en `docs/frontend-audit.md:62`) adjunta el header `Authorization: Token {token}` leyendo `localStorage` directamente en cada petición saliente — depende solo de `token`, no de los demás campos.
- `docs/frontend-audit.md:106-120` (SEC-01) ya documenta este mismo hallazgo y sugiere como solución "mover el token a una cookie `httpOnly`/`secure`... o al menos evitar persistir PII en `localStorage` (mantenerla solo en memoria/estado de la app)" — coincide con el paso 2 del backlog, sin agregar información nueva sobre implementación.
- **Verificado a pedido del usuario: sí, `name`/`email`/`phone_number` se incluyen en la proforma que efectivamente se crea** — `generateProforma()` ([ng-modal-content.component.ts:96-106](proforma/src/app/components/ng-modal-content/ng-modal-content.component.ts:96)) copia `person.name`, `person.email`, `person.phonenumber`, `person.ci`, `person.placa` directo a `this.invoice`, que es lo que `saveProforma()` envía por `POST /product/invoice` ([ng-modal-content.component.ts:108-133](proforma/src/app/components/ng-modal-content/ng-modal-content.component.ts:108)).
- **Pero es un formulario editable y obligatorio, no un envío silencioso**: `ng-modal-content.component.html:28-93` muestra que `name`, `ci`, `phonenumber`, `placa`, `email` son inputs con `required` y validación Angular (`ngModel`/`ngForm`) — el botón "Crear Proforma" está `[disabled]="!personForm.form.valid"`. El usuario **siempre** pasa por esta pantalla y puede corregir cualquier valor antes de enviar; `currentUser` solo pre-llena los campos, no los envía "a ciegas". Esto cambia el impacto real de reducir la persistencia: no rompe la creación de la proforma, solo hace que el formulario aparezca vacío en vez de prellenado (el usuario de todas formas tiene que confirmar/tocar esa pantalla).
- **Confirmado: `ci_nit` no se usa para prellenar ni siquiera este mismo formulario que tiene un campo de C.I.** — `ngOnInit()`/`onLogin()` ([ng-modal-content.component.ts:57-68,72-83](proforma/src/app/components/ng-modal-content/ng-modal-content.component.ts:57)) inicializan `person.name`, `person.email`, `person.phonenumber`, `person.placa` desde `currentUser`, pero **no** `person.ci` — ese campo queda en `''` (el default del constructor) y el usuario siempre lo escribe a mano, sin importar qué haya en `localStorage['ci_nit']`. Esto descarta del todo la hipótesis anterior: `ci_nit` persistido es 100% código muerto para autocompletado, en cualquier formulario del frontend revisado.

### Hipótesis / supuestos no confirmados

- No se confirmó qué pasaría con el autocompletado de `ng-modal-content` si `email`/`phone_number` dejaran de persistirse: la alternativa más directa (pedirlos de nuevo al backend en cada carga de página vía algún endpoint de perfil) **no existe hoy** — no se encontró ningún endpoint `GET /product/...` que devuelva el perfil del usuario autenticado; los únicos datos de usuario que el backend expone son los que vienen en la respuesta de `login` (`api-token-auth/`). Si se decide sacar `email`/`phone_number` de `localStorage`, hoy no hay de dónde más obtenerlos sin pedírselos de nuevo al usuario o sin agregar un endpoint nuevo — esto no se verificó con el usuario, se marca como pregunta abierta.
- No se confirmó si perder el autocompletado de `email`/`phone_number` en `ng-modal-content` (obligando al usuario a reescribirlos en cada proforma) es un costo de UX aceptable para el negocio — atenuado por el hecho verificado de que el usuario de todas formas pasa por un formulario editable obligatorio, no es un flujo que se salte.

### Módulos y dependencias relacionadas

- `proforma/src/app/service/pybackend/authentication/authetication.service.ts` (`login`, `logout`, `getUser`).
- `proforma/src/app/service/local-storage/local-storage.service.ts` (wrapper genérico de `localStorage`).
- `proforma/src/app/guards/auth.guard.ts` (consumidor de `getUser()` que solo necesita `token`).
- `proforma/src/app/components/top-menu/top-menu.component.ts`/`.html` (consumidor de `currentUser.name`).
- `proforma/src/app/components/ng-modal-content/ng-modal-content.component.ts` (consumidor de `currentUser.name`, `.lastname`, `.email`, `.phone_number` para precargar el formulario de proforma).
- `proforma/src/app/pages/lista/lista.component.ts`, `proforma/src/app/pages/proforma/proforma.component.ts`, `proforma/src/app/components/create-user/create-user.component.ts` (también leen `getUser()`/`currentUser`, revisar alcance exacto de qué campos usan si se decide reducir el set persistido).
- `proforma/src/app/model/user.ts` (shape de `User`).

### Implementaciones similares existentes

No hay ningún patrón existente en el proyecto para "estado de usuario solo en memoria" ni para "perfil de usuario obtenido del backend on-demand" — hoy la única fuente de verdad del usuario logueado es `localStorage`, reconstruida de forma síncrona. Cualquier alternativa (estado en memoria que se pierde al recargar la página, o un nuevo endpoint de perfil) sería un patrón nuevo para este código.

### Comportamiento actual

Al hacer login, el frontend guarda seis campos en `localStorage` en texto plano y los mantiene ahí indefinidamente (hasta un `logout()` explícito — y hoy `email` ni siquiera se limpia ahí, ver TASK-003). Cualquier script con acceso al contexto de la página (p. ej. vía XSS) puede leer el token de sesión junto con nombre, apellido, teléfono, email y CI/NIT del usuario sin necesidad de comprometer el backend. De esos seis campos, el guard de rutas solo necesita `token`; el resto se usa para UX (saludo, autocompletado de formulario) salvo `ci_nit`, que no se encontró en uso.

### Restricciones

- `docs/CLAUDE.md`: "Antes de cambios que afecten varios archivos, proponer un plan y esperar confirmación" — este cambio toca al menos `authetication.service.ts` y `ng-modal-content.component.ts`, potencialmente más si se decide sacar campos usados en otros componentes.
- `docs/CLAUDE.md`: "Todo cambio de lógica de negocio lleva su test".
- El propio backlog marca la migración a cookie `httpOnly` (paso 3 del ítem #6) como "épica separada, no forzarlo en las primeras dos semanas" — este task (paso 2) es independiente de esa migración y no debería bloquearse por ella.

### Riesgos identificados

- **Reducir los campos persistidos sin agregar una fuente alternativa degrada (no rompe) el autocompletado de `ng-modal-content`** (`name`, `lastname`, `email`, `phone_number`): tras un refresh de página esos datos se pierden y el formulario aparece vacío — pero como está confirmado que ese formulario es obligatorio, editable y con validación (`required` + `ngForm`), el usuario de todas formas debe pasar por esa pantalla y puede escribirlos a mano sin que se rompa la creación de la proforma. Es un costo de fricción (volver a tipear 3 campos tras un refresh), no una regresión funcional.
- `ci_nit` es código muerto confirmado en el frontend (se guarda pero no se usa ni siquiera para prellenar el campo C.I. del propio formulario que lo pediría) — se elimina directamente de lo persistido, sin impacto de UX.
- Cualquier decisión aquí interactúa con la pregunta de negocio abierta en el backlog sobre quién es dueño de definir qué PII es aceptable persistir — sin esa respuesta, el criterio de "lo estrictamente necesario para la UI" es ambiguo (¿el autocompletado de contacto cuenta como "necesario"?).
- No hay tests hoy sobre `AutheticationService` ni sobre `ng-modal-content` que capturen el comportamiento actual antes de tocarlo (consistente con backlog #8).

### Veredicto de complejidad

**NEEDS_ARCHITECTURE** — el cambio no es solo "borrar unas líneas de `saveData`": impacta múltiples componentes que hoy dependen de esos campos para UX (autocompletado de contacto en la creación de proforma), no existe una fuente de datos alternativa en el backend para reemplazarlos, y depende de una pregunta de negocio sin resolver sobre qué PII es aceptable persistir. Es una decisión de diseño de cómo se maneja el estado de sesión del lado cliente, no un fix acotado.

## Arquitectura

Decisión registrada en [ADR-003](../adr/ADR-003-reduce-localstorage-pii.md):

- `localStorage` pasa a persistir solo `token` + `name`. `lastname`/`email`/`phone_number` quedan solo en memoria (vía el `BehaviorSubject` `userLoginSource` ya existente en `AutheticationService`) durante la sesión del SPA — se pierden en un refresh de página. `ci_nit` deja de guardarse (confirmado código muerto).
- `getUser()` deja de reconstruir desde `localStorage` en cada llamada y pasa a leer `userLoginSource.value` (en memoria); un método nuevo separado reconstruye el estado mínimo (`token`+`name`) al arrancar la app.
- No se agrega endpoint de perfil en el backend — se descartó por sobreingeniería relativa al problema, dado que el formulario que prellenan estos campos (`ng-modal-content`) es editable y obligatorio, no un envío silencioso.
- Riesgo aceptado documentado: sesiones en múltiples pestañas dejan de sincronizarse automáticamente entre sí (antes sí, porque `getUser()` releía `localStorage` cada vez).

## Plan

[PLAN-2026-09-21-reduce-localstorage-pii.md](../plans/PLAN-2026-09-21-reduce-localstorage-pii.md) (v1)

## Implementación

Resumen (detalle completo en PR #30, sección `## Changes`):

- `login()` solo persiste `token`+`name` en `localStorage`. `getUser()` pasa a devolver `userLoginSource.value` (en memoria) en vez de reconstruir desde `localStorage`. Nuevo método privado `restoreMinimalSession()` siembra el estado mínimo al arrancar la app.
- `logout()` sigue limpiando las 6 claves legacy (incluida `email`) para cubrir PII de sesiones anteriores a este cambio.
- `ng-modal-content.component.ts`: `.trim()` en la concatenación de nombre/apellido para evitar un espacio final cuando `lastname` está vacío.
- Tests nuevos en `authetication.service.spec.ts` (6 casos, reemplazando el boilerplate).
- Confirmado por grep que ningún otro componente lee `currentUser.email`/`.lastname`/`.phone_number` — no hizo falta tocar nada más.

**Verificación propia ejecutada** (no es el Quality Gate formal — eso es `delivery-review`):
- `ng test` → 34/34 OK (28 preexistentes + 6 nuevos), sin regresiones. `ng build` → OK.
- **Verificación end-to-end real en navegador**, con el backend real corriendo y un usuario de prueba creado vía `create_client` (eliminado al terminar): login → modal de datos del cliente se prellena sin recargar (nombre, teléfono, email correctos) → `localStorage` inspeccionado en vivo confirma solo `token`+`name` → refresh de página real → saludo y guard de rutas siguen funcionando (solo necesitan `token`+`name`) → modal reaparece con nombre prellenado pero teléfono/email/C.I. vacíos y editables, formulario enviable, sin errores de consola.
- **Incidente de proceso durante la verificación, resuelto**: la primera ronda se hizo sin querer contra un `ng serve` que ya estaba corriendo en el puerto 4200, que resultó ser del checkout principal del repo (fuera de este worktree), no de esta rama — mostraba las 6 claves viejas en `localStorage`, lo cual parecía un bug. Se detectó comparando el archivo fuente en ambos checkouts, y se repitió la verificación con una instancia de `ng serve` propia apuntando a este worktree (puerto `4201`, whitelisteado en `CORS_ORIGIN_WHITELIST`), confirmando el comportamiento correcto.

## Review

**Veredicto: PASS** — sin issues abiertos, sin `docs/reviews/REV-...md` generado para este task (el único hallazgo de esta ronda de revisión, REV-2026-09-21-002, es específico de TASK-002).

Verificación independiente ejecutada (evidencia completa en el PR #30, sección `## Testing`):
- `npx ng test --watch=false --browsers=ChromeHeadless --code-coverage` → `34/34 OK`, corrida de nuevo desde cero, sin regresiones. Cobertura de `authetication.service.ts`: statements 92.85%, branches 75%, functions 75%, lines 92.59%.
- `npx ng build` → OK, sin errores (type-check limpio).
- `npm audit`: solo vulnerabilidades preexistentes de devDependencies, no relacionadas a este cambio.
- Confirmado por grep, de forma independiente (no reusando el resultado del engineer), que `ng-modal-content.component.ts` sigue siendo el único lugar que lee `currentUser.email`/`.lastname`/`.phone_number` — sin scope creep, sin componentes rotos por el cambio.
- Acceptance criteria del plan verificados contra la evidencia ya reunida por `delivery-engineer` (login → localStorage solo token+name → refresh real → saludo/guard sobreviven → formulario vacío pero editable, sin errores de consola) — no se repitió la sesión de navegador en esta revisión al no encontrarse motivo para dudar de esa evidencia (tests unitarios cubren exactamente la misma lógica de forma aislada, con cobertura alta).

**Nota de aislamiento de contexto**: esta revisión corrió en la misma sesión que implementó el cambio (`delivery-engineer`) — limitación procedimental señalada explícitamente. Se compensó re-ejecutando los comandos de forma independiente en vez de confiar en lo ya reportado.

## Publicación
_Pendiente_
