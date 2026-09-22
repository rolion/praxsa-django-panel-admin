# REV-2026-09-21-002: Test de wiring de ReportStorageAdmin falla en el entorno de review por una limitación de SQLite, no por un defecto de código

**Status:** Resolved — re-ejecutado el 2026-09-22 contra Postgres real (`localhost:5432`, DB de desarrollo del usuario, vía el venv en `praxsa_manager/.venv`), a pedido del usuario. `python manage.py test product`: **27/27 pasan**, incluido `test_report_storage_admin_filtra_qs_y_aggregated_result`. Confirma la hipótesis de este REV: la causa era exclusivamente la sustitución por SQLite en el sandbox de review, no un defecto de código.
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-09-21-filtrado-sucursal-pagos-reportes-admin.md (v1)
**Suggested owner:** _(resuelto, sin acción pendiente)_

## Description

Este entorno de review no tiene Django instalado ni acceso a Postgres/credenciales reales (mismo límite que TASK-001, ver `REV-2026-09-21-001`). Para poder ejecutar la suite de todos modos, armé de forma independiente un venv efímero (fuera del repo, sin tocar ningún `.env`) con las dependencias de `requirements-3.8.10.txt` y `DATABASES` apuntando a SQLite en memoria.

Con eso corrí **la suite completa del app `product`** (no solo los tests nuevos): `product.tests.test_smoke` (6 tests preexistentes) + `product.tests.test_sucursal_scope_admin` (21 tests nuevos de este PR). Resultado: **26/27 pasan**. El único que falla es `AdminGetQuerysetWiringTest.test_report_storage_admin_filtra_qs_y_aggregated_result`, con un `ERROR` (no un `FAIL` de aserción) al evaluar la queryset.

La regla del Quality Gate es explícita: cualquier test que falle sin autorización previa del usuario para ignorarlo es motivo de `FAIL`, así que este review no puede declararse `PASS` mientras este test quede rojo — aunque, como se detalla abajo, la causa no es un defecto introducido por este cambio.

## Expected behavior

Según el plan (paso 7 de "Implementation steps" y criterio de aceptación "`ReportStorageAdmin.aggregated_result` respeta el mismo filtro de sucursal que el queryset principal"), `ReportStorageAdmin.get_queryset()` debería devolver únicamente filas de la sucursal del usuario (salvo Admin/Caja), y `aggregated_result` debería reflejar exactamente esas mismas sucursales.

## Actual behavior

El test falla con `django.db.utils.NotSupportedError: DISTINCT ON fields is not supported by this database backend`, al evaluar `result.values_list('id', flat=True)` sobre la queryset devuelta por `ReportStorageAdmin.get_queryset()`.

**Causa raíz confirmada, no relacionada con este cambio**: `ReportStorageAdmin.get_queryset` ya terminaba con `.distinct("sucursal__id","bobina__window_film__id", "bobina__width")` — sintaxis `DISTINCT ON`, exclusiva de PostgreSQL — **antes de este PR**. Verificado directamente:

```
$ git show origin/master:praxsa_manager/product/admin_config/report_storage.py | grep -n distinct
74:        return qs.select_related("sucursal", "bobina", "bobina__window_film").distinct("sucursal__id","bobina__window_film__id", "bobina__width").order_by(...)
```

Este PR no toca esa línea — solo reemplaza `qs`/`inventario.objects.select_related(...)` por `base_qs` (la queryset ya filtrada por sucursal) como entrada de esa misma cadena. El `DATABASES` real del proyecto (`praxsa_manager/settings.py:149-157`) usa `ENGINE: django.db.backends.postgresql`, que sí soporta `DISTINCT ON` — se espera que esta línea funcione en el backend real; el error es exclusivamente un artefacto de sustituir SQLite en este sandbox por no tener Postgres disponible.

**Verificación adicional realizada para no dejar esto en una mera hipótesis**: como `.distinct(*fields)` es lo único que SQLite rechaza (no el filtrado por sucursal en sí), reproduje el mismo escenario del test con un script ad hoc que llama a `ReportStorageAdmin.get_queryset()` de verdad y evalúa `model_admin.aggregated_result` (que usa `.values().annotate()`, sin `.distinct(*fields)`, y por lo tanto sí es evaluable en SQLite) en lugar de la queryset final. Resultado: con `sucursal_a` (id=1) y `sucursal_b` (id=2) creadas, `aggregated_result` contiene únicamente `{sucursal__id: 1}` — exactamente lo esperado, confirmando que el filtro por sucursal (`Inventario_Business.get_inventario_queryset_by_role`, que alimenta tanto `aggregated_result` como la queryset principal a través del mismo `base_qs`) funciona correctamente. Lo único que no pudo ejecutarse fue el paso final de `.distinct()`, no la lógica de filtrado que introduce este PR.

## Evidence

```
$ python manage.py test product --settings=test_settings -v 2
...
test_pagos_admin_filtra_por_sucursal ... ok
test_report_daily_sell_admin_filtra_por_sucursal ... ok
test_report_nota_trabajo_admin_filtra_por_sucursal ... ok
test_report_storage_admin_filtra_qs_y_aggregated_result ... ERROR
test_report_utilidad_admin_filtra_por_sucursal ... ok
[... 21 más, todos ok ...]

======================================================================
ERROR: test_report_storage_admin_filtra_qs_y_aggregated_result
----------------------------------------------------------------------
Traceback (most recent call last):
  File ".../product/tests/test_sucursal_scope_admin.py", line 265, in test_report_storage_admin_filtra_qs_y_aggregated_result
    ids = set(result.values_list('id', flat=True))
  ...
django.db.utils.NotSupportedError: DISTINCT ON fields is not supported by this database backend

----------------------------------------------------------------------
Ran 27 tests in 10.680s
FAILED (errors=1)
```

```
$ python <script ad hoc, evalúa solo aggregated_result>
aggregated_result sucursal ids: {1}
expected only: 1   (sucursal_b was 2 )
```

```
$ python manage.py makemigrations product --check --dry-run --settings=test_settings_realmig
No changes detected in app 'product'
```

## Resolución

El usuario pidió correr la suite con el Python de `E:\praxsa\praxsa-django-panel-admin\praxsa_manager\.venv` (su entorno local, ya configurado contra Postgres real). Se ejecutó `python manage.py test product -v 2` desde el worktree (`praxsa_manager/manage.py`, código de este PR) con las variables de conexión leídas de `praxsa_manager/.env` del checkout principal (nunca copiado, modificado ni impreso en el chat) exportadas solo para el proceso de este comando.

**Resultado: 27/27 tests pasan**, incluido el que fallaba en el sandbox de review. Django creó y destruyó su base de test temporal (`test_praxsa_backup`) como de costumbre; no se tocaron datos reales. También se confirmó `makemigrations product --check --dry-run` → `No changes detected` contra el mismo Postgres real.

No hizo falta ningún cambio de código — la hipótesis del REV (limitación exclusiva de SQLite en el sandbox, no del código) quedó confirmada.
