# Integración backend/frontend y backlog unificado

Este documento sintetiza `docs/backend-audit.md` y `docs/frontend-audit.md`, verifica sus hallazgos críticos/altos contra el código actual (`praxsa_manager/` y `proforma/`) y propone un backlog de trabajo unificado. No se modificó, movió ni borró ningún archivo existente del repositorio; este documento es el único artefacto nuevo.

**Método**: se releyeron ambas auditorías y se verificó cada hallazgo crítico/alto directamente contra el código (archivo:línea exactos), más el contrato real de serializers/vistas/modelos usado por el frontend. Resultado general: **todos los hallazgos crítico/alto de ambas auditorías se confirmaron**, con line numbers casi idénticos a lo documentado. Se detectaron además 2 hallazgos nuevos, visibles solo al cruzar ambos lados (sección 3).

---

## 1. Contrato entre backend y frontend

### 1.1 Endpoints y payloads reales

| Endpoint | Método | Lo que el frontend envía | Lo que el backend realmente acepta/persiste |
|---|---|---|---|
| `/product/invoice` | POST | Objeto `Invoice` completo ([model/proformaCollection.ts](proforma/src/app/model/proformaCollection.ts)): `id, carPartItems[], name, ci_nit, car_plate, sucursal, sucursal_name, sucursal_address, sucursal_phone, car_model_id, car_model_name, car_brand_id, car_brand_name, email, phone_number, ci, placa, total_price, proforma_created_on, status` | `SalesHeaderSerializer.Meta.fields` ([serializer/invoice_serializer.py](praxsa_manager/product/serializer/invoice_serializer.py)) = `name, email, car_plate, car_model_id, total_price, carPartItems, phone_number, ci_nit, sucursal, created_by`. **Todo lo demás se descarta en silencio** — `id`, `sucursal_name`, `sucursal_address`, `sucursal_phone`, `car_model_name`, `car_brand_id`, `car_brand_name`, `ci`, `placa`, `proforma_created_on`, `status` no existen como campos del serializer ni del modelo `Proforma_Header`. Este es el comportamiento estándar de un `ModelSerializer` de DRF: claves no listadas en `Meta.fields` se ignoran, no se rechaza la request. |
| — items de `carPartItems` | (dentro del POST anterior) | `car_part, car_part_name, width, length, sub_total, quantity, window_film, window_film_name, installation_price, window_film_price, window_film_url` | `SaleDetailSerializer.Meta.fields` = `car_part, width, length, quantity, window_film, installation_price, window_film_price, sub_total`. `car_part_name`, `window_film_name`, `window_film_url` se descartan igual que arriba (son solo para mostrar en UI). |
| `/product/invoice/<pk>/` | GET | — | `InvoiceView.get` construye la respuesta **a mano** (no reusa el serializer de escritura): `{id, name, email, ci_nit, sucursal_name, sucursal, sucursal_address, sucursal_phone, car_plate, phone_number, car_model_id, car_model_name, car_brand_name, total_price, proforma_created_on (formateado dd/mm/YYYY), carPartItems: [{car_part_id, car_part_name, width, length, sub_total, quantity, window_film_id, window_film_name}]}`. |
| `/product/invoice/all` | GET | Parámetros de `angular-datatables` (sin `draw`) | `ListUserInvoice.get` responde `{recordsTotal, recordsFiltered, data}`, con filas `{name, email, ci_nit, car_plate, phone_number, car_model_id, car_model_name, total_price, date, id}`. |
| `/product/create_client` | POST | `User`: `email, password, name, lastname, phone_number, ci_nit` | `ClientSerializer` = `email, password, name, lastname, phone_number, ci_nit` — **coincide 1:1**, sin mismatch. |
| `/product/layer/<id>` | GET | — | `get_layer_info` ([views.py:187-193](praxsa_manager/product/views.py)) devuelve `{'layer': {'name', 'content'}}`, anidado bajo la clave `layer` (ver 3.2). |

### 1.2 Asimetría POST vs. GET en `/product/invoice`

Lo que el frontend **envía** al crear (`car_part`, `window_film`, con precios) y lo que **recibe** al leer (`car_part_id`, `window_film_id`, sin `installation_price`/`window_film_price`) tienen shapes distintos para el mismo concepto. Como el frontend tipa estas respuestas como `any` en varios puntos (`data.service.ts`, servicios de `pybackend/`), TypeScript no protege contra este desajuste — si algún componente asumiera el shape del POST al leer una respuesta GET, fallaría en silencio (`undefined`) en vez de dar un error de compilación.

### 1.3 Paginación

No hay un estándar único:
- `/product/invoice/all` usa un formato ad hoc estilo DataTables: `{recordsTotal, recordsFiltered, data}`. Curiosamente, ni el frontend envía ni el backend espera/devuelve el parámetro `draw` que exige el protocolo estándar de DataTables server-side — esto es **consistente entre ambos lados** (no es un bug, aunque se aparta del estándar de la librería).
- El resto de endpoints de catálogo (`calculator_info`, `model_parts/<id>`, etc.) no pagina en absoluto: `REST_FRAMEWORK` en `settings.py:119-125` no define `DEFAULT_PAGINATION_CLASS` ni `PAGE_SIZE`. A medida que crecen marcas/modelos/piezas, esos payloads crecen sin límite (ver backlog #5 relacionado con PERF-02 del backend).

### 1.4 Formato de errores

`InvoiceView.post` sí maneja el caso inválido: `if serializer.is_valid(): ... ; return Response(data=serializer.errors, status=400)` — el frontend lee `error.error` directamente (`login.component.ts`, `create-user.component.ts`), que coincide con el shape de `serializer.errors` (dict de listas de errores por campo, formato estándar de DRF).

Sin embargo, hay un bug de robustez no reportado por ninguna auditoría original: el `except Exception` externo de la misma vista también intenta devolver `serializer.errors` — si la excepción ocurre **antes** de que `serializer` se cree (p. ej. un error al leer `request.data`), esa línea lanzaría `UnboundLocalError`, enmascarando el error real detrás de un 500 distinto y más confuso. Ver hallazgo nuevo en sección 3.2.

### 1.5 El campo `status`: contrato roto en la práctica

El modelo Angular `Invoice` tiene un campo `status`, y lo envía en cada `saveProforma()`. El backend:
- No lo acepta en `SalesHeaderSerializer` (se descarta al crear).
- No lo persiste — `Proforma_Header` no tiene columna `status`.
- No lo devuelve — ni `InvoiceView.get` ni `ListUserInvoice.get` incluyen `status` en su respuesta.
- El "estado" real solo se infiere server-side con una cadena de `hasattr()` sobre relaciones inversas O2O, únicamente en el admin de Django ([admin_config/proforma_admin.py:96-111](praxsa_manager/product/admin_config/proforma_admin.py)), y **nunca se expone por ningún endpoint que el frontend consuma**.

Conclusión: el campo `status` del modelo `Invoice` en Angular es, en la práctica, un campo muerto — se define, se envía, pero nunca se persiste, calcula ni recibe de vuelta. Si algún componente del frontend lo lee esperando un valor útil, siempre estará `undefined`.

---

## 2. Lógica duplicada, sobre todo el cálculo de precio

### 2.1 Dos casos de negocio (`sales_type`), tres implementaciones — y dos de ellas no coinciden para el mismo caso

`Proforma_Header.sales_type` tiene exactamente dos valores posibles ([helper/proforma.py:13-15](praxsa_manager/product/helper/proforma.py)): `venta_instalacion` ("Venta con Instalación") y `venta_metro_lineal` ("Venta Metro Lineal", el cliente compra la lámina sin instalación — el costo de instalación es 0 porque el caso de negocio no la incluye, no porque sea un valor faltante por error). Cada caso tiene su propia fórmula correcta, pero está implementado de forma inconsistente en tres lugares:

| # | Ubicación | Caso | Fórmula |
|---|---|---|---|
| 1 | Frontend Angular — [formulario.component.ts:238](proforma/src/app/pages/formulario/formulario.component.ts) | solo `venta_instalacion` | `totalPrice = (length * quantity * bobina_price) + (installation_price * quantity)` |
| 2a | JS del panel admin, rama `if` — [sales_event.js:272-281](praxsa_manager/product/static/product/sales_event.js) (`calculate_subtotal`) | `venta_instalacion` | `subtotal = (length * quantity * film_price) + (installation_price * quantity)` — igual que (1) |
| 2b | JS del panel admin, rama `else` — [sales_event.js:284-289](praxsa_manager/product/static/product/sales_event.js) | `venta_metro_lineal` | `subtotal = length * film_price` — **sin multiplicar por `quantity`** |
| 3 | Backend, `Proforma_Business.convertir_venta_metro_lineal` — [business/proforma.py:148](praxsa_manager/product/business/proforma.py) | `venta_metro_lineal` | `sub_total = length * window_film_price * quantity` — **sí multiplica por `quantity`** |

Puntos clave:

- **El caso `venta_instalacion` (1 y 2a) es consistente** entre Angular y el JS del admin — ambos multiplican por `quantity` y suman el término de instalación.
- **El caso `venta_metro_lineal` (2b y 3) NO es consistente entre sí**: el JS del admin (2b) no multiplica por `quantity`, pero `convertir_venta_metro_lineal` (3) sí. Es la misma regla de negocio ("sin instalación") con dos resultados numéricos distintos según qué código la ejecute. Esta es la divergencia real a corregir — no la ausencia del término de instalación en (3), que es correcta para ese caso.
- **El frontend Angular no implementa el caso `venta_metro_lineal` en absoluto** — `formulario.component.ts` no tiene ningún control para elegir `sales_type`; toda proforma creada vía la calculadora usa el default del modelo (`venta_instalacion`, [models.py:146](praxsa_manager/product/models.py)). El tipo `venta_metro_lineal` solo se alcanza a través de una acción masiva del admin de Django (`ProformaAdmin`, que invoca `convertir_venta_metro_lineal` — [admin_config/proforma_admin.py:255](praxsa_manager/product/admin_config/proforma_admin.py)), la cual **reemplaza** los `Proforma_Detail` originales por otros consolidados con el subtotal recalculado (3) — es decir, convierte una proforma ya creada como `venta_instalacion` a `venta_metro_lineal`, y al hacerlo aplica una fórmula distinta a la que usó el JS del admin si alguna vez se creó una proforma directamente como `venta_metro_lineal` desde cero.

### 2.2 El precio unitario (`bobina_price`/`film_price`) también se resuelve por duplicado

Los casos (1) y (2) de la tabla anterior no solo comparten fórmula de subtotal — el **precio unitario** que alimenta esa fórmula (`bobina_price` en Angular, `film_price` en el JS del admin) viene de la misma regla de negocio, resuelta por **dos implementaciones separadas**:

```
precio = precio_venta_sucursal.precio_venta   (si existe una fila para esa sucursal + lámina + ancho — override por sucursal)
         en caso contrario, inventario.precio_venta_mtr_lineal   (precio por defecto del lote de inventario)
```

Es decir: cada sucursal puede fijar su propio precio de venta para una lámina/ancho vía `precio_venta_sucursal`; si no lo hizo, se usa el precio que trae por defecto el lote de inventario (`inventario.precio_venta_mtr_lineal`). Esta regla está escrita dos veces con código distinto:

- **Caso 1 (Angular)** — `GET /product/get_inventory/{sucursal}/{lamina}/{width}` ([views.py:195-223](praxsa_manager/product/views.py)) llama a `Inventario_Business.get_total_meters_window_film_in_inventory()` ([business/inventario.py:75-109](praxsa_manager/product/business/inventario.py)), que anota `precio_sucursal` con un `Subquery` sobre `precio_venta_sucursal`; la vista resuelve el fallback en Python: `precio = precio_sucursal if precio_sucursal is not None else precio_venta_mtr_lineal`.
- **Caso 2 (JS del admin)** — `GET /product/get_car_part_info/{car_model_id}/{sucursal}` ([views.py:54-141](praxsa_manager/product/views.py)) resuelve el mismo fallback **inline en la vista**, con `Coalesce(F('precio_sucursal'), F('precio_venta_mtr_lineal'))` directamente en el ORM — sin pasar por `business/inventario.py`.

Mismo resultado hoy, pero es la misma clase de riesgo que la fórmula del subtotal (2.1): dos implementaciones independientes de una misma regla de negocio pueden divergir con el tiempo sin que nada lo detecte. Vale aclarar, además, una corrección a una suposición anterior de este documento: **`Window_Film_Reel.price` no participa en ninguno de los dos cálculos que ve el cliente** — el precio "de catálogo" en `Window_Film_Reel` no es la fuente que se cotiza; la fuente real es el par `precio_venta_sucursal` / `inventario.precio_venta_mtr_lineal` descrito arriba.

### 2.3 Ninguna de las fuentes anteriores es la fuente de verdad validada por el servidor

Como documentan ambas auditorías (backend BIZ-01, frontend BIZ-01) y se confirmó al verificar: **el backend no recalcula ni valida el precio recibido contra `precio_venta_sucursal`/`inventario.precio_venta_mtr_lineal` (el precio unitario real) ni contra `Car_Model_Part.installation_price` en ningún camino de creación de proforma** — ni en el admin (`save_model`/`save_related` no lo hacen en creación) ni en el REST (`SalesHeaderSerializer.create()` persiste los valores recibidos tal cual). El valor que termina en `Proforma_Header.total_price` es, literalmente, el que decidió calcular el cliente (navegador o JS del admin), sin ningún punto de verificación server-side.

**Recomendación**: el backend debe ser la única fuente de verdad, para el precio unitario y para el subtotal de **ambos** `sales_type`. Concretamente:
- Crear un único método de servicio en `business/` (p. ej. un `PricingService`) que (a) resuelva el precio unitario con la misma regla `precio_venta_sucursal` → fallback `inventario.precio_venta_mtr_lineal`, reemplazando las dos implementaciones de 2.2, y (b) exponga dos funciones de subtotal explícitas y con test — `calculate_subtotal_con_instalacion(length, quantity, precio_unitario, installation_price)` y `calculate_subtotal_metro_lineal(length, quantity, precio_unitario)` — en vez de dejar que cada archivo decida por su cuenta si multiplica por `quantity` o no.
- Antes de tocar código, **decidir con negocio** cuál de las dos fórmulas de `venta_metro_lineal` es la correcta (¿el metraje de un ítem se multiplica por su `quantity` o no? — ver pregunta de negocio nueva en sección 6), ya que hoy hay dos implementaciones en producción que no concuerdan.
- Reusar el método desde `SalesHeaderSerializer.create()` (recalculando en vez de confiar en `sub_total`/`total_price` recibidos) y desde `ProformaAdmin.save_related`/`save_model` (validando o recalculando, no solo confiando en el form).
- Corregir `convertir_venta_metro_lineal` y la rama `else` de `calculate_subtotal` en `sales_event.js` para que ambas llamen a la misma fórmula ya decidida.
- El frontend (Angular y el JS del admin) puede seguir calculando un estimado para UX/preview inmediato, pero ese valor nunca debe ser lo que se persiste sin verificación server-side. Si se agrega soporte a `venta_metro_lineal` en la calculadora Angular (hoy ausente, ver 2.1), debe usar la misma fórmula decidida, no una cuarta implementación.

### 2.4 Tercer caso de duplicación: chequeo de sesión

No es cálculo de precio, pero es el mismo patrón de "misma lógica repetida en vez de centralizada": el chequeo manual de `if (!this.currentUser) { router.navigateByUrl('/login') }` se repite en `pages/lista/lista.component.ts`, `pages/proforma/proforma.component.ts` y (invertido) `components/create-user/create-user.component.ts`, en vez de un `AuthGuard` (`CanActivate`) central (frontend BIZ-02). Se referencia aquí porque comparte la misma causa raíz que el problema de precio: falta una capa central que las distintas rutas de código reusen.

---

## 3. Hallazgos que se contradicen o no se sostienen

Al verificar contra el código actual, **ningún hallazgo crítico o alto de ninguna de las dos auditorías resultó falso**. Todos se confirmaron con evidencia directa (archivo:línea). Lo que sí surgió:

### 3.1 Matiz de mecanismo — BIZ-03 (backend)

La auditoría backend describe `create_nota_venta_pago` ([business/proforma.py:256-257](praxsa_manager/product/business/proforma.py)) como roto porque asigna `paidment.proforma`, un atributo que no existe en el modelo `pago`. Verificado: es cierto que `pago` no tiene campo `proforma`. Pero el matiz importa para saber cómo fallaría en la práctica: Python permite asignar `paidment.proforma = proforma` sin error (crea un atributo de instancia efímero, no persistido) — **no lanza `AttributeError`**. El fallo real ocurre en `.save()`: como el método nunca asigna `nota_venta` (el único FK real del modelo, `NOT NULL` a nivel de base de datos), guardar lanzaría `IntegrityError`, no el error que el nombre del atributo mal puesto sugiere a primera vista. La severidad y la conclusión (código roto, sin llamadores, seguro de eliminar) no cambian — solo el mecanismo exacto del fallo.

### 3.2 Pregunta resuelta al cruzar ambas auditorías

La auditoría frontend deja como pregunta de negocio abierta #1: *"¿El backend Django recalcula y valida el precio/total de la proforma al recibir `saveProforma()`, o confía en el monto enviado por el cliente?"*. La auditoría backend (sección 5 y hallazgo BIZ-01) responde esto de forma explícita y verificada: **no, el backend no recalcula ni valida en ningún camino**. Esta pregunta se elimina de la lista unificada de la sección 6 — ya no es una incógnita, es un hallazgo confirmado (backlog #2).

### 3.3 Corrección a una suposición de una versión anterior de este mismo documento

Una primera versión de la sección 2 asumía que la fuente de precio contra la que el backend debería validar era `Window_Film_Reel.price`. Al rastrear el origen exacto de `bobina_price`/`film_price` (ver 2.2), se confirmó que **`Window_Film_Reel.price` no interviene en ninguno de los dos cálculos que ve el cliente** — la fuente real es `precio_venta_sucursal.precio_venta` (override por sucursal) con fallback a `inventario.precio_venta_mtr_lineal` (precio por defecto del lote). Se corrigió en 2.2/2.3 y en el backlog #2.

Una segunda corrección, también sobre la sección 2 de este mismo documento: la primera versión caracterizaba la fórmula (3) `convertir_venta_metro_lineal` como "divergente porque omite el término de instalación", tratándolo implícitamente como un bug. Al confirmar que `sales_type = venta_metro_lineal` es un caso de negocio real (el cliente compra la lámina sin instalación — dato aportado por el usuario y verificado en [helper/proforma.py:13-15](praxsa_manager/product/helper/proforma.py)), omitir el término de instalación en ese caso es **correcto**, no un bug. La divergencia real, corregida en 2.1, es otra: **entre las dos implementaciones del mismo caso `venta_metro_lineal`** (la rama `else` de `sales_event.js`, que no multiplica por `quantity`, y `convertir_venta_metro_lineal`, que sí) — no entre "con instalación" y "sin instalación".

### 3.4 Hallazgos nuevos, visibles solo al cruzar ambos lados

Ninguna de las dos auditorías podía detectar estos dos por sí sola, porque cada una leyó solo un lado del contrato:

- **Mismatch `get_layer_info` / `WindowsFilmService`**: el backend devuelve `{'layer': {'name', 'content'}}` (anidado bajo la clave `layer`), pero `WindowsFilmService.getWindowsFilmInfo` en el frontend trata la respuesta como un `WindowsFilm` plano (`{name, content}`), sin evidencia en el propio servicio de que desenvuelva `res.layer`. Esto **no se pudo confirmar al 100%** sin leer también el componente que consume el servicio (fuera del alcance de esta verificación) — se reporta como hallazgo probable, a confirmar con un test de integración antes de tratarlo como bug confirmado.
- **Bug de robustez en `InvoiceView.post`**: el `except Exception` externo intenta devolver `serializer.errors` sin garantía de que `serializer` exista en ese punto, con riesgo de `UnboundLocalError` enmascarando errores 500 reales (detalle en 1.4).

---

## 4. Backlog unificado — top 10 por riesgo/impacto

Para cada ítem: severidad, archivo(s), tests a escribir **antes** de tocar el código (regla del proyecto: "todo cambio de lógica de negocio lleva su test"), y pasos pequeños (1 PR por paso).

> **Nota de seguimiento (2026-09-23)**: se verificó el estado real de cada ítem contra `docs/tasks/TASK-*.md`, `docs/adr/ADR-*.md` y el historial de merges en `origin/master`. Los ítems marcados `✅ HECHO` ya están mergeados a `master`; el resto sigue pendiente. Detalle de qué falta de cada ítem parcialmente resuelto, en su propia sección.

### 1. ✅ [CRÍTICO] Secretos de producción committeados en git — **HECHO (parcial)**
**TASK-001, PR [#29](https://github.com/rolion/praxsa-django-panel-admin/pull/29) (mergeado, `origin/master` commit `6663fcd`).** Se implementó la inyección de secretos en runtime vía `env_file` para el despliegue de producción (Docker), según ADR-001, resolviendo el paso 2 original. **Pendiente explícitamente fuera de ese PR** (decisión del usuario, no ejecutado todavía): rotar `SECRET_KEY`/password de Postgres (paso 1), y limpiar el historial de git con `git filter-repo`/BFG (paso 3) — bloqueado a coordinación con el equipo.

<details>
<summary>Descripción original del ítem</summary>

**Backend SEC-01.** `praxsa_manager/.env-prod`, `.env-dev`, `.env-stg` trackeados en git, mismo `SECRET_KEY` compartido entre entornos, password real de Postgres de producción en el historial.
- **Tests**: no aplica (no es lógica de negocio) — pero sí verificar post-rotación que la app levanta con las nuevas credenciales en cada entorno (`.env-dev`/`.env-stg`/`.env-prod`).
- **Pasos**:
  1. Rotar `SECRET_KEY` (por entorno, ya no compartido) y la contraseña de Postgres de producción — acción operativa, no PR de código.
  2. PR: mover los `.env*` fuera del repo, agregar `.env-*` a `.gitignore`, documentar en README cómo se inyectan en cada Dockerfile/pipeline.
  3. Limpiar el historial de git (`git filter-repo`/BFG) — coordinar con el equipo antes, ya que reescribe historia compartida.
</details>

### 2. 🟡 [CRÍTICO] Precio/total sin validar en servidor + fórmulas y resolución de precio divergentes — **HECHO (parcial: pasos 1-4 REST + admin `venta_instalacion`; pendiente `sales_event.js` y paso 6)**
**TASK-005, PR [#33](https://github.com/rolion/praxsa-django-panel-admin/pull/33) (mergeado, `origin/master` commit `12a9cf6`), ADR-004.** Se agregaron tests de caracterización del comportamiento actual (paso 1) y se centralizó la resolución de precio unitario + cálculo de subtotal en `business/pricing.py::Pricing_Business`, usado ahora por `SalesHeaderSerializer.create()` para recalcular/sobrescribir siempre el precio en el servidor (pasos 2-4), **solo para el camino REST usado por Angular** (`POST /product/invoice`, que siempre crea `sales_type = venta_instalacion`, nunca llega `venta_metro_lineal` por ahí).

**TASK-007, PR [#36](https://github.com/rolion/praxsa-django-panel-admin/pull/36) (mergeado, `origin/master` commit `b87dc13`), ADR-006.** Cierra la mitad de lo que quedaba del paso 5: `ProformaAdmin` (camino admin de Django) ahora recalcula y sobrescribe siempre el precio real (`Car_Model_Part.installation_price` + `Pricing_Business.resolve_unit_price`, reusado tal cual de TASK-005) para proformas `venta_instalacion`, tanto en creación como en edición — `total_price` pasa a ser la suma real de los `sub_total` de los `Proforma_Detail` persistidos (`Proforma_Business.recalculate_total_price`), reemplazando la resta manual `to_reduce` que antes solo actuaba en edición. De paso corrigió un bug de datos no documentado antes (descubierto en la investigación): `CarModelPartForm.clean()` buscaba un campo `sales_header` renombrado a `proforma_header` en la migración 0066 de 2023, lo que dejaba dormidas sus validaciones de ancho/`quantity`/`installation_price` por `sales_type` desde entonces. Reactivar ese código expuso, en 3 pasadas sucesivas de review, comparaciones sin proteger contra campos vacíos (`quantity`, `installation_price`, `width`) que antes eran inalcanzables — las 3 corregidas, con un test de barrido permanente que cubre cualquier campo requerido omitido para ambos `sales_type`. Verificado con 17 tests nuevos + regresión de 63/63 contra Postgres real, más verificación manual en vivo en el admin (POST manipulado → servidor persiste el valor recalculado; `Car_Model_Part` faltante → rechazo, no 500).

**Pendiente (fuera de alcance de TASK-007 por decisión explícita de ADR-006):**
- **`sales_event.js`** (rama `else` de `calculate_subtotal`, camino admin del lado navegador) y **`Proforma_Business.convertir_venta_metro_lineal`** (paso 6): ninguno de los dos se tocó — el drift de la sección 2.1 (`sales_event.js` no multiplica por `quantity`, `convertir_venta_metro_lineal` sí, para el mismo caso `venta_metro_lineal`) **sigue sin resolverse**.
- `venta_metro_lineal` sigue sin ninguna verificación server-side de precio en ningún camino (REST nunca lo alcanza, admin lo deja fuera explícitamente en ADR-006) — deuda conscientemente aceptada, no un olvido.
- La pregunta de negocio bloqueante de la sección 6 (¿`venta_metro_lineal` multiplica por `quantity` o no?) sigue sin respuesta registrada; sigue siendo necesaria antes de poder cerrar `sales_event.js`/paso 6.

<details>
<summary>Descripción original del ítem</summary>

**Backend BIZ-01 + Frontend BIZ-01 + QUAL-01, unificados** (detalle en sección 2). Cubre tres capas del mismo problema: (a) el precio unitario (`precio_venta_sucursal.precio_venta`, con fallback a `inventario.precio_venta_mtr_lineal`) se resuelve con dos implementaciones separadas (2.2); (b) dentro del caso `venta_metro_lineal`, el JS del admin y `convertir_venta_metro_lineal` calculan el subtotal de forma distinta entre sí — uno multiplica por `quantity`, el otro no (2.1); (c) ninguna de las dos capas se valida server-side al crear la proforma.
- **Tests**: primero, tests que capturan el comportamiento **actual** de ambos `sales_type` (un POST a `/product/invoice` con `sub_total` arbitrariamente distinto al precio real de `precio_venta_sucursal`/`inventario.precio_venta_mtr_lineal` se persiste tal cual; y un test que documenta explícitamente el resultado numérico distinto entre la rama `else` de `sales_event.js` y `convertir_venta_metro_lineal` para el mismo input, como evidencia del bug antes de decidir cuál es la fórmula correcta). Luego, tests que definen el comportamiento esperado una vez resuelta la pregunta de negocio de la sección 6.
- **Pasos**:
  1. PR: tests de caracterización del comportamiento actual en `SalesHeaderSerializer`/`InvoiceView`, más un test que reproduce numéricamente la divergencia de `venta_metro_lineal` (sin tocar lógica todavía).
  2. Resolver con negocio cuál fórmula de `venta_metro_lineal` es correcta (¿multiplica por `quantity` o no?) — bloqueante para los pasos siguientes.
  3. PR: centralizar la *resolución del precio unitario* (regla `precio_venta_sucursal` → fallback `inventario.precio_venta_mtr_lineal`) en un único método de `business/`, reemplazando las implementaciones separadas de `get_inventory` y `get_car_part_info` (sección 2.2).
  4. PR: crear el método centralizado de *cálculo de subtotal*, con una función por `sales_type` (con instalación / metro lineal, usando la fórmula ya decidida en el paso 2), y usarlo en `SalesHeaderSerializer.create()`, ignorando/validando `sub_total`/`total_price` recibidos.
  5. PR: reusar el mismo método en `ProformaAdmin.save_model`/`save_related` (camino admin) y en la rama `else` de `calculate_subtotal` en `sales_event.js` (o su equivalente si se recalcula server-side).
  6. PR: corregir `convertir_venta_metro_lineal` para usar el método centralizado (elimina el drift confirmado en 2.1).
</details>

### 3. ⬜ [CRÍTICO] Condición de carrera / sobreventa de inventario — **PENDIENTE**
**Backend BIZ-02.** `reduce_inventory`/`return_to_inventory` ([business/inventario.py:35-66](praxsa_manager/product/business/inventario.py)) sin `select_for_update`.
- **Tests**: test de concurrencia (dos llamadas a `create_work_note` casi simultáneas para la misma sucursal/bobina/ancho con stock exacto para una sola) que hoy demuestra la sobreventa; debe pasar a demostrar que la segunda falla correctamente tras el fix.
- **Pasos**:
  1. PR: test que reproduce la condición de carrera (puede requerir `TransactionTestCase` + threads o simular con dos transacciones manuales).
  2. PR: agregar `select_for_update()` en `reduce_inventory` y `return_to_inventory`.
  3. PR (opcional, red de seguridad adicional): `CheckConstraint(to_install__gte=0)` a nivel de base de datos.

### 4. ✅ [ALTO] IDOR — cualquier usuario ve proformas ajenas — **HECHO**
**TASK-008, PR [#35](https://github.com/rolion/praxsa-django-panel-admin/pull/35) (mergeado, `origin/master` commit `9815652`), ADR-006.** `InvoiceView.get` ahora filtra `.get(id=pk, created_by=request.user)` (mismo patrón que `ListUserInvoice.get`). `get_proforma_car_part_info` se cerró con un mecanismo distinto al sugerido originalmente por este mismo ítem: en vez de "filtrar por pertenencia como `ListUserInvoice`", exige `is_staff` y acota por sucursal/rol reusando `Proforma_Business.get_proforma_queryset_by_role` (el mismo método que ya protege `ProformaAdmin`) — su consumidor real resultó ser el staff que arma la nota de trabajo, no el cliente dueño de la proforma, así que el filtro por `created_by` sugerido habría roto ese flujo. Verificado con 10 tests nuevos (matriz completa de autorización) + regresión de 56/56 + verificación HTTP en vivo con servidor real (login real de admin, token real).

<details>
<summary>Descripción original del ítem</summary>

**Backend SEC-04 + SEC-05.** `InvoiceView.get` sin filtrar por `created_by`; `get_proforma_car_part_info` sin auth ni filtro.
- **Tests**: test con dos usuarios (A crea una proforma, B intenta leerla por `pk`) que hoy pasa (B accede) y debe pasar a fallar con 403/404.
- **Pasos**:
  1. PR: test + fix en `InvoiceView.get` (agregar `.filter(created_by=request.user)`).
  2. PR: test + fix en `get_proforma_car_part_info` (requerir auth y filtrar por pertenencia, mismo patrón que `ListUserInvoice`).
</details>

### 5. ✅ [ALTO] Endpoints públicos sin autenticación exponen stock/precios — **HECHO**
**TASK-006 (renombrado de TASK-002), PR [#30](https://github.com/rolion/praxsa-django-panel-admin/pull/30) (mergeado, `origin/master` commit `4c79e20`), ADR-005.** Decisión de negocio ya tomada y aplicada: `calculator_info`/`model_parts` quedan públicos intencionalmente; `get_inventory`/`get_layer_info` siguen públicos pero ahora con `AllowAny` explícito + throttle (`60/min`); `get_bobina` se cerró con chequeo de `is_staff` (no lo consume `proforma`). Verificado en navegador contra datos reales (calculadora pública, `get_bobina` 403 anónimo / 200 staff).

<details>
<summary>Descripción original del ítem</summary>

**Backend SEC-03.** 7 vistas de función plana sin `@api_view` (`get_bobina`, `get_car_part_info`, `get_proforma_car_part_info`, `get_layer_info`, `get_inventory`, `get_calculator_info`, `get_model_parts`).
- **Tests**: para cada endpoint, un test que documente si debe seguir siendo público o no (requiere la respuesta a la pregunta de negocio en sección 6 sobre cuáles son intencionalmente públicos).
- **Pasos**:
  1. PR: decisión + test explícito marcando `calculator_info`/`model_parts` como públicos intencionalmente (son datos de referencia).
  2. PR: convertir `get_inventory` (expone stock/precio por sucursal) a `@api_view` con permisos explícitos.
  3. PR: mismo tratamiento para `get_bobina`/`get_layer_info` según la decisión de negocio.
</details>

### 6. ✅ [ALTO] Token de sesión + PII en `localStorage` sin defensas — **HECHO (pasos 1-2 de 3)**
**TASK-003 (PR [#31](https://github.com/rolion/praxsa-django-panel-admin/pull/31), mergeado, commit `2761fbd`) + TASK-004 (PR [#30](https://github.com/rolion/praxsa-django-panel-admin/pull/30), mergeado, commit `4c79e20`, ADR-003).** Paso 1: `logout()` ahora también limpia `email`. Paso 2: se redujo el PII persistido en `localStorage` a solo `token`+`name`; el resto (`email`, `phone_number`, `ci_nit`) vive en memoria vía el `BehaviorSubject` ya existente. Verificado end-to-end en navegador (login → localStorage solo con token+name → refresh → saludo/guard sobreviven).
**Pendiente:** paso 3, migrar el token a cookie `httpOnly`/`secure` — documentado explícitamente como épica separada, no forzado aún.

<details>
<summary>Descripción original del ítem</summary>

**Frontend SEC-01.** Token y PII (nombre, teléfono, email, CI/NIT) en `localStorage` en texto plano.
- **Tests**: test de `AutheticationService` que verifique qué se guarda y qué se limpia en `logout()` (la verificación ya detectó que `logout()` no limpia `email`, aunque `login()` sí lo guarda — bug menor a corregir en el mismo paso).
- **Pasos**:
  1. PR chico: corregir `logout()` para limpiar también `email` (paridad con lo que `login()` guarda).
  2. PR: evaluar reducir el PII persistido en `localStorage` a lo estrictamente necesario para la UI (nombre para saludo, nada más), moviendo el resto a estado en memoria.
  3. Ítem de mayor alcance (requiere coordinación con backend, no es un PR chico): migrar el token a cookie `httpOnly`/`secure` — documentar como épica separada, no forzarlo en las primeras dos semanas.
</details>

### 7. ✅ [ALTO] Sin manejo de sesión expirada ni route guards — **HECHO**
**PR [#22](https://github.com/rolion/praxsa-django-panel-admin/pull/22) "Manejar 401 en el interceptor HTTP del frontend" (mergeado) + PR [#27](https://github.com/rolion/praxsa-django-panel-admin/pull/27) "Centraliza el chequeo de sesión en AuthGuard" (mergeado).** `app-http-interceptor.ts` maneja 401 (con test); se creó `guards/auth.guard.ts` (`CanActivate`, con test) y se aplicó en `app-routing.module.ts`, eliminando los chequeos manuales duplicados en `lista.component.ts`/`proforma.component.ts` (conecta con sección 2.3, ya resuelta).

<details>
<summary>Descripción original del ítem</summary>

**Frontend SEC-02 + BIZ-02, unificados.** Cero manejo de 401/403 en el interceptor; rutas privadas protegidas solo por chequeos manuales en `ngOnInit`.
- **Tests**: test del interceptor simulando una respuesta 401 → debe limpiar sesión y redirigir a `/login`. Test del guard: usuario no autenticado → `canActivate` retorna `false`/redirige.
- **Pasos**:
  1. PR: agregar manejo de 401/403 en `app-http-interceptor.ts` (o un interceptor de errores adicional) con test.
  2. PR: crear `AuthGuard` (`CanActivate`) reutilizable con test, aplicarlo a `my-invoice`, `proforma/:id`, `create-user` en `app-routing.module.ts`, eliminando los chequeos manuales duplicados (conecta con sección 2.3).
</details>

### 8. ✅ [ALTO] Cobertura de tests real: cero en ambos lados — **HECHO**
**PR [#20](https://github.com/rolion/praxsa-django-panel-admin/pull/20) "Add backend test harness for product app" (mergeado) + PR [#26](https://github.com/rolion/praxsa-django-panel-admin/pull/26) "Fix 22 preexisting frontend testbed failures" (mergeado).** Harness backend (`product/tests/helpers.py`, fixtures reusables) y harness frontend (arregló los 22 specs rotos que solo hacían `toBeTruthy()`, ahora con providers/mocks reales) ya existen y se usaron como base de los tests de los ítems #2, #5, #6, #7, #10.

<details>
<summary>Descripción original del ítem</summary>

**Backend QUAL-05 + Frontend TEST-01.** `product/tests.py` es boilerplate; los 21 `*.spec.ts` del frontend solo verifican `toBeTruthy()`.
- Este ítem se posiciona antes de varios de los anteriores en el orden de ataque (sección 5) porque los bloquea con seguridad: no se puede aplicar la regla del proyecto "todo cambio de lógica de negocio lleva su test" sin un harness mínimo funcionando primero.
- **Pasos**:
  1. PR: harness de tests backend para `product/` (fixtures mínimos: usuario, sucursal, marca/modelo, `Window_Film_Reel`, `inventario`) reusable por los tests de los ítems #2-#5.
  2. PR: harness de tests frontend para `AutheticationService`/interceptor/guard (reusable por el ítem #7).
  3. A partir de aquí, cada PR de los ítems #2-#7 ya incluye sus propios tests — no hace falta un PR de "cobertura general" separado.
</details>

### 9. 🟡 [MEDIO] Sin máquina de estados para proforma→instalación→venta→pago — **HECHO (parcial: pasos 1-2 de 3)**
**TASK-009, PR [#37](https://github.com/rolion/praxsa-django-panel-admin/pull/37) (mergeado, `origin/master` commit `f37473a`), ADR-006.** Se agregaron tests de caracterización del flujo actual (paso 1) y un campo `status` persistido en `Proforma_Header` (`proforma`/`nota_trabajo`/`por_cobrar`/`finalizado`), sincronizado explícitamente por un único método (`Proforma_Business.refresh_status`, misma lógica que `ProformaAdmin.get_estado`) en las 5 transiciones reales de negocio, incluida una quinta (`Orden_Trabajo_Business.delete_work_note`) detectada durante la implementación (paso 2). Backfill de datos existentes verificado contra Postgres real: 25/25 proformas, 0 discrepancias contra `get_estado()`. La inferencia por `hasattr()` del admin **no se tocó** — sigue siendo la fuente visible hoy.
**Pendiente (diferido explícitamente por ADR-006):**
- Paso 3: `CheckConstraint`/validación en `clean()` para las invariantes mínimas (p. ej. no `pago` sin `nota_venta.is_close`), y migrar `ProformaAdmin`/`NotaVentaAdmin`/`NotaTrabajoAdmin` a leer el campo `status` persistido en vez de recalcular por `hasattr()`.
- Bloqueante para el paso 3: la pregunta de negocio de la sección 6 (¿existe una regla formal de transición, o se decide caso a caso?) sigue sin respuesta registrada.
- 3 hallazgos Low de la revisión (no bloqueantes, sin resolver): `business/orden_trabajo.py` tocado fuera del alcance declarado en el plan v1; el backfill de la migración sin `select_related` (N+1 de impacto bajo); y una narrativa incorrecta en ADR-006/plan sobre el resultado de `abrir_proforma` (el código y los tests ya son correctos, solo el texto de la decisión). Detalle en `docs/reviews/REV-2026-09-23-00{1,2,3}-*.md`.

<details>
<summary>Descripción original del ítem</summary>

**Backend BIZ-04.** Estado inferido con `hasattr()`, sin campo persistido ni constraint.
- **Tests**: tests que documenten las transiciones válidas hoy (crear pago sin nota de venta cerrada, por ejemplo) antes de agregar restricciones, para no romper flujos legítimos existentes.
- **Pasos**:
  1. PR: agregar tests de caracterización del flujo actual (sin cambiar comportamiento).
  2. PR: agregar campo `status` explícito con `choices`, poblado en cada transición existente (sin quitar aún la inferencia por `hasattr`, para no romper el admin de golpe).
  3. PR: agregar `CheckConstraint`/validación en `clean()` para las invariantes mínimas (p. ej. no `pago` sin `nota_venta.is_close`), y migrar el admin a leer el campo persistido.
</details>

### 10. ✅ [MEDIO] Filtrado por sucursal inconsistente en reportes/pagos del admin — **HECHO**
**TASK-002, PR [#32](https://github.com/rolion/praxsa-django-panel-admin/pull/32) (mergeado, commit `2afeb29`), ADR-002.** `PagosAdmin`, `ReportDailySellAdmin`, `ReportStorageAdmin`, `ReportUtilidadAdmin` y `ReportNotaTrabajoAdmin` ahora filtran por sucursal (delegando en `User_Helper.can_view_all_sucursales`, corregido en producción tras verificación manual: solo el grupo `Admin` ve todas las sucursales, `Caja` queda restringido a la propia); el filtro comentado en `orden_trabajo.py` se reimplementó. 27/27 tests verificados contra Postgres real.

<details>
<summary>Descripción original del ítem</summary>

**Backend SEC-06.** `PagosAdmin`, `ReportDailySellAdmin`, `ReportStorageAdmin`, `ReportUtilidadAdmin` no filtran por sucursal del usuario; `orden_trabajo.py` tiene el filtro comentado.
- Depende de la respuesta a la pregunta de negocio sobre quién debe ver datos de todas las sucursales (sección 6) antes de decidir si es "bug" o "comportamiento reservado a un rol".
- **Tests**: test por cada `ModelAdmin` afectado, con dos usuarios de distinta sucursal, verificando qué debería ver cada uno según la decisión de negocio.
- **Pasos**:
  1. PR: aplicar el patrón de `get_queryset` filtrado por sucursal (ya usado en `InventoryAdmin`/`ProformaAdmin`) a `PagosAdmin` y `ReportDailySellAdmin`.
  2. PR: mismo patrón para `ReportStorageAdmin`/`ReportUtilidadAdmin`.
  3. PR: descomentar/reimplementar el filtro en `orden_trabajo.py:32-36`.
</details>

---

## 5. Orden de ataque — primeras dos semanas

> **Estado (2026-09-25)**: de los 9 pasos originales de esta sección, queda **pendiente solo el 8 (`select_for_update` en inventario)**. El paso 4 (IDOR) se cerró con TASK-008/PR #35. Todo lo demás ya está mergeado a `master` — ver checklist abajo y el detalle por ítem en la sección 4.

**Día 0 (fuera del ciclo de PRs, es un incidente activo):** rotar `SECRET_KEY` y la contraseña de Postgres de producción. **⬜ Pendiente** — explícitamente no ejecutado todavía (decisión del usuario en TASK-001), sigue siendo un incidente activo.

**Semana 1 — cerrar exposiciones activas de datos:**
1. ✅ PR chico: `.env-stg` `DEBUG=0` (SEC-02 backend, trivial, agruparlo con la limpieza de secretos) — incluido en PR #29 (TASK-001).
2. ✅ PR: sacar los `.env*` del repo y `.gitignore` (backlog #1, paso 2) — PR #29 (TASK-001).
3. ✅ PR: harness mínimo de tests backend (backlog #8, paso 1) — PR #20.
4. ✅ PR + PR: fix IDOR en `InvoiceView.get` y en `get_proforma_car_part_info` (backlog #4) — TASK-008, PR #35 (mergeado, commit `9815652`).
5. ✅ PR: manejo de 401/403 en el interceptor del frontend (backlog #7, paso 1) — PR #22.

**Semana 2 — proteger dinero e inventario:**
6. ✅ PR: tests de caracterización + recálculo server-side de precio en `SalesHeaderSerializer.create()` (backlog #2, pasos 1-2) — PR #33 (TASK-005).
7. 🟡 PR: centralizar la fórmula en `business/` y reusarla en el admin + corregir `convertir_venta_metro_lineal` (backlog #2, pasos 3-4) — la centralización en `business/pricing.py` y el uso en `SalesHeaderSerializer.create()` **sí se hizo** (PR #33); reusarla en `ProformaAdmin` para `venta_instalacion` **también se hizo** (PR #36, TASK-007); reusarla en `sales_event.js` y corregir `convertir_venta_metro_lineal` (paso 6, `venta_metro_lineal`) **sigue pendiente**, bloqueado por la pregunta de negocio de la sección 6.
8. ⬜ PR: `select_for_update()` en inventario + test de concurrencia (backlog #3) — **sigue pendiente**, ningún PR lo tocó.
9. ✅ PR: `AuthGuard` en frontend, reemplazando los chequeos manuales (backlog #7, paso 2) — PR #27.

**Por qué este orden**: primero lo que ya es explotable hoy sin esfuerzo (secretos en git, IDOR con solo cambiar un `pk` en la URL) — es exposición de datos activa, no un riesgo teórico. Después, lo que protege dinero directamente (precio confiado al cliente, sobreventa de inventario), que requiere más diseño (de ahí que quede en la semana 2, con tests de caracterización primero). Lo estructural (máquina de estados #9, filtrado de reportes #10) y lo de menor severidad quedan fuera de las primeras dos semanas — se abordan después, una vez cerrada la exposición activa y protegido el dinero.

**Siguientes pasos recomendados, dado lo ya hecho**: con el IDOR (#4) ya cerrado y la mitad del paso 5 del ítem #2 resuelta (PR #36, recálculo de precio en `ProformaAdmin` para `venta_instalacion`), la condición de carrera de inventario (#3, `select_for_update`) queda como el hueco de mayor severidad sin tocar — es el candidato natural para el próximo ciclo de tasks. Lo que queda del ítem #2 (`sales_event.js` y `convertir_venta_metro_lineal`, paso 6) sigue bloqueado por la misma pregunta de negocio sin responder (sección 6: ¿`venta_metro_lineal` multiplica por `quantity` o no?) — no es un task de código listo para tomar hasta que se resuelva esa pregunta con negocio.

---

## 6. Preguntas de negocio pendientes (unificadas, deduplicadas)

### Seguridad y accesos
- ¿Quién debe poder ver pagos, costos y utilidad de **todas** las sucursales frente a solo la propia? (Determina si backlog #10 es un bug de seguridad o un comportamiento intencional reservado a ciertos roles, p. ej. gerencia general.)
- ¿El campo `Sucursal.empleado` (M2M a `User`) es la única fuente de verdad para "a qué sucursal pertenece un usuario", o existe otro mecanismo (grupos, perfil extendido) que también deba respetarse al corregir el filtrado por sucursal?
- De los endpoints públicos sin autenticación (backlog #5): ¿cuáles son intencionalmente públicos (p. ej. `calculator_info`, pensado para la calculadora sin login) y cuáles deberían requerir sesión (p. ej. `get_inventory`, que expone stock/precio real por sucursal)?
- ¿Quién es el dueño/responsable de definir qué PII es aceptable persistir en el cliente (nombre, teléfono, email, CI/NIT) en `localStorage` del frontend?
- ¿Hay ya un plan o proceso de rotación de credenciales, o esta auditoría es la primera vez que se detecta que `SECRET_KEY` y la contraseña de Postgres de producción están committeados en git?

### Flujo de negocio
- ¿Existe una regla de negocio formal para las transiciones proforma → instalación → venta → pago, o se decide caso a caso por el personal? (Determina el alcance real de backlog #9.)
- El flujo REST `/product/invoice` (usado por la calculadora del frontend): ¿el precio que envía se considera siempre "cotizado" y por ende confiable tal cual, o el backend debería recalcularlo server-side de todas formas? (Ya está resuelto que hoy el backend **no** recalcula — ver sección 3.2 — esta pregunta es sobre si ese comportamiento es aceptable o debe cambiar, no sobre si existe.)
- El campo `status` que el frontend modela y envía en `Invoice` pero el backend nunca persiste ni devuelve (sección 1.5): ¿se planeaba una funcionalidad de estado visible en el frontend que quedó incompleta, o es código muerto a limpiar de ambos lados?
- Para el caso `venta_metro_lineal` (sin instalación, sección 2.1): cuando un ítem tiene `quantity > 1`, ¿el subtotal debe multiplicarse por `quantity` (como hace `convertir_venta_metro_lineal`) o no (como hace la rama `else` de `sales_event.js`)? Hoy el sistema tiene ambas respuestas en producción según qué código se ejecute — es una pregunta bloqueante para el backlog #2.
- ¿Por qué el token de sesión no tiene expiración/refresh visible desde el cliente? ¿El backend expira tokens del lado servidor de alguna forma que el frontend simplemente no maneja?

### Infraestructura y deploy
- Existen dos archivos `docker-compose.prod.yml` (uno en la raíz del repo, otro dentro de `praxsa_manager/`) con configuraciones de exposición de puertos distintas — ¿cuál de los dos se usa realmente para desplegar producción hoy?
- Sobre `on_delete=DO_NOTHING` en todas las FK del backend: ¿la base de datos de Postgres tiene reglas `ON DELETE` definidas directamente a nivel de esquema que mitiguen el riesgo de filas huérfanas? No se pudo verificar desde el código Django.
- ¿Es intencional que `proforma/dist/proforma` esté commiteado en el repo (p. ej. porque el deploy lo consume directamente), o es un descuido?
- ¿El proxy `proforma/src/app/proxy.conf.json` (`/product` → `localhost:3000`) sigue en uso, o es configuración obsoleta de un entorno de desarrollo anterior?
- ¿Hay planes de mover parte de la calculadora o el listado de proformas a rutas con lazy loading en el frontend, o el tamaño actual de la app no lo justifica?
