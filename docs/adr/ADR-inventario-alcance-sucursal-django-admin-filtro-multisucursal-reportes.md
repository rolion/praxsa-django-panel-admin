# ADR-inventario-alcance-sucursal-django-admin-filtro-multisucursal-reportes: Contrato del filtro multisucursal de reportes y significado de "Todas"

**Estado:** Propuesto
**Task relacionado:** TASK-inventario-alcance-sucursal-django-admin
**Fecha:** 2026-10-02

## Contexto

El DDR del task pide que el filtro de sucursal de Reportes pase a multiselect, con las sucursales **activas marcadas por defecto** y las inactivas seleccionables (lectura). Hechos del contrato actual (verificados):
- `GET reportes/ventas-diarias` y `reportes/utilidad` reciben un único `?sucursal=<id>` (`ReporteParamsSerializer` en `serializer/reportes_serializer.py`, usado en `custom_views/reportes_admin.py:30-60`); sin parámetro significa "todas las del alcance".
- `_ventas` valida la sucursal contra `get_sucursales_in_scope` (404 si no está) y filtra con `Reportes_Business.filtrar_pagos(..., sucursal_id=...)` (`reportes_admin.py:44-60`). `sin_sucursal` = no admin sin sucursal habilitada (`:56`).
- El panel (`reporte-base.ts:31,73-84`) envía un solo id o `null`.
- El Django Admin también filtra por sucursal (`admin_config/filtros_reportes.py:19`, `RelatedDropdownFilter` en `report_storage.py:37-38`).
- El dashboard recibe un único `sucursal` (`dashboard_admin.py:42`).

Depende de `ADR-inventario-alcance-sucursal-django-admin-alcance-lectura-escritura` (alcance de lectura vs. escritura, superusuario).

## Decisión

1. **Nuevo parámetro `sucursales`** (lista separada por comas de ids enteros) en los dos endpoints de reportes. El parámetro `sucursal` (un id) **se conserva** como alias y, si vienen ambos, se unen. No se rompe ningún cliente existente.
2. **Validación:** cada id debe estar en el alcance de **lectura** del usuario; un id fuera de alcance, no numérico o inexistente responde 404 `Sucursal no encontrada.` (mismo comportamiento y mensaje que hoy), sin revelar si existe. Se aceptan sucursales inactivas del usuario (los reportes son lectura). Se limita el número de ids al total de sucursales del alcance (duplicados se ignoran).
3. **Significado de "Todas" (sin `sucursal`/`sucursales`):** todas las sucursales **activas** del alcance de lectura del usuario (superusuario: todas las activas). Las inactivas solo entran si se piden explícitamente. Esto implementa el supuesto del DDR (activas marcadas por defecto); si el negocio decide lo contrario, se cambia solo ese valor por defecto.
4. **Filtro en el negocio:** `Reportes_Business.filtrar_pagos` acepta una lista de ids (`sucursal_ids`) además del id único (se mantiene la firma actual con el id como caso particular). La consulta usa `__in`.
5. **`sin_sucursal`:** pasa a significar "el usuario no tiene ninguna sucursal en su alcance de lectura" (admin incluido; el superusuario nunca). El resultado es 0 filas con `sin_sucursal=true`, como hoy.
6. **Respuesta:** las filas conservan `sucursal_id`/`sucursal_name`; se agrega `sucursales` (ids y nombres efectivamente consultados) y `sucursal_activa` por fila solo si el panel lo necesita para el badge; es aditivo. El catálogo de sucursales del panel (`ordenes/catalogo/sucursales`) devuelve el campo `activa` (ADR de alcance, decisión 5).
7. **Dashboard:** mantiene un único `sucursal`; "Todas" significa también las activas del alcance, y puede elegir una inactiva explícitamente. No se pasa a multiselect (fuera del pedido).
8. **Django Admin de reportes:** el filtro de sucursal ya es un desplegable de una sola selección; se limita a las sucursales del alcance de lectura y mantiene "Todas" = activas. Multiselect en Django Admin queda fuera de alcance.

## Alternativas consideradas

- **Reutilizar `sucursal` repetido (`?sucursal=1&sucursal=2`)**: es el estilo nativo de `QueryDict.getlist`, sin parsear comas. Se descarta porque obliga a cambiar el serializer de parámetros y el servicio del panel (`HttpParams` con append) en un solo golpe sin retrocompatibilidad clara; la lista separada por comas es trivial de validar y deja `sucursal` intacto.
- **Reemplazar `sucursal` por `sucursales`**: contrato más limpio, pero rompe a cualquier consumidor existente (`reportes.components.spec.ts`, posibles clientes). Descartada por riesgo innecesario.
- **"Todas" = todas las del alcance de lectura (incluidas inactivas)**: conserva los totales históricos por defecto, pero contradice el pedido ("solo seleccionar las activas") y el DDR. Descartada; el usuario puede marcar las inactivas.
- **Filtrar en el cliente** tras pedir todo: expondría datos de sucursales no marcadas y complica la paginación/totales. Descartada.
- **Endpoint distinto por sucursal y sumar en el cliente**: más llamadas, totales inconsistentes. Descartada.

## Estrategia de rollback / mitigación

El cambio es **aditivo** en el contrato (`sucursales` nuevo, `sucursal` intacto, campos nuevos en la respuesta) y no toca modelos ni migraciones. Revertir el commit restaura el comportamiento anterior sin migraciones; los clientes que solo usan `sucursal` no se ven afectados. El único efecto observable (el valor por defecto "Todas" pasa a excluir sucursales inactivas) se revierte cambiando ese valor en una línea de la capa de reportes. Mitigación: tests de contrato para ambos parámetros, mezcla de ambos, ids fuera de alcance y "Todas" con/sin sucursales inactivas.

## Consecuencias

- El panel puede ofrecer el multiselect sin un cambio de versión de API; el Django Admin sigue con selección única.
- Los totales por defecto de un usuario con sucursales inactivas dejan de incluirlas hasta que las marque; aceptado (asunción del DDR, pendiente de confirmar).
- Hay dos formas válidas de pedir una sucursal (`sucursal` y `sucursales`) mientras no se retire la antigua; deuda menor documentada.
- Tests de reportes y dashboard (`test_reportes_*`, `test_dashboard_*`) cambian en dos puntos: sin excepción de admin y valor por defecto de "Todas".
- Supuesto de negocio pendiente de confirmar: "Todas" = activas del alcance (frente a todas las del alcance de lectura).
