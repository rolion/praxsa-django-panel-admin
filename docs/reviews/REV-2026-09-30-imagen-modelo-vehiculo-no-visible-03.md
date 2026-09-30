# REV-2026-09-30-imagen-modelo-vehiculo-no-visible-03: comentario de `SECURE_PROXY_SSL_HEADER` desactualizado tras plan v2

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-09-30-imagen-modelo-vehiculo-no-visible.md (v2)
**Suggested owner:** delivery-engineer

## Description
El comentario sobre `SECURE_PROXY_SSL_HEADER` en `settings.py` afirma que nginx "siempre fija X-Forwarded-Proto". Con plan v2 eso ya no es cierto: el bloque del panel propaga el valor entrante de nginx-proxy (vía `map`) y solo cae a `$scheme` si viene vacío.

## Expected behavior
El comentario describe la cadena real (nginx-proxy termina TLS → nginx interno propaga el header → Django), para que quien toque nginx o settings no rompa la dependencia.

## Actual behavior
`praxsa_manager/praxsa_manager/settings.py` (~línea 214): "ver nginx/nginx.conf.prod|stg, que siempre fija X-Forwarded-Proto".

## Evidence
`git diff origin/master...HEAD -- praxsa_manager/praxsa_manager/settings.py` (comentario no modificado en el commit b509b68 de plan v2). No bloquea.
