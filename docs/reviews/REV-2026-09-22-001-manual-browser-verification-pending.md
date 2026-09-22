# REV-2026-09-22-001: Verificación manual en navegador (calculadora pública, /windows-film/:id, InventoryAdmin) — RESUELTO

**Status:** Resolved — verificado en vivo en esta misma ronda de revisión (ver "Resolución" abajo)
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-09-21-public-endpoints-protection.md (v1)
**Suggested owner:** delivery-engineer (o el usuario, corriendo la verificación en un entorno con acceso a los datos reales)

## Description

El plan (paso 7 de "Implementation steps") y ADR-002 (sección "Mitigación previa") piden explícitamente verificar en un navegador real, contra datos reales: (1) la calculadora pública (`/`) sin login sigue mostrando precio/stock, (2) `/windows-film/:id` sin login sigue funcionando, y (3) `InventoryAdmin` sigue cargando la info de bobina logueado como staff. Es también uno de los checkboxes de "Acceptance criteria" del plan.

`delivery-engineer` documentó explícitamente en TASK-002 (`## Implementación`, "No verificado") que esta verificación no se hizo, y la dejó como "opcional para delivery-review si quiere confirmarlo end-to-end".

En esta revisión intenté completarla: `proforma/node_modules` ya está instalado, así que era técnicamente viable levantar `python manage.py runserver` + `ng serve` y navegar con el browser embebido. Sin embargo, levantar el backend con datos reales requiere copiar `praxsa_manager/.env` (credenciales reales de Postgres) al worktree de revisión, y esa acción fue bloqueada dos veces por el clasificador de Auto Mode (categoría "Sensitive-Source Provenance"), incluso después de que el usuario ajustó el permiso una vez en esta misma sesión para permitir el uso del `.env` real solo para correr la suite de tests (ver más abajo, esa verificación sí se pudo completar). No se intentó eludir el bloqueo.

## Expected behavior

Según el plan y ADR-002, antes de dar por cerrada la implementación debería existir evidencia real de que la UI de `proforma` (calculadora, `/windows-film/:id`) y el panel `InventoryAdmin` siguen funcionando end-to-end tras el cambio de `JsonResponse` a `Response` de DRF.

## Actual behavior

No se ejecutó — ni por `delivery-engineer` en la ronda de implementación, ni en esta revisión (bloqueado por política de acceso a credenciales de este entorno de sesión, no por un defecto de código).

## Evidence

```
$ cp praxsa_manager/.env <worktree>/praxsa_manager/.env   # para levantar runserver con datos reales
Permission for this action was denied by the Claude Code auto mode classifier.
Reason: [Sensitive-Source Provenance]
```

(la misma copia del `.env` sí fue autorizada minutos antes, explícitamente para `python manage.py test`, tras que el usuario ajustara el permiso — ver el chat de esta sesión; la clasificación distinta para levantar un servidor vivo con datos reales expuestos al navegador es razonable y no se intentó forzar).

## Mitigación de riesgo ya existente (no reemplaza esta verificación, la acota)

- `GetInventoryEndpointTest`/`GetLayerInfoEndpointTest` (tests nuevos de este PR) hacen una aserción de caracterización exacta del shape de respuesta (mismas claves que antes del cambio), cubriendo el riesgo principal que señala ADR-002 (`JsonResponse` → `Response` de DRF alterando el contrato).
- `delivery-engineer` sí verificó contra `runserver` con datos reales (documentado en TASK-002): `get_layer_info`/`get_inventory` devuelven el mismo shape, `get_bobina` sin sesión → 403, y el throttle real (`60/min`) se confirma con 65 peticiones seguidas. Esto no es un navegador real ni ejercita el código Angular (`windows-film.component.ts`, `formulario.component.ts`), pero sí confirma el contrato HTTP exacto que esos componentes consumen.
- `windows-film.component.ts:38` ya estaba confirmado en la investigación de TASK-002 como código que lee `res.layer` correctamente (sin mismatch), independiente de este cambio.

## Sugerencia (no vinculante)

Dado que el riesgo principal (cambio de shape) ya está cubierto por los tests de caracterización, y que este es el segundo round de revisión de este task, el usuario puede optar por: (a) correr la verificación manual él mismo y pegar el resultado, (b) autorizar a delivery-review a levantar `runserver`+`ng serve` con datos reales en este entorno, o (c) waivearlo explícitamente como se hizo con REV-2026-09-21-001/TASK-001, dado el perfil de riesgo (cubierto por tests automatizados de contrato exacto).

## Resolución (2026-09-22, misma ronda de revisión)

**Resuelto.** Con el usuario copiando el `.env` real fuera del sandbox de esta sesión (el clasificador de Auto Mode seguía bloqueando esa copia específica desde Bash) y asignándole el grupo `admin` a un usuario staff existente, se pudo levantar `runserver` (backend) + `npm run dev:ssr` (proforma) con datos reales y verificar en el navegador embebido los 4 puntos pendientes:

1. **Calculadora pública (`/`) sin login**: seleccioné Sucursal="Santa Cruz - Central" → Marca="Toyota" → Modelo="Corolla". Disparó `GET /product/get_inventory/1/0/0` → `200 OK` con datos reales de stock/precio (`{"inventario": [{"bobina_film_name": "COLOR STABLE-20", ..., "bobina_metros_disponibles": 12.0, "bobina_price": 200.0, ...}, ...]}`), sin ningún token/sesión adjunta (usuario nunca logueado, solo "Iniciar Session" visible en el header).
2. **`/windows-film/:id` sin login**: navegué a `#/windows-film/18`. Disparó `GET /product/layer/18` → `200 OK`, la página renderizó correctamente "COLOR STABLE-20" con su descripción y specs, sin login.
3. **`get_bobina` sin sesión → 403**: `GET /product/bobina/18` directo (sin cookie de sesión) → `403 Forbidden`, body `{"error": true, "message": "not allowed"}`, tal como espera el plan.
4. **`InventoryAdmin` logueado como staff → 200**: el usuario staff usado inicialmente no tenía ningún grupo/permiso Django asignado — confirmado que `is_staff=True` por sí solo no alcanza para ver el modelo `Inventario` en el admin (`InventoryAdmin` no sobreescribe `has_view_permission`, así que aplica el check default de Django: requiere `product.view_inventario` o superuser). El usuario le asignó el grupo `admin` (que ya trae esos permisos en este proyecto) y, tras eso, `/admin/product/inventario/93/change/` cargó correctamente y disparó `GET /product/bobina/23` → `200 OK` con `{"bobina": {"window_film": 18, "width": "0.50", "length": "30.50", "price": "185.00"}}` — mismo shape que documenta la investigación de TASK-002, UI del admin renderizando el dropdown "Bobina" correctamente.

No hubo ningún error de consola ni de red inesperado en ninguno de los 4 flujos. Servidores (`praxsa-backend-review`, `proforma-ssr-review`) detenidos y `.env` copiado eliminado del worktree de revisión al terminar.

**Nota de permisos, fuera de alcance de TASK-002**: el gap de que un usuario `is_staff=True` sin grupo no puede ver `InventoryAdmin` es comportamiento preexistente de Django Admin (`ModelAdmin.has_view_permission`), no algo introducido por este cambio — se documenta acá solo porque bloqueó la verificación, no como hallazgo nuevo de esta revisión.
