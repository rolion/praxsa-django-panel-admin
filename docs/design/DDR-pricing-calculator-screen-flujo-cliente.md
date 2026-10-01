# DDR-pricing-calculator-screen-flujo-cliente: Calculadora para cliente final con login/registro en modal, menú superior y lista de proformas de solo lectura

**Estado:** Propuesto
**Task relacionado:** TASK-pricing-calculator-screen
**Fecha:** 2026-09-30

## Contexto

Reemplaza a [DDR-pricing-calculator-screen-pantalla-calculadora](DDR-pricing-calculator-screen-pantalla-calculadora.md) (estado pasa a `Reemplazado por DDR-pricing-calculator-screen-flujo-cliente`), que asumía un asesor staff y hacía que "Crear Proforma" abriera el formulario interno de Órdenes, donde reaparecía el menú lateral completo (defecto que el usuario reportó tras ver la v1).

La reinvestigación del TASK (sección "Cambio de alcance") fija el nuevo actor: **cliente final con cuenta propia**, dentro de `panel_admin/`, sin sidebar ni acceso a los recursos de administración, con la **placa guardada en la cuenta**. Flujo pedido: la persona cotiza → pide guardar → si no tiene sesión, inicia sesión o crea cuenta en un modal → la proforma se guarda → ve **su lista de proformas** (solo lectura).

**Se hereda sin cambios** del DDR anterior (sigue vigente): título + stepper propio de 3 pasos, card de filtros Sucursal/Marca/Modelo con cascada, tabla de ítems con select de lámina apta y subtotal, exclusión/restauración de ítems, resumen sticky con imagen del modelo y total destacado, estados inicial/cargando/sin resultados/error, barra inferior de total en móvil, alerta informativa de precios y el criterio de no mostrar el badge "Recomendada" sin regla de negocio. **Cambia** lo que rodea a esa pantalla (encabezado, acciones, autenticación y lista) y la acción "Crear Proforma".

## Pantallas/flujos afectados

1. **Calculadora de precios** (ya existe en v1; cambia de acciones). Es navegable **sin sesión**: cotizar y "Consultar por WhatsApp" no exigen cuenta; la sesión se pide **solo al guardar**.
2. **Encabezado del cliente** (variante del header sin sidebar): logo a la izquierda; a la derecha, según estado de sesión (ver abajo).
3. **Modal de acceso** (nuevo) con dos modos: **Iniciar sesión** y **Crear cuenta** (asistente de 2 etapas).
4. **Mis proformas** (nueva): lista de solo lectura de las proformas del usuario, con el mismo encabezado.
5. **Flujo guardar**: Crear Proforma → (modal si no hay sesión) → guardado → Mis proformas con confirmación.

## Componentes/patrones elegidos

| Zona | Elección | Base |
|---|---|---|
| Encabezado cliente | Header de la plantilla en variante sin sidebar (ya hay variante `minimal` con logo). Sin sesión: botón "Iniciar sesión" (primario) y enlace "Crear cuenta". Con sesión: enlaces de navegación **Calculadora** y **Proformas** junto al logo y el dropdown de usuario (nombre + Logout) a la derecha. En móvil, los dos enlaces pasan a un menú colapsable (`navbar-expand-lg` ya presente) para no perder Logout. | `reference.md` estructura `layout/header`; header actual `header.component.html` |
| Modal de acceso | `NgbModal` + componente standalone + `ReactiveForms`, patrón de `pago-modal.component.ts` (9 componentes ya lo usan). Un solo modal que alterna login ↔ registro, sin cambiar de ruta (la cotización queda intacta detrás). | `reference.md` → `form-elements.html` y `form-validation.html` (mensajes de error estilizados) |
| Asistente de registro | Indicador de 2 pasos propio dentro del modal (mismo estilo que el stepper de la calculadora), no `angular-archwizard`: son solo dos etapas de un modal. | DDR anterior (mismo criterio) |
| Lista Mis proformas | `ngx-datatable` (mismo componente que los listados de Órdenes y la vista de proforma), paginación cliente, sin acciones. | `reference.md` → `ngx-datatable.html` y `advance-table/`; DDR de Órdenes (Actualización 3) |
| Confirmación | Mensaje de éxito tipo toast (`ngx-toastr` ya está en `package.json`) al volver a la lista, y la fila nueva resaltada unos segundos. | `panel_admin/package.json` |
| Estilos | Se extiende `assets/scss/_calculadora.scss` (clases `.calc-*`, `.layout-minimal`); sin estilos de componente por el presupuesto `anyComponentStyle`. | Decisión previa del módulo Órdenes |

## Diseño de cada zona

**Encabezado.**
- *Sin sesión:* `[Logo]` … `[Iniciar sesión]` `Crear cuenta`. Ambos abren el mismo modal (modo distinto). No se muestran "Calculadora"/"Proformas" (no hay lista que ver).
- *Con sesión:* `[Logo]  Calculadora  Proformas` … `[ícono usuario ▾]` (nombre, "Cerrar sesión"). El enlace activo se marca (subrayado/color de acento). Sin fullscreen ni toggle de sidebar.
- Nunca aparece el menú lateral ni enlaces a administración.

**Modal – Iniciar sesión.**
Campos: *Usuario o correo*, *Contraseña* (con mostrar/ocultar). Botón **Ingresar** (deshabilitado con spinner mientras envía) y enlace "¿No tienes cuenta? **Crear cuenta**". Errores: "Credenciales inválidas" y "No se pudo conectar, inténtalo de nuevo" (como en el login actual). Cerrar con la X/Escape vuelve a la calculadora sin perder la cotización; el modal no se cierra por clic fuera mientras se envía.

**Modal – Crear cuenta (2 etapas, indicador "1 Tus datos · 2 Tu acceso").**
- *Etapa 1 – Datos principales:* Nombre, Apellido, Correo, Teléfono, Placa del vehículo. Botones: **Siguiente** (valida solo esta etapa) y "¿Ya tienes cuenta? Iniciar sesión".
- *Etapa 2 – Credenciales:* Nombre de usuario (**precargado con el correo de la etapa 1, editable**, con la nota "Puedes usar tu correo"), Contraseña, Confirmar contraseña (ambas con mostrar/ocultar y un texto de requisitos). Botones: **Atrás** (conserva lo escrito) y **Crear cuenta**.
- Validación en el mismo estilo del formulario de proforma (errores bajo el campo, al tocar o al intentar avanzar): obligatorios, correo válido, teléfono de 7–11 dígitos (mismo criterio que el formulario de proforma), placa de hasta 10 caracteres, contraseñas iguales. Errores del servidor (correo o usuario ya existentes, contraseña rechazada) se muestran sobre el campo afectado o como alerta en la etapa correspondiente; si el error es de la etapa 1 (p. ej. correo duplicado) se vuelve a esa etapa.
- *Éxito:* queda con la sesión iniciada y **continúa guardando la proforma** (sin pedir login otra vez).

**Crear Proforma (acción del resumen y de la barra inferior móvil).**
1. Sin sesión → abre el modal (modo Iniciar sesión) con el mensaje "Inicia sesión o crea tu cuenta para guardar tu proforma".
2. Con sesión → guarda directamente (botón con spinner, deshabilitado para evitar doble envío). **No hay paso de datos del cliente**: nombre, correo, teléfono y placa salen de la cuenta; el resumen muestra "A nombre de: Nombre Apellido · Placa XXX".
3. Éxito → navega a **Mis proformas**, toast "Proforma N guardada", fila resaltada. El paso 3 del stepper ("Proforma") se marca mientras se guarda.
4. Error → alerta en el resumen (texto del servidor, p. ej. "No hay precio disponible para la lámina/ancho solicitado"), la cotización y la sesión se conservan.
5. Si la sesión venció al guardar (respuesta 401), se reabre el modal de acceso **conservando la cotización** en lugar de recargar la página; al volver a iniciar sesión se reintenta el guardado.

**Mis proformas.**
- Título "Mis proformas" con ícono, y botón secundario "Nueva cotización" (vuelve a la calculadora).
- Tabla `ngx-datatable` dentro de `section-card`: **Nº**, **Fecha** (`dd/MM/yyyy`), **Vehículo** (marca y modelo), **Placa**, **Total** (`Bs 2.090`, alineado a la derecha). Orden por fecha descendente y paginación de 10. Sin búsqueda, sin edición, sin anulación, sin PDF ni generación de nota (solo lectura).
- *Estado:* el listado actual del backend no devuelve un estado; **no se muestra columna de estado** hasta que negocio confirme que el cliente debe verlo.
- *Estados de la vista:* cargando (skeleton de filas), **vacía** ("Aún no tienes proformas" + botón "Ir a la calculadora"), error con "Reintentar".
- Móvil: la tabla desplaza horizontalmente solo dentro de la tarjeta (mismo criterio de `table-responsive`) o se apila como en la calculadora (a decidir en el plan según el espacio).

## Alternativas consideradas

- **Pantalla de login/registro de página completa** (la ruta `authentication/signin|signup` de la plantilla): descartada; expulsa a la persona de la calculadora y pierde la cotización. El modal conserva el contexto.
- **Exigir sesión para entrar a la calculadora**: descartada; el usuario pidió pedirla **al guardar** y la calculadora sirve también para cotizar sin compromiso.
- **Asistente de registro en una sola pantalla larga**: descartada; el usuario pidió etapas (datos → credenciales) y reduce la carga visual del modal.
- **Pedir datos del cliente en un paso extra al guardar** (formulario tipo proforma): descartada; ya se piden al crear la cuenta y duplicaría campos.
- **Llevar a la persona al formulario de Órdenes para guardar** (v1): descartada por el defecto reportado (sidebar/administración visibles).
- **Dejar la lista de proformas con acciones** (PDF, detalle): descartada por pedido explícito de solo lectura; detalle/PDF quedan como decisión pendiente.
- **Menú de dos opciones dentro del dropdown de usuario**: descartada; el usuario pidió las opciones en el menú superior, visibles sin abrir nada.

## Comportamiento por privilegio/estado

| Situación | Qué ve y qué puede hacer |
|---|---|
| Sin sesión | Calculadora completa (cotizar, excluir ítems, WhatsApp). Encabezado con "Iniciar sesión"/"Crear cuenta". "Crear Proforma" abre el modal. No ve Proformas. |
| Cliente con sesión | Encabezado con Calculadora / Proformas / usuario. Guarda proformas y ve **solo las suyas** en solo lectura. Nunca ve sidebar ni enlaces a administración; si escribe una URL de administración, ve la calculadora (o una página de "no disponible") en vez de la pantalla. |
| Sesión vencida al guardar | Se reabre el modal de acceso sin perder la cotización. |
| Staff (personal interno) | **No definido en este DDR** (ver pendientes): su flujo de administración con sidebar sigue siendo el existente. |

**Requiere que arquitectura defina** cómo se verifica del lado servidor, y no solo en la UI: (a) que un cliente **no pueda acceder a los recursos de administración** (rutas y endpoints) aunque conozca la URL; (b) que cada cliente vea **solo sus proformas**; (c) qué catálogos usa la calculadora sin sesión (los actuales son solo staff); (d) cómo se registra un cliente (username propio, placa en la cuenta, contraseña validada) y cómo se separa su sesión de la del staff. El frontend no debe ser la única barrera; ocultar el sidebar es solo UX.

## Decisiones pendientes (negocio/usuario)

1. **Staff**: ¿sigue entrando por el login del panel con el layout completo? ¿Se conserva o se retira el ítem "Calculadora de precios" del menú lateral de staff (v1)?
2. **Detalle y estado** de la proforma para el cliente (¿ver ítems y láminas? ¿ver estado? ¿descargar PDF?).
3. **CI/NIT**: no se pide en el registro pedido; ¿es obligatorio para la proforma o puede ir vacío (hoy es opcional en el registro de `proforma/`)?
4. **Etiqueta del botón**: "Crear Proforma" (original) o "Guardar proforma" (lenguaje del nuevo flujo).
5. Se mantienen abiertos: regla de "Recomendada", número de WhatsApp (global vs. por sucursal), formato de importes y textos finales.

## Consecuencias

- **Más simple:** el cliente no vuelve a escribir sus datos; un único punto de acceso (modal) sirve a login, registro y sesión vencida; la cotización nunca se pierde al autenticarse.
- **Reutiliza** lo ya construido: toda la pantalla de calculadora v1 (filtros, tabla, resumen, estados, estilos) y el patrón de modal y de tabla de Órdenes.
- **Deuda/inconsistencia aceptada:** en `panel_admin/` conviven dos experiencias (administración con sidebar y cliente sin sidebar); la variante de header crece (logo, menú de dos opciones, modo sin sesión). La vista de lista de cliente no tiene estado ni acciones hasta que negocio decida.
- **Pantallas v1 que quedan inconsistentes si no se actualizan:** el flujo "Crear Proforma → formulario de Órdenes" y el ítem del menú de staff ya no corresponden a este diseño; el plan debe retirarlos o reubicarlos.
