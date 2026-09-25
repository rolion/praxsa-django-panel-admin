# PLAN-2026-09-25-login-panel-admin-backend (v1)

**Task:** TASK-login-panel-admin-backend
**DDRs relacionados:** [DDR-login-panel-admin-backend-login-branding-menu](../design/DDR-login-panel-admin-backend-login-branding-menu.md)
**ADRs relacionados:** [ADR-login-panel-admin-backend-staff-auth-endpoint](../adr/ADR-login-panel-admin-backend-staff-auth-endpoint.md)

## Objective

Conectar el login de la plantilla `panel_admin/` (hoy 100% mock) al backend real de PRAXSA, con branding propio (logo + imagen de auto) y un menú/lateral/header reducidos a lo mínimo necesario, para tener un panel administrativo funcional que reemplace el mock de la plantilla comercial.

## Context

Ver `TASK-login-panel-admin-backend` (`## Investigación`) para el detalle completo. Resumen de lo relevante:
- `panel_admin/` es Angular 21 standalone, proyecto independiente de `proforma/` (Angular 16).
- El login/sidebar/header de `panel_admin/` vienen 100% de la plantilla comercial "Oreva", sin conexión a datos reales.
- El backend ya tiene un mecanismo de token (DRF `TokenAuthentication`) probado en `proforma/`, pero el endpoint existente (`/product/api-token-auth/`) depende de un modelo `Client` que los usuarios de `panel_admin/` no van a tener.
- Decisión de negocio explícita del usuario: por ahora **no hay verificación de rol** — cualquier usuario válido de Django entra al dashboard de `panel_admin/`. La redirección futura de usuarios `staff` hacia `proforma/` queda fuera de este task.
- No existe en el repo ningún asset gráfico (logo o foto de auto) que coincida con la referencia visual del usuario (verificado abriendo los 3 assets PRAXSA existentes).

## Current behavior

- **Backend**: `/product/api-token-auth/` (`praxsa_manager/product/custom_views/auth_token.py:1-29`) es el único login. Depende de `Client.objects.get(user_id=user)` (línea 14) sin manejo de excepción.
- **Login `panel_admin/`**: `core/service/auth.service.ts:15-56` — array hardcodeado en memoria (`admin@email.com`/`admin@123`), sin `HttpClient`. `signin.component.ts:30-31` precarga esas credenciales en el formulario. `signin.component.html:6,12` usa `assets/images/login.jpg` y `assets/images/logo.png` + texto "Oreva", más enlaces de "Remember me", "Forgot password", login social y "Sign Up" (líneas 32-72).
- **Interceptores**: `core/interceptor/jwt.interceptor.ts:19` antepone `Authorization: Bearer {token}` (el backend espera `Token {token}`). `core/interceptor/error.interceptor.ts:23` hace `err.error.message || err.statusText`, perdiendo el `status` original y sin poder distinguir "sin red" de "credenciales inválidas"; además puede fallar si `err.error` es `null`.
- **Sidebar**: `assets/data/routes.json` alimenta `sidebar.service.ts:17-22`, hoy con 6 grupos de menú (Dashboard con 2 sub-ítems, Advance Table, Authentication, Extra Pages, Multi-level Menu). El propio sidebar (`sidebar.component.html:4-7`) tiene además su logo "Oreva" arriba, y un bloque separado `.sidebar-user-panel` (líneas 13-21) con nombre hardcodeado "Emily Smith" — **distinto** del menú de usuario del header.
- **Header, menú de usuario**: `header.component.html:164-183` — trigger es un avatar; el panel abierto dice `"Hello Sarah.."` y enlaces a `/extra-pages/profile`, `/email/inbox` (rutas que no existen) y "Settings" (inerte), más "Logout" (funcional, `header.component.ts:166-172`).
- **Dashboard**: `dashboard/main/main.component.ts:44-279` solo pinta gráficos ApexCharts con datos ficticios — no se toca.

## Expected behavior

1. El usuario ingresa usuario/contraseña reales en el login de `panel_admin/`; si son correctos, el backend emite un token y el usuario entra a `/dashboard/main`.
2. Si el usuario no existe o la contraseña es incorrecta, se muestra "Credenciales inválidas" y no se navega.
3. El login, el logo del sidebar y el logo del menú de usuario muestran el branding de PRAXSA (logo generado); el panel izquierdo del login muestra la imagen de auto generada.
4. El sidebar solo lista "Dashboard".
5. El menú de usuario del header muestra el logo de PRAXSA encima del nombre real del usuario autenticado, y solo la opción "Logout" además de esa identidad (sin Profile/Email/Settings).

## Architecture considerations

Resumen del ADR (ver enlace arriba, detalle completo ahí):
- Se crea un endpoint nuevo `POST /product/api-panel-admin-token-auth/` (vista `PanelAdminAuthToken`), que valida credenciales igual que `CustomAuthToken` (mismo `AuthTokenSerializer` de DRF) pero **no depende de `Client`** y **no verifica rol**. Responde `{token, user_id, username, name, lastname}` tomando `name`/`lastname` de `user.first_name`/`user.last_name`.
- El endpoint existente `/product/api-token-auth/` no se toca — sigue siendo exclusivo de `proforma/`.
- Cambio aditivo, sin migraciones. No rompe ningún contrato que Angular ya consuma.
- **CORS**: `panel_admin/` no tiene puerto de desarrollo propio configurado (usa el default de Angular CLI, 4200 — el mismo que `proforma/`, ya whitelisteado en `praxsa_manager/praxsa_manager/settings.py:94-110`). No se agrega ninguna entrada nueva a `CORS_ORIGIN_WHITELIST` en este plan porque no hay un puerto nuevo confirmado que lo necesite; si en desarrollo se decide correr `panel_admin/` en un puerto distinto (para tenerlo abierto junto a `proforma/`), quien lo configure deberá agregar ese puerto al whitelist como paso manual, fuera de este cambio de código.
- **Dominio de producción de `panel_admin/`**: no confirmado en la investigación (existe `https://panel.praxsasrl.store` en el whitelist, pero la investigación no confirmó qué app lo usa hoy). Este plan **no** fija ninguna URL de producción para `panel_admin/` — ver "Out of scope".

## Proposed solution

### Backend (`praxsa_manager/`)

1. Agregar `PanelAdminAuthToken(ObtainAuthToken)` en `praxsa_manager/product/custom_views/auth_token.py` (junto a `CustomAuthToken`): valida con `AuthTokenSerializer`, `Token.objects.get_or_create(user=user)`, responde `{token, user_id, username: user.username, name: user.first_name, lastname: user.last_name}`. Sin `Client`, sin chequeo de `is_staff`.
2. Montar la ruta en `praxsa_manager/product/urls.py`: `path('api-panel-admin-token-auth/', PanelAdminAuthToken.as_view())`.

### Frontend (`panel_admin/`)

3. `src/environments/environment.development.ts` y `environment.ts`: corregir `apiUrl` de desarrollo a `http://localhost:8000` (el dev server de `praxsa_manager/`, mismo valor que ya usa `proforma/` en su `environment.ts`). El valor de producción de `environment.ts` queda como placeholder documentado (ver "Out of scope" — no se confirma la URL real de producción del backend para `panel_admin/`).
4. `core/models/user.ts`: quitar el campo `password` (ya no hace falta comparar contraseñas en el cliente).
5. `core/service/auth.service.ts`: reemplazar el array hardcodeado y la comparación en memoria por un `HttpClient.post` real a `` `${environment.apiUrl}/product/api-panel-admin-token-auth/` `` con `{username, password}`. Al éxito: mapear la respuesta a `User` (`name` del backend → `firstName`, con fallback a `username` si `name` viene vacío — usuarios creados con `createsuperuser` no tienen `first_name`), persistir con `LocalStorageService` (mismo patrón ya existente) y notificar `currentUserSubject`. Al error: dejar que se propague (ver punto 7).
6. `core/interceptor/jwt.interceptor.ts:19`: cambiar `Bearer ${currentUser.token}` por `Token ${currentUser.token}`.
7. `core/interceptor/error.interceptor.ts:23`: dejar de transformar el error en un string temprano — reemplazar `throwError(error)` por `throwError(() => err)` (propagar el `HttpErrorResponse` original), manteniendo el auto-logout en `401` (líneas 17-21) intacto. Esto es necesario para que el componente de login pueda distinguir "sin conexión" (`status === 0`) de "credenciales inválidas" (`status === 400`), igual que ya hace `proforma/` (`login.component.ts:38-51`).
8. `authentication/signin/signin.component.ts`:
   - Quitar los valores por defecto hardcodeados (`admin@email.com`/`admin@123`) del formulario.
   - En el callback de error de `onSubmit()`, mostrar `'Credenciales inválidas'` para cualquier error del login (sin exponer el mensaje crudo del backend), y un mensaje distinto (p. ej. `'Algo salió mal, inténtalo de nuevo más tarde'`) solo si `error.status === 0` — mismo patrón que `proforma/`.
9. `authentication/signin/signin.component.html`: quitar "Remember me", "Forgot password?", "Or Login With" (redes sociales) y "Don't have an account? Sign Up" (líneas 32-72 del archivo actual). Reemplazar `assets/images/login.jpg` por el asset de auto generado y `assets/images/logo.png` + texto "Oreva" por el logo generado + wordmark "PRAXSA".
10. `layout/sidebar/sidebar.component.html:4-7`: reemplazar el logo del sidebar por el mismo logo generado.
11. `src/assets/data/routes.json`: reemplazar todo el contenido por una sola entrada apuntando a `/dashboard/main`, sin submenú (ver punto 13 para el título).
12. `layout/header/header.component.html:164-183`: reemplazar el trigger (avatar) y el título `"Hello Sarah.."` por el logo generado (pequeño) apilado sobre el nombre real del usuario (`currentUserValue.firstName`, con el mismo fallback a `username`); quitar los enlaces "Profile", "Email" y "Settings"; conservar "Logout".
13. `src/assets/i18n/es.json` (y `en.json`, `de.json` si se quiere mantener el soporte multi-idioma ya presente): agregar una clave nueva de menú, p. ej. `MENUITEMS.DASHBOARD.TEXT` = `"Dashboard"`, en vez de reutilizar `MENUITEMS.HOME.LIST.DASHBOARD1` (que dice "Tablero 1", pensado para distinguir de un "Tablero 2" que ya no aparece en el menú).
14. Generar los dos assets nuevos en `src/assets/images/` (p. ej. `praxsa-logo.svg`, `praxsa-login-hero.svg`) — **nota de alcance de herramienta**: este entorno no tiene una herramienta de generación de imágenes fotorrealistas; "generar" acá significa construir gráficos vectoriales (SVG) a mano que sigan el lenguaje visual de la referencia (ícono "P" en degradado azul + wordmark "PRAXSA"; para el auto, una ilustración vectorial estilizada de un auto con vidrios polarizados sobre fondo oscuro con overlay azul, no una fotografía). Si el usuario esperaba una fotografía realista, esto debe confirmarse como una limitación antes de dar el task por cerrado.

## Files/components affected

**Backend:**
- `praxsa_manager/product/custom_views/auth_token.py` (nueva vista)
- `praxsa_manager/product/urls.py` (nueva ruta)
- `praxsa_manager/product/tests/test_panel_admin_auth.py` (nuevo)

**Frontend (`panel_admin/`):**
- `src/environments/environment.development.ts`, `src/environments/environment.ts`
- `src/app/core/models/user.ts`
- `src/app/core/service/auth.service.ts` (+ `auth.service.spec.ts`)
- `src/app/core/interceptor/jwt.interceptor.ts`
- `src/app/core/interceptor/error.interceptor.ts`
- `src/app/authentication/signin/signin.component.ts`, `signin.component.html` (+ `signin.component.spec.ts`)
- `src/app/layout/sidebar/sidebar.component.html`
- `src/app/layout/header/header.component.html`, `header.component.ts` si hace falta exponer `currentUserValue` a la plantilla (+ `header.component.spec.ts`)
- `src/assets/data/routes.json`
- `src/assets/i18n/es.json`, `en.json`, `de.json`
- `src/assets/images/praxsa-logo.svg` (o `.png`), `src/assets/images/praxsa-login-hero.svg` (o `.jpg`/`.png`) — nuevos

## Implementation steps

1. Backend: agregar `PanelAdminAuthToken` + ruta nueva.
2. Backend: test `test_panel_admin_auth.py` (login exitoso sin `Client`, credenciales inválidas, usuario inexistente).
3. Frontend: corregir `environment.development.ts`/`environment.ts` (`apiUrl`).
4. Frontend: `core/models/user.ts` — quitar `password`.
5. Frontend: reescribir `auth.service.ts` (`login()` real vía `HttpClient`, mapeo de respuesta con fallback de nombre).
6. Frontend: `jwt.interceptor.ts` — `Token` en vez de `Bearer`.
7. Frontend: `error.interceptor.ts` — propagar `HttpErrorResponse` original.
8. Frontend: `signin.component.ts` — quitar defaults hardcodeados, mapear error a "Credenciales inválidas" / mensaje de red.
9. Frontend: `signin.component.html` — recortar campos no pedidos, insertar assets nuevos (una vez generados en el paso 14).
10. Frontend: `assets/data/routes.json` — reducir a una entrada "Dashboard".
11. Frontend: `es.json`/`en.json`/`de.json` — clave de menú nueva.
12. Frontend: `sidebar.component.html` — logo nuevo.
13. Frontend: `header.component.html`/`.ts` — logo + nombre real + recorte de enlaces.
14. Generar los dos assets SVG y ubicarlos en `src/assets/images/`.
15. Actualizar specs existentes que hoy asumen el mock (`auth.service.spec.ts`, `signin.component.spec.ts`, `header.component.spec.ts`) para que sigan pasando con la implementación real.
16. Smoke test manual: levantar `praxsa_manager/` (`python manage.py runserver`) y `panel_admin/` (`npm start`), crear un usuario de prueba con `python manage.py createsuperuser` (o un usuario común, ya que no hay chequeo de rol), y verificar a mano: login correcto → dashboard; contraseña incorrecta → "Credenciales inválidas"; usuario inexistente → "Credenciales inválidas"; sidebar solo muestra Dashboard; header muestra logo + nombre real.

## Test strategy

**Justificación de E2E: NO corresponde.** El flujo es un login de un solo paso (usuario/contraseña → dashboard), no una navegación multi-paso ni un flujo de negocio crítico como proforma→pago. El contrato del backend puede verificarse con el cliente de test de Django contra el endpoint real (sin mocks), y el comportamiento del frontend (forma de la petición, mapeo de la respuesta, manejo de error) puede verificarse con `TestBed` + `HttpTestingController` sin necesitar un navegador real. `panel_admin/package.json` tampoco tiene Playwright instalado — no se justifica agregarlo para este cambio. El smoke test manual del paso 16 cubre la integración real end-to-end sin necesidad de automatizarla todavía.

**Backend (`praxsa_manager/product/tests/test_panel_admin_auth.py`, patrón `helpers.py` + `APIClient`):**
- Login exitoso con un usuario creado vía `create_user_with_token` (sin `Client` asociado) → `200`, respuesta incluye `token`, `user_id`, `username`, `name`, `lastname`.
- Contraseña incorrecta → `400` con `non_field_errors`.
- Usuario inexistente → `400` con `non_field_errors`.
- (Opcional, refuerza la decisión del ADR) Login exitoso con un usuario `is_staff=True` sin `Client` → `200` — confirma que no se aplica ningún filtro de rol.

**Frontend (`panel_admin/`, `TestBed` + `HttpTestingController`, mismo patrón que ya usan los `.spec.ts` existentes):**
- `auth.service.spec.ts`: `login()` hace `POST` a la URL esperada con el body correcto; en éxito persiste `currentUser` y emite por `currentUser$`; en error (400) no persiste nada y propaga el error.
- `signin.component.spec.ts`: al recibir un error 400 del servicio, `error` queda en `'Credenciales inválidas'`; al recibir `status: 0`, queda en el mensaje de "sin conexión"; en éxito, navega a `/dashboard/main`.
- `header.component.spec.ts`: el nombre mostrado viene de `authService.currentUserValue` (con el fallback a `username` cuando `firstName` está vacío), y los enlaces "Profile"/"Email"/"Settings" ya no están presentes en el DOM.

## Acceptance criteria

- [ ] `POST /product/api-panel-admin-token-auth/` autentica un usuario de Django real (con o sin `Client`, con o sin `is_staff`) y devuelve un token.
- [ ] Login con usuario/contraseña incorrectos o usuario inexistente muestra "Credenciales inválidas" en la pantalla de login de `panel_admin/`, sin navegar.
- [ ] Login exitoso navega a `/dashboard/main` (contenido del dashboard sin cambios).
- [ ] El login muestra el logo de PRAXSA generado y la imagen de auto generada, sin "Remember me"/"Forgot password"/login social/"Sign Up".
- [ ] El sidebar izquierdo solo lista "Dashboard" (sin Advance Table, Authentication, Extra Pages, Multi-level Menu) y su logo es el de PRAXSA.
- [ ] El menú de usuario del header muestra el logo de PRAXSA sobre el nombre real del usuario autenticado, con solo la opción "Logout" además de esa identidad.
- [ ] `proforma/` sigue funcionando sin cambios (no se tocó `/product/api-token-auth/`).
- [ ] Tests backend y frontend nuevos/actualizados pasan.

## Risks

- **El asset del auto será una ilustración vectorial, no una fotografía real** — ver nota del paso 14. Mitigación: confirmarlo explícitamente con el usuario antes de publicar el task como terminado; si se necesita una fotografía real, se puede pedir que la provea o buscar un banco de imágenes con licencia adecuada (fuera del alcance de este plan).
- **Cambiar el contrato de `error.interceptor.ts` (de string a `HttpErrorResponse`) es un cambio global** a un interceptor usado por toda la app. Mitigación: se verificó que ningún otro componente de `panel_admin/` consume hoy el valor de error de una petición HTTP real (las demás pantallas son datos de ejemplo sin backend); el único punto que cambia de comportamiento es `signin.component.ts`, que se actualiza en el mismo cambio.
- **El bloque `.sidebar-user-panel` del propio sidebar** (`sidebar.component.html:13-21`, nombre hardcodeado "Emily Smith") es un elemento visual distinto del menú de usuario del header y **no fue pedido explícitamente** ni decidido en el DDR. Se deja fuera de este plan (ver "Out of scope") para no inventar alcance no solicitado — pero queda visiblemente inconsistente con el resto del branding si no se actualiza en un cambio posterior.
- **Dominio de producción para `panel_admin/`** no confirmado — no se toca configuración de despliegue en este plan (ver "Out of scope").

## Out of scope

- Redirección de usuarios `is_staff` hacia `proforma/` (decisión de negocio explícitamente pospuesta, documentada en el ADR).
- Modelo de permisos/roles dentro del panel.
- Pantalla de registro (la referencia visual del usuario mostraba una, pero el requerimiento pedido es solo login — ver DDR).
- Eliminar del código fuente los módulos de ejemplo de la plantilla (`advance-table`, `extra-pages`, `multilevel`, `dashboard2`) — solo se dejan de listar en el menú.
- Fijar la URL de producción del backend para `panel_admin/` (`environment.ts` de producción queda con un placeholder documentado, no una URL real confirmada) y cualquier cambio de `CORS_ORIGIN_WHITELIST`/`CSRF_TRUSTED_ORIGINS` para un dominio de producción de `panel_admin/`.
- **Pregunta abierta para el usuario:** el bloque de "Emily Smith" dentro del propio sidebar (distinto del menú de usuario del header) — ¿se actualiza también en este task o se deja para después? Este plan asume que se deja para después, al no haber sido parte del pedido original ni del DDR.
- **Pregunta abierta para el usuario:** confirmar que un asset de auto en formato ilustración vectorial (no fotografía) es aceptable para este task.

## Dependencias nuevas

Ninguna. No se instala Playwright (no corresponde E2E) ni ninguna librería nueva; se reutiliza `rest_framework.authtoken` (ya instalado) y `HttpClient`/`ngbDropdown` ya presentes en `panel_admin/`.
