"""Comando asignar_permisos_estados (plan v2, matriz de permisos por grupo)."""
from io import StringIO

from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from ..management.commands.asignar_permisos_estados import PERMISOS_POR_GRUPO


def _codenames(group):
    return set(group.permissions.values_list('codename', flat=True))


class AsignarPermisosEstadosTest(TestCase):
    def crear_grupos(self, nombres=None):
        for nombre in nombres or PERMISOS_POR_GRUPO:
            Group.objects.get_or_create(name=nombre)

    def correr(self, *args):
        out = StringIO()
        call_command('asignar_permisos_estados', *args, stdout=out)
        return out.getvalue()

    def test_asigna_la_matriz_acordada(self):
        self.crear_grupos()
        self.correr()
        self.assertEqual(_codenames(Group.objects.get(name='Almacen')),
                         {'change_proforma_header', 'change_nota_trabajo', 'delete_nota_trabajo'})
        self.assertEqual(_codenames(Group.objects.get(name='Caja')),
                         {'add_pago', 'delete_pago', 'delete_nota_venta'})
        vendedor = _codenames(Group.objects.get(name='Vendedor'))
        self.assertLessEqual({'add_pago', 'delete_pago', 'add_nota_trabajo', 'delete_proforma_header',
                              'change_proforma_header', 'delete_nota_venta'}, vendedor)
        self.assertNotIn('change_nota_trabajo', vendedor)
        admin = _codenames(Group.objects.get(name='Admin'))
        self.assertLessEqual(set(PERMISOS_POR_GRUPO['Admin']), admin)

    def test_es_idempotente(self):
        self.crear_grupos()
        self.correr()
        antes = {g.name: _codenames(g) for g in Group.objects.all()}
        salida = self.correr()
        despues = {g.name: _codenames(g) for g in Group.objects.all()}
        self.assertEqual(antes, despues)
        self.assertIn('agregados 0', salida)

    def test_no_quita_permisos_existentes(self):
        self.crear_grupos()
        from django.contrib.auth.models import Permission
        extra = Permission.objects.get(content_type__app_label='product', codename='view_sucursal')
        caja = Group.objects.get(name='Caja')
        caja.permissions.add(extra)
        self.correr()
        self.assertIn('view_sucursal', _codenames(caja))

    def test_dry_run_no_escribe(self):
        self.crear_grupos()
        salida = self.correr('--dry-run')
        self.assertIn('se agregarían', salida)
        self.assertEqual(_codenames(Group.objects.get(name='Caja')), set())

    def test_grupo_inexistente_falla_sin_cambios_parciales_y_lista_los_existentes(self):
        self.crear_grupos(['Admin', 'Caja', 'Vendedor'])
        Group.objects.create(name='Almacén')  # con tilde: no coincide con 'Almacen'
        with self.assertRaises(CommandError) as ctx:
            self.correr()
        self.assertIn('Almacen', str(ctx.exception))
        self.assertIn('Almacén', str(ctx.exception))
        self.assertEqual(_codenames(Group.objects.get(name='Admin')), set())
        self.assertEqual(_codenames(Group.objects.get(name='Caja')), set())

    def test_el_nombre_del_grupo_no_distingue_mayusculas(self):
        Group.objects.create(name='admin')
        self.crear_grupos(['Caja', 'Vendedor', 'Almacen'])
        self.correr()
        self.assertLessEqual(set(PERMISOS_POR_GRUPO['Admin']), _codenames(Group.objects.get(name='admin')))
