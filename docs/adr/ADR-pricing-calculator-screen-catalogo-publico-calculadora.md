# ADR-pricing-calculator-screen-catalogo-publico-calculadora: La calculadora usa los catálogos públicos existentes (con filtro de activos e imagen), no los endpoints de staff

**Estado:** Propuesto
**Task relacionado:** TASK-pricing-calculator-screen
**Fecha:** 2026-09-30

## Contexto

La calculadora v1 consume endpoints solo para staff (`ordenes/catalogo/*`, `vehicles/*`; `IsStaffUser`, `ordenes_admin.py:43`). El DDR `DDR-pricing-calculator-screen-flujo-cliente` hace la calculadora **navegable sin sesión** y para clientes (que recibirían 403 en esos endpoints). Este ADR reemplaza el punto 1 de `ADR-pricing-calculator-screen-cotizacion-en-cliente` (fuente de datos) y conserva sus puntos 2, 3, 4, 7, 8 y 9. Hechos:
- Catálogos públicos existentes: `get_calculator_info` (`views.py:252-280`: marcas, modelos `id/name/brand_id`, partes, láminas, sucursales con `enable_to_install_windows_film`), `get_model_parts/<id>` (`views.py:313-325`: `width`, `length`, `quantity`, `part_id`, `part_name`, `installation_price` como `float`) y `get_inventory/<sucursal>/<lámina>/<ancho>` (`views.py:219-249`, con `PublicCatalogThrottle` 60/min, ADR-005); con `lamina=0` y `ancho=0` devuelve todas las bobinas con stock de la sucursal, con metros y `bobina_price` (`business/inventario.py:156-164`), igual precio que usa el servidor al guardar (`precio_sucursal` o `precio_venta_mtr_lineal`).
- `get_calculator_info` no filtra `is_active` (`views.py:257-261`), contra el ADR `ADR-modulo-vehiculos-soft-delete` (los inactivos no deben aparecer en selectores), y no expone la imagen del modelo (`Car_Model.image`, `models.py:29`), que el DDR muestra en el resumen.
- `proforma/` consume estos mismos endpoints (`data.service.ts`), por lo que cualquier cambio debe ser compatible.

## Decisión

1. **Fuente única de datos de la calculadora:** los catálogos públicos, para cualquier persona (sin sesión, cliente o staff): `get_calculator_info` (sucursales, marcas, modelos), `get_model_parts/<id>` (ítems) y `get_inventory/<sucursal>/0/0` (bobinas con metros y precio). El servicio de la calculadora adapta esas respuestas a los tipos ya existentes del frontend (`AppCarModelPart`, `ReelCatalogItem`, `FilmOption`), de modo que la pantalla, el cálculo con `ordenes.calc.ts` y el filtro de aptitud no cambian. Se retira el uso de `OrdenesService`/`VehiclesService` en `calculadora/`.
2. **Cambios aditivos en `get_calculator_info`:** (a) filtrar `is_active=True` en marcas, modelos y partes; (b) agregar `image` (URL absoluta o `null`) a cada modelo. Un consumidor que ignora campos no se rompe; sí desaparecen los inactivos del listado público, alineado con el ADR de vehículos (se verificará en pruebas que `proforma/` sigue funcionando).
3. **Sin endpoint nuevo de catálogo** y sin exponer datos más sensibles que los ya públicos (stock en metros y precio por metro ya se publican en `get_inventory`, aceptado en ADR-005). Se mantiene el throttle de `get_inventory`; la calculadora hace una llamada por cambio de sucursal, muy por debajo de 60/min.
4. **Errores de catálogo:** se muestran como el estado de error del DDR con "Reintentar"; no hay reload (ver `ADR-...-sesion-cliente-aislamiento`).
5. **Staff:** usa la misma fuente; su "Crear Proforma" sigue el camino de la v1 (formulario interno). El formulario interno sigue alimentándose de los endpoints de staff.

## Alternativas consideradas

- **Endpoint público nuevo agregado para la calculadora** (`calculadora/catalogo`, una sola llamada con modelos, ítems y bobinas): menos viajes y una forma a medida, pero duplica lógica de catálogo y amplía la superficie pública sin un problema real que lo justifique hoy. Se puede reconsiderar si el throttle o la latencia molestan.
- **Abrir los endpoints de staff a clientes** (quitar `IsStaffUser` en catálogos): rompe la barrera de ADR-modulo-ordenes (alcance por sucursal) y mezcla actores; descartada.
- **Dos fuentes** (staff con endpoints de staff, cliente con públicos): más código y posibilidad de precios distintos en pantalla según quien mire; descartada.
- **Exigir sesión para cotizar y usar endpoints autenticados de cliente:** contradice el DDR (cotizar sin sesión).
- **No filtrar `is_active` en el catálogo público:** mantiene inconsistencia conocida; los clientes verían modelos dados de baja.

## Estrategia de rollback / mitigación

Aditivo y de bajo riesgo: el filtro `is_active` y el campo `image` se agregan a una respuesta existente; si `proforma/` mostrara un efecto no deseado (modelo inactivo que antes aparecía), se revierte el filtro en una línea sin tocar datos ni migraciones. El cambio de fuente de la calculadora es del frontend y se revierte quitando el adaptador y volviendo a los servicios de staff (la v1 sigue en el repositorio). No hay migraciones ni cambios de infraestructura.

## Consecuencias

- Más fácil: una sola fuente, sin sesión, consistente con lo que ve el cliente de `proforma/`; el servidor ya recalcula precios al guardar (ADR-004).
- Más difícil: los catálogos públicos devuelven números como `float`/string según el campo (`installation_price` como `float`, `width`/`length` como string decimal): el adaptador debe normalizarlos y tratarlos solo como **vista previa**; el dinero autoritativo sigue en `Decimal` en servidor.
- Deuda aceptada: la respuesta de `get_calculator_info` sigue sin paginar ni cachear; no hay catálogo público de bobinas por modelo ni por ancho mínimo (la aptitud se calcula en el cliente).
