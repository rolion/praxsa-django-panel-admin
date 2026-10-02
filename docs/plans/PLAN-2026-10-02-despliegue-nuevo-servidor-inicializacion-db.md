# PLAN-2026-10-02-despliegue-nuevo-servidor-inicializacion-db (v1)

**Task:** TASK-despliegue-nuevo-servidor-inicializacion-db
**DDRs relacionados:** Ninguno
**ADRs relacionados:**
- [ADR-despliegue-nuevo-servidor-inicializacion-db-stack-v2-build-y-enrutamiento](../adr/ADR-despliegue-nuevo-servidor-inicializacion-db-stack-v2-build-y-enrutamiento.md)
- [ADR-despliegue-nuevo-servidor-inicializacion-db-inicializacion-datos-seed](../adr/ADR-despliegue-nuevo-servidor-inicializacion-db-inicializacion-datos-seed.md)

## Objective
Dejar un despliegue Docker nuevo ("v2") reproducible en un servidor aparte —sin tocar el que ya funciona— con Django en `/admin`, `panel_admin` en `/panel`, la calculadora en `/calculadora`, Adminer en `/adminer`, y un script manual que migra e inicializa la BD (grupos, sucursales, usuarios, instaladores, catálogo, láminas, bobinas, inventario). Elimina los volúmenes compartidos `static` y `laminas`: los estáticos viajan dentro de la imagen.

## Context
Ver `docs/tasks/TASK-despliegue-nuevo-servidor-inicializacion-db.md` (investigación y cuatro rondas de decisiones del usuario) y los dos ADR. Resumen: hoy el despliegue exige red/volúmenes externos creados a mano, `nginx-proxy`, dominios fijos y pasos manuales; `proforma` sale del stack; el dominio aún no existe; la contraseña del seed sale de `DEFAULT_PASSWORD` en el `.env`.

## Current behavior
- `docker-compose.prod.yml:94-106` declara red `proxy` y volúmenes `postgres/static/media/laminas` como `external: true`; `:42-45` depende de `nginx-proxy`.
- `praxsa_manager/Dockerfile.prod:42` solo arranca `gunicorn`; `migrate`/`collectstatic` son manuales (`README.md:44-47`).
- `nginx/nginx.conf.prod:27,56` separa por `server_name` de subdominios; no existe `/panel`, `/calculadora` ni `/adminer`.
- `panel_admin/` no tiene Dockerfile; `angular.json:66-81` no tiene `fileReplacements` en `production`; `environment.ts` fija `apiUrl: 'http://localhost:8000'`; usa `HashLocationStrategy` (`app.config.ts:28`) y carga i18n con ruta relativa (`app.config.ts:36`, `./assets/i18n/`).
- `settings.py:70-110` hardcodea `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` y `CORS_ORIGIN_WHITELIST`; `:34,158-163` exige `SECRET_KEY` y `POSTGRES_*` sin defaults; `:210-211` define `STATIC_ROOT` solo con `ENV=PROD`.
- Ningún comando ni migración crea los grupos; `asignar_permisos_*` fallan si faltan (`product/management/commands/asignar_permisos_estados.py:47-52`).

## Expected behavior
`docker compose -f docker-compose.v2.yml up -d --build` levanta `db`, `web`, `nginx`, `adminer` sin recursos creados a mano; luego `scripts/init-v2.sh` (manual) aplica migraciones y siembra datos de forma idempotente. Por IP o dominio futuro: `/admin/` (Django), `/panel/` (SPA), `/calculadora` → `/panel/#/calculadora`, `/adminer/` (login con credenciales de Postgres), `/static/` y `/media/`. Reconstruir imágenes no requiere destruir volúmenes. El despliegue actual no cambia.

## Architecture considerations
Resumen de los ADR (no se re-derivan):
- **Infra aditiva:** archivos nuevos con sufijo `v2`; nada de prod/stg/dev se modifica salvo `settings.py` (defaults idénticos a los valores actuales) y `README.md` (sección nueva).
- **Datos persistentes:** solo `postgres_v2` y `media_v2`.
- **Seguridad:** sin TLS en esta versión; Adminer sin puerto publicado al host y con credenciales de Postgres; contraseña del seed en `.env` (`DEFAULT_PASSWORD`), sin valor en código; `praxsa_manager/.env` real **nunca** debe entrar al contexto de build (ver paso 3).
- **Contrato API:** sin cambios; `panel_admin` usa `apiUrl` relativo (mismo origen), por lo que CORS no interviene en v2.
- **Migraciones:** no hay migración nueva (el seed no cambia el esquema).
- **Dinero:** precios de bobinas (440/880) y descripción en `Decimal`/string, nunca `float` (`docs/CLAUDE.md:33`).
- **Ajuste menor respecto del ADR de stack:** en lugar de `praxsa_manager/Dockerfile.v2` + `nginx/Dockerfile.v2`, un solo `Dockerfile.v2` multi-stage en la raíz con targets `web` y `nginx` (misma base Python compartida entre `collectstatic` y `web`, sin duplicar la instalación de dependencias). No cambia ninguna decisión del ADR; se refleja en el ADR en este mismo commit.

## Proposed solution
**Stack:** `docker-compose.v2.yml` (`name: praxsa-v2`) con `db` (`postgres:16`, healthcheck `pg_isready`, volumen `postgres_v2`, `env_file`), `web` (target `web`, `depends_on: db: condition: service_healthy`, volumen `media_v2`, `env_file`, `expose 5000`), `nginx` (target `nginx`, puerto publicado `80:80`, volumen `media_v2` de solo lectura) y `adminer` (imagen `adminer`, `ADMINER_DEFAULT_SERVER=db`, sin puertos al host). Sin límites de memoria hasta medir.

**Dockerfile.v2 (raíz, contexto raíz):**
- Etapa `backend` (python:3.10-alpine): dependencias del sistema y `pip install -r praxsa_manager/requirements-3.8.10.txt`; copia `praxsa_manager/`.
- Etapa `static`: `FROM backend`, crea `logs/` y `static/`, ejecuta `collectstatic --noinput` con variables ficticias solo en esa instrucción (`ENV=PROD`, `SECRET_KEY`, `POSTGRES_*`, `DB_HOST`, `DB_PORT`; `collectstatic` no abre la BD) → `staticfiles/`.
- Etapa `panel`: node 22, `npm ci` y `ng build --configuration production --base-href /panel/` en `panel_admin/`.
- Target `web`: desde `backend`, `gunicorn` (puerto 5000), sin migraciones ni seed.
- Target `nginx`: `nginx` + `nginx.conf.v2` + `COPY --from=static` (a `/praxsa_manager/staticfiles`) + `COPY --from=panel` (a `/usr/share/nginx/html/panel`).

**nginx.conf.v2:** un solo `server` en :80: `/admin/`, `/product/`, `/tinymce/`, `/api-auth/` → `web:5000` (con `X-Forwarded-*`; `$forwarded_proto` como en `nginx.conf.prod:12-15`); `/static/` y `/media/` por alias; `/panel/` con `try_files` a `/panel/index.html`; `/adminer/` → `adminer:8080/` (quita prefijo); `= /calculadora` y `/calculadora/` → 302 a `/panel/#/calculadora`; `= /` → 302 a `/panel/`.

**panel_admin:** `src/environments/environment.prod.ts` con `production: true`, `apiUrl: ''`, mismo `whatsappNumber`; `fileReplacements` en la configuración `production` de `angular.json`.

**Django:** `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `CORS_ORIGIN_WHITELIST` con `env.list(NOMBRE, default=<lista actual>)`.

**Seed** (ADR de seed): `product/management/commands/inicializar_datos.py` (datos fijos en constantes; `--dry-run`; `--password`; lee `DEFAULT_PASSWORD`; atómico), `exportar_catalogo_seed.py` (herramienta de desarrollo), `product/seed_data/catalogo.json`, `scripts/init-v2.sh` (`DEFAULT_PASSWORD` presente → `migrate --noinput` → `inicializar_datos` → `importar_imagenes_modelos`). Descripciones de láminas en el Apéndice A.

## Files/components affected
**Backend (`praxsa_manager/`)**
- `praxsa_manager/settings.py` — listas por entorno con defaults actuales.
- `product/management/commands/inicializar_datos.py` (nuevo), `exportar_catalogo_seed.py` (nuevo).
- `product/seed_data/catalogo.json` (nuevo).
- `product/tests/test_inicializar_datos.py`, `product/tests/test_exportar_catalogo_seed.py` (nuevos).
- `.env-v2.example` (nuevo, claves de `.env-prod.example` + `DEFAULT_PASSWORD`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `CORS_ORIGIN_WHITELIST`, `DB_HOST=db`, `ENV=PROD`).

**Infra / raíz**
- `docker-compose.v2.yml`, `Dockerfile.v2`, `nginx/nginx.conf.v2`, `.dockerignore` (nuevo en la raíz; excluye `.git`, `.claude`, `node_modules`, `**/.env*` salvo `*.example`, `praxsa_manager/media`, `logs`, `proforma/`), `scripts/init-v2.sh`, `.gitignore` (agregar `praxsa_manager/.env-v2`), `README.md` (sección v2).

**Frontend (`panel_admin/`)**
- `src/environments/environment.prod.ts` (nuevo), `angular.json` (`fileReplacements` en `production`).

No se modifican `docker-compose.prod/stg/dev.yml`, `Dockerfile*` existentes, `nginx/*prod|stg*`, `proforma/`, modelos ni migraciones.

## Implementation steps
1. **settings por entorno:** reemplazar las 3 listas por `env.list(..., default=[valores actuales])`. Verificar que sin las variables el resultado es idéntico (comparación de listas antes/después).
2. **`panel_admin` producción:** crear `environment.prod.ts` y `fileReplacements`; confirmar con `ng build --configuration production --base-href /panel/` que el build pasa y que `index.html` genera `<base href="/panel/">` y las rutas a `assets/i18n/` resuelven bajo `/panel/`.
3. **`.dockerignore` raíz y `.gitignore`:** excluir todo `.env*` real del contexto (el contexto raíz incluye `praxsa_manager/.env`, que no debe viajar al daemon ni a ninguna capa). Agregar `praxsa_manager/.env-v2` al `.gitignore`.
4. **`exportar_catalogo_seed`** y generación de `product/seed_data/catalogo.json` desde la BD local (marcas, modelos por marca, ítems, modelo-ítem; claves por nombre; ordenado; `ensure_ascii=False`; decimales como string; omite y reporta filas con ítem nulo). Revisar el JSON a mano (conteos esperados: 33/155/9/12; sin datos de prueba) antes de commitearlo.
5. **`inicializar_datos`** con el orden y reglas del ADR de seed: validar `DEFAULT_PASSWORD`/`--password` con `AUTH_PASSWORD_VALIDATORS` antes de escribir; grupos únicos (`Admin`, `Almacen`, `Caja`, `Vendedor`); `call_command` de los tres `asignar_permisos_*`; sucursales (`Santa Cruz`: Av. Ovidio Barbery entre 4to. y 5to anillo, 3352139; `La Paz`: Calle Angel Pacheco - Obrajes, 78512440); usuarios `superadmin` (superusuario, staff, ambas sucursales, grupo `Admin`), `admin1` (staff, grupo `Admin`, Santa Cruz), `admin2` (staff, grupo `Admin`, La Paz) con `set_password` solo al crear; `Profile` vacío por usuario; instaladores `instalador 1` (Santa Cruz) e `instalador 2` (La Paz), teléfono `3554432`; catálogo desde el JSON; las 10 láminas (Apéndice A); bobinas 0.5 m/440 y 1 m/880, `length` 20, para `CRYSTALLINE-70`; inventario por sucursal × bobina (`quantity` 1, `to_install` 20, `original_length` 20, `date` = ahora). `--dry-run` reporta sin escribir; todo en `transaction.atomic()`.
6. **Tests de ambos comandos** (ver Test strategy).
7. **`Dockerfile.v2`** (etapas `backend`, `static`, `panel`, targets `web` y `nginx`) y **`nginx.conf.v2`**.
8. **`docker-compose.v2.yml`** y **`.env-v2.example`**.
9. **`scripts/init-v2.sh`:** `set -e`; aborta con mensaje si `DEFAULT_PASSWORD` no está en `praxsa_manager/.env`; ejecuta con `docker compose -f docker-compose.v2.yml exec -T web` los tres comandos; parámetros opcionales (`--dry-run`) se pasan a `inicializar_datos`. Debe ser ejecutable (`git update-index --chmod=+x`) y usar finales de línea LF.
10. **README:** sección "Despliegue v2": prerrequisitos (`.env` desde `.env-v2.example`), `up -d --build`, `scripts/init-v2.sh`, volver a correr solo `migrate` en despliegues siguientes, rutas, Adminer (login = Postgres, no `PGADMIN_*`), nota de HTTP sin TLS y de la contraseña del seed.
11. **Verificación en Docker** (si el daemon está disponible; si no, declararlo): `docker compose -f docker-compose.v2.yml config`, `build`, `up`, `scripts/init-v2.sh` dos veces, y las comprobaciones de los criterios de aceptación; medir memoria de `web` y `db` con `docker stats` para decidir límites.

## Test strategy
- **Unitario/integración (Django `TestCase`, patrón de `test_asignar_permisos_reportes.py` y `test_importar_imagenes_modelos.py`):**
  - `inicializar_datos`: sin `DEFAULT_PASSWORD` ni `--password` → `CommandError` y cero escrituras; con la variable → crea 4 grupos únicos, 2 sucursales con datos exactos, 3 usuarios con flags correctos (`is_staff` para todos, `is_superuser` solo `superadmin`) y membresía a sucursales (`superadmin` en ambas), contraseña verificable con `check_password`, 2 instaladores con su sucursal y teléfono, 10 láminas con descripción, 2 bobinas (ancho/precio/largo) y 4 inventarios con `to_install`=20, `original_length`=20, `quantity`=1; **segunda ejecución sin duplicados** (conteos iguales); `--dry-run` sin escrituras; `--password` tiene precedencia; contraseña que no pasa los validadores → error sin escrituras; usuario existente conserva su contraseña salvo `--password`; los permisos de `asignar_permisos_*` quedan asignados al grupo `Admin`; atomicidad (un fallo posterior no deja datos parciales, simulado con un `JSON` de catálogo inválido).
  - Catálogo: carga mínima desde un JSON de prueba (marca/modelo/ítem/modelo-ítem), nombres únicos respetados, repetir no duplica.
  - `exportar_catalogo_seed`: escribe JSON estable (dos corridas idénticas), omite ítem nulo con reporte, no escribe en BD.
- **Frontend:** sin specs nuevos (solo configuración de build); se valida con `ng build --configuration production` y `ng lint` no se ve afectado por un archivo de entorno.
- **Infra (manual, scripteado con `curl` en el criterio de aceptación):** build, arranque, rutas, estáticos y seed idempotente.
- **E2E (Playwright): NO.** No cambia ningún flujo de usuario ni UI; los riesgos son de build/enrutamiento/datos y se cubren con tests de comandos y una verificación de humo por `curl`. Agregar Playwright sería una dependencia nueva sin valor proporcional.

## Acceptance criteria
- `python manage.py test product` en verde, con los tests nuevos; `makemigrations --check --dry-run` sin cambios.
- Con las variables de entorno nuevas ausentes, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` y `CORS_ORIGIN_WHITELIST` son idénticas a las actuales.
- `docker compose -f docker-compose.v2.yml up -d --build` levanta los 4 servicios sin crear red ni volúmenes a mano; `docker volume ls` muestra solo `postgres_v2` y `media_v2` para este stack.
- `scripts/init-v2.sh` aborta con mensaje claro sin `DEFAULT_PASSWORD`; con ella migra y siembra; una **segunda ejecución** no cambia los conteos.
- Datos tras el seed: 4 grupos; 2 sucursales; `superadmin` (superusuario, 2 sucursales), `admin1`, `admin2` (staff, grupo Admin, 1 sucursal c/u); 2 instaladores; 33 marcas, 155 modelos, 9 ítems, 12 modelo-ítem; 10 láminas; 2 bobinas de `CRYSTALLINE-70` y 4 filas de inventario de 20 m.
- Por HTTP en el host nuevo: `/admin/login/` responde 200 con CSS (`/static/admin/css/base.css` 200); `/panel/` carga la SPA y su login funciona contra `/product/api-panel-admin-token-auth/`; `/calculadora` redirige a `/panel/#/calculadora` y la calculadora lista el catálogo; `/adminer/` abre el login y permite ver la BD con las credenciales de Postgres; una imagen subida a `/media/` sobrevive a `docker compose ... up -d --build`.
- Reconstruir `web` y `nginx` **no** requiere borrar ningún volumen.
- `praxsa_manager/.env` no está presente en ninguna capa de las imágenes (`docker history`/inspección del contexto).
- Los archivos de despliegue actual (`docker-compose.prod.yml`, `Dockerfile.prod`, `nginx.conf.prod`, etc.) no tienen diferencias en el diff.

## Risks
- **Docker no disponible en la sesión** (ocurrió en el task de imágenes): el paso 11 y varios criterios pueden quedar sin verificar; se declarará explícitamente en el PR, no como PASS silencioso.
- **`collectstatic` en build exige variables ficticias:** si `settings.py` agrega lecturas de entorno nuevas sin default, el build falla; mitigación: etapa `static` documentada y cubierta por el build en el paso 11.
- **Angular 21 requiere Node reciente** (se propone node 22; no verificado contra `package.json`/engines); mitigación: probar el build en el paso 2.
- **`base href /panel/` + `HashLocationStrategy`:** no verificado que todos los assets y el lazy loading resuelvan bajo `/panel/`; mitigación: verificar en el paso 2 y en la verificación manual.
- **Adminer sobre HTTP expuesto:** credenciales de Postgres en claro; mitigación documental (restringir por firewall) hasta tener TLS; aceptado por el usuario.
- **Catálogo local puede contener datos de prueba o diferir de lo esperado:** se revisa el JSON antes de commitearlo; no hay mitigación automática.
- **Supuestos sin confirmar** (ver "Out of scope / preguntas abiertas").
- **Límites de memoria:** sin medición, `web`/`db` van sin límite; se decide tras `docker stats`.
- **`pip install` de `psycopg2` y `Pillow` en Alpine** sin wheel puede requerir paquetes del sistema (ya cubiertos por el `Dockerfile.prod` actual: gcc, libc-dev, postgresql-dev); no verificado con el build nuevo.

## Out of scope
- `proforma/` (queda sin uso y sin borrar), TLS/dominio, migrar datos de producción, límites de memoria definitivos, basic auth para Adminer, rutas sin `#` en `panel_admin`.
- **Preguntas abiertas / supuestos a confirmar** (no bloquean el plan; se implementan como están y se corrigen si el usuario dice otra cosa):
  1. `superadmin` además va en el grupo `Admin` (el pedido solo dice "superusuario").
  2. `address` de los instaladores = dirección de su sucursal (no se dio dirección).
  3. `inventario.precio_compra_mtr_lineal` y `precio_venta_mtr_lineal` quedan en 0 y `nro_lote` vacío (no se dieron).
  4. Se crea un `Profile` vacío por usuario sembrado.

## Dependencias nuevas
Ninguna (Python/Node: nada que instalar en el proyecto). Las imágenes base `postgres:16`, `adminer`, `nginx`, `node:22-alpine` son de runtime/build, no dependencias de código.

## Apéndice A — Láminas del seed (texto dado por el usuario)
Nombre → `Window_Film.name`; texto → `Window_Film.description`.

1. `CA 35` — Las nanopartículas cerámicas absorben y rechazan el calor, manteniendo la claridad. Las opciones de iluminación transmiten casi toda la luz visible para mantener los interiores brillantes, las opciones oscuras ayudan a reducir el deslumbramiento.
2. `COLOR STABLE-20` — COLOR STABLE 20. No metalizado para mantenerte conectado con dispositivos móviles, GPS o recepción de radio satelital sin interferencias, reduce el calor hasta 57% el TSER, bloquea hasta el 99% de la luz ultravioleta (UV) para brindar protección solar para usted y sus pasajeros.
3. `COLOR STABLE-5` — COLOR STABLE 5. No metalizado para mantenerte conectado con dispositivos móviles, GPS o recepción de radio satelital sin interferencias, reduce el calor hasta 57% el TSER, bloquea hasta el 99% de la luz ultravioleta (UV) para brindar protección solar para usted y sus pasajeros.
4. `Color Stable IR - 15` — La película 3M Color Stable IR para ventanas automotrices está fabricada con partículas nanocerámicas impregnadas en el poliéster de la película.
5. `Color Stable IR - 35` — (mismo texto que la 4)
6. `Color Stable IR - 5` — (mismo texto que la 4)
7. `Color Stable IR - 50` — La película 3M Color Stable IR para ventanas automotrices está fabricada con partículas nanocerámicas impregnadas en el poliéster de la película (sin punto final en el original).
8. `CRYSTALLINE-40` — CRYSTALLINE 40. Excelente rendimiento de rechazo de calor prácticamente transparente, bloquea hasta el 99% de la luz ultravioleta (UV) para brindar protección solar para usted y sus pasajeros. Ofrece un deslumbramiento reducido de la luz solar para que pueda ver mejor y concentrarse más en la carretera.
9. `CRYSTALLINE-70` — CRYSTALLINE 70. (mismo texto que la 8, con "CRYSTALLINE 70.")
10. `FX-HP 15` — FX-HP 15. Excelente rendimiento de rechazo de calor con un elegante acabado, bloquea hasta el 99% de la luz ultravioleta (UV) para brindar protección solar para usted y sus pasajeros. Ofrece un deslumbramiento reducido de la luz solar para que pueda ver mejor y concentrarse más en la carretera.
