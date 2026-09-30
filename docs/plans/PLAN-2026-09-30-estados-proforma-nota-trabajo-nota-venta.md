# PLAN-2026-09-30-estados-proforma-nota-trabajo-nota-venta (v2)

**Task:** TASK-estados-proforma-nota-trabajo-nota-venta
**DDRs relacionados:** [DDR-estados-proforma-nota-trabajo-nota-venta-estados-y-cobro](../design/DDR-estados-proforma-nota-trabajo-nota-venta-estados-y-cobro.md)
**ADRs relacionados:**
- [ADR-estados-proforma-nota-trabajo-nota-venta-maquina-de-estados](../adr/ADR-estados-proforma-nota-trabajo-nota-venta-maquina-de-estados.md)
- [ADR-estados-proforma-nota-trabajo-nota-venta-api-y-permisos](../adr/ADR-estados-proforma-nota-trabajo-nota-venta-api-y-permisos.md)
- Reemplaza parcialmente `ADR-006-proforma-status-field` (decisiones 2 y 3)

## Objective
Reemplazar la inferencia de estados por `hasattr()`/`is_close` por un estado explícito en `Nota_trabajo` y `Nota_Venta` y un estado global derivado en `Proforma_Header`, con un único servicio de transiciones. La nota de venta nace con la nota de trabajo (`por_cobrar`); el pago solo se registra con el trabajo `terminado`. Exponerlo en la API y en `panel_admin/` (terminar trabajo, notas de venta, registrar pago).

## Context
Ver `docs/tasks/TASK-estados-proforma-nota-trabajo-nota-venta.md`. Resumen: hoy "Finalizado" significa tres cosas distintas, el `status` persistido puede divergir del admin (no se refresca al crear el pago), `abrir_proforma` deja viva la nota de trabajo, y la nota de venta/pago solo existen en Django Admin. Decisiones de negocio ya tomadas con el usuario: sin anticipos; backfill de notas de venta `por_cobrar` para notas de trabajo abiertas; **permisos por grupo y por acción** (ver matriz en "Architecture considerations"): Admin/Caja/Vendedor cobran y anulan pagos; Admin/Almacen terminan/corrigen el trabajo; Admin/Almacen/Vendedor editan proformas; Vendedor/Admin aprueban y anulan proformas; Almacen/Admin anulan la nota de trabajo; Caja/Vendedor/Admin anulan la nota de venta. Anular la nota de trabajo equivale a reabrir la proforma; anular la nota de venta solo con el trabajo `en_proceso` (decisiones del usuario, v2).

## Current behavior
(Verificado de nuevo al planificar; el código no cambió desde la investigación — `master` = `21beefe`.)
- `Proforma_Header.status` derivado: `business/proforma.py:30-50`; copia en `admin_config/proforma_admin.py:96-109` y `migrations/0106_proforma_header_status.py:10-32`.
- Sin estado propio: `Nota_trabajo` (`models.py:200-218`), `Nota_Venta` (`models.py:266-282`); `pago.cerrado` (`models.py:302`).
- Transiciones dispersas: `create_work_note` (`business/proforma.py:98-140`), `abrir_proforma` (`:63-84`), `crear_nota_venta` (`:201-223`), `Pago_Business.cerrar_pago` (`business/pago.py:29-47`), `delete_work_note` (`business/orden_trabajo.py:74-109`), y acciones en `proforma_admin.py`, `nota_trabajo.py`, `nota_venta.py`, `pagos.py`.
- API solo con proformas y notas de trabajo: `custom_views/ordenes_admin.py` (rutas en `urls.py:106-114`); la transición "aprobar" es `POST ordenes/proformas/<pk>/generar-nota-trabajo/` (`urls.py:108`).
- Guards por `is_close`/`hasattr(nota_venta)`: `ordenes_admin.py:116, 222`; `is_finalizada` en `ordenes_serializer.py:307-308`.
- Otros consumidores de `Nota_Venta`/`is_close` que hay que revisar: `admin_config/report_nota_trabajo.py:92-98,116,139` (llama `crear_nota_venta`), `admin_config/reporte_proforma.py:84-90`, `report_daily_sell.py`, `Forms/nota_venta_form.py`.
- Frontend: `panel_admin/src/app/ordenes/**` (`is_close` en `proforma-view.component.ts:61,65`; `is_finalizada` en `nota-trabajo-view.component.ts:49-65` y `notas-trabajo-list.component.html:72-80`); no hay pantallas de nota de venta ni pago.

## Expected behavior
- `Nota_trabajo.status ∈ {en_proceso, terminado, cancelada}`, `Nota_Venta.status ∈ {por_cobrar, pagada, anulada}`, `Proforma_Header.status ∈ {proforma, en_trabajo, por_cobrar, finalizado, anulada}` (global, derivado).
- Aprobar una proforma crea/reutiliza NT (`en_proceso`) y NV (`por_cobrar`, total = `total_price − discount`), descontando inventario.
- Terminar el trabajo exige garantía e instalador (venta con instalación) y fija `salida_vehiculo`. Registrar pago solo con NT `terminado`, con `monto` fijado por servidor. Anular la nota de trabajo o la de venta (equivale a reabrir la proforma: NT `cancelada`, NV `anulada`, inventario devuelto, proforma `proforma`) solo con NT `en_proceso` y NV `por_cobrar`. Anular pago solo si `pago.cerrado=False`.
- Django Admin y API usan el mismo servicio; las tres definiciones de "Finalizado" desaparecen.
- El panel muestra badges unificados, acción "Marcar trabajo terminado", listado/vista de Notas de Venta y modal "Registrar pago" (DDR).

## Architecture considerations
Resumen de los ADR (no se re-decide nada):
- **Contrato API:** cambian `status` de proforma (`nota_trabajo`→`en_trabajo`, se suma `anulada`), desaparece `is_finalizada`, se agregan `status`/`status_label`/`nota_venta` a la nota de trabajo y 9 endpoints nuevos. Único consumidor conocido: `panel_admin/`, que se despliega en el mismo release (hipótesis: `proforma/` no los usa — no se hallaron referencias). Nota de planificación: el ADR de API nombra `generate-nota`, pero la ruta real vigente es `generar-nota-trabajo/`; **se mantiene la ruta real** para no romper el panel y las nuevas siguen el mismo estilo (barra final): `proformas/<pk>/anular/`, `notas-trabajo/<pk>/terminar/`, `notas-trabajo/<pk>/corregir/`, `notas-trabajo/<pk>/anular/` (reemplaza a `reabrir`), `notas-venta`, `notas-venta/<pk>/`, `notas-venta/<pk>/pago/`, `notas-venta/<pk>/anular-pago/`, `notas-venta/<pk>/anular/`.
- **Datos existentes:** migración `0111` aditiva con backfill y `reverse_code` real; las NT con `proforma` NULL se omiten con log. Backup + ensayo de `migrate`/reverso sobre copia con datos reales antes de producción.
- **Dinero:** totales y `monto` en `Decimal`; el monto del pago lo fija el servidor (`Nota_Venta.total_price`), jamás del cliente.
- **Concurrencia:** cada transición hace `select_for_update` de la proforma dentro de `transaction.atomic`; doble pago protegido además por el `OneToOne` `pago.nota_venta`.
- **Seguridad/permisos:** permisos Django estándar verificados en servidor + alcance por sucursal (404 fuera de alcance), según `ADR-…-alcance-permisos`. Las anulaciones usan los permisos estándar `delete_*` (sin permisos custom ni migración de permisos; ver ADR de API, Actualización 1). Asignación a grupos con un comando idempotente (Fase 6). Matriz acordada:

| Acción | Endpoint | Permiso verificado en servidor | Grupos (asignación acordada) |
|---|---|---|---|
| Aprobar proforma | `POST proformas/<pk>/generar-nota-trabajo/` | `add_nota_trabajo` | Vendedor, Admin |
| Anular proforma (vigente) | `POST proformas/<pk>/anular/` | `delete_proforma_header` | Vendedor, Admin |
| Terminar / corregir trabajo | `POST notas-trabajo/<pk>/terminar/` · `corregir/` | `change_nota_trabajo` | Admin, Almacen |
| Anular nota de trabajo | `POST notas-trabajo/<pk>/anular/` | `delete_nota_trabajo` | Almacen, Admin |
| Anular nota de venta | `POST notas-venta/<pk>/anular/` | `delete_nota_venta` | Caja, Vendedor, Admin |
| Registrar / anular pago | `POST notas-venta/<pk>/pago/` · `anular-pago/` | `add_pago` · `delete_pago` | Admin, Caja, Vendedor |
| Editar proforma / nota de trabajo | (existentes) | `change_proforma_header` · `change_nota_trabajo` | Proforma: Admin, Almacen, Vendedor · Nota de trabajo: Admin, Almacen |
 Nota: `Caja` y `Vendedor` no son `admin`, así que ven solo su(s) sucursal(es) (`User_Helper.can_view_all_sucursales`, ADR-002).
- **Rendimiento:** listados con `select_related` (NT→proforma→sucursal, NV→NT→proforma) para evitar N+1; sin paginación server-side (deuda aceptada).
- **Acoplamiento:** los `ModelAdmin` y los reportes dejan de calcular estado por su cuenta y llaman al servicio; es la parte con más riesgo de efectos colaterales (ver Risks).
- **Consistencia visual:** el DDR ya fijó componentes; el plan solo los traduce.

## Proposed solution
Implementar el ADR de máquina de estados y el de API/permisos tal cual, en fases que dejan el repo verde en cada paso:
1. Constantes/tabla de transiciones + campos + migración.
2. Servicio `Orden_Estado_Business` (`business/orden_estado.py`) con `calcular_estado_orden` y las 8 transiciones; los métodos legados pasan a delegar o se eliminan.
3. Re-cableado de Django Admin.
4. API + serializers + alcance de notas de venta.
5. Frontend según DDR.
6. Datos de permisos por grupo + verificación en vivo + documentación.

Alternativa descartada por arquitectura (ver ADR): `django-fsm`, un solo enum lineal, auditoría de eventos, borrar `is_close` ahora.

## Files/components affected

**Backend (`praxsa_manager/product/`)**
- `helper/estados.py` (**nuevo**): constantes de estado de NT/NV, tabla de transiciones permitidas; `helper/proforma.py` (choices de `Proforma_Header.status`).
- `models.py`: `Nota_trabajo.status`, `Nota_Venta.status`, choices de `Proforma_Header.status`.
- `migrations/0111_…py` (**nueva**): campos + backfill + reverso.
- `business/orden_estado.py` (**nuevo**): servicio y `calcular_estado_orden`.
- `business/proforma.py`, `business/pago.py`, `business/orden_trabajo.py`: delegar en el servicio; borrar `delete_proforma`, `create_nota_venta_pago`, `crear_nota_venta`; `delete_work_note` bloquea por `pago`, no por nota de venta; `get_finish_nota_queryset` filtra por `status`; nuevo `get_panel_nota_venta_queryset` (en `Pago_Business` o `Proforma_Business`, donde encaje con el patrón).
- `admin_config/{proforma_admin,nota_trabajo,nota_venta,pagos,report_nota_trabajo,reporte_proforma}.py`: acciones y `get_estado` sobre el servicio/`status`; retirar "crear nota venta"; agregar "Marcar trabajo terminado".
- `custom_views/ordenes_admin.py`, `urls.py`, `serializer/ordenes_serializer.py`: endpoints, serializers de nota de venta/pago, cambios de contrato, guards por `status`.
- `utils/exception/proforma.py`: excepción de transición inválida (si no se reutiliza `ProformaException`/`NotaVentaException`).
- Tests: `tests/test_proforma_status_field.py` (**reemplazado**), `tests/test_ordenes_proformas.py`, `tests/test_ordenes_notas_trabajo.py`, `tests/helpers.py` / `ordenes_helpers.py` (fábricas), y nuevos `test_orden_estado_service.py`, `test_orden_estado_migration.py`, `test_ordenes_notas_venta_pagos.py`.

**Frontend (`panel_admin/src/app/`)**
- `ordenes/ordenes.model.ts`, `ordenes.service.ts` (+ `.spec`): tipos y llamadas nuevas.
- `ordenes/proformas/*` (list, view, form specs): badge/filtro de estado, "Aprobar y generar orden" (`add_nota_trabajo`) y "Anular" (`delete_proforma_header`); sin "Reabrir".
- `ordenes/notas-trabajo/*`: columnas Estado/Cobro, "Marcar trabajo terminado", "Corregir", "Anular nota de trabajo", bloque Cobro; `canEdit` por `status`.
- `ordenes/notas-venta/*` (**nuevo**): list, view, modal de pago (+ specs); `ordenes.routes.ts`; `assets/data/routes.json` (submenú Nota de Venta); `assets/scss/_ordenes.scss` (clase `status-void`).

**Datos / docs**
- `management/__init__.py`, `management/commands/__init__.py`, `management/commands/asignar_permisos_estados.py` (**nuevos**) y su test `tests/test_asignar_permisos_estados.py`; `docs/integration-and-backlog.md`.

## Implementation steps

**Fase 0 — Línea base**
1. Correr la suite backend (`python manage.py test`) y `ng test`/`ng build` de `panel_admin/` para registrar el estado inicial; verificar `makemigrations --check` limpio.

**Fase 1 — Modelo y migración**
2. `helper/estados.py`: estados de NT/NV, choices, tabla `TRANSICIONES` (documento, de, a) y nuevos valores de proforma (`en_trabajo`, `anulada`). Test unitario de la tabla.
3. `models.py`: agregar `status` a `Nota_trabajo` y `Nota_Venta` (defaults `en_proceso` / `por_cobrar`); actualizar choices de `Proforma_Header.status`.
4. `makemigrations` → `0111_…`: esquema + `RunPython(backfill, reverse)` con la lógica del ADR (funciones de módulo importables para poder testearlas). Backfill: NV con `pago`→`pagada`, resto `por_cobrar`; NT con NV→`terminado`, sin NV→`en_proceso` **y crear NV `por_cobrar`** (total `total_price − discount`, `created_by`=`responsable` o `proforma.created_by`, `created_on`=ahora); NT sin proforma → omitir y loguear; recalcular `Proforma_Header.status`. Reverso: borrar NV sin `pago` cuya NT esté `en_proceso`, restaurar `nota_trabajo` en `status` de proforma.

**Fase 2 — Servicio de transiciones**
5. `business/orden_estado.py`: `calcular_estado_orden(proforma)` (pura) y `Orden_Estado_Business` con `aprobar_proforma`, `terminar_trabajo`, `corregir_trabajo`, `registrar_pago`, `anular_pago`, `anular_nota_trabajo` y `anular_nota_venta` (ambas delegan en una misma cancelación interna de la orden), `anular_proforma`, `cerrar_pago`. Cada una: `atomic` + `select_for_update` + validación contra `TRANSICIONES` + escritura de `is_close` legado + recálculo de `Proforma_Header.status` (con `update_fields`, para no tocar `proforma_created_on`, `auto_now`).
6. `aprobar_proforma` reutiliza la lógica actual de descuento de inventario/`validate_proforma_detail` (mover, no reescribir) y hace update-or-create de NT y NV refrescando el snapshot.
7. `business/proforma.py`/`pago.py`/`orden_trabajo.py`: `create_work_note`, `abrir_proforma`, `cerrar_pago`, `refresh_status` delegan; eliminar `crear_nota_venta`, `delete_proforma`, `create_nota_venta_pago`; ajustar `delete_work_note` (bloquea si hay `pago`; si no, borra NV y NT y devuelve inventario) y `get_finish_nota_queryset`.

**Fase 3 — Django Admin**
8. Re-cablear acciones: "crear/actualizar nota trabajo"→aprobar; "abrir proforma"→anular nota de trabajo; retirar "crear nota venta" de `NotaTrabajoAdmin` y `report_nota_trabajo.py:139`; agregar "Marcar trabajo terminado"; "Gestionar Pago"/alta de `pago` → `registrar_pago`; "concluir transaccion" → `cerrar_pago` (solo contable). `get_estado` de los admins lee `status`.

**Fase 4 — API**
9. Serializers: NT (`status`, `status_label`, `nota_venta` resumen; quitar `is_finalizada`), `NotaVentaListSerializer`/`DetailSerializer` (con `pago`), `PagoCreateSerializer` (`tipo_pago`, `registro_contable`; sin `monto`).
10. Vistas y rutas de acción y de lectura (lista en "Architecture considerations"); permisos según la matriz: aprobar → `add_nota_trabajo`; anular proforma → `delete_proforma_header`; terminar/corregir → `change_nota_trabajo`; anular nota de trabajo → `delete_nota_trabajo`; anular nota de venta → `delete_nota_venta`; pago → `add_pago`; anular-pago → `delete_pago`. Errores de transición → 409; fuera de alcance → 404; guards de `PATCH` por `status`. Eliminar la ruta `reabrir`.
11. Método de alcance `get_panel_nota_venta_queryset` (con `select_related`), filtros `?status=` y `?search=`.

**Fase 5 — Frontend (según DDR)**
12. Modelos y servicio (`ordenes.model.ts`, `ordenes.service.ts`): nuevos estados, `NotaVenta`, `Pago`, métodos de acción.
13. Proformas: badge de estado global en listado (+ filtro `?status=`) y vista; renombrar botón; "Anular" (solo proforma vigente) según estado y permiso.
14. Notas de trabajo: columnas Estado/Cobro, "Marcar trabajo terminado" (deshabilitado con tooltip si falta garantía/instalador), "Corregir", bloque Cobro; reemplazar `is_finalizada`.
15. Notas de venta: `notas-venta` list/view, botón "Anular nota de venta" (deshabilitado con tooltip si el trabajo está terminado), modal de pago (`NgbModal` + SweetAlert2), ruta y submenú; clase `status-void`.
16. Actualizar specs existentes afectados y crear los nuevos.

**Fase 6 — Datos, verificación en vivo, documentación**
17. **Comando `asignar_permisos_estados`** (`python manage.py asignar_permisos_estados [--dry-run]`): mapa `grupo → [permisos]` como constante (Admin, Caja, Vendedor, Almacen según la matriz); resuelve cada permiso por `codename` + `content_type` de `product`; agrega a cada grupo **solo lo que falta** (no quita permisos, no crea grupos ni permisos inexistentes); es idempotente (segunda corrida = sin cambios); si un grupo no existe, falla con mensaje que lista los grupos existentes (para detectar `Almacen`/`Almacén`) y sin aplicar cambios parciales; imprime un resumen (agregados / ya presentes / faltantes). Se ejecuta en cada ambiente después de `migrate`; el paso se documenta en `docs/integration-and-backlog.md`.
18. Verificación en vivo (`runserver` + `ng serve`) con usuarios de distintos grupos/sucursales: flujo completo aprobar → terminar → pagar, retrocesos, sin permiso, otra sucursal, y Django Admin (acciones re-cableadas, reportes).
19. Ensayo de `migrate` y del reverso (`migrate product 0110`) sobre una copia de datos reales; contar filas omitidas en el backfill.
20. Actualizar `docs/integration-and-backlog.md` (ítem de estados/BIZ-04) y el ADR-006 ya marcado como parcialmente reemplazado.

## Test strategy

**Backend – unit**
- `calcular_estado_orden`: todas las combinaciones NT×NV×anulación → estado global esperado.
- Tabla `TRANSICIONES`: cada par válido pasa; cada par inválido lanza excepción (parametrizado).
- Servicio, por transición: éxito con todos sus efectos (inventario, snapshot de total, `is_close` legado, `salida_vehiculo`); precondición fallida (sin garantía/instalador, pagar con NT `en_proceso`, reabrir con NT `terminado`/NV `pagada`, anular pago con `cerrado=True`, aprobar dos veces); reaprobar tras reabrir reutiliza NT/NV y refresca el total tras editar la proforma; `proforma_created_on` no cambia por transiciones de estado.
- `delete_work_note`: bloquea con `pago`; borra NV y NT sin pago.
- Migración (importando las funciones del archivo): backfill de cada combinación (NT sin NV, NT con NV sin pago, con pago, NT sin proforma) y `reverse_code`; sobre datos creados con `tests/helpers.py`.

**Backend – integración (API)**
- Cadena feliz por API: crear proforma → `generar-nota-trabajo` → `terminar` → `pago` → `status=finalizado`.
- Por endpoint nuevo: sin permiso → 403; usuario de otra sucursal → 404; sin sucursal → lista vacía; transición inválida → 409; `monto` enviado por el cliente se ignora; doble `POST pago` → un solo pago.
- Permisos por grupo del negocio (matriz completa): usuarios de prueba en `Admin`, `Caja`, `Vendedor`, `Almacen` con los permisos que asigna el comando; cada endpoint responde 200/409 para el grupo autorizado y 403 para el no autorizado (p. ej. Almacen no aprueba ni cobra; Caja no termina ni anula la nota de trabajo; Vendedor no termina el trabajo).
- Anulaciones: anular NT y anular NV producen el mismo resultado (NT `cancelada`, NV `anulada`, inventario devuelto, proforma `proforma`); con NT `terminado` o NV `pagada` → 409; reaprobar tras anular reutiliza NT/NV y refresca el total.
- Comando `asignar_permisos_estados`: deja los permisos esperados en cada grupo; segunda corrida no cambia nada; `--dry-run` no escribe; grupo inexistente → error sin cambios parciales; no quita permisos ya existentes.
- Contrato: NT ya no expone `is_finalizada`; `?status=` acepta los valores nuevos; los PATCH quedan bloqueados según `status`.
- Regresión de Django Admin (con `Client`): acciones re-cableadas y `get_estado` coinciden con `status`; `PagosAdmin.concluir_transaccion` solo cierra el pago.

**Frontend – unit/integración**
- `ordenes.service.spec.ts` con `HttpTestingController` para cada endpoint nuevo.
- Specs de componentes: badge/filtro de estado; botones visibles/ocultos/deshabilitados por estado y permiso (matriz del DDR); modal de pago (validación, error de servidor, monto de solo lectura); listado/vista de notas de venta.
- Actualizar `notas-trabajo.components.spec.ts`, `proformas-list.component.spec.ts`, `proforma-view.component.spec.ts`, `proforma-form.component.spec.ts`.

**E2E (Playwright): NO corresponde en este task.** Motivo: Playwright no está instalado y agregarlo es una dependencia nueva que requiere confirmación; el flujo de punta a punta (aprobar → terminar → pagar) queda cubierto por el test de integración de API de la cadena completa, los specs de componentes con `HttpTestingController` y la verificación manual en vivo del paso 18. Si el usuario quiere E2E, se plantea como task aparte.

## Acceptance criteria
1. `Nota_trabajo.status` y `Nota_Venta.status` existen y son la fuente de verdad; `Proforma_Header.status` es el estado global calculado por una única función y nunca se asigna a mano fuera del servicio.
2. Aprobar una proforma crea (o reutiliza) la nota de trabajo `en_proceso` y la nota de venta `por_cobrar` con total = `total_price − discount`, y descuenta inventario.
3. No se puede registrar el pago con la nota de trabajo en `en_proceso`; el `monto` siempre lo fija el servidor; no hay doble pago.
4. Terminar el trabajo exige garantía e instalador en venta con instalación y fija `salida_vehiculo`.
5. Anular proforma/nota de trabajo/nota de venta, corregir trabajo y anular pago respetan la tabla de transiciones; transiciones inválidas responden 409; anular la nota de trabajo equivale a reabrir y anular la nota de venta solo procede con el trabajo `en_proceso`.
6. "Finalizado" solo aparece cuando el trabajo está terminado y pagado, en API, panel y Django Admin; `is_finalizada` ya no existe en la API.
7. Los permisos se aplican en servidor según la matriz (`add_pago`/`delete_pago`, `change_nota_trabajo`, `add_nota_trabajo`, `delete_proforma_header`, `delete_nota_trabajo`, `delete_nota_venta`); alcance por sucursal (404 fuera de alcance).
8. Tras correr `asignar_permisos_estados`, un usuario de cada grupo (Admin, Caja, Vendedor, Almacen) ve y puede hacer exactamente lo que la matriz indica; el comando es idempotente.
9. Migración `0111`: `migrate` y `migrate product 0110` funcionan sobre datos con las cuatro combinaciones; `makemigrations --check` limpio; las notas sin proforma se omiten con log.
10. Django Admin y reportes siguen funcionando con las acciones re-cableadas; no queda código que use `hasattr(...,'nota_venta')` para decidir estado.
11. El panel implementa el DDR (badges, "Marcar trabajo terminado", Notas de Venta, modal de pago); suites backend y frontend en verde, `ng build` y `ng lint` limpios.

## Risks
- **Migración de producción crea notas de venta** para trabajos abiertos y recalcula estados: riesgo de datos inconsistentes. Mitigación: backup, ensayo sobre copia, reverso probado, log/recuento de filas omitidas. Rollback: `git revert` + `migrate product 0110` (siempre ambos).
- **Reescritura de la lógica de aprobación/reapertura (toca inventario):** riesgo de desalinear stock. Mitigación: mover la lógica existente en vez de reescribirla, tests con inventario y verificación en vivo.
- **Contrato de API interno cambia:** panel y backend deben salir juntos; sin panel viejo contra backend nuevo. Sin mitigación adicional (aceptado en ADR).
- **Django Admin y reportes tienen varias rutas que leen `is_close`/nota de venta** (`report_nota_trabajo.py`, `reporte_proforma.py`, `report_daily_sell.py`): riesgo de regresión silenciosa. Mitigación: tests de humo del admin y revisión explícita de cada uno en la Fase 3.
- **Sin constraint en base** que garantice la coherencia entre `Proforma_Header.status` y los estados hijos: se acepta como deuda (ADR).
- **Nombres de grupo en producción** podrían diferir de los declarados (`Almacen`/`Almacén`): el comando falla de forma explícita listando los grupos existentes, sin aplicar cambios parciales.
- **Anular es potente** (devuelve inventario y cancela cobro): mitigado con confirmación en UI, precondiciones en servidor (solo NT `en_proceso` y NV `por_cobrar`) y permisos separados.
- **Superficie de API grande sin paginación server-side** en los listados nuevos: aceptado como deuda.

## Out of scope
- Anticipos (cobrar antes de terminar el trabajo).
- `CheckConstraint` de secuencia, eliminación de las columnas `is_close`, tabla de auditoría de transiciones.
- Cierre contable (`cerrar_pago`) por API/panel; edición de la nota de venta por API.
- Playwright/E2E.
- Migración de datos para asignar permisos (se usa el comando, que se ejecuta a mano por ambiente).
- Reporte de cuentas por cobrar.
- **Preguntas abiertas:** (1) ~~¿Vendedor debe poder editar proformas?~~ Resuelto por el usuario (v2.1): sí, Vendedor recibe `change_proforma_header`. (2) Confirmar la ortografía del grupo `Almacen`/`Almacén` (el comando falla explícitamente si no lo encuentra).

## Changelog
- **v2** (2026-09-30): (a) se agrega el comando idempotente `asignar_permisos_estados` para asignar permisos por grupo; (b) permisos por acción definidos por negocio: Vendedor/Admin aprueban y anulan proformas, Almacen/Admin anulan la nota de trabajo, Caja/Vendedor/Admin anulan la nota de venta; (c) `reabrir` se reemplaza por `anular` nota de trabajo/venta (mismo efecto, solo con NT `en_proceso`); anulaciones con permisos estándar `delete_*`. Solicitado por el usuario directamente al planificador (no por delivery-engineer/review). Actualizados en el mismo PR: ADR de API y de máquina de estados (Actualización 1) y DDR (Actualización 1).
- **v2.1** (2026-09-30): Vendedor también puede editar proformas (`change_proforma_header`), indicado por el usuario al iniciar la implementación; solo cambia la asignación del comando `asignar_permisos_estados` y la matriz.
- **v1** (2026-09-30): plan inicial.
