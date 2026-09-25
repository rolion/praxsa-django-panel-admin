# REV-2026-09-23-003: ADR-006 y el plan afirman incorrectamente que `abrir_proforma` revierte `status` a `'proforma'`

**Status:** Open
**Severity:** Low
**Category:** ARCHITECTURE
**Related plan:** docs/plans/PLAN-2026-09-23-proforma-status-field.md (v1)
**Suggested owner:** delivery-architect

## Description
`ADR-006` (Decisión, punto 2) dice textualmente: *"Proforma_Business.abrir_proforma (después de reabrir — vuelve el estado a 'proforma')"*. El plan repite la misma afirmación en `Expected behavior` ("Al ejecutar abrir_proforma (reabrir) → status vuelve a 'proforma'") y en el caso de prueba 3 de `Test strategy` ("test_abrir_proforma_vuelve_a_status_proforma — sobre una proforma ya en 'nota_trabajo', abrir_proforma la vuelve a 'proforma'"). Verificado leyendo `business/proforma.py:60-81` (método `abrir_proforma`, sin cambios en su lógica de negocio más allá de agregar la llamada a `refresh_status`): el método nunca borra ni desvincula la `Nota_trabajo` ya creada — solo devuelve inventario y pone `is_close = False`. Por lo tanto `hasattr(proforma, 'nota_trabajo')` sigue siendo `True` después de "abrir" la proforma, y tanto `ProformaAdmin.get_estado()` (ya existente, sin tocar) como el `status` nuevo correctamente permanecen en `'nota_trabajo'`/`'Nota Trabajo'` — no vuelven a `'proforma'`.

## Expected behavior
El ADR y el plan, como documentos de decisión, deberían describir correctamente el comportamiento resultante de la transición que ellos mismos definen, para que alguien que los lea sin ejecutar el código no se lleve una expectativa equivocada.

## Actual behavior
La implementación es correcta (replica fielmente la lógica de `get_estado`, que es la decisión arquitectónica real y válida de ADR-006 punto 2); solo la frase descriptiva entre paréntesis sobre el resultado de `abrir_proforma` es fácticamente incorrecta, tanto en el ADR como en el plan. `delivery-engineer` lo detectó durante la implementación y corrigió el test correspondiente (ahora `test_abrir_proforma_no_revierte_status_porque_nota_trabajo_persiste`, con comentario explicando el porqué) y lo documentó en `## Implementación` de TASK-009 — pero no actualizó el texto del ADR ni del plan, que siguen afirmando lo contrario.

## Evidence
```python
# business/proforma.py:60-81 (abrir_proforma, verificado sin cambios de lógica salvo la llamada nueva)
@transaction.atomic
def abrir_proforma(self, proforma):
    if proforma.is_close == True:
        try:
            with transaction.atomic():
                detalles = Proforma_Detail.objects.select_related(...)
                detalles = detalles.filter(proforma_header = proforma)
                proforma.is_close = False
                if detalles.exists():
                    for detalle in list(detalles):
                        ...  # solo devuelve inventario
                proforma.save()
                return self.refresh_status(proforma)
```
Ningún `Nota_trabajo.objects...delete()` ni desvinculación de `proforma.nota_trabajo` en todo el método. Test que confirma el comportamiento real (pasa):
```
test_abrir_proforma_no_revierte_status_porque_nota_trabajo_persiste ... ok
```
No bloquea: el código y los tests ya son correctos; el criterio de aceptación real ("status coincide con get_estado() en todo momento") se cumple. El hallazgo es puramente documental — sugerido para `delivery-architect`: corregir la frase en ADR-006 punto 2 (y en el plan, `Expected behavior`/caso de prueba 3) para que describan el comportamiento real verificado, evitando que un futuro lector del ADR asuma una transición que no ocurre.
