# ADR-despliegue-nuevo-servidor-inicializacion-db-stack-v2-build-y-enrutamiento: Stack Docker "v2" autocontenido, estáticos horneados en imagen y enrutamiento por path

**Estado:** Propuesto
**Task relacionado:** TASK-despliegue-nuevo-servidor-inicializacion-db
**Fecha:** 2026-10-02

## Contexto
El despliegue actual (`docker-compose.prod.yml`) depende de recursos externos creados a mano (red `proxy`, volúmenes `postgres`, `static`, `media`, `laminas`; `docker-compose.prod.yml:94-106`), de un `nginx-proxy` con Let's Encrypt que no está en el repo (`:42-45`), de dominios fijos por subdominio (`nginx/nginx.conf.prod:27,56`) y de pasos manuales dentro de `web` (`collectstatic`, `migrate`; `README.md:44-47`). Los estáticos de Django y el build de `proforma` se publicaban en volúmenes que nginx leía, por eso cada cambio exigía recrearlos. El usuario decidió: servidor nuevo (o al menos recursos con sufijo `v2` para no afectar al actual), sin subdominios ni `nginx-proxy` (aún no hay dominio), `proforma` fuera del stack, `static` y `laminas` eliminados, Adminer accesible por path, y rutas `/admin` (Django), `/panel` (`panel_admin`), `/calculadora` (calculadora de `panel_admin`), `/adminer`.

Hechos relevantes: `panel_admin` ya contiene la administración y la calculadora (`panel_admin/src/app/app.routes.ts:11-65`) con `HashLocationStrategy` (`app.config.ts:28`); toda su API usa `${environment.apiUrl}/product/...` (46 archivos) y `environment.ts` fija `apiUrl: 'http://localhost:8000'`, sin `fileReplacements` en la configuración `production` (`angular.json:66-81`). `settings.py` exige `SECRET_KEY`, `POSTGRES_*` y `DB_HOST` sin valores por defecto (`:34,158-163`), define `STATIC_ROOT` solo con `ENV=PROD` (`:210-211`) y escribe logs en `BASE_DIR/logs` (`:271,277`). Hosts, CSRF y CORS están hardcodeados (`:70-110`).

## Decisión
Crear un stack nuevo **aditivo** sin tocar los archivos del despliegue actual:

1. **Archivos nuevos con sufijo `v2`:** `docker-compose.v2.yml`, un `Dockerfile.v2` multi-stage en la raíz con targets `web` y `nginx` (ajuste de plan: antes se proponían dos Dockerfiles; la decisión no cambia), `nginx/nginx.conf.v2` y un `.env-v2.example` (incluye `DEFAULT_PASSWORD`, usada solo por el seed; ver ADR de inicialización). Servicios `web`, `nginx`, `db`, `adminer`; `container_name` con sufijo (`web_v2`, `nginx_v2`, `db_v2`, `adminer_v2`); `name: praxsa-v2` a nivel de proyecto.
2. **Sin recursos externos:** red y volúmenes los crea el propio compose. Solo dos volúmenes con nombre, `postgres_v2` (datos) y `media_v2` (subidas del admin, montado en `web` y `nginx`). Desaparecen `static`, `laminas` y la red `proxy`. `proforma` no forma parte del stack.
3. **Estáticos horneados en la imagen, sin volumen compartido:** el target `nginx` de `Dockerfile.v2` (contexto en la raíz del repo) se construye con etapas: (a) etapa Python que ejecuta `collectstatic` con variables ficticias solo para el build (`ENV=PROD`, `SECRET_KEY` dummy, etc.; `collectstatic` no abre la BD) y crea `logs/`; (b) etapa Node que construye `panel_admin` con `--base-href /panel/`; (c) etapa final `nginx` que copia ambos resultados. Cada rebuild de la imagen `nginx` actualiza estáticos y SPA a la vez; no hay nada que destruir.
4. **Enrutamiento por path en un único `server` nginx** (sin `server_name`, escucha :80, sirve por IP o por cualquier dominio futuro): `/admin/`, `/product/`, `/tinymce/` y `/api-auth/` → `web:5000`; `/static/` → estáticos de la imagen; `/media/` → volumen `media_v2`; `/panel/` → SPA de `panel_admin` (fallback a `index.html`); `/adminer/` → `adminer:8080` (se retira el prefijo); `/calculadora` → redirección 302 a `/panel/#/calculadora`. `/` redirige a `/panel/`.
5. **`panel_admin` en mismo origen:** `apiUrl` pasa a `''` (URLs relativas) para el build de producción, de modo que no se hornea ningún dominio; para ello se añade un `fileReplacements`/entorno de producción en `panel_admin` (decisión de detalle del plan). El hash routing se mantiene: **`/calculadora` limpia se resuelve con la redirección**, no cambiando la estrategia de ubicación (cambiarla afectaría a las 46 dependencias de rutas y al guard de sesión, sin valor de negocio hoy).
6. **Django parametrizado por entorno, preservando el comportamiento actual:** `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` y `CORS_ORIGIN_WHITELIST` se leen de variables de entorno (django-environ, ya en uso) **con las listas actuales como valor por defecto**, de modo que el despliegue existente no cambia aunque reciba este código. En v2 se configuran por `.env` (IP/dominio futuro, con esquema `http://` o `https://`).
7. **Adminer:** imagen `adminer`, solo en la red interna (sin puerto publicado al host), con `ADMINER_DEFAULT_SERVER=db`. El login es el de Postgres (`POSTGRES_USER`/`POSTGRES_PASSWORD`); las variables `PGADMIN_*` no se usan (son de pgAdmin).
8. **Arranque ordenado, sin pasos manuales de infraestructura:** `db` con healthcheck (`pg_isready`) y `web` con `depends_on: condition: service_healthy`. Postgres con versión fija (`postgres:16`), no `latest`. **El Dockerfile no ejecuta migraciones ni seed**; ambos corren en el script manual de inicialización (ver ADR de seed).

## Alternativas consideradas
- **Reusar `docker-compose.prod.yml` con variables/perfiles:** menos archivos, pero cualquier edición se redeploya sobre el servidor que ya funciona (riesgo que el usuario quiere evitar) y arrastra volúmenes/red externos. Descartada.
- **WhiteNoise para servir estáticos desde `web`:** elimina la copia a nginx, pero agrega una dependencia (`docs/CLAUDE.md:36`) y nginx seguiría necesitando los estáticos de `panel_admin`. Descartada por ahora.
- **Mantener volumen `static` y automatizar su recreación en un script:** conserva el acoplamiento volumen↔imagen que provoca el problema. Descartada.
- **Un nginx separado para `panel_admin` (contenedor propio):** más servicios sin ganancia; el nginx ya existe. Descartada.
- **Cambiar `panel_admin` a rutas sin hash para tener `/calculadora` nativa:** toca todo el enrutado y la sesión; descartada frente a una redirección de una línea. Deuda aceptada: la URL real de la calculadora conserva `#`.
- **Basic auth de nginx delante de `/adminer`:** no se pidió; no se incluye en la decisión (ver Consecuencias).

## Estrategia de rollback / mitigación
- El cambio es **aditivo**: archivos nuevos con sufijo; no se modifican composes, Dockerfiles ni nginx del despliegue actual. La única edición compartida es `settings.py`, con defaults iguales a los valores actuales.
- Rollback del stack v2: `docker compose -f docker-compose.v2.yml down` (conserva datos) o `down -v` (borra `postgres_v2` y `media_v2`); no queda estado fuera de esos dos volúmenes ni de la red del proyecto.
- Rollback de `settings.py`: revertir el commit; sin defaults distintos no hay cambio de comportamiento en el stack actual. Verificarlo con el `.env` actual (sin las nuevas variables) en el plan.
- Si una imagen nueva falla, el volumen de datos no se toca: se reconstruye solo `web`/`nginx`.

## Consecuencias
- Reconstruir `web` o `nginx` ya no requiere destruir volúmenes; solo `postgres_v2` y `media_v2` persisten.
- El despliegue nuevo no necesita red/volúmenes creados a mano ni `nginx-proxy`.
- **Sin TLS en esta versión:** el login de Adminer, de `/admin` y del panel viajan en HTTP plano hasta que exista dominio y certificado. Riesgo aceptado conscientemente por el usuario (sin dominio aún); Adminer expone la BD con credenciales de Postgres sobre HTTP: se recomienda restringir el acceso por red/firewall hasta contar con HTTPS.
- Dominio futuro: se cambia solo `.env` (hosts/CSRF) y se añade TLS en nginx; no hay dominios horneados.
- `proforma/` y los archivos de prod/stg quedan intactos pero sin uso en v2.
- Límites de memoria (100 MB en `web`/`db` del stack actual, `docker-compose.prod.yml:21-24,81-84`) no se trasladan sin medir; el plan debe medir o dejar sin límite.
- Deuda: URL de calculadora con `#`; imagen `nginx` pesada de construir (Node + Python en el build) y contexto de build en la raíz.
