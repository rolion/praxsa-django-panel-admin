# Centralizar el chequeo de sesión en un AuthGuard

## Objetivo
Eliminar la duplicación del chequeo manual de sesión (`if (!this.currentUser) { router.navigateByUrl('/login') }`) que hoy repiten `lista.component.ts` y `proforma.component.ts` en su `ngOnInit`, centralizándolo en un `AuthGuard` (`CanActivate`) aplicado en el routing, en línea con lo que ya usa el `AuthInterceptor` para sesión inválida (BIZ-02 en `docs/frontend-audit.md`).

## Alcance
Solo frontend (`proforma/src/app`):
- `guards/auth.guard.ts` (nuevo) + `guards/auth.guard.spec.ts` (nuevo).
- `app-routing.module.ts` (agregar `canActivate` a dos rutas).
- `pages/lista/lista.component.ts` (quitar chequeo manual).
- `pages/proforma/proforma.component.ts` (quitar chequeo manual).

**`create-user.component.ts` queda fuera de este cambio** (ver "Fuera de alcance" — decisión ya confirmada con el usuario).

## Contexto relevante encontrado

- **Fuente de verdad de sesión**: `AutheticationService.getUser()` ([authetication.service.ts:69-81](../../proforma/src/app/service/pybackend/authentication/authetication.service.ts#L69-L81)) devuelve `User | null` leyendo el token desde `LocalStorageService`. Es el mismo método que ya usan `lista.component.ts:16` y `proforma.component.ts:39` para poblar `currentUser`. El guard debe reusar este método, no reimplementar la verificación.
- **Qué hace el interceptor**: `AuthInterceptor` ([app-http-interceptor.ts:26-34](../../proforma/src/app/app-http-interceptor.ts#L26-L34)) no decide "limpiar sesión" a partir de un método de `AutheticationService` — reacciona a un `401` de la API llamando `AutheticationService.logout()` y redirigiendo a `/login`. Es un mecanismo reactivo (después de una petición fallida), complementario al guard, que es preventivo (antes de entrar a la ruta). No hay solapamiento de lógica entre ambos: uno reacciona a error de API, el otro chequea estado local antes de navegar.
- **Chequeos duplicados encontrados** (patrón idéntico, "si no hay sesión, ir a /login"):
  - `lista.component.ts:19-23` — ruta `my-invoice` ([app-routing.module.ts:23](../../proforma/src/app/app-routing.module.ts#L23)).
  - `proforma.component.ts:38-42` — ruta `proforma/:id` ([app-routing.module.ts:18](../../proforma/src/app/app-routing.module.ts#L18)).
- **`create-user.component.ts` NO tiene el mismo patrón**: su `ngOnInit` ([create-user.component.ts:41-45](../../proforma/src/app/components/create-user/create-user.component.ts#L41-L45)) hace lo inverso — si **ya** hay `currentUser`, redirige a `/` (evita que un usuario logueado vuelva a pasar por el registro). Además, este componente no está directamente ruteado: la ruta `create-user` apunta a `NewUserComponent` ([app-routing.module.ts:21](../../proforma/src/app/app-routing.module.ts#L21)), que embebe `<app-create-user>` en su template ([new-user.component.html:13](../../proforma/src/app/pages/new-user/new-user.component.html#L13)). Aplicarle un `AuthGuard` que exige sesión a esa ruta bloquearía el registro de usuarios nuevos (nunca tienen sesión al llegar ahí). `docs/frontend-audit.md` (BIZ-02, línea 164) sugiere incluir `create-user` entre las rutas a proteger con el guard, pero esa sugerencia no coincide con el comportamiento real del componente — se documenta como discrepancia, no se sigue.

## Pasos de implementación

1. Crear `proforma/src/app/guards/auth.guard.spec.ts` primero, con dos casos (ver sección de pruebas).
2. Crear `proforma/src/app/guards/auth.guard.ts`: `AuthGuard implements CanActivate`, inyecta `AutheticationService` y `Router`. `canActivate()` llama `this.auth.getUser()`; si hay usuario devuelve `true`; si no, llama `this.router.navigate(['/login'])` (o `navigateByUrl`, a definir por consistencia con el resto del código) y devuelve `false`.
3. En `app-routing.module.ts`, importar `AuthGuard` y agregar `canActivate: [AuthGuard]` a las rutas `my-invoice` (línea 23) y `proforma/:id` (línea 18). No tocar la ruta `create-user`.
4. En `lista.component.ts`, quitar el `if(!this.currentUser){ this.router.navigateByUrl('/login') }` de `ngOnInit` (líneas 20-22). Evaluar si `Router` sigue siendo necesario como dependencia del componente; si ya no se usa en ningún otro lado, quitarlo del constructor.
5. En `proforma.component.ts`, quitar el `if(!this.currentUser){ this.navigate.navigateByUrl('/login') }` de `ngOnInit` (líneas 40-42), dejando la asignación de `this.currentUser = this.auth.getUser()` y la lógica de `getProforma(id)` que depende de `currentUser`.
6. Correr `ng test` (suite completa) y confirmar que no queda ningún otro chequeo de sesión duplicado fuera del guard y del interceptor (grep de `navigateByUrl('/login')` y `currentUser` en `pages/` y `components/`).

## Pruebas para validar la solución

En `proforma/src/app/guards/auth.guard.spec.ts` (siguiendo el patrón de spies ya usado en `app-http-interceptor.spec.ts`):

1. **Usuario autenticado** — dado `AutheticationService.getUser()` devuelve un `User` no nulo, cuando se llama `guard.canActivate(...)`, entonces el resultado es `true` y `router.navigate`/`navigateByUrl` **no** fue llamado (spy).
2. **Usuario no autenticado** — dado `AutheticationService.getUser()` devuelve `null`, cuando se llama `guard.canActivate(...)`, entonces el resultado es `false` y `router.navigate`/`navigateByUrl` fue llamado con `/login` (verificado con `spyOn(router, ...)`, no solo el valor de retorno).

No se modifica lógica de negocio en `lista.component.ts` ni `proforma.component.ts` más allá de quitar el chequeo (que pasa a cubrir el guard), así que no se agregan casos nuevos en sus specs; sí revisar que `lista.component.spec.ts` y `proforma.component.spec.ts` (hoy solo `'should create'`) sigan pasando sin la dependencia de `Router` en el flujo de `ngOnInit`.

## Riesgos y complicaciones de arquitectura

- **Contrato/comportamiento**: ninguno de los dos lados expone un endpoint nuevo; es un cambio puramente de frontend, sin impacto en el backend.
- **`RouterModule` en specs existentes**: `lista.component.spec.ts` y `proforma.component.spec.ts` no importan `RouterTestingModule` hoy. Si el guard o el componente siguen necesitando `Router` inyectado, `TestBed` debe seguir resolviéndolo (Angular lo resuelve automáticamente solo si algo lo provee); si esos specs empiezan a fallar por esto, es una señal de que ya estaban frágiles y hay que agregar `RouterTestingModule` ahí — se validará al correr la suite completa (paso 6).
- **`create-user` queda sin guard central**: es una decisión consciente confirmada con el usuario, no un olvido. Si en el futuro se quiere migrar también ese chequeo "inverso" a un guard, sería un `GuestGuard` separado (lógica opuesta a `AuthGuard`), fuera de este PR.
- **Discrepancia en `docs/frontend-audit.md`**: BIZ-02 lista `create-user` como ruta a proteger con el guard; este plan documenta por qué no se sigue esa sugerencia literalmente. Vale la pena corregir esa línea de la auditoría en un cambio aparte (fuera de alcance aquí, ya que tocar `docs/frontend-audit.md` no es parte de esta tarea).

## Dependencias nuevas
Ninguna — `CanActivate` es parte de `@angular/router`, ya presente en el proyecto.

## Fuera de alcance / preguntas abiertas
- `create-user.component.ts` no se toca: se confirmó con el usuario dejarlo fuera del `AuthGuard` (su chequeo es semánticamente distinto — "guest guard", no "auth guard" — y no está duplicado con el interceptor ni con los otros dos componentes).
- No se corrige la sugerencia de `docs/frontend-audit.md` (BIZ-02) sobre incluir `create-user`; queda señalado como discrepancia para quien quiera actualizar la auditoría en otro cambio.
- Elección entre `router.navigate(['/login'])` y `router.navigateByUrl('/login')` en el guard: ambos están en uso en el código actual (`navigateByUrl` en los tres componentes originales, `navigate` sugerido por la tarea para el guard). Se implementará con `navigate(['/login'])` por ser más idiomático en un `CanActivate`, pero es un detalle menor que no cambia el comportamiento.
