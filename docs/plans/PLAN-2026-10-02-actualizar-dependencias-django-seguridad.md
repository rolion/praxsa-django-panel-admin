# PLAN-2026-10-02-actualizar-dependencias-django-seguridad (v1)

**Task:** TASK-actualizar-dependencias-django-seguridad
**DDRs relacionados:** Ninguno
**ADRs relacionados:** [ADR-actualizar-dependencias-django-seguridad-ruta-actualizacion](../adr/ADR-actualizar-dependencias-django-seguridad-ruta-actualizacion.md)

## Objective
Cerrar la exposición a vulnerabilidades ya parcheadas subiendo Django a la última 4.2 (4.2.30) y las dependencias de seguridad a su último parche, sin cambiar de plataforma (Etapa A del ADR), y dejar un procedimiento para medir CVE (`pip-audit`).

## Context
Ver TASK-actualizar-dependencias-django-seguridad. Django 4.2 LTS ya no recibe parches (EOL abril 2026) y todos los pins son de 2023. El ADR decide dos etapas: A (parches, esta tarea) y B (Django 5.2 LTS sobre Python 3.12).

**Alcance de este PR/TASK = solo Etapa A.** Razón: `delivery-plan` permite un único PR por task y el ADR exige desplegar A y B por separado. La Etapa B se registra como un TASK propio posterior (ver "Out of scope").

## Current behavior
- `praxsa_manager/requirements-3.8.10.txt:1-31`: pins de mediados de 2023 (Django 4.2.1 en `:6`).
- Python por imagen: `Dockerfile:1` (raíz) y `praxsa_manager/Dockerfile.stg:1` → 3.8; `praxsa_manager/Dockerfile.prod:1` y `Dockerfile.v2:9` → 3.10. Todas instalan ese requirements (`Dockerfile.v2:24`, `Dockerfile.prod:34`, `Dockerfile.stg:32`, `Dockerfile:32`), más `psycopg2-binary` aparte.
- Existe suite de tests en `praxsa_manager/product/tests/` (≈30 archivos). No hay escaneo de CVE.
- Última migración: `0115_client_car_plate.py`.

## Expected behavior
- Django `4.2.30` y dependencias de seguridad en su último parche instalable en **Python 3.8** (la imagen más restrictiva) — mismo archivo de requirements funciona en 3.8 y 3.10.
- Ninguna migración nueva en `product/`; suite verde; `manage.py check` sin errores.
- Existe una guía corta de cómo correr `pip-audit` sobre el requirements.

## Architecture considerations
Resumen del ADR: etapa de parches, sin cambio de runtime, reversible redesplegando la imagen anterior. Puntos propios del plan:
- **Contrato API / datos**: sin cambios esperados; parches dentro de la misma versión mayor/menor. Se comprueba con `makemigrations --check --dry-run`.
- **Dinero**: sin cambios de lógica. Se cubre con los tests existentes de precios/pagos (`test_invoice_pricing.py`, `test_ordenes_price_parity.py`, etc.).
- **Seguridad**: sube Pillow/urllib3/requests/gunicorn/sqlparse/certifi. `bleach` (6.0.0, deprecado upstream) y `martor` solo se suben si hay parche en la misma línea compatible.
- **Dependencias dentro de 3.8**: algunos paquetes ya no publican versiones para 3.8. Regla: tomar la versión más alta que `pip` resuelva bajo 3.8; si un paquete de seguridad queda sin parche posible en 3.8, se documenta y se eleva a la Etapa B en vez de forzar un cambio de Python acá.
- **Rollback**: revertir el PR / redesplegar la imagen anterior (conservar tag antes de desplegar). Sin cambios de esquema, no se requiere restaurar BD.

## Proposed solution
Editar solo `requirements-3.8.10.txt` con las versiones resueltas, validar instalando en un entorno Python 3.8 y 3.10 (Docker), y correr suite + `check`. Agregar un documento breve con el procedimiento `pip-audit`. No tocar Dockerfiles ni settings (la Etapa B lo hace).

## Files/components affected
Backend:
- `praxsa_manager/requirements-3.8.10.txt` (único archivo de código/config modificado).
- `docs/` — nueva nota de procedimiento (p. ej. sección en `docs/deployment-v2.md` "Security checklist", `:219`, o archivo propio si el engineer lo considera mejor).
Frontend: ninguno.

## Implementation steps
1. **Línea base**: en un entorno limpio con el requirements actual, correr `python manage.py test` y registrar el resultado (cuántos tests, cuáles fallan hoy, si alguno). Sin esto no se puede atribuir una falla al cambio.
2. **Medir CVE (antes)**: ejecutar `pip-audit -r praxsa_manager/requirements-3.8.10.txt` (herramienta temporal, fuera del requirements) y guardar la salida en el TASK/PR como evidencia de qué se cierra.
3. **Resolver versiones**: con `docker run python:3.8-alpine` (y `python:3.10-alpine`) resolver la versión más alta instalable de cada paquete desde `pip install --dry-run`/`pip index versions`. Fijar `Django==4.2.30` y las demás; no mover versiones mayores/menores si no hace falta (DRF, django-cors-headers, django-filter, tinymce, etc. solo si el audit lo exige y la línea compatible lo permite).
4. **Editar** `requirements-3.8.10.txt` con esas versiones.
5. **Instalar y verificar** en Python 3.8 y 3.10: `pip install -r` limpio sin conflictos (`pip check`).
6. **Verificar Django**: `python manage.py check`, `python manage.py check --deploy` (solo informativo; no es objetivo cerrar sus warnings), `python manage.py makemigrations --check --dry-run` (debe decir "No changes").
7. **Suite completa**: `python manage.py test`; comparar contra el paso 1.
8. **Build de imágenes**: `docker build` de `Dockerfile.v2` (target `web`), `praxsa_manager/Dockerfile.prod`, `praxsa_manager/Dockerfile.stg` y `Dockerfile` (raíz), confirmando que compilan `psycopg2`/`Pillow` en alpine con las nuevas versiones.
9. **Smoke manual en stack v2** (según memoria del proyecto, las pruebas manuales del admin atrapan errores que la suite no ve): levantar `docker-compose.v2.yml`, entrar al admin, abrir listado/edición de proformas, pagos, inventario, un reporte, subir una imagen de modelo (Pillow) y generar el PDF de proforma (reportlab).
10. **Re-medir CVE (después)** con `pip-audit` y anotar lo que queda abierto y por qué (p. ej. paquete sin parche en 3.8 → Etapa B).
11. **Documentar** el procedimiento `pip-audit` (comando, cadencia sugerida, dónde correrlo).

## Test strategy
- **Unitario/integración (backend)**: no hay lógica de negocio nueva, por lo que no se escriben tests nuevos de negocio; la suite existente (`python manage.py test`) actúa como regresión y es el criterio de aceptación. Comparar contra la línea base del paso 1.
- **Verificación de entorno**: `pip check`, `manage.py check`, `makemigrations --check`, build de las 4 imágenes.
- **Smoke manual** de admin/PDF/imágenes en stack v2 (paso 9).
- **E2E (Playwright)**: **no corresponde.** No cambia ningún flujo ni contrato visible; el cambio es de dependencias de backend y la suite + smoke manual cubren el riesgo real (compatibilidad de librerías). Además Playwright no está instalado y no se justifica agregarlo.
- **Frontend**: sin cambios, sin tests.

## Acceptance criteria
- `requirements-3.8.10.txt` fija `Django==4.2.30`.
- Todas las dependencias de seguridad en la versión más alta instalable en Python 3.8; las que no puedan subirse están listadas con motivo.
- `pip install -r` + `pip check` limpios en Python 3.8 y 3.10.
- `python manage.py test` pasa con el mismo resultado que la línea base (o mejor).
- `makemigrations --check --dry-run` sin cambios; ninguna migración nueva.
- Las 4 imágenes Docker construyen.
- Smoke manual del admin, PDF e imagen de modelo ok en stack v2.
- Salida de `pip-audit` antes/después adjunta al PR.
- Procedimiento `pip-audit` documentado.

## Risks
- Un paquete sin versión para 3.8 impide parchearlo en esta etapa → se documenta y pasa a Etapa B. Mitigación parcial: ya existe la opción de mover stg y root a 3.10 (como prod), pero eso es cambio de plataforma y se decide aparte.
- Cambios de comportamiento en parches de Django 4.2.2…4.2.30 (por ejemplo validaciones más estrictas de entrada) podrían afectar al admin; mitigación: suite + smoke manual. No cuantificado: no se leyeron las notas de release de cada parche en esta sesión.
- Build de `psycopg2`/`Pillow` en alpine puede fallar con versiones nuevas (faltan headers) → se detecta en el paso 8.
- La línea base puede estar ya parcialmente roja; el paso 1 lo expone antes de tocar nada.
- Producción (`Dockerfile.prod`, 3.10) y stg/raíz (3.8) quedan con un mismo requirements pero distinta versión de Python: una versión puede instalar distinto en cada una; por eso el paso 5 prueba ambas.

## Out of scope
- **Etapa B** (Django 5.2 LTS, Python 3.12, unificación de Dockerfiles, paquetes del admin sin soporte declarado): TASK posterior propio.
- Frontend (Angular 16, Node 18, `npm audit`): TASK propio.
- Renombrar `requirements-3.8.10.txt`, hardening de `settings.py` (cookies seguras, HSTS), CORS deprecado (SEC-08).
- **Preguntas abiertas para el usuario:**
  1. ¿Confirmas dividir en dos tasks (este = Etapa A; Etapa B = TASK nuevo)? Si prefieres uno solo, el PR mezcla ambas etapas y se pierde el despliegue independiente.
  2. ¿Qué entornos corren hoy en producción real: `docker-compose.prod.yml` (raíz, Dockerfile.prod/3.10) o `praxsa_manager/docker-compose.prod.yml` (Dockerfile raíz/3.8)? Define qué imagen priorizar en el smoke.

## Dependencias nuevas
- `pip-audit` — herramienta de desarrollo, usada de forma temporal (p. ej. `pipx run pip-audit`), **no** se agrega a `requirements-3.8.10.txt`. Requiere tu confirmación antes de que `delivery-engineer` la instale/ejecute (ejecuta consultas a servicios externos de vulnerabilidades).
