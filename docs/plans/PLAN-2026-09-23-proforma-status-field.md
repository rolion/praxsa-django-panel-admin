# PLAN-2026-09-23-proforma-status-field (v1)

**Task:** TASK-009
**ADRs relacionados:** [ADR-006: Campo `status` persistido en `Proforma_Header`](../adr/ADR-006-proforma-status-field.md)

## Objective

Agregar un campo `status` persistido y consultable en `Proforma_Header`, sincronizado explícitamente en cada transición real de negocio (`create_work_note`, `abrir_proforma`, `crear_nota_venta`, `cerrar_pago`), sin romper ni reemplazar todavía el mecanismo actual de inferencia por `hasattr()` que usa el admin para mostrar el estado. Es el paso 1+2 del backlog #9 (`docs/integration-and-backlog.md:241-247`); el paso 3 (constraints + migrar el admin a leer el campo) queda fuera de este plan, según decide ADR-006.

## Context

Ver `docs/tasks/TASK-009.md` (`## Investigación`) para el detalle completo verificado con `archivo:línea`. Resumen mínimo necesario para este plan:

- Hoy no existe ningún campo de estado persistido. `ProformaAdmin.get_estado` ([admin_config/proforma_admin.py:96-111](../../praxsa_manager/product/admin_config/proforma_admin.py)) infiere 4 estados (`Proforma`/`Nota Trabajo`/`Por Cobrar`/`Finalizado`) recorriendo relaciones inversas O2O con `hasattr()`, sin persistir nada.
- Las 4 transiciones reales viven en `Proforma_Business` ([business/proforma.py](../../praxsa_manager/product/business/proforma.py)) y `Pago_Business.cerrar_pago` ([business/pago.py:27-44](../../praxsa_manager/product/business/pago.py)).
- `Proforma_Helper.status`/`default_status` ([helper/proforma.py:5-12](../../praxsa_manager/product/helper/proforma.py)) son constantes huérfanas de un campo `sales_status` eliminado en 2023 (migración `0076`) — sin ningún llamador vivo (verificado con grep). Se repurposan en este plan para el campo nuevo, no se dejan como deuda adicional.
- Última migración aplicada: `0105_alter_pago_registro_contable.py` → la nueva es `0106_...`.
- Cero tests ejercitan hoy estas 4 transiciones.

## Current behavior

Ver "Comportamiento actual" en `docs/tasks/TASK-009.md`. En síntesis: el estado se calcula en tiempo de lectura, nunca se escribe; 4 booleanos independientes (`Proforma_Header.is_close`, `Nota_trabajo.is_close`, `Nota_Venta.is_close`, `pago.cerrado`) gobiernan permisos y precondiciones, pero ninguno es "el estado".

**Detalle verificado en esta planificación, no señalado antes:** `Proforma_Header.proforma_created_on` es `DateTimeField(auto_now=True)` ([models.py:148](../../praxsa_manager/product/models.py)) — pese a su verbose_name "Fecha Proforma" (sugiere fecha de creación), `auto_now=True` hace que **cualquier** `.save()` sin `update_fields` explícito reescriba ese timestamp al momento actual. `abrir_proforma` ya llama `proforma.save()` a secas hoy ([business/proforma.py:55](../../praxsa_manager/product/business/proforma.py)) — comportamiento preexistente, fuera de alcance arreglarlo aquí — pero es la razón concreta por la que el método nuevo de este plan debe usar `update_fields=['status']` explícitamente: si no, cada sincronización de `status` correría el riesgo adicional de mover esa fecha en las proformas que sí pasan por el método nuevo.

## Expected behavior

- `Proforma_Header` nace con `status = 'proforma'` (default a nivel de campo, igual que ya hacen `sales_type`/`origen` en el mismo modelo).
- Al ejecutar `create_work_note` → `status = 'nota_trabajo'`.
- Al ejecutar `abrir_proforma` (reabrir) → `status` vuelve a `'proforma'`.
- Al ejecutar `crear_nota_venta` → `status = 'por_cobrar'`.
- Al ejecutar `cerrar_pago` → `status = 'finalizado'`.
- En cada caso, `proforma.status` debe coincidir exactamente con lo que `ProformaAdmin.get_estado(proforma)` calcularía en ese mismo momento (test de equivalencia — no se cambia qué muestra el admin en este plan, solo se verifica que el campo nuevo sería consistente si se leyera).
- Ningún `.save()` de este cambio debe alterar `proforma_created_on`.

## Architecture considerations

Resumen de ADR-006 (detalle completo en el archivo enlazado arriba):
- Un solo campo en `Proforma_Header`, no uno por modelo.
- Un único método de recálculo (`Proforma_Business.refresh_status`, ver más abajo por qué en `business/` y no en el modelo) llamado desde los 4 sitios de transición, en vez de asignación manual del string en cada uno.
- El `hasattr()` del admin no se toca en este plan.
- Sin nueva dependencia (no `django-fsm`).
- Constraints/validación de invariantes: diferidas a un ADR/task futuro.

**Decisión de implementación no cubierta por el ADR (nivel de detalle de este plan):** `refresh_status` se agrega como método de `Proforma_Business`, no como método del modelo `Proforma_Header`. Es consistente con el patrón ya usado en todo `praxsa_manager/product/`: los modelos son deliberadamente delgados (ningún modelo del dominio tiene métodos de negocio, solo `__str__`), y toda la lógica de transición ya vive en las clases `*_Business`. Poner el método ahí también evita import circular: `business/pago.py` puede importar `business/proforma.py` sin problema (verificado: `proforma.py` no importa `pago.py`), así que `Pago_Business.cerrar_pago` puede llamar `Proforma_Business().refresh_status(proforma)` directamente.

**Contrato API**: sin impacto. Ningún endpoint REST expone `Proforma_Header` con este campo nuevo (el serializer de `/product/invoice` tiene su propia lista explícita de `Meta.fields`, no usa `fields = '__all__'`); Angular no lo ve ni lo necesita.

**Datos existentes / migración**: la migración de esquema es aditiva (columna nueva con default), pero necesita backfill real — un default estático dejaría todas las proformas ya cerradas/pagadas mal etiquetadas como `'proforma'`. El backfill se implementa en el propio `RunPython` de la migración, **replicando la lógica de `hasattr()` inline sobre los modelos históricos** (`apps.get_model`), no llamando a `Proforma_Business.refresh_status` — los modelos históricos de una migración de datos no tienen los métodos de las clases "vivas" del proyecto, solo campos y relaciones, así que la migración necesita su propia copia mínima de la misma lógica de 3 pasos.

**Rendimiento**: el backfill recorre todas las `Proforma_Header` existentes una vez, con `select_related`/`prefetch` sobre la cadena `nota_trabajo__nota_venta__pago` para evitar N+1 (son a lo sumo unos pocos miles de filas según el tamaño actual del negocio, no hace falta batching adicional).

**Seguridad y permisos**: sin cambios — no se toca ningún `get_queryset`/`has_change_permission` en este plan.

## Proposed solution

1. **Modelo**: agregar a `Proforma_Header` ([models.py](../../praxsa_manager/product/models.py), después de `is_close`):
   ```python
   status = models.CharField(choices=helper.status, default=helper.default_status, max_length=20, verbose_name="Estado")
   ```
2. **Helper**: en `Proforma_Helper` ([helper/proforma.py](../../praxsa_manager/product/helper/proforma.py)), reemplazar las constantes huérfanas `prof`/`nov`/`notra`/`status`/`default_status` (sin llamadores vivos, verificado) por:
   ```python
   self.estado_proforma = 'proforma'
   self.estado_nota_trabajo = 'nota_trabajo'
   self.estado_por_cobrar = 'por_cobrar'
   self.estado_finalizado = 'finalizado'
   self.status = [
       (self.estado_proforma, 'Proforma'),
       (self.estado_nota_trabajo, 'Nota Trabajo'),
       (self.estado_por_cobrar, 'Por Cobrar'),
       (self.estado_finalizado, 'Finalizado'),
   ]
   self.default_status = self.estado_proforma
   ```
3. **Migración** `0106_proforma_header_status.py`: `AddField` (con el default de arriba) + `RunPython` que recorra `Proforma_Header.objects.all()` (modelo histórico vía `apps.get_model`) y aplique, por cada fila, la misma cadena de 3 `hasattr()` que hoy usa `ProformaAdmin.get_estado`, escribiendo el valor real. `reverse_code=migrations.RunPython.noop` (al revertir, la columna se elimina con el `AddField` inverso; no hay nada más que deshacer).
4. **`Proforma_Business.refresh_status(self, proforma)`** nuevo en [business/proforma.py](../../praxsa_manager/product/business/proforma.py), calculando el mismo valor con la misma estructura de `early return` que `ProformaAdmin.get_estado` (para que quede visualmente comparable en review), y guardando con `proforma.save(update_fields=['status'])`.
5. Llamar `self.refresh_status(proforma)` al final de:
   - `create_work_note` (después de `proforma.save()` existente en la línea 102, antes de crear la nota de trabajo o después — después, para no sincronizar un estado que luego podría fallar si `create_work_note` de `Orden_Trabajo_Business` lanza excepción).
   - `abrir_proforma` (después de `proforma.save()` existente).
   - `crear_nota_venta` (después de `nota_trabajo.save()` existente; nota: esta transición cambia el status de `nota_trabajo.proforma`, no de un `proforma` local — usar `nota_trabajo.proforma`).
6. En `Pago_Business.cerrar_pago` ([business/pago.py](../../praxsa_manager/product/business/pago.py)), importar `Proforma_Business` y llamar `Proforma_Business().refresh_status(proforma)` al final (después de que `proforma.save()`/`nota_trabajo.save()` existentes ya corrieron).
7. **No se toca** `ProformaAdmin.get_estado`, `NotaVentaAdmin.get_estado`, `NotaTrabajoAdmin.get_estado`, ni ningún `has_change_permission`/`get_readonly_fields` existente — quedan exactamente como están.

## Files/components affected

**Backend** (`praxsa_manager/product/`):
- `models.py` — nuevo campo `status` en `Proforma_Header`.
- `helper/proforma.py` — repurpose de constantes huérfanas.
- `business/proforma.py` — nuevo método `refresh_status`; 3 nuevas llamadas (`create_work_note`, `abrir_proforma`, `crear_nota_venta`).
- `business/pago.py` — import de `Proforma_Business`; 1 nueva llamada en `cerrar_pago`.
- `migrations/0106_proforma_header_status.py` — nueva.
- `tests/test_proforma_status_field.py` — nuevo.

**Frontend**: ninguno. No hay componente Angular que lea o escriba este campo.

## Implementation steps

1. Escribir los tests de caracterización del comportamiento actual (sin tocar código de producción todavía): construir la cadena completa `Proforma_Header → Proforma_Detail → Nota_trabajo → Nota_Venta → pago` usando las funciones de negocio reales (`create_work_note`, `crear_nota_venta`, `cerrar_pago`), y verificar en cada paso lo que `ProformaAdmin.get_estado(proforma)` devuelve hoy. Esto documenta el baseline y sirve de fixture reusable para el resto de los tests.
2. Repurposear `Proforma_Helper` (paso 2 de "Proposed solution").
3. Agregar el campo `status` al modelo y generar la migración con `python manage.py makemigrations product`, luego editarla a mano para agregar el `RunPython` de backfill (Django no lo genera solo).
4. Correr `python manage.py migrate` local para confirmar que la migración aplica limpio sobre la base de desarrollo actual.
5. Implementar `Proforma_Business.refresh_status` y las 3 llamadas en `business/proforma.py`.
6. Implementar la llamada en `Pago_Business.cerrar_pago` (`business/pago.py`).
7. Escribir los tests de equivalencia (paso "Test strategy" abajo) reusando los fixtures del paso 1.
8. Correr la suite completa (`python manage.py test`) y confirmar que nada existente se rompió (en particular `test_sucursal_scope_admin.py`, que ya crea objetos de este mismo dominio).
9. Verificación manual en el admin local: crear una proforma → nota de trabajo → nota de venta → pago paso a paso, e inspeccionar `status` directamente en el shell de Django (`Proforma_Header.objects.get(pk=...).status`) en cada etapa, confirmando que coincide con lo que la columna "Estado" del admin ya muestra.

## Test strategy

**Nivel**: unitario/integración con `django.test.TestCase` (base de datos real de test, patrón ya usado en `praxsa_manager/product/tests/`), reusando `tests/helpers.py` si ya tiene factories de `Sucursal`/`User`/`Car_Model` aplicables; si no cubre `Proforma_Header`/`Nota_trabajo`/`Nota_Venta`/`pago`, se agregan factories mínimas en el nuevo archivo de test.

**¿Corresponde E2E (Playwright)?** No. Justificación explícita: este cambio no toca ningún flujo de Angular ni ninguna vista pública — vive enteramente en modelos, `business/` y migraciones de Django, ejercitado hoy exclusivamente desde acciones del admin de Django. No hay navegación ni formulario multi-paso del lado del cliente involucrado. Un test de integración de Django (llamando directamente a los métodos de `business/`, que es lo que las acciones de admin ya hacen) cubre el flujo real sin necesitar un navegador. Instalar Playwright para esto sería sobreingeniería.

**Casos concretos**:
1. `test_proforma_recien_creada_status_default` — una `Proforma_Header` nueva (sin ninguna relación) tiene `status == 'proforma'` inmediatamente después de `save()`, sin necesidad de llamar `refresh_status`.
2. `test_create_work_note_status_nota_trabajo` — después de `Proforma_Business().create_work_note(...)`, `proforma.status == 'nota_trabajo'` y coincide con `ProformaAdmin.get_estado(proforma)`.
3. `test_abrir_proforma_vuelve_a_status_proforma` — sobre una proforma ya en `'nota_trabajo'`, `abrir_proforma` la vuelve a `'proforma'`, coincidiendo con `get_estado`.
4. `test_crear_nota_venta_status_por_cobrar` — después de `crear_nota_venta`, `proforma.status == 'por_cobrar'` (verificado sobre `nota_trabajo.proforma` recargado de la base), coincide con `get_estado`.
5. `test_cerrar_pago_status_finalizado` — después de `Pago_Business().cerrar_pago(pago)`, `proforma.status == 'finalizado'`, coincide con `get_estado`.
6. `test_refresh_status_no_modifica_proforma_created_on` — captura `proforma_created_on` antes y después de una llamada a `refresh_status`, asegura que no cambió (regresión específica del detalle de `auto_now` señalado arriba).
7. `test_migracion_backfill_calcula_status_correcto` (a nivel de migración, usando el patrón estándar de Django para testear `RunPython` con `MigratorTestCase` si el proyecto tiene la librería, o alternativamente un test funcional que cree las filas con el estado del modelo actual — sin campo `status` seteado a mano — y confirme que el `RunPython` de la migración `0106` produce el mismo valor que `get_estado`); si el proyecto no tiene infraestructura para testear migraciones aisladas, este caso se cubre como test manual documentado en el PR (paso 9 de implementación) en vez de test automatizado — a decidir durante la implementación según lo que exista.

Todo paso de "Proposed solution" que cambia lógica de negocio (5 y 6) tiene su caso de prueba correspondiente arriba (2-5). El paso 1 (agregar campo) lo cubre el caso 1. El detalle de `update_fields` lo cubre el caso 6.

## Acceptance criteria

- [ ] `Proforma_Header` tiene un campo `status` con las 4 choices definidas, default `'proforma'`.
- [ ] La migración `0106` aplica limpio sobre la base de desarrollo actual y backfillea correctamente proformas preexistentes en distintos estados (verificado manualmente si no hay al menos una proforma real en cada estado en la base de desarrollo, crear los casos de prueba para validar el backfill).
- [ ] Las 4 transiciones (`create_work_note`, `abrir_proforma`, `crear_nota_venta`, `cerrar_pago`) actualizan `status` al valor esperado, verificado por test.
- [ ] `status` coincide con `ProformaAdmin.get_estado()` en todo momento del ciclo, verificado por test.
- [ ] Ningún test existente se rompe (`python manage.py test` completo en verde).
- [ ] `ProformaAdmin.get_estado`, `NotaVentaAdmin.get_estado`, `NotaTrabajoAdmin.get_estado` y todos los `has_change_permission`/`get_readonly_fields` existentes quedan sin modificar (diff no los toca).
- [ ] `proforma_created_on` no cambia como efecto secundario de ninguna llamada a `refresh_status` (verificado por test).

## Risks

- **El backfill de la migración puede tardar o fallar si hay muchas filas con relaciones inconsistentes** (p. ej. un `Nota_trabajo` sin `Nota_Venta` pero con algún dato corrupto) — mitigación: el `RunPython` debe envolver cada fila en su propio try/except y loguear (no abortar toda la migración) si una fila puntual no se puede resolver, dejándola en el default `'proforma'` con un log de advertencia, ya que esto es solo el campo observacional (no bloquea nada si queda momentáneamente desactualizado en un caso raro) — a diferencia de una constraint dura, que sí ameritaría abortar.
- **Olvidar un quinto camino de transición en el futuro** (riesgo ya señalado en el ADR): mitigado por centralizar el cálculo en `refresh_status`, pero no eliminado — si alguien agrega una acción de admin nueva que cierra `Nota_trabajo` sin pasar por `Proforma_Business`, `status` quedará desactualizado. No hay mitigación automática para esto sin las constraints diferidas (fuera de alcance).
- **Confusión entre `status` (nuevo, observacional) y los booleanos existentes** durante el período en que ambos coexisten — mitigado documentando claramente en el ADR y en comentarios mínimos del código que `status` no gobierna permisos ni precondiciones todavía.

## Out of scope

- `CheckConstraint`/validación de invariantes de transición (paso 3 del backlog) — diferido explícitamente por ADR-006 hasta responder la pregunta de negocio pendiente.
- Migrar `ProformaAdmin.get_estado`/`NotaVentaAdmin.get_estado`/`NotaTrabajoAdmin.get_estado` a leer el campo `status` — ADR-006 lo deja como decisión de este plan, y este plan decide dejarlo para un PR separado (mantener "un objetivo por cambio" de `docs/CLAUDE.md`, dado que este PR ya toca modelo + migración + 2 módulos `business/`).
- Limpieza del código muerto identificado en la investigación (`sales_status` residual en `business/proforma.py:28` y `Forms/car_model_part.py:20-24`, la entrada `"create_sales_note"` mal referenciada en `ProformaAdmin.actions:81`) — no relacionado a agregar el campo nuevo, cambio independiente de bajo riesgo, se puede hacer en un PR aparte.
- Retirar los booleanos `is_close`/`cerrado` existentes — siguen siendo la fuente real de permisos/precondiciones hoy.
- Pregunta abierta para el usuario (no bloqueante para este plan, pero relevante para el paso 3 futuro): ¿existe una regla de negocio formal para las transiciones proforma→instalación→venta→pago, o se decide caso a caso por el personal? Sin responder esto, un ADR futuro de constraints no puede avanzar con confianza.

## Dependencias nuevas

Ninguna.
