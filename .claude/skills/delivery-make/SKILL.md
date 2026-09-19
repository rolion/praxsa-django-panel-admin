---
name: delivery-make
description: Implementa un plan ya generado por el skill delivery-plan (o el que se pase como ruta) en este monorepo (praxsa_manager en Django/DRF + proforma en Angular). Actúa como ingeniero de software senior experto en Django y Angular, pregunta si algún requerimiento del plan no queda claro en vez de asumir, sigue las mejores prácticas de Django y Angular, escribe el nivel de pruebas que corresponde a cada caso (unitarias, de integración o e2e — no siempre las tres) y deja el trabajo comiteado localmente en una rama. No ejecuta las pruebas ni hace push — eso queda para un paso aparte, deliberado por el usuario. Se invoca explícitamente con /delivery-make [ruta-al-plan]; no debe activarse solo porque el usuario mencione "implementar" en una frase suelta.
---

# Delivery Make

## Por qué existe este skill

`delivery-plan` produce un plan por escrito en `docs/plans/`. Este skill es el otro extremo del mismo flujo: toma ese plan ya aprobado y lo convierte en código, con la misma disciplina de ingeniería que se le pidió al plan — no una implementación improvisada que se aparta de lo acordado.

## Cuándo usarlo

Solo cuando el usuario invoque `/delivery-make` explícitamente (con o sin una ruta de plan como argumento). No lo dispares por tu cuenta al detectar "implementar" en una conversación normal.

## Flujo

### 1. Ubicar el plan a implementar

En este orden:

1. Si en esta misma conversación ya se generó o se leyó un plan (por ejemplo, con `/delivery-plan` en los mensajes previos), úsalo directamente — no hace falta volver a preguntar cuál es.
2. Si no, y el usuario pasó una ruta como argumento (`/delivery-make docs/plans/2026-09-19-algo.md`), lee ese archivo.
3. Si no hay ninguna de las dos cosas, busca en `docs/plans/` el archivo más reciente (por la fecha en el nombre, y si empatan, por fecha de modificación) y avisa cuál elegiste, para que el usuario pueda corregirte si no era ese.
4. Si `docs/plans/` no existe o está vacío, dilo y detente — no hay nada que implementar.

### 2. Entender el plan como ingeniero senior antes de tocar código

Lee el plan completo con la misma mirada de ingeniero senior en Django/DRF y Angular con la que se escribió: objetivo, alcance, contexto encontrado, pasos, migraciones, pruebas requeridas, riesgos de arquitectura, dependencias nuevas, y fuera de alcance.

Un plan escrito hace tiempo puede haber quedado desactualizado si el código cambió mientras tanto. Antes de seguir sus pasos al pie de la letra, verifica que lo que describe siga siendo cierto (¿el archivo que menciona sigue en esa ruta? ¿la función que dice modificar todavía existe con esa firma?). Si algo no cuadra, para y dile al usuario qué encontraste en vez de adaptar el plan por tu cuenta silenciosamente.

Si algún requerimiento queda ambiguo para poder implementarlo — el plan describe el "qué" pero no el "cómo" en un punto donde hay más de una forma razonable de resolverlo, o un paso da por sentado algo que ya no se sostiene, o falta un detalle necesario para escribir el código (p. ej. qué hacer con un caso borde que el plan no contempló) — pregunta antes de decidir por tu cuenta. Implementar sobre un supuesto equivocado cuesta más corregirlo después que preguntar antes. Si el plan es lo bastante claro para el paso que vas a dar, no preguntes por preguntar.

### 3. Preparar la rama

Revisa en qué rama y estado está el working tree (`git status`). No descartes trabajo sin comitear que no sea tuyo.

- Si estás en `master`/`main` con el árbol limpio: trae lo último (`git fetch`) y crea una rama nueva desde `origin/master` llamada `plan/<slug-del-archivo-del-plan>`.
- Si ya estás en una rama dedicada a este trabajo (por ejemplo, la rama de la sesión donde se generó el plan), puedes seguir ahí en vez de crear una nueva — si no es obvio cuál es el caso, pregunta antes de decidir.

### 4. Implementar los pasos del plan

Sigue los "Pasos de implementación" del plan en orden, sin salirte del "Alcance" declarado ahí — este skill ejecuta el plan aprobado, no una versión ampliada de él.

Aplica siempre las reglas del proyecto (`docs/CLAUDE.md`), estén o no repetidas en el plan: dinero con `Decimal` nunca `float`, nunca editar una migración ya aplicada (crear una nueva), cambios acotados a un objetivo.

Dos casos en los que debes parar y preguntar en vez de seguir hasta el final tú solo:
- El plan lista algo en "Dependencias nuevas": instalar paquetes requiere aviso previo según las reglas del proyecto, así que confirma antes de correr `pip install` / `npm install`, aunque el resto del flujo hasta el commit sí lo hagas de punta a punta.
- Durante la implementación descubres que la realidad del código diverge de lo que el plan asumía de forma que cambia el alcance o el riesgo: dilo y espera confirmación antes de improvisar una solución distinta a la acordada.

#### Buenas prácticas a aplicar mientras escribes el código

Un ingeniero senior no solo hace que el paso funcione, lo deja consistente con cómo se debería construir este tipo de sistema. Ten estas prácticas presentes al escribir cada paso (sin forzar una reescritura de lo que no toca el plan):

**Django / DRF:**
- Mantén la lógica de negocio fuera de las vistas: si el paso agrega una regla o cálculo, va en `business/` (o `helper/` si es una utilidad), no inline en `custom_views/` — así ya está organizado este proyecto.
- Deja que los serializers validen la forma y los tipos de entrada; no repliques esa validación a mano en la vista.
- Cuidado con N+1: si el paso itera sobre un queryset y accede a relaciones (`related_object.campo`), usa `select_related`/`prefetch_related` en vez de dejar que Django dispare una consulta por fila.
- Todo cambio de modelo va con su migración generada por Django (`makemigrations`), nunca escrita a mano ni editando una ya aplicada.
- Dinero siempre en `Decimal`, nunca `float`, incluyendo constantes y resultados intermedios de un cálculo.
- Nombres y estructura de archivos consistentes con lo que ya existe en la carpeta donde estás agregando código, no una convención nueva propia.

**Angular:**
- La lógica que no es de presentación (llamadas HTTP, transformación de datos, reglas de negocio del frontend) va en un service inyectable, no en el componente.
- Usa tipos explícitos (interfaces/modelos) para lo que viaja hacia y desde el backend en vez de `any`, para que un cambio de contrato de la API se note en tiempo de compilación.
- Con Observables: evita suscripciones manuales que puedan quedar colgadas — prefiere el `async` pipe en el template o desuscribirte explícitamente (`takeUntil`, `Subscription.unsubscribe()`) si no queda otra.
- Si el paso agrega un formulario, usa Reactive Forms con validación declarada en el `FormGroup`, siguiendo el patrón de los formularios ya existentes en el proyecto.
- Mantén el componente enfocado en una sola responsabilidad; si crece mucho al agregar el paso, es señal de que parte de esa lógica debería salir a un service o a un componente hijo — pero no hagas ese refactor si el plan no lo pidió, solo evita empeorar el problema.

### 5. Escribir las pruebas — el nivel que corresponde, no siempre los tres

La sección "Pruebas para validar la solución" del plan ya define los casos concretos a cubrir; tu trabajo aquí es implementarlos exactamente, eligiendo el nivel de prueba correcto para cada uno — no agregar los tres tipos por reflejo a cada cambio:

- **Unit**: para lógica aislada que no necesita base de datos ni HTTP — funciones en `business/` o `helper/` del backend, o un service/pipe puro en Angular. Es el nivel por defecto para una regla de negocio o cálculo que cambia.
- **Integración**: cuando lo que hay que validar es que varias piezas trabajan bien juntas — un endpoint DRF completo (view + serializer + modelo + base de datos real), siguiendo el patrón ya usado en `praxsa_manager/product/tests/test_smoke.py` (`Django TestCase` + `self.client`, con `praxsa_manager/product/tests/helpers.py` para armar datos). En Angular, esto es un componente probado junto con sus servicios reales vía `TestBed` y `HttpTestingController`, no todo mockeado.
- **E2E**: solo cuando el riesgo que describe el plan está al nivel de un flujo de usuario completo cruzando varias pantallas (ej. login → elegir sucursal → generar proforma → pago), y el plan lo pidió explícitamente por ese motivo. **Importante**: este proyecto todavía no tiene ningún framework de e2e instalado (no hay Cypress, Playwright ni Protractor en `proforma/package.json`). Si hace falta un test e2e, instalar esa herramienta cuenta como una dependencia nueva — para y pide confirmación antes de agregarla, igual que con cualquier otra dependencia.

Señal de que te saliste de rango: si estás por escribir un test que no corresponde a ningún caso listado en la sección de pruebas del plan, probablemente no debería estar ahí — vuelve al plan en vez de inventar cobertura adicional.

Este skill no ejecuta las pruebas que escribe. Al terminar, dile al usuario qué comando correspondería correr para verificarlas (`python manage.py test` o `python manage.py test product` desde `praxsa_manager/` para backend, `ng test` desde `proforma/` para frontend), pero la ejecución y la corrección de lo que falle quedan fuera de este skill.

### 6. Commit

Revisa qué quedó modificado (`git status`/`git diff`) y confirma que solo son archivos relacionados al plan antes de comitear. Mensaje de commit corto, en modo imperativo, mencionando qué se implementó y de qué plan viene (por ejemplo, referenciando el nombre del archivo en `docs/plans/`).

No hagas `git push` ni abras un pull request como parte de este skill — el trabajo queda comiteado localmente en la rama. Publicarlo es una decisión aparte del usuario (por ejemplo, pidiendo explícitamente crear el PR después de revisar el diff).

Al terminar, resume en el chat qué se implementó, qué pruebas se escribieron y en qué nivel, y qué comandos correrían para validarlas.

## Cuándo detenerse antes de comitear

No fuerces el flujo completo si te encuentras con:
- Una dependencia nueva no confirmada todavía.
- El plan contradice lo que hay hoy en el código.
- Un requerimiento del plan que sigue ambiguo después de leerlo con cuidado.
- Duda real sobre en qué rama deberías estar trabajando.

En cualquiera de estos casos, para y pregunta — el objetivo de este skill es ejecutar el plan con criterio de ingeniero senior, no llegar a un commit a toda costa.
