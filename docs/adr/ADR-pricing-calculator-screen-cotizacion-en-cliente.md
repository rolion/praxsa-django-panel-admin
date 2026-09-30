# ADR-pricing-calculator-screen-cotizacion-en-cliente: La cotización es una vista previa calculada en el cliente con la API existente; "Crear Proforma" recibe un borrador por `history.state`; "Recomendada" y WhatsApp por sucursal quedan diferidos

**Estado:** Propuesto
**Task relacionado:** TASK-pricing-calculator-screen
**Fecha:** 2026-09-30

## Contexto

La calculadora muestra precios por ítem y un total antes de crear la proforma (DDR). Hechos de la investigación:
- Los datos necesarios ya los sirven endpoints staff existentes: sucursales (`ordenes/catalogo/sucursales`), bobinas con `unit_price` y `available_meters` por sucursal (`ordenes/catalogo/bobinas`, `ordenes_admin.py:401-411`), marcas/modelos (`vehicles/brands`, `vehicles/models` con `image`) e ítems del modelo con `width`, `length`, `quantity`, `installation_price` (`vehicles/models/<id>/items/`).
- La fórmula ya existe en el cliente (`panel_admin/src/app/ordenes/ordenes.calc.ts:27-51`, `previewSubtotal`/`round2`) y en el servidor (`business/pricing.py:86-93`), con paridad fijada por `tests/test_ordenes_price_parity.py`. El servidor es la autoridad y recalcula al crear la proforma (`ADR-modulo-ordenes-proforma-nota-trabajo-api-y-calculo`, ADR-004).
- Reglas de aptitud del servidor: el ancho de la bobina debe ser `>=` el del ítem (`pricing.py:158-160`) y deben alcanzar los metros (`pricing.py:101-108,162`).
- La cotización no se persiste; "Recomendada" no existe en modelo, API ni docs; el número de WhatsApp está fijo en `proforma/` (`formulario.component.html:133`).

## Decisión

1. **Sin cambios de backend ni migraciones.** La pantalla consume solo endpoints existentes vía `OrdenesService.listSucursales/listBobinas` y `VehiclesService.listBrands/listModels/listModelItems`; no se agrega endpoint de cotización.
2. **El total es vista previa del cliente**, calculada con `previewSubtotal` de `ordenes.calc.ts` (tipo de venta instalación). No se escribe una tercera implementación de la fórmula. Como la cotización no se persiste, no necesita una cifra autoritativa; al crear la proforma el servidor recalcula, y el resultado puede diferir si cambió stock o precio (la pantalla lo rotula como referencial, según la alerta del DDR).
3. **Aptitud de láminas en cliente, solo como filtro de UX** (ancho y metros suficientes, igual que las reglas del servidor), nunca como validación: el servidor sigue rechazando lo inválido al crear la proforma.
4. **Estado y formularios:** `ReactiveForms` (`FormGroup` de filtros + `FormArray` de ítems, con un control de lámina y uno de "excluido" por ítem) y `signal`/`computed` para el total y el desglose, en componentes standalone (`@if`/`@for`). Carpeta nueva `panel_admin/src/app/calculadora/` con su modelo de datos, un servicio-fachada fino (solo orquesta los servicios existentes) y su `*.routes.ts`, siguiendo la estructura de `ordenes/` y `vehicles/`.
5. **Paso a "Crear Proforma":** se navega a `/ordenes/proformas/create` con un **borrador** (sucursal, modelo, líneas con ítem + lámina/ancho + largo + cantidad) en `history.state` bajo una clave versionada. `ProformaFormComponent` lo lee al iniciar; si existe y es válido, precarga; si no existe (recarga, acceso directo), abre el formulario vacío como hoy. El borrador no se guarda en `localStorage` (`ADR-003-reduce-localstorage-pii`; además no contiene datos del cliente). El formulario sigue siendo la única vía de alta: datos del cliente, validaciones y permiso `add_proforma_header` no se duplican.
6. **"Crear Proforma" visible solo con permiso** `add_proforma_header` mediante `AuthService.hasPermission` (UX). La barrera real es la del `POST` existente (`DjangoModelPermissions` + alcance por sucursal).
7. **WhatsApp:** enlace `wa.me` con mensaje prearmado; el número sale de un único valor de configuración del frontend (`environment`), global. Un número por sucursal exigiría un campo nuevo en el modelo de sucursal y se difiere hasta que negocio lo confirme.
8. **"Recomendada" diferida:** en esta entrega no hay campo, regla ni endpoint; la UI reserva el espacio del badge pero no lo renderiza. Cuando negocio defina la regla: si se deriva de datos existentes (stock/precio), se calcula en cliente con un criterio documentado; si requiere un dato nuevo, se abre un ADR propio (modelo + migración + API). No se anticipa hoy.
9. **Imagen del vehículo:** se usa `AppCarModel.image` tal cual la entrega el API, con placeholder si es `null`.

## Alternativas consideradas

- **Endpoint de cotización en el backend** (`ordenes/cotizar` reutilizando `Pricing_Business`): centraliza la fórmula y evita divergencias de redondeo, pero agrega API, permisos, serializers y tests para un dato que no se persiste y que el servidor ya recalcula al crear la proforma. Mayor esfuerzo sin problema real que lo justifique; se puede revisar si se observa divergencia.
- **Copiar el cálculo de `proforma/` (`formulario.component.ts:238`)**: triplica la fórmula y usa `float`; descartada, `ordenes.calc.ts` ya cubre el caso y está respaldado por paridad.
- **Crear la proforma directamente desde la calculadora** (modal con datos del cliente y `POST` inmediato): duplica validaciones y riesgo de inconsistencia con el formulario. Descartada (ya decidido en el DDR).
- **Pasar el borrador por query params, servicio singleton o `localStorage`**: los query params son largos y visibles; `localStorage` persiste estado y contradice `ADR-003`; un servicio singleton funcionaría pero agrega un servicio global. `history.state` es lo más simple y su fallo es inocuo (formulario vacío); se puede cambiar sin impacto en contratos.
- **Calcular "Recomendada" ya en cliente** (p. ej. la más barata): descartada por ser una regla de negocio inventada.

## Estrategia de rollback / mitigación

Cambio **aditivo y sin backend**: sin migraciones, sin cambios de contrato ni de permisos. La única modificación a código existente es en `ProformaFormComponent` (lectura opcional del borrador); con `history.state` ausente o inválido el comportamiento es idéntico al actual. Rollback = quitar la ruta `calculadora`/ítem de menú y revertir la lectura del borrador; las proformas ya creadas no se ven afectadas. Mitigación del riesgo de divergencia de importes: el servidor fija el valor definitivo al crear la proforma y la cotización se rotula como referencial.

## Consecuencias

- Más fácil: sin trabajo de backend, fórmula única en cliente, reutilización del formulario de alta con sus validaciones y permisos.
- Más difícil: `ProformaFormComponent` y la calculadora comparten `ordenes.calc.ts`; cualquier cambio de fórmula debe tocar cliente y servidor y mantener la paridad.
- Deuda aceptada: la calculadora del cliente final en `proforma/` (Angular 16) mantiene su propia lógica; no se unifica aquí. El número de WhatsApp global y la ausencia de "Recomendada" son límites conscientes de esta entrega y dependen de decisiones de negocio pendientes.
- El área no tiene pruebas hoy: el plan debe incluir specs de la calculadora (aptitud, total, exclusión de ítems, estados) y del preload del borrador en el formulario.
