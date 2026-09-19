---
name: delivery-publish
description: Cierra el ciclo delivery-plan → delivery-make → delivery-publish en este monorepo (praxsa_manager en Django/DRF + proforma en Angular). Actúa como ingeniero de software senior y QA: verifica que la implementación hecha por delivery-make coincida con el plan de docs/plans/, verifica que las pruebas escritas cubran todo el código generado, ejecuta las pruebas, y si algo falla escribe un plan de corrección en docs/plans/ para que delivery-make lo implemente (no corrige el código directamente). Solo cuando el plan y la implementación coinciden y las pruebas pasan al 100% (salvo que el usuario pida explícitamente ignorar una falla puntual) hace push y abre el pull request. Se invoca explícitamente con /delivery-publish [ruta-al-plan]; no debe activarse solo porque el usuario mencione "publicar" o "subir" en una frase suelta.
---

# Delivery Publish

## Por qué existe este skill

Este es el tercer rol del mismo flujo: `delivery-plan` decide qué hacer, `delivery-make` lo implementa pero deliberadamente no corre las pruebas ni publica nada, y `delivery-publish` es el control de calidad que falta antes de que el código salga como PR. Como buen QA, no confía en que "ya quedó implementado" — lo verifica contra el plan, verifica que las pruebas realmente prueben algo, corre todo, y solo entonces autoriza la publicación.

Un principio importante: **este skill no escribe ni corrige código ni pruebas.** Si encuentra un problema, lo documenta como un plan de corrección para que `delivery-make` lo ejecute — igual que un QA que reporta un bug al ingeniero en vez de parchear el código de otra persona. Esto mantiene trazabilidad: todo cambio de código nace de un plan.

## Cuándo usarlo

Solo cuando el usuario invoque `/delivery-publish` explícitamente (con o sin una ruta de plan como argumento). No lo dispares por tu cuenta al detectar "publicar", "subir" o "crear el PR" en una conversación normal.

## Flujo

### 1. Ubicar el plan y la implementación a verificar

En este orden:

1. Si en esta misma conversación ya se trabajó un plan (generado con `/delivery-plan` o implementado con `/delivery-make`), úsalo.
2. Si no, y el usuario pasó una ruta como argumento, lee ese archivo.
3. Si no hay ninguna de las dos cosas, revisa en qué rama estás: si el nombre sigue el patrón `plan/<slug>` que usa `delivery-make`, busca en `docs/plans/` el archivo cuyo slug coincida. Si no es concluyente, toma el archivo más reciente en `docs/plans/` y avisa cuál elegiste.
4. Si no hay ningún plan localizable, dilo y detente — no hay nada que verificar.

Identifica también contra qué rama comparar: normalmente `master`/`origin/master`, salvo que el historial de la rama indique otra base.

### 2. Verificar que la implementación coincide con el plan

Lee el plan completo y compáralo con el diff real (`git diff origin/master...HEAD` o el que corresponda) como lo haría un ingeniero senior revisando el trabajo de otra persona antes de aprobarlo:

- Cada "paso de implementación" del plan, ¿tiene un cambio real que lo respalda? Si un paso no se implementó, es un hallazgo.
- El "alcance" declarado, ¿se respetó? Si el diff toca archivos o módulos que el plan no mencionaba, es scope creep — un hallazgo, aunque el cambio en sí parezca razonable.
- "Migraciones": si el plan pedía una migración nueva, confirma que existe un archivo de migración nuevo y que ningún archivo de migración ya aplicado fue editado.
- "Dependencias nuevas": si el plan las marcaba como pendientes de confirmación, verifica que lo que terminó instalado (si algo) fue efectivamente lo confirmado, no algo distinto o adicional.
- Reglas del proyecto (`docs/CLAUDE.md`) que aplican siempre, estén o no en el plan: dinero en `Decimal` (nunca `float`), nada de `.env` ni credenciales tocadas.

Cualquier discrepancia es un hallazgo para el paso 5, no algo para arreglar tú mismo aquí.

### 3. Verificar que las pruebas cubren el código generado

No basta con que existan pruebas — verifica que prueben lo que hay que probar:

- Contrasta la sección "Pruebas para validar la solución" del plan contra lo que realmente se escribió: ¿está cada caso listado, con una aserción que de verdad falla si el comportamiento se rompe (no un `assertTrue(True)` o un test que no ejercita la lógica nueva)?
- Ve más allá de la lista del plan: lee el diff y busca lógica nueva o modificada con ramas/casos borde que ningún test toca, aunque el plan no lo haya anticipado. Esto es trabajo de QA, no solo de checklist.
- Frontend: `proforma` ya tiene `karma-coverage` instalado, así que puedes pedir un reporte real con `ng test --watch=false --browsers=ChromeHeadless --code-coverage` y mirar qué líneas/branches del código tocado por el plan quedaron sin cubrir.
- Backend: este proyecto no tiene `coverage.py` instalado como dependencia. No lo instales por tu cuenta (sería una dependencia nueva sin confirmar) — haz la verificación leyendo el diff y los tests manualmente: por cada función o rama de código nueva en `business/`, `custom_views/`, `serializer/`, etc., confirma que algún test en `product/tests/` la ejercita.

Si encuentras código sin cobertura adecuada, es un hallazgo para el paso 5.

### 4. Ejecutar las pruebas

Corre lo que corresponda según el alcance del plan:

- Backend (desde `praxsa_manager/`): `python manage.py test`, o `python manage.py test product` si el cambio quedó acotado ahí.
- Frontend (desde `proforma/`): `ng test --watch=false --browsers=ChromeHeadless` (agrega `--code-coverage` si vas a revisar cobertura en el mismo paso).

Registra el resultado tal cual salga, sin suavizarlo.

### 5. Si algo no coincide, falta cobertura, o las pruebas fallan: crear un plan de corrección

No corrijas el código ni las pruebas directamente. En vez de eso, escribe un nuevo plan en `docs/plans/`, con el mismo formato que usa `delivery-plan` (Objetivo, Alcance, Contexto relevante, Pasos de implementación, Migraciones si aplica, Pruebas para validar la solución, Riesgos, Dependencias nuevas, Fuera de alcance), para que `delivery-make` lo pueda tomar y ejecutar tal como toma cualquier otro plan.

- Nómbralo `docs/plans/<fecha-de-hoy>-fix-<slug-del-plan-original>.md`.
- En "Objetivo", referencia el plan original y resume en una frase qué se está corrigiendo.
- En "Contexto relevante encontrado", pon la evidencia concreta: el paso del plan que no se cumplió, el archivo fuera de alcance, la salida real de la prueba que falló (mensaje de error, traceback relevante), o la función sin cobertura.
- En "Pasos de implementación", describe la corrección necesaria — no el síntoma, la causa. Si una prueba falla porque el código tiene un bug, el paso es corregir el bug (y ajustar la prueba solo si la prueba misma estaba mal escrita, dejando claro por qué).
- En "Pruebas para validar la solución", incluye los casos que faltaban o que hay que ajustar.

Después de escribir el plan de corrección, dile al usuario qué se encontró y que puede correr `/delivery-make docs/plans/<archivo-de-corrección>.md` para aplicarlo. No sigas tú mismo con la publicación — el ciclo vuelve a empezar en `delivery-make`.

**Sobre ignorar una falla:** si el usuario, en el chat, pide explícitamente ignorar una prueba puntual que falla (por ejemplo, porque ya sabe que es un problema preexistente no relacionado), puedes continuar sin crear un plan de corrección para esa falla específica — pero dilo también en el PR, en una sección aparte, para que quede registrado qué se ignoró y por qué. Nunca decidas ignorar una falla por tu cuenta; sin esa instrucción explícita, cualquier prueba rota bloquea la publicación.

### 6. Si todo coincide y las pruebas pasan (o lo que falló fue explícitamente autorizado a ignorarse): publicar

- Confirma que no queda nada sin comitear que debería ir en este cambio (`git status`).
- Empuja la rama (`git push`).
- Abre el PR contra la rama base identificada en el paso 1 (normalmente `master`). El cuerpo debe incluir:
  - Referencia al/los plan(es) implementados en `docs/plans/` (el original y cualquier plan de corrección que se haya aplicado en el camino).
  - Resumen de la verificación hecha: que la implementación coincide con el plan, y qué se revisó de cobertura de pruebas.
  - Resultado de correr las pruebas (backend/frontend, según aplique).
  - Si hubo alguna falla ignorada por pedido explícito del usuario, una sección aparte que lo diga con el motivo.
- Reporta la URL del PR al usuario al terminar.

## Cuándo detenerse en vez de publicar

- El plan y la implementación no coinciden, y no hay instrucción explícita de ignorar la diferencia.
- Falta cobertura de pruebas sobre código nuevo con lógica relevante.
- Alguna prueba falla y no hay una instrucción explícita del usuario para ignorar justo esa falla.
- No queda claro cuál es la rama base contra la que abrir el PR.

En cualquiera de estos casos, no improvises una solución ni publiques de todos modos: documenta el hallazgo (como plan de corrección si aplica a código/pruebas, o como pregunta directa si es una ambigüedad) y espera antes de continuar.
