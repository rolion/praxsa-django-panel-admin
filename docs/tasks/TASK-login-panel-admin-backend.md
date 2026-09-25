# TASK-login-panel-admin-backend: Login de `panel_admin/` conectado al backend real, branding PRAXSA y menú mínimo

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** `task/TASK-login-panel-admin-backend`
**Pull Request:** https://github.com/rolion/praxsa-django-panel-admin/pull/46

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-09-25 | (nuevo) → INVESTIGATION | Task creado | delivery-investigate |
| 2026-09-25 | INVESTIGATION → ARCHITECTURE | Diseño de login/branding/menú completado | delivery-design |
| 2026-09-25 | ARCHITECTURE → PLANNING | Endpoint de auth dedicado (sin verificación de rol) definido | delivery-architect |
| 2026-09-25 | PLANNING → ENGINEERING | Plan v1 escrito, PR #46 abierto | delivery-plan |
| 2026-09-25 | ENGINEERING → REVIEW | Implementación completa, verificada con tests y smoke test manual | delivery-engineer |
| 2026-09-25 | REVIEW → PUBLISH | Quality Gate PASS (2 hallazgos Low, no bloqueantes) | delivery-review |
| 2026-09-25 | PUBLISH → PUBLISH | Plan versionado a v2 para resolver REV-01, a pedido del usuario | delivery-plan |
| 2026-09-25 | PUBLISH → PUBLISH | Descripción del PR completada; queda pendiente de aprobación humana explícita por ser cambio de autenticación | delivery-publish |

## Investigación

### Requerimiento
Adoptar la nueva plantilla Angular `panel_admin/` (ex-"Oreva", ya mergeada a `master`) para el login del panel administrativo de PRAXSA:
1. Usar la pantalla de login de `panel_admin/` como base visual.
2. Conectar ese login al backend real (`praxsa_manager/`) para autenticar usuarios reales — hoy es 100% mock.
3. Si el usuario no existe o la contraseña es incorrecta, mostrar el mensaje "credenciales inválidas".
4. Tras login exitoso, redirigir al dashboard actual de la plantilla (`/dashboard/main`), sin modificar su contenido por ahora.
5. Generar el logo de la empresa PRAXSA y una imagen de automóvil para reemplazar el branding genérico "Oreva" del login, en base a una referencia visual de diseño proporcionada por el usuario.
6. El menú lateral izquierdo debe mostrar solo la opción "Dashboard" (hoy tiene Dashboard con submenú, Advance Table, Authentication, Extra Pages y Multi-level Menu, todos de ejemplo).
7. El menú de usuario (header, superior derecho) debe mostrar solo el nombre del usuario autenticado, con el logo de PRAXSA encima del nombre (hoy muestra datos hardcodeados de la plantilla: "Sarah Smith"/"Hello Sarah..").

### Hechos encontrados

**Backend (`praxsa_manager/`) — autenticación ya existente:**
- `praxsa_manager/product/custom_views/auth_token.py:1-29` — `CustomAuthToken(ObtainAuthToken)` de DRF. Usa `TokenAuthentication` (modelo `Token` de `rest_framework.authtoken`), no JWT.
  - Valida credenciales con `AuthTokenSerializer` estándar (líneas 9-11); si son inválidas, DRF devuelve `HTTP 400` con `{"non_field_errors": ["Unable to log in with provided credentials."]}` (comportamiento estándar de DRF, `is_valid(raise_exception=True)` sin manejo custom).
  - Línea 14: `Client.objects.get(user_id=user)` **sin try/except** — si el usuario autenticado no tiene `Client` asociado, esto lanza `Client.DoesNotExist` y produce un `HTTP 500` en vez de una respuesta controlada.
  - Respuesta exitosa (líneas 15-28): `{token, user_id, email, name, lastname, phone_number, ci_nit}`.
- URL: `praxsa_manager/product/urls.py:19` → `/product/api-token-auth/` (montado bajo `praxsa_manager/praxsa_manager/urls.py:39`).
- No hay `DEFAULT_AUTHENTICATION_CLASSES` global en `settings.py`; cada vista protegida declara `authentication_classes = [authentication.TokenAuthentication]` explícitamente (ejemplo: `praxsa_manager/product/custom_views/invoice.py:15-18`).
- CORS (`praxsa_manager/praxsa_manager/settings.py`): `CORS_ORIGIN_ALLOW_ALL = False` (línea 86); whitelist (líneas 94-110) incluye `http://localhost:4200`, `4201`, `8081`, `8000`, `4000` y dominios de producción — **no hay un puerto reservado explícitamente para `panel_admin`**; si se levanta en un puerto no listado (Angular CLI por defecto usa 4200, que si está en la whitelist, pero puede chocar si `proforma/` también corre en 4200 simultáneamente en dev).
- `CSRF_TRUSTED_ORIGINS` (líneas 87-92) solo tiene dominios de producción, no localhost.
- No hay `djangorestframework-simplejwt` ni JWT instalado en el backend.

**Frontend `proforma/` — patrón de consumo actual del mismo endpoint (referencia a replicar):**
- `proforma/src/app/service/pybackend/authentication/authetication.service.ts:44-57` — `login()` hace `POST` a `${base_url}/product/api-token-auth/`, guarda **solo `token` y `name`** en `localStorage` (líneas 50-51), con comentario explícito citando `TASK-004/ADR-003` (reducción de PII en localStorage).
- `logout()` (líneas 58-70) limpia `token`, `name`, `lastname`, `phone_number`, `email`, `ci_nit`.
- `restoreMinimalSession()` (líneas 74-82): al bootstrap, si hay `token`, reconstruye sesión con solo `name`, resto vacío hasta el próximo login.
- Manejo de error: `proforma/src/app/components/login/login.component.ts:38-51` — si `error.status === 0` (fallo de red) muestra "Algo salió mal…"; en cualquier otro caso asigna literalmente `error.error` (body crudo de DRF) al arreglo de errores mostrado, sin mapear a un mensaje de negocio ni distinguir 400/401/403.
- `base_url` se resuelve por entorno: dev `http://localhost:8000` (`proforma/src/environments/environment.ts:6-7`), prod `https://panel.praxsasrl.store` (browser) / `http://web:5000` (SSR) (`environment.prod.ts:2-4`).

**Login actual de `panel_admin/` — 100% mock, sin backend:**
- `panel_admin/src/app/core/service/auth.service.ts:15-24` — array hardcodeado de un usuario en memoria (`admin@email.com` / `admin@123`, token literal `'admin-token'`). `login()` (líneas 37-56) no hace ninguna llamada HTTP, usa `of()`/`throwError()` de RxJS.
- Persiste en `LocalStorageService` propio de `panel_admin` bajo clave `currentUser`, pero **prefijada** por tema (`storage.service.ts:17-21` → `light_currentUser` / `dark_currentUser` según `config.layout.variant`).
- `panel_admin/src/app/core/interceptor/jwt.interceptor.ts:16-21` — antepone `Authorization: Bearer ${token}` a cada request; no valida JWT real, solo concatena el string. **Backend usa `Authorization: Token {token}` (DRF TokenAuthentication), no `Bearer`** — este interceptor no es compatible tal cual con el backend real.
- `panel_admin/src/app/core/interceptor/error.interceptor.ts:17-23` — en `401` hace logout + `location.reload()`; siempre intenta leer `err.error.message` sin chequear que `err.error` sea un objeto (rompe si es string o null, que es justamente lo que devuelve DRF en `non_field_errors`).
- `panel_admin/src/app/core/guard/auth.guard.ts:9-20` — solo verifica `currentUserValue` truthy (sin rol).
- `panel_admin/src/app/core/models/user.ts:1-8` — interfaz `User { id, username, password, firstName, lastName, token }`, sin `email`/`ci_nit`/etc. (distinto del modelo `User` de `proforma`).
- `panel_admin/src/app/authentication/signin/signin.component.ts:30-32` — formulario con credenciales default hardcodeadas (`admin@email.com`/`admin@123`); `onSubmit()` navega a `/dashboard/main` en éxito.
- `panel_admin/src/app/authentication/signin/signin.component.html:6,12` — imagen de fondo `assets/images/login.jpg` (genérica, sin relación a autos) y logo `assets/images/logo.png` + texto "Oreva" (branding de la plantilla comercial, no de PRAXSA). Incluye botones sociales inertes (Facebook/GitHub/Twitter/GitLab).

**Rutas y layouts de `panel_admin/`:**
- `panel_admin/src/app/app.routes.ts:7-49` — ruta raíz (`''`) usa `MainLayoutComponent` protegida por `AuthGuard`, con hijos `dashboard`, `advance-table`, `extra-pages`, `multilevel` (todos de ejemplo). Ruta `authentication` usa `AuthLayoutComponent` (sin guard, sin header/sidebar).
- `panel_admin/src/app/dashboard/dashboard.routes.ts` — `''` redirige a `main` (`MainComponent`); también existe `dashboard2` (ejemplo adicional, no mencionado por el usuario).
- `panel_admin/src/app/dashboard/main/main.component.ts:44-279` — dashboard actual solo pinta 3 gráficos ApexCharts con datos ficticios; no consume ningún servicio ni dato de usuario. El requerimiento pide dejarlo tal cual por ahora.
- `panel_admin/src/app/layout/sidebar/sidebar.service.ts:17-22` — el menú lateral se carga vía `HttpClient.get('assets/data/routes.json')`, no está hardcodeado en el componente. El archivo real es `panel_admin/src/assets/data/routes.json`, que hoy define grupos "MAIN" (Dashboard con submenú `dashboard/main` + `dashboard/dashboard2`), "Advance Table", grupo "-- Pages", "Authentication" (con 6 subitems de ejemplo), "Extra Pages" y "Multi level Menu".
- `panel_admin/src/app/layout/sidebar/sidebar.component.html:5-6,20-21` — logo genérico "Oreva" + panel de usuario hardcodeado (imagen `assets/images/user.png`, nombre fijo `"Emily Smith"`, cargo desde traducción).
- `panel_admin/src/app/layout/header/header.component.html:60-107,128-156,164-183` — dropdowns de mensajes/notificaciones con datos 100% hardcodeados de ejemplo (nombres ficticios); menú de usuario con saludo fijo `"Hello Sarah.."` (no dinámico) y botón "Logout" funcional (`header.component.ts:166-172`).

**Assets de imagen existentes:**
- `praxsa_manager/product/static/img/praxsa-logo-rmbg.png` y `praxsa-old-logo.png` — logos reales de PRAXSA ya existentes en el backend (contenido visual no confirmado, solo existencia/ubicación).
- `proforma/src/assets/img/praxsa3.jpg` — imagen PRAXSA en `proforma/` (contenido visual no confirmado, no se verificó dónde se referencia en templates).
- `panel_admin/src/assets/images/logo.png` y `panel_admin_doc/src/assets/images/logo.png` — logo genérico "Oreva" de la plantilla comercial, sin relación con PRAXSA.
- **No existe ninguna imagen de automóvil en el repo** (solo assets irrelevantes de plantilla: íconos de tarjetas de crédito, carrusel genérico).

### Hipótesis / supuestos no confirmados
- El formato exacto del JSON de error 400 de `/product/api-token-auth/` para credenciales inválidas se infiere del comportamiento estándar de DRF, no se verificó ejecutando el endpoint contra una base de datos real.
- No se abrió el contenido visual de `praxsa-logo-rmbg.png`, `praxsa-old-logo.png` ni `praxsa3.jpg` — solo se confirmó su existencia por nombre/ubicación de archivo.
- No se confirmó en qué puerto se espera correr `panel_admin/` en desarrollo (Angular CLI por defecto usa 4200, mismo puerto que usa hoy `proforma/`; correr ambos en simultáneo requeriría un puerto distinto, lo cual afecta si hace falta agregar una entrada a `CORS_ORIGIN_WHITELIST`).
- No se confirmó si existe algún usuario administrador real ya creado en la base de datos de desarrollo para probar el login manualmente.

### Módulos y dependencias relacionadas
- Backend: `praxsa_manager/product/custom_views/auth_token.py`, `praxsa_manager/product/urls.py`, `praxsa_manager/praxsa_manager/settings.py` (CORS/CSRF).
- Frontend nuevo: proyecto Angular standalone `panel_admin/` completo — `core/service/auth.service.ts`, `core/interceptor/jwt.interceptor.ts`, `core/interceptor/error.interceptor.ts`, `core/guard/auth.guard.ts`, `core/models/user.ts`, `authentication/signin/*`, `layout/sidebar/*`, `layout/header/*`, `assets/data/routes.json`, `assets/images/*`.
- Frontend existente (solo como referencia de patrón, no se modifica): `proforma/src/app/service/pybackend/authentication/authetication.service.ts`.

### Implementaciones similares existentes
El patrón de integración con `/product/api-token-auth/` ya está resuelto en `proforma/` (`authetication.service.ts`) y debería servir de referencia directa para la nueva integración en `panel_admin/`: mismo endpoint, mismo formato de respuesta, mismo criterio de qué persistir en `localStorage` (decisión ya tomada en `TASK-004`/`ADR-003` de minimizar PII).

### Comportamiento actual
`panel_admin/` es una plantilla comercial recién agregada al repo (`master`, PR #44) que trae un login, dashboard, sidebar y header completamente de demostración, sin ninguna conexión al backend Django ni al negocio de PRAXSA. Nada de lo que pide el usuario existe todavía conectado — es la primera vez que `panel_admin/` se integra con datos/autenticación reales.

### Restricciones
- `docs/CLAUDE.md`: cambios pequeños, un objetivo por cambio; no agregar dependencias sin avisar antes; si algo no se puede verificar, decirlo (aplicado arriba en hipótesis).
- `docs/frontend/panel_admin/reference.md`: `panel_admin/` es Angular 21 standalone, `proforma/` es Angular 16 eager — son apps independientes, no se debe intentar fusionar código Angular entre ambas; la brecha de versiones es una decisión ya señalada como propia de `delivery-architect`.
- El mismo documento de referencia ya advierte: el modelo de auth de `panel_admin/` es un demo (JWT-like, sin roles) y necesita construirse la integración real con Token auth de Django — exactamente lo que pide este task.

### Riesgos identificados
- El interceptor `jwt.interceptor.ts` de `panel_admin/` antepone `Bearer`, incompatible con el header `Authorization: Token {token}` que espera el backend — hay que decidir si se adapta el interceptor existente o se reemplaza.
- `auth_token.py:14` puede producir `HTTP 500` (no un error controlado) si el usuario autenticado no tiene `Client` asociado — relevante para el caso de un usuario admin de Django sin `Client`, que es justamente el tipo de usuario que usaría el panel admin.
- `error.interceptor.ts:23` asume `err.error.message`, pero DRF devuelve `non_field_errors` como array — puede fallar silenciosamente al mapear el mensaje de "credenciales inválidas".
- CORS/CSRF no tienen contemplado explícitamente un origen de desarrollo dedicado a `panel_admin/` si corre en un puerto distinto a los ya whitelisteados.
- Generar logo e imagen de auto son activos gráficos nuevos (no assets ya existentes) — su generación y ubicación final en `panel_admin/src/assets/images/` debe decidirse en diseño.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — el task modifica el mecanismo de autenticación/autorización de una app (login real vs. mock), integra por primera vez `panel_admin/` con el backend Django existente (nueva integración entre dos frontends y un backend, con formatos de token distintos: `Bearer` mock vs. `Token` real de DRF), y toca configuración compartida (CORS/CSRF) que podría afectar a `proforma/`. Son varios de los indicadores explícitos de `NEEDS_ARCHITECTURE` del flujo del equipo.

### Diseño requerido
**SI** — implica adoptar y adaptar pantallas completas de la plantilla `panel_admin/` (login, sidebar, header) reduciendo su menú y reemplazando su branding por el de PRAXSA, además de generar dos activos gráficos nuevos (logo, imagen de auto) a partir de una referencia visual. Es exactamente el tipo de adopción de componentes de plantilla que el flujo marca como Diseño requerido.

## Diseño
[DDR-login-panel-admin-backend-login-branding-menu](../design/DDR-login-panel-admin-backend-login-branding-menu.md) — login restyled sobre el componente `signin` existente (sin pantalla de registro), sidebar reducido vía `assets/data/routes.json`, menú de usuario del header reducido a logo+nombre+logout, y generación de dos assets nuevos (logo PRAXSA, imagen de auto) al no encontrar ningún asset existente que coincida con la referencia visual. Deja una pregunta abierta para el usuario: si el logo nuevo debe reemplazar también los logos usados en el backend/`proforma/` (este DDR asume que no, alcance limitado a `panel_admin/`).

## Arquitectura
[ADR-login-panel-admin-backend-staff-auth-endpoint](../adr/ADR-login-panel-admin-backend-staff-auth-endpoint.md) — no reutilizar `/product/api-token-auth/` (asume `Client`, produce `500` para cualquier usuario sin `Client`, como es el caso típico de un usuario admin de Django). Se crea un endpoint nuevo (`/product/api-panel-admin-token-auth/` o similar) que valida credenciales igual que hoy pero no depende de `Client`, devolviendo `{token, user_id, username, name, lastname}` directamente desde `User`. **Sin verificación de rol/`is_staff`** — decisión explícita del usuario (2026-09-25): por ahora cualquier usuario válido entra al dashboard; la redirección futura de usuarios staff hacia `proforma/` queda fuera de alcance de este task, documentada como pendiente en el ADR. El interceptor de `panel_admin/` se adapta para enviar `Authorization: Token {token}` (no `Bearer`), consistente con `TokenAuthentication` de DRF ya usado por `proforma/`. Cambio aditivo, sin migraciones, sin tocar el endpoint existente.

## Plan
[PLAN-2026-09-25-login-panel-admin-backend](../plans/PLAN-2026-09-25-login-panel-admin-backend.md) (v2 — actualizado tras REV-01 para reflejar los ajustes post-implementación pedidos por el usuario)

## Implementación

Implementado según [PLAN-2026-09-25-login-panel-admin-backend](../plans/PLAN-2026-09-25-login-panel-admin-backend.md) (v1), sin desviaciones de alcance. Detalle completo en `## Changes` del [PR #46](https://github.com/rolion/praxsa-django-panel-admin/pull/46).

**Verificación propia (no es el Quality Gate formal, eso es `delivery-review`):**
- Backend: 85/85 tests pasan (`python manage.py test product`), incluyendo los 4 nuevos de `test_panel_admin_auth.py`.
- Frontend: `ng lint` sin errores. `ng test`: 19 SUCCESS incluyendo los specs nuevos/actualizados (`auth.service.spec.ts`, `signin.component.spec.ts`, `header.component.spec.ts`); 15 FAILED preexistentes en specs de componentes de ejemplo de la plantilla no relacionados a este cambio (ver deuda técnica abajo).
- Smoke test manual end-to-end (backend + frontend reales, navegador): login correcto → dashboard; contraseña incorrecta y usuario inexistente → "Credenciales inválidas"; sidebar solo "Dashboard"; header con logo PRAXSA + nombre real del usuario + Logout. Usuario de prueba eliminado tras la verificación.

**Deuda técnica señalada, no resuelta (fuera de alcance del plan):**
- 15 de los 34 specs de `panel_admin/` ya fallaban antes de este PR por dependencias de test faltantes (`FeatherModule.pick`, `ActivatedRoute`, `ToastConfig` no provistos) en componentes de ejemplo de la plantilla no tocados por este cambio (Footer, Sidebar, Page404/500, AdvanceTable, Blank, Signup, Second1/2, First1/2/3, Third1, Main, Dashboard2). No se corrigieron por no ser parte del objetivo de este task.
- `environment.ts` de producción de `panel_admin/` queda con un `apiUrl` placeholder documentado (`TODO`), no una URL real confirmada.

**Fix incidental aplicado (fuera del plan, pero bloqueante para verificar el propio plan):** `app.component.spec.ts` tenía un error de compilación preexistente que impedía correr `ng test` por completo (no solo ese archivo). Se corrigió lo mínimo indispensable para poder ejecutar y verificar los tests nuevos de este task.

**Ajuste post-implementación (2026-09-25), pedido directo del usuario tras ver el resultado — ver `## Actualización` en el [DDR](../design/DDR-login-panel-admin-backend-login-branding-menu.md):**
- Se reemplazaron los dos SVG generados por los assets reales que compartió el usuario (`praxsa-admin-logo.png`, `praxsa-login-hero.png`).
- Se eliminó el bloque de identidad hardcodeado del propio sidebar ("Emily Smith") — resuelve la pregunta abierta que había quedado pendiente en el DDR y en el plan.
- El nombre del usuario se movió del dropdown derecho del header al nav izquierdo (junto al toggle del sidebar); el dropdown derecho ahora es un ícono genérico con el nombre solo como título y "Logout" como única acción.
- Verificado de nuevo: `ng lint` sin errores, `ng test` 20 SUCCESS (mismos 15 preexistentes sin cambios) y smoke test manual en navegador con el usuario real `oleon`.

## Review

**Veredicto: PASS** (limitación de aislamiento declarada: esta revisión corrió en la misma sesión que `delivery-engineer`; se mitigó reconstruyendo el veredicto solo desde artefactos — TASK, plan, ADR, diff real — y con evidencia ejecutada de forma independiente, incluyendo un worktree temporal en `origin/master` para no asumir las afirmaciones de la etapa anterior).

Verificación funcional/técnica ejecutada de forma independiente:
- Backend: 85/85 tests pasan (`python manage.py test product`).
- Frontend: `ng lint` limpio, `ng build` sin errores, `ng test --code-coverage`: 20 SUCCESS / 15 FAILED. Confirmado contra un worktree temporal en `origin/master` que esos 15 son exactamente el subconjunto preexistente (ahí fallan 17, este PR corrige 2 — `SigninComponent`, `HeaderComponent` — como parte de su propio alcance). Sin regresiones.
- Smoke test manual repetido de forma independiente (localStorage limpio): usuario inexistente → "Credenciales inválidas"; usuario real (`oleon`) → login exitoso, navega a dashboard, nombre visible en el nav izquierdo; responsive mobile oculta la imagen del login; botón `#203b84`.
- `npm audit`: 3 vulnerabilidades preexistentes en dependencias de la plantilla (echarts, lodash-es, xlsx), ninguna introducida por este cambio. Backend: sin `flake8`/`bandit` configurados en el proyecto — verificación no realizada, no se reporta como PASS.

Hallazgos (ninguno bloqueante, sin issues Critical/High):
- [REV-2026-09-25-login-panel-admin-backend-01](../reviews/REV-2026-09-25-login-panel-admin-backend-01.md) (PLAN, Low) — **Resolved**: plan actualizado a v2 a pedido del usuario, ver `## Plan` arriba.
- [REV-2026-09-25-login-panel-admin-backend-02](../reviews/REV-2026-09-25-login-panel-admin-backend-02.md) (IMPLEMENTATION, Low): fix de `app.component.spec.ts` fuera del alcance declarado en el plan — verificado como necesario, informativo.

## Publicación

**Estado: Listo para aprobación humana** (no mergeado).

PR único del task: https://github.com/rolion/praxsa-django-panel-admin/pull/46, con descripción completa (Summary, Changes, Testing, Architecture decisions, Related plan/ADRs, Review, Known limitations) y trazabilidad íntegra a TASK → DDR → ADR → PLAN (v2) → REV-01/REV-02.

**Cambio sensible — requiere aprobación humana explícita antes de mergear:** este task introduce un endpoint nuevo de autenticación (`PanelAdminAuthToken`, ver `docs/adr/ADR-login-panel-admin-backend-staff-auth-endpoint.md`) sin verificación de rol/`is_staff` — cualquier usuario válido de Django puede autenticarse en `panel_admin/`. Es una decisión de negocio explícita del usuario, ya verificada y con Quality Gate en `PASS`, pero por tratarse de autenticación no se marca como mergeable sin que un humano lo confirme.
