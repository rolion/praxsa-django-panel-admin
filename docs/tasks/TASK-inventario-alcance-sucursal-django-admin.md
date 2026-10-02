# TASK-inventario-alcance-sucursal-django-admin: Inventario — choque entre el alcance por sucursal y la regla "solo las sucursales asignadas a su cuenta"

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-inventario-alcance-sucursal-django-admin
**Pull Request:** _sin abrir todavía_

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-02 | (nuevo) → INVESTIGATION | Task creado | delivery-investigate |
| 2026-10-02 | DESIGN → ARCHITECTURE | DDR de sucursales inactivas en solo lectura y filtro multiselect de reportes registrado; veredicto NEEDS_ARCHITECTURE | delivery-design |
| 2026-10-02 | ARCHITECTURE → PLANNING | 2 ADR registrados: alcance lectura/escritura sin excepción de grupo (incl. Django Admin) y contrato multisucursal de reportes; 4 ADR previos marcados como reemplazados parcialmente | delivery-architect |
| 2026-10-02 | PLANNING → ENGINEERING | Plan v1 escrito y PR abierto; queda a la espera de la aprobación humana del plan y de las 4 preguntas abiertas antes de implementar | delivery-plan |
| 2026-10-02 | (sin cambio de etapa) | Usuario responde: regla en todo el sistema; solo el superusuario ve todo | delivery-investigate |
| 2026-10-02 | (sin cambio de etapa) | Usuario define sucursales inactivas: lectura sí, escritura no; reportes con multiselect | delivery-investigate |
| 2026-10-02 | (sin cambio de etapa) | El usuario aclara con captura que la regla aplica también al grupo admin; se agrega el hecho G como choque principal | delivery-investigate |

## Investigación

### Requerimiento
"Creo que hay un choque con una regla de negocio: el grupo solo debe poder ver, modificar o agregar el inventario en las sucursales asignadas a su cuenta."

> **Aclaración del usuario (2026-10-02, con captura de `/panel/almacen/inventario`):** un usuario del grupo **admin** que solo tiene asignada la sucursal Santa Cruz debe ver únicamente el inventario de Santa Cruz. En la captura ve filas de **La Paz y Santa Cruz** (4 filas, selector "Todas las sucursales"). El usuario lo marca como incorrecto. Es decir, **la regla aplica también al grupo admin**: el alcance sale de las sucursales asignadas a la cuenta, no del grupo. Esto convierte en el choque principal lo que antes estaba como hipótesis menor (ver hecho G). Los puntos B, C y E siguen siendo hallazgos válidos pero secundarios.

La captura confirma el síntoma en el panel (`panel_admin/`); no pude verificar con los datos reales qué sucursales tiene asignadas esa cuenta, se toma de lo dicho por el usuario.

Esta investigación busca **todos los puntos del código donde el inventario se ve, se modifica o se agrega** y compara cada uno con la regla. El PR #66 (`TASK-almacen-permisos-sucursal-filtros`, ya fusionado en `master`, `16c2fc1`) cubrió solo la API del panel `panel_admin/`.

### Hechos encontrados

**G. Causa del síntoma de la captura: el grupo `admin` está exento del alcance por sucursal (choque principal)**
- `helper/user.py:28-29` — `can_view_all_sucursales(user)` devuelve `is_request_user_admin(user)`, es decir, "pertenece al grupo admin". No consulta las sucursales asignadas.
- `business/inventario.py:21-22` — `get_panel_inventario_queryset`: si `can_view_all_sucursales`, devuelve `qs` sin filtrar. Por eso el admin de Santa Cruz ve La Paz.
- `helper/user.py:45-46` — `get_sucursales_in_scope`: admin recibe todas las sucursales habilitadas; alimenta `almacen/sucursales` (selector "Todas las sucursales" de la captura, `almacen_admin.py:126-136`), la validación del alta (`almacen_serializer.py:155`) y los Precios por sucursal (`almacen_admin.py:251-259`).
- Por lo tanto, para un admin el alta, el detalle por id, el PATCH y el toggle también aceptan cualquier sucursal.
- No es un olvido: `ADR-almacen-permisos-sucursal-filtros-alcance-inventario` lo listó como **supuesto de negocio pendiente de confirmar** ("admin conserva todas las sucursales habilitadas") y `TASK-almacen-permisos-sucursal-filtros.md` lo repite en Hipótesis. La captura es la respuesta del negocio: el supuesto era incorrecto.
- La excepción para admin está repetida en otros módulos que usan `can_view_all_sucursales`: `business/dashboard.py:87`, `business/orden_trabajo.py:43,53`, `business/pago.py:22,30,36`, `business/proforma.py:166`, y los reportes `report_daily_sell.py:114`, `reportes_admin.py:56`, `report_utilidad.py:66`, `report_storage.py:74`. Además el Django Admin de inventario tiene su propia excepción (`admin_config/inventory.py:47,60`, también para `is_superuser`).

**A. API del panel (`almacen/inventario*`) — respeta el alcance para no-admin (PR #66)**
- `custom_views/almacen_admin.py:118-123` — `_inventario_in_scope(user)` usa `get_panel_inventario_queryset`: admin todo; el resto, filas de **todas** sus sucursales habilitadas.
- `custom_views/almacen_admin.py:159-175` (listado), `:199-205` (toggle), `:234-235` (detalle/PATCH) usan ese alcance; fuera de alcance → 404.
- `serializer/almacen_serializer.py:147-157` — `validate_sucursal` rechaza sucursales fuera de `get_sucursales_in_scope`; el alta pasa `context={'request': request}` (`almacen_admin.py:178`).
- `business/inventario.py:17-23` — `get_panel_inventario_queryset`.

**B. Django Admin, alta/edición de inventario (`InventoryAdmin`) — no cumple la regla**
- `admin.py:39` — `admin.site.register(inventario, InventoryAdmin)`: el Django Admin es otra puerta de entrada para ver, agregar y modificar inventario.
- `admin_config/inventory.py:43-55` — `get_queryset` para no-admin usa **solo `sucursales[0]`** (la primera sucursal donde es empleado), **sin** filtrar `enable_to_install_windows_film`. Un usuario con 2 sucursales ve y edita únicamente una; con una sucursal deshabilitada puede quedar con esa como "la primera".
- `admin_config/inventory.py:22,71-83` y `Forms/inventario.py:22-24` — el formulario es `ModelForm` con `fields = "__all__"`; no hay `formfield_for_foreignkey` ni validación de sucursal. En el alta, el campo `sucursal` ofrece **todas** las sucursales, y no hay ninguna comprobación de que la sucursal elegida sea del usuario (el filtro del `get_queryset` no aplica a un alta).
- `admin_config/inventory.py:57-115` — `changelist_view` **muta atributos de la instancia compartida** del `ModelAdmin` (`self.list_display`, `self.fields`, `self.readonly_fields`) según el rol de quien pide; el estado queda para la siguiente petición (la instancia vive durante todo el proceso). Si un admin entra primero, `self.readonly_fields = []` (`:83`) queda activo; las ramas `supervisor` y la `else` no restablecen `fields`, y la `else` (resto de grupos) no define `readonly_fields` en absoluto. Verificado leyendo el código; no se reprodujo en vivo.
- No hay `has_add_permission`/`has_change_permission`/`has_delete_permission` por sucursal en `InventoryAdmin`; la autorización es solo el `Permission` de Django del modelo.

**C. Django Admin, reporte de almacén (`ReportStorageAdmin`) — solo lectura, alcance incompleto**
- `admin_config/report_storage.py:69` — usa `get_inventario_queryset_by_role`, que para no-admin toma solo `sucursales[0]` (`business/inventario.py:25-38`). Un usuario con varias sucursales no ve el stock de las demás.
- `admin_config/report_storage.py:87-91` — `has_add_permission` y `has_change_permission` devuelven `False` (correcto: es solo lectura).
- `ADR-almacen-permisos-sucursal-filtros-alcance-inventario` (puntos 22 y 51 del texto) decidió **no** tocar `get_inventario_queryset_by_role` y aceptó la coexistencia de dos métodos de alcance como deuda técnica. Es decir, esta divergencia fue una decisión consciente, no un olvido, pero contradice la regla tal como la formula el usuario.

**D. Otros consumidores de inventario con alcance por usuario**
- `business/inventario.py:189-203` — `get_user_inventory_window_films` y `get_inventory_window_film_reel_widths` filtran por `sucursal__empleado = user` (`:191,200`); el segundo **no** filtra `enable_to_install_windows_film`. Los usa `admin_config/proforma_admin.py:46,52` y `views.py:119,181`. Son lecturas para armar proformas, no pantallas de inventario (relevancia no confirmada).
- `business/dashboard.py:108` y `admin_config/report_utilidad.py:69` usan `get_panel_inventario_queryset` (alcance correcto).

**E. Permisos de grupo**
- `ADR-modulo-almacen-permisos-rol-frontend` fija `almacen` como solo lectura; PR #66 mantiene el permiso de Django (`add_inventario`/`change_inventario`) como condición de escritura y **no agregó comando de asignación de permisos a grupos** (`TASK-almacen-permisos-sucursal-filtros.md`, sección Implementación, "Deuda técnica"). En `management/commands/` solo hay comandos de permisos de estados, reportes e instalador/precio (`asignar_permisos_*.py`); ninguno asigna `add/change_inventario`.
- Consecuencia: un grupo no admin no puede agregar ni modificar inventario por la API hasta que alguien le asigne esos permisos a mano; y si se los asignan, el Django Admin (B) les permitiría operar con el alcance defectuoso descrito.

**F. Tests**
- `tests/test_inventario_alcance_sucursal.py` (30 casos) cubre la API (A). `tests/test_sucursal_scope_admin.py:107-156,263-266` cubre `get_inventario_queryset_by_role` y `ReportStorageAdmin` con el comportamiento actual (`sucursales[0]`). No se encontró ningún test de `InventoryAdmin` (alta/edición) por sucursal; hipótesis, falta confirmar con grep específico.

### Hipótesis / supuestos no confirmados
- **(Resuelta por la captura del usuario.)** El choque que el usuario observó es el hecho G: el admin ve todas las sucursales. B, C y E quedan como hallazgos adicionales no confirmados como parte del pedido.
### Respuestas del usuario (2026-10-02)
- **Alcance:** la regla aplica a **todo el sistema** (Órdenes, Pagos, Dashboard, Reportes, Precios por sucursal), no solo a Inventario. Respuesta "sí".
- **Admin sin sucursales asignadas:** ver decisiones confirmadas más abajo (0 filas, 0 datos).
- **Excepción global:** solo el **superusuario de Django** (`is_superuser`) ve todo. El grupo admin deja de ser global.

Hechos asociados (verificados):
- `permissions.py:11` — `IsStaffUser` exige `is_staff`; el flag `is_superuser` no se consulta en ninguna capa de alcance del backend de la API.
- `is_superuser` solo aparece en `admin_config/inventory.py:47,60` (Django Admin de inventario) y `business/proforma.py:126`; `proforma.py:188` y `admin_config/pagos.py:136` lo tienen comentado. `helper/user.py:28-29` no lo considera: hoy un superusuario sin grupo admin ve **0 filas** en la API.
- `has_perm` de Django devuelve `True` para superusuarios, así que no necesitan permisos asignados.

### Decisiones confirmadas por el usuario (2026-10-02, segunda ronda)
- **Admin sin sucursales asignadas:** ve 0 filas y 0 datos (confirmado).
- **Módulo Usuarios:** queda **fuera de alcance** por ahora. Dato para la arquitectura: `custom_views/user_admin.py:134-138` (`SucursalListCreateView`) usa `Sucursal.objects.all()`; un cambio global de `can_view_all_sucursales` no debe alterar ese módulo sin decisión explícita (no se leyó para esta investigación).
- **Impacto en producción:** aceptado. Las cuentas admin sin sucursales dejarán de ver datos; es la regla de negocio y no se requiere mitigación. No se verificó cuántas cuentas afecta.

### Decisiones confirmadas por el usuario (2026-10-02, tercera ronda): sucursales inactivas
- **Lectura sí, escritura no.** Si una sucursal asignada está inactiva (`enable_to_install_windows_film=False`), el usuario **puede ver** sus datos pero **no puede agregar ni modificar**. En Inventario: se ve el inventario de esa sucursal, no se le pueden agregar filas (la sucursal no debe ofrecerse en el formulario de alta; interpretación del mensaje "ya se deberia mostrar esa opcion", que se entiende como "ya no se debería mostrar") ni editarlo.
- **Misma regla en Órdenes:** proformas, notas de trabajo y notas de venta de una sucursal inactiva se pueden ver pero no modificar, y no se pueden crear proformas nuevas en ella.
- **Reportes:** el filtro de sucursal hoy es de selección única ("Todas" o una). Se propone volverlo **multiselect**.

- **Aplica a todos los grupos** (confirmado por el usuario): la regla de lectura sí / escritura no en sucursales inactivas rige para admin y para el resto (Almacén, Caja, Vendedor, Supervisor, etc.), sin excepción por grupo. El superusuario de Django sigue siendo la única excepción global de alcance; **no se confirmó** si el superusuario también queda bloqueado para escribir en sucursales inactivas (hoy el alta ya lo bloquea incluso al admin, `TASK-almacen-permisos-sucursal-filtros`, decisiones por defecto).

Hechos relacionados (verificados):
- `panel_admin/src/app/reportes/reporte-base.ts:31` — el filtro es un `FormControl<number | null>` (una sola sucursal o `null` = todas); `:47-48` el selector solo aparece con más de una sucursal; `:56` las sucursales vienen de `ordenes/catalogo/sucursales` (`OrdenesSucursalesView`, `ordenes_admin.py:390-398`, que usa `get_sucursales_in_scope`). La API de reportes recibe `sucursal` como un solo id (`reportes.components.spec.ts:158`).
- Esta decisión **cambia la definición de "asignada" usada hoy para lectura**: `get_enabled_sucursal_ids` (`helper/user.py:31-39`), `get_sucursales_in_scope` (`:41-47`), `get_panel_inventario_queryset` (`business/inventario.py:17-23`) y `has_assigned_sucursal` (`helper/user.py:57`) filtran por `enable_to_install_windows_film=True` y por tanto hoy **ocultan** las sucursales inactivas también para lectura. Habría dos conceptos: sucursales en alcance de lectura (asignadas, activas o no) y sucursales en alcance de escritura (asignadas y activas).
- El alta de inventario hoy ya rechaza sucursales fuera de `get_sucursales_in_scope` (`almacen_serializer.py:155`), lo que coincide con "no escribir en inactivas"; la lectura de inactivas es lo nuevo.
- No se investigó el código de Órdenes (proforma, nota de trabajo, nota de venta) para ver dónde se validan hoy las modificaciones ni cómo tratan una sucursal inactiva; es la mayor zona sin leer.

### Preguntas abiertas restantes
- **Reportes multiselect:** el mensaje dice "volverlo multiselect para solo seleccionar las activas", lo que choca con "lectura de sucursales inactivas sí". No está claro si el selector debe (a) permitir elegir varias sucursales incluyendo las inactivas (los reportes son lectura) o (b) ofrecer solo las activas. También: ¿"Todas" sigue existiendo, y significa todas las asignadas o solo las activas?
- Dónde se aplica la regla de escritura en Órdenes (qué acciones cuentan como "modificar": cambiar estado, pagos, notas, cancelar).
- Si el Django Admin (B, C) entra en el mismo cambio.
- Si el superusuario también queda bloqueado para escribir en sucursales inactivas.
- "El grupo" se asume = un `Group` de Django (p. ej. `Almacen`, `Vendedor`, `Caja`, `Supervisor`) y "sucursales asignadas a su cuenta" = `Sucursal.empleado` con `enable_to_install_windows_film=True`, igual que el resto del sistema. No se confirmó si una sucursal deshabilitada debe contar como asignada.
- ~~Se asume que `admin` sigue viendo todas las sucursales~~ — **descartada por el usuario** (hecho G). Sigue sin confirmar el trato del superusuario: el Django Admin lo exime (`inventory.py:47`) mientras que la API solo reconoce el grupo `admin` (`helper/user.py:28-29`); un superusuario sin grupo `admin` ve todo en el Django Admin pero nada en la API. No se confirmó si es intencional.
- Se asume que el Django Admin sigue en uso para inventario (los reportes sí lo usan); no se confirmó si los usuarios no admin entran a `/admin/product/inventario/`.
- No se reprodujo en vivo la fuga de estado de `InventoryAdmin.changelist_view` (B); es lectura de código.
- Falta confirmar si las lecturas del punto D deben quedar bajo la misma regla.

### Módulos y dependencias relacionadas
- Backend: `admin_config/inventory.py`, `admin_config/report_storage.py`, `Forms/inventario.py`, `business/inventario.py`, `helper/user.py`, `custom_views/almacen_admin.py`, `serializer/almacen_serializer.py`, `admin.py:39,51`.
- Tests: `tests/test_inventario_alcance_sucursal.py`, `tests/test_sucursal_scope_admin.py`, `tests/test_almacen_module.py`.
- Documentos: `docs/adr/ADR-almacen-permisos-sucursal-filtros-alcance-inventario.md`, `docs/adr/ADR-modulo-almacen-permisos-rol-frontend.md`, `docs/tasks/TASK-almacen-permisos-sucursal-filtros.md`.

### Implementaciones similares existentes
- `_inventario_in_scope` / `get_panel_inventario_queryset` (A) es el patrón ya aceptado para la API.
- `PrecioVentaSucursalAdmin` (`admin_config/precio_venta_sucursal.py`) y `ReportUtilidadAdmin` (`report_utilidad.py:69`) ya aplican alcance por sucursal en el Django Admin; no se leyó `PrecioVentaSucursalAdmin` en detalle (candidato a revisar como plantilla).

### Comportamiento actual
La API del panel respeta la regla para usuarios no admin, pero **no para el grupo admin**, que ve y opera el inventario de todas las sucursales aunque tenga solo una asignada (G; captura del usuario). El Django Admin tampoco la respeta: el listado/edición de inventario se limita a la primera sucursal del usuario sin considerar su habilitación; el alta permite elegir cualquier sucursal; y el estado compartido del `ModelAdmin` puede filtrar la configuración de un rol a otro. El reporte de almacén también se limita a la primera sucursal. Los grupos no admin carecen de permisos de escritura de inventario hasta una asignación manual.

### Restricciones
- `docs/CLAUDE.md`: lógica de negocio con test; varios archivos requieren plan; no editar migraciones aplicadas; no tocar `.env`.
- `ADR-almacen-permisos-sucursal-filtros-alcance-inventario` decidió no modificar `get_inventario_queryset_by_role`; cambiarlo exige superseder esa parte del ADR.
- `test_sucursal_scope_admin.py` codifica el comportamiento `sucursales[0]` y tendría que cambiar.

### Riesgos identificados
- Cambio de **autorización** en el Django Admin, que tiene permisos por modelo y reportes que dependen de `get_inventario_queryset_by_role`.
- Alta en el Django Admin en una sucursal ajena: fuga de escritura entre sucursales (la regla "agregar" se incumple hoy ahí).
- Estado mutable en `InventoryAdmin` (B): comportamiento dependiente del orden de peticiones; difícil de reproducir.
- Cambiar el alcance del reporte (C) altera lo que ve cada usuario multi-sucursal (más filas, no menos).
- Asignar permisos a grupos es una acción operativa sobre datos de producción, fuera del código.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — toca autorización: quitar la excepción del grupo admin en `can_view_all_sucursales` (`helper/user.py:28-29`) cambia qué ve cada admin en Inventario y, si el helper se modifica globalmente, también en Órdenes, Pagos, Dashboard y Reportes (G). Reemplaza además decisiones de ADR vigentes (admin conserva todas las sucursales; no tocar `get_inventario_queryset_by_role`) y afecta a varios módulos, al Django Admin y a los tests. La decisión de si el cambio es solo de Inventario o global es arquitectónica.

### Diseño requerido
**SI** (cambió tras la tercera ronda; antes era NO) — el filtro de sucursal de los reportes pasa de selector único a multiselect, y los formularios de alta (inventario, proformas) y las acciones de edición deben ocultarse o inhabilitarse para sucursales inactivas, con una presentación coherente en el resto de pantallas.

## Diseño
- [DDR-inventario-alcance-sucursal-django-admin-sucursales-inactivas-y-filtro-reportes](../design/DDR-inventario-alcance-sucursal-django-admin-sucursales-inactivas-y-filtro-reportes.md) — sucursal inactiva = solo lectura en Inventario y Órdenes (badge "Inactiva", botones de escritura ocultos con aviso en el detalle, altas sin sucursales inactivas, filtros de listado que sí las incluyen); filtro de sucursal de Reportes como multiselect con `NgbDropdown` + casillas (sin librería nueva), con las activas marcadas por defecto y las inactivas seleccionables. El frontend no es la barrera de seguridad: pendiente de arquitectura el alcance de lectura vs. escritura, la bandera de sucursal activa por fila, el contrato multi-id de reportes y el trato del superusuario.

Supuestos de diseño a confirmar: (1) reportes marcan por defecto solo las activas y permiten marcar las inactivas; (2) "Todas" significa "todas las activas"; (3) el superusuario también queda en solo lectura en sucursales inactivas.

## Arquitectura
- [ADR-inventario-alcance-sucursal-django-admin-alcance-lectura-escritura](../adr/ADR-inventario-alcance-sucursal-django-admin-alcance-lectura-escritura.md) — el alcance se define solo en `User_Helper`: `can_view_all_sucursales` = `is_superuser` (el grupo admin deja de ser global); dos alcances con nombres distintos (lectura = asignadas, activas o no; escritura = asignadas y activas) y se elimina `get_sucursales_in_scope`. Toda modificación de una fila exige sucursal activa (409; fuera del alcance de lectura, 404) con un helper único en las vistas; `sucursal_activa` aditivo en filas y `activa` en los catálogos. Django Admin incluido: los `*_by_role` delegan en los `get_panel_*`, `InventoryAdmin` sin estado mutable y mixin de escritura por objeto. Sin migraciones; rollback por revert, sin feature flag. Reemplaza parcialmente 4 ADR previos.
- [ADR-inventario-alcance-sucursal-django-admin-filtro-multisucursal-reportes](../adr/ADR-inventario-alcance-sucursal-django-admin-filtro-multisucursal-reportes.md) — nuevo `?sucursales=1,2` (lista por comas) junto al `?sucursal=` que se conserva; ids validados contra el alcance de lectura (404 fuera de alcance); "Todas" = activas del alcance; `sin_sucursal` = sin ninguna sucursal asignada. Dashboard y Django Admin mantienen selección única.

Supuestos de negocio pendientes de confirmar (marcados en los ADR): (a) el superusuario también queda bloqueado para escribir en sucursales inactivas; (b) 409 como respuesta por sucursal inactiva; (c) "Todas" en reportes/dashboard = solo activas.

## Plan
- [PLAN-2026-10-02-inventario-alcance-sucursal-django-admin](../plans/PLAN-2026-10-02-inventario-alcance-sucursal-django-admin.md) — **v1**. 15 pasos en 5 fases: A alcance backend (helper con alcance de lectura/escritura, guard 409, bandera `sucursal_activa`), B reportes multisucursal, C Django Admin (`*_by_role` delegando, `InventoryAdmin` sin estado mutable, mixin de escritura), D panel (badge, botones ocultos, formularios solo con activas, multiselect con `NgbDropdown`), E verificación. E2E: no corresponde (sin Playwright; integración de API + specs + verificación manual con perfiles). Sin migraciones ni dependencias nuevas. Cuatro preguntas abiertas con valor por defecto (superusuario en inactivas, 409, "Todas" = activas, un solo PR).

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
