# PLAN-2026-09-23-admin-price-recalculation-venta-instalacion (v1)

**Task:** TASK-007
**ADRs relacionados:** [ADR-006](../adr/ADR-006-admin-price-recalculation-venta-instalacion.md)

## Objective

Cerrar el backlog #2 paso 5 (`docs/integration-and-backlog.md:149`) para el camino admin de Django: que `ProformaAdmin` recalcule server-side el precio real de una proforma `venta_instalacion` (precio unitario + `installation_price` + `sub_total`/`total_price`) en vez de confiar en lo que calculó `sales_event.js` en el navegador — mismo criterio que ADR-004 ya aplicó al REST en TASK-005. De paso, corrige un bug de datos descubierto en la investigación (`CarModelPartForm.clean()` busca un campo que no existe desde 2023) que dejaba dormidas las validaciones de consistencia por `sales_type`.

## Context

Investigación completa en [TASK-007.md](../tasks/TASK-007.md). Resumen de los hechos que este plan ejecuta:
- `ProformaAdmin.save_model`/`save_related` no recalculan ni validan precio real en ningún camino (creación ni edición) — persisten `total_price`/`sub_total`/`installation_price`/`window_film_price` tal como los envía el form.
- `CarModelPartForm.clean()` ([Forms/car_model_part.py:56](../../praxsa_manager/product/Forms/car_model_part.py)) lee `cleaned_data.get("sales_header")`, campo renombrado a `proforma_header` en 2023 ([migrations/0066](../../praxsa_manager/product/migrations/0066_alter_proforma_header_options_and_more.py)) — todo el bloque condicional por `sales_type` nunca se ejecuta.
- Ya existe la base reusable de TASK-005: `Pricing_Business.resolve_unit_price(sucursal_id, lamina_id, width)` y la función de módulo `calculate_subtotal_venta_instalacion(length, quantity, unit_price, installation_price)`, ambas en [business/pricing.py](../../praxsa_manager/product/business/pricing.py), sin cambios necesarios.
- `venta_metro_lineal` queda fuera de este plan por decisión explícita de ADR-006 (pregunta de negocio sin resolver).

## Current behavior

- Crear/editar una proforma en el admin persiste el `total_price` del header y el `sub_total`/`installation_price`/`window_film_price` de cada `Proforma_Detail` exactamente como los envía el POST — sin ninguna consulta a `Car_Model_Part`/`precio_venta_sucursal`/`inventario`.
- [admin_config/proforma_admin.py:149-163](../../praxsa_manager/product/admin_config/proforma_admin.py) (`save_related`) solo actúa si `change == True`, y solo resta del `total_price` ya guardado el `sub_total` de los ítems que se están eliminando en esa edición (`to_reduce`) — no hace nada en creación.
- [Forms/car_model_part.py:41-79](../../praxsa_manager/product/Forms/car_model_part.py) (`CarModelPartForm.clean()`) intenta validar ancho de lámina / `quantity` / `installation_price` según `sales_type`, pero como `sale_header` siempre es `None` (bug del nombre de campo), esas ramas nunca corren; solo se aplican `clean_sub_total` (`sub_total > 0`) y `clean_length` (`length > 0`), incondicionales.

## Expected behavior

- Al guardar (crear o editar) un `Proforma_Detail` cuyo header tiene `sales_type = venta_instalacion`: el servidor resuelve `Car_Model_Part.installation_price` real para `(car_model_id, car_part)` y el precio unitario real vía `Pricing_Business.resolve_unit_price(sucursal_id, lamina_id, width)`, recalcula `window_film_price`/`installation_price`/`sub_total` con `calculate_subtotal_venta_instalacion`, y **siempre sobrescribe** lo que trae el form — nunca rechaza por discrepancia numérica.
- Si `Car_Model_Part` no existe para ese `(car_model_id, car_part)`, o `resolve_unit_price` devuelve `None` (sin inventario que cubra `sucursal`/lámina/ancho): el form rechaza el guardado con un error de validación visible en el admin (no persiste), igual que el `400` del REST.
- `Proforma_Header.total_price` se recalcula, tanto en creación como en edición, como la suma de los `sub_total` de los `Proforma_Detail` que sobreviven después de que el formset ya aplicó altas/bajas/modificaciones — reemplaza la resta manual `to_reduce`.
- `CarModelPartForm.clean()` usa `proforma_header` (no `sales_header`) para acceder al header — las validaciones condicionales por `sales_type` que llevaban dormidas desde 2023 vuelven a ejecutarse.
- `venta_metro_lineal` no cambia de comportamiento: sigue persistiendo lo que envía el form, sin recalcular precio (fuera de alcance, ver ADR-006).

## Architecture considerations

Resumen de ADR-006 (ver el ADR para alternativas descartadas):
- Sobrescribir siempre, nunca rechazar por discrepancia — ajustes de precio intencionales van por `discount`, no por editar `sub_total`/`total_price` a mano.
- El recálculo de precio por ítem vive en `CarModelPartForm.clean()` (mismo lugar que hoy intenta, sin éxito, la validación por `sales_type`); el recálculo de `total_price` no puede vivir ahí porque un form individual de un formset no tiene visibilidad del resto de ítems — vive en `ProformaAdmin.save_related`, después de que el formset completo ya persistió.
- Se centraliza el recálculo de `total_price` en un método nuevo de `business/proforma.py::Proforma_Business` (no en el admin directamente) para poder testearlo sin tener que simular un POST completo con management form data de un inline formset — mismo criterio de capas que ya usa el proyecto (`business/` para lógica, `admin_config/` para orquestar).
- Sin migraciones, sin cambios de modelo, sin contrato de API expuesto a Angular (no toca `serializer/`, `custom_views/`, `proforma/src/`).
- Dinero en `Decimal` de punta a punta — `Pricing_Business`/`calculate_subtotal_venta_instalacion` ya lo garantizan; el nuevo método de `total_price` debe usar `Sum('sub_total')` de Django (agregación en el ORM, ya en `Decimal` porque `sub_total` es `DecimalField`) en vez de sumar en Python con conversión a `float`.

## Proposed solution

1. **`business/proforma.py::Proforma_Business`** — agregar `recalculate_total_price(self, proforma)`: consulta `Proforma_Detail.objects.filter(proforma_header=proforma).aggregate(total=Sum('sub_total'))`, asigna `proforma.total_price = total or Decimal('0')`, guarda (`update_fields=['total_price']`). Sin lógica de `sales_type` — es una suma agnóstica del tipo, coherente con lo que ya hace `sum_all_price()` en `sales_event.js` hoy (suma todos los `sub_total` visibles, sin distinguir tipo).
2. **`Forms/car_model_part.py::CarModelPartForm.clean()`** —
   - Cambiar `cleaned_data.get("sales_header")` por `cleaned_data.get("proforma_header")` (corrige el bug; reactiva las validaciones existentes de ancho/`quantity`/`installation_price` tal como ya estaban escritas, sin modificar esas reglas).
   - Dentro de la rama ya existente `if sale_header is not None and sale_header.sales_type == self.proforma_helper.tipo_venta_instalacion:`, agregar la resolución de precio real: buscar `Car_Model_Part.objects.filter(car_model_id=sale_header.car_model_id, car_part_id=cc_car_part_id).first()`; si es `None`, `self.add_error('car_part', 'No existe información de precio de instalación para este ítem en el modelo seleccionado.')` y salir sin calcular `sub_total`. Si existe, resolver `unit_price = Pricing_Business().resolve_unit_price(sucursal_id=sale_header.sucursal_id, lamina_id=cc_window_film.id, width=cc_width)`; si es `None`, `self.add_error('window_film', 'No hay precio disponible para la lámina/ancho solicitado en esa sucursal.')`. Si ambos resuelven, sobrescribir `cleaned_data['installation_price'] = car_model_part.installation_price`, `cleaned_data['window_film_price'] = unit_price`, `cleaned_data['sub_total'] = calculate_subtotal_venta_instalacion(length=cc_length, quantity=cc_quantity, unit_price=unit_price, installation_price=car_model_part.installation_price)`.
   - La rama `venta_metro_lineal` no se toca (sigue con sus validaciones de `quantity`/`installation_price` ya existentes, ahora también reactivadas por el fix del nombre de campo, pero sin recalcular precio).
   - Import nuevo: `from ..business.pricing import Pricing_Business, calculate_subtotal_venta_instalacion` (mismo import que ya usa `invoice_serializer.py`).
3. **`admin_config/proforma_admin.py::ProformaAdmin.save_related`** — eliminar la lógica de `to_reduce`/`to_add` (muerta para `to_add`, y la de `to_reduce` queda reemplazada). Nueva versión: dejar que `super().save_related(request, form, formsets, change)` persista los formsets primero (altas/bajas/modificaciones), y **después** llamar `self.proforma_business.recalculate_total_price(form.instance)`. Aplica igual en creación y edición (ya no depende de `change == True`).
4. **Import nuevo en `proforma_admin.py`**: ya existe `from ..business.proforma import Proforma_Business` y `proforma_business = Proforma_Business()` como atributo de clase — se reusa, no hace falta agregar nada.

## Files/components affected

**Backend** (`praxsa_manager/product/`):
- `business/proforma.py` — nuevo método `Proforma_Business.recalculate_total_price`.
- `Forms/car_model_part.py` — fix `sales_header`→`proforma_header`, nueva resolución de precio real dentro de `clean()`.
- `admin_config/proforma_admin.py` — `save_related` reescrito (elimina `to_reduce`/`to_add`, llama a `recalculate_total_price` después de `super().save_related(...)`).
- `tests/test_admin_price_recalculation.py` (nuevo) — tests de este plan.
- `tests/helpers.py` — posible fábrica nueva si hace falta (p. ej. helper para instanciar `CarModelPartForm`/`SaleHeaderForm` con datos válidos reusando `build_full_scenario()` de TASK-005).

**No tocado** (confirmado en investigación, fuera de alcance): `static/product/sales_event.js`, `business/proforma.py::convertir_venta_metro_lineal`, `serializer/invoice_serializer.py`, `custom_views/invoice.py`, `proforma/src/`, cualquier archivo de `migrations/`.

## Implementation steps

1. Escribir primero los tests de caracterización del comportamiento **actual** (sin tocar código): un `CarModelPartForm` con `installation_price`/`window_film_price`/`sub_total` manipulados (sin relación a `Car_Model_Part`/inventario reales) es válido y guarda esos valores tal cual; un `save_related` en creación no cambia `total_price` aunque los ítems no coincidan con la suma real. Confirmar que fallan/documentan el bug antes de seguir (mismo patrón que TASK-005 paso 1).
2. Agregar `Proforma_Business.recalculate_total_price` en `business/proforma.py`, con su unit test (crear detalles con `sub_total` conocido, llamar al método, verificar `total_price` recalculado; caso con cero detalles → `total_price = 0`).
3. Corregir `cleaned_data.get("sales_header")` → `cleaned_data.get("proforma_header")` en `CarModelPartForm.clean()`. Verificar con un test mínimo que, solo con este cambio (sin agregar todavía la resolución de precio), las validaciones ya existentes de ancho/`quantity`/`installation_price` empiezan a ejecutarse (para aislar el efecto del fix del bug del efecto del recálculo de precio, y poder documentar cada uno por separado si algo se rompe).
4. Agregar la resolución de precio real (`Car_Model_Part` + `Pricing_Business.resolve_unit_price` + `calculate_subtotal_venta_instalacion`) dentro de la rama `venta_instalacion` de `clean()`, con sus tests: override de precio manipulado, rechazo cuando falta `Car_Model_Part`, rechazo cuando no hay inventario que cubra la lámina/ancho, `venta_metro_lineal` sigue sin recalcular (test explícito del límite de alcance, mismo patrón que TASK-005).
5. Reescribir `ProformaAdmin.save_related` para llamar a `recalculate_total_price` después de `super().save_related(...)`, eliminando `to_reduce`/`to_add`. Test de integración: crear proforma con 2 ítems vía formset simulado, verificar `total_price` = suma de los `sub_total` recalculados (no el manipulado); editar la misma proforma eliminando un ítem, verificar que `total_price` baja a la suma de los que quedan (reemplaza el caso que antes cubría `to_reduce`).
6. Correr la suite completa de `product/` (`python manage.py test product`) contra una base de datos real (mismo procedimiento que TASK-005/TASK-002: contenedor Postgres descartable si el sandbox lo permite) para confirmar que no hay regresión en `test_smoke.py`/`test_sucursal_scope_admin.py`/`test_invoice_pricing.py`.
7. **Verificación manual explícita en un entorno real** (no solo tests automatizados): crear y editar al menos una proforma `venta_instalacion` desde `/admin/product/proforma_header/` con datos reales de sucursal/modelo/lámina, confirmando en pantalla que el `total_price` mostrado tras guardar coincide con el recalculado y que no aparecen errores de validación inesperados para combinaciones normales de datos. Exigido explícitamente por ADR-006 dado el precedente de ADR-002 (un error de requerimiento de negocio que la suite automatizada en verde no detectó). Documentar en el TASK el resultado de esta verificación antes de pasar a `delivery-review`.

## Test strategy

**Nivel unitario/integración backend** (`praxsa_manager/product/tests/`, `python manage.py test product`):
- `Proforma_Business.recalculate_total_price`: suma correcta con 1 y con varios `Proforma_Detail`; caso sin detalles → `0`.
- `CarModelPartForm` (`venta_instalacion`): precio manipulado en el form se sobrescribe con el recalculado (`installation_price`, `window_film_price`, `sub_total`); `quantity > 1` multiplica correctamente; error de validación (no guarda) cuando no existe `Car_Model_Part` para `(car_model_id, car_part)`; error de validación cuando no hay inventario que cubra `(sucursal, lámina, ancho)`.
- `CarModelPartForm` (`venta_metro_lineal`): explícitamente NO se recalcula precio (test que documenta el límite de alcance de este plan, mismo patrón que `test_length_width_quantity_are_still_trusted_from_the_client` de TASK-005).
- `CarModelPartForm` — validaciones reactivadas por el fix del bug: ancho de lámina insuficiente para el ítem → error; `quantity < 1` o `installation_price < 1` en `venta_instalacion` → error; `quantity > 0` o `installation_price > 0` en `venta_metro_lineal` → error (reglas ya escritas en el código, solo vuelven a ejecutarse).
- `ProformaAdmin.save_related` (integración, vía `RequestFactory`/formset simulado, mismo nivel que `AdminGetQuerysetWiringTest` de TASK-002): creación de proforma con 2 ítems → `total_price` = suma de los recalculados, no el enviado; edición eliminando un ítem → `total_price` baja a la suma de los que quedan; edición sin eliminar nada → `total_price` se mantiene consistente con los `sub_total` recalculados.
- Regresión: suite completa (`test_smoke.py`, `test_invoice_pricing.py`, `test_sucursal_scope_admin.py`, `test_public_catalog_endpoints.py`) sin romperse — ninguno de estos toca `CarModelPartForm`/`ProformaAdmin.save_related` hoy, pero deben seguir en verde.

**No corresponde E2E** — mismo criterio que TASK-005/ADR-004: el cambio vive enteramente en Python (`Forms/`, `admin_config/`, `business/`) y no toca ningún contrato de API que consuma Angular ni ninguna vista fuera del admin de Django. El admin de Django no tiene flujo de usuario final ni navegación multi-paso equivalente al de la calculadora Angular — un test de integración a nivel de formset ya ejercita la ruta real de guardado sin necesidad de un browser real. Playwright sigue sin estar instalado en el proyecto; este plan no lo requiere.

## Acceptance criteria

- [ ] Crear una proforma `venta_instalacion` desde el admin con `sub_total`/`installation_price`/`total_price` manipulados en el POST persiste los valores **recalculados**, no los manipulados (verificado leyendo `Proforma_Header`/`Proforma_Detail` directo de BD, no solo la respuesta HTTP).
- [ ] Editar una proforma `venta_instalacion` existente (agregar/eliminar/modificar ítems) deja `total_price` = suma real de los `sub_total` recalculados de los ítems que sobreviven.
- [ ] Guardar un ítem sin `Car_Model_Part` correspondiente, o sin inventario que cubra la lámina/ancho, rechaza el guardado con un error de validación visible (no persiste nada, no lanza 500).
- [ ] `venta_metro_lineal` sigue sin recalcular precio server-side (comportamiento sin cambios, con test explícito que lo documenta).
- [ ] `CarModelPartForm.clean()` usa `proforma_header` (no `sales_header`); las validaciones de ancho/`quantity`/`installation_price` por `sales_type` se ejecutan y tienen test.
- [ ] `python manage.py test product` completo en verde, ejecutado contra una base de datos real (no solo inspeccionado).
- [ ] `python manage.py makemigrations product --check --dry-run` → `No changes detected` (no se tocó ningún modelo).
- [ ] Verificación manual en el admin real documentada en el TASK (paso 7 de implementación).
- [ ] `git diff origin/master...HEAD --stat` no toca ningún archivo fuera de los listados en "Files/components affected".

## Risks

- **La reactivación de validaciones dormidas desde 2023 puede bloquear datos que el personal guarda hoy sin problema** (p. ej. anchos de lámina que hoy pasan sin chequeo). Mitigación: paso 7 (verificación manual explícita) antes de publicar; si aparece un caso real bloqueado sin justificación de negocio, se documenta como hallazgo y se decide con el usuario si corresponde relajar esa regla puntual, sin revertir el recálculo de precio (son cambios independientes dentro del mismo `clean()`, según ADR-006).
- **Orden de ejecución de `clean()` en un formset inline**: hay que confirmar empíricamente (con el test del paso 3) que `cleaned_data.get("proforma_header")` efectivamente devuelve el header ya poblado (`sales_type`/`car_model_id`/`sucursal`) en el momento en que se valida cada fila del inline, incluso en el caso de **creación** (header sin PK todavía). Si Django no lo expone ahí como se espera, el diseño de "recalcular dentro de `clean()` del inline" necesitaría moverse a `save_related` en su lugar — el paso 3 de implementación existe específicamente para descubrir esto temprano, antes de construir el resto sobre un supuesto no verificado.
- **`Sum('sub_total')` sobre un queryset vacío devuelve `None` en Django**, no `0` — `recalculate_total_price` debe manejar ese caso explícitamente (`or Decimal('0')`), cubierto en el test del paso 2.
- Sin riesgo de migraciones ni de contrato de API (ver Architecture considerations) — el riesgo de este cambio es enteramente de comportamiento/UX del admin, no de infraestructura.

## Out of scope

- `venta_metro_lineal` en cualquiera de sus dos caminos (`sales_event.js` rama `else`, `convertir_venta_metro_lineal`) — bloqueado por la pregunta de negocio sin resolver de `docs/integration-and-backlog.md:251` (backlog #2 paso 6, queda para un task futuro).
- Retro-adaptar `get_inventory`/`get_car_part_info` para usar `Pricing_Business` (ya estaba fuera de alcance en TASK-005, sigue sin tocarse aquí).
- Cualquier cambio a `proforma/src/` (Angular) o `serializer/invoice_serializer.py`/`custom_views/invoice.py` (REST, ya resuelto en TASK-005).
- SEC-07 (condición de carrera por mutación de `self` en `changelist_view` de varios admins) — hallazgo independiente, no relacionado con precio, ya documentado por TASK-002.

**Pregunta abierta para el usuario** (no bloquea este plan, pero puede afectar el paso 7): si la verificación manual del admin real revela que alguna combinación de datos usada hoy por el personal de sucursal queda bloqueada por las validaciones reactivadas del bug de 2023, ¿se prioriza corregir esa regla puntual en este mismo PR, o se documenta como hallazgo separado y se publica igual? Se decidirá con evidencia concreta en ese momento, no de antemano.
