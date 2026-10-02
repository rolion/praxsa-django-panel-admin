"""Inicializa una BD nueva con los datos de arranque del despliegue v2
(ADR-despliegue-nuevo-servidor-inicializacion-db-inicializacion-datos-seed):
grupos, permisos, sucursales, usuarios, instaladores, catalogo de vehiculos,
laminas, bobinas e inventario.

Se ejecuta A MANO (lo invoca `scripts/init-v2.sh` despues de `migrate`); nunca desde
el Dockerfile. Es idempotente: busca cada registro por su clave natural (nombre /
username) y solo crea lo que falta, sin borrar ni pisar lo existente. Todo corre en
una transaccion: un error no deja datos parciales y `--dry-run` hace el mismo
recorrido y deshace al final, informando que se crearia.

La contrasena de los usuarios sembrados sale de la variable de entorno
`DEFAULT_PASSWORD` (`praxsa_manager/.env`); `--password` la reemplaza puntualmente.
No hay valor por defecto en el codigo."""
import json
import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from django.contrib.auth.models import Group, User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from product.models import (
    Car_Brand, Car_Model, Car_Model_Part, Car_Part, Profile, Sucursal, Window_Film,
    Window_Film_Reel, instalador, inventario,
)

CATALOGO_POR_DEFECTO = Path(__file__).resolve().parents[2] / 'seed_data' / 'catalogo.json'

GRUPOS = ['Admin', 'Almacen', 'Caja', 'Vendedor']
COMANDOS_PERMISOS = ['asignar_permisos_estados', 'asignar_permisos_reportes', 'asignar_permisos_instalador_precio']

SUCURSALES = [
    {'name': 'Santa Cruz', 'address': 'Av. Ovidio Barbery entre 4to. y 5to anillo', 'phone_number': '3352139'},
    {'name': 'La Paz', 'address': 'Calle Angel Pacheco - Obrajes', 'phone_number': '78512440'},
]

USUARIOS = [
    {'username': 'superadmin', 'superuser': True, 'sucursales': ['Santa Cruz', 'La Paz']},
    {'username': 'admin1', 'superuser': False, 'sucursales': ['Santa Cruz']},
    {'username': 'admin2', 'superuser': False, 'sucursales': ['La Paz']},
]
GRUPO_USUARIOS = 'Admin'

INSTALADORES = [
    {'name': 'instalador 1', 'sucursal': 'Santa Cruz'},
    {'name': 'instalador 2', 'sucursal': 'La Paz'},
]
TELEFONO_INSTALADORES = '3554432'

_TEXTO_COLOR_STABLE = (
    'No metalizado para mantenerte conectado con dispositivos móviles, GPS o recepción de radio satelital sin '
    'interferencias, reduce el calor hasta 57% el TSER, bloquea hasta el 99% de la luz ultravioleta (UV) para '
    'brindar protección solar para usted y sus pasajeros.'
)
_TEXTO_COLOR_STABLE_IR = (
    'La película 3M Color Stable IR para ventanas automotrices está fabricada con partículas nanocerámicas '
    'impregnadas en el poliéster de la película.'
)
_TEXTO_CRYSTALLINE = (
    'Excelente rendimiento de rechazo de calor prácticamente transparente, bloquea hasta el 99% de la luz '
    'ultravioleta (UV) para brindar protección solar para usted y sus pasajeros. Ofrece un deslumbramiento reducido '
    'de la luz solar para que pueda ver mejor y concentrarse más en la carretera.'
)

LAMINAS = [
    ('CA 35',
     'Las nanopartículas cerámicas absorben y rechazan el calor, manteniendo la claridad. Las opciones de '
     'iluminación transmiten casi toda la luz visible para mantener los interiores brillantes, las opciones oscuras '
     'ayudan a reducir el deslumbramiento.'),
    ('COLOR STABLE-20', f'COLOR STABLE 20. {_TEXTO_COLOR_STABLE}'),
    ('COLOR STABLE-5', f'COLOR STABLE 5. {_TEXTO_COLOR_STABLE}'),
    ('Color Stable IR - 15', _TEXTO_COLOR_STABLE_IR),
    ('Color Stable IR - 35', _TEXTO_COLOR_STABLE_IR),
    ('Color Stable IR - 5', _TEXTO_COLOR_STABLE_IR),
    ('Color Stable IR - 50', _TEXTO_COLOR_STABLE_IR.rstrip('.')),
    ('CRYSTALLINE-40', f'CRYSTALLINE 40. {_TEXTO_CRYSTALLINE}'),
    ('CRYSTALLINE-70', f'CRYSTALLINE 70. {_TEXTO_CRYSTALLINE}'),
    ('FX-HP 15',
     'FX-HP 15. Excelente rendimiento de rechazo de calor con un elegante acabado, bloquea hasta el 99% de la luz '
     'ultravioleta (UV) para brindar protección solar para usted y sus pasajeros. Ofrece un deslumbramiento reducido '
     'de la luz solar para que pueda ver mejor y concentrarse más en la carretera.'),
]

LAMINA_CON_BOBINAS = 'CRYSTALLINE-70'
LARGO_BOBINA = Decimal('20')
BOBINAS = [
    {'ancho': Decimal('0.5'), 'precio': Decimal('440')},
    {'ancho': Decimal('1'), 'precio': Decimal('880')},
]
METROS_INVENTARIO = Decimal('20')
CANTIDAD_INVENTARIO = 1


class _Rollback(Exception):
    """Deshace la transaccion de --dry-run."""


class Command(BaseCommand):
    help = ('Inicializa una BD nueva: grupos, permisos, sucursales, usuarios, instaladores, catalogo, laminas, '
            'bobinas e inventario. Idempotente; ejecutar a mano despues de migrate.')

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Hace el mismo recorrido, informa lo que se crearia y deshace todo.')
        parser.add_argument('--password', default=None,
                            help='Contrasena de los usuarios sembrados; por defecto se lee DEFAULT_PASSWORD.')
        parser.add_argument('--catalogo', default=str(CATALOGO_POR_DEFECTO),
                            help='JSON del catalogo (por defecto product/seed_data/catalogo.json).')

    # ------------------------------------------------------------------ utilidades
    def _contar(self, etiqueta, creado):
        self._resumen.setdefault(etiqueta, [0, 0])[0 if creado else 1] += 1

    def _linea(self, texto):
        self.stdout.write(texto)

    def _resolver_password(self, options):
        explicita = options['password']
        password = explicita if explicita is not None else os.environ.get('DEFAULT_PASSWORD')
        if not password:
            if options['dry_run']:
                self.stdout.write(self.style.WARNING(
                    'DEFAULT_PASSWORD no esta definida (ni --password): un despliegue real fallaria aqui.'))
                return None, False
            raise CommandError(
                'Falta la contrasena de los usuarios del seed: defina DEFAULT_PASSWORD en praxsa_manager/.env '
                '(o pase --password). No se creo ningun dato.')
        try:
            validate_password(password)
        except ValidationError as e:
            raise CommandError(
                f'La contrasena no cumple las reglas de Django: {" ".join(e.messages)} No se creo ningun dato.')
        return password, explicita is not None

    def _cargar_catalogo(self, ruta):
        ruta = Path(ruta)
        if not ruta.is_file():
            raise CommandError(f'No existe el catalogo {ruta}. Genérelo con exportar_catalogo_seed.')
        try:
            data = json.loads(ruta.read_text(encoding='utf-8'))
            for clave in ('marcas', 'modelos', 'items', 'modelo_items'):
                data[clave]
        except (ValueError, KeyError, TypeError) as e:
            raise CommandError(f'Catalogo invalido ({ruta}): {e!r}')
        return data

    # ------------------------------------------------------------------ pasos
    def _grupos(self):
        for nombre in GRUPOS:
            grupo = Group.objects.filter(name__iexact=nombre).order_by('name').first()
            if grupo is None:
                Group.objects.create(name=nombre)
            self._contar('grupos', grupo is None)

    def _permisos(self):
        for comando in COMANDOS_PERMISOS:
            call_command(comando, stdout=self.stdout)

    def _sucursales(self):
        for datos in SUCURSALES:
            sucursal = Sucursal.objects.filter(name=datos['name']).first()
            if sucursal is None:
                Sucursal.objects.create(enable_to_install_windows_film=True, **datos)
            self._contar('sucursales', sucursal is None)

    def _usuarios(self, password, password_explicita):
        grupo = Group.objects.filter(name__iexact=GRUPO_USUARIOS).order_by('name').first()
        for datos in USUARIOS:
            user = User.objects.filter(username=datos['username']).first()
            creado = user is None
            if creado:
                user = User(username=datos['username'], is_staff=True, is_active=True,
                            is_superuser=datos['superuser'])
                if password is not None:
                    user.set_password(password)
                else:
                    user.set_unusable_password()
                user.save()
            elif password_explicita:
                user.set_password(password)
                user.save()
            Profile.objects.get_or_create(user=user)
            user.groups.add(grupo)
            for nombre in datos['sucursales']:
                Sucursal.objects.get(name=nombre).empleado.add(user)
            self._contar('usuarios', creado)

    def _instaladores(self):
        for datos in INSTALADORES:
            sucursal = Sucursal.objects.get(name=datos['sucursal'])
            inst = instalador.objects.filter(name=datos['name']).first()
            creado = inst is None
            if creado:
                inst = instalador.objects.create(name=datos['name'], address=sucursal.address,
                                                 phonenumber=TELEFONO_INSTALADORES, is_active=True)
            inst.sucursal.add(sucursal)
            self._contar('instaladores', creado)

    def _catalogo(self, data):
        marcas = {}
        for m in data['marcas']:
            marca = Car_Brand.objects.filter(name=m['nombre']).first()
            creado = marca is None
            if creado:
                marca = Car_Brand.objects.create(name=m['nombre'], is_active=m['activo'])
            marcas[m['nombre']] = marca
            self._contar('marcas', creado)
        modelos = {}
        for m in data['modelos']:
            modelo = Car_Model.objects.filter(name=m['nombre']).first()
            creado = modelo is None
            if creado:
                modelo = Car_Model.objects.create(
                    name=m['nombre'], car_brand_id=marcas[m['marca']], is_active=m['activo'])
            modelos[m['nombre']] = modelo
            self._contar('modelos', creado)
        items = {}
        for i in data['items']:
            item = Car_Part.objects.filter(name=i['nombre']).order_by('id').first()
            creado = item is None
            if creado:
                item = Car_Part.objects.create(name=i['nombre'], is_active=i['activo'])
            items[i['nombre']] = item
            self._contar('items', creado)
        for r in data['modelo_items']:
            modelo, item = modelos[r['modelo']], items[r['item']]
            existe = Car_Model_Part.objects.filter(car_model_id=modelo, car_part_id=item).exists()
            if not existe:
                Car_Model_Part.objects.create(
                    car_model_id=modelo, car_part_id=item, width=Decimal(r['ancho']), length=Decimal(r['largo']),
                    quantity=r['cantidad'], installation_price=Decimal(r['precio_instalacion']))
            self._contar('modelo-item', not existe)

    def _laminas(self):
        for nombre, descripcion in LAMINAS:
            lamina = Window_Film.objects.filter(name=nombre).order_by('id').first()
            if lamina is None:
                Window_Film.objects.create(name=nombre, description=descripcion, is_active=True)
            self._contar('laminas', lamina is None)

    def _bobinas_e_inventario(self):
        lamina = Window_Film.objects.filter(name=LAMINA_CON_BOBINAS).order_by('id').first()
        ahora = datetime.now()
        for datos in BOBINAS:
            bobina = Window_Film_Reel.objects.filter(window_film=lamina, width=datos['ancho']).order_by('id').first()
            creada = bobina is None
            if creada:
                bobina = Window_Film_Reel.objects.create(
                    window_film=lamina, width=datos['ancho'], length=LARGO_BOBINA, price=datos['precio'],
                    is_active=True)
            self._contar('bobinas', creada)
            for sucursal in Sucursal.objects.filter(name__in=[s['name'] for s in SUCURSALES]).order_by('name'):
                fila = inventario.objects.filter(sucursal=sucursal, bobina=bobina).first()
                if fila is None:
                    inventario.objects.create(
                        sucursal=sucursal, bobina=bobina, quantity=CANTIDAD_INVENTARIO,
                        to_install=METROS_INVENTARIO, original_length=METROS_INVENTARIO, date=ahora)
                self._contar('inventario', fila is None)

    # ------------------------------------------------------------------ main
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        password, password_explicita = self._resolver_password(options)
        catalogo = self._cargar_catalogo(options['catalogo'])
        self._resumen = {}
        try:
            with transaction.atomic():
                self._grupos()
                self._permisos()
                self._sucursales()
                self._usuarios(password, password_explicita)
                self._instaladores()
                try:
                    self._catalogo(catalogo)
                except KeyError as e:
                    raise CommandError(f'Catalogo inconsistente: falta la referencia {e}. No se guardo nada.')
                self._laminas()
                self._bobinas_e_inventario()
                if dry_run:
                    raise _Rollback()
        except _Rollback:
            pass
        titulo = 'DRY-RUN (no se guardo nada): se crearian' if dry_run else 'Inicializacion completa. Creados'
        self._linea(f'{titulo} / ya existian:')
        for etiqueta, (creados, existentes) in self._resumen.items():
            self._linea(f'  {etiqueta}: {creados} / {existentes}')
