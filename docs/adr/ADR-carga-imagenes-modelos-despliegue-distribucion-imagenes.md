# ADR-carga-imagenes-modelos-despliegue-distribucion-imagenes: Las imágenes de Modelos viajan versionadas en la imagen Docker (ya reducidas) y se cargan con `importar_imagenes_modelos` como paso manual post-despliegue

**Estado:** Propuesto
**Task relacionado:** TASK-carga-imagenes-modelos-despliegue
**Fecha:** 2026-10-01

## Contexto

Se quiere poder cargar en producción las imágenes de los Modelos de vehículo con el comando `importar_imagenes_modelos`, "una vez desplegada la aplicación". La investigación dejó estos hechos:

- `media` está en `praxsa_manager/.gitignore:12` y `Dockerfile.prod` solo copia `praxsa_manager/`, `product/`, `templates/`, `requirements` y `manage.py`: las imágenes no llegan a producción por ningún camino hoy.
- El volumen `media` es externo y se monta encima de `/praxsa_manager/media` en `web` y `nginx` (`docker-compose.prod.yml:12,40`); nginx ya sirve `/media/`. Cualquier archivo puesto en esa ruta dentro de la imagen queda oculto por el volumen.
- No hay entrypoint ni proceso de carga automático; los comandos de datos existentes (`asignar_permisos_*`) se ejecutan a mano con `docker exec` tras desplegar.
- Los originales locales pesan 121 MB (1-2 MB c/u, JPEG sin transparencia); ya reducidos a WEBP (≤150 KB) serían ≈14 MB (estimación).
- El contenedor `web` tiene límite de 100 MB de memoria (`docker-compose.prod.yml:21-23`), compartido con gunicorn si el comando se ejecuta con `docker exec`.
- El comando actual **reemplaza** la imagen de cada Modelo emparejado, lo que en producción pisaría imágenes que alguien haya subido a mano desde el admin.

## Decisión

1. **Se versionan en git solo las imágenes ya reducidas** (WEBP ≤150 KB, ancho ≤900 px, nombre `Marca - Modelo.webp`) en una carpeta no ignorada dentro del código, p. ej. `praxsa_manager/product/seed_data/car_models/`, y se copian a la imagen con el `COPY product/ ./product` que ya existe. **Los originales de 1-2 MB nunca entran a git ni a la imagen.** La ruta queda fuera de `/praxsa_manager/media`, por lo que el volumen no la oculta.
2. **El comando lee por defecto esa carpeta** (hoy lee `MEDIA_ROOT/car_models`); `--carpeta` sigue permitiendo otra ruta. Escribe en el volumen `media` a través de `Car_Model.image`, igual que una subida desde el admin, y nginx lo sirve sin cambios.
3. **Se ejecuta como paso manual documentado tras cada despliegue** (`docker exec web python manage.py importar_imagenes_modelos`), igual que los otros comandos de datos. **No se ejecuta automáticamente al arrancar el contenedor** (no se agrega entrypoint).
4. **Por defecto no pisa imágenes existentes**: solo asigna a los Modelos sin imagen o cuyo archivo ya no existe en el volumen; el reemplazo requiere un flag explícito (`--forzar`). Así volver a correr el comando tras un despliegue no deshace lo que se subió desde el admin.
5. Se agrega una forma de **preparar** el set reducido desde los originales en la máquina del desarrollador (p. ej. una opción del mismo comando que escribe los WEBP reducidos en la carpeta de seed en vez de la BD); el detalle es de `delivery-plan`.

## Alternativas consideradas

- **A. Subida manual con `docker cp` a un volumen y ejecutar el comando (lo que dice hoy el README).** Cero cambios de infra y cero peso en git, pero el paso es manual, depende de que alguien tenga la carpeta correcta, no es reproducible ni versionado, y subiría 121 MB de originales. Válida como mecanismo de emergencia, no como proceso de carga.
- **B (elegida). Imágenes reducidas versionadas + `COPY` existente.** Reproducible, versionado y revisable en PR; ≈14 MB de crecimiento del repositorio y de la imagen, acotado. Costo: cada cambio del set agrega ese orden de tamaño al historial git; se acepta porque el set es chico y estable.
- **C. Git LFS o un artefacto externo (S3, release de GitHub).** Evita inflar el historial, pero introduce infraestructura nueva (LFS, credenciales, descarga en el despliegue) para ≈14 MB. Es sobreingeniería a este tamaño.
- **D. Versionar los originales de 121 MB.** Descartada: el historial git no se puede reducir después y los originales no hacen falta en producción.
- **E. Ejecutar la importación automáticamente al arrancar (entrypoint).** Descartada: el proyecto no tiene entrypoint, acopla el arranque del servicio a una tarea de CPU/memoria bajo un límite de 100 MB, y un fallo retrasaría o tumbaría el `web`. Un paso manual es consistente con cómo se opera hoy.

## Estrategia de rollback / mitigación

- **Cambio aditivo**: agregar archivos, un `COPY` ya existente y un comando; no hay migración ni cambio de contrato API. Revertir el PR y redesplegar deja el sistema como estaba; las imágenes ya asignadas siguen en el volumen `media` (no se pierden ni rompen nada) y pueden eliminarse desde el admin si se quisiera.
- **Riesgo operativo principal: memoria del contenedor `web` (100 MB) al ejecutar con `docker exec`.** Mitigado por diseño: como lo versionado ya está reducido (WEBP ≤900 px), el procesamiento en producción es liviano (decodificar un WEBP pequeño), a diferencia de procesar JPEG de 2400 px. `delivery-plan` debe medir el pico de memoria en una prueba antes de PUBLISH; si aun así fuera un riesgo, ejecutar fuera del contenedor `web` en ejecución (`docker compose run`) o por tandas (`--limit`).
- **Riesgo de pisar imágenes subidas a mano**: mitigado por la decisión 4 (no reemplaza por defecto) y por el `--dry-run`, que debe ejecutarse primero en producción.
- **Desajuste de nombres entre ambientes**: el comando ya reporta archivos sin modelo y modelos sin archivo; no falla ni modifica nada de lo no emparejado. Es solo una mitigación informativa: no hay forma de garantizarlo sin consultar la BD de producción.

## Consecuencias

- Las imágenes pasan a formar parte del artefacto desplegable: todo despliegue que incluya el set las trae, y la carga es un solo comando repetible.
- La imagen Docker crece ≈14 MB y el repositorio, lo mismo por cada versión del set; se acepta conscientemente.
- Queda pendiente de negocio (fuera de esta decisión): los derechos de uso de las imágenes generadas con IA, y si el set de 95 es el definitivo (faltan ≈60 modelos).
- El README debe actualizarse (hoy documenta el camino A con `docker cp`) para describir el nuevo flujo; es trabajo de `delivery-plan`/`delivery-engineer`.
- No se agregan dependencias (`docs/CLAUDE.md`).
