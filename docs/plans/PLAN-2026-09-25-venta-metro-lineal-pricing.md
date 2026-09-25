# PLAN-2026-09-25-venta-metro-lineal-pricing (v1)

**Task:** TASK-010
**ADRs relacionados:** [ADR-006](../adr/ADR-006-admin-price-recalculation-venta-instalacion.md) (extiende su alcance a `venta_metro_lineal`; no requiere un ADR nuevo — ver "Architecture considerations")

## Objective

Cerrar la deuda de precio no validado server-side para `sales_type = venta_metro_lineal` en el admin de Django, extendiendo a este segundo caso el mismo patrón que TASK-007/PR #36 (ADR-006) ya implementó para `venta_instalacion`: el servidor recalcula siempre `sub_total`/`window_film_price` con datos reales de inventario y sobrescribe lo que envía el navegador, en vez de confiar en él.

## Context

TASK-010 (`docs/tasks/TASK-010.md`) investigó y confirmó que:
- `CarModelPartForm.clean()` no tiene, hoy, ninguna rama de recálculo de precio para `venta_metro_lineal` — solo valida que `quantity`/`installation_price` vengan vacíos.
- Existe un test de caracterización activo, `test_venta_metro_lineal_price_still_trusted_from_client`, que documenta ese hueco enviando un `sub_total` arbitrario y confirmando que el form lo acepta tal cual.
- `Pricing_Business.resolve_unit_price(sucursal_id, lamina_id, width)` ya es agnóstico de `sales_type` y no necesita cambios.
- La fórmula no tiene ambigüedad de negocio pendiente: el propio form ya prohíbe `quantity > 0` para este `sales_type`, así que `subtotal = length * unit_price` (sin término de `quantity`) es la única fórmula consistente — coincide con lo que ya calcula `sales_event.js` client-side.
- El camino REST (`SalesHeaderSerializer`) nunca alcanza `venta_metro_lineal` (no está en su `Meta.fields`, y el modelo defaultea a `venta_instalacion`) — este cambio es exclusivamente sobre el admin de Django.

## Current behavior

1. Staff crea/edita un `Proforma_Detail` de una proforma `venta_metro_lineal` en el admin.
2. `sales_event.js` calcula `subtotal = length * film_price` client-side ([sales_event.js:283-290](../../praxsa_manager/product/static/product/sales_event.js)) y pre-llena el form inline.
3. `CarModelPartForm.clean()` ([Forms/car_model_part.py:112-118](../../praxsa_manager/product/Forms/car_model_part.py)) solo valida que `quantity`/`installation_price` estén vacíos — no toca `sub_total` ni `window_film_price`, que se persisten exactamente como llegaron en el POST (solo se valida que `sub_total != 0` vía `clean_sub_total`, [Forms/car_model_part.py:32-37](../../praxsa_manager/product/Forms/car_model_part.py)).
4. `ProformaAdmin.save_related` suma esos `sub_total` (ya confiados sin verificar) para fijar `Proforma_Header.total_price` ([business/proforma.py:188-197](../../praxsa_manager/product/business/proforma.py)) — correcto en sí mismo, pero construido sobre datos no verificados.

## Expected behavior

Al guardar un `Proforma_Detail` de una proforma `venta_metro_lineal` (creación o edición) desde el admin:
- El servidor resuelve el precio unitario real vía `Pricing_Business.resolve_unit_price(sucursal_id, lamina_id, width)` y recalcula `sub_total = length * unit_price`, **sobrescribiendo siempre** lo que envió el navegador (mismo criterio que ADR-006 ya decidió para `venta_instalacion`: nunca rechazar por discrepancia de precio, solo por datos faltantes).
- Si no existe ninguna fila de inventario que cubra `(sucursal, lámina, ancho)`, el form se invalida con un error de campo (`window_film`), no con un 500 — mismo patrón que la rama `venta_instalacion` ya implementada.
- `ProformaAdmin.save_related` no necesita cambios: al recibir `sub_total` ya correctos, la suma que hace hoy para `total_price` queda automáticamente correcta.

## Architecture considerations

- **No se requiere un ADR nuevo ni pasar por `delivery-architect`.** ADR-006 ya fijó el criterio de producto aplicable ("recalcular siempre, sobrescribir siempre, vía `Pricing_Business`") y dejó explícitamente esta extensión como trabajo futuro, bloqueada solo por la fórmula de `venta_metro_lineal` — que TASK-010 ya resolvió con evidencia de código (no era una pregunta de negocio real). Este plan hereda la decisión de ADR-006 en vez de reabrirla.
- **Contrato API**: sin impacto — no toca `serializer/`, `custom_views/` ni ningún archivo de `proforma/src/` (Angular). No requiere coordinar despliegue backend/frontend.
- **Datos existentes**: no hay migración de esquema (no se agregan/quitan columnas). Riesgo de datos: proformas `venta_metro_lineal` ya guardadas con un `sub_total` que no coincide con el precio real de inventario no se tocan retroactivamente — el recálculo solo aplica hacia adelante, en el próximo guardado desde el admin (mismo comportamiento que TASK-007 para `venta_instalacion`).
- **Dinero y precisión**: la nueva función usa `Decimal` end-to-end (igual que `calculate_subtotal_venta_instalacion`), con `.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)` antes de asignar a `cleaned_data['sub_total']`, por la misma razón ya documentada en el código existente (una multiplicación de `Decimal` conserva exponentes y hace fallar el `DecimalValidator(decimal_places=2)` de `ModelForm._post_clean()` si no se redondea explícito).
- **Rendimiento**: sin impacto — una única consulta a inventario por ítem (`resolve_unit_price`), igual que ya hace la rama `venta_instalacion`, ejecutada dentro del ciclo normal de validación del formset inline (no hay loop nuevo sobre múltiples proformas).
- **Seguridad y permisos**: sin cambios — sigue siendo un formulario del admin de Django, accesible solo a staff autenticado, mismo alcance que TASK-007.
- **Acoplamiento**: el cambio vive enteramente en `Forms/car_model_part.py` + `business/pricing.py`, los mismos dos archivos que ya tocó TASK-007 para el otro `sales_type` — no se identificó ningún efecto secundario en otro módulo.

## Proposed solution

1. **`business/pricing.py`**: agregar `calculate_subtotal_venta_metro_lineal(length: Decimal, unit_price: Decimal) -> Decimal`, análoga a `calculate_subtotal_venta_instalacion` mismo estilo/firma, implementando `length * unit_price` (sin `quantity`, consistente con que el form ya prohíbe `quantity > 0` para este `sales_type`).
2. **`Forms/car_model_part.py`**, dentro del bloque `if sale_header is not None and sale_header.sales_type == self.proforma_helper.tipo_venta_metro_lineal:` (líneas 112-118 actuales): después de las validaciones existentes de `quantity`/`installation_price`, agregar el mismo patrón de recálculo que ya usa la rama `venta_instalacion` (líneas 83-110), simplificado porque no hay `Car_Model_Part`/`installation_price` involucrados:
   - Si `cc_width` y `cc_window_film` están presentes (guard defensivo, igual que el `if cc_quantity is not None and cc_width is not None:` de la rama `venta_instalacion`, para no intentar resolver precio cuando ya hay errores de campo requerido):
     - Resolver `unit_price = self.pricing_business.resolve_unit_price(sucursal_id=getattr(sale_header, 'sucursal_id', None), lamina_id=cc_window_film.id, width=cc_width)`.
     - Si `unit_price is None`: `self.add_error('window_film', 'No hay precio disponible para la lámina/ancho solicitado en esa sucursal.')` (mismo mensaje que ya usa la rama `venta_instalacion`, para consistencia de UX).
     - Si no: sobrescribir `cleaned_data['window_film_price'] = unit_price` y `cleaned_data['sub_total'] = calculate_subtotal_venta_metro_lineal(length=cc_length, unit_price=unit_price).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)`.
3. **No se toca** `ProformaAdmin.save_related` (ya es agnóstico de `sales_type`), `sales_event.js` (sigue siendo solo una estimación client-side, ya no autoritativa — mismo estado que `venta_instalacion` desde TASK-007), ni `convertir_venta_metro_lineal` (explícitamente fuera de alcance, ver "Out of scope").

## Files/components affected

**Backend:**
- `praxsa_manager/product/business/pricing.py` — nueva función `calculate_subtotal_venta_metro_lineal`.
- `praxsa_manager/product/Forms/car_model_part.py` — nueva rama de recálculo dentro de `clean()`.
- `praxsa_manager/product/tests/test_admin_price_recalculation.py` — actualizar/agregar tests (ver Test strategy).

**Frontend:** ninguno.

## Implementation steps

1. Agregar `calculate_subtotal_venta_metro_lineal(length, unit_price)` en `business/pricing.py`, con docstring corta análoga a la de `calculate_subtotal_venta_instalacion`.
2. Importar la nueva función en `Forms/car_model_part.py` (junto al import ya existente de `calculate_subtotal_venta_instalacion`).
3. Implementar la rama de recálculo dentro del bloque `venta_metro_lineal` de `CarModelPartForm.clean()`, según "Proposed solution" arriba.
4. Actualizar `test_venta_metro_lineal_price_still_trusted_from_client`: hoy afirma que el precio manipulado se conserva tal cual — pasa a afirmar el comportamiento nuevo (se sobrescribe con el precio real), siguiendo el mismo patrón que `test_overwrites_manipulated_price_with_real_recalculated_value` (la prueba equivalente para `venta_instalacion`). Renombrar si el nombre deja de describir el comportamiento (p. ej. a `test_overwrites_manipulated_price_with_real_recalculated_value_metro_lineal`).
5. Agregar un test análogo a `test_rejects_when_no_inventory_covers_requested_width` pero para `venta_metro_lineal` (ancho sin cobertura de inventario → error de form, no 500).
6. Correr toda la suite de `product/tests/` (`python manage.py test`) y confirmar que `test_no_required_field_omission_crashes_the_form` (que ya barre ambos `sales_type` con campos requeridos faltantes) sigue pasando sin crashear con la nueva rama.
7. Verificación manual en un entorno real: crear y editar una proforma `venta_metro_lineal` desde el admin, con un `sub_total` manipulado en el POST, y confirmar que el servidor lo sobrescribe con el valor recalculado — mismo tipo de verificación ya hecha en TASK-005/TASK-007 (memoria del proyecto: los cambios de reglas de negocio se benefician de una prueba manual en vivo, no solo de tests automatizados).

## Test strategy

**Nivel: unitario/integración sobre `CarModelPartForm`, mismo nivel que ya usa `test_admin_price_recalculation.py` para `venta_instalacion`.**

Casos concretos:
- `sub_total`/`window_film_price` manipulados por el cliente se sobrescriben con el valor real calculado desde `Pricing_Business.resolve_unit_price` (reemplaza/renombra el test de caracterización existente).
- Ancho sin ninguna fila de inventario que lo cubra → el form es inválido con error en `window_film`, no crashea.
- Los tests ya existentes que verifican que `quantity`/`installation_price` siguen prohibidos para `venta_metro_lineal` no deberían necesitar cambios (siguen validando lo mismo).
- `test_no_required_field_omission_crashes_the_form` (guarda de regresión general que ya cubre ambos `sales_type`) debe seguir pasando sin modificarse — confirma que la nueva rama no reintroduce el patrón de crash que TASK-007 corrigió (REV-2026-09-23-001/002/003).

**¿Corresponde E2E (Playwright)? No.** Este es un cambio exclusivamente backend/admin (misma capa que TASK-007), sin flujo de usuario nuevo ni cambio de navegación — el admin de Django ya se ejercita con `RequestFactory`/`TestCase` como en el resto de `test_admin_price_recalculation.py`. No hay integración frontend-backend real que un test aislado no pueda cubrir (Angular no participa de `venta_metro_lineal` en absoluto). Mismo criterio ya aplicado en TASK-007, que tampoco agregó E2E. No se introduce Playwright ni ninguna dependencia nueva.

## Acceptance criteria

- [ ] `CarModelPartForm.clean()` recalcula y sobrescribe siempre `sub_total`/`window_film_price` para `venta_metro_lineal`, usando `Pricing_Business.resolve_unit_price` + la nueva `calculate_subtotal_venta_metro_lineal`.
- [ ] Cuando no hay precio de inventario disponible para `(sucursal, lámina, ancho)`, el form se invalida con un error de campo (no un 500).
- [ ] El test de caracterización existente (`test_venta_metro_lineal_price_still_trusted_from_client`) queda actualizado para reflejar el nuevo comportamiento — ya no debe quedar un test activo que afirme el comportamiento viejo.
- [ ] Se agregó al menos un test que cubre el caso de inventario sin cobertura para `venta_metro_lineal`.
- [ ] Suite completa de `product/tests/` pasa (`python manage.py test`).
- [ ] Verificación manual en un entorno real (admin, servidor corriendo) confirmando: (a) un `sub_total` manipulado se sobrescribe al guardar, (b) un ancho sin inventario se rechaza con error de formulario visible, no una página de error 500.
- [ ] `ProformaAdmin.save_related`, `sales_event.js` y `convertir_venta_metro_lineal` quedan sin modificar (fuera de alcance explícito).

## Risks

- **Sobrescribir subtotales de proformas activas que dependían de un ajuste manual no relacionado con el precio de inventario**: mismo riesgo que ya asumió ADR-006 para `venta_instalacion`, mitigado con el mismo criterio (sobrescribir siempre, nunca rechazar por discrepancia; ajustes intencionales van por el campo `discount` ya existente en `Proforma_Header`). No se verificó cuántas proformas `venta_metro_lineal` activas existen hoy en producción — si el usuario confirma que son pocas/ninguna, el riesgo es bajo; si hay volumen relevante, vale la pena una verificación manual adicional antes de publicar.
- **Ampliación de alcance hacia `convertir_venta_metro_lineal`**: existe la tentación de resolver en el mismo cambio el precio potencialmente obsoleto que copia esa acción masiva (mencionado como deuda en ADR-006). Se descarta explícitamente en este plan (ver "Out of scope") para mantener el cambio chico y con un solo objetivo, siguiendo la regla del proyecto.
- **Sin mitigación necesaria**: al no tocar el contrato de API ni el frontend, el radio de impacto de un rollback es mínimo — un `git revert` del PR no deja estado irreversible (no hay migración de datos).

## Out of scope

- `Proforma_Business.convertir_venta_metro_lineal` (acción masiva de conversión) — sigue copiando `window_film_price` del detalle original sin re-resolverlo contra el precio actual, y tiene un posible bug latente de fusión de `quantity` (detectado en la investigación de TASK-010, sin test que lo confirme). Es un método distinto, sin test, con su propio riesgo — se recomienda un task separado si se decide abordarlo.
- Corregir el listener faltante de `quantity` en `sales_event.js` (bug de UX ya documentado en `docs/integration-and-backlog.md` sección 2.3) — no aplica a `venta_metro_lineal` (ese `sales_type` no usa `quantity`), y de todas formas es un problema de otro `sales_type`, no de este task.
- Decidir si `car_part` debe dejar de ser aceptado/requerido para `venta_metro_lineal` (validación comentada en `Forms/car_model_part.py:113-114`) — no es parte del recálculo de precio, y activarla sería un cambio de comportamiento adicional no pedido por este task.
- **Pregunta abierta para el usuario** (no bloqueante para implementar, pero relevante antes de publicar): ¿hay proformas `venta_metro_lineal` activas hoy en producción cuyo `sub_total` actual el usuario sepa que no coincide con el precio real de inventario? Si las hay, conviene revisarlas manualmente antes de que el próximo guardado las sobrescriba.
