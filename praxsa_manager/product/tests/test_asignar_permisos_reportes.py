"""Comando asignar_permisos_reportes (TASK-reportes-utilidad-ventas-diarias)."""
from io import StringIO

from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from ..management.commands.asignar_permisos_reportes import PERMISOS_POR_GRUPO


def _codenames(group):
    return set(group.permissions.values_list('codename', flat=True))


class AsignarPermisosReportesTest(TestCase):

    def crear_grupos(self, nombres=None):
        for nombre in nombres or PERMISOS_POR_GRUPO:
            Group.objects.get_or_create(name=nombre)

    def correr(self, *args):
        out = StringIO()
        call_command('asignar_permisos_reportes', *args, stdout=out)
        return out.getvalue()

    def test_admin_recibe_ambos_reportes_y_caja_solo_ventas_diarias(self):
        self.crear_grupos()
        self.correr()
        self.assertEqual(_codenames(Group.objects.get(name='Admin')), {'view_proxy_pagos', 'view_utilidades'})
        caja = _codenames(Group.objects.get(name='Caja'))
        self.assertEqual(caja, {'view_proxy_pagos'})
        self.assertNotIn('view_utilidades', caja)

    def test_es_idempotente(self):
        self.crear_grupos()
        self.correr()
        antes = {g.name: _codenames(g) for g in Group.objects.all()}
        salida = self.correr()
        self.assertEqual(antes, {g.name: _codenames(g) for g in Group.objects.all()})
        self.assertIn('agregados 0', salida)

    def test_no_quita_permisos_existentes(self):
        self.crear_grupos()
        caja = Group.objects.get(name='Caja')
        caja.permissions.add(Permission.objects.get(content_type__app_label='product', codename='add_pago'))
        self.correr()
        self.assertIn('add_pago', _codenames(caja))

    def test_dry_run_no_escribe(self):
        self.crear_grupos()
        salida = self.correr('--dry-run')
        self.assertIn('se agregarían', salida)
        self.assertEqual(_codenames(Group.objects.get(name='Caja')), set())

    def test_grupo_inexistente_falla_sin_cambios_parciales(self):
        self.crear_grupos(['Admin'])
        with self.assertRaises(CommandError) as ctx:
            self.correr()
        self.assertIn('Caja', str(ctx.exception))
        self.assertEqual(_codenames(Group.objects.get(name='Admin')), set())

    def test_no_distingue_mayusculas_y_aplica_a_todos_los_grupos_que_coinciden(self):
        Group.objects.create(name='Admin')
        Group.objects.create(name='admin')
        Group.objects.create(name='caja')
        self.correr()
        for nombre in ('Admin', 'admin'):
            self.assertEqual(_codenames(Group.objects.get(name=nombre)), {'view_proxy_pagos', 'view_utilidades'})
        self.assertEqual(_codenames(Group.objects.get(name='caja')), {'view_proxy_pagos'})

    def test_los_permisos_de_los_proxies_existen(self):
        """Verifica la hipotesis del ADR: los codenames de los modelos proxy."""
        codenames = set(Permission.objects.filter(content_type__app_label='product').values_list('codename', flat=True))
        self.assertLessEqual({'view_proxy_pagos', 'view_utilidades'}, codenames)
