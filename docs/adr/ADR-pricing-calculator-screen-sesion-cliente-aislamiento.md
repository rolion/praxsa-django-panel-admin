# ADR-pricing-calculator-screen-sesion-cliente-aislamiento: Sesión de cliente en `panel_admin/` con separación staff/cliente por guards de ruta, barrera de servidor existente y manejo de sesión vencida sin recarga

**Estado:** Propuesto
**Task relacionado:** TASK-pricing-calculator-screen
**Fecha:** 2026-09-30

## Contexto

El DDR `DDR-pricing-calculator-screen-flujo-cliente` hace que el actor sea un **cliente final** con cuenta propia dentro de `panel_admin/`, que nunca debe ver el sidebar ni acceder a los recursos de administración (TASK, "Cambio de alcance"). Hechos de la investigación que condicionan la decisión:
- El login de `panel_admin/` (`PanelAdminAuthToken`, `custom_views/auth_token.py:32-56`) **no exige `is_staff`** ni `Client`: autentica a cualquier usuario válido y devuelve `is_staff`, `groups` y `permissions`. Lo usa `AuthService.login`.
- El `AuthGuard` solo comprueba que exista token (`core/guard/auth.guard.ts:13-19`) y cuelga de **todas** las rutas de administración (`app.routes.ts:7-67`). Hoy un cliente con token vería esa navegación (el backend respondería 403: `IsStaffUser`, `permissions.py:4-11`, en `ordenes/*`, `vehicles/*`, `almacen/*`, `users/*`).
- Sesión: una sola clave `currentUser` (`core/service/auth.service.ts`, `core/models/user.ts` con `isStaff`) bajo prefijo `light_`/`dark_` (`core/service/storage.service.ts`).
- El `ErrorInterceptor` ante **cualquier** 401 hace `logout()` + `location.reload()` (`core/interceptor/error.interceptor.ts:17-21`).
- El `JwtInterceptor` agrega el token a todas las peticiones (`jwt.interceptor.ts:14-20`).
- `CustomAuthToken` (`api-token-auth/`) exige un `Client` y responde 500 sin él (`auth_token.py:14`); no se usa aquí.

## Decisión

1. **Un solo login y una sola sesión por navegador.** El modal de acceso usa el mismo `POST product/api-panel-admin-token-auth/` y `AuthService.login` ya existentes; no se toca `PanelAdminAuthToken` ni se usa `api-token-auth/`. La sesión discrimina el actor con `isStaff` (ya guardado): iniciar sesión como otro actor reemplaza la sesión anterior. No se guardan datos personales del cliente en `localStorage` (solo los campos actuales del `User`); el perfil se obtiene del servidor (ADR `...-registro-y-api-cliente`) y se mantiene en memoria.
2. **Aislamiento por guards de ruta (UX + navegación), nunca como única barrera:**
   - Nuevo guard de **staff** (`isStaff === true`) en el padre `MainLayoutComponent`, en lugar de `AuthGuard` solo. Sin sesión → `authentication/signin` (como hoy); con sesión de cliente → redirige a `/calculadora`.
   - Rutas de cliente bajo el layout sin sidebar (`MinimalLayoutComponent`, ADR `...-layout-sin-sidebar`): `/calculadora` **sin guard** (pública) y `/mis-proformas` con guard de **sesión** (cualquier sesión válida); sin sesión → `/calculadora` con el modal de acceso abierto; un staff en `/mis-proformas` → `/dashboard/main` (no tiene lista de cliente).
   - La ruta comodín y las rutas de administración siguen igual; un cliente que escribe una URL de administración termina en `/calculadora`.
3. **La barrera real sigue en el servidor y no cambia:** `IsStaffUser` + permisos Django en `ordenes/*`, `vehicles/*`, `almacen/*`, `users/*`, `reportes/*`; los endpoints de cliente (ADR `...-registro-y-api-cliente`) filtran por `request.user`. Un usuario creado por el registro de cliente **nunca** recibe `is_staff`, grupos ni permisos (el serializer de alta no acepta esos campos).
4. **Sesión vencida sin recarga para clientes.** El `ErrorInterceptor` decide según la sesión **antes** de cerrarla: si era de staff, conserva el comportamiento actual (logout + recarga); si era de cliente, hace logout, **no recarga** y publica un evento de "sesión expirada" que la pantalla consume para reabrir el modal de acceso y reintentar el guardado conservando la cotización (DDR). Un 401 sin sesión previa (llamada anónima) no dispara recarga en rutas de cliente.
5. **Staff y calculadora:** no cambia su flujo. Si un staff con permiso abre `/calculadora`, "Crear Proforma" mantiene el camino de la v1 (formulario interno con el borrador en `history.state`, permiso `add_proforma_header`); los clientes usan el guardado directo. No se retira el ítem de menú de staff: es una decisión de negocio pendiente (DDR), no técnica.
6. **Login por correo:** el campo del modal es "Usuario" (con la ayuda "si no cambiaste tu usuario al registrarte, es tu correo"). No se agrega búsqueda por correo al login del panel para no alterar la semántica de un endpoint de autenticación compartido con staff; si negocio lo pide, sería un cambio aparte con su ADR. Esto simplifica el "Usuario o correo" del DDR sin perder nada mientras el username por defecto sea el correo.

## Alternativas consideradas

- **App o build separados para clientes** (subdominio o proyecto Angular aparte): aislamiento total, pero duplica configuración, despliegue y plantilla; el usuario decidió explícitamente seguir en `panel_admin/`. Descartada.
- **Dos claves de sesión** (`staffUser` y `clientUser`) para permitir ambas a la vez: permite mezclas confusas (¿a quién pertenece el token del interceptor?) sin un caso de uso que lo pida. Descartada.
- **Endurecer `PanelAdminAuthToken` para rechazar no-staff** (403): rompería el login de clientes por el mismo endpoint y contradice su docstring ("decisión de negocio explícita"); el aislamiento se logra sin tocarlo. Descartada.
- **Usar `api-token-auth/` para clientes y el del panel para staff**: obliga a elegir endpoint antes de saber quién es la persona y `api-token-auth/` falla para usuarios sin `Client`. Descartada.
- **Permisos por ítem de menú/ruta (`permission`) en vez de un guard de staff**: hoy muchos ítems no declaran permiso (`sidebar.metadata.ts:17-29`); exigirlos a todos es un cambio grande y frágil. Un guard único en el layout de administración cubre todo de una vez.
- **Reload ante 401 también para cliente**: pierde la cotización; contradice el DDR. Descartada.

## Estrategia de rollback / mitigación

Es un cambio de **autorización en el frontend** y aditivo en el resto. Mitigaciones y rollback:
- El guard de staff solo **restringe** a quien ya no debía entrar: si resultara que algún usuario no-staff usa hoy el panel (hipótesis: no puede, porque todos los endpoints de administración exigen `is_staff`), su experiencia cambiaría de "panel roto con 403" a "redirige a la calculadora". Verificar con la lista de usuarios antes de desplegar.
- Rollback inmediato: revertir el guard de staff en `MainLayoutComponent` (vuelve a `AuthGuard`), y retirar las rutas `mis-proformas`/modal; ningún dato ni endpoint de administración cambia. Las sesiones guardadas siguen siendo válidas (mismo formato de `User`).
- Sesiones de staff anteriores sin `isStaff` (campo añadido antes por el login del panel) se tratan como no-staff y deben volver a iniciar sesión — mismo precedente que `hasPermission` (`auth.service.ts`, comentario sobre sesiones antiguas).
- Como el servidor no cambia su barrera, un error en el guard **no** abre acceso a datos: el peor caso es de UX (ver pantallas vacías con 403), no de seguridad.

## Consecuencias

- Más fácil: un único punto de entrada de sesión, sin nuevos endpoints de autenticación; aislamiento verificable con pruebas de rutas y de servidor.
- Más difícil: dos tipos de actor en la misma app exigen disciplina al agregar rutas (toda ruta nueva de administración debe colgar del layout con guard de staff); la separación visual vive en el frontend.
- Deuda aceptada: `PanelAdminAuthToken` sigue autenticando a cualquier usuario válido; se documenta que la barrera es el servidor por endpoint. El login sin búsqueda por correo puede generar soporte si alguien cambia su username.
