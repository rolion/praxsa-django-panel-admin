# TASK-despliegue-nuevo-servidor-inicializacion-db: Nuevo despliegue Docker en servidor aparte, con DB admin y script manual de inicialización de datos

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** NO
**Rama:** `claude/deployment-db-initialization-b97fdc` (asignada por el entorno)
**Pull Request:** [#64](https://github.com/rolion/praxsa-django-panel-admin/pull/64)

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-01 | (nuevo) → INVESTIGATION | Task creado | delivery-investigate |
| 2026-10-01 | INVESTIGATION (actualización) | Respuestas del usuario a las preguntas abiertas: rutas `/admin`/`/panel`/`/calculadora`, sin proforma ni nginx-proxy, sin copiar datos de prod, datos de sucursales/instaladores/bobinas; nuevas discrepancias registradas | delivery-investigate |
| 2026-10-02 | INVESTIGATION (actualización) | 3ra ronda de respuestas: láminas del seed, bobinas/inventario solo CRYSTALLINE-70, todos staff, `superadmin` en ambas sucursales, sufijo `v2` | delivery-investigate |
| 2026-10-02 | INVESTIGATION (actualización) | 4ta ronda: precios de bobinas, catálogo desde BD local, grupos, Adminer con credenciales de Postgres; sin preguntas de producto bloqueantes | delivery-investigate |
| 2026-10-02 | INVESTIGATION (actualización) | Confirmado que `static` y `laminas` se eliminan; quedan `postgres` y `media` | delivery-investigate |
| 2026-10-02 | ARCHITECTURE → PLANNING | Decisiones registradas en 2 ADR: stack Docker v2 autocontenido (estáticos horneados en imagen, enrutamiento por path, Adminer, settings por entorno) y comando manual idempotente de inicialización de datos | delivery-architect |
| 2026-10-02 | PLANNING (ajuste de arquitectura) | Por pedido del usuario, la contraseña del seed se lee de `DEFAULT_PASSWORD` en el `.env` (sin valor en el código); ADR de seed actualizado | delivery-architect |
| 2026-10-02 | PLANNING → ENGINEERING | Plan v1 escrito (settings por entorno, `Dockerfile.v2` multi-stage, compose v2, nginx por path, comando `inicializar_datos` + exportador de catálogo, `scripts/init-v2.sh`, `panel_admin` con `apiUrl` relativo); PR abierto sobre la rama asignada; listo para aprobación humana | delivery-plan |
| 2026-10-02 | PLANNING → PLANNING (plan v2) | Por pedido del usuario se quita `HashLocationStrategy` (URLs sin `#`); `/calculadora` → `/panel/calculadora`; nginx con fallback `try_files`; verificación local del build en `/panel/` registrada | delivery-plan |
| 2026-10-02 | ENGINEERING → REVIEW | Implementación completa según el plan v2; verificación propia en Docker real (build, arranque, seed dos veces, rutas, login, Adminer, persistencia) y suites propias en verde | delivery-engineer |

## Investigación

### Requerimiento
Tal como se recibió: "cambio de planes, ya no se deployara en el mismo server, no quiero afectar al proyecto que ya esta funcionando. Necesito que se mejore la forma se construye el proyecto."

Puntos pedidos:
1. **Agregar un docker de DB admin** (herramienta web para administrar la base).
2. Al construir las imágenes "se tenía que destruir los volúmenes y volverlas a crear, ese paso era manual, tiene que ser automático o mediante un script".
3. **Script para inicializar la base de datos** (usuarios, roles y demás datos), de ejecución **manual**: "no debe correr cada que construya la imagen del docker".
4. Datos a sembrar:
   - **Roles (grupos):** Admin, Almacen, Caja, Vendedor.
   - **Sucursales:** Santa Cruz, La Paz.
   - **Usuarios** (todos con contraseña la contraseña de prueba indicada por el usuario): `superadmin`; `admin1` (sucursal Santa Cruz); `admin2` (sucursal La Paz).
   - **Instaladores:** "instalador 1" (Santa Cruz), "instalador 2" (La Paz).
   - **Copiar** los datos que ya existen de: marcas, modelos, ítems y modelo-ítem; y láminas.
   - **Una bobina por cada lámina**, asignada a las sucursales en el inventario; metros disponibles = 20 m en todas.
5. Sin subdominios en esta versión: `<dominio>/admin` y `<dominio>/calculadora`.

### Hechos encontrados

**Build / Docker actual**
- Existen tres composes en la raíz (`docker-compose.dev.yml`, `.stg.yml`, `.prod.yml`) y dos más viejos dentro de `praxsa_manager/` (`praxsa_manager/docker-compose.dev.yml`, `.prod.yml`). El `README.md:19-20` declara que **prod es el único ambiente Docker activo**; stg y dev-Docker están "dados de baja". `README.md:2-12` lista comandos `up -d --build` por ambiente.
- `docker-compose.prod.yml:4-24` (`web`), `:27-49` (`nginx`), `:51-68` (`proforma`), `:70-84` (`db`). Los cuatro servicios cuelgan de la red `proxy` declarada `external: true` (`:104-106`) y los volúmenes `postgres`, `static`, `media`, `laminas` son **todos `external: true`** (`:94-102`): deben crearse a mano antes de `up`; compose no los crea.
- `docker-compose.prod.yml:42-45`: nginx declara `VIRTUAL_HOST` / `LETSENCRYPT_HOST` / `LETSENCRYPT_EMAIL` con dominios fijos `*.praxsasrl.store` — contrato del contenedor `nginx-proxy` + `acme-companion` del servidor actual (que no está en este repo).
- `db` usa `image: postgres` (sin versión fija) con `env_file: praxsa_manager/.env` y límite de memoria 100 MB (`docker-compose.prod.yml:70-84`). El `.env` es leído también por Django (`settings.py:26`); el README exige crearlo a mano en el servidor (`README.md:16-19`).
- `praxsa_manager/Dockerfile.prod:42` el `CMD` es solo `gunicorn`; **no hay entrypoint ni script de arranque**. `git ls-files` no devuelve ningún `*.sh` ni fixture JSON versionado (solo configs/angular). Por tanto `migrate`, `collectstatic` y `createsuperuser` son pasos manuales con `docker exec -it web sh` (`README.md:38-47`).
- `settings.py:210-211`: `STATIC_ROOT` solo se define si `ENV == "PROD"` (la plantilla `.env-prod.example:1` trae `ENV=PROD`).
- El `Dockerfile` de la raíz (`Dockerfile:1-45`) es otro build de backend (python 3.8, `COPY product/` desde la raíz), no referenciado por los composes de prod; `Dockerfile.prod` usa python 3.10-alpine.
- `proforma/Dockerfile.prod:4-12,22-30`: build multi-stage (node 18.16, Angular CLI 16.1) que **copia `environment.prod.ts` sobre `environment.ts`**; en runtime corre `node dist/proforma/server/main.js` (SSR) en el puerto 4000. `proforma/src/environments/environment.prod.ts` fija `SERVER_APP_BASE_REF: 'http://web:5000'` y `BROWSER_APP_BASE_REF: 'https://panel.praxsasrl.store'` (dominio horneado en el build).
- **`panel_admin/` no tiene Dockerfile** (`ls panel_admin` solo muestra fuentes Angular) y los composes no lo mencionan; `docs/tasks/TASK-modulo-usuarios-perfiles-grupos-roles-sucursales.md:150` ya lo declara "no desplegado a producción".
- No hay ningún servicio de administración de BD activo: `adminer` existe en `docker-compose.dev.yml:20-26` y en `praxsa_manager/docker-compose.*.yml`, y **comentado** en `docker-compose.prod.yml:86-92` y `.stg.yml:85-91`. No hay `pgadmin` en ningún compose.
- No encontré documentación (README, ADR, TASK) que explique **por qué** hacía falta destruir los volúmenes al reconstruir; ver hipótesis.

**Rutas y dominios**
- `nginx/nginx.conf.prod:27,56`: dos `server` con `server_name` fijos (`panel.praxsasrl.store` → Django vía `proxy_pass http://praxsa_server`, y `praxsasrl.store`/`laminas.praxsasrl.store` → servicio `proforma:4000`). Es decir, hoy la separación es **por subdominio**; no hay ningún `location /admin` ni `/calculadora`. `/static/` y `/media/` se sirven por alias desde los volúmenes (`:29-36`).
- `praxsa_manager/praxsa_manager/urls.py:40` (`path('admin/', admin.site.urls)`): Django ya sirve su admin en `/admin/` y la API bajo `/product/` (`:39`). `tinymce/` y `api-auth/` también cuelgan de la raíz (`:42-43`).
- `panel_admin/src/app/app.routes.ts:11-63`: la administración (dashboard, users, vehicles, almacen, ordenes, reportes) vive bajo el layout con `StaffGuard`; `:60-65` la ruta **`calculadora`** (pública, layout mínimo) está **dentro del mismo `panel_admin/`**. `panel_admin/src/app/app.config.ts:28` usa `HashLocationStrategy` (URLs `/#/calculadora`) y `panel_admin/src/index.html:7` fija `<base href="/">`.
- `proforma/src/app/app-routing.module.ts:18-26`: la app vieja (Angular 16 SSR) tiene rutas `''` (formulario/calculadora clásica), `login`, `my-invoice`, `proforma/:id`, etc.; **no tiene una ruta `calculadora`**.
- `panel_admin/src/environments/environment.ts` tiene `apiUrl: 'http://localhost:8000'` con un TODO explícito: "apiUrl de producción sin confirmar ... no se conoce el dominio real del backend".
- `settings.py:70-83` (`ALLOWED_HOSTS`), `:87-92` (`CSRF_TRUSTED_ORIGINS`), `:94-110` (`CORS_ORIGIN_WHITELIST`) están **hardcodeados** con los dominios `praxsasrl.store` / `oscarleon.website` e IPs de servidores; un dominio nuevo no pasa CSRF/CORS/host sin editar `settings.py`. `settings.py:221` confía en `X-Forwarded-Proto` para HTTPS.

**Modelo de datos a sembrar** (`praxsa_manager/product/models.py`)
- `Car_Brand.name` único (`:17-18`); `Car_Model.name` **único global** y FK a marca (`:26-28`); `Car_Part` = "Item" (`:37-39`); `Car_Model_Part` = "Modelo-Item" con `UniqueConstraint(car_model_id, car_part_id)` (`:46-57`).
- `Window_Film` = lámina (`:62-66`, `image` opcional); `Window_Film_Reel` = bobina con `window_film`, `width`, `length`, `price` (`:74-82`). **La FK a lámina es `DO_NOTHING` y una lámina puede tener varias bobinas** (distinto ancho).
- `Sucursal.name` `max_length=20` (`:111`) y M2M `empleado` → `User` (`:114`). `instalador.name` `max_length=20`, `phonenumber` **obligatorio** (sin default ni `blank`), M2M `sucursal` (`:132-139`).
- `inventario` (`:141-155`): FK `sucursal` y `bobina`, `quantity` (obligatorio), `to_install` = "metros disponibles para instalar", `installed`, `original_length`, `date` (obligatorio, `null=False`), `precio_compra/venta_mtr_lineal`, `nro_lote`.
- `Profile` 1:1 con `User` solo con teléfono (`:120-130`). Los roles son `Group` nativos de Django; la lógica de negocio compara el nombre del grupo en minúsculas contra `'admin'`, `'instalador'`, `'supervisor'`, `'caja'`, `'almacen'` (`product/helper/user.py:4-25`); `Vendedor` no tiene helper pero sí permisos asignados.
- Los comandos de gestión existentes **asignan permisos a grupos que ya existen y fallan si no existen**: `asignar_permisos_estados.py:11-26` (grupos `Admin`, `Caja`, `Vendedor`, `Almacen`; lanza `CommandError` si falta alguno), `asignar_permisos_reportes.py`, `asignar_permisos_instalador_precio.py`. **Ningún comando ni migración crea los grupos** (no hay `Group.objects.create` en `product/`; en el ambiente local existen a mano).
- Última migración: `praxsa_manager/product/migrations/0115_client_car_plate.py` (verificado con `ls`).
- Existe `product/seed_data/car_models/` con las imágenes WEBP de modelos (95 archivos) y el comando `importar_imagenes_modelos` (`docs/tasks/TASK-carga-imagenes-modelos-despliegue.md`, PR #62) como precedente de "dato semilla distribuido dentro de la imagen y cargado a mano post-despliegue".

**Estado de los datos fuente (BD local de desarrollo, consultada solo-lectura)**
- 33 marcas, 155 modelos (145 con imagen), 9 ítems, 12 modelo-ítem; 31 láminas (**ninguna con imagen**), **59 bobinas repartidas en 27 láminas (4 láminas sin bobina)**; 7 registros de inventario; 4 sucursales (`Santa Cruz - Central` — exactamente 20 caracteres —, `norte`, `La Paz`, `Sucursal2`); 6 instaladores; 50 usuarios; 40 clientes; 2 `precio_venta_sucursal`.
- Grupos existentes localmente con **duplicados por mayúsculas**: `Vendedor`, `Admin`, `Caja`, `admin`, `almacen`, `Almacen` (el comando `asignar_permisos_reportes` ya documenta que "en algunos ambientes existen tanto `Admin` como `admin`").

### Hipótesis / supuestos no confirmados
- **"Destruir volúmenes"**: probablemente se debía a que el contenedor `postgres` solo lee `POSTGRES_USER/PASSWORD/DB` al inicializar un volumen vacío, y `static` externo conserva `collectstatic` viejo; no hay evidencia escrita en el repo — hay que confirmarlo con el usuario.
- **"Docker de db admin"** = Adminer (hay precedente en los composes) y no pgAdmin; no confirmado. Tampoco si debe quedar expuesto públicamente o solo por túnel/localhost.
- **Nuevo servidor sin `nginx-proxy`/`acme-companion`**: el compose actual depende de la red `proxy` y de `VIRTUAL_HOST`; si el servidor nuevo no los tiene, el TLS y el enrutamiento por dominio cambian. No se sabe qué hay instalado en el servidor nuevo ni si habrá HTTPS.
- **Qué significa `<dominio>/admin` y `<dominio>/calculadora`**: hay dos lecturas posibles — (a) `/admin` = Django admin (ya existe en `urls.py:40`) y `/calculadora` = alguna app Angular; (b) ambos son rutas del nuevo `panel_admin/` (que ya contiene la administración y la ruta `calculadora`, pero con hash routing). Y para `/calculadora`, no está claro si se refiere a `panel_admin` o a la app `proforma` (que hoy no la tiene). No se puede confirmar leyendo el código.
- **Fuente de "copiar lo que tenemos"**: se asume la BD local de desarrollo (única accesible aquí); no se sabe si debe copiarse de producción ni en qué formato quiere el usuario el seed (fixtures JSON, SQL, comando Django con datos embebidos). Los datos locales pueden diferir de producción.
- **"Una bobina por cada lámina"**: puede significar crear bobinas nuevas (una por lámina, con ancho/largo/precio por definir) o reusar las 59 existentes (27 láminas con bobina, 4 sin ninguna). No se dijo qué ancho, largo y precio llevan las bobinas nuevas, ni cuántas unidades (`quantity`).
- **"Los metros disponibles es 20m"** se asume = `inventario.to_install` (y probablemente `original_length`); no confirmado cuál(es) de los campos.
- **"Santa Cruz" / "La Paz"** como nombres de sucursal: localmente se llaman `Santa Cruz - Central` y `La Paz`; no se dijo dirección ni teléfono (`address`/`phone_number`).
- **Instaladores**: se asume el modelo `instalador` (con teléfono obligatorio sin valor dado), no un usuario con grupo `instalador` (que también existe como concepto en `User_Helper`). No confirmado. No se dijo si "instalador 1/2" necesitan además un `User`.
- **`superadmin`**: se asume `is_superuser=True`/`is_staff=True` y sin sucursal; `admin1`/`admin2` se asumen `is_staff=True` + grupo `Admin` (el login del panel exige staff según `docs/tasks/TASK-modulo-usuarios-...:150` y `ADR` de auth admin); no confirmado. Nota: la contraseña de prueba indicada por el usuario pasa los validadores de Django, pero es una credencial conocida y compartida — apta para entorno de pruebas, no para producción real.
- Si "no correr cada vez que se construye la imagen" implica que el script debe ser **idempotente** (re-ejecutable sin duplicar) — probable, no confirmado.

### Módulos y dependencias relacionadas
- Infra: `docker-compose.prod.yml` (y `.dev/.stg`), `praxsa_manager/Dockerfile.prod`, `proforma/Dockerfile.prod`, `nginx/Dockerfile.prod`, `nginx/nginx.conf.prod`, `README.md`, `praxsa_manager/.env-prod.example`, posible Dockerfile nuevo para `panel_admin/`.
- Backend: `praxsa_manager/praxsa_manager/settings.py` (hosts/CSRF/CORS/estáticos), `praxsa_manager/praxsa_manager/urls.py`, `product/models.py`, `product/management/commands/` (precedente de comandos manuales idempotentes), `product/helper/user.py` (nombres de grupo), `product/seed_data/`.
- Frontend: `panel_admin/src/environments/environment.ts`, `panel_admin/src/app/app.config.ts` (hash routing), `app.routes.ts`; `proforma/src/environments/environment.prod.ts`.

### Implementaciones similares existentes
- **Comando de datos manual, idempotente y distribuido en la imagen:** `importar_imagenes_modelos` + `product/seed_data/` (PR #62, `docs/adr/ADR-carga-imagenes-modelos-despliegue-distribucion-imagenes.md`), y los tres `asignar_permisos_*` (todos con `--dry-run` o idempotentes, ejecutados con `docker exec`).
- **Adminer** ya definido en `docker-compose.dev.yml:20-26` (puerto 8080).
- **Build multi-stage de frontend** con `environment.prod.ts` sustituido: `proforma/Dockerfile.prod`.
- No existe precedente de entrypoint, healthcheck, `depends_on` con condición, ni de compose que cree sus propios volúmenes/redes.

### Comportamiento actual
Un despliegue nuevo hoy exige: crear a mano red `proxy` y 4 volúmenes externos; crear `praxsa_manager/.env`; `docker compose -f docker-compose.prod.yml up -d --build`; luego, dentro de `web`, `migrate`, `collectstatic`, `createsuperuser`, crear a mano los grupos y asignar permisos con los comandos `asignar_permisos_*`, y cargar catálogos desde el admin. Los catálogos (marcas, modelos, láminas…) no viajan con el despliegue. `web` arranca en paralelo con `db` (`depends_on` sin espera de disponibilidad) y no migra por sí mismo.

### Restricciones
- `docs/CLAUDE.md:36-38`: no tocar `.env`/credenciales; no agregar dependencias sin avisar; proponer plan antes de cambios multi-archivo. `docs/CLAUDE.md:31-32`: no editar migraciones aplicadas.
- Requisito explícito del usuario: **no afectar el proyecto que ya funciona** en el otro servidor — cualquier cambio a `docker-compose.prod.yml`, nginx o `settings.py` que se redeploye allí lo afecta, así que el despliegue nuevo no puede romper el flujo actual de prod (nombres de contenedor, volúmenes externos, dominios actuales).
- `Car_Model.name` es único global (`models.py:28`): el seed no puede tener dos modelos con el mismo nombre en marcas distintas.
- `Sucursal.name` y `instalador.name` ≤ 20 caracteres.
- `web` limitado a 100 MB y `db` a 100 MB (`docker-compose.prod.yml:21-24,81-84`); un seed grande o un `collectstatic` en ese contenedor podría rozar el límite (no medido).
- Las imágenes de modelos (`seed_data/car_models/`, 2.7 MB) ya viajan en la imagen; las láminas locales no tienen imagen que copiar.

### Riesgos identificados
- **Contaminación del entorno actual:** si el compose nuevo reusa nombres de contenedor (`web`, `nginx`, `db`, `proforma`) o volúmenes/redes externos con el mismo nombre, y se levanta en el mismo host Docker, pisaría producción. El usuario dice que será otro servidor, pero los nombres hardcodeados (`container_name`) y los volúmenes `external` con nombres genéricos siguen siendo un riesgo si alguien lo corre localmente o por error en el servidor viejo.
- **Dominio horneado en builds:** `settings.py` (hosts/CSRF/CORS), `nginx.conf.prod` y `environment.prod.ts` llevan dominios fijos; un dominio nuevo implica editarlos en varios sitios (acoplamiento alto, sin variable de entorno).
- **Datos sembrados con credenciales conocidas** (la contraseña de prueba indicada por el usuario, `superadmin`) en un servidor accesible por internet.
- **Roles duplicados por mayúsculas** (`Admin`/`admin`, `Almacen`/`almacen`) en la fuente: copiar tal cual duplicaría; crear solo uno puede romper comparaciones case-sensitive si algún código no usa `lower()` (los helpers sí lo usan; los comandos `asignar_permisos_*` usan `name__iexact`).
- **El seed depende de migraciones al día**: debe correr después de `migrate`; si se ejecuta antes o contra un esquema distinto, falla.
- **Sin tests de integración del flujo Docker** (build + migrate + seed + servir `/admin` y `/calculadora`); en el TASK de imágenes la verificación Docker quedó pendiente por daemon apagado — el mismo hueco puede repetirse.
- **Hash routing en `panel_admin`:** servir "`/calculadora`" como ruta limpia (sin `#`) requeriría cambiar la estrategia de ubicación o redirigir; no verificado.
- El volumen `postgres` conserva credenciales de la primera inicialización: cambiar `.env` sin recrear el volumen deja la app sin acceso (probable origen del paso manual de "destruir volúmenes").

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — el pedido combina cambios de infraestructura de despliegue (nuevo servidor, nuevos contenedores, enrutamiento por path en lugar de subdominio, ciclo de vida de volúmenes/BD), cambios importantes de datos (seed con usuarios/roles/catálogos que deben ser idempotentes) e impacto en varios módulos (compose, Dockerfiles, nginx, `settings.py`, dos frontends). Además hay decisiones con deuda técnica (cómo parametrizar dominios, qué app sirve `/admin` y `/calculadora`, formato del seed). Varias ambigüedades de producto deben resolverse antes de planificar.

### Diseño requerido
**NO** — no agrega ni cambia superficie de UI; es infraestructura de despliegue y un script de datos (el docker de DB admin es una herramienta de terceros sin UI propia a diseñar).

### Decisiones del usuario (2da ronda, 2026-10-01)
Respuestas a las preguntas abiertas; **prevalecen sobre las hipótesis de arriba** que contradicen.
- **Rutas:** `/admin` = Django admin; `/panel` = `panel_admin/`; `/calculadora` = la calculadora nueva de `panel_admin/`. `proforma/` **ya no se usa** (no se borra todavía). Adminer accesible por otro path (p. ej. `/adminer`).
- **TLS/dominio:** no se usará `nginx-proxy`/Let's Encrypt; sin subdominios; **el dominio aún no existe**.
- **Por qué se destruían volúmenes:** el build de `proforma` y los estáticos de Django admin se publicaban en volúmenes (`laminas`, `static`) que nginx leía; al reconstruir había que recrearlos. El usuario reconoce que no era buena forma y pide mejorarla (es el problema real; la hipótesis de credenciales de Postgres queda como causa secundaria no confirmada).
- **Datos:** no se copia nada de producción ni de la BD local. Se crea la BD, se corren las migraciones y el script siembra los datos. (Sobre "formato del seed": se refería a si los datos viven como comando Django, fixtures JSON o SQL; no hace falta decidirlo con el usuario, es decisión de arquitectura.)
- **Bobinas:** nuevas, de ancho 0.5 y 1 m (una por cada ancho y lámina), `to_install` = 20 m.
- **Usuarios:** `admin1`/`admin2` **sin `is_staff`**. Instaladores: modelo `instalador` ("modelo staff" fue lapsus; confirmar), teléfono `3554432`.
- **Sucursales:** Santa Cruz — Av. Ovidio Barbery entre 4to. y 5to anillo, tel. 3352139; La Paz — Calle Angel Pacheco - Obrajes, tel. 78512440.

### Hechos nuevos derivados de esas respuestas
- **Qué láminas, ítems, marcas y modelos se siembran sigue sin definirse.** "Copia las marcas, modelos, ítems, modelo-ítem y láminas que tenemos" (pedido original) choca con "no copiaremos nada de prod": se interpreta como copiar el **catálogo de la BD local de desarrollo** (33 marcas, 155 modelos, 9 ítems, 12 modelo-ítem, 31 láminas) a un seed versionado, pero **no está confirmado** que sea esa fuente.
- **`admin1`/`admin2` sin `is_staff` no pueden usar `/panel`:** `StaffGuard` solo deja entrar al layout de administración si `isStaff` (`panel_admin/src/app/core/guard/staff.guard.ts:16-25`; un no-staff autenticado se trata como cliente y va a `/calculadora`), y los endpoints de usuarios exigen `IsStaffUser` (`praxsa_manager/product/permissions.py:4-13`). Tampoco entran a `/admin` de Django, que exige `is_staff`. El login `PanelAdminAuthToken` sí los autentica (`auth_token.py:32-43`, no verifica staff), pero solo les sirve para la calculadora y sus APIs de cliente. Hay que confirmar con el usuario si es intencional: solo `superadmin` administraría.
- **Endpoint de cada pieza hoy:** el backend ya funciona bajo `/product/...` y `/admin/` (`praxsa_manager/praxsa_manager/urls.py:39-40`); `panel_admin/` usa `HashLocationStrategy` (`app.config.ts:28`) y `<base href="/">` (`index.html:7`) — servirlo en `/panel` implica cambiar `base href`/`--base-href` en el build (no verificado que `angular.json` lo soporte sin más) y su `apiUrl` apunta a localhost (`environment.ts`, con TODO). `/calculadora` es una ruta interna de `panel_admin` (`app.routes.ts:60-65`), así que bajo hash routing sería `/panel/calculadora`, no `/calculadora` limpia; el enrutado limpio exige cambiar de estrategia de ubicación o redirección de nginx. **No verificado.**
- **Django bajo path:** servir Django en `/admin` sin prefijo extra es directo; pero `/static/` de Django admin ya no necesitaría un volumen compartido si el contenedor `web` (o nginx con la imagen) lleva los estáticos horneados — **posibilidad, no verificada**. `STATIC_ROOT` solo existe con `ENV=PROD` (`settings.py:210-211`).
- **El seed requiere migraciones aplicadas y los permisos dependen de grupos**: orden necesario = `migrate` → crear grupos → asignar permisos (`asignar_permisos_*`) → resto. Los comandos de permisos actuales fallan si faltan los grupos (`asignar_permisos_estados.py:11-26,47-52`).
- `Sucursal.name` ≤ 20 caracteres: "Santa Cruz" y "La Paz" caben. `Sucursal.phone_number` y `instalador.phonenumber` usan `RegexValidator('(\+)*\d{7,11}')` (`models.py:115,135`): `3554432`, `3352139`, `78512440` pasan (7-8 dígitos).
- `inventario.quantity` y `date` son obligatorios y `numero_referencia`, `precio_compra/venta_mtr_lineal` tienen default 0 (`models.py:144-152`): el seed debe definir `quantity` (no indicada; se asume 1 bobina por registro, sin confirmar), `date`, y `original_length` (20 m asumido junto con `to_install`, no confirmado). `Window_Film_Reel.price` es obligatorio y **no se dio precio para las bobinas nuevas**.

### Decisiones del usuario (3ra ronda, 2026-10-02)
- **Láminas del seed (9, con nombre y descripción pegados por el usuario):** `CA 35`, `COLOR STABLE-20`, `COLOR STABLE-5`, `Color Stable IR - 15`, `Color Stable IR - 35`, `Color Stable IR - 5`, `Color Stable IR - 50`, `CRYSTALLINE-40`, `CRYSTALLINE-70`, `FX-HP 15`. (Son **10** nombres en el texto pegado, no 9.) Reemplazan al catálogo local de 31 láminas; el texto de cada una va en `Window_Film.description`.
- **Bobinas e inventario:** solo para `CRYSTALLINE-70`, 4 registros: ancho 0.5 y 1 m × sucursales Santa Cruz y La Paz, con `to_install` = 20, `original_length` = 20, `quantity` = 1. Las demás láminas **quedan sin bobina ni inventario**.
- **Usuarios:** **todos son staff** (`superadmin`, `admin1`, `admin2`) — esto resuelve la discrepancia anterior con `/panel` y `/admin`. `superadmin` va asignado a **ambas sucursales** (Santa Cruz y La Paz).
- **Instaladores:** solo registros del modelo `instalador`, sin `User`.
- **Convivencia con el despliegue actual:** puede ser otro servidor, pero en esta versión se **renombran los recursos con sufijo `v2`** (contenedores, volúmenes, red) para no chocar con el actual.

### Hechos nuevos
- Nombres locales de las láminas (BD de desarrollo) difieren de los pedidos: localmente no existe `CA 35`; las "Color Stable IR - N" se llaman `IR-5/15/35/50`; `COLOR STABLE-20`, `COLOR STABLE-5`, `CRYSTALLINE-40`, `CRYSTALLINE-70` y `FX-HP 15` sí coinciden. El seed define los nombres **tal como los dio el usuario**, no los locales.
- Referencia de precios locales de `CRYSTALLINE-70` (no pedidos, solo antecedente): bobina 0.5 m → 440.00 y 1.00 m → 880.00 (largo 30.50 m en la BD local, `Window_Film_Reel.price` obligatorio, `models.py:81`).
- Dos bobinas (0.5 y 1 m) se comparten entre las 2 sucursales: son 2 `Window_Film_Reel` y 4 `inventario`. `Window_Film_Reel.length` es obligatorio (`models.py:80`); `inventario.original_length` es otro campo (`models.py:147`).
- Marcas, modelos, ítems y modelo-ítem: sigue sin decidirse la fuente (ver pregunta 2).
- Todos los usuarios staff entran a `/panel` (`StaffGuard`) y a `/admin`; los permisos efectivos dependen de los grupos, que siguen sin definirse para `admin1`/`admin2`.
- `Window_Film.description` es `TextField()` obligatorio y `content` es HTML opcional (`models.py:63-65`).
- Sufijo `v2`: hoy los composes usan `container_name: web|nginx|db|proforma` y volúmenes/red externos `postgres|static|media|laminas|proxy` (`docker-compose.prod.yml:5,28,52,71,94-106`); el sufijo aplica a todos ellos en el compose nuevo. `proforma` deja de ser parte del stack nuevo.

### Decisiones del usuario (4ta ronda, 2026-10-02)
- **Bobinas `CRYSTALLINE-70`:** 0.5 m → precio 440, 1 m → precio 880, ambas con `length` = 20.
- **Catálogo:** se copia de la BD local: 33 marcas, 155 modelos, 9 ítems y 12 modelo-ítem (las láminas son las 10 definidas en la ronda anterior, no las locales).
- **Grupos:** `admin1` y `admin2` → grupo `Admin`; `superadmin` es superusuario.
- **`CA 35`:** se crea con ese nombre exacto.
- **Adminer:** el usuario quiere entrar y ver la BD; propone usar `PGADMIN_DEFAULT_EMAIL`/`PGADMIN_DEFAULT_PASSWORD` o, si no, `POSTGRES_USER`/`POSTGRES_PASSWORD`.

### Hechos nuevos
- El `.env` local (`praxsa_manager/.env`, no versionado) contiene las claves `PGADMIN_DEFAULT_EMAIL` y `PGADMIN_DEFAULT_PASSWORD`, pero **ni los `.env-*.example`, ni ningún compose, ni el código las usan** (`git grep PGADMIN` sin resultados). Esas variables son de la imagen **pgAdmin**, no de Adminer.
- **Adminer no tiene usuario/contraseña propios**: la pantalla de login pide servidor, usuario, contraseña y base, y esas credenciales son las de Postgres. Para ver la BD hay que usar `POSTGRES_USER`/`POSTGRES_PASSWORD` (ya presentes en `.env-prod.example:4-5`); `PGADMIN_*` no sirven con Adminer. Si se quisiera pgAdmin en lugar de Adminer, esas variables sí aplicarían (hipótesis, no verificada contra la imagen).
- Con Adminer en `/adminer` detrás de nginx, la BD queda alcanzable por HTTP con las credenciales de Postgres: nada más protege el acceso salvo esas credenciales (y, opcionalmente, un basic auth de nginx — no decidido).
- Conflicto con la nota de roles: `docs` anteriores indican que los grupos locales están duplicados por mayúsculas (`Admin`/`admin`, `Almacen`/`almacen`); el seed nuevo debe crear uno solo de cada (`Admin`, `Almacen`, `Caja`, `Vendedor`) — decisión del usuario en el requerimiento original.
- Copiar el catálogo de la BD local significa que el snapshot depende de ese estado local: las marcas/modelos locales con imagen (145 de 155) enlazan archivos que se cargan con `importar_imagenes_modelos` (`product/seed_data/car_models/`, PR #62), no con el seed.
- Estado de las ambigüedades originales: ya no quedan preguntas de producto abiertas; sí quedan **decisiones de arquitectura** (cómo reemplazar los volúmenes compartidos `static`/`laminas`, base href de `panel_admin` en `/panel`, `/calculadora` limpia vs hash, formato del snapshot, Adminer y su protección, `v2`).

### Decisión del usuario (5ta ronda, 2026-10-02)
Los volúmenes compartidos `static` y `laminas` **ya no son necesarios** en el stack nuevo: los estáticos de Django y el build de `panel_admin` deben llegar a nginx por build de imagen, no por volumen. Se conservan `postgres` y `media` (con sufijo `v2`). El mecanismo exacto (multi-stage vs WhiteNoise, que sería dependencia nueva) queda para arquitectura.

### Preguntas que siguen abiertas
Ninguna de producto bloqueante. Pendientes menores (pueden resolverse en arquitectura/plan): (a) ¿se protege `/adminer` con basic auth de nginx además del login de Postgres?; (b) ¿`quantity` y `date` del inventario? (se asumen 1 y la fecha de ejecución del seed).

## Diseño
No aplica

## Arquitectura
- [ADR-despliegue-nuevo-servidor-inicializacion-db-stack-v2-build-y-enrutamiento](../adr/ADR-despliegue-nuevo-servidor-inicializacion-db-stack-v2-build-y-enrutamiento.md) (Propuesto): stack `docker-compose.v2.yml` aditivo con sufijo `v2`, solo volúmenes `postgres_v2` y `media_v2` creados por el compose; estáticos de Django y build de `panel_admin` horneados en la imagen nginx (multi-stage); nginx único con `/admin`, `/panel`, `/adminer`, `/media`, `/static` y redirección `/calculadora` → `/panel/calculadora`; `apiUrl` relativo; hosts/CSRF/CORS de `settings.py` por variables de entorno con defaults actuales; Adminer con credenciales de Postgres sin puerto publicado; Postgres con versión fija y healthcheck. Descartados: reusar `docker-compose.prod.yml`, WhiteNoise, volumen `static` automatizado, cambiar a rutas sin hash.
- [ADR-despliegue-nuevo-servidor-inicializacion-db-inicializacion-datos-seed](../adr/ADR-despliegue-nuevo-servidor-inicializacion-db-inicializacion-datos-seed.md) (Propuesto): comando `inicializar_datos` manual, idempotente y transaccional (grupos → permisos existentes → sucursales → usuarios → instaladores → catálogo → láminas → bobinas → inventario), catálogo local como snapshot JSON por nombres en `product/seed_data/`, exportado con un comando de desarrollo; `scripts/init-v2.sh` ejecuta `migrate` + seed + `importar_imagenes_modelos`. Descartados: `loaddata`, migración de datos, SQL, entrypoint.
- **Pendiente para el plan:** medir memoria de `web`/`db` (límites 100 MB sin trasladar), definir el entorno de producción de `panel_admin` con `apiUrl` relativo y `--base-href /panel/`, versión de Node requerida por Angular 21, revisar el snapshot del catálogo antes de commitearlo, verificar que `settings.py` con las nuevas variables ausentes se comporta igual que hoy, y verificar el build y los tres caminos (`/admin`, `/panel`, `/adminer`) en Docker (el daemon estuvo apagado en el task anterior).

## Plan
[PLAN-2026-10-02-despliegue-nuevo-servidor-inicializacion-db](../plans/PLAN-2026-10-02-despliegue-nuevo-servidor-inicializacion-db.md) — **v2**. Pendiente de aprobación humana antes de implementar. Incluye 4 supuestos sin confirmar (superadmin en grupo Admin, dirección de instaladores, precios de inventario en 0, Profile vacío).

## Implementación
Implementado según el plan v2. Todos los pasos 1-11 del plan, con verificación propia (no es el Quality Gate: eso es de `delivery-review`).

**Backend (`praxsa_manager/`)**
- `settings.py`: `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` y `CORS_ORIGIN_WHITELIST` por `env.list(..., default=<lista actual>)`. Comprobado que sin las variables las tres listas son idénticas a las de `HEAD`.
- `product/management/commands/exportar_catalogo_seed.py` (nuevo, solo desarrollo) y `product/seed_data/catalogo.json` (33 marcas, 155 modelos, 9 ítems, 12 modelo-ítem, generado desde la BD local; el JSON se escribe con LF y es idéntico entre corridas).
- `product/management/commands/inicializar_datos.py` (nuevo): atómico, idempotente, `--dry-run` (recorre y deshace), `--password` y `--catalogo`; contraseña de `DEFAULT_PASSWORD` (error claro si falta, validada con los validadores de Django, no se imprime). Reutiliza `asignar_permisos_*` vía `call_command`.
- Tests nuevos: `test_inicializar_datos.py` (17) y `test_exportar_catalogo_seed.py` (4).

**Infra:** `Dockerfile.v2` (etapas `backend`, `static`, `panel`; targets `web` y `nginx`), `docker-compose.v2.yml` (`name: praxsa-v2`, solo `postgres_v2` y `media_v2`, sin recursos externos), `nginx/nginx.conf.v2`, `praxsa_manager/.env-v2.example`, `.dockerignore` raíz, `.gitignore` (+`.env-v2`), `.gitattributes` (`*.sh` con LF), `scripts/init-v2.sh`, sección "Despliegue v2" en `README.md`. No se modificó ningún archivo del despliegue actual.

**Frontend (`panel_admin/`):** se quitó `HashLocationStrategy` (rutas sin `#`); `src/environments/environment.prod.ts` con `apiUrl: ''` y `fileReplacements` en `angular.json` (`production`).

**Desvíos menores respecto del plan (no cambian alcance ni riesgo):**
- `.npmrc` de `panel_admin` (`legacy-peer-deps=true`) se copia en la etapa `panel`; sin él `npm ci` falla en Docker por peer deps de `angular-datetime-picker`.
- Se agregó `ENV_FILE` (por defecto `praxsa_manager/.env`) en el compose y en el script, para poder verificar con un env-file desechable sin tocar el `.env` real.
- nginx: `client_max_body_size 10m` (el default de 1 MB rompería subidas de imágenes de hasta 5 MB), `absolute_redirect off` (el puerto publicado por Docker no es el 80 interno) y `/adminer` redirige a `/adminer/?pgsql=db` (Adminer ofrece MySQL por defecto).
- `web` corre como usuario `app` (no root, a diferencia de `Dockerfile.prod`); `media` se crea con ese dueño para que el volumen nuevo sea escribible.
- Los logs de Django quedan dentro del contenedor (no hay tercer volumen).
- `importar_imagenes_modelos` pasa `--dry-run` cuando `scripts/init-v2.sh` recibe `--dry-run`.

**Verificación propia en Docker (daemon disponible):** `docker compose build` OK; `up -d` con los 4 servicios (db `healthy`); `scripts/init-v2.sh` corrido dos veces: la segunda con 0 creados y 95 imágenes omitidas; datos en BD (4 grupos; `superadmin` superusuario con 2 sucursales, `admin1`/`admin2` staff en `Admin`; 2 instaladores; 33/155/9/12; 10 láminas; 2 bobinas 0.5 m/440 y 1 m/880 de 20 m; 4 inventarios de 20 m; 95 modelos con imagen); `/`, `/calculadora`, `/admin`, `/adminer` redirigen como se diseñó; `/admin/login/`, `/static/admin/css/base.css`, `/panel/`, `/panel/calculadora`, `/panel/users` (recarga sin 404), `/product/calculator_info`, `/media/car_models/2.webp` → 200; login del panel (`superadmin`, `admin1`) 200 y clave incorrecta 400; login de Django admin con CSRF OK; login de Adminer con credenciales de Postgres lista las tablas; ningún `.env` dentro de las imágenes (`web` y `nginx`); datos y media sobreviven a `up --force-recreate`; volúmenes creados: solo `postgres_v2` y `media_v2`. Memoria en reposo: `db` ≈71 MiB y `web` ≈68 MiB (por eso no se trasladaron los límites de 100 MB).

**Resultados de las corridas propias:** `manage.py test product` 588 tests OK (+21 nuevos); `makemigrations --check` sin cambios; `ng lint` limpio; `ng build --configuration production --base-href /panel/` OK; `ng test` 456 OK y 13 fallos, todos `should create` de componentes demo de la plantilla (`No provider found for ActivatedRoute`), sin relación con este cambio (el TASK de la calculadora ya documentaba 14 de la misma clase en `master`; no se corrió `master` en esta sesión).

**Pendiente / no verificado:**
- Los 4 supuestos del plan siguen sin confirmar por el usuario (superadmin en `Admin`, dirección de instaladores = la de su sucursal, precios de inventario en 0, `Profile` vacío).
- Sin TLS: Adminer, `/admin` y el panel viajan por HTTP.
- No se probó un despliegue en el servidor real ni con dominio; `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` se verificaron solo con `localhost:8088`.
- Un `.env` con `$` en algún valor (p. ej. el `.env` local de desarrollo) produce avisos de interpolación de compose; documentado en el README (`$$`).
- `ng test` en `master` no se corrió para comparar de forma directa.
- El acceso a Adminer no tiene capa extra (decisión aceptada del ADR).

## Review
_Pendiente_

## Publicación
_Pendiente_
