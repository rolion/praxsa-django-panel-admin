# to start working as dev
docker-compose -f docker-compose.prod.yml up -d --build
python3 manage.py runserver

# to deploy in prod
docker compose -f docker-compose.prod.yml up -d --build

# to run migration
python manage.py migrate 

# to create static file
python manage.py collectstatic

# chage static file owenership
chown -R app:app /praxsa_manager