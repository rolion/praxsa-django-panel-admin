# ADR-modulo-ordenes-proforma-nota-trabajo-api-y-calculo: API REST de Órdenes para `panel_admin/` con cálculo de precios server-side reutilizando `Pricing_Business`

**Estado:** Propuesto
**Task relacionado:** TASK-modulo-ordenes-proforma-nota-trabajo
**Fecha:** 2026-09-29

## Contexto

La investigación confirmó que Proformas y Notas de Trabajo solo existen hoy en Django Admin, y que la API REST actual (`InvoiceView`/`ListUserInvoice`, `custom_views/invoice.py:15-104`) sirve al cliente final: filtra por `created_by`, solo crea, solo cubre `venta_instalacion` (`serializer/invoice_serializer.py:37-71`) y falla con 500 ante proformas de metro lineal (`invoice.py:41-42,62-64`). Las reglas de negocio completas viven en `CarModelPartForm.clean()` (`Forms/car_model_part.py:52-147`), `SaleHeaderForm` (`Forms/Sale_header.py:13-49`) y `Proforma_Business`.

El DDR (`DDR-modulo-ordenes-proforma-nota-trabajo-listado-y-flujo-ordenes`) fijó el comportamiento: listar/ver/editar/crear proformas de dos tipos, con la bobina (lámina + ancho, disponible en la sucursal) como eje de la línea; acciones "Generar nota de trabajo" y "PDF"; notas de trabajo con listado, ver y edición de campos operativos. Este ADR decide el contrato de API y dónde vive el cálculo. El alcance por rol/sucursal y los permisos están en `ADR-modulo-ordenes-proforma-nota-trabajo-alcance-permisos`.

## Decisión

1. **API nueva y separada para el panel**, con `TokenAuthentication`, rutas planas con `path()` en `product/urls.py` (mismo patrón que `users/`, `vehicles/`, `almacen/`), vistas en `custom_views/ordenes_admin.py` y serializers en `serializer/ordenes_serializer.py`. No se reutiliza ni se modifica `InvoiceView`/`SalesHeaderSerializer` (contrato del frontend `proforma/`, que queda intacto):

   | Método y ruta | Uso |
   |---|---|
   | `GET/POST ordenes/proformas` | Listado (sin líneas, con estado y total a pagar) y alta |
   | `GET/PATCH ordenes/proformas/<id>/` | Detalle con líneas y edición |
   | `POST ordenes/proformas/<id>/generar-nota-trabajo/` | Genera la nota (acción del pipeline) |
   | `GET ordenes/proformas/<id>/pdf/` | PDF de la proforma |
   | `GET ordenes/notas-trabajo` | Listado |
   | `GET/PATCH ordenes/notas-trabajo/<id>/` | Detalle (con resumen de láminas) y edición operativa |
   | `GET ordenes/catalogo/sucursales` | Sucursales dentro del alcance del usuario |
   | `GET ordenes/catalogo/bobinas?sucursal=<id>` | Láminas/anchos con stock en esa sucursal: metros disponibles y precio unitario resuelto |
   | `GET ordenes/catalogo/instaladores?sucursal=<id>` | Instaladores de esa sucursal |

   Los items de un modelo se obtienen del endpoint ya existente `vehicles/models/<model_id>/items/` (largo, ancho, cantidad y precio de instalación por item); el plan debe verificar que devuelve lo necesario y que no expone datos que el diseño de Vehículos decidió ocultar. `get_inventory` (`views.py:222-250`) **no** se reutiliza: es público, agrega por lámina/ancho y devuelve como `bobina_id` el id de la lámina, no de la bobina (`views.py:244`).

2. **La línea de proforma se identifica por (lámina, ancho)**, no por un id de bobina: `Proforma_Detail` no tiene FK a bobina (`models.py:245-263`) y el descuento de inventario ya resuelve por lámina + ancho exacto (`business/inventario.py:52-57`). No hay cambios de modelo ni migraciones. Entrada de cada línea: `car_part` (solo instalación), `window_film`, `width`, `length`, `quantity` (solo instalación).

3. **El servidor calcula y sobrescribe siempre** (ADR-004/ADR-006/TASK-010): `installation_price`, `window_film_price` y `sub_total` de cada línea y `total_price` de la cabecera se ignoran si vienen del cliente. Se reutilizan sin cambios `Pricing_Business.resolve_unit_price` y las funciones `calculate_subtotal_venta_instalacion`/`calculate_subtotal_venta_metro_lineal` (`business/pricing.py:13-39`) — las **fórmulas siguen en un único lugar**. La orquestación por línea se escribe una vez como función nueva en `business/pricing.py` y es la que usa el serializer del panel.

4. **Reglas de validación del alta/edición** (las mismas que hoy imponen los forms del admin, expresadas en el serializer):
   - Común: al menos una línea; `sucursal` obligatoria y dentro del alcance del usuario; `length > 0`; (lámina, ancho) debe existir con stock en la sucursal (ancho **exacto**, no `>=`, porque `reduce_inventory` exige ancho exacto); si no hay precio resoluble → error 400, nunca 500.
   - `venta_instalacion`: `car_model_id` y `car_plate` obligatorios (`Sale_header.py:35-49`); cada línea con `car_part` que exista para ese modelo en `Car_Model_Part`, `quantity >= 1`, y ancho de bobina >= ancho del item (`car_model_part.py:47-49,66-68`).
   - `venta_metro_lineal`: sin `car_part`, sin `quantity`, sin `installation_price` (`car_model_part.py:112-118`); modelo de vehículo y placa opcionales.
   - Descuento: no mayor al 50% del total **recalculado en servidor**, y con motivo si es > 0 (`Sale_header.py:13-33`). El form del admin lo compara contra el total que envía el cliente; aquí no.
   - El stock **no bloquea** el guardado de la proforma (igual que hoy; `car_model_part.py:74-77,139-145` tiene ese chequeo comentado). La UI lo muestra como orientación; la verificación real sigue ocurriendo al generar la nota de trabajo.

5. **`CarModelPartForm.clean()` no se toca.** Reescribirlo para que use la función nueva reabriría el riesgo que ADR-006 mitigó con verificación manual del flujo del personal. Se acepta duplicación de la orquestación (no de las fórmulas) y se compensa con tests de paridad que ejecutan el mismo caso por el form y por el serializer y comparan resultados. Migrar el form a la función nueva queda como deuda explícita.

6. **Edición.** `PATCH` no permite cambiar `sales_type` ni `sucursal` (400 si difieren; igual criterio que `proforma_admin.py:187-193`); rechaza con 409 si la proforma está cerrada (`is_close`) o `is_delete`. Si el `PATCH` incluye líneas, se **reemplaza el conjunto completo** dentro de `transaction.atomic()` (borrar + recrear + recalcular con `Proforma_Business.recalculate_total_price`, `business/proforma.py:188-197`). Sin diff parcial: una proforma abierta no tiene inventario descontado, así que reemplazar líneas es seguro. `proforma_created_on` seguirá moviéndose en cada guardado por su `auto_now=True` (`models.py:168`); cambiarlo requeriría migración y se deja fuera de alcance.

7. **Generar nota de trabajo** delega en `Proforma_Business.create_work_note(proforma, responsable=request.user)` (`business/proforma.py:96-138`) sin modificarlo. La vista bloquea la fila de la proforma (`select_for_update`) dentro de una transacción para evitar doble generación simultánea, y responde 409 si la proforma ya está cerrada. Los errores de negocio (`NoHayLaminasDisponibles`, `ProformaException`) se devuelven como 409/400 con su mensaje; lo inesperado, como 500 con mensaje genérico (sin filtrar detalles internos). La concurrencia sobre filas de `inventario` en `reduce_inventory` es preexistente y no se resuelve aquí.

8. **PDF** con `PDFService.create_proforma` tal como lo usa la acción del admin (`proforma_admin.py:263-273`); ya tolera `car_part` y `car_model_id` nulos (`helper/pdf.py:215,387-388`), por lo que cubre metro lineal. Requiere `sucursal` (`pdf.py:380-381`): proformas legadas sin sucursal devuelven 409 con mensaje claro.

9. **Nota de Trabajo.** `PATCH` acepta solo `instaladar`, `codigo_garantia`, `salida_vehiculo` y `observaciones`; el resto (proforma, responsable, cliente, vehículo, entrada) es de solo lectura. Rechaza con 409 si la nota ya tiene nota de venta (`is_close`). `codigo_garantia` vacío se normaliza a `null` (es `unique` y `null=True`, `models.py:202`); duplicado → 400. `instaladar` debe pertenecer a la sucursal de la proforma. No se expone alta ni baja de notas.

10. **Listados sin paginación servidor** (no existe `DEFAULT_PAGINATION_CLASS` en DRF), con serializer liviano (sin líneas), `select_related` de sucursal/modelo/marca y filtros opcionales `?search=`, `?sales_type=`, `?status=`. Coherente con el DDR (búsqueda cliente sobre el array completo) y con los demás módulos. Proformas es la tabla que más crece: se acepta el riesgo y se fija como disparador de revisión que el listado supere unos pocos miles de filas o tarde perceptiblemente.

11. **Vista previa de importes en el frontend** calculada localmente con `precio unitario` (catálogo de bobinas) y `precio de instalación` (items del modelo), con la misma fórmula que ya duplican `proforma/` y `sales_event.js`. No se agrega endpoint de "calcular"; la respuesta del alta/edición trae los importes definitivos y la UI los muestra tras guardar.

## Alternativas consideradas

- **Extender `InvoiceView`/`SalesHeaderSerializer`**. Descartada: su contrato es del frontend de cliente (filtra por dueño, solo instalación) y cualquier cambio arriesga `proforma/`; además ya tiene un bug latente con metro lineal.
- **Reescribir `CarModelPartForm` para compartir toda la validación con el serializer** (única fuente). Es lo ideal a largo plazo pero cambia el camino de trabajo diario del personal y obliga a repetir la verificación manual de ADR-006. Se descarta ahora; queda como deuda con tests de paridad como red de seguridad.
- **Usar Django Admin embebido/iframe o `ModelViewSet` sobre el `ModelAdmin`**. Descartada: mezcla sesión de admin con Token y no resuelve el formulario condicional por tipo de venta.
- **Endpoint `POST ordenes/proformas/calcular` para la vista previa**. Da una única fuente de verdad, pero agrega una llamada por cambio de campo y una superficie más; la duplicación de fórmula en el cliente ya existe y es una fórmula de una línea. Se puede añadir después sin romper nada.
- **Edición de líneas por diff (crear/actualizar/borrar individualmente)**. Descartada: más código y más casos de borde sin beneficio, ya que las líneas de una proforma abierta no tienen efectos externos.
- **Modificar `Proforma_Business.create_work_note` para que no dependa de `is_close`/excepciones genéricas**. Fuera de alcance: se reutiliza tal cual para no divergir del comportamiento del admin.
- **Bloquear el guardado de proformas cuando la longitud excede el stock**. Descartada: cambia una regla de negocio actual (cotizar sin reservar) y no fue pedida.

## Estrategia de rollback / mitigación

Cambio **aditivo**: endpoints nuevos, sin migraciones de esquema, sin modificar `InvoiceView`, `CarModelPartForm`, `Proforma_Business` ni los modelos. Riesgos y mitigaciones:
- **Inconsistencia de precios API vs admin**: tests de paridad (mismo input, mismo `sub_total`/`total_price`) y verificación manual en vivo creando proformas de ambos tipos por el panel y comprobando el resultado en Django Admin, siguiendo la práctica de TASK-002/005/007.
- **"Generar nota de trabajo" muta inventario**: reutiliza la misma función que el admin y queda detrás de permiso Django explícito (ver ADR de permisos); verificación manual en vivo contra datos de prueba, comprobando que el inventario baja y que el estado pasa a "Nota Trabajo".
- **Reversión**: `git revert` del PR; no hay datos migrados. Para desactivar sin revertir, basta quitar el grupo "Órdenes" de `panel_admin/src/assets/data/routes.json` (los endpoints exigen permisos y staff, así que sin asignación quedan inertes). Las proformas/notas creadas por el panel son filas normales que el admin sigue manejando.

## Consecuencias

**Más fácil:** el panel y el admin operan sobre las mismas entidades y reglas; el frontend de cliente no se ve afectado; no hay migración de datos.

**Más difícil / deuda aceptada:**
- Orquestación de validación duplicada entre `CarModelPartForm` y el serializer (fórmulas compartidas; orquestación no) — mitigada con tests de paridad, con migración del form como tarea futura.
- El subtotal mostrado antes de guardar puede diferir del definitivo (stock/precio cambió entre la carga del catálogo y el guardado).
- Listados sin paginación y `proforma_created_on` con `auto_now` siguen siendo limitaciones conocidas.
- Los bugs latentes de `Proforma_Business.delete_proforma`/`abrir_proforma` (`sales_status` inexistente, `e` sin `except`) no se tocan: esas acciones no forman parte de este alcance.
- `InvoiceView.get` sigue devolviendo 500 para proformas de metro lineal en el frontend `proforma/`; queda fuera de este task.
