# DDR-login-panel-admin-backend-login-branding-menu: Login, branding PRAXSA y menú mínimo en `panel_admin/`

**Estado:** Propuesto
**Task relacionado:** TASK-login-panel-admin-backend
**Fecha:** 2026-09-25

## Contexto

`panel_admin/` es la plantilla comercial "Oreva" recién agregada a `master` (ver `docs/frontend/panel_admin/reference.md`). Su login, sidebar y header vienen 100% de demostración: credenciales hardcodeadas, branding "Oreva", datos de usuario ficticios ("Sarah Smith", "Emily Smith") y un menú con secciones de ejemplo (Advance Table, Authentication, Extra Pages, Multi-level Menu) que no aplican al panel de PRAXSA.

El usuario pidió, además de la conexión real al backend (fuera del alcance de este DDR, ver `delivery-architect`):
1. Adoptar el login de la plantilla con el branding real de PRAXSA.
2. Generar un logo de la empresa y una imagen de automóvil, en base a una referencia visual que compartió (panel dividido: imagen a la izquierda con overlay oscuro sobre foto de auto + texto de marca, formulario a la derecha con look claro).
3. Reducir el menú lateral a solo "Dashboard".
4. Reducir el menú de usuario (header, superior derecho) a solo el nombre del usuario autenticado, con el logo de la empresa encima.

**Verificación de assets existentes (hecho, no hipótesis — se abrieron los tres archivos):**
- `praxsa_manager/product/static/img/praxsa-logo-rmbg.png` y `praxsa-old-logo.png` — ambos son la misma marca "Px" en un solo color (azul sólido, sin degradado, sin wordmark "PRAXSA" separado). No coinciden visualmente con la referencia del usuario (ícono "P" en degradado azul + wordmark "PRAXSA" en mayúsculas espaciadas + subtítulo).
- `proforma/src/assets/img/praxsa3.jpg` — wordmark plano "PRAXSA" + banner de partner "3M Automotive Window Films". Tampoco coincide con la referencia, y trae branding de un tercero (3M) que no corresponde reutilizar en el ícono del panel admin.
- **No existe ninguna fotografía de automóvil en el repo** (se buscó en las tres apps; lo único "car-like" son íconos de tarjetas de crédito y un carrusel genérico de la plantilla, sin relación).

**Conclusión de la verificación:** ningún asset existente sirve como reemplazo directo — se justifica generar dos activos gráficos nuevos en vez de reutilizar algo ya presente en el repo.

## Pantallas/flujos afectados

1. **Login** (`/authentication/signin`) — la persona ingresa usuario/contraseña y entra al panel. Sin cambios de flujo (sigue siendo solo login), solo de contenido visual y de campos.
2. **Sidebar** (visible en todo el layout autenticado) — la persona ve y navega el menú lateral izquierdo.
3. **Header, menú de usuario** (visible en todo el layout autenticado) — la persona ve quién tiene la sesión iniciada y cierra sesión.

No se tocan: dashboard (`/dashboard/main`, contenido intacto por pedido explícito del usuario), ni las demás rutas de ejemplo (`advance-table`, `extra-pages`, `multilevel`, `dashboard2`) — se dejan de listar en el menú pero sus componentes/rutas no se eliminan (ver "Consecuencias").

## Componentes/patrones elegidos

### 1. Login — reutilizar `panel_admin/src/app/authentication/signin/*` tal cual, no crear una pantalla nueva

`docs/frontend/panel_admin/reference.md` (sección "Estructura real de `panel_admin/src/app/`") confirma que `authentication/` ya trae `signin` como página resuelta por la plantilla, con exactamente el layout de panel dividido (imagen izquierda + formulario derecha) que pide la referencia del usuario — `signin.component.html:1-9` ya usa `col-md-5` para la imagen y `col-md-7` para el formulario. No hace falta un componente nuevo, solo restylear el existente:
- Reemplazar `assets/images/login.jpg` (línea 6) por la imagen de auto generada.
- Reemplazar `assets/images/logo.png` + texto "Oreva" (línea 12) por el logo generado + wordmark "PRAXSA".
- El campo de usuario ya se llama `formControlName="username"` (línea 21) — coincide con el campo `username` que espera `AuthTokenSerializer` de DRF (confirmado en la investigación del task) y con el mismo nombre de campo que ya usa `proforma/` (`login.component.ts:37`, `Credentials(username, password)`). No hace falta renombrar el control.
- El bloque de error ya existe: `@if (error) { <div class="alert alert-danger ...">{{error}}</div> }` (línea 46-48) — es el punto donde se muestra "Credenciales inválidas" (la lógica de qué texto poner y cuándo activarlo es de `delivery-architect`/implementación, no de este DDR).

**Recorte de contenido no solicitado:** el login actual de la plantilla incluye "Remember me", "Forgot password?", "Or Login With" (redes sociales inertes) y "Don't have an account? Sign Up" (líneas 32-72). Nada de esto fue pedido, ninguno tiene backend real detrás (los botones sociales son `href="javascript:void(0)"`, y no hay endpoint de registro ni de recuperación de contraseña mencionado en la investigación), y el TASK dice explícitamente que por ahora la única página es el dashboard. **Decisión: quitar estos cuatro elementos del login**, dejando solo: logo + wordmark, campo usuario, campo contraseña, mensaje de error, botón "Ingresar". Si en el futuro se necesita registro/recuperación, es un task aparte con su propio backend.

**Nota sobre la referencia visual del usuario:** la captura que compartió el usuario es en realidad la pantalla de **registro** ("Bienvenido a... Regístrate", campos Nombre/Apellido/Correo/Contraseña, checkbox de Términos y Condiciones, botones sociales, enlace "¿Ya tienes una cuenta? Inicia sesión"), no la de login. El usuario fue explícito en que esto es "diseño inicial de cómo se vería el login" y que el alcance de este task es solo login (sin registro). **Decisión: tomar de la referencia únicamente el lenguaje visual (panel dividido, paleta azul/blanco, logo + wordmark, foto de auto con overlay oscuro a la izquierda) y aplicarlo al login real de dos campos que ya existe en la plantilla — no construir la pantalla de registro que aparece literalmente en la captura**, porque el requerimiento del usuario no la pidió y no hay backend de registro investigado. Si el usuario en realidad quería también una pantalla de registro, es una ambigüedad a confirmar antes de `delivery-plan`.

### 2. Sidebar — editar el archivo de datos `assets/data/routes.json`, no el componente

`docs/frontend/panel_admin/reference.md` confirma que el sidebar es data-driven: `SidebarService.getRouteInfo()` (`sidebar.service.ts:17-22`) carga `panel_admin/src/assets/data/routes.json` vía `HttpClient`. **Decisión: reemplazar el contenido de ese JSON por una sola entrada** apuntando a `/dashboard/main`, sin submenú (el mismo patrón que ya usa la entrada `"advance-table"` del archivo actual, que es un item simple sin `submenu`). Esto evita tocar `sidebar.component.ts`/`.html` (que solo iteran lo que reciben) y no requiere borrar las rutas de ejemplo (`advance-table.routes.ts`, `extra-pages.routes.ts`, `multilevel.routes.ts`, `dashboard.routes.ts` → `dashboard2`) — simplemente dejan de estar enlazadas desde el menú.

**Alternativa considerada y descartada:** eliminar físicamente los módulos de ejemplo (`advance-table/`, `extra-pages/`, `multilevel/`, `dashboard/dashboard2/`) del código fuente. Se descarta para este task porque el pedido es "el menú izquierdo solo debe tener la página de dashboard" (un requisito de menú visible, no de limpieza de código), y borrar módulos enteros es un cambio más grande y no reversible fácilmente que excede "un objetivo por cambio" (`docs/CLAUDE.md`). Puede proponerse como task de limpieza aparte.

### 3. Header, menú de usuario — editar `header.component.html:164-183` (trigger + dropdown)

Hoy el trigger del dropdown es solo un avatar (`header.component.html:166`), y el panel abierto muestra `"Hello Sarah.."` (línea 169, texto fijo) seguido de enlaces "Profile" (`/extra-pages/profile`, ruta que no existe tras el recorte del sidebar — ya estaba rota antes, no es un problema nuevo), "Email" (`/email/inbox`, tampoco existe), "Settings" (inerte, `href=""`), y "Logout" (funcional, línea 178-181).

**Decisión:** reemplazar el contenido del trigger/panel de identidad por: logo de PRAXSA (pequeño) apilado **encima** del nombre del usuario autenticado (reemplazando el `<img src="assets/images/user.png">` + `"Hello Sarah.."`), y quitar los enlaces "Profile", "Email" y "Settings" (ninguno tiene pantalla real detrás ni fue pedido). Se conserva "Logout" porque es funcionalidad ya operativa y necesaria — "solo mostrar el nombre del usuario" se interpreta como el contenido de identidad mostrado (logo + nombre), no como eliminar la acción de cerrar sesión, que es indispensable para cualquier panel autenticado.

**Fuera de este DDR:** de dónde sale el nombre real del usuario en tiempo de ejecución (`AuthService`/`currentUserValue` vs. otro modelo) es decisión de `delivery-architect`, ya que depende de cómo se resuelva la integración con el token real del backend.

### 4. Assets gráficos nuevos

Se generan dos archivos nuevos (no se reutiliza nada existente, ver verificación arriba):
- **Logo**: ícono "P" en degradado azul + wordmark "PRAXSA" en mayúsculas espaciadas, siguiendo el estilo de la referencia del usuario. Reemplaza `panel_admin/src/assets/images/logo.png` (usado en login, sidebar y ahora también en el header por el punto 3).
- **Imagen de auto**: fotografía/ilustración de un automóvil con vidrios polarizados, en tono oscuro/nocturno con overlay azul, coherente con el rubro de PRAXSA (láminas de control solar). Reemplaza `panel_admin/src/assets/images/login.jpg`.

Ambos se guardan en `panel_admin/src/assets/images/` con nombres descriptivos (p. ej. `praxsa-logo.png`, `praxsa-login-hero.jpg`) en vez de sobrescribir los archivos genéricos de la plantilla, para no perder de vista cuáles son assets propios de PRAXSA vs. remanentes de "Oreva" que puedan seguir usándose en pantallas de ejemplo no tocadas por este task.

## Alternativas consideradas

- **Reutilizar `praxsa-logo-rmbg.png` en vez de generar un logo nuevo**: descartada — no coincide visualmente con la referencia (sin wordmark, sin degradado, marca "Px" en vez de ícono "P" + texto "PRAXSA"), y usar dos logos distintos entre el panel admin y el backend/proforma sería inconsistente. Se deja como pregunta abierta para el usuario (ver "Consecuencias").
- **Construir la pantalla de registro que aparece en la captura de referencia**: descartada por ahora — no fue pedida explícitamente (el usuario la llamó "diseño del login") y no hay backend de registro investigado. Ver nota en sección 1.
- **`ngx-datatable` u otros componentes de listado**: no aplica a este task, no hay tablas involucradas.

## Comportamiento por privilegio/estado

No aplica — el login y el menú reducido no varían según rol/privilegio (la plantilla no tiene modelo de roles, confirmado en la investigación del task). El único estado relevante es autenticado/no autenticado, ya resuelto por `AuthGuard` (`core/guard/auth.guard.ts`) y las rutas (`app.routes.ts`). **Nota para arquitectura:** cualquier necesidad futura de roles/privilegios en el panel requiere que `delivery-architect` defina el modelo — no existe hoy ni en el backend consultado por este DDR ni en la plantilla.

## Consecuencias

- El login queda más simple (2 campos) que el resto de las páginas de ejemplo de la plantilla (`signup`, `forgot`, `reset` siguen existiendo con su diseño original de "Oreva" sin tocar) — quedan visualmente inconsistentes entre sí hasta que un task futuro decida si se actualizan, se ocultan o se eliminan.
- `dashboard2` y las rutas de ejemplo (`advance-table`, `extra-pages`, `multilevel`) siguen siendo accesibles por URL directa aunque no aparezcan en el menú — no es un problema de seguridad (no exponen datos reales), pero es deuda visual/de alcance a decidir en otro momento.
- Los enlaces rotos "Profile" (`/extra-pages/profile`) y "Email" (`/email/inbox`) que ya existían en el header quedan resueltos por este cambio (se eliminan), no se dejan como deuda.
- **Pregunta abierta — resuelta:** el usuario confirmó (2026-09-25) que el alcance del logo nuevo es únicamente `panel_admin/`; no reemplaza `praxsa-logo-rmbg.png`/`praxsa-old-logo.png` en el backend Django ni ningún asset de `proforma/`.

## Actualización (2026-09-25, post-implementación)

Tras ver la implementación con los SVG generados, el usuario compartió los assets reales (fotografía del auto con el logo "PRAXSA WINDOW FILM" ya integrado, y el lockup horizontal "PRAXSA ADMIN") y pidió tres ajustes, todos aplicados directamente sobre la implementación (no ameritan un nuevo ciclo de diseño por ser reemplazos de asset/reubicación de elementos ya decididos, no nuevas decisiones de UX):

1. **Assets reales en vez de SVG generados**: se reemplazan `praxsa-logo.svg`/`praxsa-login-hero.svg` por `praxsa-admin-logo.png` (lockup completo, ya incluye el wordmark) y `praxsa-login-hero.png` (foto real, el logo "PRAXSA WINDOW FILM" ya viene integrado en la imagen). Como el wordmark ya está en la imagen, se quita el `<span class="logo-name">` duplicado del login.
2. **Sidebar**: se elimina por completo el bloque `.sidebar-user-panel` (imagen + "Emily Smith" + cargo) — el usuario pidió explícitamente sacarlo, resolviendo la ambigüedad que este DDR había dejado abierta sobre si tocarlo o no. El logo (`praxsa-admin-logo.png`) queda arriba del sidebar, reemplazando el logo+texto "PRAXSA" que tenía antes.
3. **Header**: el nombre del usuario se muestra en el nav izquierdo (junto al toggle del sidebar), no en el dropdown de la derecha. El trigger del dropdown derecho pasa a ser un ícono genérico (feather `user`), con el nombre solo como título del dropdown al abrirlo (evita duplicarlo) y "Logout" como única acción — mismo criterio ya decidido de "el frontend no necesita mostrar el nombre dos veces", ahora aplicado a dónde va cada aparición.
