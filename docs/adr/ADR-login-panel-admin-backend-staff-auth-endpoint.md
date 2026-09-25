# ADR-login-panel-admin-backend-staff-auth-endpoint: Endpoint de autenticación dedicado para `panel_admin/`, independiente de `Client`

**Estado:** Propuesto
**Task relacionado:** TASK-login-panel-admin-backend
**Fecha:** 2026-09-25

## Contexto

`panel_admin/` es la nueva plantilla Angular para el **panel interno de PRAXSA** (`docs/CLAUDE.md`: "usa el panel de administrador por defecto de Django para la gestión interna" — `panel_admin/` es, a futuro, el reemplazo de eso).

**Decisión de negocio explícita del usuario (2026-09-25):** por ahora **no se distingue por rol** — cualquier usuario válido de Django que se autentique en `panel_admin/` debe llegar al dashboard, sin importar si es staff o no. A futuro, los usuarios de tipo staff deberían ser redirigidos al proyecto `proforma/` en lugar de quedarse en `panel_admin/`, pero esa redirección **queda explícitamente fuera de alcance de este task** — se documenta acá como nota para no perderla, no se implementa.

El único endpoint de login que existe hoy es `praxsa_manager/product/custom_views/auth_token.py:1-29` (`CustomAuthToken`, montado en `praxsa_manager/product/urls.py:19` como `/product/api-token-auth/`), y es el que ya consume `proforma/`. Ese endpoint tiene un problema técnico independiente de cualquier decisión de rol:

- Línea 14: `client = Client.objects.get(user_id=user)` — **sin try/except**. `Client` (`praxsa_manager/product/models.py:89-99`) es un modelo pensado para clientes finales (tiene `phone_number`, `ci_nit`, se crea vía `views.create_client` — el flujo de registro de `proforma/`). Un usuario de Django típico creado desde el admin de Django (el tipo de cuenta con el que se probará/usará `panel_admin/`, sea o no `is_staff`) **no tiene necesariamente un `Client` asociado**, porque nunca pasó por ese flujo de registro de cliente.
- Consecuencia verificada por lectura del código (no hipótesis): si un usuario sin `Client` intenta autenticarse contra este endpoint, `Client.objects.get()` lanza `Client.DoesNotExist` y la vista responde `HTTP 500` en vez de un login exitoso — sin importar si ese usuario es staff o no.

Esto es lo único que este ADR necesita resolver: que el login de `panel_admin/` funcione para cualquier usuario válido de Django, sin depender de que exista un `Client`. No hay verificación de rol/permiso en esta decisión — eso es justamente lo que el usuario pidió dejar fuera por ahora.

## Decisión

**Crear un endpoint de autenticación nuevo y separado para `panel_admin/`, en vez de reutilizar `/product/api-token-auth/`, sin verificación de rol.**

- Nueva vista (p. ej. `PanelAdminAuthToken`) en `praxsa_manager/product/custom_views/`, montada en una ruta nueva, p. ej. `praxsa_manager/product/urls.py` → `path('api-panel-admin-token-auth/', PanelAdminAuthToken.as_view())`.
- Reutiliza el mismo mecanismo de validación de credenciales que ya usa `CustomAuthToken` (`AuthTokenSerializer` estándar de DRF vía `ObtainAuthToken` — usuario/contraseña, `Token.objects.get_or_create`), para mantener consistencia con el patrón ya probado en `proforma/` y no introducir JWT ni un mecanismo de auth nuevo (el backend no tiene `djangorestframework-simplejwt` instalado, y agregar una dependencia nueva requiere avisar antes por `docs/CLAUDE.md`).
- **Sin verificación de `is_staff` ni de ningún otro rol** — cualquier usuario de Django con credenciales válidas recibe un token y accede al dashboard. Esto es una decisión de negocio explícita del usuario para esta etapa del proyecto, no un descuido.
- **No depende de `Client`** — la respuesta solo necesita `{token, user_id, username, name (first_name), lastname (last_name)}` desde el propio `User` de Django, sin ningún `Client.objects.get()`. Esto elimina de raíz el riesgo de `500` que tiene hoy `/product/api-token-auth/` para cualquier usuario sin `Client`.
- El endpoint existente `/product/api-token-auth/` **no se toca** — sigue siendo exclusivo de `proforma/`, tal como está hoy.

**Contrato de error para "credenciales inválidas" (usuario no existe o contraseña incorrecta):** `HTTP 400` con el formato que ya produce `AuthTokenSerializer` por defecto (`{"non_field_errors": ["..."]}`) — el mismo patrón que ya usa `proforma/` hoy. El frontend de `panel_admin/` mapea cualquier `400` de este endpoint al mensaje "Credenciales inválidas"; la redacción exacta queda libre para `delivery-plan`/implementación.

**Formato de token en el frontend:** el interceptor de `panel_admin/` (`core/interceptor/jwt.interceptor.ts`) hoy antepone `Authorization: Bearer {token}`. El backend usa `rest_framework.authtoken` (`TokenAuthentication` de DRF), cuyo formato esperado es `Authorization: Token {token}`. **Decisión: adaptar el interceptor existente de `panel_admin/` para enviar `Token` en vez de `Bearer`**, en vez de agregar soporte a `Bearer` en el backend — mantiene un solo esquema de autenticación en todo el backend (ya usado por `InvoiceView` y compatible con `proforma/`), evitando que el backend tenga que aceptar dos formatos de header para el mismo mecanismo.

## Alternativas consideradas

1. **Reutilizar `/product/api-token-auth/` tal cual está, arreglando solo el `Client.DoesNotExist` con un try/except.** Descartada: aunque ahora no hace falta distinguir audiencias por rol, seguiría acoplando el login de `panel_admin/` a un contrato de respuesta pensado para clientes (`phone_number`, `ci_nit` desde `Client`, campos que un usuario admin de Django no tiene). Un endpoint propio con un contrato mínimo (`token`, `user_id`, `username`, `name`, `lastname` desde `User`) es más simple y no necesita ese try/except como parche.
2. **Agregar el manejo de `Client` faltante directamente en `CustomAuthToken`** (un solo endpoint compartido por `proforma/` y `panel_admin/`). Descartada: aunque hoy no hay verificación de rol, seguir compartiendo el mismo endpoint entre el frontend de clientes y el panel interno deja la puerta abierta a acoplar ambos contratos de respuesta a futuro (por ejemplo, cuando se implemente la redirección de staff → `proforma/` mencionada en el contexto). Separar ahora es más barato que separar después de que ambos frontends ya dependan del mismo shape de respuesta.
3. **JWT real (`djangorestframework-simplejwt`) para `panel_admin/`, ya que su interceptor se llama "jwt".** Descartada: es una dependencia nueva no instalada hoy (`docs/CLAUDE.md` exige avisar antes de agregar dependencias), y el backend ya tiene un mecanismo de token funcionando (`rest_framework.authtoken`) consistente con `proforma/`. El nombre del interceptor (`jwt.interceptor.ts`) es un artefacto de la plantilla comercial, no una restricción real — se puede adaptar sin renombrarlo si el naming se decide dejar para no tocar más archivos de los necesarios.

## Estrategia de rollback / mitigación

Cambio aditivo y de bajo riesgo:
- El endpoint nuevo (`/product/api-panel-admin-token-auth/`) no modifica ni reemplaza el existente (`/product/api-token-auth/`); `proforma/` sigue funcionando exactamente igual sin cambios.
- No requiere migración de base de datos.
- Si algo falla en producción, revertir es eliminar la ruta nueva y la vista nueva — no hay datos que limpiar ni estado que revertir, porque no se persiste nada nuevo (solo `Token.objects.get_or_create`, igual que el endpoint existente, que ya es el comportamiento actual y probado).
- El cambio de `Bearer` → `Token` en el interceptor de `panel_admin/` es local a esa app Angular (proyecto standalone, no comparte build con `proforma/`); revertirlo es un cambio de una línea sin efecto en producción hasta que `panel_admin/` mismo se despliegue.
- **CORS/CSRF:** si `panel_admin/` corre en desarrollo en un puerto no incluido hoy en `CORS_ORIGIN_WHITELIST` (`praxsa_manager/praxsa_manager/settings.py:94-110`), habrá que agregarlo. Es una decisión de bajo riesgo (solo development) — `delivery-plan` debe fijar el puerto real y quién lo agrega. En producción, si `panel_admin/` se despliega bajo un dominio propio, ese dominio deberá sumarse a `CORS_ORIGIN_WHITELIST`/`CSRF_TRUSTED_ORIGINS` en el mismo cambio de infraestructura — no se decide el dominio final en este ADR por ser información de despliegue no confirmada en la investigación.

## Consecuencias

- **Más fácil:** el login de `panel_admin/` no depende de datos de cliente que nunca va a tener; cualquier usuario válido de Django entra sin fricción, que es exactamente lo que pidió el usuario para esta etapa.
- **Más difícil / deuda aceptada conscientemente:** ahora hay dos endpoints de "obtener token" con lógica parecida (`CustomAuthToken` para `proforma/`, el nuevo para `panel_admin/`) — cierta duplicación de la parte de validación de credenciales. Se acepta porque son contratos de respuesta genuinamente distintos (uno depende de `Client`, el otro no), y extraer una función compartida solo para el `AuthTokenSerializer.is_valid()` es una micro-optimización que puede hacerse después si se vuelve a tocar este código, no algo que bloquee esta decisión.
- **Sin control de acceso por rol, a propósito:** cualquier usuario de Django (staff o no) que hoy tenga credenciales válidas puede entrar a `panel_admin/`. Es una decisión de negocio explícita del usuario para esta etapa, no un descuido de seguridad — pero queda registrado acá para que no se pierda de vista.
- **Pendiente para `delivery-plan`:** decidir el nombre final del archivo/vista, el puerto de desarrollo de `panel_admin/` y si hace falta agregarlo a `CORS_ORIGIN_WHITELIST`, y el texto exacto de "Credenciales inválidas" en el frontend.
- **No resuelto por este ADR (fuera de alcance, explícitamente pospuesto por el usuario):** la redirección de usuarios `is_staff` hacia `proforma/` en lugar de `panel_admin/`. Cuando se decida implementarla, es una decisión arquitectónica nueva (define dónde se verifica el rol y cómo se redirige) que además debería revisar si sigue teniendo sentido no tener ninguna verificación de rol en el endpoint de `panel_admin/` en ese momento.
