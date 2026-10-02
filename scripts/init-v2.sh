#!/usr/bin/env bash
# Inicializacion MANUAL del stack v2 (ADR-despliegue-nuevo-servidor-inicializacion-db-inicializacion-datos-seed).
# No corre al construir imagenes ni al arrancar contenedores: se ejecuta a mano, despues de
#   docker compose -f docker-compose.v2.yml up -d --build
# Hace, en orden: migrate -> inicializar_datos -> importar_imagenes_modelos. Es idempotente.
# Los argumentos se pasan a inicializar_datos (p. ej. --dry-run).
set -euo pipefail

cd "$(dirname "$0")/.."

ENV_FILE="${ENV_FILE:-praxsa_manager/.env}"
COMPOSE=(docker compose -f docker-compose.v2.yml)

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: falta $ENV_FILE. Copie praxsa_manager/.env-v2.example a $ENV_FILE y complete los valores." >&2
  exit 1
fi
if ! grep -Eq '^DEFAULT_PASSWORD=.+' "$ENV_FILE"; then
  echo "ERROR: defina DEFAULT_PASSWORD en $ENV_FILE (contrasena de los usuarios del seed)." >&2
  exit 1
fi
if ! "${COMPOSE[@]}" ps --status running --services | grep -qx web; then
  echo "ERROR: el contenedor web no esta corriendo. Ejecute: docker compose -f docker-compose.v2.yml up -d --build" >&2
  exit 1
fi

DRY_RUN=0
for arg in "$@"; do
  [ "$arg" = "--dry-run" ] && DRY_RUN=1
done

echo "==> migrate"
"${COMPOSE[@]}" exec -T web python manage.py migrate --noinput

echo "==> inicializar_datos $*"
"${COMPOSE[@]}" exec -T web python manage.py inicializar_datos "$@"

echo "==> importar_imagenes_modelos"
if [ "$DRY_RUN" = "1" ]; then
  "${COMPOSE[@]}" exec -T web python manage.py importar_imagenes_modelos --dry-run
else
  "${COMPOSE[@]}" exec -T web python manage.py importar_imagenes_modelos
fi

echo "Listo."
