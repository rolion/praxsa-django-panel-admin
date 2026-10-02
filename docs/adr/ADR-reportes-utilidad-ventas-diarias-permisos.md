# ADR-reportes-utilidad-ventas-diarias-permisos: Permisos de los reportes de ventas y utilidad (servidor, Django Admin y panel)

**Estado:** Propuesto -- reemplazado parcialmente (alcance de admin y sucursales inactivas) por ADR-inventario-alcance-sucursal-django-admin-alcance-lectura-escritura
**Task relacionado:** TASK-reportes-utilidad-ventas-diarias
**Fecha:** 2026-09-30

## Contexto

Los reportes se exponen ahora en dos superficies (Django Admin y API del panel; ver `ADR-reportes-utilidad-ventas-diarias-calculo-y-api`) y **Utilidad muestra costos de compra y márgenes**, mucho más sensibles que las ventas diarias. El DDR de la tarea pide ocultar el submenú a quien no tenga acceso, pero deja explícito que eso es solo UX y que la barrera real debe definirse en el servidor.

El usuario definió (2026-09-30): **Ventas Diarias: Admin y Caja; Utilidad: solo Admin.**

Hechos relevantes:
- El patrón vigente del proyecto son **permisos Django estándar sin permisos custom ni migración**, asignados a grupos con un comando idempotente (`management/commands/asignar_permisos_estados.py`, y `ADR-modulo-ordenes-proforma-nota-trabajo-alcance-permisos`, decisión 3). `DjangoModelPermissions` **no exige permiso a los `GET`**, por lo que un endpoint de lectura necesita verificación explícita (`ADR-estados-...-api-y-permisos`, decisión 1).
- Los dos reportes son modelos proxy (`utilidades`, `Proxy_Pagos`, `models.py:161-164,323-327`); Django crea para cada modelo, proxies incluidos, los permisos por defecto `add/change/delete/view`. Los `ModelAdmin` de solo lectura ya dependen de ese permiso `view`.
- El login del panel devuelve los permisos efectivos del usuario (`permissions`) y `AuthService.hasPermission(codename)` los consume (`panel_admin/src/app/core/service/auth.service.ts:81`); el menú lateral **no filtra ítems por permiso hoy** (sin uso de `hasPermission`/`hasGroup` en `app/layout/`).
- El alcance por sucursal ya está resuelto para el panel (`User_Helper.can_view_all_sucursales` / `get_enabled_sucursal_ids`, `helper/user.py`); Admin ve todo, el resto solo sus sucursales habilitadas.
- Hipótesis a verificar en el plan (no comprobado leyendo el código): que los codenames de los proxies sean `view_proxy_pagos` y `view_utilidades` en la base real y que aparezcan como `product.view_proxy_pagos` / `product.view_utilidades` en `permissions` del login.

## Decisión

1. **Un permiso `view` por reporte, el mismo para ambas superficies:**

   | Reporte | Permiso Django | Grupos (definido por el usuario) |
   |---|---|---|
   | Ventas Diarias | `product.view_proxy_pagos` | Admin, Caja |
   | Utilidad | `product.view_utilidades` | Admin |

   Sin permisos custom ni migraciones. El mismo permiso gobierna el `ModelAdmin` (`has_view_permission` por defecto) y el endpoint de la API, de modo que quitarlo a un grupo lo cierra en ambos lados.

2. **API:** cada vista verifica `IsAuthenticated`, `IsStaffUser` y además un chequeo explícito `request.user.has_perm(<permiso del reporte>)`; sin permiso → **403**. Un superusuario pasa por la regla estándar de Django.

3. **Separación de datos sensibles por diseño de respuesta:** el endpoint de Ventas Diarias **no incluye** ningún campo de costo, utilidad ni margen. Aunque Caja pudiera ver más filas de las esperadas, nunca recibe costos. Es la barrera que protege el requisito "Caja no ve costos ni márgenes".

4. **Alcance por sucursal:** el del panel (Admin todas; resto sus sucursales habilitadas; sin sucursal → respuesta vacía con indicador; sucursal ajena en el filtro → 404), aplicado siempre en servidor. Estos permisos deciden **quién ve el reporte**; el alcance decide **de qué sucursales**.

5. **Asignación a grupos:** un comando idempotente nuevo, `asignar_permisos_reportes` (mismo patrón que `asignar_permisos_estados`: `--dry-run`, no quita permisos, no crea grupos, falla si un grupo o permiso no existe), agrega `view_proxy_pagos` a Admin y Caja y `view_utilidades` a Admin. Los nombres de grupo se resuelven sin distinguir mayúsculas.

6. **Django Admin de solo lectura efectiva:** los dos `ModelAdmin` devuelven `False` en `has_add_permission`, `has_change_permission` y `has_delete_permission` (este último hoy sin definir), de modo que no se puede borrar un pago ni un lote de inventario desde un reporte, ni siquiera por URL directa.

7. **Frontend (solo UX):** el DDR pide ocultar el submenú "Utilidad" a quien no tenga `view_utilidades` y mostrar un aviso en la pantalla si se entra por URL; requiere que el sidebar pueda filtrar por permiso, cosa que hoy no hace. Ese cambio es del plan; **la seguridad no depende de él**.

## Alternativas consideradas

- **Permisos custom (`ver_reporte_ventas`, `ver_reporte_utilidad`)**: nombres más claros, pero exigen migración y se apartan del patrón del proyecto; los `view_*` de los proxies ya existen y ya gobiernan el Django Admin. Se descarta.
- **Decidir por nombre de grupo en el servidor (`is_request_user_caja`)**: simple, pero hardcodea roles y rompe el módulo Grupos, que configura permisos (`ADR-modulo-ordenes-proforma-nota-trabajo-alcance-permisos`, alternativa 3). Se descarta.
- **Un único permiso para ambos reportes**: más simple, pero no permite dar Ventas Diarias a Caja sin darle Utilidad, que es el requisito del usuario.
- **Un endpoint único con campos de costo condicionados al permiso**: ahorra una ruta, pero mezcla en una respuesta datos de sensibilidad distinta y facilita una fuga por error de serializer. Se descarta a favor de dos serializers separados.
- **Dejar el Django Admin sin cerrar `has_delete_permission`**: menos cambios, pero deja abierta la brecha de borrado desde un reporte que debe ser de solo lectura. Se descarta.

## Estrategia de rollback / mitigación

Cambio de autorización, aditivo y sin migraciones (los permisos ya existen; se asignan como datos).
- Riesgos: **sobre-permisividad** (alguien ve Utilidad sin corresponderle, o Caja recibe costos) y **sub-permisividad** (usuarios legítimos con 403 por olvidar ejecutar el comando de asignación).
- Mitigación: tests de API por escenario: Admin accede a ambos; Caja accede solo a Ventas Diarias (403 en Utilidad); Vendedor sin acceso a ninguno (403); no-staff → 403; sin sucursal → vacío; sucursal ajena → 404; Ventas Diarias sin campos de costo en el JSON. Prueba del Django Admin: sin `add/change/delete` para ningún usuario. Verificación manual en vivo con usuarios reales de los grupos Admin y Caja de dos sucursales (práctica del proyecto para cambios de autorización). El comando debe ejecutarse en cada ambiente; el plan debe incluirlo como paso explícito con `--dry-run` previo.
- Reversión: `git revert` del PR; los permisos asignados a los grupos quedan como datos inocuos sin los endpoints y no cambian lo que esos grupos ya podían hacer en el resto del sistema. Si el filtro del menú del panel causara problemas, la pantalla sigue protegida por el 403 del servidor.

## Consecuencias

**Más fácil:** quitar o dar acceso a un reporte se hace desde el módulo Grupos, con el mismo permiso en Django Admin y en el panel; Caja puede cuadrar cobros sin ver costos; el panel decide su UI a partir de `permissions` sin hardcodear roles.

**Más difícil / deuda aceptada:**
- Asignar los permisos es un paso operativo por ambiente; olvidarlo se manifiesta como 403.
- Los nombres `view_proxy_pagos` / `view_utilidades` no son evidentes para quien administre grupos; se documenta en el comando.
- El sidebar debe ganar filtrado por permiso solo para este grupo, dejando el resto del menú inconsistente hasta que se generalice (deuda visual ya anotada en el DDR).
- Dar acceso a Vendedor o a otros grupos en el futuro es solo asignación de datos, pero no está en este alcance.
- Un usuario Admin cuyo grupo no se llame exactamente `Admin`/`admin` no recibirá los permisos por el comando y tampoco verá todas las sucursales (`User_Helper` compara en minúsculas): el plan debe verificar los grupos reales.
