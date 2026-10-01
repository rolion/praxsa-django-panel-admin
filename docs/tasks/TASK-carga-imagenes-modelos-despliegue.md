# TASK-carga-imagenes-modelos-despliegue: Incluir las imágenes de Modelos y `importar_imagenes_modelos` en el proceso de carga de datos al desplegar en Docker

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** NO
**Rama:** task/TASK-carga-imagenes-modelos-despliegue
**Pull Request:** _sin abrir todavía_

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-01 | (nuevo) → INVESTIGATION | Task creado | delivery-investigate |
| 2026-10-01 | ARCHITECTURE → PLANNING | Decisión de distribución de imágenes registrada en ADR | delivery-architect |
| 2026-10-01 | PLANNING → ENGINEERING | Plan v1 listo para aprobación humana | delivery-plan |

## Investigación

### Requerimiento
"La carpeta `media` que tenemos más la función `importar_imagenes_modelos` quiero que sean parte del proceso de carga de DB, o sea poder ejecutarlos en el docker una vez desplegada la aplicación."

Contexto de la conversación previa: se generaron imágenes de ~95 modelos (nombres `Marca - Modelo.jfif/.png`, 1–2 MB c/u) en `praxsa_manager/media/car_models/` del entorno local, y se creó el comando `importar_imagenes_modelos` (que las reduce a WEBP ≤150 KB y las asigna a `Car_Model.image`). Ambos existen solo en el worktree local; nada está commiteado ni desplegado.

### Hechos encontrados
- `praxsa_manager/.gitignore:12` ignora `media` (confirmado con `git check-ignore -v praxsa_manager/media`): la carpeta con las imágenes **no está ni puede estar hoy en git**. El worktree tiene 124 MB en `praxsa_manager/media` (95 originales de 1–2 MB, 121 MB en `car_models/`).
- `praxsa_manager/Dockerfile.prod:13-16` solo copia `praxsa_manager/`, `product/`, `templates/`, `requirements` y `manage.py` a la imagen: `media/` nunca entra a la imagen. El `CMD` (`Dockerfile.prod:44`) es solo `gunicorn`; **no hay entrypoint ni script de arranque** (no hay `*.sh` ni fixtures versionados: `git ls-files` no devuelve ninguno).
- `docker-compose.prod.yml:12` y `:40` montan el volumen Docker `media` (declarado `external: true`, `:99`) en `/praxsa_manager/media`, tanto en `web` como en `nginx`; `nginx/nginx.conf.prod:34-35` sirve `/media/` con `alias /praxsa_manager/media/`. Es decir, la infraestructura de servir imágenes ya existe (ADR-modulo-vehiculos-almacenamiento-imagenes); lo que falta es **cómo llegan los archivos a ese volumen**.
- No existe hoy ningún proceso automatizado de "carga de DB": el `README.md` documenta pasos manuales con `docker exec -it web sh` + `python manage.py migrate` / `createsuperuser` / `collectstatic`. Los comandos de datos existentes (`asignar_permisos_estados`, `asignar_permisos_instalador_precio`, `asignar_permisos_reportes`, en `praxsa_manager/product/management/commands/`) se ejecutan a mano tras desplegar (p. ej. `docs/tasks/TASK-agrupacion-menu-instalador-precio-sucursal.md:133`: "hay que ejecutar `python manage.py asignar_permisos_instalador_precio` en cada ambiente").
- Los modelos de vehículo **no se cargan por migraciones ni fixtures** (las migraciones que tocan `Car_Model` son de esquema); viven en la BD de cada ambiente, así que la carga de imágenes por nombre `Marca - Modelo` depende de que esos nombres coincidan en el ambiente destino.
- `importar_imagenes_modelos` (nuevo, sin commitear) lee por defecto `MEDIA_ROOT/car_models`, empareja por nombre sin distinguir mayúsculas/espacios alrededor de guiones, reemplaza la imagen anterior y no borra los originales. Es idempotente. Simulación contra la BD local: 95/95 archivos emparejados, 60 modelos sin archivo. Tiene 3 tests (`product/tests/test_importar_imagenes_modelos.py`).
- Estado local actual: los 131 modelos con imagen en la BD local apuntan a archivos inexistentes (tras reemplazar archivos a mano); la importación real aún no se ejecutó.
- Producción es el único ambiente Docker activo (stg y dev-Docker dados de baja, `README.md` sección "Variables de entorno"). El volumen `media` es externo y se crea a mano (`ADR-modulo-vehiculos-almacenamiento-imagenes`, "Estrategia de rollback").

### Hipótesis / supuestos no confirmados
- Que los nombres de `Car_Brand`/`Car_Model` en producción sean los mismos que en la BD local (155 modelos) — no verificado; si difieren, los archivos no emparejarán.
- Que el servidor de producción tenga espacio y acceso (SSH/`docker cp`) para subir ~120 MB; no confirmado. Peso real a transportar: si se reduce a WEBP antes, serían ~95 × ≤150 KB ≈ 14 MB (estimación, no medida).
- Que "proceso de carga de DB" signifique un paso manual documentado post-despliegue (como los otros comandos) y no un arranque automático en cada `up`; la frase "poder ejecutarlos en el docker una vez desplegada" sugiere lo primero, pero no está confirmado.
- Que las imágenes finales sean estas 95 (hay 60 modelos sin archivo y se seguirán generando bloques en Gemini): el set aún no es definitivo.

### Módulos y dependencias relacionadas
- Backend: `praxsa_manager/product/models.py:26-35` (`Car_Model.image`, `upload_to='car_models/'`), `product/serializer/vehicle_serializer.py:60-88` (ya borra la imagen anterior al reemplazar), `product/management/commands/` (comandos nuevos y de permisos).
- Infra: `docker-compose.prod.yml`, `praxsa_manager/Dockerfile.prod`, `nginx/nginx.conf.prod`, `README.md`.
- Docs relacionados: `docs/adr/ADR-modulo-vehiculos-almacenamiento-imagenes.md`, `docs/tasks/TASK-imagen-modelo-vehiculo-no-visible.md` (PR #58).

### Implementaciones similares existentes
- Patrón de comando post-despliegue manual e idempotente: los tres `asignar_permisos_*` (con `--dry-run` en el de reportes).
- Patrón de servir `/media/` desde volumen compartido con nginx: ya implementado (ver arriba).
- No hay ningún precedente de distribuir datos binarios (imágenes) junto con la aplicación.

### Comportamiento actual
Tras desplegar, el volumen `media` solo contiene lo que se suba desde el admin; `Car_Model.image` es `null` para modelos nuevos. No existe forma de cargar imágenes masivamente en el servidor; `importar_imagenes_modelos` solo corre contra una carpeta local de la máquina donde se ejecute.

### Restricciones
- `docs/CLAUDE.md`: no agregar dependencias sin avisar (este cambio no las necesita; `requests`/`Pillow` ya están).
- `media` en `.gitignore`: versionar 120 MB de originales en git es costoso (el historial no se puede reducir después); decisión de distribución pendiente de arquitectura.
- El contenedor `web` tiene 100 MB de memoria límite (`docker-compose.prod.yml:21-23`): el comando procesa imágenes de 1–2 MB una por una, pero conviene verificar que Pillow + LANCZOS sobre 2400 px no se acerque al límite — no medido.
- El volumen `media` externo monta encima de `/praxsa_manager/media` de la imagen: cualquier archivo "horneado" en la imagen en esa ruta queda oculto por el volumen (comportamiento estándar de Docker; no se probó aquí).

### Riesgos identificados
- Elegir mal el mecanismo de distribución (git vs. imagen Docker vs. subida manual) puede inflar el repositorio/imagen de forma irreversible.
- Desajuste de nombres entre ambientes: importación parcial silenciosa (el comando ya reporta archivos sin modelo y modelos sin archivo, pero no falla).
- Derechos de uso de las imágenes generadas con IA (originales) vs. las anteriores de Wikimedia (licencias libres con atribución): decisión de negocio, no técnica.
- Sin tests de integración del flujo completo en Docker; solo tests unitarios del comando.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — toca infraestructura de despliegue (cómo llegan ~100+ MB de binarios al volumen `media` de producción y quién/cuándo ejecuta el comando), y hay una decisión con deuda a largo plazo (¿versionar imágenes en git, Git LFS, imagen Docker, artefacto externo?). Es un cambio aditivo y de bajo riesgo funcional, pero la decisión de distribución no es trivial.

### Diseño requerido
**NO** — no agrega ni cambia superficie de UI; es proceso de despliegue y comandos de gestión.

## Diseño
No aplica

## Arquitectura
- [ADR-carga-imagenes-modelos-despliegue-distribucion-imagenes](../adr/ADR-carga-imagenes-modelos-despliegue-distribucion-imagenes.md) (Propuesto): imágenes ya reducidas (WEBP ≤150 KB) versionadas en `praxsa_manager/product/seed_data/car_models/` y copiadas con el `COPY product/` existente; `importar_imagenes_modelos` lee esa carpeta por defecto, no pisa imágenes existentes salvo `--forzar`, y se ejecuta como paso manual post-despliegue (sin entrypoint). Originales (121 MB) fuera de git. Descartados: `docker cp` manual como proceso, Git LFS/artefacto externo, versionar originales, importación automática al arrancar.
- Pendiente para el plan: medir memoria en el contenedor `web` (límite 100 MB), actualizar el README y definir cómo se genera el set reducido desde los originales.

## Plan
[PLAN-2026-10-01-carga-imagenes-modelos-despliegue](../plans/PLAN-2026-10-01-carga-imagenes-modelos-despliegue.md) — **v1**. Pendiente de aprobación humana antes de implementar.

## Implementación
_Pendiente_ (el comando `importar_imagenes_modelos` y sus tests ya existen sin commitear, creados antes de abrir este task)

## Review
_Pendiente_

## Publicación
_Pendiente_
