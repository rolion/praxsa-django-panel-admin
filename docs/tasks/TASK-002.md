# TASK-002: Filtrado por sucursal inconsistente en reportes/pagos del admin (backlog #10)

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Rama:** `claude/pagosadmin-filtrado-sucursal-34d0c8`
**Pull Request:** https://github.com/rolion/praxsa-django-panel-admin/pull/32

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-09-21 | (nuevo) → INVESTIGATION | Task creado a partir del ítem #10 de docs/integration-and-backlog.md (backend SEC-06) | delivery-investigate |
| 2026-09-21 | INVESTIGATION → PLANNING | Decisión arquitectónica tomada tras confirmar con el usuario: grupo "Caja" ya existe, Admin+Caja ven todas las sucursales, se incluye ReportNotaTrabajoAdmin, se excluye el bug de "Admin sin sucursal" | delivery-architect |
| 2026-09-21 | PLANNING → ENGINEERING | Plan v1 escrito y PR #32 abierto sobre la rama existente del worktree (mismo criterio que TASK-001: worktree nombrado para este task, sin necesidad de crear `task/TASK-002-...`) | delivery-plan |

## Investigación

### Requerimiento

Ejecutar el ítem #10 del backlog unificado (`docs/integration-and-backlog.md:206-213`, backend `SEC-06`): el filtrado por sucursal del usuario es inconsistente entre los distintos `ModelAdmin` del panel de Django — algunos sí restringen los datos a la sucursal del usuario, otros muestran datos de todas las sucursales a cualquier staff con permiso sobre el modelo.

El usuario agrega una pregunta abierta específica al pedir esta investigación: **confirmar si el grupo "Caja" ya existe en el admin de Django, o si hay que crearlo.** Esto importa porque la solución depende de qué roles deben poder ver datos de todas las sucursales (p. ej. un rol tipo "Caja" o "Admin") frente a los que solo deben ver la propia.

### Hechos encontrados

**Admins que NO filtran por sucursal hoy** (confirmado leyendo cada `get_queryset`, coincide con lo documentado en `docs/backend-audit.md:398,446-451`):
- `PagosAdmin.get_queryset` — [admin_config/pagos.py:131-138](praxsa_manager/product/admin_config/pagos.py) — solo hace `select_related`, sin `.filter()` por sucursal.
- `ReportDailySellAdmin.get_queryset` — [admin_config/report_daily_sell.py:136-140](praxsa_manager/product/admin_config/report_daily_sell.py) — solo `prefetch_related`/`select_related`, sin filtro.
- `ReportStorageAdmin.get_queryset` — [admin_config/report_storage.py:65-74](praxsa_manager/product/admin_config/report_storage.py) — agrega (`annotate`/`Sum`) sobre `inventario.objects` sin filtrar por sucursal; el atributo compartido `aggregated_result` (línea 62, a nivel de clase) también se calcula sin filtro.
- `ReportUtilidadAdmin.get_queryset` — [admin_config/report_utilidad.py:49-60](praxsa_manager/product/admin_config/report_utilidad.py) — igual patrón, expone `precio_compra_mtr_lineal` (costo) y utilidad de todas las sucursales.
- `Orden_Trabajo_Business.get_finish_nota_queryset` — [business/orden_trabajo.py:30-44](praxsa_manager/product/business/orden_trabajo.py) — el filtro por sucursal está **explícitamente comentado** (líneas 32-36); el método ni siquiera recibe `user` como parámetro. Lo consume `ReportNotaTrabajoAdmin.get_queryset` — [admin_config/report_nota_trabajo.py:106-111](praxsa_manager/product/admin_config/report_nota_trabajo.py) — que llama a `get_finish_nota_queryset(qs=qs)` sin pasar el usuario.

**Admins que SÍ filtran correctamente por sucursal hoy** (para usar como referencia de patrón):
- `ProformaAdmin.get_queryset` — [admin_config/proforma_admin.py:191-197](praxsa_manager/product/admin_config/proforma_admin.py) — delega a `Proforma_Business.get_proforma_queryset_by_role` — [business/proforma.py:197-216](praxsa_manager/product/business/proforma.py) — que primero chequea `'Admin' in request.user.groups` (ve todo) y si no, filtra por la primera `Sucursal` a la que pertenece el usuario vía `Sucursal.empleado`.
- `NotaVentaAdmin.get_queryset` — [admin_config/nota_venta.py:114-120](praxsa_manager/product/admin_config/nota_venta.py) — delega a `Proforma_Business.get_nota_venta_queryset_by_role` — [business/proforma.py:218-231](praxsa_manager/product/business/proforma.py). **Diferencia importante con `ProformaAdmin`: este método NO tiene el atajo de "Admin ve todo"** — filtra directo por `Sucursal.objects.filter(empleado__id=user.id,...)`, y si el usuario no tiene sucursal asignada (p. ej. un usuario del grupo Admin sin sucursal propia) devuelve `None`, lo que hace que el admin muestre el mensaje de error "Asigne una sucursal al usuario" y una queryset vacía (`sucursal=-1`) — es decir, hoy un Admin sin sucursal asignada **no puede ver ninguna Nota de Venta**, a diferencia de `ProformaAdmin` donde sí vería todas.
- `NotaTrabajoAdmin.get_queryset` — [admin_config/nota_trabajo.py:130-136](praxsa_manager/product/admin_config/nota_trabajo.py) — delega a `Orden_Trabajo_Business.get_nota_queryset_by_role` — [business/orden_trabajo.py:16-27](praxsa_manager/product/business/orden_trabajo.py) — mismo patrón sin atajo de Admin, misma limitación que `NotaVentaAdmin`.
- `InventoryAdmin.get_queryset`/`changelist_view` — [admin_config/inventory.py:43-115](praxsa_manager/product/admin_config/inventory.py) — usa un patrón distinto de los anteriores: llama a `User_Helper.is_request_user_admin(user)` (línea 47) para el atajo de "ver todo", y en `changelist_view` distingue **tres** roles (`admin`, `supervisor`, cualquier otro) para variar `list_display`/`readonly_fields` — no solo dos como en `ProformaAdmin`.

**Cómo se determinan los roles hoy** (relevante para la pregunta del "grupo Caja"):
- `User_Helper` — [helper/user.py](praxsa_manager/product/helper/user.py) — define exactamente tres chequeos de grupo por nombre (comparando en minúsculas): `is_request_user_admin` (`'admin'`), `is_request_user_installer` (`'instalador'`), `is_request_user_supervisor` (`'supervisor'`).
- `Proforma_Business.get_proforma_queryset_by_role` — [business/proforma.py:200](praxsa_manager/product/business/proforma.py) — chequea el string `'Admin'` directamente contra `user.groups`, sin pasar por `User_Helper` (implementación duplicada del mismo chequeo, con nombre de grupo hardcodeado en dos lugares distintos: `User_Helper` y aquí).
- **No existe ningún chequeo de grupo `'caja'`/`'Caja'` en ningún archivo `.py` del backend** (búsqueda exhaustiva case-insensitive en `praxsa_manager/`, cero resultados). No hay fixtures ni migraciones que creen `Group`s de Django en este proyecto — los grupos (`Admin`, `Supervisor`, `Instalador`, y cualquier otro) se gestionan manualmente desde `/admin/auth/group/` (Django admin estándar; `admin.py` no sobreescribe el `GroupAdmin` por defecto). Esto significa que **no se puede confirmar ni descartar desde el código si el grupo "Caja" ya existe** — es un dato que vive únicamente en la base de datos de cada ambiente (dev/stg/prod), no en el repositorio.
- `Sucursal.empleado` — [models.py:105](praxsa_manager/product/models.py) — `ManyToManyField(User)` es la única fuente de verdad para "a qué sucursal pertenece un usuario" que existe en el modelo de datos; no hay ningún campo o modelo adicional de "rol por sucursal".

**Riesgo ya documentado en el propio repo, relevante para no repetirlo en la solución:**
- `docs/backend-audit.md:453-458` (SEC-07) — `changelist_view` en `InventoryAdmin`, `ProformaAdmin` y `ReportStorageAdmin` muta atributos de instancia (`self.list_display`, `self.readonly_fields`, `self.aggregated_result` en el caso de `ReportStorageAdmin`) según el rol del usuario de la request actual. Como las instancias de `ModelAdmin` son singletons compartidos por proceso, esto es una condición de carrera: bajo concurrencia, una request podría ver transitoriamente columnas calculadas para el rol de otro usuario. Si la solución de este task sigue el mismo patrón (`changelist_view` mutando `self`), heredaría el mismo bug — ya identificado como hallazgo independiente (SEC-07), no parte de este backlog #10, pero relevante si se copia el patrón de `InventoryAdmin` tal cual.

### Hipótesis / supuestos no confirmados

- No se pudo confirmar si el grupo Django "Caja" existe hoy en algún ambiente (dev/stg/prod) — no es verificable desde el código ni desde este entorno de investigación (sin acceso a la base de datos en ejecución). Se necesita confirmarlo consultando `/admin/auth/group/` en el ambiente real, o preguntando directamente a quien administra el sistema.
- Se asume, sin confirmar con negocio, que el propósito de un eventual grupo "Caja" sería ver pagos/reportes de **todas** las sucursales (similar al atajo que hoy tiene `'Admin'` en `Proforma_Business.get_proforma_queryset_by_role`) — pero también podría significar lo contrario (un rol más restringido que solo ve caja de su propia sucursal, a diferencia de otro rol gerencial que sí ve todas). El nombre del grupo no basta para inferir el comportamiento esperado.
- No se verificó si actualmente hay usuarios reales asignados a los grupos `Admin`/`Supervisor`/`Instalador` sin sucursal asignada en `Sucursal.empleado` — dato relevante porque, como se documentó arriba, `NotaVentaAdmin`/`NotaTrabajoAdmin` ya tienen el bug de que un usuario sin sucursal ve una lista vacía aunque sea Admin; si `PagosAdmin`/`ReportDailySellAdmin` copian ese mismo patrón (en vez del patrón de `ProformaAdmin`), un Admin sin sucursal se quedaría también sin ver pagos.

### Módulos y dependencias relacionadas

- **Admins a corregir**: `praxsa_manager/product/admin_config/pagos.py` (`PagosAdmin`), `report_daily_sell.py` (`ReportDailySellAdmin`), `report_storage.py` (`ReportStorageAdmin`), `report_utilidad.py` (`ReportUtilidadAdmin`).
- **Business a corregir**: `praxsa_manager/product/business/orden_trabajo.py` (`Orden_Trabajo_Business.get_finish_nota_queryset`, filtro comentado) y su llamador `report_nota_trabajo.py` (`ReportNotaTrabajoAdmin.get_queryset`).
- **Capa de roles existente, candidata a reusar/extender**: `praxsa_manager/product/helper/user.py` (`User_Helper`) y los métodos `*_queryset_by_role` en `business/proforma.py` y `business/orden_trabajo.py`.
- **Modelo de datos**: `Sucursal` (`empleado` M2M) — [models.py:101-109](praxsa_manager/product/models.py); ningún modelo de "rol" persistido, solo `django.contrib.auth.models.Group`.
- **Gestión de grupos**: Django admin estándar (`/admin/auth/group/`), no hay código propio que la envuelva.

### Implementaciones similares existentes

- El patrón a replicar es el de `ProformaAdmin`/`Proforma_Business.get_proforma_queryset_by_role`: delegar el filtrado a un método de `business/`, con un atajo explícito para el/los rol(es) que deben ver todas las sucursales y, si no aplica, filtrar por la sucursal del usuario (`Sucursal.objects.filter(empleado__id=user.id, enable_to_install_windows_film=True)`).
- Alternativamente, el patrón de `InventoryAdmin` (usa `User_Helper.is_request_user_admin`/`is_request_user_supervisor` en vez de repetir el chequeo de grupo inline) es más consistente con tener la lógica de roles centralizada en un solo lugar — pero **ninguno de los dos patrones existentes es 100% consistente entre sí hoy** (uno chequea el string `'Admin'` inline en `business/proforma.py`, otro pasa por `User_Helper`), lo cual es en sí mismo parte de la deuda técnica a considerar al decidir el enfoque.

### Comportamiento actual

Hoy, cualquier usuario staff de Django con permiso de modelo sobre `pago`, `Proxy_Pagos` (reporte de venta diaria), `inventario_proxy` (reporte de storage) o `utilidades` (reporte de utilidad) ve, en el listado del admin, los registros de **todas** las sucursales sin restricción — sin importar a qué sucursal pertenezca el usuario vía `Sucursal.empleado`, y sin importar su grupo. Esto contrasta con `Proforma_Header`, `Nota_trabajo`, `Nota_Venta` e `inventario`, donde el listado ya se restringe a la sucursal del usuario (con distintas variantes de qué rol ve "todo"). El reporte de notas de trabajo finalizadas (`ReportNotaTrabajoAdmin`, vía `Proxy_Nota_trabajo`) tampoco filtra, porque su único filtro de sucursal está comentado en el código fuente.

### Restricciones

- `docs/CLAUDE.md`: "Antes de cambios que afecten varios archivos, proponer un plan y esperar confirmación" — aplica: la solución toca como mínimo 5 archivos (`pagos.py`, `report_daily_sell.py`, `report_storage.py`, `report_utilidad.py`, `orden_trabajo.py`, más posiblemente `report_nota_trabajo.py` y `helper/user.py`).
- `docs/CLAUDE.md`: "Todo cambio de lógica de negocio lleva su test" — este cambio es explícitamente de control de acceso a datos financieros (pagos, utilidad, costos), por lo que aplica de lleno; hoy `product/tests.py` es boilerplate (confirmado también en `docs/integration-and-backlog.md:190-196`, backlog #8), así que probablemente haga falta harness mínimo antes de poder testear esto con confianza.
- No editar migraciones ya aplicadas — no se anticipa necesidad de migraciones para esta tarea (no hay cambios de modelo previstos; los grupos de Django no requieren migración de esquema, solo datos), pero si la decisión de arquitectura terminara requiriendo un campo/modelo nuevo para roles, esta regla aplicaría.
- "Si algo no se puede verificar en el código, decirlo; no inventar" — aplica directamente a la existencia del grupo "Caja": se declara como no verificable desde este entorno, no se asume ninguna respuesta.

### Riesgos identificados

- **Inconsistencia de qué rol "ve todo"**: hoy solo `'Admin'` tiene ese atajo (y solo en `Proforma_Business`, no en `NotaVentaAdmin`/`NotaTrabajoAdmin`). Si la intención de negocio es que un futuro grupo "Caja" también vea todas las sucursales (o, al revés, que "Caja" sea el rol que NO ve todas mientras que otro sí), aplicar el patrón equivocado a los 4-5 admins de este backlog puede ocultar datos a quien sí debería verlos, o exponerlos a quien no debería — exactamente el tipo de decisión que la pregunta del usuario busca evitar tomar a ciegas.
- **Bug ya presente de "Admin sin sucursal ve cero"**: si se copia el patrón de `NotaVentaAdmin`/`NotaTrabajoAdmin` (sin atajo de rol) en vez del de `ProformaAdmin` (con atajo), cualquier usuario administrativo sin `Sucursal.empleado` asignada quedaría sin poder ver pagos/reportes, replicando un bug de UX ya existente en otros dos admins.
- **SEC-07 (condición de carrera por mutación de `self` en `changelist_view`)**: riesgo de repetir este antipatrón si la solución sigue el ejemplo de `InventoryAdmin` al pie de la letra para variar columnas por rol.
- `ReportStorageAdmin` calcula `self.aggregated_result` (atributo de **clase**, no de instancia, definido en la línea 62 fuera de cualquier método) dentro de `get_queryset` y lo lee después en `get_metros_disponibles` — si se agrega un filtro por sucursal aquí, hay que tener cuidado de que el filtro se aplique tanto al `aggregated_result` (usado para calcular "metros disponibles") como al queryset principal, o los números mostrados quedarán inconsistentes entre sí (aparte del riesgo de condición de carrera ya heredado de ser un atributo compartido entre requests).
- El alcance real de "reportes del admin" mencionado por el usuario podría interpretarse como incluyendo también `ReportNotaTrabajoAdmin` (que hoy tiene el filtro comentado) aunque no esté nombrado en el título del ítem #10 del backlog — se investigó y se documenta aquí, pero la decisión de incluirlo o no en el mismo cambio queda para `delivery-architect`/`delivery-plan`.

### Veredicto de complejidad

**NEEDS_ARCHITECTURE** — Aunque mecánicamente el cambio es "aplicar un `get_queryset` filtrado por sucursal" a varios `ModelAdmin` (lo que por sí solo sería un `NEEDS_PLAN`), la tarea encaja directamente en el indicador "cambios de autenticación/autorización": antes de tocar código hace falta decidir **el modelo de roles** que gobierna el acceso — confirmar si el grupo "Caja" existe y, en cualquier caso, qué rol(es) deben ver todas las sucursales frente a solo la propia (pregunta de negocio ya señalada como abierta en `docs/integration-and-backlog.md:241` y `docs/backend-audit.md:615,621`, y sin resolver hoy). Además, ya existen **dos patrones distintos e inconsistentes entre sí** en el propio código (`Proforma_Business` con atajo de rol string vs. `User_Helper`/`InventoryAdmin` vs. `NotaVentaAdmin`/`NotaTrabajoAdmin` sin atajo), y elegir/unificar cuál seguir — o si conviene centralizarlo en un solo lugar en vez de seguir duplicándolo en un tercer archivo — es una decisión de arquitectura, no de implementación directa. Impacta además a 4-6 archivos y su corrección afecta a "quién ve qué dinero", un dato sensible del negocio.

## Arquitectura

**[ADR-002: Centralizar en User_Helper qué roles ven todas las sucursales, y aplicar el filtro por sucursal a Pagos/Reportes/NotaTrabajo del admin](../adr/ADR-002-filtrado-sucursal-pagos-reportes-admin.md)**

Decisión: agregar `is_request_user_caja` y `can_view_all_sucursales` (Admin o Caja) a `User_Helper`; agregar `Pago_Business.get_pago_queryset_by_role` (usado por `PagosAdmin` y `ReportDailySellAdmin`), `Inventario_Business.get_inventario_queryset_by_role` (usado por `ReportStorageAdmin` y `ReportUtilidadAdmin`), y corregir `Orden_Trabajo_Business.get_finish_nota_queryset` (acepta `user`, filtro descomentado, usado por `ReportNotaTrabajoAdmin`) — todos siguiendo la convención `get_*_queryset_by_role(user, qs)` ya usada por `Proforma_Business`. Fuera de alcance (decisión explícita del usuario): unificar `Proforma_Business.get_proforma_queryset_by_role` a `User_Helper`, corregir el bug de "Admin sin sucursal ve vacío" en `NotaVentaAdmin`/`NotaTrabajoAdmin`, y resolver SEC-07 (mutación de estado compartido en `changelist_view`). Sin migraciones; rollback por `git revert` simple. Ver el ADR para las alternativas descartadas y el detalle de `ReportStorageAdmin.aggregated_result`.

## Plan

[PLAN-2026-09-21-filtrado-sucursal-pagos-reportes-admin.md (v1)](../plans/PLAN-2026-09-21-filtrado-sucursal-pagos-reportes-admin.md)

Alcance: `User_Helper.is_request_user_caja`/`can_view_all_sucursales`; `Pago_Business.get_pago_queryset_by_role` (usado por `PagosAdmin` y `ReportDailySellAdmin`); `Inventario_Business.get_inventario_queryset_by_role` (usado por `ReportStorageAdmin`, incluyendo su `aggregated_result`, y `ReportUtilidadAdmin`); `Orden_Trabajo_Business.get_finish_nota_queryset` corregido (usado por `ReportNotaTrabajoAdmin`). Tests unitarios de cada método `business/`/`helper/` nuevo o modificado, más un test de wiring por cada `ModelAdmin.get_queryset` tocado (5 admins). Sin E2E (cambio vive solo en el admin de Django, sin flujo de usuario en Angular). Sin migraciones ni dependencias nuevas. Fuera de alcance: `Proforma_Business`, `NotaVentaAdmin`/`NotaTrabajoAdmin`, SEC-07.

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
