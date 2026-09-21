# PLAN-2026-09-21-secure-prod-env-injection (v1)

**Task:** TASK-001
**ADRs relacionados:** [ADR-001: Dejar de commitear y de hornear secretos de producción; inyectarlos solo en runtime](../adr/ADR-001-runtime-env-injection-prod.md)

## Objective

Cerrar los dos vectores de exposición de secretos de producción confirmados en TASK-001 (`SECRET_KEY` compartido y password real de Postgres): dejar de commitearlos en git y dejar de hornearlos dentro de la imagen Docker de producción, inyectándolos únicamente en runtime en el único ambiente activo (prod).

## Context

Resumen de `docs/tasks/TASK-001.md` (investigación) y `docs/adr/ADR-001-runtime-env-injection-prod.md` (decisión): `praxsa_manager/.env-prod`, `.env-dev`, `.env-stg` están trackeados en git desde 2023; `praxsa_manager/Dockerfile.prod` copia `.env-prod` dentro de la imagen; solo producción está activa (dev sin Docker, stg dado de baja). La decisión tomada es inyectar `env_file: praxsa_manager/.env` en runtime para el servicio `web` (mismo patrón que ya usa `db`), dejar de trackear los `.env*`, y documentar el mecanismo real. Quedan explícitamente fuera de alcance: rotación de credenciales y limpieza del historial de git (paso 3 del backlog, pospuesto por decisión del usuario).

## Current behavior

- `praxsa_manager/praxsa_manager/settings.py:26` — Django siempre lee `praxsa_manager/.env` (nombre fijo).
- `praxsa_manager/Dockerfile.prod:18` — `COPY .env-prod ./.env` hornea el secreto en la imagen.
- `docker-compose.prod.yml:71` — el servicio `db` ya usa `env_file: praxsa_manager/.env`; el servicio `web` no tiene `env_file` (recibe todo vía el `COPY` de la imagen).
- No existe `.gitignore` en la raíz del repo.
- `praxsa_manager/.env-dev`, `.env-prod`, `.env-stg` están trackeados en git con valores reales (`.env-prod` incluye el password real de Postgres de producción).

## Expected behavior

- La imagen `web` de producción no contiene ningún secreto — se construye igual sin importar el ambiente.
- El servicio `web` recibe sus variables de entorno en runtime desde `praxsa_manager/.env`, un archivo que existe únicamente en el filesystem del servidor de producción (nunca en git, nunca en la imagen).
- El repositorio deja de trackear cualquier `.env*` con valores reales; queda una plantilla `.env-prod.example` (y `.env-dev.example` para el flujo de desarrollo local, que sigue necesitando su propio `praxsa_manager/.env`) con placeholders.
- El README explica, sin inventar nada no verificado, qué archivo espera cada Dockerfile/compose y cuál es el paso manual pendiente en el servidor.

## Architecture considerations

Ver ADR-001 para el detalle completo. Resumen: se descartó Docker `secrets:` (requeriría reescribir la carga de configuración en `settings.py`, sin beneficio real a esta escala) y un gestor de secretos externo (agrega dependencia/infraestructura no justificada para un solo VPS sin CI/CD). Se eligió extender el patrón `env_file` que el propio `docker-compose.prod.yml` ya usa para `db`, por ser la alternativa más simple que no requiere tocar código de la aplicación ni agregar dependencias.

Es un cambio de infraestructura que afecta el único ambiente productivo activo — no hay ambiente de stg para probarlo primero, así que la validación se hace con `docker compose config` y un build/run local con un `.env` de placeholder antes de tocar el servidor real (ver Test strategy y Risks).

## Proposed solution

1. Crear `.gitignore` en la raíz ignorando los `.env*` reales de `praxsa_manager/` pero permitiendo los `*.example`.
2. Crear `praxsa_manager/.env-prod.example` y `praxsa_manager/.env-dev.example` con las mismas claves que los archivos reales actuales, pero con valores placeholder (sin secretos).
3. `git rm --cached` de `praxsa_manager/.env-dev`, `.env-prod`, `.env-stg` — quedan en el filesystem local, dejan de trackearse.
4. Quitar la línea `COPY .env-prod ./.env` de `praxsa_manager/Dockerfile.prod`.
5. Agregar `env_file: praxsa_manager/.env` al servicio `web` en `docker-compose.prod.yml` (raíz).
6. Agregar una sección al `README.md` documentando el mecanismo real de inyección por archivo/servicio, y el paso manual pendiente en el servidor de producción (crear `praxsa_manager/.env` ahí, con permisos restringidos, antes de desplegar este cambio).

## Files/components affected

**Infraestructura / config (no hay componentes de backend/frontend de aplicación involucrados):**
- `.gitignore` (nuevo)
- `praxsa_manager/.env-prod.example` (nuevo)
- `praxsa_manager/.env-dev.example` (nuevo)
- `praxsa_manager/Dockerfile.prod` (editar — quitar 1 línea)
- `docker-compose.prod.yml` (editar — agregar 1 línea al servicio `web`)
- `README.md` (editar — nueva sección de variables de entorno)
- `praxsa_manager/.env-dev`, `.env-prod`, `.env-stg` (dejan de trackearse vía `git rm --cached`, contenido sin cambios)

No se tocan `praxsa_manager/product/`, `proforma/src/`, modelos, serializers, ni componentes Angular — no hay lógica de negocio involucrada en este plan.

## Implementation steps

1. Crear `.gitignore` en la raíz del repo.
2. Crear `praxsa_manager/.env-prod.example` y `praxsa_manager/.env-dev.example` (placeholders).
3. `git rm --cached praxsa_manager/.env-dev praxsa_manager/.env-prod praxsa_manager/.env-stg`.
4. Editar `praxsa_manager/Dockerfile.prod`: quitar `COPY .env-prod ./.env`.
5. Editar `docker-compose.prod.yml`: agregar `env_file: praxsa_manager/.env` al servicio `web`.
6. Editar `README.md`: agregar sección "Variables de entorno y despliegue".
7. Validar sintaxis: `docker compose -f docker-compose.prod.yml config`.
8. Validar en local: build de `praxsa_manager/Dockerfile.prod` con un `.env` de prueba (placeholder) montado vía `env_file`/`--env-file` al levantar el contenedor `web`, confirmando que arranca sin errores de variables faltantes (django-environ) y sin que la imagen contenga el secreto (`docker run --rm <imagen> cat .env` no debería encontrar valores reales, solo lo que se monte en runtime).
9. Avisar explícitamente al usuario, antes de fusionar/desplegar, el prerrequisito operativo: crear `praxsa_manager/.env` en el servidor de producción real con los valores actuales (o rotados) y permisos restringidos, **antes** de correr `docker compose -f docker-compose.prod.yml up -d --build` con este cambio.

## Test strategy

Este plan es exclusivamente de infraestructura/configuración de despliegue — no toca modelos, serializers, vistas, ni componentes Angular. Siguiendo el criterio explícito de testing:

- **No corresponde tests unitarios ni de integración** (`praxsa_manager/product/tests/`, `TestBed` de Angular) — no hay lógica de negocio, contrato de API, ni comportamiento de UI involucrado que esos niveles puedan verificar.
- **No corresponde E2E** — no se toca ningún flujo de usuario (login, calculadora, proforma, pago); Playwright no está instalado ni hace falta instalarlo para este cambio.
- **Verificación de infraestructura (manual, no automatizada)**, ya incluida como pasos 7 y 8 de implementación:
  - `docker compose -f docker-compose.prod.yml config` sin errores de sintaxis.
  - Build local de la imagen `web` (Dockerfile.prod) y arranque del contenedor con un `.env` de placeholder vía `env_file`, confirmando que lee las variables correctamente y que la imagen construida no contiene ningún secreto real horneado.

## Acceptance criteria

- [ ] `.gitignore` existe en la raíz e ignora `praxsa_manager/.env`, `.env-dev`, `.env-stg`, `.env-prod`, sin ignorar `*.example`.
- [ ] `git ls-files` ya no incluye `praxsa_manager/.env-dev`, `.env-prod`, `.env-stg`; los tres siguen presentes en el filesystem local sin cambios de contenido (más allá del `DEBUG=0` ya aplicado en `.env-stg`).
- [ ] `praxsa_manager/.env-prod.example` y `.env-dev.example` existen, con las mismas claves que los archivos reales y sin secretos reales.
- [ ] `praxsa_manager/Dockerfile.prod` ya no contiene ningún `COPY` de un archivo `.env*`.
- [ ] `docker-compose.prod.yml` inyecta `env_file: praxsa_manager/.env` en el servicio `web`.
- [ ] `docker compose -f docker-compose.prod.yml config` no arroja errores.
- [ ] Un build+run local de la imagen `web` con un `.env` placeholder arranca correctamente.
- [ ] `README.md` documenta el mecanismo real de inyección y el paso manual pendiente en el servidor.
- [ ] No se modificó ningún archivo de `praxsa_manager/product/` ni de `proforma/src/`.
- [ ] No se rotaron credenciales ni se tocó el historial de git.

## Risks

- **Caída del servicio `web` en producción** si `praxsa_manager/.env` no existe (o le faltan variables) en el servidor al momento de desplegar este cambio. Mitigación: paso 9 de implementación — aviso explícito y verificación previa con el usuario antes de desplegar, documentado también en el ADR como prerrequisito operativo.
- **No hay ambiente de stg para probar el cambio de compose antes de tocar producción** (fue dado de baja). Mitigación: validación local con `docker compose config` + build/run con placeholder (pasos 7-8) antes de aplicar el cambio en el servidor real.
- **Rollback**: cambio puramente de configuración/infraestructura, sin datos ni migraciones — revertir es `git revert` del commit + rebuild; ver ADR-001 para el detalle completo de la estrategia de rollback.

## Out of scope

- Rotación de `SECRET_KEY` y del password de Postgres de producción — acción operativa de "Día 0" (`docs/integration-and-backlog.md:219`), fuera de una PR de código. Sin esta rotación, los valores ya expuestos en el historial de git siguen siendo válidos independientemente de este plan.
- Limpieza del historial de git (`git filter-repo`/BFG, paso 3 del backlog) — explícitamente pospuesta por decisión del usuario, pendiente de coordinar con el equipo.
- Cualquier cambio a los artefactos de infraestructura ya inactivos: `Dockerfile.stg` (de `praxsa_manager`, `nginx`, `proforma`), `docker-compose.stg.yml`, `docker-compose.dev.yml` (raíz y anidado), `praxsa_manager/docker-compose.prod.yml` (anidado, distinto del de la raíz). No se borran ni modifican en este plan.
- **Pregunta abierta para el usuario** (no bloqueante para este plan, pero relevante para un follow-up): ¿se puede eliminar el código muerto de stg/dev-docker en una tarea separada, o preferís conservarlo por si esos ambientes vuelven a activarse?

## Dependencias nuevas

Ninguna.
