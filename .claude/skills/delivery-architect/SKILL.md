---
name: delivery-architect
description: Toma la investigación de un task (docs/tasks/TASK-<id>.md, producida por delivery-investigate) y determina las decisiones arquitectónicas necesarias en este monorepo (praxsa_manager en Django/DRF + proforma en Angular). Interviene cuando hay cambio estructural, nuevo módulo o bounded context, nueva integración externa, cambios importantes de base de datos, cambios de autenticación/autorización, cambios de infraestructura, impacto en múltiples módulos, problemas con la arquitectura existente, o decisiones que puedan generar deuda técnica importante. Evalúa la arquitectura existente, identifica impactos, compara alternativas, explica trade-offs, evita sobreingeniería y define una estrategia explícita de rollback/mitigación para cambios sensibles (o justifica por qué no aplica). Registra la decisión como ADR en docs/adr/ADR-<id>-<slug>.md y actualiza el TASK. No implementa código. Se invoca explícitamente con /delivery-architect TASK-<id>; no debe activarse solo porque el usuario mencione "arquitectura" o "diseño" en una frase suelta.
---

# Delivery Architect

## Por qué existe este skill

No todas las tareas necesitan una decisión arquitectónica, pero las que sí la necesitan no deben resolverse de paso dentro de un plan de implementación. Este skill existe para que esa decisión quede explícita, comparada contra alternativas, y registrada como ADR — trazable independientemente del plan que la ejecuta. `delivery-investigate` decide si esta etapa es necesaria (veredicto `NEEDS_ARCHITECTURE`); este skill no re-investiga desde cero, parte de lo que ya se documentó.

## Cuándo usarlo

Solo cuando el usuario invoque `/delivery-architect TASK-<id>` explícitamente — típicamente porque `delivery-investigate` emitió `NEEDS_ARCHITECTURE`, o porque `delivery-review`/`delivery-engineer` reabrieron el task con `ARCHITECTURE_REVIEW_REQUIRED`. No lo dispares por tu cuenta.

## Inputs

- `TASK-<id>` con la sección `## Investigación` ya completa.

## Outputs

- Uno o más ADR en `docs/adr/ADR-<id>-<slug>.md`.
- `docs/tasks/TASK-<id>.md` actualizado: sección `## Arquitectura` enlazando el/los ADR, transición de etapa, fila en el historial.

## Flujo

### 1. Leer el TASK

Lee `docs/tasks/TASK-<id>.md` completo. Si `## Investigación` está vacía o dice "Pendiente", detente y dile al usuario que primero corra `/delivery-investigate TASK-<id>`. Si el task viene de un `ARCHITECTURE_REVIEW_REQUIRED` (reportado por `delivery-engineer` o `delivery-review`), lee también esa nota en `## Implementación` o `## Review` para entender qué problema arquitectónico se encontró a mitad de camino.

### 2. Evaluar la arquitectura existente

No propongas en el vacío. Revisa cómo está construido hoy el área afectada (capas del backend en `praxsa_manager/product/`, estructura de servicios/componentes en `proforma/src/`, ADRs previos en `docs/adr/` que puedan ya haber decidido algo relacionado) antes de decidir. Mantén consistencia con decisiones arquitectónicas ya tomadas, a menos que la tarea justifique explícitamente revisarlas.

### 3. Identificar impactos

Piensa en términos concretos de este stack:
- **Contrato API**: ¿rompe algo que el frontend Angular ya consume?
- **Datos existentes / migraciones**: ¿una migración puede fallar sobre datos ya guardados?
- **Autenticación/autorización**: ¿cambia quién puede hacer qué?
- **Infraestructura**: ¿afecta Docker, variables de entorno, despliegue (`docker-compose.*.yml`, `nginx/`)?
- **Acoplamiento**: dada la deuda técnica conocida (`docs/*-audit.md`), ¿el cambio se propaga a módulos que no se esperaban?

### 4. Proponer soluciones y comparar alternativas

Cuando exista más de una forma razonable de resolverlo, compáralas explícitamente con sus trade-offs (complejidad, esfuerzo, deuda técnica que deja, consistencia con lo existente). Evita sobreingeniería: la alternativa más simple que resuelve el problema real gana salvo que haya una razón concreta para algo más elaborado — no diseñes para requerimientos hipotéticos futuros.

### 5. Definir estrategia de rollback/mitigación

Para cambios sensibles (infraestructura, autenticación/autorización, base de datos), la decisión debe incluir explícitamente cómo se revierte o mitiga si algo sale mal en producción: feature flag, migración reversible, despliegue gradual, plan de rollback de infraestructura, etc. Si genuinamente no aplica (por ejemplo, el cambio es aditivo y no puede romper nada existente), dilo y justifica por qué no hace falta — no lo omitas en silencio.

### 6. Crear o actualizar el ADR

Calcula el próximo id: lista `docs/adr/ADR-*.md` (Glob), toma el número más alto y súmale 1 (`001` si no hay ninguno), 3 dígitos. Nombra el archivo `docs/adr/ADR-<id>-<slug-corto-de-la-decisión>.md`.

```markdown
# ADR-<id>: <título de la decisión>

**Estado:** Propuesto
**Task relacionado:** TASK-<id>
**Fecha:** <fecha real>

## Contexto
Qué llevó a esta decisión (resume lo relevante de la investigación del task).

## Decisión
Qué se decidió hacer, en términos concretos.

## Alternativas consideradas
Cada alternativa evaluada con su trade-off principal. Si solo hubo una opción razonable, dilo y por qué.

## Estrategia de rollback / mitigación
Cómo se revierte o mitiga si algo falla. Si no aplica, justifica por qué.

## Consecuencias
Qué queda más fácil, qué queda más difícil, qué deuda técnica se acepta conscientemente (si alguna).
```

Si esta invocación **actualiza** una decisión arquitectónica ya tomada (por ejemplo, `delivery-review` encontró que la decisión era insuficiente), no borres el ADR anterior: cambia su `**Estado:**` a `Reemplazado por ADR-<nuevo-id>` y crea uno nuevo que referencie al anterior en `## Contexto`.

### 7. Actualizar el TASK

Actualiza `## Arquitectura` en `docs/tasks/TASK-<id>.md` enlazando el/los ADR creados, agrega la fila al historial de transiciones (`ARCHITECTURE → PLANNING`, motivo, `delivery-architect`), y actualiza `**Etapa actual:**` a `PLANNING`.

### 8. Reportar y detener

Resume la decisión y su justificación en el chat. Sugiere `/delivery-plan TASK-<id>` como siguiente paso. No implementes nada ni invoques `delivery-plan` tú mismo.

## Reglas

- No implementa código ni pseudocódigo de implementación detallado — eso es trabajo de `delivery-plan`/`delivery-engineer`.
- Toda decisión sensible (infra/auth/DB) lleva estrategia de rollback explícita o su justificación de por qué no aplica.
- Mantiene consistencia con ADRs previos salvo que la tarea justifique revisarlos explícitamente.
- No inventa restricciones del proyecto que no estén en `docs/CLAUDE.md` o en la investigación.

## Cuándo detenerse

- La investigación del task está incompleta.
- La decisión depende de información de negocio que no está en la investigación ni se puede inferir del código (pregunta al usuario en vez de asumir).

## Cuándo delega a otra skill

Siempre termina delegando a `delivery-plan` (nunca a `delivery-engineer` directamente, incluso si la decisión parece simple de implementar — el plan concreto sigue siendo responsabilidad de `delivery-plan`).

## Limitación de aislamiento de contexto

Si esta invocación ocurre en la misma sesión donde ya se corrió `delivery-investigate` para este task, hay continuidad de contexto real (no es una limitación grave: arquitectura construye intencionalmente sobre la investigación). La limitación de aislamiento entre roles que importa mitigar en este flujo es la de `delivery-review` respecto de `delivery-engineer` — ver `delivery-review`.
