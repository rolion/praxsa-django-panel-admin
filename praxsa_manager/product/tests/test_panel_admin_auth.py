"""Tests del login dedicado de panel_admin/ (TASK-login-panel-admin-backend):
no depende de Client y no filtra por rol/is_staff."""
import json

from django.contrib.auth.models import User
from django.test import TestCase

from . import helpers


class PanelAdminAuthTokenTest(TestCase):
    def _post(self, username, password):
        return self.client.post(
            '/product/api-panel-admin-token-auth/',
            data=json.dumps({'username': username, 'password': password}),
            content_type='application/json',
        )

    def test_login_without_client_returns_200_and_expected_shape(self):
        password = 'testpass123'
        user, _token = helpers.create_user_with_token(password=password)
        user.first_name = 'Ana'
        user.last_name = 'Gomez'
        user.save()

        response = self._post(user.username, password)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('token', data)
        self.assertEqual(data['user_id'], user.pk)
        self.assertEqual(data['username'], user.username)
        self.assertEqual(data['name'], 'Ana')
        self.assertEqual(data['lastname'], 'Gomez')

    def test_login_with_staff_user_without_client_returns_200(self):
        user, password = helpers.create_staff_user()

        response = self._post(user.username, password)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('token', data)
        self.assertEqual(data['user_id'], user.pk)

    def test_login_response_includes_is_staff_and_groups(self):
        """TASK-modulo-almacen: el frontend necesita saber el rol del
        usuario logueado para diferenciar admin/almacen -- ver
        ADR-modulo-almacen-permisos-rol-frontend."""
        user, password = helpers.create_staff_user()
        helpers.add_user_to_group(user, 'almacen')

        response = self._post(user.username, password)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['is_staff'])
        self.assertEqual(data['groups'], ['almacen'])

    def test_login_response_groups_empty_for_user_without_groups(self):
        password = 'testpass123'
        user, _token = helpers.create_user_with_token(password=password)

        response = self._post(user.username, password)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['groups'], [])

    def test_login_with_wrong_password_returns_400(self):
        user, _token = helpers.create_user_with_token(password='testpass123')

        response = self._post(user.username, 'contraseña-incorrecta')

        self.assertEqual(response.status_code, 400)
        self.assertIn('non_field_errors', response.json())

    def test_login_with_nonexistent_user_returns_400(self):
        response = self._post('no-existe@test.com', 'cualquiera')

        self.assertEqual(response.status_code, 400)
        self.assertIn('non_field_errors', response.json())
