# PLAN-2026-09-30-pricing-calculator-screen (v2)

**Task:** TASK-pricing-calculator-screen
**DDRs relacionados:** [DDR-pricing-calculator-screen-flujo-cliente](../design/DDR-pricing-calculator-screen-flujo-cliente.md) (vigente); [DDR-pricing-calculator-screen-pantalla-calculadora](../design/DDR-pricing-calculator-screen-pantalla-calculadora.md) (reemplazado; su pantalla de cotización se hereda)
**ADRs relacionados:** [sesion-cliente-aislamiento](../adr/ADR-pricing-calculator-screen-sesion-cliente-aislamiento.md), [registro-y-api-cliente](../adr/ADR-pricing-calculator-screen-registro-y-api-cliente.md), [catalogo-publico-calculadora](../adr/ADR-pricing-calculator-screen-catalogo-publico-calculadora.md), [layout-sin-sidebar](../adr/ADR-pricing-calculator-screen-layout-sin-sidebar.md) (vigente, extendido); [cotizacion-en-cliente](../adr/ADR-pricing-calculator-screen-cotizacion-en-cliente.md) (reemplazado en parte: siguen los puntos 2, 3, 4, 7, 8, 9)

## Objective

Que un **cliente final** pueda cotizar sin sesión en la calculadora de `panel_admin/`, y al pedir guardar inicie sesión o cree su cuenta en un modal (registro en 2 etapas, con placa en la cuenta), guarde la proforma con los datos de su cuenta y vea **sus proformas** en una lista de solo lectura; sin sidebar y sin acceso a los recursos de administración.

## Context

Ver TASK-pricing-calculator-screen: "Cambio de alcance (2026-09-30)" (actor cliente, no staff), el DDR de flujo de cliente y los 3 ADR nuevos. Este **v2 se construye sobre lo ya implementado por el plan v1** (PR #60): `MinimalLayoutComponent`, variante `minimal` del header, módulo `panel_admin/src/app/calculadora/` (pantalla, helpers, servicio, modelo, specs), ruta `calculadora`, SCSS `_calculadora.scss`, ítem de menú de staff, `whatsappNumber` en `environment` y la precarga opcional del borrador en `ProformaFormComponent`. Esos cambios se **conservan**; v2 agrega backend y cambia la sesión, el origen de datos y las acciones de la calculadora.

**Notas de verificación (código vigente al planificar):**
- La rama `claude/pricing-calculator-screen-b5e976` está **9 commits detrás de `origin/master`** (incluye PR #58: ajustes de URL de imágenes de modelo con `SECURE_PROXY_SSL_HEADER` en `settings.py:219`, nginx y specs de vehículos). **Primer paso: traer master** (en una worktree de la app, con `sync_with_base_branch`), antes de tocar código; la última migración en master sigue siendo `0114_precio_venta_sucursal_unico.py` (verificado con `git ls-tree`).
- Siguen vigentes los hechos citados por los ADR: `PanelAdminAuthToken` (`custom_views/auth_token.py:32-56`), `ClientSerializer` (`serializer/client_serializer.py:6-40`), `Client` (`models.py:97-107`), `InvoiceView`/`ListUserInvoice` (`custom_views/invoice.py:15-105`), `SalesHeaderSerializer` (`serializer/invoice_serializer.py:28-72`), `get_calculator_info`/`get_model_parts`/`get_inventory` (`views.py:252-280, 313-325, 219-249`), `AuthGuard` (`core/guard/auth.guard.ts:13-19`), `ErrorInterceptor` (`core/interceptor/error.interceptor.ts:17-21`), rutas (`app.routes.ts`).
- Precisión nueva: `is_active` existe en `Car_Brand`, `Car_Model`, `Car_Part` **y `Window_Film`** (`models.py:19,30,39,67`), así que el filtro del catálogo público aplica a las cuatro; `Client.ci_nit` no tiene `blank` pero el registro nuevo no lo pide (se guarda vacío).
- El payload de `POST product/invoice` que hoy arma `proforma/` es: cabecera (`name, email, car_plate, car_model_id, total_price, phone_number, ci_nit, sucursal`) + `carPartItems[{car_part, width, length, quantity, window_film, installation_price, window_film_price, sub_total}]` (`proforma/src/app/model/proformaCollection.ts`, `tests/test_invoice_pricing.py:16-40`); el servidor sobrescribe los importes.

## Current behavior

- Calculadora v1 (solo staff): catálogos de staff (`ordenes/catalogo/*`, `vehicles/*`), "Crear Proforma" navega al formulario interno con el borrador en `history.state` (`calculadora.component.ts`, `createProforma`), ruta protegida por `AuthGuard` (`app.routes.ts:72`).
- Un cliente no tiene registro propio en `panel_admin/`, no hay modal de acceso, ni lista de proformas de cliente; `create_client` no recibe placa ni username (`client_serializer.py`); el login del panel acepta cualquier usuario y el guard no separa actores; todo 401 recarga la página.
- Catálogo público: `get_calculator_info` no filtra `is_active` ni trae la imagen (`views.py:257-261`).

## Expected behavior

- `/calculadora` es **pública** (sin sesión) y usa los catálogos públicos; muestra el encabezado sin sidebar con el estado de sesión (DDR).
- "Crear Proforma": sin sesión abre el modal; con sesión de cliente guarda con `POST invoice` usando `GET client/me` y termina en `/mis-proformas` con aviso y fila resaltada; con sesión vencida reabre el modal y reintenta conservando la cotización.
- Registro en 2 etapas contra `POST client/register`; al crear la cuenta inicia sesión y continúa guardando.
- `/mis-proformas` (requiere sesión) lista solo las proformas propias (sin borradas) con `GET client/proformas`, en solo lectura.
- Un cliente no ve ni navega a la administración (guard de staff) y el servidor sigue devolviendo 403 en los recursos de staff.
- Staff conserva el flujo de la v1 (formulario interno, permiso `add_proforma_header`) y el resto del panel sin cambios.

## Architecture considerations

Resumen de los ADR (no se re-decide):
- **Sesión/aislamiento:** un login y una sesión (`isStaff` discrimina); guard de staff en el layout de administración, `/calculadora` pública, `/mis-proformas` con guard de sesión; 401 de cliente sin recarga; barrera real = servidor (`IsStaffUser`, sin cambios). Rollback: revertir el guard y quitar rutas/modal.
- **API de cliente:** `Client.car_plate` (migración `0115` aditiva), `POST client/register` (throttle, `validate_password`, username opcional, nunca `is_staff`), `GET client/me`, `GET client/proformas` (propias, `is_delete=False`); `create_client` e `invoice/all` intactos; guardado con `POST invoice`. Despliegue: backend primero, frontend después.
- **Catálogo:** la calculadora usa `calculator_info` / `model_parts` / `get_inventory` públicos; se agregan `is_active` e `image` de forma aditiva (afecta también a `proforma/`: desaparecen los inactivos, consistente con el ADR de vehículos).
- **Dinero:** el servidor sigue recalculando (ADR-004); en cliente los importes son vista previa con `previewSubtotal` (`Number`, igual que hoy), nunca autoritativos; los importes enviados a `invoice` se ignoran. **No** se persiste en `localStorage` PII del cliente (ADR-003): el perfil va en memoria.
- **Seguridad:** `client/me` y `client/proformas` filtran por `request.user` sin parámetros de id (ADR-006-idor); registro con throttle; contraseña con validadores de Django; el serializer no expone `is_staff`/grupos/permisos.
- **Rendimiento:** `client/proformas` con `select_related('car_model_id__car_brand_id')` (sin N+1); catálogos públicos: una llamada por cambio de modelo/sucursal, muy por debajo del throttle de `get_inventory` (60/min).
- **Acoplamiento:** se tocan `get_calculator_info` (lo consume `proforma/`: pruebas de no regresión), `ErrorInterceptor` (todo el panel: staff mantiene el comportamiento actual) y `app.routes.ts` (guard del layout de administración: verificar que staff sigue entrando).

## Proposed solution

**Backend (`praxsa_manager/product/`)**: migración + campo en `Client`; `serializer/client_register_serializer.py`; `custom_views/client_api.py` (`ClientRegisterView`, `ClientMeView`, `ClientProformasView`, throttle `ClientRegisterThrottle`); rutas `client/register|me|proformas` en `urls.py`; tasa `client_register` en `settings.py`; `get_calculator_info` con `is_active` e `image`.
**Frontend (`panel_admin/src/app/`)**: `AuthService` (estado de sesión y evento de sesión vencida); `StaffGuard` y `SessionGuard`; `ErrorInterceptor` diferenciado; layout/header con estado de sesión; módulo `cliente/` (modelo, servicio, modal de acceso con registro en 2 etapas, lista Mis proformas, rutas); `calculadora/` adaptada (catálogo público con adaptadores, acciones según sesión).

## Files/components affected

**Backend (nuevos):** `product/migrations/0115_client_car_plate.py`; `product/serializer/client_register_serializer.py`; `product/custom_views/client_api.py`; `product/tests/test_client_api.py`.
**Backend (modificados):** `product/models.py` (`Client.car_plate`); `product/urls.py`; `praxsa_manager/settings.py` (`DEFAULT_THROTTLE_RATES`); `product/views.py` (`get_calculator_info`); `product/tests/test_public_catalog_endpoints.py` (no regresión del catálogo).
**Frontend (nuevos):** `core/guard/staff.guard.ts`, `core/guard/session.guard.ts` (+ specs); `cliente/cliente.model.ts`, `cliente.service.ts`, `acceso-modal.component.{ts,html}` (+ servicio de apertura), `mis-proformas.component.{ts,html}`, `cliente.routes.ts` (+ specs); estilos en `assets/scss/_calculadora.scss` (o parcial `_cliente.scss` importado en `style.scss`).
**Frontend (modificados):** `core/service/auth.service.ts`, `core/index.ts`, `core/interceptor/error.interceptor.ts`, `app.routes.ts`, `layout/header/header.component.{ts,html}`, `layout/app-layout/minimal-layout/*`, `calculadora/calculadora.component.{ts,html}`, `calculadora.service.ts`, `calculadora.model.ts`, `calculadora.helpers.ts` (adaptadores) y sus specs.
**Sin cambios:** `proforma/`, `create_client`, `invoice/all`, `PanelAdminAuthToken`, endpoints de staff, `ProformaFormComponent` (se conserva la precarga de la v1 para staff).

## Implementation steps

**Fase 0 — Base**
0.1. Traer `origin/master` a la rama (ver nota de verificación) y confirmar que `ng test`/`manage.py test` parten igual que master.

**Fase 1 — Backend (se despliega primero)**
1.1. `Client.car_plate` (`CharField(max_length=10, blank=True, default='')`) + migración `0115` generada con `makemigrations`; `makemigrations --check --dry-run` limpio.
1.2. `ClientRegisterSerializer`: campos `name, lastname, email, phone_number, car_plate, username (opcional), password`; `email` único (como `ClientSerializer`); `username` único sin distinguir mayúsculas y sin espacios, por defecto el correo; `validate_password` con el usuario; teléfono con la regex actual; placa ≤ 10; `create` en transacción creando `User` (sin `is_staff`/`is_superuser`/grupos) y `Client`. Campos no declarados (p. ej. `is_staff`) se ignoran.
1.3. `ClientRegisterView` (`AllowAny`, `ClientRegisterThrottle` con scope `client_register`), `ClientMeView` y `ClientProformasView` (`TokenAuthentication` + `IsAuthenticated`; `me` → 404 sin `Client`; `proformas` filtra `created_by`, `is_delete=False`, orden por fecha descendente, `select_related` de modelo y marca, importes como string). Rutas `client/register`, `client/me`, `client/proformas` y tasa `client_register` (10/hora por IP, configurable).
1.4. `get_calculator_info`: filtrar `is_active=True` en marcas, modelos, partes y láminas; agregar `image` (URL absoluta con `request.build_absolute_uri`, `null` si no hay) a cada modelo; sin quitar campos existentes.

**Fase 2 — Sesión y aislamiento (frontend)**
2.1. `AuthService`: getters de sesión (`isLoggedIn`, `isStaff`, `isClient` = sesión con `isStaff` falso) y `sessionExpired$`; `@core` los exporta. Sin cambios en el formato guardado del `User`.
2.2. `StaffGuard` (staff → pasa; sin sesión → `authentication/signin`; cliente → `/calculadora`) y `SessionGuard` (con sesión → pasa; sin sesión → `/calculadora` con el modal abierto; staff en `/mis-proformas` → `/dashboard/main`).
2.3. `app.routes.ts`: `StaffGuard` en el padre `MainLayoutComponent`; `calculadora` **sin guard** bajo `MinimalLayoutComponent`; nueva ruta `mis-proformas` bajo el mismo layout con `SessionGuard`.
2.4. `ErrorInterceptor`: ante 401, si la sesión era de staff → comportamiento actual (logout + recarga); si era de cliente → logout, **sin recarga**, emite `sessionExpired$`; 401 sin sesión previa en rutas de cliente no recarga. La recarga se aísla en un método para poder probar.

**Fase 3 — Módulo `cliente/`**
3.1. `cliente.model.ts` (perfil, payload de registro, fila de lista) y `cliente.service.ts` (`register`, `me`, `proformas`, `createInvoice` → `POST product/invoice`).
3.2. Modal de acceso (`NgbModal`, patrón `pago-modal`): modo **Iniciar sesión** (usuario + contraseña con mostrar/ocultar, errores "Credenciales inválidas"/"No se pudo conectar") y modo **Crear cuenta** en 2 etapas con el indicador del DDR; validación por etapa; usuario sugerido = correo (editable); confirmar contraseña solo en cliente; errores de servidor sobre el campo (correo/usuario duplicado vuelve a la etapa 1); éxito → `AuthService.login` automático; el modal cierra devolviendo el resultado a quien lo abrió. Servicio de apertura reutilizable por el header y la calculadora.
3.3. `MisProformasComponent`: `ngx-datatable` (Nº, Fecha `dd/MM/yyyy`, Vehículo, Placa, Total `Bs`), 10 por página, orden por fecha descendente, estados cargando/vacío/error, botón "Nueva cotización", resalta la fila recién guardada (id recibido por navegación) y muestra el toast.

**Fase 4 — Calculadora y encabezado**
4.1. `CalculadoraService` + adaptadores a los tipos existentes: sucursales/marcas/modelos de `calculator_info` (con imagen), ítems de `model_parts/<id>` (normalizando `installation_price` de `float` a string), bobinas de `get_inventory/<sucursal>/0/0` (`bobina_film_id/name`, `bobina_width`, `bobina_metros_disponibles`, `bobina_price` → `ReelCatalogItem`); se deja de usar `OrdenesService`/`VehiclesService` en `calculadora/`. Cálculo y filtro de aptitud sin cambios.
4.2. `CalculadoraComponent`: sin guard; acciones según sesión — anónimo: "Crear Proforma" abre el modal; cliente: guardar (perfil + `createInvoice` + navegación a `/mis-proformas`); staff con permiso: camino de la v1 (formulario interno); staff sin permiso: botón oculto. `sessionExpired$` reabre el modal y reintenta el guardado con la cotización conservada. Resumen con "A nombre de / Placa" cuando hay sesión. Errores del servidor en el resumen.
4.3. Header (variante mínima): anónimo → "Iniciar sesión" / "Crear cuenta"; cliente → **Calculadora** · **Proformas** + dropdown (nombre, Logout); staff → enlace "Panel" en lugar de "Proformas" + Logout; enlace activo marcado; visible y usable en móvil (enlaces envueltos, Logout siempre accesible).

**Fase 5 — Verificación**
5.1. `ng lint`, `ng build` (producción, cuidando el presupuesto de estilos: todo en parciales globales), `ng test` y `manage.py test`.
5.2. Verificación manual en vivo (ver Test strategy) y revisión de los textos pendientes del DDR.

## Test strategy

Patrones: backend `praxsa_manager/product/tests/` con `helpers.py` (`create_user_with_token`, `create_staff_user`, `build_full_scenario`) y `build_invoice_payload` de `test_invoice_pricing.py`; frontend `TestBed` + `HttpTestingController`.

**Backend (integración, BD real de pruebas) — `test_client_api.py`:**
- Registro: éxito (crea `User` no staff y `Client` con placa; username por defecto = correo; `is_staff`/`groups` del payload ignorados); correo y username duplicados (incluido distinto case); contraseña débil/común/similar rechazada; teléfono y placa inválidos; throttling (con `override_settings` de la tasa); no devuelve token ni contraseña.
- Login del panel con la cuenta nueva devuelve token con `is_staff=False`, sin grupos ni permisos.
- `client/me`: 200 con los datos; 401 sin token; 404 para un usuario sin `Client`.
- `client/proformas`: solo las propias (no las de otro cliente ni las creadas por staff), excluye `is_delete`, orden descendente, forma de la respuesta (id, fecha ISO, marca, modelo, placa, total string); 401 anónimo.
- Flujo: cliente hace `POST invoice` (con importes manipulados → el servidor recalcula) y la proforma aparece en `client/proformas`.
- **Aislamiento:** el token de un cliente recibe 403 en `ordenes/proformas`, `ordenes/catalogo/sucursales`, `vehicles/models`, `almacen/laminas` y `users`.
- `get_calculator_info` (en `test_public_catalog_endpoints.py`): excluye marcas/modelos/partes/láminas inactivos; incluye `image` (URL absoluta o `null`); las claves anteriores siguen presentes.
- `makemigrations --check --dry-run` sin migraciones pendientes y `manage.py test` completo.

**Frontend:**
- Unitarios/servicio: adaptadores del catálogo público (tipos y normalización de importes), borrador/payload de `invoice`, `ClienteService` (URLs y cuerpos), `AuthService` (getters, evento).
- Guards: `StaffGuard` (staff, cliente, anónimo) y `SessionGuard`; `ErrorInterceptor` (staff recarga, cliente no recarga y emite el evento, 401 anónimo).
- Componente: modal de acceso (login ok/error; registro: validación por etapa, sugerencia de usuario, contraseñas distintas, errores de servidor que devuelven a la etapa 1, login automático al crear); `MisProformasComponent` (columnas, formato de fecha/total, estados, resaltado); `CalculadoraComponent` (anónimo abre el modal; cliente guarda con el payload esperado y navega; sesión vencida reabre y reintenta; staff conserva el camino de la v1; catálogo público; errores); header (anónimo/cliente/staff); `proforma-form` no regresiona.
- Los specs de la v1 que dependen de `OrdenesService`/`VehiclesService` se migran al nuevo origen de datos.

**E2E (Playwright): NO corresponde en este plan.** Aunque el flujo es de punta a punta (registro → login → guardar → lista), no hay infraestructura E2E en el repositorio, agregar Playwright es una dependencia nueva que requiere confirmación, y el riesgo principal (autorización y aislamiento) queda cubierto por pruebas de integración del backend (403 en recursos de staff, filtrado por propietario) y de componente/guard en el frontend. En su lugar es **obligatoria una verificación manual en vivo contra el backend real de desarrollo** (con confirmación previa del usuario antes de crear cuentas de prueba en su base de datos de desarrollo), que cubre: (1) anónimo cotiza y pulsa Crear → modal; (2) registro completo y guardado → aparece en Mis proformas; (3) cliente tecleando `#/users`, `#/ordenes`, `#/almacen` → vuelve a la calculadora y no ve el sidebar; (4) sesión vencida (token inválido) al guardar → modal sin perder la cotización; (5) staff: login por el panel, menú completo, acceso a administración y camino de la v1; (6) correo duplicado y contraseña débil; (7) móvil y tema oscuro; (8) `proforma/` (cliente antiguo) sigue iniciando sesión, registrándose y cotizando con los catálogos modificados.

## Acceptance criteria

1. `Client.car_plate` existe con migración `0115` reversible; `makemigrations --check --dry-run` limpio; los clientes existentes quedan con placa vacía.
2. `POST client/register` crea un usuario **no staff** con `Client` y placa, con username opcional (por defecto el correo), contraseña validada por Django, duplicados rechazados y throttling; `create_client` y `proforma/` siguen funcionando igual.
3. `GET client/me` y `GET client/proformas` devuelven solo datos del usuario autenticado, sin proformas borradas ni ajenas; responden 401 sin token.
4. Un token de cliente recibe 403 en los endpoints de administración (`ordenes/*`, `vehicles/*`, `almacen/*`, `users/*`).
5. `get_calculator_info` no lista marcas/modelos/partes/láminas inactivos e incluye `image`; las claves existentes no cambian.
6. `/calculadora` abre sin sesión y usa solo catálogos públicos; el encabezado muestra "Iniciar sesión/Crear cuenta" (anónimo) o Calculadora · Proformas + usuario (cliente); nunca hay sidebar en esas rutas.
7. "Crear Proforma" sin sesión abre el modal; con sesión de cliente guarda con los datos de la cuenta (`created_by` = el cliente), el servidor recalcula el total y la persona llega a `/mis-proformas` con toast y fila resaltada.
8. El registro por etapas valida cada etapa, sugiere el correo como usuario, exige contraseñas iguales, vuelve a la etapa 1 ante correo duplicado y, al crear la cuenta, inicia sesión y continúa el guardado.
9. Con el token vencido al guardar, el modal se reabre **sin recargar** y el guardado se reintenta con la cotización conservada; para staff el 401 sigue recargando.
10. `/mis-proformas` exige sesión (anónimo → calculadora con modal), es de solo lectura y muestra Nº, fecha `dd/MM/yyyy`, vehículo, placa y total con estados cargando/vacío/error.
11. Un cliente que escribe una URL de administración termina en la calculadora; staff sigue entrando a todo el panel y conserva el flujo de la v1.
12. `ng lint` y `ng build` de producción limpios; specs nuevos y migrados en verde sin fallos nuevos frente a master; `manage.py test` completo en verde.
13. No se guarda PII del cliente en `localStorage` más allá de los campos actuales del `User`.

## Risks

- **Seguridad/autorización (alto):** el aislamiento depende del guard de staff en el frontend y de `IsStaffUser` en el servidor; mitigación: pruebas de 403 por recurso y verificación manual del punto (3). Un usuario no-staff que hoy use el panel (hipótesis: ninguno, porque los endpoints exigen `is_staff`) cambiaría de "panel roto" a "redirige a la calculadora": revisar la lista de usuarios antes de desplegar.
- **Registro público:** abuso/spam de cuentas; mitigación: throttle y validación de contraseña; sin verificación de correo (fuera de alcance).
- **Cambio en `get_calculator_info`:** afecta a `proforma/` (los inactivos dejan de listarse); mitigación: prueba de no regresión y cambio de una línea revertible.
- **`ErrorInterceptor` compartido:** un error en la rama de cliente podría afectar al staff; mitigación: pruebas por rama y mantener la ruta actual para staff.
- **Rama desactualizada (9 commits):** posibles conflictos con PR #58 en `settings.py` y specs de vehículos; mitigación: sincronizar primero (Fase 0).
- **`POST invoice` no valida ancho/metros en servidor** (deuda de ADR): el UI filtra, pero un cliente malicioso podría guardar una proforma con lámina no apta; mitigación: el precio siempre se recalcula y el stock se valida al generar la nota de trabajo; queda fuera de alcance.
- **`proforma_created_on` es `auto_now`:** la fecha mostrada cambia si se edita la proforma; se acepta (deuda del ADR).
- **Dos registros y dos listados** (legado y nuevo) hasta migrar `proforma/`.
- **Presupuesto de estilos de componente (REV-01 de Órdenes):** todo el SCSS nuevo va en parciales globales.
- **Importes con `Number`** en la vista previa y `float` en `model_parts`: no autoritativo; nunca se confía en el servidor.
- **Sin mitigación** para: verificación de correo/recuperación de contraseña y número de WhatsApp por sucursal (fuera de alcance).

## Out of scope

- Verificación de correo, recuperación/cambio de contraseña, edición de perfil, detalle/PDF/estado de proformas para el cliente.
- Migrar `proforma/` al nuevo registro/listado o retirar `create_client` e `invoice/all`.
- Reglas de ancho/metros en `POST invoice`, "Recomendada", WhatsApp por sucursal, formato final de importes.
- Login por correo (solo por usuario), CI/NIT en el registro, asociar proformas de staff a clientes.
- Retirar el ítem "Calculadora de precios" del menú de staff o cambiar el flujo de staff (decisión de negocio pendiente).
- Playwright y cambios de infraestructura/Docker/nginx.

**Preguntas abiertas (no bloquean; hay valor por defecto en los ADR):** ¿el staff conserva su flujo y el ítem de menú?; ¿login solo por usuario o también por correo?; ¿CI/NIT obligatorio para la proforma?; ¿tasa de registro de 10/hora por IP es aceptable?; número de WhatsApp global y formato `Bs 2.090`.

## Dependencias nuevas

Ninguna (no se agregan paquetes; `ngx-toastr` y `@ng-bootstrap/ng-bootstrap` ya están en `panel_admin/package.json`).

## Changelog

- **v2** (2026-09-30): cambio de alcance pedido por el usuario tras ver la v1: la calculadora pasa de herramienta de staff a flujo de cliente final (modal de acceso con registro en 2 etapas, menú Calculadora/Proformas, lista de proformas de solo lectura, guardado directo, sin sidebar ni acceso a administración) dentro de `panel_admin/`, con la placa en la cuenta. Se agregan backend (migración, registro, perfil y lista propios, catálogo público con `is_active`/`image`), guards y manejo de 401, y el módulo `cliente/`. Reescribe las fases de la v1 sobre lo ya implementado. Solicitado por el usuario (nuevo requerimiento; sin referencia a REV).
- **v1** (2026-09-30): plan original (calculadora de staff con layout mínimo, módulo `calculadora/`, borrador hacia el formulario de proforma, ítem de menú); implementado en PR #60. Sus fases 1–5 se consideran hechas y quedan como base de v2.
