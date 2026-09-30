# ADR-estados-proforma-nota-trabajo-nota-venta-maquina-de-estados: Estado explícito por documento, nota de venta creada con la nota de trabajo, y transiciones centralizadas en un solo servicio

**Estado:** Propuesto
**Task relacionado:** TASK-estados-proforma-nota-trabajo-nota-venta
**Fecha:** 2026-09-30

## Contexto

La investigación del task (`docs/tasks/TASK-estados-proforma-nota-trabajo-nota-venta.md`) encontró que hoy:

- Solo `Proforma_Header` tiene `status` (`models.py:184`), y es **derivado**: `Proforma_Business.refresh_status` (`business/proforma.py:30-50`) lo recalcula por `hasattr()` de relaciones, con la misma lógica copiada en `ProformaAdmin.get_estado` (`proforma_admin.py:96-109`) y en la migración `0106`. `Nota_trabajo` y `Nota_Venta` no tienen estado; se infiere de `is_close`, que significa cosas distintas en cada modelo (`proforma.py:127`, `:218`; `pago.py:36-43`).
- "Finalizado" significa tres cosas distintas (proforma: existe un `pago`; nota de venta: `pago.cerrado`; nota de trabajo: existe la nota de venta).
- `refresh_status` no se llama al crear el pago (`pagos.py:88-96`), así que el valor persistido puede divergir del que muestra el admin.
- No hay estado de anulación; `abrir_proforma` deja viva la nota de trabajo y no revisa la nota de venta (`proforma.py:63-84`); no hay endpoint ni pantalla de nota de venta/pago (solo Django Admin).
- La transición se dispersa en 5 lugares (`create_work_note`, `abrir_proforma`, `crear_nota_venta`, `cerrar_pago`, `delete_work_note`) y en las acciones de 3 `ModelAdmin`.

El DDR `DDR-estados-proforma-nota-trabajo-nota-venta-estados-y-cobro` fija lo que la persona ve (vocabulario unificado; "Finalizado" = terminado y pagado; estado global derivado en el listado de proformas). Este ADR define el modelo que lo sostiene. Reemplaza **parcialmente** a `ADR-006-proforma-status-field`: se conserva la idea de un único punto de cálculo y de `Proforma_Header.status` como estado global persistido, pero se abandona el `hasattr()` como fuente de verdad y el compromiso de dejar `ProformaAdmin.get_estado` intacto (decisiones 2 y 3 de ese ADR).

Respuestas del usuario que condicionan la decisión:
- **Backfill:** a las notas de trabajo existentes sin nota de venta se les crea una nota de venta `por_cobrar`.
- **Anticipos:** el usuario preguntó cómo funciona hoy. Verificado en código: hoy **no se puede pagar antes de cerrar el trabajo**, pero la compuerta es indirecta — el `pago` exige una `Nota_Venta`, y esta solo se crea a mano (`crear_nota_venta`, `proforma.py:201-223`) cuando ya hay garantía e instalador; **`salida_vehiculo` nunca se valida** (`grep`: solo aparece en modelo, admin y serializer). `PagosForm` (`Forms/pagos.py`) no agrega validación de estado ni de monto. Es decir: en la práctica se paga después de que alguien decidió que el trabajo terminó, pero el sistema no lo comprueba. Se conserva esa regla (sin anticipos) y se hace explícita y validada en servidor. Queda aislada en una única precondición para que admitir anticipos sea un cambio de una línea (más un caso en el estado global), no un rediseño.

## Decisión

### 1. Un estado explícito y persistido por documento

| Modelo | Campo | Valores | Fuente de verdad de… |
|---|---|---|---|
| `Nota_trabajo` | `status` (nuevo) | `en_proceso`, `terminado`, `cancelada` | ciclo de la ejecución del trabajo |
| `Nota_Venta` | `status` (nuevo) | `por_cobrar`, `pagada`, `anulada` | ciclo del cobro |
| `Proforma_Header` | `status` (existente, valores cambian) | `proforma`, `en_trabajo`, `por_cobrar`, `finalizado`, `anulada` | **estado global de la orden** (denormalizado, solo lectura) |
| `pago` | `cerrado` (existente) | bool | únicamente el cierre contable; ya no cascada a otros documentos |

- `Proforma_Header.status` **no se escribe a mano en ningún sitio**: es el resultado de una función pura `calcular_estado_orden(proforma)` que lo deriva de los estados de la nota de trabajo y la nota de venta (y de un marcador de anulación), y se persiste al final de cada transición. Mapa: sin nota de trabajo vigente → `proforma`; NT `en_proceso` → `en_trabajo`; NT `terminado` + NV `por_cobrar` → `por_cobrar`; NT `terminado` + NV `pagada` → `finalizado`; proforma anulada → `anulada`. Renombrar `nota_trabajo`→`en_trabajo` y agregar `anulada` cambia los valores del filtro `?status=` y de `status`/`status_label` de la API; el único consumidor conocido es `panel_admin/` (se actualiza en el mismo release).
- El badge "Aprobada" de la proforma del DDR no necesita columna: se deriva de `status` (`proforma`→Vigente, `anulada`→Anulada, resto→Aprobada).
- **Se mantienen `is_close` (en los tres modelos) sin borrar columnas**, pero pasan a ser **campos legados derivados**, escritos únicamente por el servicio de transiciones para no romper Django Admin y los guards actuales (`has_change_permission`, `ordenes_admin.py:116,222`): `proforma.is_close = (status != vigente)`; `nota_trabajo.is_close = (status != en_proceso)`; `nota_venta.is_close = (status != por_cobrar)`. Ningún código nuevo lee `is_close` para decidir; leen `status`. Su eliminación queda para un cambio posterior.

### 2. Un único servicio de transiciones

Nuevo `Orden_Estado_Business` (`business/orden_estado.py`) y una tabla declarativa de transiciones permitidas (constante en `helper/`, siguiendo la convención de `Proforma_Helper`). Es el **único** lugar que escribe estados. Cada método: abre `transaction.atomic`, bloquea la proforma con `select_for_update` (patrón ya usado en `ProformaGenerateNotaView`, `ordenes_admin.py:135`), valida `(estado actual → destino)` contra la tabla y las precondiciones, aplica efectos, recalcula el estado global y devuelve el resultado. Una transición inválida lanza una excepción de negocio que la API traduce a **409** con mensaje legible.

| Método | Documento: de → a | Precondiciones (servidor) | Efectos |
|---|---|---|---|
| `aprobar_proforma` | Proforma vigente; NT `∅|cancelada→en_proceso`; NV `∅|anulada→por_cobrar` | Proforma en `proforma`; validaciones actuales de stock y ancho | Descuenta inventario (lógica actual de `create_work_note`); crea o **reutiliza** NT y NV (OneToOne) y **refresca el snapshot** `total = total_price − discount`; `entrada_vehiculo = now` |
| `terminar_trabajo` | NT `en_proceso→terminado` | Si `venta_instalacion`: `codigo_garantia` e `instaladar` presentes (reglas hoy en `crear_nota_venta`, `proforma.py:204-208`) | `salida_vehiculo = now` si está vacía |
| `corregir_trabajo` | NT `terminado→en_proceso` | NV en `por_cobrar` | — |
| `registrar_pago` | NV `por_cobrar→pagada` | NT `terminado` (**única** precondición de anticipos); no existe `pago` | Crea `pago` con `monto = nota_venta.total_price` **calculado en servidor** (se ignora cualquier monto del cliente), `cerrado=False`, `created_by` |
| `anular_pago` | NV `pagada→por_cobrar` | `pago.cerrado == False` | Elimina el `pago` (registrado en el log) |
| `reabrir_proforma` | Proforma aprobada→vigente; NT `en_proceso→cancelada`; NV `por_cobrar→anulada` | NT `en_proceso` y NV `por_cobrar` | Devuelve inventario (lógica actual de `abrir_proforma`) |
| `anular_proforma` | Proforma vigente→`anulada` | Sin nota de trabajo vigente | Marca la anulación (no usa `is_delete`, que sigue siendo el borrado oculto) |
| `cerrar_pago` (contable) | `pago.cerrado=True` | `pago` existente | Solo el flag; no cambia ningún estado |

Los métodos legados de negocio (`create_work_note`, `abrir_proforma`, `crear_nota_venta`, `cerrar_pago`, `refresh_status`, `delete_work_note`) se convierten en **delegadores finos** al servicio (o se eliminan si nadie los usa), de modo que Django Admin y la API pasan por el mismo camino y no puede volver a haber dos lógicas. `crear_nota_venta` desaparece como acción (la nota de venta ya nace en la aprobación); `create_nota_venta_pago` y `delete_proforma`, que hoy referencian campos inexistentes (`business/proforma.py:52-61, 301-314`), se eliminan.

### 3. Nota de venta nace con la nota de trabajo

`aprobar_proforma` crea la `Nota_Venta` en la misma transacción que la nota de trabajo. Consecuencias resueltas:
- El bloqueo de edición de la nota de trabajo (`ordenes_admin.py:222`) deja de mirar `hasattr(nota,'nota_venta')` y pasa a `status != en_proceso`.
- `is_finalizada` (`ordenes_serializer.py:307-308`) se elimina de la API y se reemplaza por `status`/`status_label` de la NT más un resumen `nota_venta {id, status, status_label, total_price}`.
- `get_finish_nota_queryset` (`orden_trabajo.py:45-60`, filtro `nota_venta__isnull=False`) pasa a filtrar por `status`.
- `delete_work_note` (borrado físico desde Django Admin, `orden_trabajo.py:74-109`) deja de bloquear por "existe nota de venta" (ahora siempre existe): bloquea si la NV está `pagada`/tiene `pago`; en otro caso elimina NV y NT como hoy y devuelve el inventario.
- Si la proforma se reabre y se edita, el snapshot no queda viejo: reabrir anula la NV y volver a aprobar la **reutiliza y refresca** (decisión abierta en la investigación).

### 4. Migración de datos

Una migración `0111_…` (la última es `0110_inventario_is_active`), **aditiva** en esquema, con `RunPython` de backfill y `reverse_code` real:
- Agrega `Nota_trabajo.status` (default `en_proceso`) y `Nota_Venta.status` (default `por_cobrar`); actualiza `choices` de `Proforma_Header.status`.
- Backfill de `Nota_Venta.status`: con `pago` → `pagada`, si no → `por_cobrar`. Backfill de `Nota_trabajo.status`: con nota de venta existente → `terminado`; sin nota de venta → `en_proceso` **y se le crea una `Nota_Venta` `por_cobrar`** (total = `total_price − discount` de su proforma; `created_by` = `responsable` o, si falta, `proforma.created_by`; `created_on` = ahora). Las notas de trabajo con `proforma` NULL (permitido por `models.py:201`) se **omiten** y se registran en el log (no se puede calcular el total).
- Recalcula `Proforma_Header.status` con la nueva función (la lógica se copia dentro de la migración, como hizo `0106`, porque no puede importar código de la app).
- `reverse_code`: elimina las `Nota_Venta` sin `pago` cuya nota de trabajo esté `en_proceso` (en el modelo anterior una nota de venta nunca coexiste con una NT abierta) y recalcula `Proforma_Header.status` al vocabulario anterior; luego el esquema revierte solo.

### 5. Django Admin

Las acciones de los tres `ModelAdmin` se reconectan al servicio (misma lógica, un solo camino): "crear/actualizar nota trabajo"→`aprobar_proforma`, "abrir proforma"→`reabrir_proforma`, "crear nota venta" se retira de `NotaTrabajoAdmin` y se reemplaza por "Marcar trabajo terminado", "Gestionar Pago"→`registrar_pago`, "concluir transaccion"→`cerrar_pago`. Los tres `get_estado` pasan a leer `status`. Los tests `tests/test_proforma_status_field.py` (paridad con `get_estado`, hoy `:62-148`) se sustituyen por tests de la tabla de transiciones y de la función de estado global.

## Alternativas consideradas

- **Solo `Proforma_Header.status` derivado, sin estado en NT/NV (statu quo mejorado).** Menos migración, pero deja los tres significados de "Finalizado" y no permite `cancelada`/`anulada` ni consultar estados de nota de venta sin joins. Se descarta: no resuelve el problema.
- **Un solo campo de estado en `Proforma_Header` con todos los pasos del pipeline, sin estado propio en NT/NV.** Es lo que sugería ADR-006. Se descarta: cuando la nota de venta nace con la nota de trabajo, dos ciclos (trabajo y cobro) avanzan en paralelo y un único enum lineal no puede expresar "trabajo en proceso, cobro pendiente" sin explotar en combinaciones; además el panel necesita filtrar notas de venta por estado.
- **`django-fsm` o librería de máquina de estados.** Se descarta: agrega una dependencia (regla de `docs/CLAUDE.md`: no agregar dependencias sin avisar) para 3 documentos y ~8 transiciones; una tabla declarativa + un servicio bastan.
- **Trigger/constraint en base de datos para validar transiciones.** Se descarta por ahora: hay datos históricos que pueden violar secuencias esperadas (mismo argumento de ADR-006 decisión 5); se refuerza en servidor y se deja `CheckConstraint` para después de estabilizar los datos.
- **Registro de auditoría de transiciones (tabla de eventos).** Se descarta en este task por sobreingeniería: el requerimiento no lo pide; `salida_vehiculo`, `entrada_vehiculo`, `Nota_Venta.created_on` y `pago.created_on` cubren los hitos principales. Queda como mejora si negocio la solicita.
- **Anticipos permitidos.** No se adopta (ver contexto); la precondición de `registrar_pago` es el único punto a cambiar si negocio lo pide.
- **Borrar las columnas `is_close` ahora.** Se descarta: rompería Django Admin y agrandaría el PR; se dejan como legado derivado.

## Estrategia de rollback / mitigación

Cambio sensible: toca base de datos, lógica de dinero (pagos) y autorización de acciones.
- **Antes de desplegar:** backup completo de la base (obligatorio en producción) y ensayo del `migrate` y de `migrate product 0110` (reverso) sobre una copia con datos reales.
- **Migración reversible** (decisión 4): esquema aditivo; el reverso elimina las notas de venta de relleno (las únicas que rompen el modelo anterior si el código se revierte) y restaura los valores de `Proforma_Header.status`.
- **Orden de reversión:** `git revert` del PR **más** `migrate product 0110`. Revertir solo el código dejaría notas de trabajo abiertas con nota de venta, que el código anterior interpreta como bloqueadas (`ordenes_admin.py:222`); por eso el reverso debe ejecutarse siempre.
- **Despliegue:** backend y `panel_admin` salen juntos (cambian los valores de `status` y desaparece `is_finalizada`); no se soporta un panel viejo contra el backend nuevo.
- **Sin feature flag:** el cambio de semántica es de datos, no conmutable a mitad de camino sin dos caminos de código; se prefiere la migración reversible.
- **Riesgos y mitigaciones:** (a) doble cobro o transición concurrente → `select_for_update` sobre la proforma + `OneToOne` existentes; (b) pago con monto incorrecto → el monto lo fija el servidor; (c) backfill con datos inconsistentes → omisión con log y reporte de cuántas filas se omitieron para revisión manual; (d) inventario desalineado al reabrir → tests sobre `reabrir_proforma` y `aprobar_proforma` con inventario y verificación en vivo.

## Consecuencias

**Más fácil:** un vocabulario y una regla por documento; una sola función escribe estados; el panel puede filtrar notas de trabajo y de venta por estado; cancelaciones y anulaciones son posibles; Django Admin y API no pueden divergir.

**Más difícil / deuda aceptada:** siguen existiendo tres `is_close` legados y `Proforma_Header.status` denormalizado (dos fuentes que el servicio mantiene sincronizadas, sin constraint que lo garantice en base); no hay auditoría de quién/cuándo cambió cada estado; se cambia un contrato de API interno (`status`, `is_finalizada`); la migración crea notas de venta en producción para trabajos abiertos (decisión de negocio ya tomada); Django Admin convive con la API hasta que se retire. Queda fuera: `CheckConstraint` de secuencia, eliminación de `is_close`, anticipos.
