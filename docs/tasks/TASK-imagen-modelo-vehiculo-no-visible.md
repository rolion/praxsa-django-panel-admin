# TASK-imagen-modelo-vehiculo-no-visible: La imagen del vehículo no se visualiza en el listado ni en la vista de Modelo

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** NO
**Rama:** task/TASK-imagen-modelo-vehiculo-no-visible
**Pull Request:** _sin abrir todavía_

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-09-30 20:11 UTC | (nuevo) → INVESTIGATION | Task creado | delivery-investigate |
| 2026-09-30 20:40 UTC | INVESTIGATION → PLANNING | Investigación completa, veredicto NEEDS_PLAN, sin diseño | delivery-plan |
| 2026-09-30 20:40 UTC | PLANNING → ENGINEERING | Plan v1 listo, pendiente de confirmación humana | delivery-plan |

## Investigación

### Requerimiento
"En la tabla de modelo, la imagen del vehículo no se está visualizando correctamente, ni en el listado ni en la vista del modelo." Captura adjunta: pantalla "Ver modelo" (Honda / CR-V / Activo) con el `<img>` roto mostrando el texto alternativo "Imagen del vehículo".

### Hechos encontrados
- `panel_admin/src/app/vehicles/models/model-view.component.html:21-22` — la vista pinta `<img [src]="model.image" alt="Imagen del vehículo">` cuando `model.image` es truthy. El alt visible en la captura coincide con este literal: el navegador recibió una URL, intentó cargarla y falló (no es el placeholder de "sin imagen").
- `panel_admin/src/app/vehicles/models/models-list.component.html:62-63` — el listado usa `<img [src]="row.image" class="data-table-img">` con el mismo `image` de la API. Ambas pantallas consumen el mismo campo, sin transformación de URL en el frontend.
- `praxsa_manager/product/serializer/vehicle_serializer.py:66-68` — `CarModelSerializer` expone `image` (ImageField estándar de DRF). Con `request` en el contexto, DRF devuelve URL absoluta construida con `request.build_absolute_uri`.
- `praxsa_manager/product/custom_views/vehicle_admin.py:120-147` — las vistas genéricas (`ListCreateAPIView`/`RetrieveUpdateAPIView`) pasan `request` al contexto; la URL emitida es absoluta.
- `praxsa_manager/praxsa_manager/settings.py:211-212` — `MEDIA_URL='/media/'`, `MEDIA_ROOT = BASE_DIR / 'media'` (relativo al checkout donde corre el backend).
- `praxsa_manager/praxsa_manager/urls.py:48-49` — Django solo sirve `/media/` si `settings.DEBUG` es verdadero.
- `praxsa_manager/.gitignore:12` — `media` está ignorado por git: los archivos subidos no viajan entre checkouts/worktrees.
- **Verificado contra la BD Postgres local real** (consulta de solo lectura vía `manage.py shell`): de 155 modelos, 2 tienen imagen: `CR-V` (id 1, Honda) → `car_models/honda-cr-v-966738.jpg` y `A1` (id 58) → `car_models/audi_a1.jfif`. Ninguno de los dos archivos existe en `praxsa_manager/media/` de este worktree, ni del checkout principal (no tiene carpeta `media`), ni en ninguno de los demás worktrees (búsqueda por nombre en todo `E:\praxsa\praxsa-django-panel-admin`, sin resultados).
- **Reproducido**: el serializer emite `http://localhost:8000/media/car_models/honda-cr-v-966738.jpg` (URL bien formada, `DEBUG=True`), pero `GET /media/car_models/honda-cr-v-966738.jpg` responde **404**. Es decir, el fallo de la captura se reproduce en dev: la fila en BD apunta a un archivo que no está en disco.
- `praxsa_manager/praxsa_manager/settings.py` — no hay `SECURE_PROXY_SSL_HEADER` ni `USE_X_FORWARDED_HOST` (grep sin resultados). Con `X-Forwarded-Proto: https` y `Host: panel.praxsasrl.store`, el serializer emite `http://panel.praxsasrl.store/media/...` (reproducido con `APIRequestFactory`): esquema `http`, no `https`.
- `nginx/nginx.conf.prod:26-28` — existe `location /media/ { alias /praxsa_manager/media/; }` (mismo en `.stg:27-29`); `nginx.conf.prod:31-38` ya envía `X-Forwarded-Proto` a Django.
- `docs/tasks/TASK-modulo-vehiculos.md:172` — el volumen Docker `media` debe crearse manualmente antes del primer despliegue; no se pudo verificar en ese entorno.
- `panel_admin/src/app/vehicles/models/model-edit.component.spec.ts:19,55-60` — el spec del formulario de edición solo verifica que el `src` coincida con el valor de la API; ningún spec comprueba que la URL realmente cargue.
- Última migración: `praxsa_manager/product/migrations/0114_precio_venta_sucursal_unico.py` (la tarea no parece requerir migración).

### Hipótesis / supuestos no confirmados
- Causa más probable en el entorno de la captura (dev local): las imágenes se subieron desde otro worktree (cada uno con su propio `BASE_DIR/media`) que luego se borró/limpió, mientras la BD local es compartida entre worktrees. Es coherente con los hechos pero no se pudo confirmar el origen histórico de los archivos.
- No se sabe si la captura viene de dev local o de stg/prod. Si fuera stg/prod, hay dos causas adicionales posibles, no verificadas (sin acceso a esos entornos): (a) el volumen `media` no existe/está vacío, (b) contenido mixto — la página https del panel bloquea la imagen con URL `http://` (ver hecho del esquema).
- No se verificó si la pantalla de edición del formulario también muestra la imagen rota (el usuario solo reportó listado y vista; ambos usan el mismo `image`, así que probablemente sí).
- No se verificó que subir una imagen nueva en dev hoy funcione de punta a punta (archivo se guarda y se sirve); la ausencia de los 2 archivos sugiere un problema de entorno, no de código de subida, pero no se ejercitó el flujo en un navegador.

### Módulos y dependencias relacionadas
- Backend: `product/models.py:29` (`Car_Model.image`), `product/serializer/vehicle_serializer.py`, `product/serializer/image_validation.py`, `product/custom_views/vehicle_admin.py`, `praxsa_manager/settings.py`, `praxsa_manager/urls.py`.
- Frontend: `panel_admin/src/app/vehicles/models/` (view, list, edit, create), `shared/image-upload/`.
- Infra: `nginx/nginx.conf.prod|stg`, `docker-compose.prod|stg.yml` (volumen `media`).
- Las láminas (`Window_Film.image`, `product/models.py:66`) usan el mismo `MEDIA_ROOT` y comparten el problema por construcción.

### Implementaciones similares existentes
- El módulo de Almacén (láminas) reutiliza `validate_uploaded_image` y el mismo mecanismo de `ImageField` + `MEDIA_ROOT` (`docs/tasks/TASK-modulo-almacen.md`); no hay otro mecanismo de servir archivos en el proyecto.

### Comportamiento actual
La API devuelve una URL absoluta bien formada derivada del `request`. Si el archivo no está en `MEDIA_ROOT` del proceso que corre el backend, `/media/...` responde 404 y el `<img>` se muestra roto en listado y vista (y probablemente en el formulario de edición). No existe ningún manejo de error de carga en el frontend (`(error)` handler ni fallback al placeholder). Detrás de nginx, la URL sale con esquema `http`.

### Restricciones
- `docs/CLAUDE.md`: proyecto con deuda técnica; cambios acotados y consistentes con lo existente.
- ADR `ADR-modulo-vehiculos-almacenamiento-imagenes` fijó el almacenamiento en filesystem local + nginx; cambiarlo sería decisión de arquitectura.
- La BD de dev es una Postgres real compartida entre worktrees (memoria de entorno local); no modificar datos sin consentimiento.

### Riesgos identificados
- Los datos en BD con `image` huérfana (2 filas en dev) seguirán rotos aunque se arregle el código, salvo que se re-suban o se restauren los archivos.
- `media` ignorado por git y por worktree: el problema se repetirá en cualquier worktree nuevo con la BD compartida.
- En stg/prod, si el problema es de esquema/volumen, afecta también a láminas y requiere cambios de infraestructura/configuración que no se pueden verificar desde este entorno.
- Sin tests que validen que la URL emitida sea servible.

### Veredicto de complejidad
**NEEDS_PLAN** — No se encontró un defecto de lógica en el código de listado/vista; hay un problema de datos/entorno confirmado (archivos ausentes) y una posible falla de configuración (esquema `http` tras nginx) que requiere decidir el alcance de la corrección. Es acotado y no exige una decisión arquitectónica nueva (el ADR de almacenamiento se mantiene), por lo que va a `delivery-plan`; si se decidiera cambiar dónde/cómo se guardan las imágenes, escalaría a NEEDS_ARCHITECTURE.

### Diseño requerido
**NO** — No hay superficie de UI nueva; a lo sumo un fallback al placeholder existente cuando la imagen no carga, que reutiliza el patrón visual ya presente.

## Diseño
_Pendiente / No aplica_

## Arquitectura
_Pendiente / No aplica según veredicto_

## Plan
[PLAN-2026-09-30-imagen-modelo-vehiculo-no-visible.md](../plans/PLAN-2026-09-30-imagen-modelo-vehiculo-no-visible.md) — versión vigente: v1

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
