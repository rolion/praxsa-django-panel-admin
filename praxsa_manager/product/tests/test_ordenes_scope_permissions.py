"""Tests de alcance por sucursal, permisos y catalogos del modulo Ordenes
(TASK-modulo-ordenes-proforma-nota-trabajo). Ver
ADR-modulo-ordenes-proforma-nota-trabajo-alcance-permisos."""
import json
from decimal import Decimal

from django.test import TestCase

from ..models import Nota_trabajo
from . import helpers
from .ordenes_helpers import auth, instalacion_payload, make_scenario, make_staff, metro_lineal_payload

PROFORMAS = '/product/ordenes/proformas'
NOTAS = '/product/ordenes/notas-trabajo'


def _create(client, s, payload_fn=instalacion_payload):
    return client.post(
        PROFORMAS, payload_fn(s), content_type='application/json', **auth(s['token'])
    ).json()['id']


class ScopeTest(TestCase):
    def setUp(self):
        self.a = make_scenario()
        self.b = make_scenario()
        self.proforma_a = _create(self.client, self.a)
        self.proforma_b = _create(self.client, self.b)
        self.client.post(f'{PROFORMAS}/{self.proforma_b}/generar-nota-trabajo/', **auth(self.b['token']))
        self.nota_b = Nota_trabajo.objects.get(proforma_id=self.proforma_b)

    def test_employee_only_sees_own_sucursal(self):
        ids = [r['id'] for r in self.client.get(PROFORMAS, **auth(self.a['token'])).json()]
        self.assertEqual(ids, [self.proforma_a])
        self.assertEqual(self.client.get(NOTAS, **auth(self.a['token'])).json(), [])

    def test_foreign_objects_return_404_for_every_operation(self):
        headers = auth(self.a['token'])
        base = f'{PROFORMAS}/{self.proforma_b}'
        self.assertEqual(self.client.get(f'{base}/', **headers).status_code, 404)
        self.assertEqual(
            self.client.patch(f'{base}/', {'name': 'x'}, content_type='application/json', **headers).status_code, 404
        )
        self.assertEqual(self.client.post(f'{base}/generar-nota-trabajo/', **headers).status_code, 404)
        self.assertEqual(self.client.get(f'{base}/pdf/', **headers).status_code, 404)
        self.assertEqual(self.client.get(f'{NOTAS}/{self.nota_b.id}/', **headers).status_code, 404)
        self.assertEqual(
            self.client.patch(
                f'{NOTAS}/{self.nota_b.id}/', {'observaciones': 'x'}, content_type='application/json', **headers
            ).status_code,
            404,
        )

    def test_cannot_create_in_foreign_sucursal(self):
        payload = instalacion_payload(self.b)
        response = self.client.post(PROFORMAS, payload, content_type='application/json', **auth(self.a['token']))
        self.assertEqual(response.status_code, 400)
        self.assertIn('sucursal', response.json())

    def test_admin_group_sees_everything_and_can_use_any_sucursal(self):
        admin, token = make_staff(group='admin')
        headers = auth(token)
        ids = sorted(r['id'] for r in self.client.get(PROFORMAS, **headers).json())
        self.assertEqual(ids, sorted([self.proforma_a, self.proforma_b]))
        self.assertEqual(len(self.client.get(NOTAS, **headers).json()), 1)
        response = self.client.post(
            PROFORMAS, metro_lineal_payload(self.b), content_type='application/json', **headers
        )
        self.assertEqual(response.status_code, 201, response.content)

    def test_admin_group_match_is_case_insensitive(self):
        _, token = make_staff(group='Admin')
        self.assertEqual(len(self.client.get(PROFORMAS, **auth(token)).json()), 2)

    def test_user_with_two_sucursales_sees_both(self):
        user = self.a['user']
        self.b['sucursal'].empleado.add(user)
        ids = sorted(r['id'] for r in self.client.get(PROFORMAS, **auth(self.a['token'])).json())
        self.assertEqual(ids, sorted([self.proforma_a, self.proforma_b]))

    def test_user_without_sucursal_sees_nothing(self):
        user, token = make_staff()
        self.assertEqual(self.client.get(PROFORMAS, **auth(token)).json(), [])
        self.assertEqual(self.client.get(NOTAS, **auth(token)).json(), [])
        self.assertEqual(self.client.get('/product/ordenes/catalogo/sucursales', **auth(token)).json(), [])

    def test_disabled_sucursal_is_out_of_scope(self):
        self.a['sucursal'].enable_to_install_windows_film = False
        self.a['sucursal'].save()
        self.assertEqual(self.client.get(PROFORMAS, **auth(self.a['token'])).json(), [])


class PermissionsTest(TestCase):
    def setUp(self):
        self.s = make_scenario()
        self.proforma = _create(self.client, self.s)

    def test_anonymous_and_non_staff_are_rejected(self):
        self.assertEqual(self.client.get(PROFORMAS).status_code, 401)
        user, token, _ = helpers.create_staff_user_with_token(is_staff=False)
        for url in (PROFORMAS, NOTAS, '/product/ordenes/catalogo/sucursales',
                    f'{PROFORMAS}/{self.proforma}/', f'{PROFORMAS}/{self.proforma}/pdf/'):
            self.assertEqual(self.client.get(url, **auth(token)).status_code, 403, url)
        self.assertEqual(self.client.post(f'{PROFORMAS}/{self.proforma}/generar-nota-trabajo/', **auth(token)).status_code, 403)

    def test_read_needs_only_staff_but_write_needs_model_permissions(self):
        user, token = make_staff(permissions=())
        self.s['sucursal'].empleado.add(user)
        headers = auth(token)
        self.assertEqual(self.client.get(PROFORMAS, **headers).status_code, 200)
        self.assertEqual(
            self.client.post(PROFORMAS, instalacion_payload(self.s), content_type='application/json', **headers).status_code,
            403,
        )
        self.assertEqual(
            self.client.patch(
                f'{PROFORMAS}/{self.proforma}/', {'name': 'x'}, content_type='application/json', **headers
            ).status_code,
            403,
        )
        self.assertEqual(self.client.post(f'{PROFORMAS}/{self.proforma}/generar-nota-trabajo/', **headers).status_code, 403)

    def test_each_write_permission_is_enforced_independently(self):
        only_add, token = make_staff(permissions=('add_proforma_header',))
        self.s['sucursal'].empleado.add(only_add)
        headers = auth(token)
        self.assertEqual(
            self.client.post(PROFORMAS, metro_lineal_payload(self.s), content_type='application/json', **headers).status_code,
            201,
        )
        self.assertEqual(
            self.client.patch(
                f'{PROFORMAS}/{self.proforma}/', {'name': 'x'}, content_type='application/json', **headers
            ).status_code,
            403,
        )


class CatalogTest(TestCase):
    def setUp(self):
        self.s = make_scenario()
        self.headers = auth(self.s['token'])

    def test_sucursales_catalog(self):
        rows = self.client.get('/product/ordenes/catalogo/sucursales', **self.headers).json()
        self.assertEqual([r['id'] for r in rows], [self.s['sucursal'].id])

    def test_bobinas_catalog_has_meters_and_resolved_price(self):
        helpers.create_precio_venta_sucursal(
            self.s['sucursal'], self.s['film'], width=Decimal('1.50'), precio_venta=Decimal('150.00')
        )
        response = self.client.get(
            '/product/ordenes/catalogo/bobinas', {'sucursal': self.s['sucursal'].id}, **self.headers
        )

        self.assertEqual(response.status_code, 200)
        rows = response.json()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['window_film'], self.s['film'].id)
        # Strings con 2 decimales (no floats): mismo formato que las lineas de proforma,
        # porque el frontend arma la clave de bobina con el ancho (REV-...-02).
        self.assertEqual(rows[0]['width'], '1.50')
        self.assertEqual(rows[0]['available_meters'], '50.00')
        self.assertEqual(rows[0]['unit_price'], '150.00')
        self.assertIsInstance(rows[0]['width'], str)
        self.assertIsInstance(rows[0]['unit_price'], str)

    def test_bobinas_catalog_width_matches_the_saved_line_width_format(self):
        created = self.client.post(
            '/product/ordenes/proformas',
            {
                'sales_type': 'venta_metro_lineal', 'sucursal': self.s['sucursal'].id, 'name': 'Ana',
                'email': 'a@test.com', 'ci_nit': '1', 'phone_number': '70000001', 'discount': '0',
                'items': [{'window_film': self.s['film'].id, 'width': '1.50', 'length': '2'}],
            },
            content_type='application/json', **self.headers,
        ).json()
        catalog = self.client.get(
            '/product/ordenes/catalogo/bobinas', {'sucursal': self.s['sucursal'].id}, **self.headers
        ).json()

        self.assertEqual(catalog[0]['width'], created['items'][0]['width'])

    def test_bobinas_catalog_excludes_inactive_and_empty_stock(self):
        self.s['inventario'].to_install = Decimal('0')
        self.s['inventario'].save()
        url = '/product/ordenes/catalogo/bobinas'
        self.assertEqual(self.client.get(url, {'sucursal': self.s['sucursal'].id}, **self.headers).json(), [])

        self.s['inventario'].to_install = Decimal('10')
        self.s['inventario'].save()
        self.s['film'].is_active = False
        self.s['film'].save()
        self.assertEqual(self.client.get(url, {'sucursal': self.s['sucursal'].id}, **self.headers).json(), [])

    def test_bobinas_and_instaladores_require_a_sucursal_in_scope(self):
        other = make_scenario()
        for url in ('/product/ordenes/catalogo/bobinas', '/product/ordenes/catalogo/instaladores'):
            self.assertEqual(self.client.get(url, **self.headers).status_code, 404)
            self.assertEqual(self.client.get(url, {'sucursal': 'abc'}, **self.headers).status_code, 404)
            self.assertEqual(self.client.get(url, {'sucursal': other['sucursal'].id}, **self.headers).status_code, 404)

    def test_instaladores_catalog(self):
        from ..models import instalador
        inst = instalador.objects.create(name='Instalador Uno', address='x', phonenumber='70000002')
        inst.sucursal.add(self.s['sucursal'])
        rows = self.client.get(
            '/product/ordenes/catalogo/instaladores', {'sucursal': self.s['sucursal'].id}, **self.headers
        ).json()
        self.assertEqual(rows, [{'id': inst.id, 'name': 'Instalador Uno'}])


class LoginPermissionsTest(TestCase):
    def _login(self, username, password):
        return self.client.post(
            '/product/api-panel-admin-token-auth/',
            data=json.dumps({'username': username, 'password': password}),
            content_type='application/json',
        )

    def test_login_returns_effective_permissions(self):
        user, password = helpers.create_staff_user()
        helpers.grant_permission(user, 'product', 'add_proforma_header')
        group = helpers.add_user_to_group(user, 'admin')
        from django.contrib.auth.models import Permission
        group.permissions.add(Permission.objects.get(content_type__app_label='product', codename='add_nota_trabajo'))

        data = self._login(user.username, password).json()

        self.assertIn('product.add_proforma_header', data['permissions'])
        self.assertIn('product.add_nota_trabajo', data['permissions'])
        self.assertNotIn('product.change_proforma_header', data['permissions'])
        self.assertEqual(data['groups'], ['admin'])
        self.assertTrue(data['is_staff'])

    def test_login_permissions_for_user_without_any_and_for_superuser(self):
        user, password = helpers.create_staff_user()
        self.assertEqual(self._login(user.username, password).json()['permissions'], [])

        from django.contrib.auth.models import User
        superuser = User.objects.create_superuser('root@test.com', 'root@test.com', 'testpass123')
        permissions = self._login(superuser.username, 'testpass123').json()['permissions']
        self.assertIn('product.add_nota_trabajo', permissions)
