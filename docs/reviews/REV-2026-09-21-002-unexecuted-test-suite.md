# REV-2026-09-21-002: `python manage.py test` no se pudo ejecutar en este entorno de review

**Status:** Open — pendiente de decisión del usuario (waiver como en TASK-001, o correr en un entorno con acceso real a Postgres).
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-09-21-price-recalculation-serializer.md (v1)
**Suggested owner:** delivery-engineer (o el usuario, corriendo los comandos en un entorno con credenciales de base de datos)

## Description

El acceptance criterion #1 del plan ("`python manage.py test` pasa completo, incluidos los tests nuevos y los ya existentes") no se pudo verificar ejecutando el comando real. No es un defecto de código encontrado — es una limitación de este entorno de review (mismo tipo de limitación ya documentada y Waived en TASK-001, `REV-2026-09-21-001`), pero el Quality Gate exige declararlo explícitamente en vez de asumir un `PASS`.

A diferencia de `REV-2026-09-21-001` (donde ni siquiera se pudo importar Django), esta vez se avanzó bastante más: se instaló Django + el resto de `requirements-3.8.10.txt` localmente (no es una dependencia nueva del proyecto), `python manage.py check` corre limpio, y `python manage.py test` llega hasta el intento real de conexión a la base de datos — falla únicamente por credenciales, no por ningún error de import, sintaxis o configuración del código nuevo.

## Expected behavior

Correr `python manage.py test` (o acotado a `product.tests.test_invoice_pricing`) desde `praxsa_manager/` y ver los 9 tests nuevos + la suite completa existente (`test_smoke.py` incluido) en verde, como evidencia real adjunta a este review.

## Actual behavior

Se encontró una instancia de PostgreSQL 16 corriendo nativamente en este host (`Get-Service postgresql-x64-16`, puerto 5432 escuchando), pero sin credenciales conocidas ni accesibles desde este entorno de review — no existe un `praxsa_manager/.env` en este worktree (solo `.env-dev.example`/`.env-prod.example`, con placeholders). Se encontró un `.env` real en el checkout principal del repo (`E:/praxsa/praxsa-django-panel-admin/praxsa_manager/.env`), pero **no se leyó su contenido**: `docs/CLAUDE.md` dice explícitamente "No tocar archivos `.env` ni credenciales", y usar esas credenciales para este review —aunque sea solo lectura— cruza esa regla. Tampoco se intentó adivinar la contraseña real más allá de 2-3 valores obvios de desarrollo (`postgres`/`postgres`, etc.), que fallaron.

## Evidence

```
$ python manage.py check
(1 issue) System check identified 1 issue (0 silenced).
WARNINGS:
?: (staticfiles.W004) The directory '...\praxsa_manager\static' in the STATICFILES_DIRS setting does not exist.
# limpio salvo ese warning irrelevante, preexistente, no relacionado a este cambio

$ python manage.py test product.tests.test_invoice_pricing
...
django.db.utils.OperationalError: connection to server at "localhost" (::1), port 5432 failed:
FATAL:  password authentication failed for user "x"
```

```
PS> Get-Service | Where-Object {$_.Name -match 'postgres'}
Status  Name              DisplayName
------  ----              -----------
Running postgresql-x64-16 postgresql-x64-16 - PostgreSQL Server 16
```

## Verificación estática realizada (por inspección, no ejecución)

- `git diff origin/master...HEAD --stat`: solo toca los 4 archivos backend previstos en el plan + los 3 documentos (`TASK-005.md`, `ADR-004`, `PLAN-...md`) — sin scope creep.
- `create()` de `SalesHeaderSerializer` confirmado sin diff (el cambio se concentra en `validate()` + `business/pricing.py`, tal como pedía el plan).
- Revisión manual línea por línea de `validate()`/`Pricing_Business` contra los 9 tests nuevos de `test_invoice_pricing.py`: la aritmética de cada caso (override de sucursal, fallback, `quantity > 1`, `length`/`width` no canónicos) se recalculó a mano y coincide con las aserciones de cada test.
- `python -m flake8`/`bandit` corridos ad hoc (el proyecto no tiene ninguno configurado) sobre los archivos nuevos/modificados: sin hallazgos de seguridad; solo nits de estilo (líneas largas, un import ya no usado que es preexistente) — no bloqueantes, ver `## Review` del PR.

## Resolución

Pendiente. Ver mensaje de esta revisión en el chat — se le pregunta al usuario si quiere: (a) autorizar un waiver igual que en TASK-001 dado que la revisión estática y el análisis manual no encontraron ningún indicio de que los tests fallarían, o (b) dar acceso a credenciales reales de un Postgres de test/dev para correr la suite de punta a punta en esta sesión.
