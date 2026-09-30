# TASK-pricing-calculator-screen: Pantalla "Calculadora de precios" para staff/asesores en panel_admin

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** `claude/pricing-calculator-screen-b5e976` (asignada por el entorno)
**Pull Request:** [#60](https://github.com/rolion/praxsa-django-panel-admin/pull/60)

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-09-30 | (nuevo) → INVESTIGATION | Task creado | delivery-investigate |
| 2026-09-30 | INVESTIGATION → ARCHITECTURE (via DESIGN) | Diseño de UI resuelto en DDR (layout sin sidebar, stepper, tabla de ítems, resumen sticky, estados); veredicto NEEDS_ARCHITECTURE exige decidir layout/rutas, cálculo de la cotización, paso de datos a la proforma y regla de "Recomendada" | delivery-design |
| 2026-09-30 | ARCHITECTURE → PLANNING | Decisiones tomadas en 2 ADR: layout mínimo como ruta hermana con variante del header, y cotización como vista previa en cliente con la API existente (sin backend), borrador por `history.state` hacia el formulario de proforma; "Recomendada" y WhatsApp por sucursal diferidos | delivery-architect |
| 2026-09-30 | PLANNING → ENGINEERING | Plan v1 escrito (solo frontend `panel_admin/`: layout mínimo, módulo `calculadora/`, preload del borrador en el formulario de proforma, ítem de menú; sin backend ni dependencias; sin E2E, con verificación manual en vivo); PR abierto sobre la rama asignada por el entorno | delivery-plan |

## Investigación

### Requerimiento
Prompt recibido (resumen fiel): implementar la pantalla de **Calculadora de Precios y Cotizaciones** de láminas de seguridad/polarizado para PRAXSA SRL, dirigida a staff y asesores, **reutilizando layout, barra superior y estilos de la plantilla administrativa existente** ("Tailwind CSS / Bootstrap / SCSS según corresponda"), en **Angular 15+** con componente standalone `PricingCalculatorComponent`.

- Sin sidebar/menú lateral en esta vista; solo barra superior con **logo PRAXSA a la izquierda** y **menú de perfil a la derecha**.
- Título "Calculadora de precios" con ícono de vehículo y **stepper de 3 pasos** (1. Vehículo, 2. Láminas, 3. Proforma).
- Card horizontal con 3 `<select>`: Sucursal, Marca, Modelo.
- Grid 70/30: izquierda, lista de ítems de cristales (ícono, nombre, subtítulo, select de lámina con badge "Recomendada", subtotal en `Bs`, botón eliminar/desactivar) + alerta al pie ("Los precios pueden variar según la disponibilidad de láminas…"); derecha, resumen sticky (imagen del vehículo, desglose, total destacado, botones "Crear Proforma" y "Consultar por WhatsApp").
- Estados de UI: inicial, cargando (skeletons), sin resultados, vista activa.
- `ReactiveForms`, recálculo automático de subtotal/total, `@for`/`@if`, interfaces `Branch`, `VehicleBrand`, `VehicleModel`, `WindowItem`, `FilmOption`, `QuoteSummary`, y comentarios donde conectar con APIs reales del backend de Praxsa.
- Entregables pedidos: `pricing-calculator.model.ts`, `pricing-calculator.component.ts`, `pricing-calculator.component.html`.

### Hechos encontrados
**Dos apps Angular distintas; la "plantilla administrativa" es `panel_admin/`**
- `panel_admin/package.json:17` Angular `^21.0.8`, Bootstrap `^5.3.8` (`:45`), `@ng-bootstrap/ng-bootstrap` 20, `angular-feather`, `@ngx-translate`. `proforma/package.json:22` Angular `^16.1.0`, Bootstrap `^5.2.3` (`:37`). Son proyectos separados (`docs/frontend/panel_admin/reference.md`, sección "Versiones reales").
- **No hay Tailwind** en `panel_admin/` (grep en `package.json`/`angular.json` sin resultados). El estilo es Bootstrap 5 + SCSS propio en `panel_admin/src/assets/scss/` (incluye `_ordenes.scss`, `_reportes.scss`, `_dashboard.scss`, `_custom.scss`). Las clases `grid grid-cols-12` / `col-span-8` del prompt son de Tailwind y no existen aquí; el equivalente es `row` / `col-lg-8` / `col-lg-4`.

**Layout y header**
- `MainLayoutComponent` monta siempre `<app-header>`, `<app-sidebar>` y `<app-right-sidebar>` + `<router-outlet>` (`panel_admin/src/app/layout/app-layout/main-layout/main-layout.component.html:1-6`). Todas las rutas autenticadas cuelgan de ese layout con `AuthGuard` (`panel_admin/src/app/app.routes.ts:7-67`). Existe además `AuthLayoutComponent` (solo login) (`app.routes.ts:69-74`). **No hay hoy un layout "solo header, sin sidebar".**
- El header actual (tras PR #59) tiene solo: toggle del sidebar, fullscreen y menú de usuario con nombre + Logout (`panel_admin/src/app/layout/header/header.component.html:1-30`). **No tiene logo**; el logo `assets/images/praxsa-admin-logo.png` vive en el sidebar (`sidebar.component.html:4-7`) y en el login (`signin.component.html:12`). El toggle del header depende del sidebar (`mobileMenuSidebarOpen`, `html:5-6`).

**Calculadora existente (cliente final) en `proforma/`**
- `proforma/src/app/pages/formulario/formulario.component.ts` (287 líneas) implementa la calculadora actual con formularios template-driven (`selectedSucursalId`, `selectedMarcaId`, `selectedModelId`), select de lámina por ítem (`addLamina`, `:201-229`), subtotal `largo × cantidad × precio_bobina + precio_instalación × cantidad` (`:238`), total (`:248-251`), botón WhatsApp `https://wa.me/+59178181012` (`formulario.component.html:133`) y "abrir proforma" en modal (`openModal`, `:278-281`).
- Usa endpoints públicos `calculator_info`, `model_parts/<id>` y `getInventario` (`praxsa_manager/product/urls.py:86-88`), con DataService de `proforma/` (Angular 16, módulos NgModule).

**Backend/API disponible para staff (consumido por `panel_admin/`)**
- Sucursales: `GET product/ordenes/catalogo/sucursales` (`urls.py:152`; `OrdenesService.listSucursales`, `panel_admin/src/app/ordenes/ordenes.service.ts:147-149`), filtrado al alcance del usuario.
- Bobinas (lámina + ancho) con stock y precio unitario por sucursal: `GET product/ordenes/catalogo/bobinas?sucursal=` (`urls.py:153`, `ordenes_admin.py:401-411`, `ordenes.service.ts:151-155`); devuelve `window_film`, `window_film_name`, `width`, `available_meters`, `unit_price` (`ordenes.model.ts:118-124`). Autenticación `TokenAuthentication` + `IsStaffUser` (`_STAFF_ONLY`, `ordenes_admin.py:43`).
- Marcas y modelos: `vehicles/brands`, `vehicles/models` (con `car_brand_id`, `image`), ítems del modelo `vehicles/models/<id>/items/` con `car_part_name`, `width`, `length`, `quantity`, `installation_price` (`urls.py:113-119`; `vehicles.service.ts:38,84-94`; `vehicles.model.ts:1-33`).
- Crear proforma: `POST product/ordenes/proformas` (`ordenes.service.ts:~45-47`); el servidor recalcula importes (ADR `ADR-modulo-ordenes-proforma-nota-trabajo-api-y-calculo`). Fórmula y validaciones en `praxsa_manager/product/business/pricing.py:86-93,113-181`; el ancho de lámina debe ser `>=` el ancho del ítem (`pricing.py:158-160`) y debe haber metros suficientes (`:162`, `:101-108`).
- Ya existe un formulario de proforma en `panel_admin`: `ProformaFormComponent` (`panel_admin/src/app/ordenes/proformas/proforma-form.component.ts:32-...`), ruta `/ordenes/proformas/create` (`ordenes.routes.ts:12`). Reutiliza `previewSubtotal`/`round2` (`ordenes.calc.ts:27-51`), exige datos de cliente (nombre, email, CI/NIT, teléfono, placa) (`proforma-form.component.ts:~100-115`) y arma líneas por bobina (clave `lámina|ancho`, `:reelKey`).
- Permisos de menú: `sidebar.metadata.ts` oculta ítems por `permission` (`:12-25`).

**Lo que NO existe en el código**
- No hay concepto de **lámina "Recomendada"** en backend ni en frontend (grep `recomend` sin resultados en `praxsa_manager/product`, `panel_admin/src`, `proforma/src`).
- No hay campo de "subtítulo" por ítem de cristal ni íconos por tipo de cristal (el ítem solo tiene `car_part_name`, `width`, `length`, `quantity`, `installation_price`: `vehicles.model.ts:24-33`).
- No hay un endpoint de "cotización" sin crear proforma: el precio por ítem hoy se calcula en cliente como vista previa (`ordenes.calc.ts:31-51`) y el definitivo solo aparece al persistir la proforma.
- No hay flujo "Consultar por WhatsApp" en `panel_admin/`; en `proforma/` es un enlace fijo al número `+59178181012` sin mensaje.
- El prompt menciona `Toyota Hilux` como imagen de ejemplo; `AppCarModel.image` existe (`vehicles.model.ts:19-22`) pero puede ser `null` (`models.py:29`, `null=True`).
- No hay un stepper de 3 pasos en `panel_admin/` (no verificado exhaustivamente; existe `angular-archwizard` en `package.json`, sin evidencia de uso aquí).

### Hipótesis / supuestos no confirmados
- **Dónde vive la pantalla:** se asume `panel_admin/` (Angular 21, standalone) porque es la "plantilla administrativa" con Navbar/sidebar y usuarios staff. La mención "Angular 15+", "`<app-navbar>`" y "Tailwind" en el prompt es genérica y no coincide con el repo (selector real `app-header`, Bootstrap/SCSS). No se confirmó con el usuario.
- **Quién es "staff y asesores":** se asume usuarios ya autenticados en `panel_admin` con sucursal asignada y `IsStaffUser`; no se verificó si los "asesores" tienen el permiso `add_proforma_header` para el botón "Crear Proforma".
- Se asume que "Crear Proforma" debe **llevar al formulario existente** o crear la proforma con datos del cliente solicitados después (paso 3 del stepper); no hay evidencia de qué se espera (¿modal con datos del cliente?, ¿navegar a `/ordenes/proformas/create` precargado?). Es decisión de diseño/arquitectura.
- "Recomendada" podría derivarse de una regla de negocio (p. ej. lámina más vendida o con stock); no hay definición en el código ni en docs revisados.
- "Eliminar/desactivar" ítem: en `proforma/` `removeReportItem` solo pone en 0 el ítem (`formulario.component.ts:187-199`); se asume la misma semántica (excluir del total), sin confirmar.
- La ruta sin sidebar podría resolverse con un layout nuevo, un flag en `MainLayoutComponent` o un parámetro de ruta; no se evaluaron alternativas (trabajo de diseño/arquitectura).
- No se verificó si el número de WhatsApp debe ser configurable por sucursal.
- No se verificó el estado del backend de desarrollo ni las suites de test frontend de `panel_admin/` tras este cambio (hay 15 fallas preexistentes según `TASK-login-panel-admin-backend.md:148`, citado por `TASK-appheader-nav-cleanup.md`).

### Módulos y dependencias relacionadas
- Frontend `panel_admin/src/app/`: `layout/app-layout/main-layout`, `layout/header`, `layout/sidebar`, `app.routes.ts`, `ordenes/` (servicio, cálculo, modelo, proforma-form), `vehicles/` (servicio, modelo), `core/` (auth, permisos), SCSS `assets/scss/_ordenes.scss` y `_custom.scss`, sidebar (`sidebar.metadata.ts`).
- Backend `praxsa_manager/product/`: `custom_views/ordenes_admin.py`, `business/pricing.py`, `urls.py`, `serializer/`. Posible ampliación solo si se decide un endpoint de cotización o "recomendada" (no decidido).
- `proforma/` (cliente final): referencia funcional de la calculadora; **no** se toca a priori.

### Implementaciones similares existentes
- `ProformaFormComponent` (`panel_admin/.../proforma-form.component.ts`): mismo dominio (sucursal → modelo → ítems → bobinas → total, vista previa cliente vs servidor), reactive forms con `FormArray`, servicios `OrdenesService`/`VehiclesService`, SCSS de tarjetas por sección en `assets/scss/_ordenes.scss` y panel de referencia de medidas.
- `FormularioComponent` (`proforma/.../formulario.component.ts`) como fuente de la lógica de cálculo y del botón WhatsApp.
- DDRs de pantallas del panel, p. ej. `docs/design/DDR-modulo-ordenes-proforma-nota-trabajo-listado-y-flujo-ordenes.md`, como referencia de patrones visuales.

### Comportamiento actual
Hoy un asesor arma una cotización creando directamente una proforma en `/ordenes/proformas/create`: debe llenar datos del cliente y elegir bobina por línea en un formulario denso; no existe una vista de "cotizar primero" con stepper, resumen sticky ni imagen del vehículo. El cliente final usa la calculadora de `proforma/` (Angular 16) con endpoints públicos. El layout de `panel_admin` siempre incluye sidebar.

### Restricciones
- `docs/CLAUDE.md`: cambios pequeños/un objetivo por PR, dinero con `Decimal` (en front, strings del API), lógica de negocio con tests, "No agregar dependencias sin avisar" (p. ej. Tailwind sería una dependencia nueva y es ajeno a `panel_admin/`), proponer plan antes de tocar varios archivos, no tocar `.env`.
- El precio mostrado en cliente es solo vista previa; el servidor recalcula (ADR-004 y `ADR-modulo-ordenes-proforma-nota-trabajo-api-y-calculo`).
- Alcance por sucursal y permisos Django por acción (`ADR-modulo-ordenes-proforma-nota-trabajo-alcance-permisos`).
- Suite frontend con 15 fallas preexistentes ajenas.

### Riesgos identificados
- **Desalineación prompt vs repo** (Angular 15+/Tailwind/`app-navbar`/`grid-cols` vs Angular 21 standalone/Bootstrap/`app-header`): implementarlo literal rompería la coherencia con la plantilla.
- **Datos que no existen**: "Recomendada", subtítulo e íconos por cristal requieren decisión de negocio/datos (¿campo nuevo en modelo? ¿regla derivada? ¿solo UI?).
- **Precio por ítem depende del ancho de bobina** (`pricing.py:158-160`): un select de "lámina" por ítem debe mapear a bobinas con ancho suficiente; el "precio por lámina" del dropdown no es un único valor por lámina.
- **Layout sin sidebar**: `MainLayoutComponent` está acoplado a sidebar/right-sidebar y al toggle del header; hay que decidir cómo variar el layout sin romper el resto de pantallas.
- **Duplicación de lógica** con `ProformaFormComponent` y `formulario.component.ts` (tres lugares calculando subtotales) si no se reutiliza `ordenes.calc.ts`.
- **"Crear Proforma"** exige datos de cliente obligatorios (`proforma-form.component.ts:~100-115`); el flujo entre paso 2 y 3 no está definido.
- Sin tests propios del área nueva; las 15 fallas preexistentes dificultan distinguir regresiones.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — La tarea agrega una pantalla/layout nuevo en un módulo con impacto en varios archivos (layout, rutas, header, sidebar/permisos, SCSS global), y tiene decisiones abiertas de arquitectura: cómo variar el layout sin sidebar, dónde se calcula la cotización (cliente vs endpoint nuevo), cómo se modela "Recomendada" (posible cambio de modelo/API) y cómo se conecta con la creación de proforma. Ante la duda entre NEEDS_PLAN y NEEDS_ARCHITECTURE se prefiere la segunda.

### Diseño requerido
**SI** — Pantalla nueva de varios pasos (stepper, card de filtros, grid 70/30 con sticky, estados inicial/cargando/vacío) y adopción de componentes de la plantilla `panel_admin/` (`docs/frontend/panel_admin/reference.md`); debe definirse visualmente con criterio para no quedar inconsistente con las pantallas de `ordenes/`.

## Diseño
- [DDR-pricing-calculator-screen-pantalla-calculadora](../design/DDR-pricing-calculator-screen-pantalla-calculadora.md) — pantalla única sin sidebar (header mínimo con logo + perfil), stepper propio de 3 pasos derivado del estado, tabla Bootstrap de ítems con select de lámina apta por ítem, resumen sticky con Crear Proforma (lleva al formulario existente precargado) y WhatsApp con mensaje prearmado, estados inicial/cargando/sin resultados/error.

**Pendientes de negocio (no resolubles desde el código):** regla de "Recomendada", número de WhatsApp (global vs. por sucursal), texto/formato de importes y ubicación de la entrada al menú.

## Arquitectura
- [ADR-pricing-calculator-screen-layout-sin-sidebar](../adr/ADR-pricing-calculator-screen-layout-sin-sidebar.md) — `MinimalLayoutComponent` + ruta hermana `calculadora`; `app-header` con variante mínima (logo, sin toggle de sidebar) vía `input()` con default que preserva el comportamiento actual; offset del sidebar neutralizado con clase propia.
- [ADR-pricing-calculator-screen-cotizacion-en-cliente](../adr/ADR-pricing-calculator-screen-cotizacion-en-cliente.md) — sin cambios de backend; total como vista previa con `ordenes.calc.ts`; `ReactiveForms` + signals en `calculadora/`; borrador por `history.state` al formulario de proforma; permiso `add_proforma_header` solo como UX; WhatsApp con número global en `environment`; "Recomendada" diferida.

**Rollback:** ambos cambios son aditivos (sin migraciones ni cambios de contrato); basta quitar la ruta/ítem de menú y la lectura opcional del borrador.

## Plan
- [PLAN-2026-09-30-pricing-calculator-screen](../plans/PLAN-2026-09-30-pricing-calculator-screen.md) — **v1**. 5 fases (layout, modelo/helpers/servicio, pantalla, acciones y enlace con la proforma, entrada y verificación). Preguntas abiertas no bloqueantes: número de WhatsApp, ubicación en el menú y formato de importes.

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
