# ADR-pricing-calculator-screen-registro-y-api-cliente: Registro de cliente con placa y username propio en un endpoint nuevo, perfil y lista de proformas propios, y guardado con `POST invoice` existente

**Estado:** Propuesto
**Task relacionado:** TASK-pricing-calculator-screen
**Fecha:** 2026-09-30

## Contexto

El DDR `DDR-pricing-calculator-screen-flujo-cliente` pide: registro en dos etapas (nombre, apellido, correo, teléfono, placa; luego usuario, contraseña y confirmación), guardado de proforma con los datos de la cuenta y una lista de proformas del usuario en solo lectura; la placa se guarda **en la cuenta** (decisión del usuario). Hechos de la investigación:
- `POST product/create_client` (`views.py:331-339`, `AllowAny`) → `ClientSerializer` (`serializer/client_serializer.py:6-40`): `email` único, `password` sin validar con `validate_password` (`:10`; `AUTH_PASSWORD_VALIDATORS` existe en `settings.py:168-182`), `name`, `lastname`, `phone_number`, `ci_nit` opcional; fija `username=email` (`:19`); sin placa ni username propio. Lo consume también `proforma/` (`authetication.service.ts:35-42`).
- `Client` (`models.py:97-107`): sin placa. Última migración `0114_precio_venta_sucursal_unico.py`.
- `POST product/invoice` (`custom_views/invoice.py:15-34`): `TokenAuthentication` + `IsAuthenticated`, `created_by = request.user`; `SalesHeaderSerializer` recalcula el precio en servidor (ADR-004; `invoice_serializer.py:37-72`), sin las reglas de ancho/metros de `business/pricing.py:158-162`. `ci_nit` del header es `null=True` sin `blank` (`models.py:174`).
- `GET product/invoice/all` (`invoice.py:74-105`): filtra por `created_by`, **no excluye `is_delete`**, sin marca ni estado, y `date` con formato `"%d%m/%Y"` (`:94`); lo consume `proforma/` (`proforma.service.ts:49`).
- `get_calculator_info` (`views.py:252-280`) lista `Car_Model.objects...all()` sin `is_active` y sin imagen; el ADR `ADR-modulo-vehiculos-soft-delete` (punto 4) exige que lo inactivo no aparezca en selectores.
- El throttling existente solo cubre `get_inventory`/`get_layer_info` (`settings.py:126-128`, ADR-005); no hay limitación en el registro.

## Decisión

Todo es **aditivo**; los endpoints actuales y `proforma/` quedan intactos.

1. **Modelo:** `Client.car_plate` = `CharField(max_length=10, blank=True, default='')` con migración nueva `0115_...` (aditiva; los clientes existentes quedan con placa vacía). Sin cambios en migraciones aplicadas.
2. **Registro nuevo `POST product/client/register`** (`AllowAny`, con throttle propio): serializer nuevo que acepta `name`, `lastname`, `email`, `phone_number`, `car_plate`, `username` (opcional; por defecto el correo) y `password`. Reglas de servidor: correo único (como hoy); `username` único (sin distinguir mayúsculas) y sin espacios; contraseña validada con `validate_password` de Django (el usuario se pasa al validador); teléfono con la regex actual; placa ≤ 10. Crea `User` (nunca `is_staff`, `is_superuser`, grupos ni permisos; el serializer no expone esos campos) y `Client` con la placa, en una transacción. No devuelve token: el frontend inicia sesión enseguida con el login existente (ADR `...-sesion-cliente-aislamiento`). La confirmación de contraseña se valida solo en el frontend (el servidor recibe una contraseña). `create_client` **no se modifica** (evita cambiar el comportamiento de `proforma/`).
3. **Limitación de tasa:** nuevo `scope` (p. ej. `client_register`) en `DEFAULT_THROTTLE_RATES`, con el patrón de `PublicCatalogThrottle`, tasa inicial conservadora (10/hora por IP, ajustable por configuración).
4. **Perfil propio `GET product/client/me`:** `TokenAuthentication` + `IsAuthenticated`; devuelve nombre, apellido, correo, teléfono, placa y `ci_nit` del `Client` del usuario; 404 si no tiene `Client` (p. ej. un staff). Es la fuente de los datos que el frontend precarga al guardar y que no se persisten en `localStorage` (ADR-003).
5. **Lista propia `GET product/client/proformas`:** `TokenAuthentication` + `IsAuthenticated`; filtra por `created_by = request.user` y **`is_delete = False`**, con `select_related` del modelo y la marca; devuelve `id`, fecha (`proforma_created_on` en ISO), `car_brand_name`, `car_model_name`, `car_plate` y `total_price` (string decimal). Solo lectura, sin detalle de ítems ni estado (DDR). `invoice/all` no se toca (evita romper `proforma/` y su formato de fecha).
6. **Guardar la proforma del cliente con `POST product/invoice` existente**, con la forma de datos que hoy usa `proforma/`; nombre, correo, teléfono, placa y `ci_nit` salen del perfil (punto 4). `ci_nit` no se pide en el registro: se envía `null` cuando la cuenta no lo tiene. El servidor sigue **recalculando precios** (ADR-004) y fija `created_by`; el filtro de aptitud de láminas de la calculadora es solo UX y el servidor **no** agrega en este cambio las reglas de ancho/metros de `pricing.py:158-162` a ese camino (deuda aceptada, ver Consecuencias).
7. **Catálogo público de la calculadora** (mismas decisiones en `ADR-...-catalogo-publico-calculadora`).

## Alternativas consideradas

- **Extender `create_client`** con `username`/`car_plate` opcionales y validar contraseñas: menos código, pero cambia el comportamiento de un endpoint que `proforma/` usa hoy (contraseñas que hoy se aceptan podrían rechazarse y su UI no muestra el error) y mezcla dos contratos. Descartada; el costo de un endpoint nuevo es bajo.
- **Placa solo en cada proforma** (como hoy): descartada por decisión explícita del usuario.
- **Token en la respuesta del registro:** ahorra una llamada, pero duplica la lógica de emisión de token fuera de los endpoints de login; se prefiere un solo camino de sesión.
- **Modificar `invoice/all` (fecha, marca, `is_delete`)**: arregla defectos, pero el formato de fecha y la forma de la respuesta son un contrato de `proforma/`; riesgo de regresión sin necesidad. Descartada.
- **Validar aptitud de láminas en `SalesHeaderSerializer` ahora:** reduce el riesgo de proformas inconsistentes por clientes maliciosos, pero cambia un contrato usado por `proforma/` y excede el alcance de este task; se deja como deuda explícita (hoy el servidor ya recalcula el precio y el stock se valida al generar la nota de trabajo).
- **Devolver datos del cliente dentro de `PanelAdminAuthToken`:** ahorra una llamada, pero mezcla PII en un endpoint de login compartido con staff y en `localStorage` (ADR-003). Descartada.
- **Permisos Django o grupo "cliente":** no hace falta; el aislamiento es por `is_staff=False` + endpoints filtrados por propietario.

## Estrategia de rollback / mitigación

- **Migración aditiva y reversible** (`AddField` con default vacío); `migrate` hacia atrás quita la columna sin afectar otros datos. Orden de despliegue: backend primero (migración y endpoints nuevos, ninguno usado aún) y frontend después; si falla, se retira el frontend y los endpoints nuevos quedan inertes.
- Los endpoints nuevos son **independientes**: desactivar `client/register`, `client/me` o `client/proformas` (quitar la ruta) no afecta `create_client`, `invoice`, `invoice/all` ni `proforma/`.
- Mitigación de abuso del registro: throttling por IP (punto 3) y validación de contraseña; la activación de cuenta por correo queda fuera de alcance.
- Seguridad: el registro jamás asigna `is_staff`/permisos; `client/me` y `client/proformas` no aceptan identificadores de otro usuario; pruebas de servidor deben cubrir que un cliente no ve proformas ajenas ni de staff (ADR-006-idor).

## Consecuencias

- Más fácil: contrato claro para el cliente, sin tocar la app `proforma/`; la placa queda en la cuenta y se precarga en cada proforma.
- Más difícil: hay dos registros (`create_client` legado y `client/register`) y dos listados de proformas por usuario (`invoice/all` y `client/proformas`) hasta que `proforma/` se migre (fuera de alcance).
- Deuda aceptada: (a) el camino `POST invoice` no valida ancho/metros en servidor; (b) `Proforma_Header.proforma_created_on` es `auto_now` (`models.py:170`): la "fecha" de la lista cambia si la proforma se modifica después; (c) sin verificación de correo ni recuperación de contraseña; (d) el `ci_nit` queda vacío en cuentas nuevas.
- Pruebas obligatorias en el plan: registro (éxito, duplicados, contraseña débil, no crea staff), throttling, `client/me`, `client/proformas` (propietario, `is_delete`, no-cliente) y `invoice` desde un cliente.
