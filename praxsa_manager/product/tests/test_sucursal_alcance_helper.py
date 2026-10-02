"""Alcance de lectura y de escritura por sucursal en User_Helper (ADR-inventario-
alcance-sucursal-django-admin-alcance-lectura-escritura, decisiones 1, 2 y 4):
lectura = sucursales asignadas (activas o no); escritura = asignadas y activas;
solo el superusuario ve todo; el grupo admin no tiene excepcion."""
from django.test import TestCase

from ..helper.user import User_Helper
from ..utils.exception.sucursal import SucursalInactiva
from . import helpers


def _desactivar(sucursal):
    sucursal.enable_to_install_windows_film = False
    sucursal.save(update_fields=['enable_to_install_windows_film'])


class AlcanceLecturaEscrituraTest(TestCase):
    helper = User_Helper()

    def setUp(self):
        self.user, _ = helpers.create_user_with_token()
        self.activa = helpers.create_sucursal(self.user)
        self.inactiva = helpers.create_sucursal(self.user)
        _desactivar(self.inactiva)
        self.ajena = helpers.create_sucursal(helpers.create_user_with_token()[0])

    def test_lectura_incluye_asignadas_activas_e_inactivas_y_no_las_ajenas(self):
        self.assertEqual(set(self.helper.get_readable_sucursal_ids(self.user)), {self.activa.id, self.inactiva.id})

    def test_escritura_solo_asignadas_activas(self):
        self.assertEqual(self.helper.get_writable_sucursal_ids(self.user), [self.activa.id])
        self.assertTrue(self.helper.is_sucursal_writable(self.user, self.activa.id))
        self.assertFalse(self.helper.is_sucursal_writable(self.user, self.inactiva.id))
        self.assertFalse(self.helper.is_sucursal_writable(self.user, self.ajena.id))

    def test_require_sucursal_writable_lanza_409_en_inactiva_y_ajena(self):
        self.helper.require_sucursal_writable(self.user, self.activa.id)
        for sucursal in (self.inactiva, self.ajena):
            with self.assertRaises(SucursalInactiva) as ctx:
                self.helper.require_sucursal_writable(self.user, sucursal.id)
            self.assertEqual(ctx.exception.status_code, 409)

    def test_grupo_admin_no_tiene_excepcion(self):
        helpers.add_user_to_group(self.user, 'Admin')
        self.assertFalse(self.helper.can_view_all_sucursales(self.user))
        self.assertEqual(set(self.helper.get_readable_sucursal_ids(self.user)), {self.activa.id, self.inactiva.id})
        self.assertEqual(self.helper.get_writable_sucursal_ids(self.user), [self.activa.id])

    def test_admin_sin_sucursales_no_ve_ni_escribe_nada(self):
        admin, _ = helpers.create_user_with_token()
        helpers.add_user_to_group(admin, 'admin')
        self.assertEqual(self.helper.get_readable_sucursal_ids(admin), [])
        self.assertEqual(self.helper.get_writable_sucursal_ids(admin), [])
        self.assertFalse(self.helper.has_assigned_sucursal(admin))

    def test_superusuario_lee_todas_pero_escribe_solo_en_activas(self):
        superuser, _, _ = helpers.create_superuser_with_token()
        self.assertTrue(self.helper.can_view_all_sucursales(superuser))
        self.assertEqual(
            set(self.helper.get_readable_sucursal_ids(superuser)), {self.activa.id, self.inactiva.id, self.ajena.id})
        self.assertEqual(set(self.helper.get_writable_sucursal_ids(superuser)), {self.activa.id, self.ajena.id})
        with self.assertRaises(SucursalInactiva):
            self.helper.require_sucursal_writable(superuser, self.inactiva.id)

    def test_has_assigned_sucursal_cuenta_las_inactivas(self):
        solo_inactiva, _ = helpers.create_user_with_token()
        _desactivar(helpers.create_sucursal(solo_inactiva))
        self.assertTrue(self.helper.has_assigned_sucursal(solo_inactiva))
        self.assertEqual(self.helper.get_writable_sucursal_ids(solo_inactiva), [])

    def test_los_metodos_antiguos_ya_no_existen(self):
        # Evita que un llamador nuevo use el concepto ambiguo "en alcance".
        self.assertFalse(hasattr(self.helper, 'get_sucursales_in_scope'))
        self.assertFalse(hasattr(self.helper, 'get_enabled_sucursal_ids'))
