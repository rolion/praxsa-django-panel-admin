"""Comando inicializar_datos (TASK-despliegue-nuevo-servidor-inicializacion-db)."""
import json
import os
import shutil
import tempfile
from decimal import Decimal
from io import StringIO
from pathlib import Path
from unittest import mock

from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from ..models import (
    Car_Brand, Car_Model, Car_Model_Part, Car_Part, Profile, Sucursal, Window_Film, Window_Film_Reel,
    instalador, inventario,
)

PASSWORD = 'ClaveSegura#2026x'


def _sin_password():
    env = {k: v for k, v in os.environ.items() if k != 'DEFAULT_PASSWORD'}
    return mock.patch.dict(os.environ, env, clear=True)


def _con_password(valor=PASSWORD):
    return mock.patch.dict(os.environ, {'DEFAULT_PASSWORD': valor})


def _conteos():
    return {
        'grupos': Group.objects.count(), 'usuarios': User.objects.count(), 'sucursales': Sucursal.objects.count(),
        'instaladores': instalador.objects.count(), 'marcas': Car_Brand.objects.count(),
        'modelos': Car_Model.objects.count(), 'items': Car_Part.objects.count(),
        'modelo_items': Car_Model_Part.objects.count(), 'laminas': Window_Film.objects.count(),
        'bobinas': Window_Film_Reel.objects.count(), 'inventario': inventario.objects.count(),
        'perfiles': Profile.objects.count(),
    }


class InicializarDatosBase(TestCase):
    """Usa un catalogo pequeno de prueba salvo en las pruebas del catalogo real."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dir = tempfile.mkdtemp()
        cls.catalogo = Path(cls.dir) / 'catalogo.json'
        cls.catalogo.write_text(json.dumps({
            'marcas': [{'nombre': 'CHERY', 'activo': True}, {'nombre': 'Audi', 'activo': True}],
            'modelos': [{'marca': 'CHERY', 'nombre': 'QQ', 'activo': True},
                        {'marca': 'Audi', 'nombre': 'A1', 'activo': False}],
            'items': [{'nombre': 'Parabrisas', 'activo': True}, {'nombre': 'Luneta', 'activo': True}],
            'modelo_items': [{'modelo': 'QQ', 'item': 'Parabrisas', 'ancho': '0.70', 'largo': '1.00',
                              'cantidad': 2, 'precio_instalacion': '50.00'}],
        }), encoding='utf-8')

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(cls.dir, ignore_errors=True)

    def correr(self, *args, password=PASSWORD, catalogo=None):
        out = StringIO()
        args = list(args) + ['--catalogo', str(catalogo or self.catalogo)]
        if password is None:
            with _sin_password():
                call_command('inicializar_datos', *args, stdout=out)
        else:
            with _con_password(password):
                call_command('inicializar_datos', *args, stdout=out)
        return out.getvalue()


class InicializarDatosCreacionTest(InicializarDatosBase):

    def test_crea_todos_los_datos_del_pedido(self):
        self.correr()
        self.assertEqual(set(Group.objects.values_list('name', flat=True)), {'Admin', 'Almacen', 'Caja', 'Vendedor'})
        sc = Sucursal.objects.get(name='Santa Cruz')
        lp = Sucursal.objects.get(name='La Paz')
        self.assertEqual((sc.address, sc.phone_number), ('Av. Ovidio Barbery entre 4to. y 5to anillo', '3352139'))
        self.assertEqual((lp.address, lp.phone_number), ('Calle Angel Pacheco - Obrajes', '78512440'))

        sa, a1, a2 = (User.objects.get(username=u) for u in ('superadmin', 'admin1', 'admin2'))
        for u in (sa, a1, a2):
            self.assertTrue(u.is_staff)
            self.assertTrue(u.check_password(PASSWORD))
            self.assertTrue(u.groups.filter(name='Admin').exists())
            self.assertTrue(Profile.objects.filter(user=u).exists())
        self.assertTrue(sa.is_superuser)
        self.assertFalse(a1.is_superuser or a2.is_superuser)
        self.assertEqual(set(sa.sucursal_set.values_list('name', flat=True)), {'Santa Cruz', 'La Paz'})
        self.assertEqual(list(a1.sucursal_set.values_list('name', flat=True)), ['Santa Cruz'])
        self.assertEqual(list(a2.sucursal_set.values_list('name', flat=True)), ['La Paz'])

        i1, i2 = instalador.objects.get(name='instalador 1'), instalador.objects.get(name='instalador 2')
        self.assertEqual(i1.phonenumber, '3554432')
        self.assertEqual(list(i1.sucursal.values_list('name', flat=True)), ['Santa Cruz'])
        self.assertEqual(list(i2.sucursal.values_list('name', flat=True)), ['La Paz'])
        self.assertFalse(User.objects.filter(username__startswith='instalador').exists())

    def test_laminas_bobinas_e_inventario(self):
        self.correr()
        self.assertEqual(Window_Film.objects.count(), 10)
        self.assertEqual(Window_Film.objects.get(name='CA 35').description[:20], 'Las nanopartículas c')
        self.assertTrue(Window_Film.objects.get(name='CRYSTALLINE-70').description.startswith('CRYSTALLINE 70. '))
        lamina = Window_Film.objects.get(name='CRYSTALLINE-70')
        bobinas = {r.width: r for r in Window_Film_Reel.objects.all()}
        self.assertEqual(Window_Film_Reel.objects.count(), 2)
        self.assertEqual({w: (r.price, r.length, r.window_film_id) for w, r in bobinas.items()},
                         {Decimal('0.50'): (Decimal('440.00'), Decimal('20.00'), lamina.id),
                          Decimal('1.00'): (Decimal('880.00'), Decimal('20.00'), lamina.id)})
        self.assertEqual(inventario.objects.count(), 4)
        for fila in inventario.objects.all():
            self.assertEqual((fila.quantity, fila.to_install, fila.original_length),
                             (1, Decimal('20.00'), Decimal('20.00')))
            self.assertIn(fila.sucursal.name, {'Santa Cruz', 'La Paz'})
        self.assertEqual({(f.sucursal.name, f.bobina.width) for f in inventario.objects.all()},
                         {(s, w) for s in ('Santa Cruz', 'La Paz') for w in (Decimal('0.50'), Decimal('1.00'))})

    def test_catalogo_se_carga_por_nombres(self):
        self.correr()
        self.assertEqual((Car_Brand.objects.count(), Car_Model.objects.count(), Car_Part.objects.count()), (2, 2, 2))
        self.assertFalse(Car_Model.objects.get(name='A1').is_active)
        self.assertEqual(Car_Model.objects.get(name='QQ').car_brand_id.name, 'CHERY')
        parte = Car_Model_Part.objects.get()
        self.assertEqual((parte.car_model_id.name, parte.car_part_id.name, parte.width, parte.length,
                          parte.quantity, parte.installation_price),
                         ('QQ', 'Parabrisas', Decimal('0.70'), Decimal('1.00'), 2, Decimal('50.00')))

    def test_el_admin_recibe_los_permisos_de_los_comandos_existentes(self):
        self.correr()
        codenames = set(Group.objects.get(name='Admin').permissions.values_list('codename', flat=True))
        self.assertTrue({'add_instalador', 'add_pago', 'view_utilidades'} <= codenames)

    def test_catalogo_real_versionado(self):
        self.correr(catalogo=Path(__file__).resolve().parents[1] / 'seed_data' / 'catalogo.json')
        self.assertEqual(Car_Brand.objects.count(), 33)
        self.assertEqual(Car_Model.objects.count(), 155)
        self.assertEqual(Car_Part.objects.count(), 9)
        self.assertEqual(Car_Model_Part.objects.count(), 12)


class InicializarDatosIdempotenciaTest(InicializarDatosBase):

    def test_segunda_ejecucion_no_duplica(self):
        self.correr()
        primero = _conteos()
        salida = self.correr()
        self.assertEqual(_conteos(), primero)
        self.assertIn('ya existian', salida)

    def test_no_duplica_un_grupo_existente_con_otras_mayusculas(self):
        Group.objects.create(name='admin')
        self.correr()
        self.assertEqual(Group.objects.filter(name__iexact='admin').count(), 1)
        self.assertTrue(User.objects.get(username='admin1').groups.filter(name='admin').exists())

    def test_usuario_existente_conserva_su_contrasena(self):
        User.objects.create_user('admin1', password='OtraClave#99zz')
        self.correr()
        self.assertTrue(User.objects.get(username='admin1').check_password('OtraClave#99zz'))

    def test_password_explicita_reemplaza_la_de_un_usuario_existente(self):
        User.objects.create_user('admin1', password='OtraClave#99zz')
        self.correr('--password', 'NuevaClave#2026q')
        self.assertTrue(User.objects.get(username='admin1').check_password('NuevaClave#2026q'))
        self.assertTrue(User.objects.get(username='admin2').check_password('NuevaClave#2026q'))

    def test_password_explicita_tiene_precedencia_sobre_la_variable(self):
        self.correr('--password', 'NuevaClave#2026q')
        self.assertTrue(User.objects.get(username='superadmin').check_password('NuevaClave#2026q'))


class InicializarDatosPasswordYErroresTest(InicializarDatosBase):

    def test_sin_password_falla_sin_escribir(self):
        antes = _conteos()
        with self.assertRaisesMessage(CommandError, 'DEFAULT_PASSWORD'):
            self.correr(password=None)
        self.assertEqual(_conteos(), antes)

    def test_password_invalida_falla_sin_escribir(self):
        antes = _conteos()
        with self.assertRaisesMessage(CommandError, 'reglas de Django'):
            self.correr(password='12345678')
        self.assertEqual(_conteos(), antes)

    def test_catalogo_inexistente_falla_sin_escribir(self):
        antes = _conteos()
        with self.assertRaisesMessage(CommandError, 'No existe el catalogo'):
            self.correr(catalogo=Path(self.dir) / 'no-existe.json')
        self.assertEqual(_conteos(), antes)

    def test_catalogo_inconsistente_no_deja_datos_parciales(self):
        malo = Path(self.dir) / 'malo.json'
        malo.write_text(json.dumps({
            'marcas': [], 'modelos': [{'marca': 'NoExiste', 'nombre': 'X', 'activo': True}],
            'items': [], 'modelo_items': []}), encoding='utf-8')
        antes = _conteos()
        with self.assertRaisesMessage(CommandError, 'Catalogo inconsistente'):
            self.correr(catalogo=malo)
        self.assertEqual(_conteos(), antes)

    def test_la_password_no_se_imprime(self):
        self.assertNotIn(PASSWORD, self.correr())


class InicializarDatosDryRunTest(InicializarDatosBase):

    def test_dry_run_no_escribe_nada(self):
        antes = _conteos()
        salida = self.correr('--dry-run')
        self.assertEqual(_conteos(), antes)
        self.assertIn('DRY-RUN', salida)
        self.assertIn('usuarios: 3 / 0', salida)

    def test_dry_run_sin_password_solo_avisa(self):
        antes = _conteos()
        salida = self.correr('--dry-run', password=None)
        self.assertEqual(_conteos(), antes)
        self.assertIn('DEFAULT_PASSWORD no esta definida', salida)
