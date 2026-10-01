# REV-2026-09-30-pricing-calculator-screen-01: El throttle del registro público se evade variando `X-Forwarded-For`

**Status:** Open
**Severity:** Medium
**Category:** ARCHITECTURE
**Related plan:** docs/plans/PLAN-2026-09-30-pricing-calculator-screen.md (v2)
**Suggested owner:** delivery-architect

## Description
`POST product/client/register` (público, `AllowAny`) se protege solo con `ClientRegisterThrottle` (`AnonRateThrottle`, scope `client_register`, `10/hour`; `praxsa_manager/product/custom_views/client_api.py:20-24`, `praxsa_manager/settings.py:125-130`). La implementación sigue el ADR/plan, pero la mitigación decidida es insuficiente en el despliegue real: `api_settings.NUM_PROXIES` no está configurado y nginx reenvía `X-Forwarded-For` con `$proxy_add_x_forwarded_for` (`nginx/default.conf:15`), que **conserva el valor que envió el cliente**.

Con `NUM_PROXIES = None`, DRF identifica al solicitante con **todo el valor** de `X-Forwarded-For` (`rest_framework/throttling.py:40`). Un atacante que cambie ese encabezado en cada petición obtiene un bucket nuevo cada vez y nunca recibe 429.

## Expected behavior
Plan, "Risks → Registro público": "abuso/spam de cuentas; mitigación: throttle y validación de contraseña". Criterio de aceptación 2: "… duplicados rechazados y **throttling**".

## Actual behavior
El throttle funciona en las pruebas (`override_settings`, misma IP) pero no limita a un cliente que falsifica `X-Forwarded-For`. Además no hay `CACHES` definido (cache local por proceso), por lo que el contador no se comparte entre workers. El mismo defecto afecta al `PublicCatalogThrottle` existente (ADR-005); este PR lo hereda y lo extiende a un endpoint que **crea cuentas**.

## Evidence
- `rest_framework/throttling.py:29-40` (DRF instalado en el venv del proyecto): sin `NUM_PROXIES`, `return ''.join(xff.split()) if xff else remote_addr`.
- `nginx/default.conf:15`: `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;`.
- `grep -rn NUM_PROXIES` sobre el repo: sin resultados; `grep CACHES praxsa_manager/settings.py`: sin resultados.
- No se reprodujo contra un despliegue real (solo lectura de código + fuente de DRF); no hay prueba que cubra el encabezado.

## Sugerencia (decisión del owner)
Definir `NUM_PROXIES` según la topología real (1 con nginx delante) y, si hay más de un worker, un cache compartido; agregar una prueba con `HTTP_X_FORWARDED_FOR` variable. No bloquea este PR por sí solo (riesgo de spam, no de acceso a datos; sin verificación de correo fuera de alcance), pero conviene registrarlo antes de exponer el registro a Internet.
