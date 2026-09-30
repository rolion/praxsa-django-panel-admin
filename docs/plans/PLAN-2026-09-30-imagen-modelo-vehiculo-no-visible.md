# PLAN-2026-09-30-imagen-modelo-vehiculo-no-visible (v1)

**Task:** TASK-imagen-modelo-vehiculo-no-visible
**DDRs relacionados:** Ninguno
**ADRs relacionados:** [ADR-modulo-vehiculos-almacenamiento-imagenes](../adr/ADR-modulo-vehiculos-almacenamiento-imagenes.md) (se respeta, no se modifica)

## Objective
Que la imagen del Modelo se vea en el listado y en la vista de Modelo cuando el archivo existe, y que cuando no se pueda cargar se muestre el placeholder existente en vez de un `<img>` roto. Además, que la URL emitida por la API sea `https` detrás de nginx.

## Context
Ver `docs/tasks/TASK-imagen-modelo-vehiculo-no-visible.md`. Causa confirmada en dev: las 2 filas con imagen (CR-V, A1) apuntan a archivos que no existen en ningún `MEDIA_ROOT` (por worktree, ignorado por git, BD compartida) → `/media/...` da 404. Causa adicional posible en stg/prod: URL con esquema `http` por falta de `SECURE_PROXY_SSL_HEADER` (contenido mixto).

## Current behavior
- `model-view.component.html:21-22` y `models-list.component.html:62-63` pintan `<img [src]="...image">` sin manejo de error: si la URL falla, se ve el icono de imagen rota con el alt.
- `vehicle_serializer.py:66-68` devuelve la URL absoluta vía `request.build_absolute_uri`; sin `SECURE_PROXY_SSL_HEADER` en `settings.py`, detrás de nginx sale `http://panel.praxsasrl.store/media/...`.
- `urls.py:48-49` sirve `/media/` solo con `DEBUG=True`.

## Expected behavior
- Si la imagen carga: se ve, en listado, vista y edición.
- Si la imagen no carga (404, bloqueo, etc.): se muestra el placeholder (`fa-image`) ya usado para "sin imagen", en listado, vista y formulario de edición.
- Detrás de nginx con `X-Forwarded-Proto: https`, la URL de `image` es `https://...`; en dev (sin header) no cambia.

## Architecture considerations
- **Contrato API**: sin cambios de campos; solo cambia el esquema de la URL detrás de proxy. Angular la consume tal cual. No requiere despliegue coordinado.
- **Seguridad**: `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')` confía en un header que cualquiera puede enviar si el backend es alcanzable sin pasar por nginx. `nginx.conf.prod:31-38` (bloque panel) siempre lo fija con `$scheme`, y los compose prod/stg no publican el puerto de `web` (a confirmar en la implementación). Efecto colateral: `request.is_secure()` pasa a ser True tras nginx con https; hoy ninguna cookie/redirect depende de `SECURE_*` (grep sin resultados), así que no hay cambios de comportamiento previsibles en CSRF más allá de lo ya configurado con `CSRF_TRUSTED_ORIGINS`.
- **Datos existentes**: sin migración. Las 2 imágenes huérfanas en BD dev no se tocan (datos del usuario).
- **Acoplamiento**: el fallback se implementa localmente en los 3 componentes; no se crea componente nuevo.
- **Rendimiento / dinero**: no aplica.

## Proposed solution
1. **Frontend (robustez)**: en listado y vista, manejar `(error)` del `<img>` y conmutar al placeholder existente (bandera por fila/por componente). En `image-upload` hacer lo mismo para `currentImageUrl` remoto (no para el preview local de un `File`).
2. **Backend (esquema)**: agregar `SECURE_PROXY_SSL_HEADER` en `settings.py` para que las URLs absolutas salgan con `https` tras nginx.
3. **Datos/entorno (manual, sin código)**: restaurar o re-subir las 2 imágenes en dev; en stg/prod verificar volumen `media` y `location /media/`. Se documenta en el PR, no se automatiza.

Alternativa descartada: devolver URL relativa (`/media/...`) y resolver en el frontend. Cambia el contrato, y en dev el frontend (puerto 4200) y la API (8000) tienen orígenes distintos, por lo que exigiría lógica extra con `environment.apiUrl`.

## Files/components affected
**Backend**
- `praxsa_manager/praxsa_manager/settings.py` (1 línea de configuración)
- `praxsa_manager/product/tests/test_vehicles_module.py` (test nuevo)

**Frontend (`panel_admin/src/app/`)**
- `vehicles/models/model-view.component.{html,ts}` y su spec
- `vehicles/models/models-list.component.{html,ts}` y su spec
- `shared/image-upload/image-upload.component.{html,ts}` y `vehicles/models/model-edit.component.spec.ts` (o spec propio del componente)

## Implementation steps
1. Backend: añadir `SECURE_PROXY_SSL_HEADER` en `settings.py` con comentario sobre la dependencia de nginx; confirmar en los compose prod/stg que `web` no publica puerto al exterior.
2. Backend: test en `test_vehicles_module.py` que crea un Modelo con imagen y hace GET con `HTTP_X_FORWARDED_PROTO='https'` → `image` empieza con `https://`; y sin header → `http://`.
3. Frontend: `model-view` — propiedad `imageFailed`, `(error)="imageFailed = true"`, condición `@if (model.image && !imageFailed)`; resetear al cargar el modelo.
4. Frontend: `models-list` — mismo patrón por fila (p. ej. conjunto de ids fallidos) con `(error)`.
5. Frontend: `image-upload` — `(error)` sobre `currentImageUrl` remoto: mostrar placeholder y no mostrar "Quitar imagen" falsa; el preview de `File` local no se ve afectado.
6. Specs Angular: simular evento `error` en el `<img>` y verificar que aparece el placeholder (view, list, image-upload); verificar que con imagen válida se mantiene el `<img>`.
7. Correr suite backend de vehículos y specs Angular afectados; `ng build` y `ng lint`.
8. Smoke manual en dev (con el usuario): re-subir una imagen a un Modelo y ver listado/vista/edición; comprobar placeholder con una URL rota.

## Test strategy
- **Backend (integración, `APIClient` + helpers existentes)**: esquema `https` con `X-Forwarded-Proto` y `http` sin él.
- **Frontend (unit, `TestBed`)**: fallback al placeholder al disparar `error` en listado, vista e image-upload; no regresión con imagen válida. No se prueba que el archivo cargue realmente (eso es dato/entorno).
- **E2E (Playwright): NO corresponde** — no es flujo crítico de punta a punta ni cambia navegación/formularios multi-paso; los specs de componente cubren el comportamiento. Playwright no está instalado y no se justifica agregarlo.
- Verificación manual de la causa raíz (archivos faltantes) queda como paso de smoke con el usuario.

## Acceptance criteria
- Con archivo existente, la imagen se ve en listado, vista y edición de Modelo.
- Con archivo inexistente/URL rota, en las tres pantallas se ve el placeholder, no el icono roto.
- Con `X-Forwarded-Proto: https` la API devuelve `image` con `https://`; sin header, sin cambios.
- Tests backend de vehículos y specs Angular afectados en verde (las fallas preexistentes de la plantilla no cuentan); `ng build`/`ng lint` limpios.
- El PR documenta los pasos manuales de datos/infra (re-subir imágenes, volumen `media`).

## Risks
- El fallback **oculta** el síntoma: si faltan archivos en prod, el usuario verá placeholder sin aviso. Mitigación: los pasos manuales quedan documentados; no hay monitoreo (no se agrega).
- `SECURE_PROXY_SSL_HEADER` mal confiado si `web` fuera accesible directamente: a verificar en el paso 1; si no se puede garantizar, no se aplica y se escala a `delivery-architect`.
- No se pudo verificar stg/prod desde este entorno: si la causa allí es el volumen vacío, el código no la resuelve.
- Las 2 imágenes huérfanas de dev seguirán rotas (verán placeholder) hasta que el usuario las re-suba.

## Out of scope
- Restaurar/re-subir las 2 imágenes y crear el volumen `media` en stg/prod (acciones manuales del usuario).
- Hacer que los tests backend escriban en un `MEDIA_ROOT` temporal: hoy `test_vehicles_module.py` y `test_almacen_module.py` no hacen `override_settings(MEDIA_ROOT=...)` y dejan archivos `vehiculo*.jpg`/`lamina*.jpg` en `media/` real; conviene un task aparte.
- Mover el almacenamiento a un `MEDIA_ROOT` compartido entre worktrees o storage externo (sería decisión de arquitectura).
- Láminas (`Window_Film.image`): se benefician del cambio de esquema, pero su UI no se toca.

**Preguntas abiertas para el usuario:**
1. ¿La captura es de dev local o de stg/prod? (No cambia el código del plan, sí los pasos manuales.)
2. ¿Aceptás mostrar el placeholder cuando la imagen no carga, o preferís otro indicador?
