# Auditoría del frontend (`proforma/`)

Auditoría de solo lectura del frontend Angular ubicado en `proforma/`. No se modificó, movió ni borró ningún archivo existente; este documento es el único artefacto generado.

Todas las rutas son relativas a la raíz del repo (`proforma/...`).

---

## PARTE 1 — Arquitectura

### 1. Estructura

- **Angular**: `^16.1.0` (todos los paquetes `@angular/*`), Angular CLI `~16.1.1`. Usa Angular Universal (SSR): `@nguniversal/express-engine` y `@nguniversal/builders ^16.1.0`, con `server.ts` como servidor Express y `main.server.ts` como entrypoint de servidor.
- **TypeScript**: `~5.1.3` (`proforma/package.json`, devDependencies).
- **Sin librería de estado global** (no hay NgRx/Akita/NgXs). El estado se maneja de forma ad hoc con `BehaviorSubject` dentro de servicios (p. ej. `AutheticationService.userLoginSource`) y campos de componente.
- **Dependencias principales**: `@angular/common/http` (HttpClientModule) para HTTP; `@ng-bootstrap/ng-bootstrap` + `bootstrap` para UI; `@fortawesome/*` para iconos; `angular-datatables` + `datatables.net*` + `jquery` para tablas (listado de proformas); `jspdf` + `jspdf-autotable` para generación de PDF en cliente.
- **No hay componentes standalone** ni módulos por feature con lazy loading: todo se declara/importa de forma eager en `app.module.ts`.
- **Organización del código** (`proforma/src/app/`):
  - `components/`: componentes reutilizables — `banner/`, `create-user/`, `invoiceTable/` (listado de proformas), `login/`, `ng-modal-content/` (modal de creación de proforma), `notfound/`, `top-menu/`.
  - `pages/`: componentes de ruta — `eliminacion-datos/`, `formulario/` (calculadora, ruta raíz), `lista/`, `login-page/`, `new-user/`, `politica/`, `proforma/` (detalle + descarga PDF), `windows-film/`.
  - `service/`: servicios (ver sección 2).
  - `model/`: clases planas (`credentials`, `item`, `lamina`, `marca`, `modelo`, `person`, `proformaCollection`, `report`, `sucursal`, `user`, `windowsFilm`).
  - `interface/`: `iCalculator`, `iCarPart`, `iInventory`.
- **Nota de higiene de repo**: `proforma/dist/proforma/{browser,server}` (artefactos de build) parecen estar commiteados dentro del repositorio — normalmente estos directorios deberían estar en `.gitignore` (ver hallazgo QUALITY-06).

### 2. Consumo de la API

Cada servicio que llama al backend resuelve la URL base en su constructor según el entorno de ejecución (SSR vs. navegador):

```ts
this.API_URL = isPlatformBrowser(this.platformId)
  ? environment.BROWSER_APP_BASE_REF
  : environment.SERVER_APP_BASE_REF;
```

Esto existe porque, con SSR, el proceso de servidor y el navegador del cliente deben apuntar a hosts distintos (p. ej. hostname interno de Docker `web:5000` en servidor vs. dominio público en el navegador).

| Servicio | Endpoints | Notas de tipado |
|---|---|---|
| `service/data.service.ts` | `GET /product/calculator_info`, `GET /product/get_inventory/{sucursalId}/{laminaId}/{width}`, `GET /product/model_parts/{modelId}` | Respuestas mapeadas con `.pipe(map((res: any) => ...))` — sin interfaces de respuesta tipadas (`data.service.ts:36,49,54,60,73,85`). |
| `service/pybackend/authentication/authetication.service.ts` | `POST /product/api-token-auth/` (login), creación de usuario | Respuesta también tipada como `any` (líneas 39, 46). |
| `service/pybackend/film/windows-film.service.ts` | Detalle de una lámina/film por id | Deja `console.log` en constructor/método (líneas 23-24, 28-29). |
| `service/pybackend/proforma/proforma.service.ts` | `POST` guardar proforma, `GET` proforma por id, `GET /product/invoice/all` (listado paginado server-side vía DataTables) | — |

La URL base por entorno se configura en `proforma/src/environments/`:

| Archivo | `BROWSER_APP_BASE_REF` | `SERVER_APP_BASE_REF` | `production` |
|---|---|---|---|
| `environment.ts` (default) | `http://localhost:8000` | `http://localhost:8000` | `false` |
| `environment.dev.ts` | `http://localhost:8000` | `http://localhost:8000` | `false` |
| `environment.stg.ts` | `https://panel.oscarleon.website` | `http://web:5000` | `false` |
| `environment.prod.ts` | `https://panel.praxsasrl.store` | `http://web:5000` | `true` |

El swap de archivo se hace vía `fileReplacements` en `angular.json` (configuraciones `production`, `development`, `staging`); `defaultConfiguration` es `"production"`, es decir que un `ng build`/`ng serve` sin flags usa el entorno de producción salvo que se pase `--configuration=development`.

También existe `proforma/src/app/proxy.conf.json` (proxy de desarrollo, `/product` → `http://localhost:3000`), pero no se encontró evidencia de que esté conectado al target `serve` en `angular.json` — posible configuración obsoleta o sin usar.

### 3. Sesión

- **Login**: `AutheticationService.login()` (`service/pybackend/authentication/authetication.service.ts:44-58`) hace `POST {base_url}/product/api-token-auth/` (estilo token-auth de Django REST Framework). En caso de éxito guarda en `localStorage` (vía `LocalStorageService`): `token`, `name`, `lastname`, `phone_number`, `email`, `ci_nit`.
- **Almacenamiento del token**: `localStorage`, en texto plano, junto con PII del usuario (nombre, apellido, teléfono, email, CI/NIT). No se usa cookie ni `sessionStorage`, y no hay opción de mantenerlo solo en memoria.
- **Adjunto a peticiones**: `app-http-interceptor.ts` (`AuthInterceptor`) lee el token de `localStorage` y, si existe, clona **toda** petición saliente agregando el header `Authorization: Token {token}`. Se registra globalmente en `app.module.ts` vía `HTTP_INTERCEPTORS`, sin exclusión por endpoint (incluye llamadas públicas como la info de la calculadora).
- **Expiración / 401 / 403**: no se encontró ningún manejo. El interceptor no implementa `catchError` ni lógica de error; no hay referencias a `401`, `403`, `HttpErrorResponse` o `catchError` en todo `src/`. Los componentes manejan errores HTTP puntualmente y solo para UX (p. ej. `login.component.ts` revisa `error.status == 0` para mostrar un mensaje genérico), pero ningún lugar detecta un token expirado/inválido para forzar logout o redirigir a `/login`.
- **Logout**: `AutheticationService.logout()` limpia las mismas claves de `localStorage` y emite `null` en el `BehaviorSubject` de estado de sesión.
- No hay refresh token ni verificación de expiración en el cliente.

### 4. Calculadora de precios

Componente principal: `pages/formulario/formulario.component.ts` (ruta raíz `''`), apoyado en `pages/formulario/data.ts` (clase `iDB`, instanciada directamente con `new iDB()` — no es un servicio inyectable) y en `service/data.service.ts`.

Flujo de selección y origen de los datos:

1. **Carga inicial** (`ngOnInit` → `getCalculatorInfo()`): `DataService.getCalculatorInfo()` llama `GET /product/calculator_info`, que trae marcas, modelos, sucursales y partes de modelo en una sola respuesta. Se usa `TransferState` de Angular Universal para no duplicar el fetch entre SSR y navegador.
2. **Marca → Modelo**: filtrado 100% client-side sobre la lista ya cargada (`iDB.getModelByMarca`), sin llamada a API adicional.
3. **Selección de sucursal → inventario**: al fijar `selectedSucursalId`, se llama `DataService.getInventario(sucursalId, 0, 0)` → `GET /product/get_inventory/{sucursalId}/{laminaId}/{width}`; el resultado se deduplica en un `Film[]` en el cliente.
4. **Modelo → partes del auto**: `DataService.getModelParts(modelId)` → `GET /product/model_parts/{modelId}`; luego `iDB.getModelParts` filtra client-side por `model_id` y precarga ancho/largo/cantidad/precio de instalación por parte desde el payload de la API.
5. **Selección de lámina por parte → precio**: `getLaminaItemPrice()` hace una **segunda** llamada más específica, `DataService.getInventario(selectedSucursalId, lamina.id, carPartWidth)`, para obtener el precio de esa lámina/ancho puntual.
6. **Cálculo del precio — se hace en el cliente**: la fórmula vive en `formulario.component.ts:238`:
   ```ts
   let totalPrice = (carPartLength * itemQuantity * filmPrice.bobina_price) + (carPartInstallationPrice * itemQuantity);
   ```
   El precio unitario (`bobina_price`) y el precio de instalación (`installation_price`) vienen del backend, pero la multiplicación, redondeo (`.toFixed(2)`) y suma total (`calculateTotal()`, líneas 248-251) ocurren enteramente en el navegador. El objeto `Invoice` resultante se envía tal cual a `ProformaService.saveProforma()`, sin evidencia (desde el frontend) de que el backend recalcule o valide ese total antes de persistirlo.
7. Existe un método muerto, `iDB.getLamninaPriceByWidth()` (`pages/formulario/data.ts:30-55`, nótese el typo "Lamnina"), que ya no se usa (fue reemplazado por el flujo de `getLaminaItemPrice` basado en API) — ver hallazgo QUALITY-05.

### 5. Generación y listado de proformas

- **Creación**: `components/ng-modal-content/ng-modal-content.component.ts` (`NgModalContentComponent`), abierto como modal desde `FormularioComponent.openModal()`. Implementa una máquina de estados manual (campo `estado` + constantes `STATUS_*`) para: exigir login (si `AutheticationService.getUser()` es `null`) → recolectar datos de la persona (nombre, email, teléfono, CI, placa) → `ProformaService.saveProforma(invoiceClone)` (filtrando filas sin lámina seleccionada) → navegar a `/proforma/{id}`.
- **Detalle + descarga PDF**: `pages/proforma/proforma.component.ts` (`ProformaComponent`, ruta `proforma/:id`). En `ngOnInit` exige login (redirige a `/login` si no hay usuario). `downloadProforma()` arma el PDF usando `PdfBuilderService` (jsPDF + jspdf-autotable) y hace `doc.save('proforma.pdf')` — la generación del PDF es enteramente client-side, no hay generación server-side.
- **Listado**: `components/invoiceTable/list-proforma.component.ts` (`ListProformaComponent`, embebido en `pages/lista/lista.component.ts`, ruta `my-invoice`) usa `angular-datatables` con paginación server-side vía `ProformaService.getUserProforma(dataTablesParameters)` → `GET /product/invoice/all`. Un callback `columnDefs.render` inyecta un `<a href="/#/proforma/${data}">` como string en la celda de DataTables, saltándose la sanitización propia de Angular (ver hallazgo SEC-04).
- `ListaComponent` es el wrapper de página que exige login antes de mostrar el listado.

### 6. Manejo de errores y estados de carga

- No existe un manejo de errores HTTP centralizado (ni interceptor de errores, ni servicio dedicado). Cada componente decide qué hacer con un error de forma ad hoc; el patrón más común es mostrar un mensaje genérico en español cuando `error.status == 0` (p. ej. `login.component.ts`).
- No hay indicadores de "loading" consistentes a nivel de aplicación (spinners globales, interceptor de loading, etc.); no se observó un patrón sistemático de estado de carga fuera de flags puntuales por componente.
- No se encontró manejo específico de errores 401/403 en ningún punto del código (ver sección 3).

---

## PARTE 2 — Hallazgos

Cada hallazgo indica ID, severidad, archivo/línea, evidencia, impacto, solución sugerida y esfuerzo estimado (S = horas, M = 1-3 días, L = más de 3 días / requiere coordinación con backend).

### Seguridad del lado cliente

**SEC-01 — Token de sesión y PII en `localStorage` en texto plano**
- Severidad: **Alta**
- Archivo: `proforma/src/app/service/pybackend/authentication/authetication.service.ts:47-52`
- Evidencia:
  ```ts
  this.local.saveData('token', res.token)
  this.local.saveData('name', res.name)
  this.local.saveData('lastname', res.lastname)
  this.local.saveData('phone_number', res.phone_number)
  this.local.saveData('email', res.email)
  this.local.saveData('ci_nit', res.ci_nit)
  ```
- Impacto: cualquier script inyectado (XSS) puede leer `localStorage` y obtener el token de sesión junto con datos personales (nombre, teléfono, email, CI/NIT), permitiendo suplantación de sesión y fuga de PII sin necesidad de comprometer el backend.
- Solución sugerida: mover el token a una cookie `httpOnly`/`secure` gestionada por el backend, o al menos evitar persistir PII en `localStorage` (mantenerla solo en memoria/estado de la app).
- Esfuerzo: **M** (requiere cambios coordinados con el backend si se migra a cookies).

**SEC-02 — Sin manejo de 401/403 ni expiración de token**
- Severidad: **Alta**
- Archivo: `proforma/src/app/app-http-interceptor.ts` (interceptor completo, sin `catchError`)
- Evidencia: no hay ninguna referencia a `401`, `403`, `HttpErrorResponse` o `catchError` en todo `proforma/src`.
- Impacto: un usuario con token vencido o revocado no es redirigido a `/login`; simplemente ve peticiones fallidas sin explicación, y potencialmente queda en pantallas que asumen sesión válida (p. ej. calculadora, listado).
- Solución sugerida: agregar manejo de errores en el interceptor (o un interceptor adicional) que, ante 401/403, limpie la sesión local y redirija a `/login`.
- Esfuerzo: **S**.

**SEC-03 — Interceptor de auth global sin scoping por endpoint**
- Severidad: **Media**
- Archivo: `proforma/src/app/app-http-interceptor.ts:11-16`, registrado en `proforma/src/app/app.module.ts` (`HTTP_INTERCEPTORS`)
- Evidencia: el interceptor añade `Authorization: Token {token}` a toda petición saliente si hay un token guardado, sin distinguir endpoints públicos (p. ej. `calculator_info`) de privados.
- Impacto: bajo por sí solo, pero acopla toda petición HTTP al estado de sesión y dificulta, por ejemplo, integrar APIs de terceros en el futuro sin filtrar el header manualmente.
- Solución sugerida: filtrar por URL (whitelist/blacklist) qué peticiones reciben el header de autenticación.
- Esfuerzo: **S**.

**SEC-04 — HTML crudo inyectado en celda de DataTables (listado de proformas)**
- Severidad: **Baja**
- Archivo: `proforma/src/app/components/invoiceTable/list-proforma.component.ts` (callback `columnDefs.render`, ~línea 72)
- Evidencia: `render` arma un string `<a href="/#/proforma/${data}">...</a>` que DataTables inserta como `innerHTML`, evitando la sanitización de Angular.
- Impacto: bajo en la práctica porque `data` actualmente es el id numérico de la proforma devuelto por la propia API, pero es un patrón riesgoso si en el futuro ese campo incorpora datos menos controlados.
- Solución sugerida: sanitizar/validar el valor (forzar a número) antes de interpolarlo, o mover el renderizado a un componente Angular en vez de HTML crudo de DataTables.
- Esfuerzo: **S**.

### Lógica de negocio en el cliente

**BIZ-01 — Cálculo de precio y total realizado enteramente en el cliente**
- Severidad: **Alta**
- Archivo: `proforma/src/app/pages/formulario/formulario.component.ts:231-246` (`getLaminaItemPrice`), `:248-251` (`calculateTotal`)
- Evidencia:
  ```ts
  let totalPrice = (carPartLength * itemQuantity * filmPrice.bobina_price) + (carPartInstallationPrice * itemQuantity);
  ```
- Impacto: el precio unitario viene del backend, pero la multiplicación/suma final se hace en el navegador y se envía tal cual en `saveProforma()`. Un usuario con acceso a devtools podría alterar el estado del componente (o interceptar/editar el payload) antes de guardar la proforma, si el backend no recalcula el total de forma independiente. **No se pudo verificar desde el frontend si el backend Django revalida este monto** — requiere revisar el backend, fuera del alcance de esta auditoría.
- Solución sugerida: que el backend recalcule y valide el precio/total a partir de los ids de sucursal/lámina/parte recibidos, ignorando (o solo usando como referencia) el total enviado por el cliente.
- Esfuerzo: **L** (cambio de contrato con el backend).

**BIZ-02 — Protección de rutas privadas manual e inconsistente (sin route guards)**
- Severidad: **Media**
- Archivo: `proforma/src/app/app-routing.module.ts` (rutas sin `canActivate`); comprobación manual en `pages/lista/lista.component.ts:20-22`, `pages/proforma/proforma.component.ts:40-41`, `components/create-user/create-user.component.ts:42-44`
- Evidencia: cada componente protegido repite en `ngOnInit` un patrón del tipo "si no hay usuario, `router.navigateByUrl('/login')`", en vez de usar un `CanActivate` guard central.
- Impacto: la ruta y su componente llegan a renderizarse brevemente antes de que se dispare el redirect; además, cualquier ruta nueva que deba protegerse depende de que el desarrollador recuerde replicar el patrón manualmente — fácil de olvidar.
- Solución sugerida: introducir un `AuthGuard` (`CanActivate`) reutilizable y aplicarlo en `app-routing.module.ts` a las rutas privadas (`my-invoice`, `proforma/:id`, `create-user`, etc.).
- Esfuerzo: **S**.

### Calidad

**QUALITY-01 — Uso extendido de `any` pese a `strict: true`**
- Severidad: **Media**
- Archivo: múltiples (≈32 ocurrencias en 13 archivos); ejemplos: `service/data.service.ts:36,49,54,60,73,85`, `service/pybackend/authentication/authetication.service.ts:39,46`, `model/proformaCollection.ts:4` (`items: any[]`), `components/top-menu/top-menu.component.ts:17` (`userSubscription: any`)
- Evidencia: `proforma/tsconfig.json` tiene `"strict": true` y flags adicionales (`noImplicitOverride`, `noImplicitReturns`, etc.), pero el código anota `any` explícitamente en respuestas HTTP y en campos que deberían tipar `Subscription` u otras interfaces concretas.
- Impacto: se pierde la seguridad de tipos justo en los puntos más sensibles (respuestas de API, suscripciones), lo que facilita bugs silenciosos y dificulta refactors.
- Solución sugerida: definir interfaces de respuesta para cada endpoint y tipar explícitamente los campos de suscripción (`Subscription` en vez de `any`).
- Esfuerzo: **M**.

**QUALITY-02 — Suscripciones sin cancelar**
- Severidad: **Media**
- Archivo: `components/create-user/create-user.component.ts:50-61`, `components/ng-modal-content/ng-modal-content.component.ts:125-132`, `pages/windows-film/windows-film.component.ts:35-48` (además este último ni siquiera declara `implements OnInit`); también `pages/proforma/proforma.component.ts:51` (la llamada a `getProforma()` no asigna su suscripción al campo `httpSubscription` ya existente para ese propósito, quedando sin cancelar pese a que el patrón de limpieza sí existe en el componente)
- Evidencia: llamadas `.subscribe(...)` sin `takeUntil`, sin `async` pipe y sin `OnDestroy`/unsubscribe manual.
- Impacto: potenciales fugas de memoria y llamadas/efectos tardíos si el componente se destruye antes de que la petición HTTP resuelva; el caso de `formulario.component.ts` (que sí cancela su suscripción en `ngOnDestroy`) muestra que el patrón correcto es conocido pero no se aplica consistentemente.
- Solución sugerida: adoptar `async` pipe donde sea posible, o un `Subject` `destroy$` + `takeUntil` como patrón estándar en todos los componentes con `.subscribe()`.
- Esfuerzo: **S/M** según cantidad de componentes a tocar.

**QUALITY-03 — Lógica de negocio en componentes en vez de servicios**
- Severidad: **Media**
- Archivo: `pages/formulario/formulario.component.ts:231-251` (cálculo de precio/total); `pages/formulario/data.ts` (clase `iDB`, instanciada con `new iDB()` en `formulario.component.ts`, no inyectable vía DI); `pages/proforma/proforma.component.ts:60-96` (armado de arrays `pdfHead`/`pdfBody`/`pdfFoot` para el PDF); `components/ng-modal-content/ng-modal-content.component.ts:20-30` (máquina de estados `estado`/`STATUS_*` del wizard de creación)
- Evidencia: ver fragmentos citados en la sección 4 y 5 de la Parte 1.
- Impacto: lógica difícil de testear de forma aislada (depende del ciclo de vida y del DOM del componente), y duplicación de responsabilidades entre `data.ts` y `DataService`.
- Solución sugerida: extraer la lógica de precio a un servicio de pricing testeable, convertir `iDB` en un servicio Angular inyectable, y mover el armado de datos del PDF a `PdfBuilderService`.
- Esfuerzo: **M**.

**QUALITY-04 — `console.log` dejado en código de producción**
- Severidad: **Baja**
- Archivo: `service/pybackend/film/windows-film.service.ts:23-24,28-29`
- Impacto: ruido en consola del navegador en producción, posible exposición incidental de datos en logs del cliente.
- Solución sugerida: eliminar los `console.log` o reemplazarlos por un logger condicionado a `environment.production`.
- Esfuerzo: **S**.

**QUALITY-05 — Código muerto**
- Severidad: **Baja**
- Archivo: `pages/formulario/data.ts:30-55` (`getLamninaPriceByWidth`, con typo "Lamnina")
- Impacto: mantenimiento innecesario y confusión (nombre con typo, dos caminos aparentes para lo mismo).
- Solución sugerida: eliminar el método si se confirma que no se usa.
- Esfuerzo: **S**.

**QUALITY-06 — Artefactos de build commiteados en el repo**
- Severidad: **Baja**
- Archivo: `proforma/dist/proforma/{browser,server}`
- Impacto: infla el repositorio y puede generar diffs ruidosos o confusión sobre qué build está "vigente"; no se verificó si esto es intencional (p. ej. para deploy directo desde el repo).
- Solución sugerida: si no es necesario para el proceso de deploy, agregar `dist/` al `.gitignore` y remover del historial reciente.
- Esfuerzo: **S** (pendiente de confirmar con el equipo si el deploy depende de que `dist/` esté versionado).

### Tests y tooling

**TEST-01 — Cobertura de tests real: cero**
- Severidad: **Alta**
- Archivo: los 21 archivos `*.spec.ts` del proyecto (componentes y servicios)
- Evidencia (`service/pybackend/authentication/authetication.service.spec.ts:1-16`):
  ```ts
  describe('AutheticationService', () => {
    let service: AutheticationService;
    beforeEach(() => {
      TestBed.configureTestingModule({});
      service = TestBed.inject(AutheticationService);
    });
    it('should be created', () => {
      expect(service).toBeTruthy();
    });
  });
  ```
- Impacto: `ng test` "pasa" pero no protege contra regresiones en ninguna lógica real, en particular el cálculo de precios (BIZ-01) y el flujo de autenticación, que son las partes más sensibles del sistema.
- Solución sugerida: priorizar tests unitarios para la lógica de precio (`formulario.component.ts` / futuro servicio de pricing) y para `AutheticationService` (login/logout/estado de sesión).
- Esfuerzo: **M/L** según cobertura objetivo.

**TEST-02 — Sin ESLint/TSLint ni script de lint**
- Severidad: **Media**
- Archivo: `proforma/package.json` (bloque `scripts`, sin entrada `lint`); no existe `.eslintrc*` ni `tslint.json` en `proforma/` (fuera de `node_modules`); `@angular-eslint/*` no está en las dependencias.
- Impacto: no hay ningún gate automatizado de estilo/calidad más allá del chequeo de tipos de `tsc`; problemas como los de QUALITY-01/02/04 no son detectados automáticamente en CI ni en pre-commit.
- Solución sugerida: agregar `@angular-eslint` + configuración base, y un script `lint` en `package.json` (idealmente enforced en CI).
- Esfuerzo: **S** (setup inicial) + tiempo variable para resolver findings existentes.

---

## Preguntas de negocio (no deducibles del código)

1. ¿El backend Django recalcula y valida el precio/total de la proforma al recibir `saveProforma()`, o confía en el monto enviado por el cliente? (Determina la severidad real de BIZ-01.)
2. ¿Por qué el token de sesión no tiene expiración/refresh visible desde el cliente? ¿El backend expira tokens del lado servidor de alguna forma que el frontend simplemente no maneja?
3. ¿Es intencional que `proforma/dist/proforma` esté commiteado (p. ej. porque el deploy lo consume directamente desde el repo), o es un descuido?
4. ¿El endpoint `GET /product/calculator_info` está pensado como público (sin autenticación), y si es así, es aceptable que igual reciba el header `Authorization` cuando hay sesión activa?
5. ¿Hay planes de mover parte de la calculadora o el listado de proformas a rutas con lazy loading, o el tamaño actual de la app no lo justifica?
6. ¿Quién es el dueño/responsable de definir qué PII es aceptable persistir en el cliente (nombre, teléfono, email, CI/NIT), dado que hoy se guarda en `localStorage`?
7. ¿El proxy `proforma/src/app/proxy.conf.json` (`/product` → `localhost:3000`) sigue en uso, o es configuración obsoleta de un entorno de desarrollo anterior?
