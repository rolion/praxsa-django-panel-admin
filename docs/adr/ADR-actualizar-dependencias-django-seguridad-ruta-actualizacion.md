# ADR-actualizar-dependencias-django-seguridad-ruta-actualizacion: Ruta de actualización de Django y dependencias

**Estado:** Propuesto
**Task relacionado:** TASK-actualizar-dependencias-django-seguridad
**Fecha:** 2026-10-02

## Contexto
El backend corre `Django==4.2.1` (`praxsa_manager/requirements-3.8.10.txt:6`). La rama 4.2 LTS terminó soporte en abril de 2026 (último release 4.2.30); las ramas con soporte son 5.2 LTS (hasta abril 2028) y 6.0 (hasta abril 2027). El resto de pins son de mediados de 2023 (`gunicorn 20.1.0`, `Pillow 10.0.1`, `requests 2.31.0`, `urllib3 2.0.3`, `sqlparse 0.4.4`, `certifi 2023.5.7`...). Los Dockerfiles usan Python 3.8 (`Dockerfile`, `Dockerfile.stg`) y 3.10 (`Dockerfile.prod`, `Dockerfile.v2`); los cuatro instalan `requirements-3.8.10.txt`.

Hechos del código que condicionan la ruta:
- `praxsa_manager/product/models.py:291` y la migración `0113_inventario_movimiento.py` usan `CheckConstraint(check=...)`. Ese argumento se renombra a `condition` en 5.1 (deprecado) y, según mi conocimiento (no verificado en esta sesión), se elimina en 6.0. La migración ya aplicada no se puede editar (`docs/CLAUDE.md`).
- `settings.py:200` fija `USE_TZ = False` explícito; el cambio de default de 5.0 no lo afecta.
- Sin `index_together`, `DEFAULT_FILE_STORAGE`, `ugettext`, `length_is` ni `timezone.utc` en código no-migración (grep). Superficie de deprecación propia baja.
- Compatibilidad de terceros (PyPI, 2026-10-02): `django-tinymce 5.0.0` y `django-cors-headers 4.9.0` declaran 5.2; `martor 1.8.2` declara hasta 5.1; `djangorestframework 3.18.1` y `django-filter 26.1` declaran 5.2/6.x pero exigen Python ≥ 3.10; `django-bootstrap-v5 1.0.11` (sin release nuevo) y `django-admin-list-filter-dropdown 1.0.3` no declaran ninguna versión de Django moderna; `django-admin-logs` y `django-admin-rangefilter` no declaran versiones.

## Decisión
Actualizar en **dos etapas, cada una en su propio PR y despliegue**:

1. **Etapa A — parches sin cambio de plataforma.** Subir Django a `4.2.30` (última de la rama) y las dependencias de seguridad a su último parche compatible con Python 3.8/3.10 sin cambiar de versión mayor (`Pillow`, `requests`, `urllib3`, `certifi`, `sqlparse`, `gunicorn`, etc., hasta donde permita el runtime). Cierra los CVE ya parcheados con el menor riesgo posible y es reversible al instante.
2. **Etapa B — Django 5.2 LTS sobre Python 3.12.** Unificar los cuatro Dockerfiles en la misma imagen base de Python, subir Django a la última `5.2.x`, DRF/django-cors-headers/django-tinymce/martor a versiones que declaren 5.2, y probar en el stack v2 (volúmenes separados) antes de tocar producción. Los paquetes del admin sin soporte declarado (`django-bootstrap-v5`, `django-admin-list-filter-dropdown`, `django-admin-logs`, `django-admin-rangefilter`) se validan en esa etapa con la suite y un smoke test manual del admin; si alguno rompe, se reemplaza o se vendoriza solo ese paquete (decisión caso a caso en el plan, no ahora).

Destino **5.2 LTS, no 6.0**: soporte hasta 2028 contra 2027, y evita tener que reescribir `CheckConstraint(check=)` más una migración ya aplicada. La salida a 6.0 queda como tarea futura, no parte de esta.

Además: agregar `pip-audit` como verificación manual/CI documentada (sin sumarlo a `requirements`) para que el estado de CVE deje de ser una suposición. No se renombra `requirements-3.8.10.txt` en esta tarea (el nombre queda engañoso; renombrarlo toca cuatro Dockerfiles sin aportar seguridad).

## Alternativas consideradas
- **Salto directo 4.2.1 → 5.2 en un solo PR.** Más simple en papel, pero mezcla parches urgentes de seguridad con un riesgo de ruptura de terceros; si falla, se pierden también los parches. Descartada.
- **Solo parchear 4.2.30 y quedarse.** Barata, pero la rama ya no recibe parches: la deuda reaparece con el próximo CVE. Se acepta únicamente como etapa A, no como destino.
- **Ir a Django 6.0.** Soporte más corto (abril 2027) y obliga a tocar `check=` y una migración ya aplicada. Descartada por ahora.
- **Congelar y poner WAF/mitigaciones externas.** No resuelve vulnerabilidades de la librería. Descartada.

## Estrategia de rollback / mitigación
- Infraestructura/dependencias, no esquema: cada etapa es un PR revertible; las imágenes anteriores se conservan con tag para volver a desplegarlas.
- Antes de desplegar la etapa B: `pg_dump` de la base. Django 5.x puede aplicar migraciones de `contrib` (auth/admin/etc.) que un código 4.2 no conozca; el plan debe correr `makemigrations --check --dry-run` y listar migraciones nuevas pendientes (`showmigrations`) para confirmar si eso ocurre. Si ocurre, el rollback incluye restaurar el dump, no solo la imagen.
- Probar primero en el stack v2 con volúmenes aparte (`docs/deployment-v2.md:16`); no se despliega a producción sin suite verde (`python manage.py test`) y smoke test manual de admin (usuarios, proformas, pagos, reportes) y de los endpoints que consume el frontend.
- Etapa A puede desplegarse antes y por separado: su rollback es volver a la imagen anterior.

## Consecuencias
- **Más fácil:** backend con soporte de seguridad hasta 2028, runtime de Python unificado, estado de CVE verificable.
- **Más difícil:** hay que validar a mano paquetes de admin sin soporte declarado; dos despliegues en vez de uno.
- **Deuda aceptada:** nombre `requirements-3.8.10.txt` engañoso; `CheckConstraint(check=)` pendiente para la futura subida a 6.x; Angular 16/Node 18 y las vulnerabilidades de `npm audit` quedan **fuera de esta tarea** y requieren su propio task.
