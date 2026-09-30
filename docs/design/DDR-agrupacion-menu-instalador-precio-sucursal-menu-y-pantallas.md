# DDR-agrupacion-menu-instalador-precio-sucursal-menu-y-pantallas: Ubicación en el menú y pantallas de Instaladores y Precios por sucursal

**Estado:** Propuesto
**Task relacionado:** TASK-agrupacion-menu-instalador-precio-sucursal
**Fecha:** 2026-09-30

## Contexto

`instalador` (`praxsa_manager/product/models.py:131-137`) y `precio_venta_sucursal` (`models.py:328-334`) no tienen pantalla en `panel_admin/`; solo existen en el admin Django viejo. El usuario pidió decidir en qué grupo del menú van (o si se crea uno nuevo) y construir sus pantallas. El menú actual (`panel_admin/src/assets/data/routes.json`) tiene los grupos Usuarios, Vehículos, Almacén y Órdenes, armados por entidad de dominio. Precedentes de pantallas: `TASK-modulo-almacen`/`DDR-modulo-almacen-listado-y-flujo-almacen` (entidad simple = listado + modal; entidad rica = páginas separadas) y el listado simple de Sucursales (`panel_admin/src/app/users/sucursales/`).

## Pantallas/flujos afectados

1. **Menú**: se agrega la entrada **Instaladores** al grupo **Usuarios** y la entrada **Precios por sucursal** al grupo **Almacén**. No se crea un grupo nuevo.
2. **Instaladores — listado** (`/users/instaladores`): tabla con nombre, teléfono, dirección y sucursales; búsqueda; acciones Editar/Eliminar; botón "Nuevo instalador".
3. **Instaladores — crear/editar**: modal sobre el propio listado (nombre, dirección, teléfono, multiselección de sucursales).
4. **Precios por sucursal — listado** (`/almacen/precios-sucursal`): tabla con sucursal, lámina, ancho y precio de venta; búsqueda; acciones Editar/Eliminar; botón "Nuevo precio".
5. **Precios por sucursal — crear/editar**: modal sobre el listado (selects de sucursal y lámina, ancho, precio de venta). Sin pantalla de detalle propia: todos los campos ya se ven en la tabla.

## Componentes/patrones elegidos

- **Menú** (`routes.json`): solo se agregan dos objetos `submenu` con `"class": "ml-menu"` a grupos existentes, con la misma forma que las entradas actuales (p. ej. `/users/sucursales`). Patrón de menú anidado de la plantilla (`docs/frontend/panel_admin/reference.md`, fila "Multinivel").
- **Tablas**: `ngx-datatable` con filtro client-side, igual que Láminas/Bobinas/Sucursales (`reference.md`, fila `ngx-datatable` / `advance-table`). Ambos catálogos son pequeños (una sucursal tiene pocos instaladores y pocas combinaciones lámina/ancho), por lo que no se justifica paginación server-side.
- **Formularios**: `ReactiveFormsModule` en modal, mismo patrón que Marca/Item de Vehículos y Bobina de Almacén (entidades de catálogo simples, 3-4 campos, sin imagen). Validación con los estilos de `form-validation.html` (`reference.md`, categoría Formularios).
- **Multiselección de sucursales** (Instalador): `ng-select`, ya usado en el módulo Usuarios para grupos/sucursales.
- **Botones de tabla**: clases `btn-tbl-edit` / `btn-tbl-delete`; confirmación de borrado con SweetAlert2, igual que el resto de módulos.

## Alternativas consideradas

- **Grupo nuevo "Catálogos/Configuración" con ambas entradas.** Se descarta: agruparía dos entidades sin dominio común (personal vs. precios) solo por no tener otro lugar, y crearía un grupo con dos ítems que el criterio actual del menú (una entidad de dominio por grupo) no respalda.
- **Ambos en Almacén.** Se descarta: un instalador no es material ni stock. Solo el precio por sucursal depende de Láminas e inventario.
- **Ambos en Órdenes.** Se descarta: el uso en Nota de Trabajo es solo de lectura desde ese módulo; Órdenes agrupa documentos de venta, no catálogos.
- **Precios por sucursal dentro de Usuarios > Sucursales (como pestaña o sección).** Se descarta por ahora: convertiría un listado simple en una pantalla compuesta y el precio se define por lámina y ancho, no solo por sucursal.
- **Instaladores en Vehículos.** Se descarta: no tiene relación con marcas, modelos ni ítems (aunque `installation_price` sí vive en Vehículos > Items, es el precio, no la persona).
- **Páginas separadas (list/create/view/edit) en vez de modal.** Se descarta: son entidades simples sin imagen ni detalle adicional; el patrón "rico" sería sobreingeniería e inconsistente con Marca/Item/Bobina.
- **Aviso de nomenclatura**: existe un rol/grupo Django llamado `instalador` (`praxsa_manager/product/helper/user.py`) distinto de este modelo. La entrada se llama "Instaladores" (registros de personal de instalación), no "Instalador" a secas, y la pantalla no crea usuarios de login. Si negocio espera lo contrario, hay que reabrir este DDR.

## Comportamiento por privilegio/estado

El proyecto aún no define qué rol gestiona estas dos entidades (hipótesis abierta en la investigación). Comportamiento de UI propuesto, igual que Almacén:

| Perfil | Menú | Listado | Crear/Editar/Eliminar |
|---|---|---|---|
| Con permiso de modificar | Visible | Ve todo | Botones visibles |
| Solo lectura | Visible | Ve todo | Botones ocultos (no deshabilitados), igual que Láminas para `almacen` |
| Sin acceso | Entrada oculta si el mecanismo de roles del frontend lo permite | — | — |

Además, para Precios por sucursal el listado y los selects deberían mostrar solo las sucursales que le corresponden a la persona, según el comportamiento del admin viejo (`admin_config/precio_venta_sucursal.py`); el criterio exacto lo define arquitectura.

**Requiere que arquitectura defina** cómo se verifican del lado servidor: el permiso para gestionar cada entidad, el alcance por sucursal de Precios, la unicidad sucursal+lámina+ancho (hoy solo se valida en el admin viejo), y qué significa "eliminar" cuando un instalador ya está asignado a Notas de Trabajo (`Nota_trabajo.instaladar`, `on_delete=DO_NOTHING`, `models.py:207`; el modelo no tiene `is_active`). El frontend no debe ser la única barrera.

## Consecuencias

- Menú más simple: sin grupo nuevo, y cada entidad queda junto a lo que más usa (Instaladores con Sucursales/Credenciales, Precios con Láminas/Inventario).
- Se acepta que Usuarios pase a contener una entidad que no es una cuenta de login; se mitiga con el nombre "Instaladores" y esta nota.
- Almacén tendrá 4 entradas (Láminas, Bobinas, Inventario, Precios por sucursal).
- Quedan inconsistentes hasta que se arreglen: `installation_price` sigue en Vehículos > Items; y el textual "Sucursales" de Usuarios no muestra sus instaladores ni sus precios.
- Si negocio define que otros catálogos de configuración también necesitan su lugar, este DDR se puede reemplazar por uno que cree el grupo nuevo.
