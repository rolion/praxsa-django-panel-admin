# ADR-001: Dejar de commitear y de hornear secretos de producción; inyectarlos solo en runtime

**Estado:** Propuesto
**Task relacionado:** TASK-001
**Fecha:** 2026-09-21

## Contexto

`docs/tasks/TASK-001.md` (investigación) confirmó dos vectores de exposición distintos para los secretos de producción (`SECRET_KEY`, password de Postgres):

1. **Git**: `praxsa_manager/.env-prod`, `.env-dev`, `.env-stg` están trackeados desde 2023-06-23 (commit `4daf717`), con `SECRET_KEY` compartido entre entornos y el password real de Postgres de producción en texto plano (`praxsa_manager/.env-prod:5`).
2. **Imagen Docker**: `praxsa_manager/Dockerfile.prod:16` (`COPY .env-prod ./.env`) hornea ese mismo secreto dentro de una capa de la imagen de producción. Este vector es independiente del anterior — sobrevive a cualquier limpieza futura del historial de git (paso 3 del backlog, explícitamente pospuesto) y no lo resuelve por sí solo el paso 2 tal como estaba descrito originalmente ("sacar los `.env*` del repo").

El usuario confirmó además el estado real de los ambientes: dev corre sin Docker (comandos `python`/`ng` directos); stg fue dado de baja por costos; **producción es el único ambiente Docker activo**, construido con `docker-compose.prod.yml` (raíz) + `praxsa_manager/Dockerfile.prod`. El pedido explícito es una mejor forma de desplegar a producción sin exponer las llaves — no se pidió (ni se justifica) resolver esto para stg/dev, que están inactivos.

Restricciones del proyecto (`docs/CLAUDE.md`) relevantes: no agregar dependencias sin avisar; cambios pequeños con un objetivo por cambio; no inventar lo que no se puede verificar. No hay evidencia en el repo de un pipeline de CI/CD ni de un gestor de secretos ya en uso.

## Decisión

Separar completamente la construcción de la imagen Docker de producción de los secretos, e inyectar todas las variables de entorno del servicio `web` en **runtime**, con el mismo mecanismo que ya usa el servicio `db` en el propio `docker-compose.prod.yml`:

1. Quitar `COPY .env-prod ./.env` de `praxsa_manager/Dockerfile.prod` — la imagen deja de contener ningún secreto.
2. Agregar `env_file: praxsa_manager/.env` al servicio `web` en `docker-compose.prod.yml` (raíz), igual que ya tiene `db` en la línea 71 — mismo patrón, sin mecanismo nuevo.
3. El archivo real `praxsa_manager/.env` con los valores de producción **nunca se commitea**: vive únicamente en el filesystem del servidor de producción, con permisos restringidos (p. ej. `chmod 600`, propietario el usuario de despliegue).
4. Dejar de trackear en git los `.env*` existentes (`.env-prod`, `.env-dev`, `.env-stg`) vía `.gitignore` + `git rm --cached`, y publicar `praxsa_manager/.env-prod.example` (placeholders, sin secretos reales) como plantilla de referencia.
5. Documentar en `README.md` el mecanismo real de inyección (qué archivo espera cada Dockerfile/compose, y que el `.env` de producción se crea a mano una sola vez en el servidor a partir del `.example`).

Esto resuelve en un solo mecanismo consistente tanto la exposición en git (paso 2 del backlog) como el hallazgo nuevo de la imagen horneada, sin tocar los artefactos ya inactivos de stg/dev (fuera de alcance, según lo indicado por el usuario).

**Nota explícita de alcance**: esta decisión no rota `SECRET_KEY` ni el password de Postgres (eso es la acción operativa de "Día 0" que ya señala `docs/integration-and-backlog.md:219`, fuera de una PR de código) ni ejecuta la limpieza del historial de git (paso 3, explícitamente pospuesto por el usuario en la investigación). Sin rotación, los valores ya expuestos en el historial siguen siendo válidos independientemente de este cambio.

## Alternativas consideradas

- **Docker Compose `secrets:` (montaje de archivos en `/run/secrets/*`)**: técnicamente algo más prolijo (no aparece en `docker inspect`/variables de entorno del proceso), pero requeriría reescribir cómo `settings.py` lee configuración (hoy usa `django-environ` con un único archivo `.env`, no lectura de múltiples archivos de secreto) — un cambio de código no pedido y no trivial para el beneficio marginal que aporta en un despliegue de un solo servidor sin Swarm. Se descarta por sobreingeniería relativa al problema real.
- **Gestor de secretos externo (Vault, AWS Secrets Manager, Doppler, etc.)**: resolvería rotación y auditoría de forma más robusta, pero agrega una dependencia/servicio nuevo, costo y complejidad operativa no justificados para una app self-hosted de un solo VPS sin pipeline de CI/CD existente. Violaría además la regla del proyecto de no agregar dependencias sin avisar. Se descarta por ahora; si el equipo crece o se automatiza el despliegue con CI/CD, vale la pena reconsiderarlo como ADR separado.
- **Mantener el `COPY` pero agregarlo a `.dockerignore` después del build (`docker build --secret`)**: BuildKit soporta `--secret` para no dejar el archivo en ninguna capa, pero requiere habilitar BuildKit explícitamente y cambiar la sintaxis del Dockerfile (`# syntax=docker/dockerfile:1`, `RUN --mount=type=secret`) — es una mejora real, pero para este caso no hace falta ningún secreto en tiempo de **build** (ni `SECRET_KEY` ni el password de Postgres se usan durante `pip install`/`collectstatic`); el problema se resuelve más simple no metiendo el secreto a la imagen en absoluto. Se descarta por ser una solución más compleja para un problema que no existe (no hay secretos que el build realmente necesite).

La opción elegida (`env_file` en runtime) es la única que no requiere tocar código de la aplicación, reutiliza un patrón ya presente en el mismo archivo de configuración, y no agrega dependencias — es la alternativa más simple que cierra ambos vectores de exposición encontrados.

## Estrategia de rollback / mitigación

Este cambio afecta el único ambiente productivo activo, así que sí aplica una estrategia explícita:

- **Riesgo principal**: si `praxsa_manager/.env` no existe (o le faltan variables) en el servidor de producción en el momento del primer `docker compose -f docker-compose.prod.yml up -d --build` con estos cambios, el contenedor `web` fallará al arrancar (`django-environ` lanza error ante variables faltantes) — caída del servicio.
- **Mitigación previa al despliegue**: el usuario (único con acceso al servidor) debe crear manualmente `praxsa_manager/.env` en el servidor **antes** de desplegar esta PR, con el mismo contenido que hoy tiene `.env-prod` (o el valor rotado, si se decide rotar en el mismo momento), permisos `600`. Este es un paso operativo, no parte del PR de código — se documentará explícitamente en el README y se le avisará al usuario como prerrequisito antes de mergear/desplegar.
- **Validación antes de producción**: correr `docker compose -f docker-compose.prod.yml config` para validar sintaxis, y (dado que no hay ambiente de stg activo para probar) hacer una prueba local con un `.env` de placeholder para confirmar que la imagen `web` arranca correctamente sin el `COPY` del secreto.
- **Rollback**: es un cambio puramente de infraestructura/configuración, sin migraciones ni cambios de datos. Si el `web` no levanta tras el despliegue, revertir es `git revert` del commit de este cambio + `docker compose up -d --build` de nuevo — vuelve a hornear el secreto temporalmente (riesgo conocido y aceptado como plan B de corto plazo) mientras se corrige el `.env` del servidor. Docker conserva las capas de la imagen anterior salvo `prune` explícito, por lo que también es viable simplemente re-taggear la imagen previa si estuviera disponible.

## Consecuencias

- **Más fácil**: los secretos de producción dejan de depender de que alguien recuerde no commitear un archivo; quedan en un único lugar (el `.env` del servidor), fuera del control de versiones y fuera de la imagen. Rotar una credencial a futuro ya no requiere reconstruir la imagen (solo editar el `.env` del servidor y reiniciar el contenedor).
- **Más difícil**: levantar producción desde cero exige un paso manual extra documentado (crear `praxsa_manager/.env` en el servidor a partir del `.example`) que antes "funcionaba solo" porque el secreto viajaba dentro del propio repo/imagen. Es una fricción aceptada a cambio de dejar de exponer credenciales.
- **Deuda técnica aceptada conscientemente**: el `.env` de producción sigue siendo un archivo plano en el filesystem del servidor (no un gestor de secretos con rotación/auditoría). Se acepta por ahora dado el tamaño y la infraestructura actual del proyecto (un solo VPS, sin CI/CD); queda como candidato a revisar en un ADR futuro si el proyecto crece o se automatiza el despliegue.
- **No resuelto por este ADR** (fuera de su alcance, según la investigación): la rotación de `SECRET_KEY`/password ya expuestos, y la limpieza del historial de git (paso 3 del backlog) — ambos quedan como acciones pendientes separadas, explícitamente pospuestas.
