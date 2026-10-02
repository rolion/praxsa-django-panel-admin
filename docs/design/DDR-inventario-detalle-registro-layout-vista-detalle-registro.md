# DDR-inventario-detalle-registro-layout-vista-detalle-registro: Vista de detalle de registro de inventario en dos columnas

**Estado:** Propuesto
**Task relacionado:** TASK-inventario-detalle-registro-layout
**Fecha:** 2026-10-02

## Contexto

`Ver inventario` (`panel_admin/src/app/almacen/inventario/inventario-view.component.html`) es una tarjeta `col-lg-8` con una `<dl>` plana de 14 filas, valores crudos (`'50.00'`, fecha ISO), estado como texto y el botón "Gestionar" al pie. El pedido pide: contenedor gris claro, tarjetas blancas redondeadas, cabecera con título + nombre del producto + solo "Editar" a la derecha, columna izquierda "Información General" (grid interno de 2 columnas) y columna derecha con "Métricas de Stock" y "Valores Financieros". `AppInventario` ya trae todos los datos (ver investigación); este DDR es solo de UI, sin cambios de API ni modelo. `reference.md` (tabla de versiones) confirma Angular 21 standalone + Bootstrap 5.3, así que se resuelve con Bootstrap + SCSS de la plantilla; no se agrega Tailwind.

## Pantallas/flujos afectados

- **Ver inventario** (`/almacen/inventario/view/:id`, existente, solo lectura): la persona consulta un registro (dónde está, cuánto stock queda, a qué precios) y, si tiene permiso, va a editarlo. No se crean pantallas nuevas ni se toca el listado, la edición ni la creación.

## Componentes/patrones elegidos

- **Breadcrumb:** se conserva (`page-title` "Ver inventario" + ícono de retorno al listado), igual que `user-view` y `lamina-view`. El título "Detalle de Registro" va en la cabecera del cuerpo.
- **Estilos base:** se reutiliza la raíz `.orden-view` (`assets/scss/_ordenes.scss:11,87`: `section-card`, `section-header`, `info-item`/`info-label`/`info-value`/`empty-value`), como ya hacen `nota-venta-view` y los reportes (`_reportes.scss:2-3`). Esos estilos usan fondos/bordes translúcidos (`rgba(128,128,128,…)`), por lo que sirven en tema claro y oscuro. Se agrega una clase `.inventario-view` en un parcial nuevo `assets/scss/_inventario.scss` (importado en `style.scss` junto a `_ordenes`, línea 37) solo para lo que no existe: contenedor gris y mosaicos de métricas. Raíz: `class="main-content orden-view inventario-view"`.
- **Contenedor gris claro:** el `section-body` lleva fondo `rgba(128,128,128,0.08)`, `border-radius: 12px`, `padding: 1.25rem`. Las tarjetas son `card section-card` (`border-radius: 12px`).
- **Cabecera (dentro del contenedor, sobre las columnas):** `d-flex justify-content-between align-items-start flex-wrap gap-2`. Izquierda: `h4` "Detalle de Registro" y debajo subtítulo `text-muted` con `window_film_name` (el "nombre del producto"). Derecha: único botón `btn btn-primary` **"Editar"** con ícono `fa-pen`, `routerLink` a `/almacen/inventario/edit/:id`, bajo `@if (canManage)`. No hay imprimir ni historial (no existen hoy).
- **Columnas:** `row g-4`; izquierda `col-lg-8`, derecha `col-lg-4`; bajo `lg` se apilan (Información General primero).
- **Información General (izquierda):** `section-card` con `section-header` (ícono `fa-info-circle`) y `card-body` con `row` de `col-6` (2 columnas incluso en móvil: valores cortos) usando `info-item`. Orden: Sucursal | Lámina; Ancho (`{{ bobina_width }} m`) | Nro. de Lote (`—` con `empty-value` si es nulo); Nro. de Referencia | Estado; y Fecha de Registro inmediatamente después de Estado. Si la celda sola en la última fila se ve desbalanceada, Estado y Fecha pueden ir en una fila final a ancho completo, siempre con Fecha justo tras Estado (ajuste de implementación).
- **Estado:** `badge bg-success` "Activo" / `badge bg-secondary` "Inactivo" (mismo patrón que `users-list`/`user-view`; overrides de píldora en `assets/scss/override/_badge.scss`).
- **Fecha:** `{{ inventario.date | date: 'dd/MM/yyyy - HH:mm' }} h`, el formato ya usado en `nota-venta-view.component.html:44`.
- **Métricas de Stock (derecha, arriba):** `section-card` compacta con grid 2×2 (`row g-2`, `col-6`) de mosaicos `.stat-tile` (fondo translúcido, `border-radius: 10px`, `padding: .75rem`), etiqueta pequeña en mayúsculas (estilo `info-label`) y valor grande (`1.5rem`, `fw-bold`). Orden: **Disponible**, Cantidad, Instalado, Longitud Inicial. "Disponible" es el destacado (valor en el acento `#4f6bed`, el de `section-header i`). Sufijo ` m` pequeño en Disponible/Instalado/Longitud Inicial; Cantidad sin unidad.
- **Valores Financieros (derecha, abajo):** `section-card` compacta con dos filas etiqueta/valor (`d-flex justify-content-between`): Precio de Compra y Precio de Venta (etiqueta aclara "por metro lineal"). Formato con `formatBs` de `calculadora/calculadora.helpers.ts:43` (es-BO, hasta 2 decimales), importado en el componente sin moverlo.
- **Estados de carga/error:** se mantienen `Cargando...` y `alert alert-danger`.

## Alternativas consideradas

1. **Agregar Tailwind** (jerga del pedido): descartada, igual que en DDR-credencial-detalle; dependencia y build nuevos, solapa con Bootstrap.
2. **Solo utilidades Bootstrap, sin SCSS:** descartada; el contenedor gris translúcido y los mosaicos destacados no salen con utilidades solas, y `bg-light` (`override/_misc.scss:107`) fuerza un gris fijo que en tema oscuro desentona. Costo del SCSS: un parcial pequeño.
3. **Clases `info-*` nuevas desde cero:** descartada; ya existen bajo `.orden-view`. Costo aceptado: la clase `orden-view` en Almacén no es semánticamente exacta (precedente en reportes).
4. **"Editar" al pie (como hoy):** descartada; el pedido lo ubica arriba a la derecha.
5. **Ancho junto al nombre del producto en la cabecera:** descartada; ya está en Información General.

## Comportamiento por privilegio/estado

- **Editar** solo con `change_inventario` (`canManage`, sin cambios de lógica); sin permiso la cabecera queda sin botón. Es solo UX: la verificación real del permiso la hace la API ya existente de edición; **el frontend no es la barrera de seguridad** y este DDR no pide cambios de backend ni de arquitectura.
- Activo → badge verde; Inactivo → gris. Lote nulo → `—` tenue.

## Consecuencias

- Pantalla más legible, con stock y precios agrupados.
- **Rótulo inconsistente aceptado:** el botón dice "Editar" (pedido), pero el listado conserva `title="Gestionar"` (`inventario-list.component.html:103`) y la pantalla destino se titula "Gestionar inventario", y solo edita 5 campos (por ADR de almacén). Unificar rótulos sería un ajuste menor posterior; ampliar campos editables sería otro task con arquitectura.
- **Formato numérico:** `DecimalPipe` usa `LOCALE_ID`; no se encontró `registerLocaleData`/`LOCALE_ID` en `panel_admin/src/app` (probablemente `en-US`: `1,234.50`), distinto de `formatBs` (es-BO). `delivery-plan` debe decidir si formatea las métricas con un helper `Intl` es-BO para coherencia. No verificado en ejecución.
- **Zona horaria de `date`:** sin confirmar (naive vs. `Z`); verificar con datos reales en review.
- **Tema oscuro:** el diseño usa fondos translúcidos para sobrevivir; confirmar visualmente en `delivery-review`.
- **Pruebas:** hoy no hay specs de contenido; el plan debe cubrir título/subtítulo, botón Editar según permiso, badge, `—` en lote nulo, formato de fecha y Bs.
- Otras vistas planas de Almacén (`lamina-view`) quedan con el estilo anterior; no se tocan.
