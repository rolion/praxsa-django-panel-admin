# ADR-modulo-vehiculos-soft-delete: Campo `is_active` con filtrado por defecto para Marca/Modelo/Item, sin cascada automática

**Estado:** Propuesto
**Task relacionado:** TASK-modulo-vehiculos
**Fecha:** 2026-09-26

## Contexto

El pedido exige borrado lógico para Marca, Modelo e Item (punto 17): no eliminar físicamente, no aparecer en listas normales ni en selectores, no poder re-asociarse, mantener el historial. La investigación del task encontró **tres mecanismos de soft-delete distintos y no unificados** ya convivientes en el proyecto:

1. `Proforma_Header.is_delete` (`praxsa_manager/product/models.py:173`) — un booleano que **nunca se usa para filtrar ninguna query** en ningún lugar del código (solo está oculto del formulario de Django Admin vía `exclude`, `docs/backend-audit.md:539-540`). Es decorativo, no una implementación funcional de soft-delete.
2. `User.is_active` (campo nativo de Django) — **sí funciona de verdad**: `UserListCreateView.get_queryset()` (`praxsa_manager/product/custom_views/user_admin.py:26-30`) filtra `is_active=True` por defecto y solo lo desactiva con el query param explícito `?include_inactive=true`.
3. Borrado físico real para `Group`/`Sucursal` (`GroupDetailView`/`SucursalDetailView`, `user_admin.py:116-120,141-145`) — no aplica acá, el pedido exige explícitamente que no se borre físicamente.

Ninguno de los 3 modelos afectados (`Car_Brand`, `Car_Model`, `Car_Part`) tiene hoy ningún campo de estado/actividad.

## Decisión

1. **Agregar `is_active = models.BooleanField(default=True)` a `Car_Brand`, `Car_Model` y `Car_Part`** (una migración nueva, aditiva — no se toca ninguna migración existente, cumpliendo la regla de `docs/CLAUDE.md`: "no editar migraciones ya aplicadas").
2. **Replicar el patrón que ya funciona** (`UserListCreateView`, punto 2 arriba), no el decorativo: cada vista de listado (`Car_Brand`, `Car_Model`, `Car_Part`) filtra `is_active=True` por defecto en `get_queryset()`, con el mismo query param `?include_inactive=true` para que el panel pueda, si se decide más adelante, mostrar un listado de inactivos — el pedido no exige esa vista, así que no es obligatorio construirla ahora en el frontend, pero el backend queda preparado sin costo adicional al copiar el patrón existente.
3. **"Eliminar" desde el panel = `PATCH is_active=false`** sobre el registro (mismo endpoint dedicado que ya existe para usuarios, `UserToggleActiveView`, `user_admin.py:82-106` — se replica esa forma para Marca/Modelo/Item), no un `DELETE` HTTP real.
4. **Los selectores usados al crear/editar (selector de Marca en el formulario de Modelo, resultados de "buscar item existente" al asociar a un Modelo) deben consumir el mismo endpoint filtrado por `is_active=True`** — no un endpoint distinto sin filtro. Esto cumple directamente "no deben aparecer en selectores" y "no deben poder asociarse nuevamente" (punto 17).
5. **Sin cascada automática**: desactivar una Marca no desactiva sus Modelos existentes, ni desactivar un Modelo desasocia sus Items. Los Modelos/Items ya existentes bajo una Marca/Modelo inactivo siguen visibles con su historial intacto (cumple "mantener la información histórica existente"); lo único que cambia es que esa Marca/Modelo inactivo deja de estar disponible para *nuevas* asociaciones (por el punto 4). Ningún dato deja de ser consistente porque las FK ya son `on_delete=models.DO_NOTHING` (`Car_Model.car_brand_id`, `Car_Model_Part`) — desactivar nunca implica borrar ni tocar la FK.

## Alternativas consideradas

- **Reutilizar `is_delete` (patrón de `Proforma_Header`).** Descartado: es decorativo, nunca filtra ninguna query real hoy; copiarlo significaría reconstruir de cero toda la lógica de filtrado igual que con un campo nuevo, sin ninguna ganancia de consistencia real (la "consistencia" sería solo de nombre, no de comportamiento).
- **Campo `deleted_at` (timestamp nullable) en vez de booleano.** Se descarta por sobreingeniería: el pedido no pide saber *cuándo* se eliminó un registro, solo que no aparezca más en listas/selectores; un booleano es lo mínimo que resuelve el requerimiento, y es exactamente el tipo de campo que ya funciona en el precedente de `User.is_active`. Si en el futuro el negocio pide auditoría de fecha de baja, se puede agregar `deleted_at` como campo adicional sin tocar `is_active`.
- **Cascada automática (desactivar Marca desactiva sus Modelos, y estos sus Items asociados).** Se descarta: el pedido no lo pide, ningún otro soft-delete del proyecto hace cascada, y añadiría un efecto secundario no solicitado y potencialmente sorpresivo (un admin que desactiva una Marca por error de nombre no espera que eso apague en cascada modelos e items que sí se siguen usando). Si el negocio confirma que sí lo quiere, es una decisión de negocio explícita a pedir, no una inferencia de este ADR.
- **Manager personalizado (`ActiveManager`) que excluye inactivos por defecto a nivel de modelo, en vez de filtrar explícitamente en cada vista.** Se descarta por ahora: ningún modelo del proyecto usa managers personalizados hoy (confirmado en la investigación, sin resultados de managers custom en `product/`), y el patrón ya probado (`UserListCreateView`) filtra explícitamente en la vista. Introducir un manager custom aquí sería la primera instancia de ese patrón en el proyecto sin que el pedido lo requiera — se prefiere consistencia con lo que ya existe y funciona.

## Estrategia de rollback / mitigación

Migración aditiva (agrega 3 columnas `is_active` con `default=True`) — no reversible con pérdida de datos porque no borra ni transforma nada existente; un `migrate` hacia atrás simplemente quita las columnas, y todos los registros actuales (que hoy no tienen concepto de "inactivo") quedan interpretados como activos por el default, sin necesidad de backfill manual. Si el filtrado por defecto en `get_queryset()` resultara demasiado agresivo en producción (por ejemplo, se descubre un consumidor externo que esperaba ver todo sin filtrar), el rollback es inmediato y de bajo riesgo: quitar el filtro de la vista específica es un cambio de una línea, sin tocar la migración ni los datos.

## Consecuencias

- Marca/Modelo/Item ganan un comportamiento de soft-delete que **realmente funciona** (a diferencia del `is_delete` decorativo ya existente en el proyecto), sin inventar un mecanismo nuevo — es el mismo patrón que ya se probó con Usuarios.
- El proyecto sigue teniendo 3 (ahora 4, contando este) patrones de estado/borrado distintos convivientes (`is_delete` decorativo de Proforma, `is_active` de User, borrado físico de Group/Sucursal, `is_active` nuevo de Vehículos) — no es este ADR el que unifica todo el proyecto a un solo mecanismo; eso sería sobreingeniería fuera de alcance de esta tarea. Se deja constancia de que, si en el futuro se quiere consolidar, `Proforma_Header.is_delete` es el candidato más urgente a arreglar por ser el único que no filtra nada pese a existir.
- Los endpoints de listado para selectores (Marca en el form de Modelo, búsqueda de Item para asociar) quedan atados al mismo filtro `is_active=True` que el listado principal — no hay riesgo de que un selector muestre algo que la lista no muestra.
