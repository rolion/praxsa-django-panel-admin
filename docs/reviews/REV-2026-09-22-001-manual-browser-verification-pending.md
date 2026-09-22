# REV-2026-09-22-001: Verificación manual en navegador (calculadora pública, /windows-film/:id, InventoryAdmin) sigue sin ejecutarse

**Status:** Open
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
