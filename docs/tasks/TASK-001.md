# TASK-001: Dejar de exponer secretos de producción (backlog #1) y asegurar el despliegue a prod

**Etapa actual:** PLANNING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Rama:** _sin asignar todavía_
**Pull Request:** _sin abrir todavía_

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-09-21 | (nuevo) → INVESTIGATION | Task creado a partir del ítem #1 de docs/integration-and-backlog.md | delivery-investigate |
| 2026-09-21 | INVESTIGATION → PLANNING | Decisión arquitectónica tomada: inyección de secretos en runtime vía `env_file`, sin hornear en la imagen ni commitear en git | delivery-architect |

## Investigación

### Requerimiento

Ejecutar el ítem #1 del backlog de seguridad (`docs/integration-and-backlog.md:133-139`), con tres pasos originalmente descritos:

1. `.env-stg` con `DEBUG=0` — trivial. **Ya aplicado** en esta rama (fuera de este flujo `delivery-*`, por decisión directa del usuario en conversación).
2. Sacar los `.env*` del repo, agregarlos a `.gitignore`, documentar en el README cómo se inyectan en cada Dockerfile/pipeline. Depende del paso 1.
3. Limpiar el historial de git (`git filter-repo`/BFG) — depende de coordinar con el equipo porque reescribe historia compartida. El usuario indicó explícitamente que **"vale la pena revisarlo, pero antes"** hay que resolver el paso 2, y no dio luz verde a ejecutarlo todavía.

El usuario aportó contexto adicional que cambia el alcance real del paso 2: los ambientes Docker de dev y stg fueron dados de baja (dev corre hoy con comandos `python`/`ng` directos, sin Docker; stg se quitó por costos). El único ambiente Docker activo es **producción**, construido con `docker-compose.prod.yml` (raíz) + `praxsa_manager/Dockerfile.prod`. El pedido explícito del usuario es: *"necesitamos una mejor forma de desplegar en producción y sin exponer nuestras llaves"* — es decir, el paso 2 del backlog no es solo "mover archivos y documentar", sino diseñar cómo inyectar secretos en el único ambiente productivo sin exponerlos ni en git ni en la imagen Docker.

### Hechos encontrados

- `praxsa_manager/.env-prod`, `.env-dev`, `.env-stg` están trackeados en git desde el commit `4daf717` (2023-06-23) — más de 2 años de exposición en el historial.
- `praxsa_manager/.env-prod:3` y `praxsa_manager/.env-dev:3` comparten el mismo `SECRET_KEY`.
- `praxsa_manager/.env-prod:5` contiene el password real de Postgres de producción, en texto plano.
- `praxsa_manager/praxsa_manager/settings.py:26` — Django siempre lee un archivo llamado literalmente `.env` en `BASE_DIR` (`praxsa_manager/`), sin importar el ambiente; el nombre no es parametrizable sin tocar código.
- `praxsa_manager/Dockerfile.prod:16` — `COPY .env-prod ./.env`: el secreto queda horneado en una capa de la imagen Docker. Esto es un vector de exposición independiente de git: sobrevive a cualquier limpieza de historial futura, y cualquiera con acceso a la imagen (registro, `docker save`, `docker history --no-trunc`) puede extraerlo.
- `docker-compose.prod.yml` (raíz), línea 71 — el servicio `db` usa `env_file: praxsa_manager/.env` (nombre fijo `.env`, no `.env-prod`) — requiere que exista un archivo `.env` real en el host al momento de `docker compose up`, mecanismo distinto al de la imagen `web`.
- `docker-compose.prod.yml` (raíz) — el servicio `web` **no tiene** `env_file:`; sus variables llegan únicamente por el `COPY` horneado en `Dockerfile.prod:16`.
- No existe archivo `.gitignore` en la raíz del repo (verificado: no existe).
- No existe pipeline de CI/CD en el repo — se buscó `.github/workflows`, `.gitlab-ci.yml`, `Jenkinsfile` y scripts de deploy; no se encontró ninguno.
- `praxsa_manager/.dockerignore` no excluye ningún archivo `.env*` del contexto de build.
- `README.md` (raíz) no documenta variables de entorno ni cómo se inyectan secretos; solo lista comandos (`README.md:1-45`).
- Siguen presentes en el repo, aunque según el usuario ya no se usan: `praxsa_manager/Dockerfile.stg`, `nginx/Dockerfile.stg`, `proforma/Dockerfile.stg`, `docker-compose.stg.yml`, `docker-compose.dev.yml` (raíz), `praxsa_manager/docker-compose.dev.yml`, `praxsa_manager/docker-compose.prod.yml` (anidado, distinto del de la raíz), `.env-stg`, `.env-dev`.
- El patrón `env_file:` ya se usa en este mismo `docker-compose.prod.yml` para el servicio `db` (línea 71) — no sería un mecanismo nuevo, solo extenderlo al servicio `web`.

### Hipótesis / supuestos no confirmados

- No se pudo verificar cómo llega hoy el archivo `praxsa_manager/.env` real (no trackeado) al servidor de producción para el servicio `db` — si se coloca manualmente, vía algún proceso externo al repo, o si en la práctica alguien copia `.env-prod` a `.env` a mano en el servidor. No hay evidencia de ese paso en el repo.
- Se asume, por indicación verbal del usuario (no verificable en código), que `docker-compose.stg.yml`/`Dockerfile.stg` y los compose de dev ya no se usan en ningún servidor real.
- No se pudo confirmar si el registro/imagen Docker de producción es privado o público, ni si alguien ya extrajo el secreto horneado en la imagen (`Dockerfile.prod:16`) — dato relevante para decidir la urgencia de rotación de `SECRET_KEY`/password.
- No se confirmó si hay un `praxsa_manager/.env` ya presente y funcionando en el servidor de producción actual, lo que afectaría si "sacar los .env* del repo" rompe el próximo build o no.

### Módulos y dependencias relacionadas

- **Infra de despliegue activa**: `docker-compose.prod.yml` (raíz), `praxsa_manager/Dockerfile.prod`, `nginx/Dockerfile.prod`, `proforma/Dockerfile.prod`.
- **Configuración de Django**: `praxsa_manager/praxsa_manager/settings.py` (lectura de `.env`).
- **Documentación**: `README.md` (raíz), `docs/integration-and-backlog.md` (origen del ítem #1).
- **Código de infra ya inactivo, no tocado en esta investigación**: `Dockerfile.stg` (3 variantes), `docker-compose.stg.yml`, `docker-compose.dev.yml` (raíz y anidado), `.env-stg`, `.env-dev`.

### Implementaciones similares existentes

- El propio `docker-compose.prod.yml` ya resuelve la inyección de secretos en runtime para el servicio `db` vía `env_file:` (línea 71) — es el patrón nativo de Docker Compose que ya se usa en este repo, candidato natural para extender al servicio `web` en vez de introducir una herramienta nueva.

### Comportamiento actual

Para levantar producción hoy: `docker compose -f docker-compose.prod.yml up -d --build` (`README.md:9`). Esto construye la imagen `web` a partir de `praxsa_manager/Dockerfile.prod`, que copia el archivo `.env-prod` (trackeado en git) al `.env` interno de la imagen — el secreto queda parte de la imagen construida. El contenedor `db`, en cambio, recibe sus variables en runtime desde un archivo `praxsa_manager/.env` que debe existir en el host en el momento del `up` — no está confirmado si ese archivo es una copia manual de `.env-prod` o se mantiene por separado.

### Restricciones

- `docs/CLAUDE.md`: "No tocar archivos `.env` ni credenciales" — regla explícita. El usuario ya autorizó una excepción puntual para el paso 1 (`DEBUG=0`) en esta conversación; esta tarea es en sí misma la remediación de esa regla, por lo que la misma excepción aplicaría a los pasos siguientes, sujeta a que el usuario la confirme explícitamente en cada paso (ya se hizo para el paso 1).
- `docs/CLAUDE.md`: "Antes de cambios que afecten varios archivos, proponer un plan y esperar confirmación" — aplica de lleno: la solución tocaría como mínimo `Dockerfile.prod`, `docker-compose.prod.yml`, `.gitignore`, `git rm --cached` de 3 archivos, un `.env-prod.example` nuevo, y `README.md`.
- `docs/CLAUDE.md`: "No agregar dependencias sin avisar antes" — relevante si la "mejor forma de desplegar" implicara herramientas nuevas (gestor de secretos externo, CI/CD nuevo). El hallazgo del patrón `env_file:` ya existente sugiere que puede resolverse sin dependencias nuevas, pero es una decisión de `delivery-architect`, no de esta etapa.
- `docs/CLAUDE.md`: "Si algo no se puede verificar en el código, decirlo; no inventar" — aplica directamente al mecanismo real de cómo llega el `.env` al servidor hoy (ver hipótesis).

### Riesgos identificados

- El `SECRET_KEY` compartido y el password real de Postgres llevan expuestos en el historial de git desde 2023-06-23 (2+ años) — cualquier colaborador pasado o presente con acceso de lectura al repo ya tuvo acceso a ambos.
- Hornear secretos en una capa de imagen Docker (`Dockerfile.prod:16`) es un vector de exposición **independiente de git**: sobrevive a un futuro `git filter-repo`/BFG (paso 3) y no lo resuelve el paso 2 tal como está descrito originalmente en el backlog (que solo habla del repo, no de la imagen).
- Remover los `.env*` de git sin dejar un mecanismo de reemplazo funcional (plantilla `.example` + instrucciones claras) puede romper el próximo build de quien reconstruya el servidor de producción desde cero.
- Cualquier cambio a `Dockerfile.prod`/`docker-compose.prod.yml` afecta directamente el único ambiente productivo activo hoy — un error ahí no es cosmético, puede tumbar el despliegue real de la aplicación.
- El paso 3 (limpieza de historial) queda explícitamente pospuesto por decisión del usuario; no se investigó en profundidad su mecánica en este TASK.

### Veredicto de complejidad

**NEEDS_ARCHITECTURE** — El paso 1 (ya aplicado) era un `TRIVIAL_FIX` aislado, pero el alcance real que pide el usuario ahora ("una mejor forma de desplegar en producción sin exponer nuestras llaves") es una decisión de infraestructura de despliegue: cómo inyectar secretos en el único ambiente productivo activo, con impacto en múltiples archivos de build/deploy (`Dockerfile.prod`, `docker-compose.prod.yml`, `.gitignore`, README) y riesgo de romper el despliegue real si se hace mal. Encaja directamente con los indicadores "cambios de infraestructura" e "impacto en múltiples módulos" que `delivery-architect` evalúa, y conviene decidir explícitamente el mecanismo de inyección (y si aplica algo más que `env_file:`) antes de planificar la implementación.

## Arquitectura

**[ADR-001: Dejar de commitear y de hornear secretos de producción; inyectarlos solo en runtime](../adr/ADR-001-runtime-env-injection-prod.md)**

Decisión: quitar el `COPY .env-prod ./.env` de `praxsa_manager/Dockerfile.prod`, inyectar el servicio `web` de `docker-compose.prod.yml` con `env_file: praxsa_manager/.env` (mismo patrón que ya usa `db`), dejar de trackear los `.env*` en git (`.gitignore` + `git rm --cached`), publicar `praxsa_manager/.env-prod.example` como plantilla, y documentar el mecanismo real en el README. No incluye rotación de credenciales ni limpieza de historial de git (pospuestas, fuera de alcance). Ver el ADR para las alternativas descartadas (Docker secrets, gestor de secretos externo, `docker build --secret`) y la estrategia de rollback.

## Plan
_Pendiente_

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
