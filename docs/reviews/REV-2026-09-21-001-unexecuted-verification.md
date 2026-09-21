# REV-2026-09-21-001: Verificación funcional/técnica no ejecutable en este entorno de review

**Status:** Waived — autorizado por el usuario en el chat de la sesión (2026-09-21) para proceder a publicación sin ejecutar estas verificaciones, dado el perfil de riesgo bajo del cambio (diff de una línea por archivo, puramente de infraestructura, sin lógica de negocio tocada). Queda como pendiente informativo para quien despliegue en el servidor real (ver nota abajo).
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-09-21-secure-prod-env-injection.md (v1)
**Suggested owner:** delivery-engineer (o el usuario, corriendo los comandos en un entorno con las herramientas instaladas)

## Description

El plan (paso 8 de "Implementation steps") pide validar con un build+run real de `praxsa_manager/Dockerfile.prod` que la imagen arranca correctamente sin el `COPY .env-prod ./.env` y que la inyección por `env_file` funciona. Ese paso ya había quedado señalado como pendiente por `delivery-engineer` (ver `## Implementación` de TASK-001). Al reconstruir la verificación de forma independiente para este review, confirmo que **ninguna verificación funcional o técnica ejecutable** definida en el skill `delivery-review` pudo correrse en este entorno de review, más allá de la validación de sintaxis de `docker compose config`.

No se trata de un defecto de código encontrado — es una limitación del entorno donde corre este review (sin Docker daemon, sin Django instalado, sin `node_modules`). Se documenta igual porque la regla del Quality Gate es explícita: no declarar `PASS` mientras una verificación quede sin ejecutar.

## Expected behavior

Según `delivery-review/SKILL.md`, este review debería ejecutar y adjuntar evidencia real de: tests backend (`python manage.py test`), tests frontend (`ng test --watch=false --browsers=ChromeHeadless`), build frontend (`ng build`), lint/type-check si están configurados, y el build+run de Docker que el propio plan pide como verificación de infraestructura (paso 8).

## Actual behavior

- **Backend tests**: no ejecutable — Django no está instalado en este entorno (`ModuleNotFoundError: No module named 'django'` al correr `manage.py test`). Tampoco existe un `praxsa_manager/.env` local con el que `settings.py` pudiera arrancar, incluso si Django estuviera instalado.
- **Frontend tests/build**: no ejecutable — `proforma/node_modules` no existe en este entorno.
- **Lint/type-check**: no aplica — no hay `.flake8`, `setup.cfg`, `pyproject.toml` ni `.eslintrc*` configurados en el repo (verificado, ninguno existe). No es una verificación omitida, es una herramienta que el proyecto nunca configuró.
- **Security checks** (`npm audit`, `bandit`/`safety`): no ejecutable — dependen de `node_modules`/entorno Python que no están disponibles aquí.
- **Build+run de Docker** (paso 8 del plan): no ejecutable — `docker info`/`docker build` fallan con error de conexión (`open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified`); el CLI de Docker está presente pero el daemon no es alcanzable desde este sandbox.
- **Sí se pudo ejecutar y pasó**: `docker compose -f docker-compose.prod.yml config` con un `praxsa_manager/.env` de placeholder temporal — sintaxis válida, `env_file` se resuelve correctamente para `web` y `db` (ver Evidence).

## Evidence

```
$ cd praxsa_manager && python manage.py test
Traceback (most recent call last):
  ...
ModuleNotFoundError: No module named 'django'
...
ImportError: Couldn't import Django. Are you sure it's installed and available on your PYTHONPATH environment variable? Did you forget to activate a virtual environment?

$ ls proforma/node_modules
ls: cannot access 'proforma/node_modules': No such file or directory

$ docker build -f praxsa_manager/Dockerfile.prod -t praxsa-web-test:validate praxsa_manager/
ERROR: error during connect: Head "http://%2F%2F.%2Fpipe%2FdockerDesktopLinuxEngine/_ping": open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.

$ docker compose -f docker-compose.prod.yml config   # con praxsa_manager/.env de placeholder
name: delivery-env-config-67c844
services:
  db:
    ...
    environment:
      DB_HOST: db
      DB_PORT: "5432"
      DEBUG: "0"
      ENV: PROD
      ...
  web:
    ...
    environment:
      DB_HOST: db
      DB_PORT: "5432"
      DEBUG: "0"
      ...
```

(salida completa disponible en el historial de comandos de esta sesión — se resumió aquí por longitud, sin omitir el resultado del chequeo).

## Verificación estática realizada (por inspección de archivos, no ejecución)

Como complemento, sí verifiqué por lectura directa del diff (`git diff origin/master...HEAD`) y del filesystem, sin depender de herramientas no instaladas:
- `.gitignore` ignora exactamente `praxsa_manager/.env`, `.env-dev`, `.env-prod`, `.env-stg`; no ignora los `.example`.
- `git ls-files | grep env` ya no incluye los 3 archivos reales; siguen presentes en disco sin cambios de contenido más allá del `DEBUG=0` ya aplicado en `.env-stg`.
- `praxsa_manager/.env-prod.example` y `.env-dev.example` tienen exactamente las mismas claves que sus contrapartes reales (`ENV, DEBUG, SECRET_KEY, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, DB_HOST, DB_PORT[, TZ, PGTX]`), sin valores reales.
- `praxsa_manager/Dockerfile.prod` ya no tiene ningún `COPY` de archivo `.env*` (`grep` confirma cero coincidencias).
- `docker-compose.prod.yml` tiene `env_file: praxsa_manager/.env` en el servicio `web`, idéntico al que ya tenía `db`.
- El diff (`git diff origin/master...HEAD --name-only`) no toca ningún archivo de `praxsa_manager/product/` ni de `proforma/src/` — sin scope creep respecto del plan.
- No hay cambios que roten `SECRET_KEY`/password ni que toquen el historial de git.

Estos puntos de la lista de acceptance criteria del plan están confirmados por inspección directa. Los dos que exigían ejecución real (build+run de la imagen, y la ausencia de regresión en las suites de test existentes) quedan sin verificar.

## Resolución

El usuario autorizó explícitamente, en el chat de esta sesión, proceder a publicación sin ejecutar estas verificaciones — no las considera bloqueantes dado que el cambio es de una línea por archivo, puramente de infraestructura, y `docker compose config` ya validó la sintaxis. Queda como recomendación operativa (no bloqueante) correr `docker compose -f docker-compose.prod.yml up -d --build` una primera vez en un entorno controlado, con el `.env` real ya creado en el servidor, antes de confiar en que el despliegue funciona de punta a punta.
