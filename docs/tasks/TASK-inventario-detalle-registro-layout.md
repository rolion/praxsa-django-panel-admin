# TASK-inventario-detalle-registro-layout: Rediseño de la vista de detalle de registro de inventario (dos columnas, métricas y valores)

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** SI
**Rama:** `claude/inventory-record-detail-e97b4e` (asignada por el entorno)
**Pull Request:** [#70](https://github.com/rolion/praxsa-django-panel-admin/pull/70)

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-02 | (nuevo) → INVESTIGATION | Task creado | delivery-investigate |
| 2026-10-02 | INVESTIGATION → PLANNING | Diseño decidido: Bootstrap + SCSS (no Tailwind), reutiliza `.orden-view`, contenedor gris translúcido, métricas en mosaicos, "Editar" en cabecera; NEEDS_PLAN, no requiere arquitectura | delivery-design |
| 2026-10-02 | PLANNING → ENGINEERING | Plan v1 escrito (solo frontend: plantilla, componente, parcial SCSS y spec; sin E2E ni dependencias) y PR #70 abierto sobre la rama asignada por el entorno; a la espera de aprobación humana del plan | delivery-plan |
| 2026-10-02 | ENGINEERING → REVIEW | Implementación completa del plan v1 (plantilla, componente, parcial SCSS y specs) | delivery-engineer |
| 2026-10-02 | REVIEW → ENGINEERING | Quality Gate FAIL: REV-2026-10-02-inventario-detalle-registro-layout-01 (Medium, título ilegible en tema oscuro) | delivery-review |
| 2026-10-02 | ENGINEERING → REVIEW | REV-01 corregido: el título recibe color propio en `body.dark` (clase `inventario-title`) | delivery-engineer |

## Investigación

### Requerimiento
Estructurar la vista de detalle de un registro de inventario (pedido redactado como "desarrollador Frontend Senior UI/UX"):
1. Layout en dos columnas para escritorio, contenedor de fondo gris claro, tarjetas blancas con bordes redondeados, tipografía limpia y jerarquizada.
2. Cabecera: título dinámico "Detalle de Registro" + nombre del producto; a la derecha **solo** el botón principal "Editar" (sin imprimir, historial ni otros secundarios).
3. Columna izquierda (principal): tarjeta **Información General** con grid interno de 2 columnas: Sucursal, Lámina, Ancho, Número de Lote, Número de Referencia, Estado (etiqueta verde para Activo) y Fecha de Registro justo debajo del Estado, con formato de fecha legible.
4. Columna derecha: dos tarjetas compactas apiladas: **Métricas de Stock** (numérico destacado: Disponible, Cantidad, Instalado, Longitud Inicial) y **Valores Financieros** (Precio de Compra, Precio de Venta).

### Hechos encontrados
- `panel_admin/src/app/almacen/inventario/inventario-view.component.html:1-54` — la vista actual (`/almacen/inventario/view/:id`, ruta en `almacen.routes.ts:19`) es una sola `card` dentro de `col-lg-8` con una `<dl class="row">` plana de 14 filas (`dt col-sm-3` / `dd col-sm-9`): Sucursal, Lámina, Ancho, Cantidad, Disponible, Instalado, Longitud inicial, Fecha, Nro. referencia, Precio compra, Precio venta, Nro. lote, Estado.
- `inventario-view.component.html:5` — el título hoy es "Ver inventario" en el breadcrumb (`page-title`), no hay encabezado propio con el nombre del producto.
- `inventario-view.component.html:46-48` — el botón se llama **"Gestionar"** (no "Editar"), visible solo con `canManage`, enlaza a `/almacen/inventario/edit/:id`. `inventario-view.component.ts:20-22` — `canManage` = `hasPermission('change_inventario')`; el spec lo cubre (`inventario-view.component.spec.ts:61-72`).
- `inventario-view.component.html:34,37,40,43` — todos los valores se imprimen crudos (strings decimales del API como `'50.00'`, `date` sin pipe: se vería ISO `2026-09-27T00:00:00Z`); `:43` estado como texto plano "Activo"/"Inactivo", sin badge.
- No existen hoy botones de imprimir ni historial en esta vista (el pedido de "eliminar" secundarios no tiene nada que quitar). El listado tiene sus propias acciones (`inventario-list.component.html:103`, botón "Gestionar" con `title`).
- `panel_admin/src/app/almacen/almacen.model.ts:19-36` — `AppInventario` ya trae todos los campos necesarios: `sucursal_name`, `window_film_name`, `bobina_width`, `quantity`, `to_install`, `installed`, `original_length`, `date`, `numero_referencia`, `precio_compra_mtr_lineal`, `precio_venta_mtr_lineal`, `nro_lote` (nullable), `is_active`. No hay "nombre del producto" aparte: el equivalente es `window_film_name` (lámina).
- `praxsa_manager/product/serializer/almacen_serializer.py:57-79` — `InventarioSerializer` expone exactamente esos campos; no se requiere cambio de API para el pedido. `models.py:141-154` — `date` es `DateTimeField`, `nro_lote` es `null=True`, `is_active` default `True`.
- `praxsa_manager/praxsa_manager/settings.py:196,200` — `TIME_ZONE='America/La_Paz'`, `USE_TZ=False` (fechas naive en el servidor).
- Patrón visual existente para vistas de solo lectura: `.orden-view` con `section-card`/`info-label`/`info-value`/`empty-value` en `panel_admin/src/assets/scss/_ordenes.scss:84-111` (las clases están **anidadas bajo `.orden-view`**, no son globales); usado en `ordenes/notas-venta/nota-venta-view.component.html:1,14-45`. Formato de fecha ya usado en el proyecto: `{{ x | date: 'dd/MM/yyyy - HH:mm' }} h` (`nota-venta-view.component.html:44`).
- `docs/design/DDR-credencial-detalle-layout-vista-detalle-chips.md` — precedente directo de rediseño de una vista de detalle: Bootstrap 5.3 (no Tailwind), `card` con `shadow-sm rounded-3`, `row` + `col-md-6`, badge de estado `badge bg-success`/`bg-secondary` (como `users-list.component.html:49-51`; overrides de píldora en `assets/scss/override/_badge.scss`), botón `btn btn-primary` "Editar". `docs/frontend/panel_admin/reference.md` confirma Angular 21 standalone + `bootstrap ^5.3.8`.
- `docs/design/DDR-modulo-almacen-listado-y-flujo-almacen.md:19-22,55` — Inventario es "entidad rica" con páginas `list/create/view/edit`; la edición ("Gestionar") está acotada a 5 campos (`to_install`, `installed`, `precio_compra_mtr_lineal`, `precio_venta_mtr_lineal`, `nro_lote`) por decisión de arquitectura (`InventarioUpdateSerializer`, `almacen_serializer.py:82-95`).
- Vista hermana ya existente con el mismo patrón plano: `laminas/lamina-view.component.html:1-47` (botón "Editar" aquí sí).
- Tests del área: `inventario-view.component.spec.ts` (3 pruebas: carga, error, `canManage`); no hay pruebas de contenido renderizado de la plantilla.

### Hipótesis / supuestos no confirmados
- "Nombre del producto" = `window_film_name`; podría querer "Lámina + ancho". No confirmado con el usuario.
- La fecha del API llega naive (sin `Z`) por `USE_TZ=False`; el sample del spec usa `Z`. Si llegara con `Z`, `DatePipe` la convertiría a hora local del navegador y podría correr el día. No se verificó la respuesta real del endpoint.
- Renombrar "Gestionar" → "Editar" es coherente con lo pedido, pero la pantalla destino sigue editando solo 5 campos (no Sucursal/Lámina/Ancho/Referencia/Fecha). No se confirmó si el usuario espera ampliar la edición (sería otro task, con impacto de arquitectura según el DDR/ADR de almacén).
- "Etiqueta verde para Activo": se asume que Inactivo se muestra con un estilo neutro/gris (el pedido no lo define).
- Tema oscuro de la plantilla: "tarjetas blancas / fondo gris claro" puede verse mal en tema oscuro; no verificado.
- No se confirmó si hay formato esperado de moneda/unidades (Bs, "m") en los números; el pedido solo pide "numérico destacado".

### Módulos y dependencias relacionadas
- Frontend `panel_admin/` (Angular 21): `almacen/inventario/inventario-view.component.{ts,html,spec.ts}`, `almacen.model.ts`, `almacen.service.ts` (`getInventario`), SCSS en `assets/scss/`.
- Backend `praxsa_manager/product/` solo como contrato (serializador de solo lectura); sin cambios requeridos.
- `proforma/` (app cliente) no está involucrado.

### Implementaciones similares existentes
- `users/view/user-view.component` (ver DDR credencial) y `ordenes/notas-venta/nota-venta-view.component` (secciones `section-card` con `info-grid`); `almacen/laminas/lamina-view.component` (vista hermana).

### Comportamiento actual
La pantalla muestra una única tarjeta angosta (`col-lg-8`) con lista de definiciones plana, sin jerarquía visual, sin agrupar stock/precios, estado y fecha sin formato, y el botón "Gestionar" al pie de la tarjeta (no en la cabecera).

### Restricciones
- `docs/CLAUDE.md`: proyecto con deuda técnica; no asumir por nombres; el panel es `panel_admin/` (Bootstrap, no Tailwind).
- Mantener visibilidad del botón por permiso `change_inventario` (`inventario-view.component.ts:20-22`); el frontend no es la única barrera (la API valida).
- Sin migraciones ni cambios de modelo (última migración `0115_client_car_plate.py`).

### Riesgos identificados
- Las clases `.info-*` están acotadas a `.orden-view`; reutilizarlas fuera de ese contenedor no aplica estilo.
- Cobertura de pruebas de la plantilla casi nula: un rediseño puede romper el contenido sin que ningún spec falle.
- Fecha/zona horaria (ver hipótesis) y tema oscuro sin verificar.
- Rótulo "Editar" sobre una edición parcial puede generar expectativas distintas en usuarios.

### Veredicto de complejidad
**NEEDS_PLAN** — Cambio acotado a un componente de frontend (plantilla, posible SCSS y spec), sin cambios de API, modelo, permisos ni decisión arquitectónica nueva.

### Diseño requerido
**SI** — Cambia de forma no trivial la superficie de UI de una pantalla existente (layout de dos columnas, tarjetas, jerarquía numérica, badge), con decisiones a comparar (reutilizar `.orden-view`/`info-*` vs. estilos propios, escala de métricas, comportamiento responsive, tema oscuro).

## Diseño
- [DDR-inventario-detalle-registro-layout-vista-detalle-registro](../design/DDR-inventario-detalle-registro-layout-vista-detalle-registro.md) — layout 8/4 columnas, cabecera con "Editar" (solo con `change_inventario`), Información General en grid de 2 columnas con Fecha bajo Estado, Métricas de Stock en mosaicos 2×2 (Disponible destacado), Valores Financieros con `formatBs`. Solo frontend; sin cambios de API.

## Arquitectura
_No aplica según veredicto_

## Plan
- [PLAN-2026-10-02-inventario-detalle-registro-layout](../plans/PLAN-2026-10-02-inventario-detalle-registro-layout.md) — **v1**.

## Implementación
Implementado según plan v1 y DDR, solo frontend (`panel_admin/`), commit `0fc62a5`:
- `inventario-view.component.html` reescrita: cabecera (título, nombre de la lámina, único botón Editar bajo `canManage`), Información General en grid de 2 columnas (Fecha de registro bajo Estado mediante `offset-6`), Métricas de Stock en mosaicos 2x2 (Disponible destacado) y Valores Financieros con `formatBs`.
- `inventario-view.component.ts`: `DatePipe`, `formatBs` (importado de `calculadora/calculadora.helpers`) y `formatMeters` (`Intl` es-BO).
- `assets/scss/_inventario.scss` nuevo, importado en `style.scss`; reutiliza `.orden-view`.
- Spec: 9 pruebas nuevas de render (título, orden Estado→Fecha, badges, lote nulo, métricas/Bs, `formatMeters`, Editar con y sin permiso); las 3 existentes se mantienen.
- Verificación propia (no es el Quality Gate): spec de la vista 12/12, `ng lint` y `ng build` limpios.

Notas: (1) las dos preguntas abiertas del plan (nombre del producto = solo lámina; prefijo `Bs`) se implementaron con los supuestos del plan, sin respuesta del usuario. (2) Quedan para review la verificación visual (responsive, tema oscuro) y la zona horaria de `date`. (3) Deuda señalada: dependencia `almacen` → `calculadora` por `formatBs`.
**Corrección de REV-01** (tema oscuro): el `h4` de la cabecera recibe la clase `inventario-title` y una regla `body.dark .inventario-view .inventario-title { color: #fff }` en `_inventario.scss`; el spec comprueba la clase. Verificado en el stack local en tema oscuro (color computado `rgb(255,255,255)`); spec de la vista 13/13 y `ng lint` limpios (verificación propia).

## Review
**Resultado: FAIL** (corrida 1, 2026-10-02; ejecutada en la misma sesión que la implementación, aislamiento solo procedimental).
- Issue abierto: [REV-2026-10-02-inventario-detalle-registro-layout-01](../reviews/REV-2026-10-02-inventario-detalle-registro-layout-01.md) — Medium, IMPLEMENTATION: título "Detalle de Registro" negro e ilegible en tema oscuro (criterio de aceptación de tema oscuro no cumplido).
- Verificado OK: suite completa de `panel_admin` 510/523, con 13 fallas idénticas a la línea base de master (501 OK + 9 nuevas; todos specs "should create" de la plantilla demo, ajenos al cambio); `ng lint` limpio; `ng build` OK (aviso de selectores SCSS ajeno al cambio); cobertura de `inventario-view.component.ts` 100%; sin cambios en `package*.json` (`npm audit` reporta hallazgos preexistentes de dependencias); fecha del API sin `Z` y mostrada sin desfase; layout correcto en escritorio y móvil, tema claro.

## Publicación
_Pendiente_
