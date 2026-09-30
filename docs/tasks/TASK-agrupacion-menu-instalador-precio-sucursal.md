# TASK-agrupacion-menu-instalador-precio-sucursal: Dónde agrupar `instalador` y `precio_venta_sucursal` en el menú lateral de `panel_admin/`

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** `task/TASK-agrupacion-menu-instalador-precio-sucursal`
**Pull Request:** [#53](https://github.com/rolion/praxsa-django-panel-admin/pull/53)

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-09-30 | (nuevo) → INVESTIGATION | Task creado | delivery-investigate |
| 2026-09-30 | INVESTIGATION (sin cambio de etapa) | Usuario confirmó que también quiere construir las pantallas (CRUD) de ambos modelos; alcance ampliado | delivery-investigate |
| 2026-09-30 | INVESTIGATION → DESIGN → ARCHITECTURE | Diseño decidido: Instaladores en Usuarios, Precios por sucursal en Almacén, sin grupo nuevo; ambos como listado + modal. Pendiente de arquitectura: permisos, alcance por sucursal, unicidad y borrado | delivery-design |
| 2026-09-30 | ARCHITECTURE → PLANNING | ADR: permisos por `DjangoModelPermissions` (escritura solo `admin`, supuesto a confirmar), soft delete de instalador con `is_active`, borrado físico de precios, alcance por `get_sucursales_in_scope`, unicidad validada en serializer (constraint en base diferido) | delivery-architect |
| 2026-09-30 | PLANNING → ENGINEERING | Plan v1 escrito (backend primero, frontend después, un solo PR); el usuario confirmó que solo `admin` escribe y los demás roles solo leen | delivery-plan |
| 2026-09-30 | ENGINEERING → REVIEW | Plan v1 implementado sin desvíos de alcance (backend + frontend). Verificación propia: backend 371/371, `makemigrations --check` limpio, `ng build`/`ng lint` limpios, frontend 235/250 con las mismas 15 fallas de componentes demo de la plantilla | delivery-engineer |
| 2026-09-30 | REVIEW → PUBLISH | Quality Gate PASS: backend 371/371, frontend sin fallas nuevas, prueba en vivo correcta; 1 issue Low abierto (REV-01, estético, no bloqueante) | delivery-review |
| 2026-09-30 | PUBLISH (sin cambio de etapa) | Descripción del PR completada; cambio sensible (permisos + migración): pendiente de aprobación humana para merge | delivery-publish |

## Investigación

### Requerimiento
"En praxsa_manager hay 2 tablas `instalador` y `precio_sucursal`, no sé dónde agrupar estos 2 modelos en el nuevo panel_admin; investiga dónde agruparlos o si deberíamos crear un nuevo grupo en el menú lateral."

Nota de nombre: la segunda tabla se llama `precio_venta_sucursal` en el código (`praxsa_manager/product/models.py:328`), verbose name "Precio por Sucursal" (`models.py:334`). No existe ningún modelo llamado `precio_sucursal` (el nombre aparece solo como alias de `Subquery` en `views.py:79` y `business/inventario.py:114`).

**Ampliación de alcance (2026-09-30, confirmada por el usuario en chat):** además de decidir la agrupación en el menú, se quieren construir las pantallas de ambos modelos en `panel_admin/`.

### Hechos encontrados

**Los dos modelos**
- `praxsa_manager/product/models.py:131-137` — `instalador`: `name`, `address`, `phonenumber`, `sucursal = ManyToManyField(Sucursal)`. Sin `is_active`, sin `verbose_name`, sin relación con `User`.
- `praxsa_manager/product/models.py:328-334` — `precio_venta_sucursal`: FK a `Window_Film` (lámina), `width`, FK a `Sucursal`, `precio_venta`. Sin unique constraint (ya documentado como BIZ-07 en `docs/backend-audit.md:530`).
- Las migraciones muestran que `instalador` fue antes una relación `instalador_sucursal` y hoy es M2M directo a `Sucursal` (`migrations/0032`, `0043`, `0072`); la última migración del proyecto es `0111_estados_orden.py`.

**Cómo se usan hoy (dominio)**
- `instalador` se referencia desde `Nota_trabajo.instaladar` (FK, `models.py:207`, campo con typo histórico). Se lista por sucursal en `OrdenesInstaladoresView` (`custom_views/ordenes_admin.py:414-423`, ruta `urls.py:132` `ordenes/catalogo/instaladores`) y el serializer de PATCH de Nota de Trabajo valida que el instalador pertenezca a la sucursal de la proforma (`serializer/ordenes_serializer.py:389`). Es decir, en el panel nuevo ya se **consume** desde el módulo Órdenes, pero no hay CRUD.
- `precio_venta_sucursal` es un **override de precio por sucursal + lámina + ancho**: si existe, gana; si no, se usa `inventario.precio_venta_mtr_lineal` (`docs/integration-and-backlog.md:78-82`; implementado en `business/pricing.py:80-81`, `views.py:79-87`, `business/inventario.py:114`). Depende de dos entidades ya agrupadas en el menú: `Window_Film` (Almacén > Láminas) y `Sucursal` (Usuarios > Sucursales).

**Cómo estaban expuestos en el admin Django viejo**
- `admin.py:33` `admin.site.register(instalador, Installer)` (`admin_config/installer.py`: list_display nombre/teléfono/dirección, búsqueda por nombre; sin filtro por sucursal).
- `admin.py:53` `admin.site.register(precio_venta_sucursal, PrecioVentaSucursalAdmin)` (`admin_config/precio_venta_sucursal.py`): el formulario limita sucursales a las del usuario que estén habilitadas y láminas a las que tengan bobina en inventario de esas sucursales (líneas 16-29); rechaza duplicados sucursal+lámina+ancho en `save_model` (líneas 31-44); el listado se filtra a **una sola sucursal del usuario** vía `Precio_Venta_Business` (`business/precio_venta.py:11-24`, toma `sucursales[0]`).
- No hay `app_label`/agrupación personalizada: en el admin viejo ambos aparecían planos bajo la app `product`, junto con todos los demás modelos (no hay agrupación de negocio que heredar).

**Menú actual de `panel_admin/`** (`panel_admin/src/assets/data/routes.json`, cargado por `layout/sidebar/sidebar.service.ts`): Dashboard (l.4) · **Usuarios** (l.15: Credenciales, Grupos, Sucursales) · **Vehículos** (l.60: Marcas, Modelos, Items) · **Almacén** (l.105: Láminas, Bobinas, Inventario) · **Órdenes** (l.150: Proforma, Nota de Trabajo, Nota de Venta). Cada grupo tiene su carpeta de rutas lazy-loaded en `app.routes.ts` (`users`, `vehicles`, `almacen`, `ordenes`). Ninguno de los dos modelos tiene pantalla ni entrada de menú hoy.

**Conceptos vecinos para el criterio de agrupación**
- `Car_Model_Part.installation_price` ("Costo Instalación", `models.py:256`) ya vive bajo Vehículos > Items: el precio de mano de obra está en Vehículos, el de material por sucursal aún no tiene lugar.
- Los grupos existentes están armados por **entidad de dominio que se administra** (personas/accesos, catálogo de vehículos, stock/materiales, documentos de venta), no por tipo de pantalla.
- `helper/user.py:4-25` usa un grupo Django llamado `instalador` como rol de usuario; es un concepto **distinto** del modelo `instalador` (el modelo no tiene FK a `User`). Riesgo de confusión en nombres/menú.
- Permisos: el patrón de los módulos nuevos es `DjangoModelPermissions` + `IsStaffUser` (`custom_views/vehicle_admin.py:16`, según `TASK-modulo-almacen`); Almacén define roles `admin`/`almacen` (`docs/tasks/TASK-modulo-almacen.md`). No hay decisión previa sobre qué rol administra instaladores ni precios por sucursal en el panel nuevo.

### Hipótesis / supuestos no confirmados
- (Resuelto) El usuario confirmó que las pantallas entran en el alcance. Sigue sin definirse si son CRUD completo o solo listado/edición.
- No se verificó si `proforma/` (Angular viejo) o algún otro cliente consume `instalador`/`precio_venta_sucursal` por endpoints distintos a los citados; solo se revisó `praxsa_manager/` y `panel_admin/`.
- No se confirmó qué rol de negocio debe gestionar instaladores y precios por sucursal (¿`admin`, `almacen`, admin de sucursal?), ni si el override de precio debe ser editable por un usuario que no sea admin global.
- No se confirmó si los instaladores deben seguir sin vínculo con `User` (hoy son registros independientes).

### Módulos y dependencias relacionadas
- Backend: `models.py`, `admin_config/installer.py`, `admin_config/precio_venta_sucursal.py`, `Forms/precio_venta_sucursal_form.py`, `business/precio_venta.py`, `business/pricing.py`, `business/inventario.py`, `custom_views/ordenes_admin.py`, `serializer/ordenes_serializer.py`, `helper/user.py`.
- Frontend: `panel_admin/src/assets/data/routes.json`, `panel_admin/src/app/app.routes.ts`, módulos `users/`, `almacen/`, `ordenes/`.

### Implementaciones similares existentes
- Alta de un nuevo grupo de menú con CRUD: `almacen/` y `vehicles/` (routes.json + carpeta lazy + service + model + list/create/edit/view), según `TASK-modulo-almacen` y `TASK-modulo-vehiculos`.
- Sucursales dentro de Usuarios como listado simple (`/users/sucursales`), precedente de una entidad "de soporte" colgada de un grupo mayor.

### Comportamiento actual
Ni `instalador` ni `precio_venta_sucursal` son administrables desde `panel_admin/`; solo desde el admin Django viejo. `instalador` se elige (solo lectura) al asignar una Nota de Trabajo; `precio_venta_sucursal` afecta el precio sugerido en cotización pero no tiene UI nueva.

### Restricciones
- `docs/CLAUDE.md`: proyecto con deuda técnica; no asumir por nombre de archivo.
- Coherencia con la plantilla `panel_admin/` (`docs/frontend/panel_admin/reference.md`, edición de `routes.json` siguiendo el patrón de menú anidado).
- `precio_venta_sucursal` sin unique constraint (BIZ-07) y con `on_delete=DO_NOTHING` en ambas FK; `instalador` sin `is_active`: cualquier CRUD que borre tendrá que resolver esto (tema de arquitectura, no de este reporte).

### Riesgos identificados
- Colisión de nombre entre el modelo `instalador` y el grupo/rol `instalador`.
- El listado histórico de precios por sucursal opera sobre `sucursales[0]` del usuario (`business/precio_venta.py:16-19`): comportamiento frágil si se replica en la API nueva.
- Si se agrega un grupo de menú nuevo con pocas entradas, el sidebar crece; si se cuelgan en grupos existentes, puede quedar semánticamente forzado (ver puntos de comparación abajo).

### Puntos de comparación para la decisión (hechos, sin recomendar)
| Modelo | Afinidad con grupo existente | Evidencia |
|---|---|---|
| `precio_venta_sucursal` | **Almacén** (depende de Láminas y de inventario; es precio de material, se resuelve junto a `inventario.precio_venta_mtr_lineal`) o **Usuarios > Sucursales** (es un atributo por sucursal) | `pricing.py:80-81`, FK a `Window_Film` y `Sucursal` |
| `instalador` | **Usuarios** (es personal, pertenece a sucursales, como Sucursales/Credenciales) u **Órdenes** (solo se usa en Nota de Trabajo) o un grupo nuevo "Catálogos/Configuración" que también podría absorber otros | M2M a `Sucursal`; FK desde `Nota_trabajo` |
| Grupo nuevo | Ningún otro modelo huérfano hoy justifica por sí solo un grupo; ambos juntos no comparten dominio (personal vs. precios) | Solo dos candidatos, ambos con dominio distinto |

La elección concreta es trabajo de `delivery-design` (criterio de UX/consistencia del menú), no de esta investigación.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — Exponer ambos modelos en el panel nuevo implica nuevos endpoints CRUD, definición de permisos por rol (hoy sin decisión previa), y resolver deudas de datos (`DO_NOTHING`, falta de unique constraint, borrado sin `is_active`, alcance por sucursal). Ante la duda entre PLAN y ARCHITECTURE se prefiere ARCHITECTURE. El usuario confirmó que también se construyen las pantallas, por lo que el alcance incluye backend y frontend.

### Diseño requerido
**SI** — La pregunta central es de estructura del menú lateral y de pantallas nuevas (listados/formularios) que deben ser consistentes con Usuarios/Almacén/Órdenes.

## Diseño
[DDR-agrupacion-menu-instalador-precio-sucursal-menu-y-pantallas](../design/DDR-agrupacion-menu-instalador-precio-sucursal-menu-y-pantallas.md) — Instaladores en el grupo Usuarios y Precios por sucursal en Almacén (sin grupo nuevo), ambos como listado `ngx-datatable` con modal de crear/editar.

## Arquitectura
[ADR-agrupacion-menu-instalador-precio-sucursal-api-permisos-borrado](../adr/ADR-agrupacion-menu-instalador-precio-sucursal-api-permisos-borrado.md) — API aditiva, permisos por grupo, borrado lógico de Instaladores, borrado físico de Precios, alcance por sucursal y unicidad en serializer.

## Plan
[PLAN-2026-09-30-agrupacion-menu-instalador-precio-sucursal](../plans/PLAN-2026-09-30-agrupacion-menu-instalador-precio-sucursal.md) — v1.

## Implementación
Plan v1 implementado tal cual, sin desvíos de alcance.

**Backend (`praxsa_manager/product/`)**
- `models.py` + `migrations/0112_instalador_is_active.py`: `instalador.is_active` (default `True`), aditiva.
- `serializer/instalador_precio_serializer.py`: `InstaladorSerializer` (`is_active` de solo lectura, `sucursal_names`) y `PrecioVentaSucursalSerializer` (ancho y precio > 0, lámina activa, sucursal dentro de `get_sucursales_in_scope`, unicidad sucursal+lámina+ancho excluyendo la propia fila).
- `custom_views/instalador_admin.py` (listado/alta, detalle, `toggle-active`) y vistas de Precios en `custom_views/almacen_admin.py` (`DELETE` físico; queryset acotado al alcance del usuario).
- `urls.py`: `instaladores…` y `almacen/precios-sucursal…`.
- Órdenes: `OrdenesInstaladoresView` excluye inactivos; `NotaTrabajoUpdateSerializer` rechaza **asignar** un instalador inactivo, pero no bloquea editar otros campos de una nota que ya lo tenía.
- `management/commands/asignar_permisos_instalador_precio.py`: da al grupo `Admin` los permisos de escritura de ambos modelos (idempotente, `--dry-run`).
- `tests/test_instaladores_precios_module.py`: 25 pruebas nuevas.

**Frontend (`panel_admin/src/`)**
- `InstaladoresListComponent` (`/users/instaladores`) y `PreciosSucursalListComponent` (`/almacen/precios-sucursal`): `ngx-datatable`, búsqueda en el navegador, modal reactivo, `ng-select` de sucursales, confirmación con SweetAlert2 y botones de escritura solo con `hasGroup('admin')`.
- Modelos y métodos de servicio en `users.*` y `almacen.*`; rutas y dos entradas en `assets/data/routes.json`.
- Specs de ambos componentes (que ejercitan las llamadas de servicio).

**Verificación propia (no es el Quality Gate formal)**
- Backend: `manage.py test` 371/371 OK; `makemigrations --check --dry-run` sin cambios.
- Frontend: `ng build` y `ng lint` limpios; `ng test` 235 OK y 15 fallas, todas de componentes demo de la plantilla (`AdvanceTable`, `Blank`, `Dashboard2`, `First1-3`, `Footer`, `Main`, `Page404`, `Page500`, `Second1-2`, `Sidebar`, `Signup`, `Third1`), ninguna de este cambio.

**No verificado**
- No se hizo prueba en vivo en el navegador: exigiría migrar la base de desarrollo real y iniciar sesión. Queda para `delivery-review`. Punto a mirar: la columna "Acciones" se declara dentro de un `@if (canManage)` dentro de `ngx-datatable`; no se comprobó visualmente que se oculte/muestre bien.

**Notas y deuda técnica**
- Se usó una junction `panel_admin/node_modules` hacia el checkout principal solo para correr las pruebas locales (ignorada por git).
- Los archivos nuevos quedaron con fin de línea LF y los existentes conservaron CRLF (aviso de git, sin efecto funcional).
- Sigue pendiente el `UniqueConstraint` en base para precios (BIZ-07).
- Tras desplegar hay que ejecutar `python manage.py asignar_permisos_instalador_precio` en cada ambiente.

## Review
**Resultado: PASS** (2026-09-30, delivery-review; sesión distinta de la implementación, aislamiento procedimental).

- Backend `manage.py test` 371/371 OK; `makemigrations --check` limpio; migración `0112` aplicada sin error sobre BD vacía.
- Frontend `ng lint` limpio, `ng build` OK, `ng test` 235 OK / 15 fallas preexistentes de componentes demo (ajenas al cambio).
- Prueba en vivo (BD descartable) con `admin` y con usuario de solo lectura: CRUD, soft delete, unicidad, alcance por sucursal y 403 verificados.
- No realizado: `flake8`/`ruff`/`mypy`/`bandit`/`safety`/`coverage.py` no están instalados en backend (revisión manual de cobertura de ramas nuevas). `npm audit`: 79 vulnerabilidades preexistentes, sin dependencias nuevas.
- Issues abiertos: [REV-2026-09-30-agrupacion-menu-instalador-precio-sucursal-01](../reviews/REV-2026-09-30-agrupacion-menu-instalador-precio-sucursal-01.md) (Low, IMPLEMENTATION, estético; no bloquea).
- Siguiente: `/delivery-publish TASK-agrupacion-menu-instalador-precio-sucursal`.

## Publicación
PR [#53](https://github.com/rolion/praxsa-django-panel-admin/pull/53) — **Listo para aprobación humana** (no mergeado). Cambio sensible: permisos por grupo (autorización) y migración `0112` de BD, respaldado por el ADR `ADR-agrupacion-menu-instalador-precio-sucursal-api-permisos-borrado`. Al desplegar: migrar y ejecutar `python manage.py asignar_permisos_instalador_precio`.
