# to start working as dev
docker-compose -f docker-compose.prod.yml up -d --build
python3 manage.py runserver

# to deploy in stg
docker compose -f docker-compose.stg.yml up -d --build

# to deploy in prod
docker compose -f docker-compose.prod.yml up -d --build

# to deploy in dev 
docker compose -f docker-compose.dev.yml up -d --build

## Variables de entorno

Django siempre lee `praxsa_manager/.env` (nombre fijo, sin importar el ambiente — ver `praxsa_manager/praxsa_manager/settings.py`). Ese archivo **nunca se commitea** (está en `.gitignore`); se crea a mano en cada lugar donde haga falta, a partir de las plantillas `praxsa_manager/.env-dev.example` / `praxsa_manager/.env-prod.example`.

- **Local / dev** (sin Docker, comandos `python`/`ng` directos): copiar `praxsa_manager/.env-dev.example` a `praxsa_manager/.env` y completar los valores reales antes de correr `python manage.py runserver`.
- **Producción** (único ambiente Docker activo hoy — `docker-compose.prod.yml` + `praxsa_manager/Dockerfile.prod`): el `.env` real debe existir en `praxsa_manager/.env` **en el servidor**, con permisos restringidos (`chmod 600`), creado a mano a partir de `praxsa_manager/.env-prod.example`. No se hornea en la imagen: `docker-compose.prod.yml` lo inyecta en runtime al contenedor `web` con `env_file: praxsa_manager/.env`, igual que ya hace con `db`. Sin ese archivo presente **antes** de `docker compose -f docker-compose.prod.yml up -d --build`, el contenedor `web` no arranca.
- El ambiente de stg (`Dockerfile.stg`, `docker-compose.stg.yml`) y el compose de dev vía Docker (`docker-compose.dev.yml`) están dados de baja; sus archivos siguen en el repo como referencia pero no forman parte del despliegue actual.

## Despliegue v2 (servidor nuevo, sin subdominios)

Stack independiente del despliegue actual: `docker-compose.v2.yml` + `Dockerfile.v2` + `nginx/nginx.conf.v2`. Contenedores y volumenes llevan sufijo `_v2` (`db_v2`, `web_v2`, `nginx_v2`, `adminer_v2`, `postgres_v2`, `media_v2`), el propio compose crea red y volumenes (no hay nada `external`) y los estaticos de Django y el build de `panel_admin` viajan **dentro de la imagen de nginx**: reconstruir imagenes ya no requiere destruir volumenes. `proforma/` no forma parte de este stack.

Rutas (todas por el mismo host, por IP o por el dominio que haya despues; sin TLS por ahora):

| Ruta | Sirve |
|---|---|
| `/admin/` | admin de Django |
| `/panel/` | `panel_admin` (administracion; rutas sin `#`) |
| `/calculadora` | redirige a `/panel/calculadora` |
| `/adminer/` | Adminer (login con `POSTGRES_USER` / `POSTGRES_PASSWORD`; las variables `PGADMIN_*` no se usan) |
| `/product/...` | API |

```
# 1. Variables de entorno (una sola vez; el archivo real nunca se commitea)
cp praxsa_manager/.env-v2.example praxsa_manager/.env
#    completar SECRET_KEY, POSTGRES_*, DEFAULT_PASSWORD, ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS, CORS_ORIGIN_WHITELIST
#    si un valor lleva `$`, escribirlo como `$$` (docker compose interpola el env_file)

# 2. Construir y levantar
docker compose -f docker-compose.v2.yml up -d --build

# 3. Inicializacion MANUAL (migrate + datos + imagenes de modelos); nunca corre al construir
./scripts/init-v2.sh              # agregar --dry-run para ver que se crearia sin guardar
```

`scripts/init-v2.sh` es idempotente: se puede repetir sin duplicar datos (`inicializar_datos` solo crea lo que falta). Crea los grupos Admin, Almacen, Caja y Vendedor con sus permisos, las sucursales Santa Cruz y La Paz, los usuarios `superadmin` (superusuario), `admin1` y `admin2` (staff, grupo Admin) con la contrasena de `DEFAULT_PASSWORD`, los instaladores, el catalogo de vehiculos (`product/seed_data/catalogo.json`), 10 laminas y las bobinas/inventario de `CRYSTALLINE-70` (20 m por sucursal). En despliegues posteriores con migraciones nuevas basta `docker compose -f docker-compose.v2.yml exec web python manage.py migrate`.

Para publicar en otro puerto del host: `HTTP_PORT=8088 docker compose -f docker-compose.v2.yml up -d --build`. Para usar otro archivo de variables: `ENV_FILE=ruta/al/.env`.

Importante: sin TLS, el login de Adminer, de `/admin/` y del panel viaja en HTTP plano; restringir el acceso por firewall hasta tener dominio y certificado. Los logs de Django quedan dentro del contenedor (no hay volumen de logs).

### Actualizar el catalogo del seed (desarrollo)

```
cd praxsa_manager
python manage.py exportar_catalogo_seed      # reescribe product/seed_data/catalogo.json desde tu BD local
```
Revisar el diff del JSON antes de commitearlo.

go to praxsa_manager folder

pip install -r requirements-3.8.10.txt

go to proforma folder

npm i

## run praxsa server
python manage.py runserver
## run proforma
npm run dev:ssr

## stop postgre
sudo systemctl stop postgresql

# execute command in container
docker exec -it web sh
# create admin user
python manage.py createsuperuser --username=joe --email=joe@example.com

# to run migration
python manage.py migrate 

# to create static file
python manage.py collectstatic

# chage static file owenership
chown -R app:app /praxsa_manager

## Cargar imagenes de los modelos de vehiculo

Las imagenes de los Modelos viajan dentro de la imagen Docker, ya reducidas (WEBP de hasta 900 px y 150 KB), en `praxsa_manager/product/seed_data/car_models/`, con nombre `Marca - Modelo.webp`. Despues de cada despliegue se cargan con `importar_imagenes_modelos` (paso manual, igual que los demas comandos de datos). Por defecto **no pisa** a los modelos que ya tienen imagen (por ejemplo una subida desde el admin); se puede repetir sin riesgo.

```
# 1. Simular (muestra que se asignaria, los omitidos y los archivos/modelos sin pareja; no guarda nada)
docker exec -it web python manage.py importar_imagenes_modelos --dry-run

# 2. Importar de verdad
docker exec -it web python manage.py importar_imagenes_modelos

# Reemplazar tambien las imagenes que ya existen
docker exec -it web python manage.py importar_imagenes_modelos --forzar
```

Ejecutar siempre primero el `--dry-run` en produccion: si los nombres de marca/modelo difieren de los de `seed_data`, los reporta como "Archivos sin modelo" / "Modelos sin archivo" y no modifica nada de lo no emparejado.

### Agregar o actualizar imagenes del set (desarrollo)

Poner los originales (`.png`, `.jpg`, `.jfif`, `.webp`, nombrados `Marca - Modelo.<ext>`) en una carpeta fuera de git, por ejemplo `praxsa_manager/media/car_models/`, y generar los WEBP reducidos desde `praxsa_manager/`:

```
python manage.py importar_imagenes_modelos --carpeta media/car_models --exportar-a product/seed_data/car_models
```

`--exportar-a` no toca la base de datos. Luego commitear solo los WEBP de `seed_data/` (nunca los originales) y redesplegar. En local, `python manage.py importar_imagenes_modelos` carga el set en tu BD.

Alternativa para modelos sin imagen: `python manage.py precargar_imagenes_modelos` las busca en Wikimedia Commons (fotos con licencia libre) y deja un CSV con la fuente y licencia (`--dry-run`, `--limit N`, `--brand Marca`).

# reset id auto increment
ALTER SEQUENCE auth_permission_id_seq RESTART WITH 125