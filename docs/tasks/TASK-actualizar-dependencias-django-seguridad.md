# TASK-actualizar-dependencias-django-seguridad: Actualizar Django y dependencias con observaciones de seguridad

**Etapa actual:** PLANNING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** NO
**Rama:** task/TASK-actualizar-dependencias-django-seguridad
**Pull Request:** _sin abrir todavía_

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-02 | (nuevo) → INVESTIGATION | Task creado | delivery-investigate |
| 2026-10-02 | ARCHITECTURE → PLANNING | ADR de ruta de actualización (4.2.30 y luego 5.2 LTS sobre Python 3.12) registrado | delivery-architect |
| 2026-10-02 | PLANNING → PLANNING | Plan v1 escrito y PR abierto; espera confirmación del usuario (alcance Etapa A, entorno de producción real) antes de pasar a ENGINEERING | delivery-plan |

## Investigación

### Requerimiento
El usuario recuerda que en una conversación anterior se mencionaron "observaciones de seguridad respecto a Django" y pregunta si falta actualizar algún componente.

### Hechos encontrados
- `praxsa_manager/requirements-3.8.10.txt:6` — `Django==4.2.1` (fijado; el nombre del archivo y la fecha son de 2023). Todas las dependencias están pinneadas a versiones de mediados de 2023 (`:1-31`): `djangorestframework==3.14.0` (:15), `gunicorn==20.1.0` (:16), `Pillow==10.0.1` (:21), `requests==2.31.0` (:25), `urllib3==2.0.3` (:29), `certifi==2023.5.7` (:4), `sqlparse==0.4.4` (:28), `django-cors-headers==4.0.0` (:11), `bleach==6.0.0` (:3), `reportlab==4.0.5` (:24), `martor==1.6.26` (:20), `Markdown==3.3.4` (:19).
- Búsqueda web (2026-10-02): la rama Django 4.2 LTS terminó soporte en abril de 2026; su último release es 4.2.30 ([HeroDevs](https://www.herodevs.com/blog-posts/django-4-2-is-reaching-end-of-life), [endoflife.ai](https://endoflife.ai/django/4.2)). Ramas con soporte: 5.2 LTS (hasta abril 2028) y 6.0 (hasta abril 2027) ([djangoproject.com](https://www.djangoproject.com/download/)). Es decir: el proyecto está en una versión **sin parches de seguridad** y además 29 releases de parche por detrás de la última 4.2.
- `docs/backend-audit.md:43,59` — la auditoría registró `Django 4.2.1` como versión del proyecto, pero ninguno de los hallazgos SEC-01..SEC-10 (`:409-479`) trata de versiones de dependencias. Tampoco el backlog (`docs/integration-and-backlog.md:134-290`, ítems 1-10, todos HECHO salvo #3 y #9 parcial) incluye "actualizar Django/dependencias". Hallazgo: **la actualización de componentes no está cubierta por ningún ítem existente**.
- Runtime Python inconsistente entre Dockerfiles: `Dockerfile:1` (raíz del repo; lo usa `praxsa_manager/docker-compose.prod.yml:7`) y `praxsa_manager/Dockerfile.stg:1` usan `python:3.8-alpine`; `praxsa_manager/Dockerfile.prod:1` (usado por `docker-compose.prod.yml:8`) y `Dockerfile.v2:9` (usado por `docker-compose.v2.yml:29`) usan `python:3.10-alpine`. Django 5.2 requiere Python ≥ 3.10 (conocimiento general, no verificado en esta sesión), por lo que las imágenes de 3.8 no podrían correr Django 5.x.
- Los cuatro Dockerfiles instalan desde `requirements-3.8.10.txt` (`Dockerfile.v2:24`, `Dockerfile.prod:34`, `Dockerfile.stg:32`, `Dockerfile:32`).
- `praxsa_manager/praxsa_manager/settings.py:226` — único flag de endurecimiento HTTPS: `SECURE_PROXY_SSL_HEADER`. No hay `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_HSTS_*` (grep sin coincidencias). `docs/deployment-v2.md:18,224` documenta que v2 corre sin TLS por ahora.
- `praxsa_manager/praxsa_manager/settings.py:118` — `CSRF_COOKIE_HTTPONLY = False`, con comentario "default" (consistente con el default de Django).
- Frontend: `proforma/package.json` — `@angular/core ^16.1.0`, `@angular/cli ~16.1.1`; `proforma/Dockerfile.prod:2,23` y `Dockerfile.stg:2` usan `node:18.16`. `docs/tasks/TASK-003.md:80` y `docs/tasks/TASK-almacen-permisos-sucursal-filtros.md:148` ya registran `npm audit` con 79-109 vulnerabilidades (en su mayoría devDependencies) y 3 en dependencias de producción (echarts, lodash), declaradas "preexistentes, fuera de alcance".
- Verificación de seguridad automatizada: `bandit`/`safety`/`pip-audit` no están instalados ni configurados (`docs/tasks/TASK-009.md:155`, `TASK-010.md:113`). Nunca se ha corrido un escaneo de CVE sobre `requirements-3.8.10.txt`.
- Última migración: `praxsa_manager/product/migrations/0115_client_car_plate.py`.

### Hipótesis / supuestos no confirmados
- Que "las observaciones de seguridad respecto a Django" que recuerda el usuario sean esta (Django 4.2 fuera de soporte + pins de 2023). No encontré en el repo una conversación previa; las únicas observaciones documentadas son SEC-01..SEC-10 del `backend-audit.md`, ya resueltas. Hay que confirmar con el usuario si recuerda algo distinto.
- Los CVE concretos afectando `Django 4.2.1`, `Pillow 10.0.1`, `gunicorn 20.1.0`, `requests 2.31.0`, `urllib3 2.0.3`, `sqlparse 0.4.4`, `certifi`, `reportlab`, `bleach`, `martor` **no se enumeraron** en esta sesión (sin `pip-audit` disponible). Que existan parches posteriores a esas versiones es muy probable pero no está verificado paquete por paquete.
- Compatibilidad con Django 5.2 de `django-admin-logs 1.2.0`, `django-admin-list-filter-dropdown 1.0.3`, `django-admin-rangefilter 0.12.4`, `django-bootstrap-v5 1.0.11`, `django-tinymce 3.6.1`, `martor 1.6.26`: no verificada. Son los candidatos de mayor riesgo de ruptura.
- Qué entorno (prod actual, stg, v2) corre realmente con qué Dockerfile: no confirmado.
- Los cambios de comportamiento/deprecaciones entre 4.2 → 5.2 que afecten al código propio (p. ej. `ModelAdmin`, `STORAGES`, `index_together`) no se auditaron.

### Módulos y dependencias relacionadas
- Backend: `praxsa_manager/requirements-3.8.10.txt`, `praxsa_manager/praxsa_manager/settings.py` (INSTALLED_APPS con `martor`, `tinymce`, `rangefilter`, `django_filters`, `corsheaders`, `rest_framework.authtoken`), los 4 Dockerfiles, `docker-compose*.yml`, `scripts/init-v2.sh`.
- Toda la capa `product/admin_config/` depende de APIs de `ModelAdmin` que cambian entre versiones.
- Frontend: `proforma/package.json`, `proforma/Dockerfile.*`; panel Angular (`Dockerfile.v2:42`, `node:22-alpine`).

### Implementaciones similares existentes
- No hay precedente de actualización de dependencias en `docs/adr/` ni `docs/tasks/`. Patrón a reutilizar: `docs/deployment-v2.md` (imágenes versionadas, volúmenes persistentes) para probar la actualización en un entorno aparte sin tocar el productivo.

### Comportamiento actual
El backend corre con Django 4.2.1 y dependencias de 2023 sobre Python 3.8/3.10 según el entorno. No hay mecanismo de detección de CVE ni cadencia de actualización. La suite de tests existe desde TASK-009/010 (`python manage.py test`), lo que da algo de red de seguridad para validar una subida de versión.

### Restricciones
- `docs/CLAUDE.md`: "No agregar dependencias sin avisar antes" (esta tarea cambia versiones, no agrega paquetes, pero conviene avisar); "No editar migraciones ya aplicadas"; "No tocar archivos `.env`"; cambios pequeños y un objetivo por PR; proponer plan antes de cambios multi-archivo.
- Una migración mayor de framework suele obligar a revisar migraciones generadas (`makemigrations --check`).

### Riesgos identificados
- Producción en versión sin soporte de seguridad: riesgo vigente y creciente.
- Salto 4.2 → 5.2 cruza una versión mayor: posibles rupturas en librerías de terceros del admin y en deprecaciones.
- Python 3.8 (stg y `Dockerfile` raíz) impide Django 5.x; hay que unificar el runtime.
- Nombre del archivo `requirements-3.8.10.txt` fijo en 4 Dockerfiles: renombrarlo implica tocarlos todos.
- Sin escáner de CVE, no hay forma objetiva de priorizar el resto de paquetes.
- Angular 16 y Node 18 también fuera de soporte (hecho de calendario general, no verificado en esta sesión), con `npm audit` ya reportando altas en producción.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — Cambio de versión mayor de framework, de runtime Python y de dependencias que impacta todos los módulos y la infraestructura (Dockerfiles, despliegue); requiere decidir ruta (4.2→5.2 LTS vs 6.0), estrategia de rollback y orden de PRs.

### Diseño requerido
**NO** — Cambio puramente de backend/infraestructura, sin superficie de UI nueva.

## Diseño
_No aplica_

## Arquitectura
- [ADR-actualizar-dependencias-django-seguridad-ruta-actualizacion](../adr/ADR-actualizar-dependencias-django-seguridad-ruta-actualizacion.md) — dos etapas: (A) Django 4.2.30 + parches de dependencias sin cambiar plataforma; (B) Django 5.2 LTS sobre Python 3.12 con validación en stack v2. Rollback por PR revertible, imágenes con tag y `pg_dump` previo.

## Plan
- [PLAN-2026-10-02-actualizar-dependencias-django-seguridad](../plans/PLAN-2026-10-02-actualizar-dependencias-django-seguridad.md) (v1) — alcance: solo Etapa A del ADR (Django 4.2.30 + parches). Etapa B (Django 5.2 / Python 3.12) = TASK posterior. Pendiente de confirmación del usuario (2 preguntas abiertas en el plan).

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
