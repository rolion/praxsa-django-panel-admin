# PLAN-2026-10-01-carga-imagenes-modelos-despliegue (v1)

**Task:** TASK-carga-imagenes-modelos-despliegue
**DDRs relacionados:** Ninguno
**ADRs relacionados:** [ADR-carga-imagenes-modelos-despliegue-distribucion-imagenes](../adr/ADR-carga-imagenes-modelos-despliegue-distribucion-imagenes.md), [ADR-modulo-vehiculos-almacenamiento-imagenes](../adr/ADR-modulo-vehiculos-almacenamiento-imagenes.md) (contexto)

## Objective
Poder cargar en producción, con un solo comando ejecutado tras el despliegue, las imágenes de los Modelos de vehículo que viajan dentro de la propia imagen Docker, sin pisar imágenes subidas a mano desde el admin y sin versionar los originales de 121 MB.

## Context
Ver `docs/tasks/TASK-carga-imagenes-modelos-despliegue.md` (investigación) y el ADR de distribución. Resumen: el volumen `media` y nginx ya sirven `/media/`; faltaba cómo llegan los archivos. Se decidió versionar solo WEBP reducidos (≈14 MB) en `product/seed_data/car_models/`, copiarlos con el `COPY product/` existente y cargarlos con `importar_imagenes_modelos` como paso manual post-despliegue.

## Current behavior
- `praxsa_manager/.gitignore:12` ignora `media`; `praxsa_manager/Dockerfile.prod:13-16` solo copia código; no hay entrypoint (`Dockerfile.prod:44`, solo `gunicorn`).
- `Car_Model.image` (`praxsa_manager/product/models.py:29`) solo se llena desde el admin, uno por uno.
- Existen, **sin commitear** (creados en esta misma sesión antes de abrir el task): `product/management/commands/importar_imagenes_modelos.py` (lee `MEDIA_ROOT/car_models`, reemplaza siempre, reduce a WEBP), `product/management/commands/precargar_imagenes_modelos.py` (Wikimedia, aporta `reducir_a_webp`), sus tests (`product/tests/test_importar_imagenes_modelos.py`, `test_precargar_imagenes_modelos.py`, 9 tests en verde) y una sección en `README.md` que documenta el camino manual con `docker cp` (a reemplazar).

## Expected behavior
- Tras `docker compose ... up -d --build`, el contenedor `web` contiene las imágenes reducidas en `/praxsa_manager/product/seed_data/car_models/`.
- `docker exec web python manage.py importar_imagenes_modelos --dry-run` informa qué se asignaría, y sin `--dry-run` lo asigna.
- Por defecto solo asigna a modelos **sin imagen o con archivo inexistente**; `--forzar` reemplaza.
- Volver a ejecutarlo es seguro (idempotente) y no toca imágenes subidas desde el admin.
- Existe un modo para generar el set reducido desde una carpeta de originales (para el desarrollador, no para producción).

## Architecture considerations
Resumen de los ADR (no se re-deriva):
- **Contrato API / datos**: sin cambios; sin migraciones. El serializer ya expone `image` como URL absoluta (`vehicle_serializer.py:60-88`).
- **Infra**: sin cambios de compose/nginx/volúmenes. La carpeta de seed está en la imagen, fuera de `/praxsa_manager/media` (que oculta el volumen). Verificar que `praxsa_manager/.dockerignore` (solo `calculadora13/`, `env/`) no la excluya, y que `.gitignore` no ignore `*.webp` ni `seed_data` (verificado: no ignora).
- **Memoria**: el límite de 100 MB de `web` (`docker-compose.prod.yml:21-23`) aplica al `docker exec`; por eso lo versionado va ya reducido (decodificar WEBP ≤900 px es liviano). Hay que **medirlo** (ver Test strategy).
- **Seguridad/permisos**: comando de consola, solo accesible a quien ya tiene acceso al servidor; sin endpoints nuevos.
- **Rendimiento**: una pasada secuencial sobre ≈155 modelos; sin N+1 relevante (un solo `select_related`).
- **Dinero**: no aplica.
- **Acoplamiento**: el comando solo escribe `Car_Model.image`; `reducir_a_webp` hoy vive en `precargar_imagenes_modelos.py` y `importar_imagenes_modelos.py` lo importa de ahí — moverlo a un módulo compartido evita que un comando dependa de otro.

## Proposed solution
Según el ADR (alternativa B): imágenes reducidas versionadas + `COPY` existente + comando manual idempotente que no pisa por defecto. Se descartaron `docker cp` manual como proceso, Git LFS/artefacto externo, versionar originales e importar automáticamente al arrancar (ver ADR).

## Files/components affected
Backend (`praxsa_manager/`):
- `product/management/commands/importar_imagenes_modelos.py` — carpeta por defecto = seed, `--forzar`, `--exportar-a`, y no pisar por defecto.
- `product/management/commands/precargar_imagenes_modelos.py` — se mantiene; `reducir_a_webp` se mueve a un módulo compartido (p. ej. `product/helper/imagenes.py`) que ambos usan.
- `product/seed_data/car_models/*.webp` — set inicial (≈95 archivos, ≈14 MB).
- `product/tests/test_importar_imagenes_modelos.py`, `test_precargar_imagenes_modelos.py` — ajustes y casos nuevos.
Raíz del repo: `README.md` (reemplazar la sección de `docker cp`). Sin cambios en `Dockerfile.prod`, compose ni nginx. Sin cambios en `proforma/`.

## Implementation steps
1. Mover `reducir_a_webp` (y sus constantes) a `product/helper/imagenes.py`; actualizar los imports de ambos comandos y de sus tests. Los tests existentes deben seguir en verde.
2. En `importar_imagenes_modelos`: cambiar la carpeta por defecto a `product/seed_data/car_models` (ruta calculada desde `Path(__file__)`, no desde `MEDIA_ROOT`); aceptar `.webp` (ya está en las extensiones).
3. Agregar el comportamiento "no pisar por defecto": asignar solo si el modelo no tiene imagen o `image.storage.exists(image.name)` es falso; contar y reportar los "omitidos por tener imagen". Agregar `--forzar` para el comportamiento actual (reemplazar y borrar la anterior).
4. Agregar `--exportar-a DIR`: lee la carpeta de originales (`--carpeta`), escribe los WEBP reducidos como `Marca - Modelo.webp` (nombre canónico del modelo emparejado) en `DIR` sin tocar la BD. Es la forma reproducible de generar el set versionado desde los originales de `media/car_models/`.
5. Generar el set inicial en local con `--exportar-a`, verificar que cada archivo cumple (≤150 KB, 500–900 px de ancho, WEBP) y tamaño total ≈14 MB, y agregarlo a `product/seed_data/car_models/`.
6. Reemplazar la sección del `README.md` por el flujo nuevo (`docker exec web python manage.py importar_imagenes_modelos --dry-run` y luego sin flag; `--forzar`; cómo regenerar el set con `--exportar-a`), y quitar el paso de `docker cp` como proceso principal (puede quedar como nota de emergencia con `--carpeta`).
7. Verificación manual en vivo (ver Test strategy): construir la imagen o ejecutar en un contenedor de prueba local, medir memoria y comprobar que nginx/Django sirven la imagen.

## Test strategy
Unit/integración Django (`praxsa_manager/product/tests/`, `TestCase` con `override_settings(MEDIA_ROOT=tmp)` como los tests actuales):
- Carpeta por defecto: sin `--carpeta`, el comando lee la carpeta de seed (se prueba apuntando `--carpeta` a un directorio temporal y comprobando también el valor por defecto del argumento).
- **No pisa por defecto**: un modelo con imagen existente no cambia (mismo `image.name`); aparece como omitido.
- Un modelo con `image` apuntando a un archivo inexistente **sí** se asigna.
- `--forzar` reemplaza y borra el archivo anterior.
- `--dry-run` no escribe nada (ya existe; mantener).
- `--exportar-a`: escribe `Marca - Modelo.webp` reducido, no modifica la BD, respeta límites de peso/ancho.
- Emparejamiento tolerante (`CHERY -QQ`), archivo sin modelo reportado, transparencia conservada (ya existen; mantener).
- `reducir_a_webp`: tests directos de límites (peso ≤150 KB, ancho entre 500 y 900, imagen muy pequeña → `None`).
- Se corre la suite completa de `product.tests` (cambio de imports no debe romper nada).

**E2E (Playwright): NO corresponde.** No cambia ningún flujo de usuario ni UI, solo un comando de consola y archivos estáticos; no hay navegación ni formulario afectado. Playwright tampoco está instalado en `proforma/package.json` y no se justifica agregarlo.

**Verificación manual en vivo (obligatoria antes de PUBLISH, por el riesgo de memoria y de despliegue):** con el contenedor `web` corriendo con el mismo límite de 100 MB (`docker run --memory 100m` o el compose local), ejecutar el comando con `docker exec` mientras gunicorn atiende y registrar el pico con `docker stats`; luego abrir la URL `/media/car_models/<id>.webp` de un modelo vía nginx. Resultado y medición se anotan en el TASK. Si el pico se acerca al límite, plan B del ADR (`docker compose run` o `--limit`).

## Acceptance criteria
- `python manage.py importar_imagenes_modelos --dry-run` y su ejecución real funcionan dentro del contenedor `web` sin argumentos y cargan el set versionado.
- Un modelo que ya tiene imagen (archivo existente) no se modifica sin `--forzar`; se reporta como omitido.
- El set versionado pesa ≈14 MB en total; cada archivo es WEBP ≤150 KB y 500–900 px de ancho; ningún original (JFIF/PNG de >300 KB) está en git.
- `git status` / `git ls-files` muestran las imágenes; `docker build` las incluye en `/praxsa_manager/product/seed_data/car_models/`.
- El comando se ejecuta sin que el contenedor `web` supere el límite de memoria ni se reinicie (medido, anotado en el TASK).
- El README describe el flujo nuevo y no el de `docker cp`.
- Todos los tests nuevos y existentes de `product.tests` pasan.

## Risks
- **Memoria en `docker exec` (100 MB)**: mitigado por diseño (WEBP ya reducido) y por la medición obligatoria; fallback documentado en el ADR.
- **Crecimiento del repo/imagen (≈14 MB por versión del set)**: aceptado en el ADR; se mitiga haciendo commits del set solo cuando cambia de forma relevante, no por cada imagen suelta.
- **Nombres distintos entre local y producción**: el comando solo reporta (no falla ni modifica lo no emparejado); sin mitigación completa posible sin ver la BD de producción — el `--dry-run` previo en producción es el control.
- **Derechos de uso** de las imágenes generadas con IA: decisión de negocio, ver Out of scope.
- **Dos comandos con lógica compartida**: riesgo de regresión al mover `reducir_a_webp`; cubierto por los tests existentes más los nuevos directos.

## Out of scope
- Generación de las ≈60 imágenes faltantes (se hace aparte en Gemini; el set se amplía después con el mismo flujo).
- Automatizar la ejecución al arrancar el contenedor, entrypoint, Git LFS o almacenamiento externo (descartados en el ADR).
- Quitar el fondo (transparencia) de los `.jfif` generados con IA.
- Cambios de UI, de contrato API, de compose, de nginx o de volúmenes.
- Preguntas abiertas para el usuario: (1) ¿confirmás que los derechos de uso de las imágenes generadas con IA son aceptables para el negocio? (2) ¿versionamos ya el set de 95 o esperamos a completar los ≈155? El plan asume **versionar ya el set actual** y ampliarlo luego con el mismo flujo.

## Dependencias nuevas
Ninguna. `Pillow` y `requests` ya están en `requirements-3.8.10.txt`.
