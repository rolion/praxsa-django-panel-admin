"""Tests de alcance por sucursal y filtros de Inventario (TASK-almacen-permisos-
sucursal-filtros). Ver ADR-almacen-permisos-sucursal-filtros-alcance-inventario:
el usuario solo ve/agrega/edita inventario de sus sucursales habilitadas
(admin: todas), y el listado se filtra por ?sucursal= y ?window_film=.
"""
from decimal import Decimal

from django.test import TestCase

from ..models import inventario
from . import helpers

INVENTARIO_URL = '/product/almacen/inventario'


def _auth(token):
    return {'HTTP_AUTHORIZATION': f'Token {token.key}'}


def _payload(sucursal, reel, **overrides):
    data = {
        'sucursal': sucursal.id, 'bobina': reel.id, 'quantity': 1,
        'to_install': '10.00', 'precio_compra_mtr_lineal': '80.00',
        'precio_venta_mtr_lineal': '120.00', 'nro_lote': 'L001',
    }
    data.update(overrides)
    return data


class _AlcanceBase(TestCase):
    def setUp(self):
        self.user, self.token, _ = helpers.create_staff_user_with_token()
        self.sucursal_a = helpers.create_sucursal(self.user)
        self.sucursal_b = helpers.create_sucursal(self.user)
        other_user, _ = helpers.create_user_with_token()
        self.sucursal_c = helpers.create_sucursal(other_user)  # ajena al usuario
        self.film_1 = helpers.create_window_film(name='Carbon 20%')
        self.film_2 = helpers.create_window_film(name='Ceramico 30%')
        self.reel_1 = helpers.create_window_film_reel(window_film=self.film_1)
        self.reel_2 = helpers.create_window_film_reel(window_film=self.film_2)
        self.inv_a1 = helpers.create_inventario(sucursal=self.sucursal_a, bobina=self.reel_1)
        self.inv_b2 = helpers.create_inventario(sucursal=self.sucursal_b, bobina=self.reel_2)
        self.inv_c1 = helpers.create_inventario(sucursal=self.sucursal_c, bobina=self.reel_1)

    def get_ids(self, query='', token=None):
        response = self.client.get(f'{INVENTARIO_URL}{query}', **_auth(token or self.token))
        self.assertEqual(response.status_code, 200, response.content)
        return {row['id'] for row in response.json()}


class InventarioListAlcanceTest(_AlcanceBase):
    def test_user_sees_all_own_sucursales_and_not_foreign_ones(self):
        self.assertEqual(self.get_ids(), {self.inv_a1.id, self.inv_b2.id})

    def test_admin_sees_every_sucursal(self):
        admin, admin_token, _ = helpers.create_staff_user_with_token()
        helpers.add_user_to_group(admin, 'admin')

        ids = self.get_ids(token=admin_token)

        self.assertTrue({self.inv_a1.id, self.inv_b2.id, self.inv_c1.id} <= ids)

    def test_user_without_sucursal_sees_empty_list(self):
        _, lonely_token, _ = helpers.create_staff_user_with_token()

        self.assertEqual(self.get_ids(token=lonely_token), set())

    def test_disabled_sucursal_is_not_in_scope(self):
        self.sucursal_b.enable_to_install_windows_film = False
        self.sucursal_b.save(update_fields=['enable_to_install_windows_film'])

        self.assertEqual(self.get_ids(), {self.inv_a1.id})

    def test_filter_by_own_sucursal(self):
        self.assertEqual(self.get_ids(f'?sucursal={self.sucursal_a.id}'), {self.inv_a1.id})

    def test_filter_by_foreign_sucursal_returns_nothing(self):
        self.assertEqual(self.get_ids(f'?sucursal={self.sucursal_c.id}'), set())

    def test_filter_by_window_film_stays_inside_scope(self):
        # film_1 tiene inventario en A (propia) y en C (ajena): solo se ve A.
        self.assertEqual(self.get_ids(f'?window_film={self.film_1.id}'), {self.inv_a1.id})

    def test_filters_combine(self):
        query = f'?sucursal={self.sucursal_b.id}&window_film={self.film_1.id}'
        self.assertEqual(self.get_ids(query), set())
        query = f'?sucursal={self.sucursal_b.id}&window_film={self.film_2.id}'
        self.assertEqual(self.get_ids(query), {self.inv_b2.id})

    def test_non_numeric_filters_are_ignored(self):
        self.assertEqual(self.get_ids('?sucursal=abc&window_film=xyz'), {self.inv_a1.id, self.inv_b2.id})

    def test_filters_combine_with_search_and_inactive(self):
        self.inv_a1.is_active = False
        self.inv_a1.save(update_fields=['is_active'])

        self.assertEqual(self.get_ids(f'?window_film={self.film_1.id}'), set())
        self.assertEqual(
            self.get_ids(f'?window_film={self.film_1.id}&include_inactive=true&search=carbon'),
            {self.inv_a1.id},
        )


class InventarioDetalleAlcanceTest(_AlcanceBase):
    def setUp(self):
        super().setUp()
        helpers.grant_permission(self.user, 'product', 'change_inventario')

    def _patch(self, inv, data=None, suffix=''):
        return self.client.patch(
            f'{INVENTARIO_URL}/{inv.id}/{suffix}', data or {'to_install': '25.00'},
            content_type='application/json', **_auth(self.token),
        )

    def test_get_own_row(self):
        response = self.client.get(f'{INVENTARIO_URL}/{self.inv_b2.id}/', **_auth(self.token))
        self.assertEqual(response.status_code, 200)

    def test_get_foreign_row_is_404(self):
        response = self.client.get(f'{INVENTARIO_URL}/{self.inv_c1.id}/', **_auth(self.token))
        self.assertEqual(response.status_code, 404)

    def test_patch_own_row_in_second_sucursal(self):
        response = self._patch(self.inv_b2)
        self.assertEqual(response.status_code, 200, response.content)
        self.inv_b2.refresh_from_db()
        self.assertEqual(self.inv_b2.to_install, Decimal('25.00'))

    def test_patch_foreign_row_is_404_and_does_not_change_it(self):
        response = self._patch(self.inv_c1)
        self.assertEqual(response.status_code, 404)
        self.inv_c1.refresh_from_db()
        self.assertNotEqual(self.inv_c1.to_install, Decimal('25.00'))

    def test_toggle_foreign_row_is_404(self):
        self.inv_c1.to_install = Decimal('0.00')
        self.inv_c1.save(update_fields=['to_install'])

        response = self._patch(self.inv_c1, {'is_active': False}, 'toggle-active/')

        self.assertEqual(response.status_code, 404)
        self.inv_c1.refresh_from_db()
        self.assertTrue(self.inv_c1.is_active)

    def test_toggle_own_row(self):
        self.inv_a1.to_install = Decimal('0.00')
        self.inv_a1.save(update_fields=['to_install'])

        response = self._patch(self.inv_a1, {'is_active': False}, 'toggle-active/')

        self.assertEqual(response.status_code, 200, response.content)

    def test_own_row_without_permission_is_forbidden(self):
        _, token, _ = helpers.create_staff_user_with_token()
        sucursal = helpers.create_sucursal(token.user)
        inv = helpers.create_inventario(sucursal=sucursal)

        response = self.client.patch(
            f'{INVENTARIO_URL}/{inv.id}/', {'to_install': '25.00'},
            content_type='application/json', **_auth(token),
        )

        self.assertEqual(response.status_code, 403)

    def test_admin_can_patch_any_row(self):
        admin, admin_token, _ = helpers.create_staff_user_with_token()
        helpers.add_user_to_group(admin, 'admin')
        helpers.grant_permission(admin, 'product', 'change_inventario')

        response = self.client.patch(
            f'{INVENTARIO_URL}/{self.inv_c1.id}/', {'to_install': '25.00'},
            content_type='application/json', **_auth(admin_token),
        )

        self.assertEqual(response.status_code, 200, response.content)


class InventarioCreateAlcanceTest(_AlcanceBase):
    def setUp(self):
        super().setUp()
        helpers.grant_permission(self.user, 'product', 'add_inventario')

    def _post(self, sucursal, token=None):
        return self.client.post(
            INVENTARIO_URL, _payload(sucursal, self.reel_1),
            content_type='application/json', **_auth(token or self.token),
        )

    def test_create_in_each_own_sucursal(self):
        self.assertEqual(self._post(self.sucursal_a).status_code, 201)
        self.assertEqual(self._post(self.sucursal_b).status_code, 201)

    def test_create_in_foreign_sucursal_is_400_on_sucursal(self):
        before = inventario.objects.count()

        response = self._post(self.sucursal_c)

        self.assertEqual(response.status_code, 400)
        self.assertIn('sucursal', response.json())
        self.assertEqual(inventario.objects.count(), before)

    def test_create_in_disabled_sucursal_is_400(self):
        self.sucursal_a.enable_to_install_windows_film = False
        self.sucursal_a.save(update_fields=['enable_to_install_windows_film'])

        response = self._post(self.sucursal_a)

        self.assertEqual(response.status_code, 400)
        self.assertIn('sucursal', response.json())

    def test_admin_cannot_create_in_disabled_sucursal(self):
        admin, admin_token, _ = helpers.create_staff_user_with_token()
        helpers.add_user_to_group(admin, 'admin')
        helpers.grant_permission(admin, 'product', 'add_inventario')
        self.sucursal_c.enable_to_install_windows_film = False
        self.sucursal_c.save(update_fields=['enable_to_install_windows_film'])

        response = self._post(self.sucursal_c, admin_token)

        self.assertEqual(response.status_code, 400)

    def test_admin_can_create_in_any_enabled_sucursal(self):
        admin, admin_token, _ = helpers.create_staff_user_with_token()
        helpers.add_user_to_group(admin, 'admin')
        helpers.grant_permission(admin, 'product', 'add_inventario')

        self.assertEqual(self._post(self.sucursal_c, admin_token).status_code, 201)

    def test_create_without_permission_is_forbidden_even_in_own_sucursal(self):
        _, token, _ = helpers.create_staff_user_with_token()
        sucursal = helpers.create_sucursal(token.user)

        response = self._post(sucursal, token)

        self.assertEqual(response.status_code, 403)


class AlmacenSucursalesViewTest(_AlcanceBase):
    URL = '/product/almacen/sucursales'

    def _names(self, token):
        response = self.client.get(self.URL, **_auth(token))
        self.assertEqual(response.status_code, 200, response.content)
        return {row['id'] for row in response.json()}

    def test_user_gets_only_own_enabled_sucursales(self):
        self.assertEqual(self._names(self.token), {self.sucursal_a.id, self.sucursal_b.id})

    def test_disabled_sucursal_is_excluded(self):
        self.sucursal_b.enable_to_install_windows_film = False
        self.sucursal_b.save(update_fields=['enable_to_install_windows_film'])

        self.assertEqual(self._names(self.token), {self.sucursal_a.id})

    def test_admin_gets_every_enabled_sucursal(self):
        admin, admin_token, _ = helpers.create_staff_user_with_token()
        helpers.add_user_to_group(admin, 'admin')

        self.assertTrue({self.sucursal_a.id, self.sucursal_b.id, self.sucursal_c.id} <= self._names(admin_token))

    def test_response_shape(self):
        response = self.client.get(self.URL, **_auth(self.token))
        self.assertEqual(set(response.json()[0].keys()), {'id', 'name'})

    def test_non_staff_is_forbidden(self):
        _, token, _ = helpers.create_staff_user_with_token(is_staff=False)
        response = self.client.get(self.URL, **_auth(token))
        self.assertEqual(response.status_code, 403)

    def test_anonymous_is_rejected(self):
        self.assertEqual(self.client.get(self.URL).status_code, 401)
