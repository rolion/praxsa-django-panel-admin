# TASK-003: Corregir logout() para que también limpie el email (backlog #6, paso 1)

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** TRIVIAL_FIX
**Rama:** `task/TASK-003-logout-clear-email`
**Pull Request:** https://github.com/rolion/praxsa-django-panel-admin/pull/31

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-09-21 | (nuevo) → INVESTIGATION | Task creado a partir del paso 1 del ítem #6 de docs/integration-and-backlog.md, separado del paso 2 (evaluar reducir PII persistido, TASK-004) por tener naturaleza y complejidad distintas | delivery-investigate |
| 2026-09-21 | INVESTIGATION → ENGINEERING → REVIEW | Camino TRIVIAL_FIX: PR #31 abierto desde `task/TASK-003-logout-clear-email` (creada desde `origin/master`, independiente de la rama compartida de TASK-002/TASK-004); implementado el fix de una línea + test | delivery-engineer |
| 2026-09-21 | REVIEW → PUBLISH | Veredicto PASS (sin issues) — `npm install` + `ng test --code-coverage` (30/30 SUCCESS) + `ng build` corridos con evidencia real; `npm audit` reporta solo vulnerabilidades preexistentes de devDependencies, fuera de alcance. Revisión corrida en la misma sesión que implementó el cambio (limitación de aislamiento procedimental, señalada explícitamente) | delivery-review |

## Investigación

### Requerimiento

Ejecutar el paso 1 del ítem #6 del backlog (`docs/integration-and-backlog.md:175-181`, frontend SEC-01): `AutheticationService.logout()` no limpia la clave `email` de `localStorage`, aunque `login()` sí la guarda — asimetría confirmada por el usuario como "bug menor a corregir".

### Hechos encontrados

- `login()` guarda seis claves en `localStorage` vía `LocalStorageService.saveData` — [authetication.service.ts:47-52](proforma/src/app/service/pybackend/authentication/authetication.service.ts:47): `token`, `name`, `lastname`, `phone_number`, `email`, `ci_nit`.
- `logout()` ([authetication.service.ts:59-68](proforma/src/app/service/pybackend/authentication/authetication.service.ts:59)) llama `removeData` para `token`, `name`, `lastname`, `phone_number`, `ci_nit` — **`email` no está en la lista**. Confirmado por lectura directa del código, línea por línea contra lo que guarda `login()`.
- `getUser()` ([authetication.service.ts:69-81](proforma/src/app/service/pybackend/authentication/authetication.service.ts:69)) reconstruye el `User` leyendo las mismas seis claves, incluyendo `email` — es decir, el campo sí se usa activamente para reconstruir la sesión, no es una clave muerta.
- No hay tests hoy sobre `AutheticationService` (no se encontró ningún `authetication.service.spec.ts` con aserciones más allá de `toBeTruthy()`, consistente con backlog #8).

### Hipótesis / supuestos no confirmados

- No se confirmó si dejar `email` huérfano en `localStorage` tras logout produjo algún efecto visible en producción (p. ej. algún componente que lea `localStorage.getItem('email')` directamente en vez de pasar por `getUser()`) — no se encontró ningún acceso directo a esa clave fuera de `AutheticationService`, pero no se descarta al 100%.

### Módulos y dependencias relacionadas

- `proforma/src/app/service/pybackend/authentication/authetication.service.ts` (único archivo a tocar).
- `proforma/src/app/service/local-storage/local-storage.service.ts` (helper genérico de `localStorage` usado por el servicio de arriba, no requiere cambios).

### Implementaciones similares existentes

El propio archivo ya tiene el patrón correcto para las otras cinco claves (`removeData('name')`, `removeData('lastname')`, etc. en `logout()`) — el fix es agregar la línea faltante siguiendo exactamente ese mismo patrón.

### Comportamiento actual

Tras cerrar sesión, `localStorage['email']` permanece con el valor del último usuario logueado, mientras las otras cinco claves de PII/token se borran correctamente. `userLoginSource.next(null)` sí se emite igual ([authetication.service.ts:66](proforma/src/app/service/pybackend/authentication/authetication.service.ts:66)), por lo que el estado de sesión en memoria (`isUserLoged`) se limpia correctamente — el bug es puntual a la clave `email` en `localStorage`, no afecta el flujo de logout en sí (redirecciones, UI del `top-menu`, etc.).

### Restricciones

- `docs/CLAUDE.md`: "Todo cambio de lógica de negocio lleva su test" — aplica aunque el cambio sea de una línea, dado que toca el manejo de sesión/PII.

### Riesgos identificados

Ninguno relevante: cambio de una línea, sin impacto en contrato de API, sin tocar modelos ni otros archivos.

### Veredicto de complejidad

**TRIVIAL_FIX** — una línea (`this.local.removeData('email')`) siguiendo un patrón ya existente en el mismo método, sin tocar lógica de negocio, contrato de API, modelos, permisos ni múltiples archivos relacionados.

## Arquitectura
_Pendiente / No aplica según veredicto_

## Plan
_Pendiente_

## Implementación

- `proforma/src/app/service/pybackend/authentication/authetication.service.ts`: agregada `this.local.removeData('email')` en `logout()`, en paridad con las otras 5 claves que ya limpiaba (mismo patrón que las líneas vecinas).
- `proforma/src/app/service/pybackend/authentication/authetication.service.spec.ts`: reemplazado el único test boilerplate (`toBeTruthy`) — se mantuvo y se agregó un test que siembra las 6 claves en `localStorage` y verifica que `logout()` las limpia todas, incluida `email`; se agregó `afterEach(() => localStorage.clear())` para no contaminar otros tests.
- No se tocó nada más — cambio acotado a un archivo de lógica y su spec, sin lógica de negocio nueva ni cambios de contrato.
- **Deuda/nota señalada, no resuelta aquí**: si TASK-004 (reducir PII persistido) se implementa después, `login()` dejará de guardar `email` en `localStorage` — la línea agregada en `logout()` se vuelve un no-op inofensivo en ese momento (remueve una clave que ya no existe), no hace falta revertirla.
- **No se corrió `ng test` en este entorno** — `node_modules` no está instalado en el worktree y instalarlo solo para este cambio de una línea no se justificaba; queda para la corrida independiente de `delivery-review`.

## Review

**Veredicto: PASS** — sin issues abiertos, sin `docs/reviews/REV-...md` generado (no hubo hallazgos).

Verificación real ejecutada (evidencia completa en el PR #31, sección `## Testing`):
- `npm install` (limpio, 1109 paquetes) + `npx ng test --watch=false --browsers=ChromeHeadless --code-coverage` → `TOTAL: 30 SUCCESS` (incluye el test nuevo + 29 preexistentes, sin regresiones).
- Cobertura de `authetication.service.ts` tras el cambio: statements 62.5%, branches 75%, functions 42.85%, lines 61.29%.
- `npx ng build` → OK, sin errores (sirve como type-check).
- Lint: no configurado en el proyecto (`proforma/` no tiene `eslint`/`tslint` ni script `lint`) — no ejecutado porque no existe, no se omitió silenciosamente.
- `npm audit`: 109 vulnerabilidades preexistentes en devDependencies (tooling), no relacionadas a este cambio — deuda técnica preexistente, no bloqueante para este PR.
- Diff revisado contra `## Investigación` (no hay Plan formal, `TRIVIAL_FIX`): el cambio implementado coincide exactamente con lo descrito, sin scope creep (solo `authetication.service.ts` + su spec).

**Nota de aislamiento de contexto**: esta revisión corrió en la misma sesión que implementó el cambio (`delivery-engineer`), no en una sesión nueva — limitación procedimental de esta ejecución concreta. Se compensó reconstruyendo la verificación desde comandos reales (no desde memoria de la implementación).

## Publicación
_Pendiente_
