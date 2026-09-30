# PLAN-2026-09-30-pricing-calculator-screen (v1)

**Task:** TASK-pricing-calculator-screen
**DDRs relacionados:** [DDR-pricing-calculator-screen-pantalla-calculadora](../design/DDR-pricing-calculator-screen-pantalla-calculadora.md)
**ADRs relacionados:** [ADR-pricing-calculator-screen-layout-sin-sidebar](../adr/ADR-pricing-calculator-screen-layout-sin-sidebar.md), [ADR-pricing-calculator-screen-cotizacion-en-cliente](../adr/ADR-pricing-calculator-screen-cotizacion-en-cliente.md)

## Objective

Que un asesor pueda cotizar una instalación sin capturar datos del cliente: elegir sucursal, marca y modelo, elegir una lámina por cristal, ver el total y luego crear la proforma (con los datos ya cargados) o consultar por WhatsApp. La pantalla se presenta sin sidebar, con logo a la izquierda y perfil a la derecha.

## Context

Ver TASK-pricing-calculator-screen (investigación, DDR y 2 ADR). Es **solo frontend `panel_admin/`**: no hay cambios de backend, modelos ni migraciones.

**Nota de verificación (código vigente al planificar):** se comprobó que siguen igual `MainLayoutComponent` (`layout/app-layout/main-layout/main-layout.component.html:1-3`), `app.routes.ts` (layout principal y `authentication` como rutas hermanas), `header.component.html` (toggle del sidebar en `:4-8`, menú de usuario), `ordenes.calc.ts:27-51`, `OrdenesService.listSucursales/listBobinas` (`ordenes.service.ts:147-155`), `VehiclesService.listBrands/listModels/listModelItems` (`vehicles.service.ts:38,84,132`) y `ProformaFormComponent` (`onSucursalesLoaded`, `loadCatalog`, `loadItems`, `save`). Dos precisiones frente a la investigación: (1) el menú lateral **no** sale de código sino de `panel_admin/src/assets/data/routes.json` (con `submenu`, sin filtro por permiso en el ítem existente de Órdenes; `filterByPermission` ya soporta `permission` opcional, `sidebar.metadata.ts:12-25`); (2) `ProformaFormComponent` ya tiene `reelKey(windowFilm, width)` y las advertencias `widthWarning`/`stockWarning` (`proforma-form.component.ts:~208,~363-385`) que conviene no duplicar.

Rama: se usa la rama asignada por el entorno `claude/pricing-calculator-screen-b5e976` (mismo criterio que TASK-appheader-nav-cleanup), no `task/TASK-...`.

## Current behavior

- Un asesor arma una cotización creando una proforma en `/ordenes/proformas/create` (`ordenes.routes.ts:12`): formulario con datos de cliente obligatorios (`proforma-form.component.ts:~94-107`) y tabla de líneas. No hay vista de "cotizar primero".
- Todas las pantallas autenticadas muestran el sidebar (`main-layout.component.html:2`); el header no tiene logo (`header.component.html:1-30`) y su toggle opera el sidebar (`:5-6`).
- El importe en vista previa se calcula con `previewSubtotal` (`ordenes.calc.ts:34-51`); el servidor recalcula al guardar (`business/pricing.py`, ADR-004).
- El menú lateral se alimenta de `assets/data/routes.json` (`sidebar.service.ts:17-22`).

## Expected behavior

- `/calculadora` (ruta protegida por `AuthGuard`) muestra un header con logo + perfil, sin sidebar, y la pantalla descrita en el DDR: stepper de 3 pasos, card de filtros (Sucursal/Marca/Modelo), tabla de ítems con select de lámina apta y subtotal, resumen sticky y estados inicial/cargando/sin resultados/error.
- Al elegir láminas el subtotal por ítem y el total se recalculan solos; "Quitar" excluye un ítem y se puede restaurar.
- "Crear Proforma" (solo con permiso `add_proforma_header`) abre `/ordenes/proformas/create` con sucursal, modelo y líneas precargados; "Consultar por WhatsApp" abre `wa.me` con un mensaje con vehículo, ítems y total.
- Las demás pantallas siguen exactamente igual (sidebar, header con toggle, sin logo).

## Architecture considerations

Resumen de los ADR (no se re-decide):
- **Layout:** layout mínimo + ruta hermana + variante del header por `input()` (default sin cambios); offset del sidebar neutralizado con clase propia. Aditivo; rollback = quitar ruta y menú.
- **Cotización:** vista previa en cliente con `ordenes.calc.ts`, APIs existentes, sin backend. Filtro de aptitud de láminas como UX (ancho ≥ ancho del ítem y metros suficientes, espejo de `pricing.py:158-162`); el servidor sigue validando.
- **Borrador → proforma:** `history.state` con clave y versión; ausente/inválido ⇒ formulario vacío como hoy. Sin `localStorage` (ADR-003).
- **Permisos:** `add_proforma_header` solo oculta el botón (`AuthService.hasPermission`, `auth.service.ts:81-84`); la barrera real es el `POST` existente. Los catálogos ya están acotados al alcance por sucursal.
- **Dinero:** los importes llegan del API como strings; la vista previa usa `Number` igual que `ordenes.calc.ts`/`ProformaFormComponent` (no autoritativo). No se persiste ni se envía al servidor ningún importe calculado: el `POST` manda solo lámina/ancho/largo/cantidad y el servidor calcula en `Decimal`.
- **Rendimiento:** una sola carga de bobinas por sucursal y de ítems por modelo; el filtro de aptitud es O(ítems × bobinas) en memoria (decenas de filas); total vía `computed`.
- **Acoplamiento:** el único archivo existente con lógica que se toca es `ProformaFormComponent` (preload opcional del borrador); `HeaderComponent` recibe un `input()` con default inocuo; `routes.json` recibe un ítem.

## Proposed solution

Nuevo módulo `panel_admin/src/app/calculadora/` (standalone, carga diferida) con componente de pantalla, pequeños componentes presentacionales solo si aportan claridad (stepper y resumen), helpers puros para aptitud/mensaje de WhatsApp/borrador y un servicio-fachada. `MinimalLayoutComponent` en `layout/app-layout/`. Variante `minimal` en `HeaderComponent`. Lectura opcional del borrador en `ProformaFormComponent`. Ítem de menú en `routes.json`. El número de WhatsApp sale de `environment.whatsappNumber` (valor inicial: el que hoy usa `proforma/`, `+59178181012`, a confirmar).

## Files/components affected

**Frontend `panel_admin/` (nuevos)**
- `src/app/layout/app-layout/minimal-layout/minimal-layout.component.{ts,html}` (+ spec)
- `src/app/calculadora/calculadora.model.ts` — interfaces del dominio de la pantalla: `CotizacionLine`, `CotizacionDraft` (con `version`), `FilmOption` (lámina/ancho apto con precio), `QuoteSummary` (desglose + total); reusa `OrdenSucursal`, `AppCarBrand`, `AppCarModel`, `AppCarModelPart`, `ReelCatalogItem` existentes en lugar de crear `Branch`/`VehicleBrand`/`VehicleModel` duplicados (el prompt original los pedía; en el repo ya existen con otro nombre).
- `src/app/calculadora/calculadora.helpers.ts` (+ spec) — funciones puras: aptitud de bobina por ítem, opciones por ítem, mensaje de WhatsApp, (de)serialización del borrador, formateo `Bs`.
- `src/app/calculadora/calculadora.service.ts` (+ spec) — fachada que orquesta `OrdenesService` y `VehiclesService`.
- `src/app/calculadora/calculadora.component.{ts,html}` (+ spec) — pantalla, `FormGroup` de filtros + `FormArray` de ítems, `signal`/`computed`, estados con `@if`/`@for`.
- `src/app/calculadora/calculadora.routes.ts`
- `src/assets/scss/_calculadora.scss` (importado en `assets/scss/style.scss`, igual que `_ordenes.scss`) — `.layout-minimal`, `.pricing-calculator`, stepper, skeletons, sticky.

**Frontend `panel_admin/` (modificados)**
- `src/app/app.routes.ts` — ruta hermana `calculadora`.
- `src/app/layout/header/header.component.{ts,html}` — `input()` `minimal` (+ logo, sin toggle) y su spec.
- `src/app/ordenes/proformas/proforma-form.component.ts` — lectura opcional del borrador (solo alta) y su spec.
- `src/assets/data/routes.json` — ítem "Calculadora de precios".
- `src/environments/environment.ts` y `environment.development.ts` — `whatsappNumber`.
- `src/assets/scss/style.scss` — import del parcial nuevo.

**Backend / `proforma/`:** sin cambios.

## Implementation steps

**Fase 1 — Layout sin sidebar**
1. Crear `MinimalLayoutComponent` (`app-header` con `minimal` + `router-outlet`, contenedor `.layout-minimal`, dirección RTL/LTR como `MainLayoutComponent`).
2. Añadir el `input()` `minimal` al header: logo enlazado y sin toggle cuando es `true`; default `false`.
3. SCSS `.layout-minimal`: anular `padding-left` de `.main-content` y el desplazamiento de la barra por sidebar (claro/oscuro, móvil). Verificar en navegador.
4. Registrar la ruta `calculadora` (layout mínimo + `AuthGuard` + `loadChildren`).

**Fase 2 — Modelo, helpers y servicio**
5. Definir `calculadora.model.ts` y `calculadora.helpers.ts` (aptitud: `Number(reel.width) >= Number(item.width)` y metros suficientes; opciones ordenadas por precio; formateo `Bs` con `Intl.NumberFormat('es-BO')` aislado en una función para poder cambiar el formato).
6. Crear `CalculadoraService` (sucursales, marcas, modelos por marca, ítems por modelo, bobinas por sucursal).

**Fase 3 — Pantalla**
7. `CalculadoraComponent`: filtros en cascada, sucursal única preseleccionada y en gris, estados (inicial/cargando/sin resultados/error/activo), tabla de ítems con select, exclusión/restauración, alertas por fila con las clases `.line-alert` existentes, pie informativo.
8. Stepper derivado del estado (1 Vehículo → 2 Láminas → 3 Proforma al pulsar Crear).
9. Resumen sticky: imagen con placeholder, desglose, total, botones; responsive (apilado y barra inferior móvil).

**Fase 4 — Acciones y enlace con la proforma**
10. WhatsApp: mensaje prearmado y `wa.me/<environment.whatsappNumber>` en pestaña nueva; botón deshabilitado sin ítems con lámina.
11. Crear Proforma: construir `CotizacionDraft` y navegar con `history.state`; botón oculto sin `add_proforma_header`.
12. `ProformaFormComponent`: en alta, si `history.state` trae un borrador válido (versión conocida, sucursal dentro de las cargadas), precargar sucursal, modelo, ítems y líneas; si no, comportamiento actual. Las bobinas no disponibles se limpian con el mecanismo existente (`loadCatalog`).

**Fase 5 — Entrada, config y verificación**
13. Agregar "Calculadora de precios" a `routes.json` (bajo Órdenes), y `whatsappNumber` a ambos `environment`.
14. Correr `ng lint`, `ng test`, `ng build` (producción; cuidado con el presupuesto de estilos de componente, por eso los estilos van en el parcial global) y la verificación manual en vivo.

## Test strategy

Patrones existentes: `TestBed` + `HttpTestingController` (como `proforma-form.component.spec.ts`), spec del header con `AuthService`.

**Unitarios (helpers, sin TestBed)** — `calculadora.helpers.spec.ts`: aptitud (ancho menor/igual/mayor, metros justos/insuficientes, `cantidad > 1`), orden y etiqueta de opciones, mensaje de WhatsApp (ítems incluidos/excluidos, URL correctamente codificada), borrador (ida y vuelta, versión desconocida ⇒ `null`, datos corruptos ⇒ `null`), formato `Bs`.

**Componente** — `calculadora.component.spec.ts`:
- estado inicial; cascada Marca → Modelo; carga con skeleton; sin resultados (modelo sin ítems / sin bobinas); error con "Reintentar";
- sucursal única preseleccionada;
- elegir lámina actualiza subtotal y total; cambiar la lámina recalcula; excluir/restaurar ítem;
- select sin opciones inaptas; botones deshabilitados sin lámina;
- "Crear Proforma" oculto sin permiso y navega con el borrador esperado con permiso; WhatsApp arma el enlace.

**Layout/header** — `minimal-layout.component.spec.ts` (monta header sin sidebar); `header.component.spec.ts` ampliado: default intacto (toggle presente, sin logo) y `minimal` (logo, sin toggle).

**Proforma form** — `proforma-form.component.spec.ts` ampliado: con borrador válido precarga sucursal/modelo/líneas; sin borrador o inválido abre vacío (regresión del alta actual); bobina no disponible ⇒ línea limpia con el aviso existente.

**Backend:** sin cambios, no se agregan tests; la paridad de fórmula cliente/servidor sigue cubierta por `tests/test_ordenes_price_parity.py`.

**E2E (Playwright): NO corresponde.** El flujo se valida con specs de componente/servicio con `HttpTestingController` y una **verificación manual en vivo** contra el backend de desarrollo (paso 14); no hay cambios de integración frontend-backend (se usan endpoints existentes y ya cubiertos), y `proforma/`/`panel_admin/` no tienen Playwright instalado (agregarlo sería una dependencia nueva sin un flujo crítico nuevo que lo exija).

**Verificación manual en vivo (paso 14):** iniciar sesión con un usuario con y otro sin permiso de crear proformas; cotizar un modelo con varios ítems; comprobar total, exclusión, WhatsApp y que "Crear Proforma" precarga el formulario y guarda con el total que calcula el servidor; probar tema oscuro, móvil y una sucursal sin stock.

## Acceptance criteria

1. `/calculadora` exige sesión (redirige al login) y se ve sin sidebar, con logo a la izquierda y menú de perfil (nombre + Logout) a la derecha.
2. Las demás pantallas conservan sidebar y header actuales (toggle presente, sin logo); `header.component.spec.ts` original sigue verde.
3. Sucursal, Marca y Modelo funcionan en cascada; con una sola sucursal asignada se fija en gris; sin sucursal se muestra el aviso existente.
4. Cada ítem del modelo aparece en una fila con ícono, nombre, subtítulo `ancho × largo · cantidad`, select de láminas **aptas y con stock**, subtotal y acción quitar/restaurar.
5. El subtotal por ítem y el total se recalculan al cambiar cualquier selección o exclusión y coinciden con `previewSubtotal`; un ítem excluido o sin lámina no suma.
6. Estados inicial, cargando (skeletons), sin resultados (dos causas), error con reintento y activo se alternan sin solaparse.
7. El stepper refleja el paso actual (1 sin modelo, 2 con modelo, 3 al crear proforma).
8. El resumen es sticky en ≥ lg y se apila en pantallas menores; muestra imagen (placeholder si `image` es `null`), desglose y total.
9. "Consultar por WhatsApp" abre `wa.me` con número de `environment` y un mensaje con vehículo, ítems con lámina y total; deshabilitado sin ítems con lámina.
10. "Crear Proforma" solo se ve con `add_proforma_header`; al pulsarlo el formulario de alta se abre con sucursal, modelo y líneas precargados; sin borrador (recarga/acceso directo) el formulario abre vacío como antes; el total final lo fija el servidor.
11. No se renderiza ningún badge "Recomendada" (diferida por ADR) y no hay cambios de backend.
12. `ng lint` y `ng build` de producción limpios; los specs nuevos pasan y no aparecen fallos nuevos frente a los 15 preexistentes de la plantilla.

## Risks

- **CSS de layout**: la plantilla desplaza contenido y barra por el sidebar (`_layout.scss:710-716`); `.layout-minimal` podría dejar huecos en tema oscuro/RTL/móvil. Mitigación: verificación visual explícita (paso 3 y 14); el cambio es aislado a la clase nueva.
- **Presupuesto de estilos de componente** (`ng build` falló en Órdenes por esto, REV-01): todo el SCSS nuevo va en parcial global, sin `styleUrls` grandes.
- **Divergencia cotización vs. total final** si cambian stock o precio entre ambos pasos: aceptado; se rotula como referencial (alerta del DDR).
- **Importes con `Number`** en vista previa: mismo criterio que el código existente; nunca se envían al servidor. Mitigación: ninguna adicional (no autoritativo).
- **`history.state`** se pierde al recargar el formulario: comportamiento intencional (formulario vacío); documentado.
- **Dos calculadoras en el repo** (`proforma/` Angular 16 y esta): sin unificar; aceptado por ADR.
- **Ítem de menú sin filtro de permiso** hasta que negocio defina la ubicación: visible para todo usuario staff; la pantalla es de solo lectura salvo "Crear Proforma", que ya se oculta sin permiso.
- **Tests frontend preexistentes fallando (15)**: dificultan leer regresiones; se compara contra `master`.
- **Sin mitigación** para el número de WhatsApp global: si negocio lo quiere por sucursal, requiere un cambio de modelo y un ADR propio.

## Out of scope

- Regla y badge "Recomendada" (sin definición de negocio; si requiere dato nuevo, ADR propio).
- Número de WhatsApp por sucursal.
- Endpoint de cotización en backend, persistir cotizaciones, descuentos, venta por metro lineal y cualquier cambio a la calculadora de `proforma/`.
- Tailwind u otras dependencias nuevas.
- Quitar el toggle/ajustar el header del resto de pantallas.

**Preguntas abiertas para el usuario (no bloquean el plan):**
1. ¿Se confirma `+59178181012` (el de `proforma/`) como número global inicial?
2. ¿"Calculadora de precios" bajo **Órdenes** en el menú lateral, y/o botón en el listado de proformas?
3. ¿Formato de importes `Bs 2.090` (prompt) o `2090.00 Bs` (Órdenes)? El plan implementa `Bs 2.090` aislado en una función.

## Dependencias nuevas

Ninguna.
