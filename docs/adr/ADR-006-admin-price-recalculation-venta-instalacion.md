# ADR-006: Recalcular server-side el precio de `venta_instalacion` en `ProformaAdmin`, reusando `Pricing_Business`; dejar `venta_metro_lineal` fuera de alcance hasta resolver la pregunta de negocio pendiente

**Estado:** Propuesto
**Task relacionado:** TASK-007
**Fecha:** 2026-09-23

## Contexto

TASK-007 (investigación) confirmó que `ProformaAdmin` (el camino de creación/edición de proformas desde el admin de Django, usado por personal de sucursal) persiste `total_price`/`sub_total`/`installation_price`/`window_film_price` exactamente como los calculó `sales_event.js` en el navegador, sin ninguna verificación server-side — el mismo hallazgo BIZ-01 que ADR-004/TASK-005 ya cerraron para el camino REST (`SalesHeaderSerializer.create()`), pero nunca para este camino (backlog #2, paso 5 de `docs/integration-and-backlog.md`).

TASK-007 también encontró, como hallazgo nuevo no documentado antes, que `CarModelPartForm.clean()` ([Forms/car_model_part.py:56](../../praxsa_manager/product/Forms/car_model_part.py)) busca `cleaned_data.get("sales_header")`, un campo renombrado a `proforma_header` en 2023 ([migrations/0066](../../praxsa_manager/product/migrations/0066_alter_proforma_header_options_and_more.py)) — por lo que todo el bloque de validación condicional por `sales_type` (ancho de lámina vs. ítem, `quantity`/`installation_price` requeridos u opcionales según el caso) está muerto desde entonces.

Se consultó al usuario sobre tres decisiones de negocio que la investigación dejó explícitamente abiertas (no inferibles del código):

1. **¿Sobrescribir siempre o rechazar cuando el precio recalculado difiere del enviado por el form?** → El usuario confirmó: **sobrescribir siempre**, igual que ADR-004 en el REST.
2. **Para `venta_metro_lineal`, ¿el subtotal se multiplica por `quantity` o no?** → El usuario respondió: **no lo sabe, hay que confirmarlo con negocio antes de tocar código**. Sigue siendo la misma pregunta bloqueante de `docs/integration-and-backlog.md:251` (sección 6), sin resolver.
3. **¿Corregir en este task el bug `sales_header`/`proforma_header`?** → El usuario confirmó: **sí, corregirlo como parte de este task**.

Estas tres respuestas determinan el alcance de esta decisión.

## Decisión

**Alcance de este ADR: solo `sales_type = venta_instalacion`.** Es el único caso con fórmula acordada y sin ambigüedad de negocio (confirmado en TASK-005 y re-verificado en TASK-007: Angular y `sales_event.js` ya coinciden en esa fórmula). `venta_metro_lineal` queda explícitamente fuera — ver "Fuera de alcance" abajo.

1. **Recalcular siempre, sobrescribir siempre.** Al guardar una proforma `venta_instalacion` desde el admin (creación o edición), el servidor resuelve el precio unitario real (`Pricing_Business.resolve_unit_price`, ya centralizado en TASK-005) y el `installation_price` real (`Car_Model_Part`, misma fuente que ya usa `get_car_part_info`) por cada ítem, recalcula `sub_total` con `Pricing_Business.calculate_subtotal_venta_instalacion` (ya existe, sin cambios), y **siempre sobrescribe** lo que trae el formulario — nunca rechaza por discrepancia con el valor enviado. Un ajuste de precio intencional (p. ej. negociación en sucursal) debe canalizarse por el campo `discount` ya existente en `Proforma_Header`, no editando `sub_total`/`installation_price`/`total_price` a mano. Mismo criterio de producto que ADR-004, extendido aquí por decisión explícita del usuario — no se asume, se confirma.
2. **`Proforma_Header.total_price` se recalcula como la suma de los `sub_total` reales de sus `Proforma_Detail`** (no como resta manual de ítems eliminados). Esto reemplaza la lógica actual de `save_related` (`to_reduce`, que solo ajustaba el total por ítems eliminados en `change == True` y no hacía nada en creación) por un cálculo uniforme: una vez que el formset ya guardó altas/bajas/modificaciones, sumar los `sub_total` recalculados de los ítems que sobreviven. Aplica igual a creación y edición — elimina la asimetría que hoy existe entre ambos casos.
3. **Rechazar (error de validación del form, no un 500) solo cuando el precio real no se puede resolver** — mismo criterio que ADR-004 (`Car_Model_Part` inexistente para `(car_model_id, car_part_id)`, o ningún `inventario` que cubra `(sucursal, lámina, ancho)`). Esto es un caso de datos faltantes genuinos, no de discrepancia de precio.
4. **Corregir el bug `sales_header` → `proforma_header` en `CarModelPartForm.clean()`**, reactivando las validaciones condicionales por `sales_type` que llevan dormidas desde 2023 (ancho de lámina suficiente, `quantity`/`installation_price` coherentes con el caso). Se hace en el mismo cambio porque toca el mismo método (`clean()`) que necesita tocarse para integrar la resolución de precio real, y porque dejar el bug sin corregir dejaría el nuevo recálculo de precio conviviendo con datos de ítem potencialmente inconsistentes (ancho insuficiente, cantidad en cero) que la propia validación ya pretendía impedir. Al activar estas reglas, `delivery-plan` debe prever que algún flujo de trabajo actual del personal podría empezar a fallar validación donde antes no fallaba — el plan debe incluir verificación manual explícita de esto antes de publicar (no basta con tests automatizados).
5. **Dónde vive el recálculo**: se centraliza en la capa `Forms`/`admin_config` (no se crea una nueva capa `business/` para esto — `Pricing_Business` ya existe y se reusa tal cual). La decisión exacta de si el recálculo ocurre en `CarModelPartForm.clean()` (por ítem, con acceso a `Car_Model_Part`/`Pricing_Business` ahí mismo) y la suma de `total_price` en `ProformaAdmin.save_related` (después de que el formset persiste los ítems), o se concentra todo en `save_related`, es una decisión de implementación concreta — queda para `delivery-plan`, no para este ADR.

## Alternativas consideradas

- **Recalcular en `CarModelPartForm`/`SaleHeaderForm.clean()` únicamente (antes de guardar nada)**: más parecido al patrón REST (`SalesHeaderSerializer.validate()`), pero los forms de un inline no tienen fácil acceso al resto de ítems del formset para sumar `total_price` durante su propio `clean()` — el total de cabecera solo se puede calcular con certeza después de que el formset completo (altas + bajas + modificaciones) esté resuelto. Se descarta como única fuente; el recálculo de `total_price` queda en `save_related`, después del formset.
- **Dejar `total_price` como la resta manual de eliminados (`to_reduce`) y solo corregir el precio por ítem**: mantiene la asimetría creación/edición y no resuelve el caso de creación (`change == False`), donde hoy no se recalcula nada. Se descarta — no cierra completamente el backlog #2 paso 5.
- **Rechazar (400/form error) en vez de sobrescribir ante discrepancia**: descartada explícitamente por el usuario — mismo criterio que ADR-004, con el argumento adicional de que el admin es una herramienta operativa diaria y bloquear guardado por discrepancias de precio (incluyendo ruido de redondeo en `float` del lado del navegador, mismo riesgo ya documentado en TASK-005) rompería el flujo de trabajo sin necesidad, cuando el campo `discount` ya cubre el caso legítimo de ajuste manual.
- **Resolver también la fórmula de `venta_metro_lineal` en este mismo ADR, asumiendo una de las dos implementaciones existentes como la correcta**: descartada explícitamente — el usuario no confirmó cuál es la fórmula correcta, y decidir unilateralmente violaría la restricción de `docs/CLAUDE.md` ("si algo no se puede verificar, decirlo; no inventar") aplicada a una decisión de negocio, no solo de código. Ver "Fuera de alcance".

## Fuera de alcance (bloqueado, no descartado)

**`venta_metro_lineal` no se toca en la implementación derivada de este ADR.** Ni `sales_event.js` (rama `else` de `calculate_subtotal`) ni `Proforma_Business.convertir_venta_metro_lineal` se modifican — la divergencia entre ambas (¿multiplica por `quantity` o no?, backlog `docs/integration-and-backlog.md:251`) sigue existiendo sin corregir. `Pricing_Business.resolve_unit_price` (resolución de precio unitario) ya es agnóstico de `sales_type` y quedará disponible para cuando se resuelva; falta escribir `calculate_subtotal_venta_metro_lineal` una vez decidida la fórmula. Backlog #2 paso 6 queda explícitamente pendiente — es trabajo para un task futuro, una vez que el usuario confirme la fórmula con quien corresponda en el negocio. Esto significa que, tras esta implementación, el admin seguirá aceptando sin verificar server-side cualquier `sub_total`/`total_price` para proformas `venta_metro_lineal` (tanto creadas desde cero como por conversión) — deuda conocida y documentada, no un olvido.

## Estrategia de rollback / mitigación

Cambio de solo backend/admin, sin contrato de API expuesto a Angular (no toca `serializer/`, `custom_views/`, ni `proforma/src/`), sin migraciones de esquema (no se agregan/quitan columnas ni modelos). Riesgo de producción acotado a: (a) el admin empieza a rechazar guardados de `venta_instalacion` con `Car_Model_Part`/inventario faltante donde antes se guardaban silenciosamente con datos inconsistentes, y (b) las validaciones reactivadas de `CarModelPartForm.clean()` podrían bloquear combinaciones que el personal guarda hoy sin problema. Mitigación:
- Rollback simple por `git revert` del commit/PR — no hay estado persistido irreversible (no se migra ni transforma data existente, solo cambia la lógica de guardado hacia adelante).
- Antes de publicar, verificación manual explícita en un entorno real (no solo tests automatizados) creando y editando proformas `venta_instalacion` desde el admin, siguiendo la práctica ya usada en TASK-002/TASK-005 de este mismo proyecto — dado que este es exactamente el tipo de cambio (regla de negocio de precio) donde ya se detectaron antes errores de requerimiento (ADR-002) que los tests automatizados no capturaron.
- Si la reactivación de validaciones de `CarModelPartForm.clean()` bloquea un flujo real de trabajo no anticipado, se puede revertir *solo* ese punto (mantener el fix de recálculo de precio, volver a comentar/relajar las validaciones de ancho/`quantity`/`installation_price`) sin deshacer el resto del cambio — son cambios independientes dentro del mismo `clean()`, no acoplados entre sí.

## Consecuencias

**Más fácil:**
- El admin y el REST quedan consistentes en su tratamiento de `venta_instalacion`: ambos recalculan y sobrescriben siempre, usando la misma función `Pricing_Business.calculate_subtotal_venta_instalacion`.
- `total_price` deja de tener dos caminos de cálculo distintos entre creación y edición dentro del propio admin.
- Las validaciones de `CarModelPartForm` vuelven a ejecutarse después de 3 años dormidas, cerrando una brecha de calidad de datos no relacionada directamente con precio pero descubierta en el mismo lugar.

**Más difícil / deuda aceptada conscientemente:**
- `venta_metro_lineal` sigue sin ninguna verificación server-side de precio en ningún camino (REST nunca lo alcanza, admin ahora lo deja fuera de este ADR) — deuda ya documentada, explícitamente no resuelta aquí.
- Reactivar las validaciones de `CarModelPartForm.clean()` es, en sí mismo, un cambio de comportamiento con su propio riesgo de romper flujos de trabajo actuales del personal no cubiertos por tests automatizados — mitigado con verificación manual explícita antes de publicar, no eliminado.
- `convertir_venta_metro_lineal` sigue copiando `window_film_price` del detalle original sin re-resolverlo contra `precio_venta_sucursal`/`inventario` actual — no se toca en este ADR, sigue siendo una fuente de precio potencialmente obsoleta para esa acción específica.
