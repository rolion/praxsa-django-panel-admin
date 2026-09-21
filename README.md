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

# reset id auto increment
ALTER SEQUENCE auth_permission_id_seq RESTART WITH 125