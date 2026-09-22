# ADR-002: Centralizar en User_Helper qué roles ven todas las sucursales, y aplicar el filtro por sucursal a Pagos/Reportes/NotaTrabajo del admin

**Estado:** Propuesto (corregido el 2026-09-22, ver "Corrección" abajo — el PR aún no se mergeó)
**Task relacionado:** TASK-002
**Fecha:** 2026-09-21

## Corrección (2026-09-22)

Al probar manualmente la rama, el usuario detectó que la decisión original de este ADR ("Admin y Caja ven todas las sucursales") no era la correcta: el requerimiento real es que **solo el grupo `Admin` ve todas las sucursales**; el grupo `Caja` debe comportarse como cualquier usuario sin rol especial — ve únicamente la(s) sucursal(es) a la que está asignado vía `Sucursal.empleado`.

Esto se corrigió antes de mergear (sin necesidad de re-planificar ni reabrir arquitectura desde cero, dado el tamaño mínimo del cambio): `User_Helper.can_view_all_sucursales` ahora devuelve `is_request_user_admin(user)` únicamente, sin el `or is_request_user_caja(user)`. Como los 5 admins y las 3 capas de `business/` ya delegaban en `can_view_all_sucursales` para decidir "ver todo vs. filtrar por sucursal", **no hizo falta tocar ningún otro archivo de código** — un usuario `Caja` cae automáticamente en la misma rama que cualquier usuario sin rol especial (filtrado por su propia sucursal, o lista vacía si no tiene sucursal asignada). El texto de este documento se actualizó para reflejar la decisión corregida; el resto del contenido original (alternativas, rollback) sigue vigente sin cambios.

## Contexto

El ítem #10 del backlog (`docs/integration-and-backlog.md:206-213`, backend `SEC-06`) y la investigación de TASK-002 confirmaron que `PagosAdmin`, `ReportDailySellAdmin`, `ReportStorageAdmin` y `ReportUtilidadAdmin` no filtran sus listados por la sucursal del usuario — cualquier staff con permiso de Django sobre esos modelos ve datos financieros (pagos, costos, utilidad) de **todas** las sucursales. Además, `Orden_Trabajo_Business.get_finish_nota_queryset` (usado por `ReportNotaTrabajoAdmin`) tiene ese mismo filtro explícitamente comentado.

Ya existen admins que sí filtran correctamente (`ProformaAdmin`, `NotaVentaAdmin`, `NotaTrabajoAdmin`, `InventoryAdmin`), pero con **dos patrones distintos e inconsistentes entre sí**:
- `Proforma_Business.get_proforma_queryset_by_role` chequea el string `'Admin'` directamente contra `request.user.groups`, con un atajo explícito para ver todas las sucursales.
- `InventoryAdmin` usa `User_Helper.is_request_user_admin`/`is_request_user_supervisor` (helper ya centralizado, pero limitado a los roles `admin`, `instalador`, `supervisor` — no conoce ningún rol `caja`).
- `NotaVentaAdmin`/`NotaTrabajoAdmin` no tienen ningún atajo de rol: filtran siempre por la sucursal del usuario, sin excepción — lo que hoy deja a un usuario Admin sin sucursal asignada viendo listas vacías (bug preexistente, confirmado en la investigación).

Se resolvió con el usuario, antes de diseñar esta decisión, lo siguiente:
- El grupo Django **"Caja" ya existe** en el ambiente real (no hace falta crearlo).
- Deben ver datos de **todas** las sucursales en Pagos/Reportes solo el grupo **"Admin"**; el grupo **"Caja"** y cualquier otro usuario ven solo su propia sucursal (corregido el 2026-09-22 — ver "Corrección" arriba; la primera versión de esta decisión incluía por error también a "Caja" en el atajo de ver todo).
- El filtro comentado en `Orden_Trabajo_Business.get_finish_nota_queryset` (usado por `ReportNotaTrabajoAdmin`) se corrige en el mismo cambio, porque es la misma causa raíz (SEC-06) aunque no esté nombrado en el título del ítem #10.
- El bug ya existente de "Admin sin sucursal ve listas vacías" en `NotaVentaAdmin`/`NotaTrabajoAdmin` **queda fuera de alcance** de este cambio — no se toca.

## Decisión

1. **Extender `User_Helper`** ([helper/user.py](../../praxsa_manager/product/helper/user.py)) con:
   - `is_request_user_caja(user)` — mismo patrón que los tres métodos `is_request_user_*` existentes (chequeo de grupo en minúsculas). Se mantiene como primitivo reutilizable aunque, tras la corrección, `can_view_all_sucursales` ya no lo use.
   - `can_view_all_sucursales(user)` — devuelve `is_request_user_admin(user)`. Este es el único lugar del código que decide "qué roles ven todas las sucursales" para los admins de este cambio; hoy es exclusivamente el grupo `Admin`.

2. **Agregar un método `get_*_queryset_by_role(user, qs)` a la capa de `business/` correspondiente a cada modelo**, replicando la firma y estructura ya usada por `Proforma_Business.get_proforma_queryset_by_role`/`get_nota_venta_queryset_by_role` y `Orden_Trabajo_Business.get_nota_queryset_by_role`:
   - `Pago_Business.get_pago_queryset_by_role` ([business/pago.py](../../praxsa_manager/product/business/pago.py)) — usado por **`PagosAdmin`** y **`ReportDailySellAdmin`** (ambos exponen el modelo `pago`/`Proxy_Pagos`, misma ruta de relación `nota_venta__nota_trabajo__proforma__sucursal`).
   - `Inventario_Business.get_inventario_queryset_by_role` ([business/inventario.py](../../praxsa_manager/product/business/inventario.py)) — usado por **`ReportStorageAdmin`** y **`ReportUtilidadAdmin`** (ambos exponen `inventario`/`inventario_proxy`/`utilidades`, con FK directa `sucursal`).
   - `Orden_Trabajo_Business.get_finish_nota_queryset` — se modifica para aceptar `user`, se descomenta el filtro y se reemplaza el chequeo comentado por `User_Helper.can_view_all_sucursales`. Usado por **`ReportNotaTrabajoAdmin`**.

   Cada método sigue la misma forma: si `can_view_all_sucursales(user)` es `True`, devuelve el queryset sin filtrar por sucursal (pero conservando cualquier filtro de negocio ya existente, p. ej. `is_delete=False` donde aplique); si no, filtra por la(s) sucursal(es) de `Sucursal.objects.filter(empleado__id=user.id, enable_to_install_windows_film=True)` — mismo criterio que ya usan `Proforma_Business`/`Orden_Trabajo_Business` hoy — y si el usuario no tiene sucursal asignada, devuelve `None` (mismo contrato que los métodos `*_queryset_by_role` existentes, que el admin ya sabe interpretar mostrando "Asigne una sucursal al usuario").

   Como el atajo de "ver todo" se evalúa **antes** de requerir una sucursal, un usuario Admin sin sucursal asignada sigue viendo todos los datos — este diseño no reintroduce ni depende de corregir el bug ya excluido de alcance. Un usuario Caja sin sucursal asignada, en cambio, cae en la rama de "sin sucursal" como cualquier otro usuario sin rol especial (lista vacía + mensaje de error) — comportamiento correcto y esperado, ya que Caja ya no tiene el atajo de ver todo.

3. Cada `ModelAdmin` (`PagosAdmin`, `ReportDailySellAdmin`, `ReportStorageAdmin`, `ReportUtilidadAdmin`, `ReportNotaTrabajoAdmin`) llama al método de `business/` correspondiente desde su `get_queryset`, con el mismo patrón de manejo de `None` (mensaje de error + `qs.filter(sucursal=-1)`/equivalente) ya usado por `ProformaAdmin`/`NotaVentaAdmin`.

4. **`ReportStorageAdmin`** requiere atención adicional al implementar (detalle para `delivery-plan`, no arquitectónico): además de filtrar el `qs` principal, el atributo `aggregated_result` (usado por `get_metros_disponibles`) se calcula con una query aparte sobre `inventario.objects` y debe recibir el mismo filtro de sucursal, o los "metros disponibles" mostrados quedarían inconsistentes con las filas visibles.

## Alternativas consideradas

- **Repetir el chequeo de grupo inline en cada método nuevo** (como ya hace `Proforma_Business.get_proforma_queryset_by_role` con el string `'Admin'`), sin pasar por `User_Helper`. Rechazada: duplicaría la lógica de "qué roles ven todo" una quinta vez en el código, exactamente el problema de inconsistencia que esta tarea busca no empeorar.
- **Unificar de una vez todos los admins existentes** (migrar también `Proforma_Business`, `NotaVentaAdmin`, `NotaTrabajoAdmin` a `User_Helper.can_view_all_sucursales`, y de paso corregir el bug de "Admin sin sucursal"). Rechazada para este cambio: el usuario decidió explícitamente mantener ese bug fuera de alcance, y tocar código que hoy funciona correctamente (`ProformaAdmin`) sin necesidad viola la regla del proyecto "cambios pequeños: un objetivo por cambio" (`docs/CLAUDE.md`). Queda como mejora futura, no bloqueante.
- **Crear un servicio nuevo y genérico de scoping por sucursal** (p. ej. `business/access_control.py` con una función única reutilizable por todos los admins, presentes y futuros). Rechazada por sobreingeniería: el proyecto ya tiene una convención establecida (`get_*_queryset_by_role` por cada `business/*.py`) que los desarrolladores del proyecto reconocen y siguen; introducir una abstracción nueva para 5 admins no se justifica todavía, y puede reconsiderarse si en el futuro se repite una tercera vez la misma duplicación.

## Estrategia de rollback / mitigación

Cambio de autorización (restringe visibilidad de datos previamente sin restricción), sin migraciones de base de datos ni cambios de esquema — es reversible con un simple `git revert` del PR y redeploy, sin pasos de datos que deshacer.

Riesgo principal: si algún usuario real de producción tiene mal asignada su sucursal (`Sucursal.empleado`) o no pertenece a los grupos `Admin`/`Caja` cuando debería, perdería acceso legítimo a datos que antes veía sin restricción (regresión operativa, no de seguridad). Mitigación:
- Antes de mergear: verificar manualmente en un ambiente no productivo que un usuario del grupo `Admin` ve el listado completo, y que un usuario del grupo `Caja` (o sin ningún grupo especial, con sucursal asignada) ve solo su propia sucursal — como parte de los tests que `delivery-plan` debe definir. (Verificado manualmente por el usuario contra Postgres real el 2026-09-22, que fue justamente lo que detectó la corrección de este ADR.)
- Después de desplegar a producción: chequeo manual rápido (no bloqueante, ~5 minutos) iniciando sesión como un usuario real de `Admin` para confirmar que conserva visibilidad completa en `PagosAdmin`/reportes.
- No se considera necesario un feature flag: el cambio es de bajo impacto de despliegue (una sola app Django, sin coordinación con el frontend Angular ni con infraestructura), totalmente reversible por revert, y consistente con el enfoque incremental que ya usa el proyecto (ver ADR-001).

## Consecuencias

- **Más fácil**: hay un único lugar (`User_Helper.can_view_all_sucursales`) para saber qué roles ven todas las sucursales en los admins de Pagos/Reportes/NotaTrabajo; agregar un futuro rol con el mismo privilegio es una línea.
- **Más difícil / deuda aceptada conscientemente**:
  - `Proforma_Business.get_proforma_queryset_by_role` sigue con su chequeo inline de `'Admin'`, sin pasar por `User_Helper` — inconsistencia preexistente que este cambio no resuelve, documentada aquí para que quede trazable.
  - El bug de "Admin sin sucursal ve listas vacías" en `NotaVentaAdmin`/`NotaTrabajoAdmin` sigue sin corregirse — decisión explícita del usuario, queda como hallazgo abierto para un task futuro.
  - SEC-07 (mutación de atributos de instancia compartida en `changelist_view`, `docs/backend-audit.md:453-458`) no se corrige aquí; los admins de este cambio no necesitan variar `list_display` por rol, así que no se agrega una nueva instancia del problema, pero `ReportStorageAdmin` mantiene su atributo de clase `aggregated_result` (con el filtro de sucursal ya aplicado, pero sin resolver el patrón compartido subyacente).
