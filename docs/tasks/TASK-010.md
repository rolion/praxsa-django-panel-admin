# TASK-010: Recalcular server-side el precio de `venta_metro_lineal` en el admin (extender ADR-006)

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_PLAN
**Rama:** `task/TASK-010-venta-metro-lineal-pricing`
**Pull Request:** [#41](https://github.com/rolion/praxsa-django-panel-admin/pull/41)

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-09-25 14:28 UTC | (nuevo) → INVESTIGATION | Task creado | delivery-investigate |
| 2026-09-25 | INVESTIGATION → PLANNING | Investigación completa, veredicto NEEDS_PLAN | delivery-plan |
| 2026-09-25 | PLANNING → ENGINEERING | Plan v1 listo, PR #41 abierto | delivery-plan |
| 2026-09-25 | ENGINEERING → REVIEW | Implementación completa, tests en verde, verificación manual en vivo OK | delivery-engineer |
| 2026-09-25 | REVIEW → PUBLISH | Quality Gate PASS, sin issues abiertos | delivery-review |

## Investigación

### Requerimiento

Backlog unificado ([docs/integration-and-backlog.md](../integration-and-backlog.md), ítem #2), tras la actualización de 2026-09-25: cerrar la deuda restante del ítem #2 extendiendo a `sales_type = venta_metro_lineal` el mismo recálculo server-side de precio que TASK-007/PR #36 (ADR-006) ya implementó para `venta_instalacion` en `ProformaAdmin`. La reformulación que motiva este task: ya no se trata de "corregir un drift" entre `sales_event.js` y `Proforma_Business.convertir_venta_metro_lineal` (esa aparente divergencia se investigó y se confirmó que no existe — son dos escenarios distintos, cada uno correcto para su caso, ver sección 2.1 del backlog), sino simplemente de que **`venta_metro_lineal` sigue sin ninguna verificación server-side de precio** — deuda ya identificada y aceptada explícitamente en ADR-006, no bloqueada por ninguna pregunta de negocio pendiente.

### Hechos encontrados

- **El servidor no recalcula nada para `venta_metro_lineal` hoy.** `CarModelPartForm.clean()` ([Forms/car_model_part.py:112-118](../../praxsa_manager/product/Forms/car_model_part.py)) solo valida que `quantity` e `installation_price` estén vacíos/cero para este `sales_type` — no hay ninguna rama equivalente a las líneas 83-110 (la que sí recalcula `sub_total`/`window_film_price`/`installation_price` para `venta_instalacion`). El `sub_total` y `window_film_price` que llegan del formulario (calculados en el navegador por `sales_event.js`) se persisten tal cual, solo validados como no-cero por `clean_sub_total` ([Forms/car_model_part.py:32-37](../../praxsa_manager/product/Forms/car_model_part.py)).
- **Ya hay un test que caracteriza exactamente este gap.** `test_venta_metro_lineal_price_still_trusted_from_client` ([product/tests/test_admin_price_recalculation.py:88-100](../../praxsa_manager/product/tests/test_admin_price_recalculation.py)) crea una proforma `venta_metro_lineal` con `sub_total='999.99'` y `window_film_price='5.00'` arbitrarios (sin relación con ningún precio real de inventario) y confirma que el form los acepta tal cual — es la prueba viva de que el problema es real y reproducible, no solo teórico.
- **`Pricing_Business.resolve_unit_price` ya es agnóstico de `sales_type`** ([business/pricing.py:13-24](../../praxsa_manager/product/business/pricing.py)) — resuelve `(sucursal, lámina, ancho)` → precio unitario real (`precio_venta_sucursal` con fallback a `inventario.precio_venta_mtr_lineal`), sin ninguna dependencia de `installation_price`/`quantity`/`Car_Model_Part`. Ya está listo para reusarse en la rama `venta_metro_lineal` sin cambios.
- **La fórmula de subtotal para `venta_metro_lineal` (creación directa) no tiene ambigüedad de negocio pendiente — se confirmó en código, no se necesita preguntarle a nadie.** El servidor ya prohíbe `quantity > 0` para este `sales_type` ([Forms/car_model_part.py:115-116](../../praxsa_manager/product/Forms/car_model_part.py)): `if cc_quantity is not None and cc_quantity > 0: self.add_error('quantity', 'campo no requerido')`. Sin un `quantity` válido que multiplicar, la única fórmula consistente con las reglas ya existentes es `subtotal = length * unit_price` — que es exactamente lo que ya calcula `sales_event.js` en su rama `else` ([sales_event.js:283-290](../../praxsa_manager/product/static/product/sales_event.js)), sin ningún término de `quantity`.
- **`business/pricing.py` no tiene todavía una función `calculate_subtotal_venta_metro_lineal`** — solo existe `calculate_subtotal_venta_instalacion` ([business/pricing.py:27-31](../../praxsa_manager/product/business/pricing.py)), documentada explícitamente como "único caso alcanzable desde `SalesHeaderSerializer`".
- **El camino REST (`SalesHeaderSerializer`) nunca alcanza `venta_metro_lineal`** — `sales_type` no está en `Meta.fields` ([serializer/invoice_serializer.py:35](../../praxsa_manager/product/serializer/invoice_serializer.py)) y el modelo usa `default=helper.tipo_venta_instalacion` ([models.py:146](../../praxsa_manager/product/models.py)). Por lo tanto este task es exclusivamente sobre `ProformaAdmin`/`CarModelPartForm` (camino admin), no toca el serializer ni Angular.
- **`ProformaAdmin.save_related` ya recalcula `total_price` de forma agnóstica de `sales_type`** ([business/proforma.py:188-197](../../praxsa_manager/product/business/proforma.py)), sumando los `sub_total` reales de los `Proforma_Detail` persistidos — no necesita cambios; una vez que `sub_total` por ítem sea correcto, el total de cabecera ya sale correcto automáticamente.
- **ADR-006 documenta explícitamente esta deuda como pendiente, no bloqueada por otra decisión que no sea la de la fórmula** ([docs/adr/ADR-006-admin-price-recalculation-venta-instalacion.md](../adr/ADR-006-admin-price-recalculation-venta-instalacion.md), sección "Fuera de alcance"): *"`Pricing_Business.resolve_unit_price` ya es agnóstico de `sales_type` y quedará disponible para cuando se resuelva; falta escribir `calculate_subtotal_venta_metro_lineal` una vez decidida la fórmula."* — la fórmula ya quedó decidida por los hechos de arriba.
- **`convertir_venta_metro_lineal` (acción masiva de conversión, distinta de la creación directa) sigue copiando `window_film_price` del detalle original sin re-resolverlo contra el precio actual** — mencionado explícitamente en ADR-006 como deuda no resuelta ahí ("Consecuencias", último punto). Es un problema relacionado pero en un método distinto (`business/proforma.py:142-186`), sin ningún test hoy (`Grep` de `convertir_venta_metro_lineal` en `praxsa_manager/` solo encuentra su definición y su único llamador en `admin_config/proforma_admin.py:240-246`).

### Hipótesis / supuestos no confirmados

- Se asume que el criterio de "recalcular siempre, sobrescribir siempre" que ADR-006 ya decidió para `venta_instalacion` (punto 1 de la Decisión) aplica igual a `venta_metro_lineal` — es consistente con el mismo ADR y con el patrón ya implementado, pero no hay una confirmación explícita del usuario específica para este segundo `sales_type` (la memoria del proyecto indica revisar con el usuario cambios de lógica de negocio antes de tocar código de varios archivos; no se verificó si el usuario ya dio esa confirmación fuera de esta conversación).
- No se verificó si existen proformas `venta_metro_lineal` reales en la base de datos de producción hoy (solo se sabe que el único camino para crearlas es la acción masiva `convertir_venta_metro_lineal` o edición manual directa en el admin) — dato relevante para dimensionar el riesgo de un cambio de validación que podría rechazar guardados que antes pasaban.
- No se confirmó si `car_part` debe seguir siendo un campo requerido para un `Proforma_Detail` de tipo `venta_metro_lineal` creado desde cero — hay una validación comentada en `Forms/car_model_part.py:113-114` (`# if cc_car_part_id is not None: self.add_error('car_part_id','este campo no es requerido')`) que sugiere que en algún momento se consideró que no debería ser requerido, pero nunca se activó ni se removió. Queda fuera del alcance directo de este task (no es parte del recálculo de precio), pero `delivery-plan`/`delivery-architect` debería decidir si se toca en el mismo cambio o se deja para otro task.

### Módulos y dependencias relacionadas

- **Backend, capa `Forms/`**: [Forms/car_model_part.py](../../praxsa_manager/product/Forms/car_model_part.py) — único archivo que necesita la nueva rama de recálculo (mismo patrón que ya existe para `venta_instalacion` en `clean()`).
- **Backend, capa `business/`**: [business/pricing.py](../../praxsa_manager/product/business/pricing.py) — necesita una nueva función `calculate_subtotal_venta_metro_lineal(length, unit_price)`, análoga a `calculate_subtotal_venta_instalacion` ya existente.
- **Backend, capa `admin_config/`**: [admin_config/proforma_admin.py](../../praxsa_manager/product/admin_config/proforma_admin.py) — no necesita cambios (`save_related` ya es agnóstico de `sales_type`), pero es el punto de entrada real (admin de Django) donde se ejercita `CarModelPartForm` vía el formset inline.
- **No toca**: `serializer/invoice_serializer.py`, ningún archivo de `proforma/src/` (Angular), ni migraciones (no se agregan/quitan columnas).
- **Relacionado pero fuera de este task**: `business/proforma.py::convertir_venta_metro_lineal` (acción masiva de conversión) — comparte la misma familia de deuda (precio no re-resuelto server-side) pero es un método distinto, sin test, y con su propio riesgo (el bug latente de fusión de `quantity` detectado en la validación previa de esta sesión, ver `docs/integration-and-backlog.md` sección 2.1). No se investigó a fondo aquí porque el requerimiento de este task se acotó explícitamente a "extender el recálculo server-side a venta_metro_lineal" en el contexto de `ProformaAdmin`/`CarModelPartForm`, el mismo camino que cerró TASK-007. Si se decide incluirlo, es una ampliación de alcance que debería decidirse explícitamente en la planificación, no asumirse.
- **`sales_event.js`** ([static/product/sales_event.js](../../praxsa_manager/product/static/product/sales_event.js)) — sigue calculando un estimado client-side que ya no sería la fuente de verdad tras este cambio (igual que ya pasa con `venta_instalacion` desde TASK-007). No requiere cambios funcionales obligatorios, aunque queda pendiente (deuda ya documentada) el bug de UX del listener faltante de `quantity` — no aplica a `venta_metro_lineal` porque ese `sales_type` no usa `quantity`.

### Implementaciones similares existentes

TASK-007/PR #36 (ADR-006) es el precedente directo y el patrón a seguir: en `CarModelPartForm.clean()`, dentro del bloque `if sale_header.sales_type == tipo_venta_instalacion`, se resuelve `unit_price` con `Pricing_Business.resolve_unit_price(sucursal_id, lamina_id, width)`, se recalcula `sub_total` con una función dedicada de `business/pricing.py`, y se sobrescribe siempre `cleaned_data['sub_total']`/`cleaned_data['window_film_price']` (y `installation_price` cuando aplica), redondeando con `Decimal.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)` para evitar el fallo de `DecimalValidator` por exponentes de `Decimal` sin normalizar ([Forms/car_model_part.py:100-110](../../praxsa_manager/product/Forms/car_model_part.py)). El bloque `if sale_header.sales_type == tipo_venta_metro_lineal` (líneas 112-118) es estructuralmente el lugar natural para la rama equivalente — ya existe, solo le falta el recálculo.

### Comportamiento actual

1. Usuario staff crea/edita una proforma `venta_metro_lineal` en el admin de Django y agrega un ítem (lámina + ancho + largo).
2. `sales_event.js` (navegador) calcula `subtotal = length * film_price` client-side y lo pre-llena en el form inline ([sales_event.js:283-290](../../praxsa_manager/product/static/product/sales_event.js)).
3. Al enviar el form, `CarModelPartForm.clean()` valida que `quantity`/`installation_price` estén vacíos, pero **no toca `sub_total` ni `window_film_price`** — lo que llegó del navegador se persiste tal cual (validado solo como "no cero" por `clean_sub_total`).
4. `ProformaAdmin.save_related` suma los `sub_total` de los `Proforma_Detail` guardados para fijar `Proforma_Header.total_price` — correcto en sí mismo, pero construido sobre subtotales por ítem que nunca se verificaron contra el precio real de inventario/sucursal.
5. Resultado: un usuario con acceso al admin (staff) puede manipular el `sub_total`/`window_film_price` enviado en el POST y el servidor lo acepta sin verificación, exactamente como estaba documentado para `venta_instalacion` antes de TASK-007 — la misma clase de riesgo (BIZ-01), sin cerrar para este segundo `sales_type`.

### Restricciones

- `docs/CLAUDE.md`: "El dinero se maneja con `Decimal`, nunca con `float`" — la nueva función de `business/pricing.py` debe seguir ese patrón (ya lo hace `calculate_subtotal_venta_instalacion`).
- `docs/CLAUDE.md`: "Todo cambio de lógica de negocio lleva su test" — ya existe un test de caracterización del comportamiento actual (`test_venta_metro_lineal_price_still_trusted_from_client`) que **debe actualizarse** (dejará de ser válido tal como está escrito una vez implementado el recálculo — hoy documenta el comportamiento "malo" que este task busca corregir).
- `docs/CLAUDE.md`: "Antes de cambios que afecten varios archivos, proponer un plan y esperar confirmación" — aplica aquí (mínimo 2 archivos: `Forms/car_model_part.py` + `business/pricing.py`, más el test).
- ADR-006 ya fijó el criterio de producto "recalcular siempre, sobrescribir siempre" (no rechazar por discrepancia) para el camino admin — este task hereda ese criterio por consistencia, salvo que se decida explícitamente lo contrario en la planificación.
- Memoria del proyecto (`feedback_manual_testing_catches_requirement_errors`): cambios de autorización/reglas de negocio como este se beneician de una verificación manual en vivo en el admin además de los tests automatizados — mismo patrón ya seguido en TASK-005/TASK-007.

### Riesgos identificados

- **Riesgo de romper flujos existentes**: si hoy el personal de sucursal está creando/editando proformas `venta_metro_lineal` con subtotales que no coinciden exactamente con `precio_venta_sucursal`/`inventario.precio_venta_mtr_lineal` (por redondeo del lado navegador, o por ajustes manuales que el staff hace a propósito), el recálculo empezaría a sobrescribirlos silenciosamente — mismo riesgo ya identificado y mitigado en ADR-006 vía "sobrescribir siempre, nunca rechazar" + el campo `discount` existente para ajustes intencionales. No se verificó si hay proformas `venta_metro_lineal` activas hoy que dependan de un subtotal manual no relacionado con el precio de inventario.
- **Rechazo por datos faltantes**: igual que en `venta_instalacion`, si `resolve_unit_price` devuelve `None` (no hay fila de inventario que cubra `sucursal+lámina+ancho`), habría que decidir si eso rechaza el form (como ya hace la rama `venta_instalacion`, línea 97-98) o se comporta distinto — mismo patrón esperable, pero es una decisión de `delivery-plan`.
- **Alcance ambiguo con `convertir_venta_metro_lineal`**: existe la tentación de resolver en el mismo cambio el precio potencialmente obsoleto que copia esa acción masiva (mencionado en ADR-006), pero es un método distinto, sin test, con su propio bug latente ya detectado (fusión de `quantity` sin acumular). Meterlo en el mismo PR ampliaría el alcance más allá de lo que pide el ítem #2 reformulado — riesgo de que `delivery-plan` lo intente resolver todo junto y el cambio deje de ser "chico" (regla del proyecto: "Cambios pequeños: un objetivo por cambio").
- **Test de caracterización a modificar, no solo agregar**: `test_venta_metro_lineal_price_still_trusted_from_client` documenta explícitamente el comportamiento que este task cambia — hay que decidir si se reescribe para afirmar el nuevo comportamiento (recalculado) o se conserva como test histórico y se agrega uno nuevo; dejarlo como está haría fallar la suite después del cambio (es, por diseño, una aserción de que el precio NO se recalcula).
- **Sin impacto en Angular/REST**: confirmado que este cambio no toca el contrato de API ni el frontend — reduce el radio de blast comparado con TASK-005, similar a TASK-007.

### Veredicto de complejidad

**NEEDS_PLAN** — Es una extensión directa de un patrón ya decidido e implementado (ADR-006/TASK-007) a un segundo `sales_type`, en la misma capa (`Forms/car_model_part.py` + `business/pricing.py`), sin nuevo módulo, sin cambio de autenticación/autorización, sin migración de esquema, sin impacto en el frontend ni en el contrato REST. La decisión arquitectónica de fondo (recalcular siempre server-side, sobrescribir siempre, reusar `Pricing_Business`) ya fue tomada en ADR-006 y no hace falta revisarla — lo que falta es trabajo de planificación concreto: la fórmula exacta de la nueva función, qué test actualizar/agregar, y decidir explícitamente si `convertir_venta_metro_lineal` entra o no en este mismo cambio (recomendación de esta investigación: no, por la regla de cambios pequeños). No calza como `NEEDS_ARCHITECTURE` porque no hay una decisión de negocio abierta que resolver (la que bloqueaba esto en ADR-006 ya se resolvió con evidencia de código, documentada arriba) ni ningún indicador de los que `delivery-architect` evalúa (no es cambio estructural, no es nuevo bounded context/integración externa, no toca infraestructura ni impacta múltiples módulos).

## Arquitectura
_No aplica según veredicto — ADR-006 ya cubre el criterio de producto aplicable; no se identificó ninguna decisión arquitectónica nueva pendiente._

## Plan
[docs/plans/PLAN-2026-09-25-venta-metro-lineal-pricing.md](../plans/PLAN-2026-09-25-venta-metro-lineal-pricing.md) (v1)

## Implementación

Implementado exactamente según el plan v1, sin desvíos:

- `praxsa_manager/product/business/pricing.py`: agregada `calculate_subtotal_venta_metro_lineal(length, unit_price) -> Decimal` (`length * unit_price`, sin `quantity`).
- `praxsa_manager/product/Forms/car_model_part.py`: en el bloque `venta_metro_lineal` de `CarModelPartForm.clean()`, tras las validaciones existentes de `quantity`/`installation_price`, se agregó la resolución de precio real (guard `if cc_width is not None and cc_window_film is not None`, idéntico patrón al de `venta_instalacion`): `Pricing_Business.resolve_unit_price(sucursal_id, lamina_id, width)` → si `None`, `add_error('window_film', ...)`; si no, sobrescribe `cleaned_data['window_film_price']` y `cleaned_data['sub_total']` (redondeado con `.quantize(Decimal('0.01'), ROUND_HALF_UP)`, mismo motivo ya documentado en el código existente).
- `praxsa_manager/product/tests/test_admin_price_recalculation.py`: se reemplazó `test_venta_metro_lineal_price_still_trusted_from_client` (documentaba el comportamiento viejo) por `test_overwrites_manipulated_price_with_real_recalculated_value_metro_lineal` (afirma la sobrescritura) y se agregó `test_rejects_when_no_inventory_covers_requested_width_metro_lineal`.

**Tests**: suite completa `product/tests/` — 81/81 en verde (incluye los 18 tests de `test_admin_price_recalculation.py`).

**Verificación manual en vivo** (servidor real en `localhost:8010`, HTTP real con `requests`, login real, datos reales creados/eliminados en el mismo checkeo contra el Postgres dev del usuario):
1. Proforma `venta_metro_lineal` real, ítem con `length=3.00`, inventario con `precio_venta_mtr_lineal=77.00`. POST con `sub_total=999999.99` y `window_film_price=5.00` manipulados → persistido: `sub_total=231.00`, `window_film_price=77.00`, `total_price` de cabecera `231.00` — el servidor ignoró por completo los valores del navegador.
2. Ítem con un ancho (`2.00`) que ningún reel de la lámina elegida cubre → rechazado con error de formulario `"No hay precio disponible para la lámina/ancho solicitado en esa sucursal."`, HTTP 200 (no 500).
3. Nota incidental descubierta durante la verificación (no relacionada al cambio, no requiere acción): el filtro de inventario (`bobina__width__gte=width`) acepta cualquier reel **igual o más ancho** que el solicitado, no solo coincidencia exacta — comportamiento preexistente y ya usado igual en la rama `venta_instalacion`, no introducido por este cambio.

**Deuda técnica no tocada (fuera de alcance, ver plan)**: `convertir_venta_metro_lineal`, el listener faltante de `quantity` en `sales_event.js`, y la opcionalidad de `car_part` para `venta_metro_lineal` — sin cambios, según lo acordado.

## Review

**Veredicto: PASS.** Sin issues abiertos — no se generó ningún `docs/reviews/REV-*.md`.

Verificado de forma independiente (re-ejecutado, no reutilizando lo reportado por `delivery-engineer`):
- `python manage.py test product` → 81/81 OK.
- `python manage.py makemigrations --check --dry-run` → sin cambios pendientes, confirma que el plan acertó ("sin migración de esquema").
- Lint/type-check/coverage/security: no configurados/instalados en el proyecto — verificación no realizable en este entorno, dejado explícito, no un PASS silencioso.
- Cobertura del código nuevo revisada manualmente (sin `coverage.py`): ambas ramas de la nueva lógica tienen test dedicado.
- Los 7 acceptance criteria del plan v1 se cumplen con evidencia concreta. Alcance respetado: el diff de código toca únicamente los archivos que predecía el plan.

**Nota de proceso**: esta revisión corrió en la misma sesión que implementó el código — aislamiento procedimental (reconstruido desde TASK-010.md, el plan, ADR-006 y el diff real contra `origin/master`), no aislamiento real de contexto.

Detalle completo en [PR #41](https://github.com/rolion/praxsa-django-panel-admin/pull/41), secciones `## Testing` y `## Review`.

## Publicación
_Pendiente_
