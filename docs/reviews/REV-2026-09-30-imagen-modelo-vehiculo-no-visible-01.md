# REV-2026-09-30-imagen-modelo-vehiculo-no-visible-01: `SECURE_PROXY_SSL_HEADER` probablemente inefectivo en prod/stg (nginx interno reenvía `$scheme` = http)

**Status:** Code resolved (plan v2) — pendiente verificar `nginx -t` (no ejecutable: Docker daemon apagado, nginx no instalado)
**Severity:** Medium
**Category:** PLAN
**Related plan:** docs/plans/PLAN-2026-09-30-imagen-modelo-vehiculo-no-visible.md (v1)
**Suggested owner:** delivery-plan

## Description
El plan asume que `nginx.conf.prod|stg` "siempre fija `X-Forwarded-Proto` con `$scheme`" y que por eso `SECURE_PROXY_SSL_HEADER` hará que las URLs de imagen salgan en `https`. Pero ese nginx solo tiene `listen 80;` (sin TLS) y su contenedor solo hace `expose: 80`. Por lo tanto `$scheme` vale siempre `http` y **sobrescribe** cualquier `X-Forwarded-Proto: https` que venga de un terminador TLS externo. Django seguirá viendo `http` y emitirá `http://` en `image`.

## Expected behavior
Criterio de aceptación del plan: "Con `X-Forwarded-Proto: https` la API devuelve `image` con `https://`" y, por objetivo, que detrás de nginx en prod la URL sea `https` (evitar contenido mixto).

## Actual behavior
El test backend envía el header directamente al cliente de tests, por lo que solo prueba que Django respeta el header; no prueba la cadena real. Según la config del repo, el header que llegaría a Django en prod/stg es `http`.

## Evidence
```
nginx/nginx.conf.prod:17:        listen 80;
nginx/nginx.conf.prod:31:            proxy_set_header X-Forwarded-Proto $scheme;
nginx/Dockerfile.prod:3:# EXPOSE 443
docker-compose.prod.yml:32-33:    expose: - "80"
```
No se pudo verificar el terminador TLS externo (fuera del repo). Si existe y nginx interno usa `$scheme`, el cambio es inocuo pero no produce el efecto buscado; habría que usar `$http_x_forwarded_proto` (con `map`/fallback a `$scheme`) en nginx, lo que amplía el alcance a infraestructura.

## Notas
No bloquea: el fallback al placeholder (parte frontend) es independiente y está verificado. El cambio de settings no rompe nada (522 tests OK).
