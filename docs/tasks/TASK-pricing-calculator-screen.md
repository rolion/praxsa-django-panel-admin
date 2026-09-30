# TASK-pricing-calculator-screen: Pantalla "Calculadora de precios" para staff/asesores en panel_admin

**Etapa actual:** PLANNING
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
| 2026-09-30 | ENGINEERING → REVIEW | Implementación completa según plan v1 (5 fases, solo frontend `panel_admin/`); specs propios en verde, `ng lint` y `ng build` limpios; verificación en vivo con API simulada (escritorio y móvil) | delivery-engineer |
| 2026-09-30 | REVIEW → INVESTIGATION | Cambio de alcance pedido por el usuario tras ver la v1: la calculadora es para cliente final (login/registro en modal por etapas, menú superior Calculadora/Proformas, lista de proformas de solo lectura, sin sidebar ni acceso a administración), dentro de `panel_admin/` y con la placa en la cuenta. Reinvestigación de cuentas de cliente, sesión y contratos; el DDR/ADR/plan v1 quedan pendientes de revisión | delivery-investigate |
| 2026-09-30 | INVESTIGATION → ARCHITECTURE (via DESIGN) | Diseño del flujo de cliente resuelto en un DDR nuevo que reemplaza al de la v1: calculadora navegable sin sesión, modal de acceso (login y registro en 2 etapas), encabezado con Calculadora/Proformas, guardado directo con datos de la cuenta y lista Mis proformas de solo lectura; el veredicto NEEDS_ARCHITECTURE exige decidir aislamiento de sesión/autorización, registro con username y placa, catálogos y contrato de listado | delivery-design |
| 2026-09-30 | ARCHITECTURE → PLANNING | Decisiones tomadas en 3 ADR nuevos: sesión de cliente con aislamiento por guards y barrera de servidor existente (sin tocar el login del panel), registro y API de cliente aditivos (endpoint nuevo, `Client.car_plate` con migración, perfil y lista propios, `POST invoice` para guardar), y catálogo público para la calculadora; el ADR de cotización v1 queda reemplazado en parte | delivery-architect |

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

### Cambio de alcance (2026-09-30, pedido del usuario tras ver la implementación v1)

**Requerimiento nuevo (resumen fiel):**
1. Al pulsar "Crear proforma" la pantalla salta a la vista de Órdenes/Proforma y muestra el **menú lateral completo**. Quien usa esta pantalla **nunca** debe ver el menú lateral ni tener acceso a otros recursos de administración del sistema (el usuario escribió "usuario staff"; ver hipótesis H1).
2. Si la persona **no está logueada** debe pedírsele iniciar sesión, en un **modal sencillo**; si no tiene cuenta, el modal debe permitirle **crearla**.
3. Creación de cuenta en **modal por etapas**: (a) datos principales: nombre, apellido, correo, teléfono y placa del vehículo; (b) credenciales: nombre de usuario (sugerencia: el correo), contraseña y confirmar contraseña.
4. Logueada, el **menú superior** muestra 2 opciones: **Calculadora** (vuelve a la calculadora) y **Proformas** (lista de proformas del usuario, **solo lectura**).
5. Flujo: la persona llega a la calculadora → pide guardar la proforma → si no está logueada, login/crear cuenta → se guarda y pasa a **su lista de proformas**.
6. Decisiones confirmadas por el usuario: el flujo **sigue en `panel_admin/`** (no en `proforma/`); **la placa se guarda en la cuenta del usuario**; en esta pantalla no se ve el sidebar y el usuario nunca accede a los demás recursos de administración.

Este requerimiento **cambia el actor** (de asesor staff a cliente final con cuenta propia) y **supera** los supuestos de la investigación anterior sobre "staff/asesores" y sobre "Crear Proforma lleva al formulario interno". Los hechos previos sobre `panel_admin/` y los endpoints staff siguen siendo ciertos pero ya no cubren este actor.

### Hechos nuevos (cuentas de cliente, sesión y proformas del usuario)

**Backend — lo que ya existe para clientes**
- `POST product/create_client` (`AllowAny`): `praxsa_manager/product/views.py:331-339` → `ClientSerializer` (`serializer/client_serializer.py:6-40`). Campos: `email` (único contra `User`), `password`, `name`, `lastname`, `phone_number` (regex `(\+)*\d{7,11}`), `ci_nit` opcional. Crea `User` con `username=email` (`:18-23`) y un `Client` (`:25-30`). **No recibe ni guarda placa ni un username distinto del correo**, y `password` es un `CharField` simple (`:10`): no pasa por `validate_password`, aunque `AUTH_PASSWORD_VALIDATORS` está definido (`praxsa_manager/settings.py:168-182`). No hay confirmación de contraseña en servidor.
- Modelo `Client` (`praxsa_manager/product/models.py:97-107`): `name`, `last_name`, `phone_number`, `ci_nit`, `user_id` (FK nullable). **Sin campo de placa.** Última migración: `0114_precio_venta_sucursal_unico.py`.
- Login de cliente: `POST product/api-token-auth/` → `CustomAuthToken` (`custom_views/auth_token.py:6-29`): exige un `Client` para el usuario (`Client.objects.get(user_id=user)`, `:14`; un usuario sin `Client` produciría una excepción no controlada) y devuelve `token, user_id, email, name, lastname, phone_number, ci_nit` (sin `is_staff`, `groups` ni `permissions`).
- Login de `panel_admin/`: `POST product/api-panel-admin-token-auth/` → `PanelAdminAuthToken` (`auth_token.py:32-56`): su docstring (`:33-36`) dice que **no verifica rol ni `is_staff`** ("por ahora cualquier usuario válido entra") y devuelve `is_staff`, `groups`, `permissions`. Lo usa `AuthService.login` (`panel_admin/src/app/core/service/auth.service.ts`, método `login`).
- Crear proforma como cliente: `POST product/invoice` (`custom_views/invoice.py:15-34`): `TokenAuthentication` + `IsAuthenticated` (**acepta a cualquier usuario autenticado, staff o cliente**), fija `created_by = request.user` (`:25`). `SalesHeaderSerializer` (`serializer/invoice_serializer.py:28-72`): campos `name, email, car_plate, car_model_id, total_price, carPartItems, phone_number, ci_nit, sucursal, created_by` (`:33-36`); `validate` (`:37-72`) **recalcula el precio en servidor** (ADR-004) y la proforma queda con `origen = calculadora` (`helper/proforma.py:6`). Este serializer **no aplica** las reglas de aptitud de la API de Órdenes (ancho de bobina ≥ ancho del ítem, metros suficientes: `business/pricing.py:158-162`); solo resuelve el precio de lámina/ancho y falla si no hay precio.
- Listar proformas del usuario: `GET product/invoice/all` (`invoice.py:74-105`): `TokenAuthentication` + `IsAuthenticated`; filtra por `created_by = request.user.id` (`:97-98`); devuelve `{recordsTotal, recordsFiltered, data:[{id, name, email, ci_nit, car_plate, phone_number, car_model_id, car_model_name, total_price, date}]}`. **Sin detalle de ítems**, sin estado y sin marca; el campo `date` usa el formato `"%d%m/%Y"` (`:94`, sin separador entre día y mes, a diferencia de `"%d/%m/%Y"` en `:66`); hay un `print(request.user.id)` de depuración (`:84`). El detalle `GET product/invoice/<pk>/` filtra por `created_by = request.user` (`:38`) e incluye ítems con lámina.
- Barrera staff: `IsStaffUser` (`permissions.py:4-11`) exige `is_staff`; los endpoints `ordenes/*`, `vehicles/*`, `almacen/*`, `users/*` la usan (p. ej. `ordenes_admin.py:43`). Un cliente (`create_user` sin `is_staff`, `client_serializer.py:18-23`) **recibiría 403 en todos**, incluidos `ordenes/catalogo/*` y `vehicles/*` que consume la calculadora v1.
- Catálogos **públicos** disponibles para un cliente: `get_calculator_info` (`views.py:252-280`, vista Django sin `@api_view`): marcas, modelos (`id, name, brand_id`; **sin imagen**), partes, láminas y sucursales con `enable_to_install_windows_film`; `get_model_parts/<id>` (`views.py:313-325`): `width, length, quantity, part_id, part_name, installation_price` (este último como `float`); `get_inventory/<sucursal>/<lamina>/<width>` (`views.py:219-249`, con `PublicCatalogThrottle` 60/min, `settings.py:126-128`): por `(lámina, ancho)` devuelve metros y `bobina_price`; con `lamina_id=0` y `width=0` no filtra (`business/inventario.py:156-164`), es decir lista todas las bobinas de la sucursal; su filtro de ancho es `>=` (`inventario.py:161-164`). No existe un equivalente público de `ordenes/catalogo/bobinas`.
- CORS: la whitelist incluye `http://localhost:4200`, `http://localhost:4201` y `http://127.0.0.1:4200/4201` (`settings.py:94-110`), además de los dominios `panel.*` de producción.

**Frontend `panel_admin/` — sesión y layout**
- `AuthGuard` solo verifica que exista `currentUser.token` (`core/guard/auth.guard.ts:13-19`); **todas** las rutas de administración cuelgan del mismo padre con ese guard (`app.routes.ts:7-67`). No distingue staff de cliente ni permisos de ruta. Cualquier usuario con token (incluido uno creado por `create_client` y logueado por el endpoint del panel) podría abrir `#/users`, `#/almacen`, etc. en la UI; el backend los rechaza (403), pero la navegación y los menús quedan visibles.
- El sidebar se arma desde `assets/data/routes.json` y `filterByPermission` (`layout/sidebar/sidebar.metadata.ts:17-29`): los ítems **sin** `permission` se muestran siempre; hoy muchos ítems no declaran `permission`.
- El `JwtInterceptor` agrega `Authorization: Token <token>` a **todas** las peticiones (`core/interceptor/jwt.interceptor.ts:14-20`); el `ErrorInterceptor`, ante cualquier `401`, hace `logout()` + `location.reload()` (`core/interceptor/error.interceptor.ts:17-21`), lo que descarta el estado de la pantalla.
- Sesión: `AuthService.login` guarda un `User` (`id, username, firstName, lastName, token, isStaff, groups, permissions`; `core/models/user.ts`) con `LocalStorageService` bajo prefijo `light_`/`dark_` (`core/service/storage.service.ts`), clave única `currentUser`.
- Auth actual de la app: rutas `authentication/signin|signup|forgot|reset` (`authentication/auth.routes.ts`). `signup` es un **demo de la plantilla** (marca "Oreva", `signup.component.html:12`), no el registro de clientes. No existe un componente de login/registro en modal.
- Modales: el patrón existente es `NgbModal` + `NgbActiveModal` con componente standalone y `ReactiveForms` (p. ej. `ordenes/notas-venta/pago-modal.component.ts:1-40`; `@ng-bootstrap/ng-bootstrap` 20). Hay 9 componentes que ya usan `NgbModal`.
- Layouts existentes: `MainLayoutComponent` (header + sidebar + right-sidebar) y `AuthLayoutComponent` (login); la v1 agregó `MinimalLayoutComponent` (solo header, variante `minimal`) y la ruta `calculadora` bajo `AuthGuard`. La v1 también agregó el ítem "Calculadora de precios" al menú lateral de staff (`assets/data/routes.json`), y "Crear Proforma" navega a `/ordenes/proformas/create` con el borrador en `history.state` (`calculadora/calculadora.component.ts`, método `createProforma`).
- El header de la v1 (variante `minimal`) tiene logo + fullscreen + menú de usuario con Logout (`layout/header/header.component.html`); **no tiene** las opciones "Calculadora"/"Proformas" ni un modo "no logueado".

**Frontend `proforma/` (cliente final, Angular 16) — referencia de un flujo equivalente ya existente**
- Login `POST product/api-token-auth/` y registro `POST product/create_client` (`proforma/src/app/service/pybackend/authentication/authetication.service.ts:35-60`), creación de proforma `POST product/invoice` y listado `GET product/invoice/all` (`service/pybackend/proforma/proforma.service.ts:30,49`), calculadora con `get_inventory/<sucursal>/0/0` (`service/data.service.ts:69-71`). Sirve de contrato de referencia; el usuario decidió **no** mover el flujo allí.

### Hipótesis / supuestos no confirmados (adicionales)
- **H1.** "Usuario staff" en los puntos 1 y 6 se lee como "el usuario de esta pantalla" (cliente final con cuenta propia), porque el flujo describe autoregistro y "la lista de **sus** proformas". No está confirmado si además el personal interno (staff con permisos) seguirá entrando por el login del panel y usará el layout completo, ni si la calculadora v1 para staff debe conservarse.
- **H2.** La sesión de cliente y la de staff conviven en la **misma app** `panel_admin/` (mismo origen y mismo `localStorage`): no se verificó qué pasa si un navegador tiene las dos; el almacenamiento usa una única clave `currentUser`.
- **H3.** "Nombre de usuario" distinto del correo implica que el `username` de `User` debe aceptarse en el registro; hoy se fija al correo (`client_serializer.py:19`). No se verificó si existen usuarios cuyo username no sea su correo ni qué unicidad se exige.
- **H4.** "Solo lectura" para la lista de proformas se asume sin acciones (sin editar, anular, PDF ni generar nota); no se confirmó si el cliente debe ver detalle de ítems, estado o descargar PDF. El endpoint de listado hoy no devuelve ítems ni estado.
- **H5.** Se asume que las proformas creadas por staff en `/ordenes/proformas` (con `created_by` = el staff) no deben aparecer en la lista de un cliente; por el filtro `created_by` no aparecerían. No verificado si se espera que un asesor asocie proformas a un cliente.
- **H6.** No se confirmó si la sucursal se elige en la calculadora (como hoy) o se asigna por la cuenta; `Client` no tiene sucursal.
- **H7.** No se verificó contra el backend real (solo lectura de código) el comportamiento de `api-token-auth/` con un usuario sin `Client` (se asume error no controlado por `Client.objects.get`).
- **H8.** No se verificó limitación de tasa ni captcha en `create_client`; el throttling existente solo cubre `get_inventory`/`get_layer_info` (`settings.py:126-128`, ADR-005).
- Siguen sin confirmar (investigación anterior): regla de lámina "Recomendada", número de WhatsApp (global vs. por sucursal), formato de importes y ubicación de la entrada al menú.

### Módulos y dependencias relacionadas (adicionales)
- Backend `praxsa_manager/product/`: `serializer/client_serializer.py`, `models.py` (`Client`), `custom_views/auth_token.py`, `custom_views/invoice.py`, `serializer/invoice_serializer.py`, `business/pricing.py`, `views.py` (catálogos públicos y `create_client`), `permissions.py`, `praxsa_manager/settings.py` (DRF/CORS/validadores), migraciones.
- Frontend `panel_admin/src/app/`: `core/` (auth, guard, interceptores, modelos), `layout/` (header, layouts, sidebar), `app.routes.ts`, `authentication/`, `calculadora/` (v1), `ordenes/proformas/proforma-form.component.ts` (recibe el borrador en la v1), `assets/data/routes.json`.
- Docs: `docs/adr/ADR-004-server-side-price-recalculation.md`, `ADR-005-public-catalog-endpoints-protection.md`, `ADR-006-idor-invoice-and-proforma-car-part-info.md`, `ADR-003-reduce-localstorage-pii.md`, `docs/backend-audit.md` (SEC-03, SEC-04).

### Comportamiento actual (con la v1 implementada)
La calculadora v1 (PR #60) solo funciona para un usuario staff: usa catálogos `IsStaffUser`, "Crear Proforma" navega al formulario interno del panel (layout completo, sidebar visible) y no existe login/registro de clientes ni lista de proformas de cliente dentro de `panel_admin/`. Un cliente real que llegara a `#/calculadora` sin sesión es redirigido a `#/authentication/signin` (login de la plantilla, endpoint del panel) y, aun con sesión, recibiría 403 en los catálogos.

### Restricciones (adicionales)
- `docs/CLAUDE.md`: dinero en `Decimal`; todo cambio de lógica de negocio con su test; no editar migraciones aplicadas (un campo de placa en `Client` exigiría una migración nueva); no agregar dependencias sin avisar; **proponer plan y esperar confirmación antes de cambios que afecten varios archivos** (autenticación, backend y frontend).
- ADR-004: el precio nunca se confía del cliente; ADR-005: endpoints públicos con throttling; ADR-006-idor: acotar siempre por propietario en el detalle.
- Cambios de autenticación/autorización y de registro público son sensibles: requieren estrategia de rollback explícita en arquitectura.

### Riesgos identificados (adicionales)
- **Seguridad/autorización (alto):** el login del panel acepta a cualquier usuario válido (`auth_token.py:33-36`) y el `AuthGuard` no separa actores; un cliente autenticado vería toda la navegación de administración. Falta una barrera de UI y de ruta que lo aísle (el backend ya responde 403 en los recursos staff).
- **Registro público (alto):** `create_client` es `AllowAny`, sin throttling ni validación de contraseña con los validadores de Django, y fija `username=email`; agregar username propio y placa exige cambiar serializer y modelo (migración) y definir unicidad.
- **Datos existentes / migración:** agregar la placa a `Client` requiere migración; los clientes actuales quedarían con placa vacía.
- **Contrato de listado pobre:** `invoice/all` no trae ítems ni estado y tiene un formato de fecha inconsistente; una "lista solo lectura" puede exigir ampliar el contrato (el frontend `proforma/` también lo consume: riesgo de romperlo).
- **Validación de negocio distinta por camino:** `POST product/invoice` no aplica las reglas de aptitud de ancho/stock de `ordenes/*` (`invoice_serializer.py:37-72` vs. `pricing.py:158-162`), así que lo que la calculadora muestre como "apto" podría no validarse al guardar un cliente.
- **Catálogo público sin imagen ni reels** equivalentes al de staff: la pantalla v1 (imagen del modelo, bobinas con metros disponibles) no puede alimentarse igual con endpoints públicos; además `get_inventory` está limitado a 60/min por IP anónima.
- **Sesiones mezcladas:** una sola clave `currentUser` en `localStorage` con dos tipos de usuario, y el `ErrorInterceptor` que recarga la página ante cualquier 401 (se perdería el estado de la calculadora si el token expira o es inválido).
- **Alcance del PR #60:** la v1 ya implementa un flujo que el usuario descartó (staff + formulario interno); buena parte del módulo `calculadora/` es reutilizable, pero la navegación, el layout y las fuentes de datos cambian.
- No está decidido si la calculadora v1 para staff se conserva o se reemplaza.

### Veredicto de complejidad (actualizado por el cambio de alcance)
**NEEDS_ARCHITECTURE** — Cambia la autenticación/autorización (cliente final dentro de `panel_admin/`, aislamiento respecto de los recursos de administración, registro público con username y placa), requiere cambios de backend (serializer, modelo con migración, posiblemente catálogos y listado) y de frontend (layout, guard, modal por etapas, menú superior, lista), y toca múltiples módulos. Ya era NEEDS_ARCHITECTURE; ahora con decisiones de seguridad que deben resolverse antes de planificar.

### Diseño requerido (actualizado)
**SI** — Pantallas y flujos nuevos: modal de login y de registro por etapas, menú superior con dos opciones, lista de proformas de solo lectura, comportamiento "no logueado → login → guardar → lista", y revisión del diseño v1 (`DDR-pricing-calculator-screen-pantalla-calculadora`), que asumía staff y el formulario interno. El DDR existente queda parcialmente superado.

### Hechos encontrados (investigación original, actor staff)
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
- [DDR-pricing-calculator-screen-flujo-cliente](../design/DDR-pricing-calculator-screen-flujo-cliente.md) — **vigente (2026-09-30)**. Actor cliente final: calculadora sin sesión; "Crear Proforma" pide login/registro en modal (registro en 2 etapas: datos → credenciales) y guarda con los datos de la cuenta; encabezado sin sidebar con Calculadora/Proformas y usuario; lista Mis proformas (`ngx-datatable`, solo lectura, sin columna de estado). Hereda del DDR anterior la pantalla de cotización.
  - Pendientes: flujo/menú de staff, detalle y estado para el cliente, CI/NIT, etiqueta del botón, y los de la v1.
- *(Reemplazado por el DDR de flujo cliente; la pantalla de cotización se hereda)* [DDR-pricing-calculator-screen-pantalla-calculadora](../design/DDR-pricing-calculator-screen-pantalla-calculadora.md) — pantalla única sin sidebar (header mínimo con logo + perfil), stepper propio de 3 pasos derivado del estado, tabla Bootstrap de ítems con select de lámina apta por ítem, resumen sticky con Crear Proforma (lleva al formulario existente precargado) y WhatsApp con mensaje prearmado, estados inicial/cargando/sin resultados/error.

**Pendientes de negocio (no resolubles desde el código):** regla de "Recomendada", número de WhatsApp (global vs. por sucursal), texto/formato de importes y ubicación de la entrada al menú.

## Arquitectura
### Vigente tras el cambio de alcance (2026-09-30)
- [ADR-pricing-calculator-screen-sesion-cliente-aislamiento](../adr/ADR-pricing-calculator-screen-sesion-cliente-aislamiento.md) — un solo login/sesión (`isStaff` discrimina); guard de staff en el layout de administración, `/calculadora` pública y `/mis-proformas` con guard de sesión; barrera real en servidor (`IsStaffUser`, sin cambios); 401 de cliente sin recarga (reabre el modal); staff conserva el camino de la v1; login solo por usuario.
- [ADR-pricing-calculator-screen-registro-y-api-cliente](../adr/ADR-pricing-calculator-screen-registro-y-api-cliente.md) — `POST product/client/register` (username opcional, contraseña validada, throttle), `Client.car_plate` con migración `0115` aditiva, `GET client/me`, `GET client/proformas` (propias, sin `is_delete`), guardado con `POST invoice` existente; `create_client` e `invoice/all` intactos.
- [ADR-pricing-calculator-screen-catalogo-publico-calculadora](../adr/ADR-pricing-calculator-screen-catalogo-publico-calculadora.md) — la calculadora usa `get_calculator_info` / `get_model_parts` / `get_inventory` públicos (con `is_active` e imagen agregados de forma aditiva).
- [ADR-pricing-calculator-screen-layout-sin-sidebar](../adr/ADR-pricing-calculator-screen-layout-sin-sidebar.md) — sigue vigente (layout mínimo y variante de header); se extiende por el ADR de sesión.

**Rollback:** backend aditivo (migración reversible, endpoints nuevos independientes, cambio de una línea en el catálogo público) y frontend revertible quitando guard/rutas/modal; sin cambios de infraestructura. Despliegue: backend primero, frontend después.

**Decisiones tomadas por defecto (a confirmar con negocio):** el staff mantiene el flujo de la v1 y su ítem de menú; login por "Usuario" (no por correo); CI/NIT no se pide y se envía `null`; sin columna de estado ni detalle en la lista del cliente; el servidor no agrega aquí las reglas de ancho/metros a `POST invoice` (deuda explícita).

### Versión anterior (v1, actor staff)
- [ADR-pricing-calculator-screen-layout-sin-sidebar](../adr/ADR-pricing-calculator-screen-layout-sin-sidebar.md) — `MinimalLayoutComponent` + ruta hermana `calculadora`; `app-header` con variante mínima (logo, sin toggle de sidebar) vía `input()` con default que preserva el comportamiento actual; offset del sidebar neutralizado con clase propia.
- [ADR-pricing-calculator-screen-cotizacion-en-cliente](../adr/ADR-pricing-calculator-screen-cotizacion-en-cliente.md) — sin cambios de backend; total como vista previa con `ordenes.calc.ts`; `ReactiveForms` + signals en `calculadora/`; borrador por `history.state` al formulario de proforma; permiso `add_proforma_header` solo como UX; WhatsApp con número global en `environment`; "Recomendada" diferida.

**Rollback:** ambos cambios son aditivos (sin migraciones ni cambios de contrato); basta quitar la ruta/ítem de menú y la lectura opcional del borrador.

## Plan
- [PLAN-2026-09-30-pricing-calculator-screen](../plans/PLAN-2026-09-30-pricing-calculator-screen.md) — **v1**. 5 fases (layout, modelo/helpers/servicio, pantalla, acciones y enlace con la proforma, entrada y verificación). Preguntas abiertas no bloqueantes: número de WhatsApp, ubicación en el menú y formato de importes.

## Implementación

Implementado según [PLAN v1](../plans/PLAN-2026-09-30-pricing-calculator-screen.md), sin desvíos de alcance, sin dependencias nuevas y sin cambios de backend.

**Fase 1 — Layout:** `MinimalLayoutComponent` (`layout/app-layout/minimal-layout/`), `input()` `minimal` en `HeaderComponent` (logo, sin toggle; default `false` intacto), ruta hermana `calculadora` con `AuthGuard` en `app.routes.ts`, y `assets/scss/_calculadora.scss` (`.layout-minimal`, íconos del header visibles sobre fondo blanco, estilos de la pantalla).
**Fases 2-3 — Módulo `calculadora/`:** `calculadora.model.ts`, `calculadora.helpers.ts` (aptitud de bobinas, formato `Bs`, mensaje/URL de WhatsApp, borrador), `calculadora.service.ts` (fachada sobre `OrdenesService`/`VehiclesService`), `CalculadoraComponent` (ReactiveForms + signals, estados inicial/cargando/sin resultados/error/activo, stepper, exclusión/restauración de ítems, resumen sticky) y `calculadora.routes.ts`.
**Fase 4 — Acciones:** WhatsApp con `environment.whatsappNumber`; "Crear Proforma" (oculto sin `add_proforma_header`) navega con el borrador en `history.state`; `ProformaFormComponent` lo precarga solo en alta (sucursal, modelo, ítems, líneas) y cae al formulario vacío si falta o es inválido.
**Fase 5:** ítem "Calculadora de precios" bajo Órdenes en `assets/data/routes.json`; `whatsappNumber: '+59178181012'` (valor de `proforma/`, pendiente de confirmar) en ambos `environment`.

**Ajustes sobre el plan (sin cambiar alcance):** barra inferior con total y acción principal en pantallas < lg (estaba en el DDR), filas apiladas en < md (la plantilla fuerza `min-width: 800px` a tablas responsive en xs, `override/_table.scss:589-594`, se anula solo para esta tabla), y `catalogsLoaded` para no mostrar "sin sucursal" antes de que lleguen los catálogos.

**Pruebas escritas:** `calculadora.helpers.spec.ts` (unitarias), `calculadora.component.spec.ts` (componente + `HttpTestingController`), `minimal-layout.component.spec.ts`, casos nuevos en `header.component.spec.ts` (default vs. `minimal`) y `proforma-form.component.spec.ts` (precarga de borrador, sin borrador, borrador inválido, bobina ya no disponible). Sin E2E (decidido en el plan).

**Corridas propias (no son el Quality Gate):** `ng lint` limpio; `ng build` de producción ok; `ng test`: 368 OK y 14 fallos, todos `should create` de specs de la plantilla ajenos al cambio (Sidebar, Footer, Signup, Page404/500, demos de menú); ninguno en archivos tocados. Verificación en vivo en el navegador con el API simulado en la página (sin tocar la base de desarrollo ni credenciales reales): layout sin sidebar, filtro de láminas aptas, total 388 + 110 = 498, exclusión, enlace de WhatsApp, precarga del formulario de proforma y vista móvil sin scroll horizontal.

**Deuda / pendientes señalados (no resueltos aquí):**
- Regla y badge "Recomendada" diferidos (ADR); el espacio existe y solo se renderiza si `FilmOption.recommended` llega a ser `true`.
- Número de WhatsApp global en `environment` (por sucursal requeriría campo nuevo + ADR); formato `Bs 2.090` aislado en `formatBs`; ubicación del menú bajo Órdenes: los tres a confirmar con negocio.
- No verificado visualmente: tema oscuro y RTL de `.layout-minimal`; tampoco se probó contra el backend real (solo API simulada). La verificación manual contra el backend de desarrollo con usuarios con y sin permiso sigue pendiente para `delivery-review`.
- `ng build` emite la advertencia "23 rules skipped due to selector errors" (selectores `%` de la plantilla); no proviene de los estilos nuevos.
- Sigue habiendo dos calculadoras (esta y la de `proforma/`), aceptado por el ADR.

## Review
_Pendiente_

## Publicación
_Pendiente_
