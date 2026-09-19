# Proyecto: gestión de proformas de láminas para autos

Sistema para gestionar proformas de láminas (polarizado) para venta e instalación en autos.
Monorepo con dos proyectos:

- `praxsa_manager/`: backend en Django + Django REST Framework. Usa el panel de administrador por defecto de Django para la gestión interna.
- `proforma/`: frontend en Angular para el cliente final. Se comunica con el backend por API.

## Flujo de negocio
El cliente entra al frontend, hace login, elige sucursal, marca y modelo de auto, y la lámina para cada parte del auto (calculadora de precios). Con eso genera una proforma. Luego va a la sucursal y se inicia la instalación de las láminas. Desde el frontend puede listar y gestionar sus proformas.

## Entidades del dominio
Inventario, sucursales, modelos de auto, ítems de auto, láminas, bobinas, proformas, instalación, instalador responsable y pago de proforma.

## Comandos (ajustar si difieren en el proyecto)
Backend (desde `praxsa_manager/`):
- Levantar: `python manage.py runserver`
- Tests: `python manage.py test`
- Verificar migraciones pendientes: `python manage.py makemigrations --check --dry-run`

Frontend (desde `proforma/`):
- Instalar: `npm install`
- Levantar: `ng serve`
- Tests: `ng test`
- Build: `ng build`

## Estado del código
El proyecto NO se construyó con buenas prácticas. Se está mejorando de forma incremental con ayuda de IA.

## Reglas de trabajo
- Cambios pequeños: un objetivo por cambio, pensado para un PR.
- No editar migraciones ya aplicadas; crear migraciones nuevas.
- El dinero se maneja con `Decimal`, nunca con `float`.
- Todo cambio de lógica de negocio lleva su test.
- No tocar archivos `.env` ni credenciales.
- No agregar dependencias sin avisar antes.
- Antes de cambios que afecten varios archivos, proponer un plan y esperar confirmación.
- Si algo no se puede verificar en el código, decirlo; no inventar.