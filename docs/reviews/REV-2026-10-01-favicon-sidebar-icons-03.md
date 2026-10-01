# REV-2026-10-01-favicon-sidebar-icons-03: Plan v1 no refleja la ampliacion del logo del header de /calculadora

**Status:** Open
**Severity:** Low
**Category:** PLAN
**Related plan:** docs/plans/PLAN-2026-10-01-favicon-sidebar-icons.md (v1)
**Suggested owner:** delivery-plan

## Description
El commit `Usar el logo PRAXSA + 3M en el menu superior de la calculadora` toca `header.component.{html,spec.ts}`, `_calculadora.scss` y agrega `praxsa-3m-header-logo.jpg`, archivos que el plan v1 no lista. El cambio fue pedido expresamente por el usuario despues del primer PASS, pero el plan no tiene entrada de changelog.

## Expected behavior
Cambios de alcance reflejados en el plan versionado (v2 + Changelog).

## Actual behavior
Plan en v1, sin changelog; el TASK y el PR si documentan la ampliacion.

## Evidence
`git diff --stat HEAD~1` lista 5 archivos, 3 de ellos fuera de la seccion "Files/components affected" del plan.
