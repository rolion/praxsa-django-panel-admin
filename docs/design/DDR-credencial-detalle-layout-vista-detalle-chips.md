# DDR-credencial-detalle-layout-vista-detalle-chips: Vista de detalle de credencial con chips de grupos y sucursales

**Estado:** Propuesto
**Task relacionado:** TASK-credencial-detalle-layout
**Fecha:** 2026-09-30

## Contexto

La vista `Ver credencial` (`panel_admin/src/app/users/view/user-view.component.html`) ya existe, con el breadcrumb pedido, pero muestra todo en una lista plana: estado como texto, y grupos/sucursales unidos por comas sin límite. El pedido llegó redactado para Tailwind CSS, pero `panel_admin/` usa Bootstrap 5.3 + SCSS de la plantilla y no tiene Tailwind (ver `## Investigación` del task). `reference.md` confirma que `panel_admin/` es Angular 21 standalone con `bootstrap ^5.3.8`. `AppUser` ya trae `groups[]` y `sucursales[]`, así que este DDR es solo de UI: sin cambios de API ni modelo.

## Pantallas/flujos afectados

- **Ver credencial** (`/users/view/:id`, existente, solo lectura): la persona revisa identidad, estado y asignaciones de un usuario, y puede ir a editarlo. No se crea ninguna pantalla nueva ni una página de "maqueta" aparte: el caso de más de 3 elementos es comportamiento real del componente.

## Componentes/patrones elegidos

- **Traducción Tailwind → Bootstrap:** se implementa con utilidades y componentes de Bootstrap 5.3 (ya instalado, ver `reference.md`, tabla de versiones), no se agrega Tailwind.
- **Layout:** `card` de la plantilla (mismo que `users-list`/`user-edit`, para consistencia) con `shadow-sm` y `rounded-3`; dentro `row` con dos `col-md-6` (una columna bajo `md`, dos desde `md`). Ancho de la card: `col-12` (ya no `col-lg-8`), porque el contenido ahora es de dos columnas.
- **Columna izquierda (identidad):** nombre completo (`first_name last_name`, con fallback a `username` si ambos están vacíos) como título `h4`; debajo el badge de estado, con las mismas clases que el listado (`badge bg-success` "Activo" / `badge bg-secondary` "Inactivo", `users-list.component.html:49-51`; los overrides de `assets/scss/override/_badge.scss` dan forma de píldora); luego una `dl` con Usuario, Correo, Teléfono (`—` si no hay). Se quitan las filas separadas Nombre/Apellido y Estado porque quedan absorbidas por título y badge.
- **Columna derecha (accesos):** dos bloques con etiqueta pequeña (`text-muted text-uppercase`), **Grupos** y **Sucursales**, cada uno con chips en `d-flex flex-wrap gap-2`.
  - Chips de grupos: `badge` con fondo `bg-primary-subtle text-primary-emphasis` (tonos azules).
  - Chips de sucursales: `badge` con `bg-info-subtle text-info-emphasis` y un icono `fa-store`/`fa-building` inicial (color e icono distintos: la distinción no depende solo del color).
  - Vacío: texto `text-muted` "Sin grupos" / "Sin sucursales" (ya existente, se conserva).
- **Límite y contador:** se muestran los primeros 3 chips por bloque. Si hay más, un chip contador `+N más` (elemento `<button type="button">` con estilo de badge neutro `bg-light text-dark border`) que al activarse expande la lista completa y pasa a "Ver menos". Con 3 o menos, no aparece contador. Lógica en el componente (helper que devuelve visibles/restantes por bloque), no en plantilla, para poder testearla.
- **Acción:** botón `btn btn-primary` "Editar" en la parte inferior izquierda de la card, separado por un `border-top` (`mt-4 pt-3`), hacia `/users/edit/:id` como hoy.
- **Estados de carga/error:** se mantienen (`Cargando...`, `alert alert-danger`).

## Alternativas consideradas

1. **Agregar Tailwind al proyecto** (fiel al pedido literal): descartada. Es una dependencia y un paso de build nuevos, con utilidades que se solapan con Bootstrap (`d-flex` vs `flex`, `badge`, resets) y riesgo de romper el resto de la plantilla; el beneficio es puramente de sintaxis. Consistencia con `users-list`/`user-edit` pesa más.
2. **Chips con SCSS propio** (clases `.chip-group`, `.chip-sucursal`): descartada por ahora; los `*-subtle` de Bootstrap 5.3 cubren el caso sin CSS nuevo. Se reconsideraría si el tema oscuro de la plantilla los renderiza mal (no verificado; ver riesgos).
3. **`+N más` solo informativo (con `title` nativo):** más simple, pero inaccesible en táctil y sin acción; se prefiere el toggle inline, que cuesta una variable booleana por bloque.
4. **`+N más` con popover de `ng-bootstrap`:** más pesado para una lista corta; se descarta salvo que las listas reales sean muy largas.
5. **Página de maqueta estática aparte:** descartada; el requerimiento de "versión con más de 3" se cubre con el comportamiento real y se verifica con datos de prueba/spec.

## Comportamiento por privilegio/estado

- El estado Activo/Inactivo cambia el badge (verde / gris). Sin grupos o sin sucursales cambia a texto neutro.
- El botón "Editar" hoy se muestra siempre; este DDR no introduce ocultarlo por privilegio. Si en el futuro se oculta o deshabilita según permiso, eso es solo UX: requiere que arquitectura/backend defina cómo se verifica el permiso de edición del lado servidor. El frontend no debe ser la única barrera.

## Consecuencias

- La vista queda visualmente más rica y consistente con el listado, sin dependencias nuevas.
- Se acepta que el pedido en Tailwind no se cumple a la letra; el resultado visual pedido sí.
- `user-edit` y `user-create` siguen con su presentación actual (formularios); si se quiere el mismo lenguaje de chips en el resumen del paso 4 del wizard, queda como tarea aparte.
- Falta verificar el render de los chips `*-subtle` con el tema oscuro y los colores de acento de la plantilla (`config.service.ts`); debe cubrirse en verificación manual.
- `UserViewComponent` no tiene spec: el plan debería agregar uno para el límite de 3, el contador y los estados vacíos.
