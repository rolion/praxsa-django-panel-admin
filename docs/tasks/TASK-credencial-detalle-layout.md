# TASK-credencial-detalle-layout: Rediseño de la vista de detalle de credencial (grupos y sucursales como chips)

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** SI
**Rama:** `claude/credential-detail-layout-248c24` (asignada por el entorno)
**Pull Request:** _pendiente de abrir_

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-09-30 | (nuevo) → INVESTIGATION | Task creado | delivery-investigate |
| 2026-09-30 | INVESTIGATION → PLANNING | Diseño decidido: Bootstrap 5 en lugar de Tailwind, card de 2 columnas, chips diferenciados con límite de 3 y toggle `+N más`; veredicto NEEDS_PLAN, no requiere arquitectura | delivery-design |
| 2026-09-30 | PLANNING → ENGINEERING | Plan v1 escrito (3 archivos frontend, spec nuevo, sin E2E ni dependencias); PR abierto sobre la rama asignada por el entorno | delivery-plan |

## Investigación

### Requerimiento
Maquetar la vista de detalle de una credencial de usuario (`Ver credencial > Icono > Credenciales`) en `panel_admin/`:
1. Breadcrumbs superiores.
2. Tarjeta principal blanca, sombra suave, bordes redondeados, 2 columnas en md/lg y 1 en móvil.
3. Izquierda: nombre completo como título, badge de estado dinámico (Activo en verde), datos personales (Usuario, Correo, Teléfono).
4. Derecha: **Grupos** como chips (estado neutro "Sin grupos"), **Sucursales** como chips de estilo distinto (estado neutro "Sin sucursales"), y límite de visualización: si hay más de 3 elementos, mostrar un chip contador (`+N más`).
5. Botón primario "Editar" (inferior izquierda o superior derecha).

El pedido está redactado para Tailwind CSS (ver hechos: el proyecto no usa Tailwind).

### Hechos encontrados
- `panel_admin/src/app/users/view/user-view.component.html:1-56` — la vista ya existe. Breadcrumb `Ver credencial` → icono `fa-users` (link a `/users`) → `Credenciales` (líneas 2-8); una sola card en `col-lg-8`; datos en un `<dl class="row">` de una columna (Usuario, Correo, Nombre, Apellido, Teléfono, Estado, Grupos, Sucursales); botón `btn btn-primary mt-3` "Editar" hacia `/users/edit/:id` (línea 51). El breadcrumb pedido ya coincide con el actual.
- `user-view.component.html:26` — Estado se muestra como texto plano (`Activo`/`Inactivo`), sin badge.
- `user-view.component.html:28-43` — Grupos y Sucursales se muestran como texto unido por comas (`groupNames.join(', ')`), sin chips ni límite; los estados vacíos "Sin grupos"/"Sin sucursales" ya existen con `text-muted`.
- `panel_admin/src/app/users/view/user-view.component.ts:1-46` — componente standalone; solo importa `RouterLink`; hace `forkJoin` de `getUser`, `listGroups`, `listSucursales` y resuelve IDs → nombres (`groupNames`, `sucursalNames`, líneas 26-37). Estados `loading` y `errorMessage`.
- `panel_admin/src/app/users/users.model.ts:1-13` — `AppUser` trae `first_name`, `last_name`, `email`, `username`, `phone_number: string | null`, `is_active`, `groups: number[]`, `sucursales: number[]`. Ya soporta múltiples grupos y sucursales; no hace falta cambio de API ni de modelo para la vista.
- `panel_admin/package.json:31,45` — la UI usa **Bootstrap 5.3.8** y `@ng-bootstrap/ng-bootstrap` 20; **no hay Tailwind** (`ls panel_admin/tailwind.config.*` y `postcss*` sin resultados; `grep tailwind package.json` sin resultados).
- `panel_admin/src/app/users/list/users-list.component.html:49-51` — el listado ya usa badges Bootstrap `badge bg-success` / `badge bg-secondary` para Activo/Inactivo (patrón a seguir para consistencia).
- `panel_admin/src/assets/scss/override/_badge.scss` — la plantilla tiene overrides propios de badge (no leído en detalle).
- No existe spec para `user-view` (`ls panel_admin/src/app/users/view` solo lista el `.html` y el `.ts`); sí existen specs de `users-list` y `user-create`.
- `panel_admin/src/app/users/users.routes.ts:15` — ruta `view/:id` → `UserViewComponent`, ya registrada.
- Historial: la vista fue creada en `4d8060c` y ajustada en `f5d4cc9`. Última migración backend: `0114_precio_venta_sucursal_unico.py` (no relevante: sin cambios de modelo).

### Hipótesis / supuestos no confirmados
- "Nombre completo" se asume `first_name + last_name`; no se verificó qué se muestra si ambos están vacíos (probable fallback a `username`).
- Se asume que "Usuario (Email)" y "Correo electrónico" del pedido son campos distintos (`username` y `email`); en el backend `username` puede no ser un email. No confirmado.
- Se asume que el pedido en Tailwind es una guía visual y no exige agregar Tailwind al proyecto; no confirmado con el usuario.
- "Maqueta una versión con más de 3 elementos" se interpreta como comportamiento real del componente (límite + chip `+N más`), y opcionalmente una vista de ejemplo; no confirmado si se quiere una página de maqueta estática aparte.
- Se desconoce si el chip `+N más` debe ser interactivo (expandir/tooltip) o solo informativo.
- El comportamiento de la vista con el tema oscuro de la plantilla (`right-sidebar.component.ts:64-80` maneja temas) no se verificó.

### Módulos y dependencias relacionadas
- Frontend únicamente: `panel_admin/src/app/users/view/` (componente a rediseñar), `users.model.ts`, `users.service.ts:27,52,76` (sin cambios previstos), estilos globales `panel_admin/src/assets/scss/` (badges/tema).
- Backend (`praxsa_manager/`) no interviene.

### Implementaciones similares existentes
- Badge de estado en `users-list.component.html:49-51`.
- `panel_admin/src/app/vehicles/brands/brands-list.component.ts:11` declara replicar el patrón de "Credenciales"; conviene no divergir visualmente de `users-list`/`user-edit` (misma breadcrumb y estilos de card).

### Comportamiento actual
La vista carga usuario, grupos y sucursales, y muestra todo en una lista de definición plana en una card de 8 columnas. No hay jerarquía visual (título/estado), ni chips, ni truncado de listas largas.

### Restricciones
- `docs/CLAUDE.md`: el proyecto tiene deuda técnica conocida; seguir los patrones existentes en vez de introducir nuevos.
- `docs/frontend/panel_admin/reference.md`: `panel_admin/` es Angular 21 standalone con Bootstrap/plantilla; no comparte código con `proforma/`.
- Introducir Tailwind implicaría una nueva dependencia de build y posible conflicto con Bootstrap (ambos definen utilidades solapadas) — no verificado empíricamente.

### Riesgos identificados
- Conflicto de tecnología: pedido en Tailwind vs. stack Bootstrap 5 actual.
- Sin spec para `UserViewComponent`; cambios de lógica (límite de chips, contador) quedan sin cobertura si no se agrega.
- Consistencia visual con tema oscuro/temas de color de la plantilla no verificada.
- Diferenciar colores de chips de grupos vs. sucursales debe funcionar con los temas de la plantilla y con accesibilidad de contraste.

### Veredicto de complejidad
**NEEDS_PLAN** — Cambio acotado a un único componente frontend existente, sin cambios de API, modelo, permisos ni de otros módulos. No requiere decisión arquitectónica nueva, salvo la cuestión Tailwind vs. Bootstrap, que es de diseño/UI y debe resolverse en `delivery-design`.

### Diseño requerido
**SI** — Es un rediseño de una pantalla con componentes nuevos (chips, badge de estado, contador `+N más`, layout de 2 columnas) que debe mantenerse consistente con la plantilla `panel_admin/`; además hay que decidir cómo traducir el pedido en Tailwind al stack Bootstrap.

## Diseño
- [DDR-credencial-detalle-layout-vista-detalle-chips](../design/DDR-credencial-detalle-layout-vista-detalle-chips.md) — Bootstrap 5 (no Tailwind), card 2 columnas, badge de estado, chips de grupos (azul) y sucursales (info + icono), límite 3 con toggle `+N más`, botón Editar inferior izquierdo.

## Arquitectura
_Pendiente / No aplica según veredicto_

## Plan
- [PLAN-2026-09-30-credencial-detalle-layout](../plans/PLAN-2026-09-30-credencial-detalle-layout.md) — v1

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
