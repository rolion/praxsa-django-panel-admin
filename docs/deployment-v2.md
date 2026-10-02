# Deploying the v2 stack to production

Step-by-step guide for the v2 Docker stack (`docker-compose.v2.yml`). Commands are given for **Linux/macOS (bash)** and **Windows (PowerShell)**.

What you get (one host, one port, no subdomains):

| Path | Serves |
|---|---|
| `/panel/` | Admin panel (`panel_admin`) |
| `/calculadora` | Redirects to `/panel/calculadora` (price calculator) |
| `/admin/` | Django admin |
| `/adminer/` | Adminer (database browser) |
| `/product/...` | REST API |
| `/static/`, `/media/` | Static files and uploaded images |

Containers: `db_v2` (PostgreSQL 16), `web_v2` (Django + gunicorn), `nginx_v2` (reverse proxy, panel and static files), `adminer_v2`. Persistent data lives in two named volumes only: `postgres_v2` (database) and `media_v2` (uploaded images). Rebuilding images never requires deleting volumes.

> **No TLS yet.** This version serves plain HTTP. Passwords (panel, Django admin, Adminer) travel unencrypted. Restrict access with a firewall until you have a domain and a TLS terminator in front of nginx.

## 1. Prerequisites

- **Linux:** Docker Engine 24+ with the Compose plugin (`docker compose version`), `git`, `bash`. Open the HTTP port (default 80) in the firewall.
- **Windows:** Docker Desktop (Linux containers), `git` for Windows (it ships Git Bash, needed for `scripts/init-v2.sh`), PowerShell.
- ~4 GB of free disk and internet access for the first build (Python, Node and Docker base images are downloaded).

## 2. Get the code

```bash
# Linux / macOS
git clone https://github.com/rolion/praxsa-django-panel-admin.git
cd praxsa-django-panel-admin
git checkout <branch-or-tag-to-deploy>
```

```powershell
# Windows (PowerShell)
git clone https://github.com/rolion/praxsa-django-panel-admin.git
cd praxsa-django-panel-admin
git checkout <branch-or-tag-to-deploy>
```

All commands below are run from the repository root.

## 3. Create the environment file

The real file is **never committed** (it is git-ignored). Start from the template:

```bash
# Linux / macOS
cp praxsa_manager/.env-v2.example praxsa_manager/.env
chmod 600 praxsa_manager/.env
```

```powershell
# Windows (PowerShell)
Copy-Item praxsa_manager\.env-v2.example praxsa_manager\.env
```

Edit `praxsa_manager/.env` and replace every `change-me`:

| Variable | What to put |
|---|---|
| `ENV` | `PROD` |
| `DEBUG` | `0` |
| `SECRET_KEY` | A long random value, unique per environment (see below). Avoid `$` characters. |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Database credentials. They are applied only when the `postgres_v2` volume is created the first time. |
| `DB_HOST` | **`db`** (the Compose service name — not `localhost`) |
| `DB_PORT` | `5432` |
| `DEFAULT_PASSWORD` | Password for the seeded users `superadmin`, `admin1`, `admin2`. Must pass Django's password rules (8+ characters, not common, not only digits). |
| `ALLOWED_HOSTS` | Comma-separated: `localhost,127.0.0.1,web,nginx,<server-ip-or-domain>` |
| `CSRF_TRUSTED_ORIGINS` | With scheme, e.g. `http://203.0.113.10` (add the port if not 80, e.g. `http://203.0.113.10:8080`) |
| `CORS_ORIGIN_WHITELIST` | Same value as `CSRF_TRUSTED_ORIGINS` |

Generate a `SECRET_KEY`:

```bash
# Linux / macOS
python3 -c "import secrets; print(secrets.token_urlsafe(60))"
```

```powershell
# Windows (PowerShell)
$b = New-Object byte[] 48; [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b); [Convert]::ToBase64String($b)
```

Docker Compose interpolates `$` in env files. If any value contains a `$`, write it as `$$`.

## 4. Build and start

```bash
# Linux / macOS
docker compose -f docker-compose.v2.yml up -d --build
docker compose -f docker-compose.v2.yml ps
```

```powershell
# Windows (PowerShell)
docker compose -f docker-compose.v2.yml up -d --build
docker compose -f docker-compose.v2.yml ps
```

The first build takes several minutes (Angular build). Wait until `db_v2` is `healthy` and all four containers are `Up`.

To publish on a port other than 80:

```bash
# Linux / macOS
HTTP_PORT=8080 docker compose -f docker-compose.v2.yml up -d --build
```

```powershell
# Windows (PowerShell)
$env:HTTP_PORT = "8080"
docker compose -f docker-compose.v2.yml up -d --build
```

To use an env file other than `praxsa_manager/.env`, set `ENV_FILE` the same way (`ENV_FILE=path/to/file` in bash, `$env:ENV_FILE = "path\to\file"` in PowerShell). Set the variables again in every new shell, and use the same values for every later `docker compose` command (otherwise Compose falls back to the defaults).

## 5. Initialize the database (manual, run once)

This applies migrations, seeds roles, branches, users, installers, the vehicle catalog, window films, reels and inventory, and imports the model images. It is **never** run automatically when images are built. It is idempotent: running it again does not duplicate data.

```bash
# Linux / macOS
./scripts/init-v2.sh              # add --dry-run to preview without saving
```

```powershell
# Windows (PowerShell) — the script needs bash; use the one from Git for Windows
& "C:\Program Files\Git\bin\bash.exe" scripts/init-v2.sh
```

If you prefer not to use bash on Windows, run the three steps directly (same result):

```powershell
docker compose -f docker-compose.v2.yml exec -T web python manage.py migrate --noinput
docker compose -f docker-compose.v2.yml exec -T web python manage.py inicializar_datos
docker compose -f docker-compose.v2.yml exec -T web python manage.py importar_imagenes_modelos
```

The script aborts with a clear message if the env file is missing, `DEFAULT_PASSWORD` is not set, or `web_v2` is not running.

Seeded accounts (password = your `DEFAULT_PASSWORD`): `superadmin` (superuser, both branches), `admin1` (Santa Cruz) and `admin2` (La Paz), all staff in the `Admin` group. **Change these passwords after the first login** (panel > Users) and consider removing `DEFAULT_PASSWORD` from the env file once seeding is done (it is only needed for `init-v2.sh`).

## 6. Verify

Open (replace the host/port):

- `http://<server>/panel/` — log in with `superadmin`
- `http://<server>/calculadora` — should redirect to `/panel/calculadora` and list branches and brands
- `http://<server>/admin/` — Django admin
- `http://<server>/adminer/` — System `PostgreSQL`, server `db`, user/password/database from `POSTGRES_*`

Quick command-line check:

```bash
# Linux / macOS
curl -I http://localhost/panel/ http://localhost/admin/login/
```

```powershell
# Windows (PowerShell)
curl.exe -I http://localhost/panel/
curl.exe -I http://localhost/admin/login/
```

## 7. Updating a running deployment

```bash
# Linux / macOS
git pull
docker compose -f docker-compose.v2.yml up -d --build
docker compose -f docker-compose.v2.yml exec web python manage.py migrate --noinput
```

```powershell
# Windows (PowerShell)
git pull
docker compose -f docker-compose.v2.yml up -d --build
docker compose -f docker-compose.v2.yml exec web python manage.py migrate --noinput
```

No volume has to be removed. Only run `init-v2.sh` again if you need the seed data re-applied (it only creates what is missing).

## 8. Logs, stop, backups

```bash
# Linux / macOS
docker compose -f docker-compose.v2.yml logs -f web nginx   # follow logs
docker compose -f docker-compose.v2.yml down                # stop, keep data
docker compose -f docker-compose.v2.yml down -v             # stop AND delete the database and uploaded images
docker compose -f docker-compose.v2.yml exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > backup.sql
```

```powershell
# Windows (PowerShell)
docker compose -f docker-compose.v2.yml logs -f web nginx
docker compose -f docker-compose.v2.yml down
docker compose -f docker-compose.v2.yml down -v      # deletes the database and uploaded images
# Backup: run the pg_dump line above from Git Bash (PowerShell 5.1's ">" would write UTF-16)
```

Django application logs stay inside the `web_v2` container (there is no logs volume).

## 9. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `connection to server at "localhost" ... Connection refused` when migrating | `DB_HOST` is `localhost`; set `DB_HOST=db` and recreate: `docker compose -f docker-compose.v2.yml up -d --force-recreate web` |
| Changed the env file but nothing changed | Containers read the env file when they are created: recreate them (`--force-recreate`). Check with `docker compose -f docker-compose.v2.yml exec web printenv DB_HOST` |
| `Invalid HTTP_HOST header` / 400 | Add the host you browse to in `ALLOWED_HOSTS` |
| `CSRF verification failed` on login | Add the full origin (with `http://` and port) to `CSRF_TRUSTED_ORIGINS` |
| `init-v2.sh` says `DEFAULT_PASSWORD` is missing or the password is rejected | Set a value that passes Django's password rules in the env file |
| Warnings like `The "i1" variable is not set` | A `$` in an env value; write it as `$$` |
| Port already in use | Publish on another port with `HTTP_PORT` |
| Uploads fail | The proxy accepts bodies up to 10 MB; images are limited to 5 MB by the application |
| `scripts/init-v2.sh` fails with `\r` errors on Windows | Make sure the file has LF line endings (the repo's `.gitattributes` enforces this on checkout) |

## 10. Security checklist

- Strong, unique `SECRET_KEY`, `POSTGRES_PASSWORD` and `DEFAULT_PASSWORD`; the env file has restricted permissions and is never committed.
- Change the seeded users' passwords after the first login.
- Adminer exposes the whole database at `/adminer/`: limit access by firewall/VPN, or block the path in `nginx/nginx.conf.v2` if you do not need it.
- Add TLS (a TLS-terminating proxy in front of nginx that sets `X-Forwarded-Proto: https`) as soon as you have a domain, then use `https://` origins in `CSRF_TRUSTED_ORIGINS`.
- The PostgreSQL port is not published to the host; only nginx (HTTP port) is reachable from outside.
- Dependency vulnerabilities: periodically (e.g. monthly and before each release) audit the pinned packages from a throwaway environment, without adding the tool to the requirements: `pipx run pip-audit -r praxsa_manager/requirements-3.8.10.txt`. Update the pins in that file and rebuild the images; see `docs/adr/ADR-actualizar-dependencias-django-seguridad-ruta-actualizacion.md` for the upgrade path.
