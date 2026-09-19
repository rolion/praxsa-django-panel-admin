---
name: delivery-plan
description: Genera un plan de implementación por escrito para una tarea de este monorepo (praxsa_manager en Django/DRF + proforma en Angular) antes de tocar código. Analiza la tarea con criterio de arquitecto de software senior en Django y Angular, pregunta si algo queda ambiguo en vez de asumir, investiga el código relevante, evalúa riesgos y complicaciones de arquitectura (contratos de API, migraciones, rendimiento, seguridad), incluye las pruebas concretas que validan la solución, respeta las reglas de docs/CLAUDE.md (cambios pequeños, un objetivo por cambio, Decimal para dinero, no editar migraciones aplicadas, avisar antes de nuevas dependencias) y guarda el resultado como archivo en docs/plans/. Se invoca explícitamente con /delivery-plan <descripción de la tarea>; no debe activarse solo porque el usuario mencione "plan" o "implementar" en una frase suelta.
---

# Delivery Plan

## Por qué existe este skill

`docs/CLAUDE.md` ya pide: "Antes de cambios que afecten varios archivos, proponer un plan y esperar confirmación." Este skill es esa práctica hecha repetible: en vez de improvisar un plan distinto cada vez, sigue siempre la misma investigación y el mismo formato, para que cualquiera del equipo (o Claude en otra sesión) pueda leer `docs/plans/` y entender qué se decidió y por qué.

Un plan bueno aquí vale más que uno exhaustivo: el objetivo es que la persona que lo lea pueda aprobarlo o corregirlo en un vistazo, no que cubra cada caso imaginable.

## Cuándo usarlo

Solo cuando el usuario invoque `/delivery-plan <tarea>` explícitamente. No lo dispares por tu cuenta al detectar palabras como "plan" o "implementar" en una conversación normal — el usuario prefiere pedirlo a propósito.

## Flujo

### 1. Entender la tarea antes de investigar

Lee la descripción de la tarea con la mirada de un arquitecto de software senior con experiencia real en Django/DRF y Angular: qué problema de negocio resuelve, qué comportamiento nuevo se espera, y qué capas del sistema probablemente intervienen (¿es puramente backend, puramente frontend, o requiere cambios coordinados en ambos porque cambia el contrato de la API?).

Si algo queda ambiguo, pregunta antes de seguir — no asumas y sigas adelante. Ejemplos de cuándo preguntar:
- La tarea admite más de una interpretación razonable (p. ej. "agregar descuento" — ¿por sucursal, por cliente, por volumen?).
- No queda claro si debe tocar backend, frontend o ambos.
- Hay un caso borde que cambiaría la solución según la respuesta (p. ej. qué pasa con proformas ya creadas si cambia una regla de precio).
- Falta un dato necesario para dimensionar el trabajo (rango de valores, quién lo usa, con qué frecuencia).

Si la tarea ya es clara y acotada, no preguntes por preguntar — sigue directo a investigar. El objetivo es evitar construir un plan entero sobre un supuesto equivocado, no interrogar al usuario por rutina.

### 2. Investigar el código como arquitecto

No redactes el plan de memoria. Este proyecto tiene, según sus propias palabras, deuda técnica ("El proyecto NO se construyó con buenas prácticas"), así que lo que parece obvio por el nombre de un archivo puede no serlo. Investiga no solo dónde insertar código nuevo, sino cómo encajan las piezas: qué contrato expone el backend hacia el frontend (endpoints DRF, forma de los serializers), qué asume cada lado del otro, y qué tan frágil es esa relación en este código concreto.

- Ubica el código relevante a la tarea. El backend (`praxsa_manager/product/`) separa por capas: `business/` (lógica de dominio), `admin_config/` (registro en el admin de Django), `custom_views/` (endpoints DRF), `serializer/`, `Forms/`, `helper/`. Una tarea sobre, por ejemplo, precios de láminas probablemente toca `business/precio_venta.py`, su `admin_config`, y quizás `custom_views/`.
- Revisa `praxsa_manager/product/migrations/` para saber cuál es la última migración, si la tarea implica cambios de modelo.
- Revisa `praxsa_manager/product/tests/` para ver qué patrón de test ya existe (`helpers.py` trae fixtures/utilidades compartidas) y no reinventar convenciones.
- Si la tarea toca el frontend, ubica los componentes/servicios relevantes en `proforma/src/`.
- Si existen, revisa `docs/backend-audit.md`, `docs/frontend-audit.md` y `docs/integration-and-backlog.md` por si ya hay contexto conocido sobre esa área (deuda técnica identificada, TODOs, bugs conocidos).

Usa Grep/Glob para esto en vez de asumir; cita rutas y líneas reales (`archivo.py:42`) en el plan, no ubicaciones inventadas.

### 3. Evaluar riesgos y complicaciones de arquitectura

Antes de proponer los pasos, piensa como arquitecto qué puede salir mal más allá del camino feliz. No hace falta que todos apliquen a cada tarea, pero revísalos activamente:

- **Contrato API**: ¿el cambio rompe algo que el frontend Angular ya consume (forma de la respuesta, nombre o tipo de un campo)? ¿hay que coordinar el despliegue de backend y frontend?
- **Datos existentes**: ¿una migración de modelo puede fallar o dejar en un estado inconsistente registros ya guardados? ¿hay filas que no cumplirían una regla nueva?
- **Dinero y precisión**: cualquier cálculo nuevo de precios/pagos debe seguir usando `Decimal`; señala si el cambio introduce alguna conversión riesgosa (`float`, redondeos).
- **Rendimiento**: ¿el cambio agrega consultas N+1, reportes pesados, o cálculos en loop sobre inventario/proformas que puedan crecer mucho?
- **Seguridad y permisos**: ¿el cambio toca vistas del admin o endpoints que deberían quedar restringidos por rol o sucursal?
- **Acoplamiento**: dado que hay deuda técnica conocida (ver `docs/*-audit.md`), ¿tocar este archivo puede tener efectos secundarios en otra parte que lo importa o hereda de él?

Documenta lo que encuentres aunque no tenga solución todavía — esa es justamente la información que necesita quien apruebe el plan para decidir con criterio.

### 4. Escribir el plan

Crea (o asegúrate de que exista) la carpeta `docs/plans/`. Guarda el plan como `docs/plans/<YYYY-MM-DD>-<slug-de-la-tarea>.md`, usando la fecha de hoy y un slug corto en minúsculas con guiones derivado de la tarea.

Usa esta plantilla. Omite una sección solo si genuinamente no aplica (por ejemplo, "Migraciones" en una tarea que no toca modelos) — no la dejes vacía, bórrala.

```markdown
# <Título corto de la tarea>

## Objetivo
Qué se quiere lograr y por qué, en 1-3 frases. Si la tarea vino con una motivación de negocio (un bug reportado, un pedido de sucursal, etc.), inclúyela.

## Alcance
Qué partes del monorepo toca: backend (`praxsa_manager`), frontend (`proforma`), o ambos. Lista las apps/módulos específicos identificados en la investigación.

## Contexto relevante encontrado
Lo que se encontró al revisar el código actual: archivos y líneas relevantes (`archivo.py:42`), comportamiento actual, y cualquier deuda técnica o riesgo ya documentado en `docs/*-audit.md` que aplique aquí.

## Pasos de implementación
Lista ordenada y pequeña. Cada paso debe ser algo verificable (un archivo que cambia, una función que se agrega). Si la tarea es grande, divídela en fases, cada una pensada para un PR separado — no la comprimas en un solo paso gigante.

## Migraciones
Si el paso anterior requiere cambios de modelo: qué migración nueva se crea (nunca editar una ya aplicada) y qué comando la genera.

## Pruebas para validar la solución
Esto no es opcional ni un recordatorio genérico de "agregar tests": describe los casos de prueba concretos que van a confirmar que la solución funciona, uno por cada comportamiento nuevo o modificado. Para cada caso indica el escenario (dado/cuando/entonces, o input → output esperado) y dónde vive (`product/tests/` en backend, specs de Angular en frontend). Si un paso de implementación cambia lógica de negocio y no tiene un caso de prueba correspondiente aquí, el plan está incompleto.

## Riesgos y complicaciones de arquitectura
Lo que salió de evaluar la tarea como arquitecto: contrato API entre backend y frontend, impacto en datos existentes o migraciones, precisión de `Decimal` en dinero, rendimiento (consultas N+1, reportes pesados), permisos/seguridad, y acoplamiento con otras partes del código dada la deuda técnica conocida. Si algún riesgo no tiene mitigación clara, dilo explícitamente en vez de omitirlo.

## Dependencias nuevas
Si el plan requiere instalar algo que no está ya en el proyecto, decirlo aquí explícitamente — el proyecto exige avisar antes de agregar dependencias, así que esto es una señal para pedir confirmación, no algo para resolver solo.

## Fuera de alcance / preguntas abiertas
Cosas que no se pudieron verificar en el código, decisiones que le corresponden al usuario, o partes de la tarea que quedan deliberadamente para otro PR.
```

### 5. Presentar y esperar confirmación

Después de guardar el archivo, resume el plan en el chat en pocas líneas (no repitas el archivo completo) y pregunta si se puede proceder con la implementación o si hay que ajustar algo. No empieces a programar en la misma respuesta salvo que el usuario ya lo haya pedido explícitamente junto con el plan.
