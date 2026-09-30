# ADR-estados-proforma-nota-trabajo-nota-venta-api-y-permisos: Endpoints de transición, listados de nota de venta y permisos por acción

**Estado:** Propuesto
**Task relacionado:** TASK-estados-proforma-nota-trabajo-nota-venta
**Fecha:** 2026-09-30

## Contexto

El DDR del task exige que el panel pueda aprobar, terminar el trabajo, listar/ver notas de venta y registrar o anular pagos. Hoy la API de Órdenes (`custom_views/ordenes_admin.py`) solo expone proformas y notas de trabajo, y solo la transición "generar nota" (`ProformaGenerateNotaView`, `:121-150`); nota de venta y pago no tienen endpoints. Este ADR extiende el patrón de `ADR-modulo-ordenes-proforma-nota-trabajo-alcance-permisos` (alcance por sucursal, 404 fuera de alcance, permisos Django estándar sin permisos custom, reglas de estado siempre en servidor) y usa el servicio de transiciones definido en `ADR-estados-proforma-nota-trabajo-nota-venta-maquina-de-estados`.

## Decisión

1. **Endpoints de acción (POST, sin cuerpo salvo indicación), bajo el prefijo existente de Órdenes**, con el mismo estilo que `generate-nota`/`toggle-active`. Cada uno llama a un método del servicio, devuelve el recurso actualizado y traduce transiciones inválidas a **409** con el mensaje de negocio:

   | Endpoint | Transición | Permiso Django verificado en servidor |
   |---|---|---|
   | `POST proformas/<pk>/generate-nota` (existente, semántica ahora "aprobar") | `aprobar_proforma` | `product.add_nota_trabajo` (sin cambio) |
   | `POST proformas/<pk>/reabrir` | `reabrir_proforma` | `product.change_proforma_header` |
   | `POST proformas/<pk>/anular` | `anular_proforma` | `product.change_proforma_header` |
   | `POST notas-trabajo/<pk>/terminar` | `terminar_trabajo` | `product.change_nota_trabajo` |
   | `POST notas-trabajo/<pk>/corregir` | `corregir_trabajo` | `product.change_nota_trabajo` |
   | `POST notas-venta/<pk>/pago` (cuerpo: `tipo_pago`, `registro_contable` opcional) | `registrar_pago` | `product.add_pago` |
   | `POST notas-venta/<pk>/anular-pago` | `anular_pago` | `product.delete_pago` |

   `monto` **no** se acepta en el cuerpo (lo fija el servidor). El cierre contable (`cerrar_pago`) queda solo en Django Admin en este task (no está en el DDR).

2. **Listado y detalle de notas de venta** (`GET notas-venta`, `GET notas-venta/<pk>`): `IsStaffUser` + alcance por sucursal a través de `nota_trabajo__proforma__sucursal`, con un método nuevo `get_panel_nota_venta_queryset` que reutiliza `User_Helper.can_view_all_sucursales` / `get_enabled_sucursal_ids` (no se reutiliza `get_nota_venta_queryset_by_role`, que usa `sucursales[0]` y devuelve `None`, `business/proforma.py:271-284`). Fuera de alcance → 404; sin sucursal → lista vacía con el indicador que ya usan proformas y notas. Filtros `?status=` y `?search=` (nº de proforma, cliente, CI/NIT). El detalle incluye el `pago` (monto, tipo, registro contable, fecha, `cerrado`). Solo lectura: no hay edición de la nota de venta por API.

3. **Cambios de contrato en recursos existentes:** `Nota_trabajo` (lista y detalle) agrega `status`, `status_label` y un resumen `nota_venta`; se elimina `is_finalizada`. `Proforma` mantiene `status`/`status_label` con los nuevos valores (`en_trabajo`, `anulada`) y sigue aceptando `?status=`. El bloqueo de `PATCH` de la nota de trabajo pasa de `is_close or hasattr(nota_venta)` a `status != en_proceso`; el de la proforma de `is_close` a `status != proforma`.

4. **Permisos efectivos al frontend:** sin cambios de mecanismo (`permissions` en el login, `AuthService.hasPermission`); el DDR exige que la UI oculte según esos permisos, y esta lista cubre los codenames nuevos (`add_pago`, `delete_pago`, `change_proforma_header`, `change_nota_trabajo`). **Asignarlos a los grupos reales es configuración de datos** y debe estar en el plan, como en el ADR de alcance.

5. **Reglas de estado y precondiciones siempre en servidor** (nunca solo en la UI): pagar antes de terminar, editar una nota en `terminado`/`cancelada`, reabrir con trabajo terminado o con pago, anular un pago con cuenta cerrada, y monto distinto del total se rechazan aunque se llame al endpoint directamente.

## Alternativas consideradas

- **Un único endpoint `PATCH status` genérico** con el estado destino en el cuerpo. Más corto, pero traslada al cliente la elección de la transición y esconde los permisos distintos de cada una; además cada acción tiene precondiciones y datos propios (tipo de pago). Se descarta a favor de acciones explícitas, consistentes con `generate-nota`.
- **Permisos custom (`terminar_trabajo`, `registrar_pago`).** Requerirían migración y decisión de negocio sobre roles que no existe; los permisos estándar sobre `nota_trabajo`, `pago` y `proforma_header` describen bien cada acción (mismo razonamiento del ADR de alcance).
- **CRUD completo de `Nota_Venta` y `pago` por API.** Se descarta por alcance: el DDR solo pide consulta y "Registrar pago"; editar el total o el pago manualmente rompería el snapshot.
- **Mantener `is_finalizada` como alias por compatibilidad.** Se descarta: mantendría viva la ambigüedad de "finalizado" y el único consumidor (`panel_admin`) se actualiza en el mismo release.
- **Aceptar `monto` del cliente y validarlo contra el total.** Se descarta: el servidor puede fijarlo, y un campo menos elimina una clase de errores/abuso con dinero.

## Estrategia de rollback / mitigación

Cambios de autorización y de contrato de API, sin migraciones propias (la migración de datos está en el otro ADR).
- Los endpoints nuevos son **aditivos**; el riesgo real es sobre-/sub-permisividad y transiciones inválidas. Mitigación: tests de API por escenario (permiso faltante → 403; fuera de alcance → 404; sin sucursal → vacío; transición inválida → 409; pago con monto manipulado ignorado; doble `POST` concurrente de `pago` → un solo pago) y verificación manual en vivo con usuarios de distintos grupos/sucursales.
- Reversión: `git revert` del PR junto con la reversión de migración descrita en el ADR de máquina de estados. Los permisos asignados a grupos son datos inocuos sin los endpoints.
- El cambio de contrato (`status`, `is_finalizada`) se despliega junto con `panel_admin`; no hay clientes externos conocidos (hipótesis: `proforma/` no consume estos campos — no se encontraron referencias a `status_label`/`is_finalizada` fuera de `panel_admin/`).

## Consecuencias

**Más fácil:** cada acción tiene su permiso, su precondición y su error, y la UI del DDR se cablea directamente; el panel deja de depender de Django Admin para cobrar.

**Más difícil / deuda aceptada:** crece la superficie de API (7 endpoints de acción + 2 de lectura) sin paginación server-side; queda sin API el cierre contable y la edición de nota de venta; requiere asignar 4 permisos a los grupos reales, decisión de negocio pendiente (qué rol puede cobrar, anular y reabrir).
