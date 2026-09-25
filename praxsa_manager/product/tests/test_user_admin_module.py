"""Tests del modulo de Usuarios, Perfiles, Grupos, Roles y Sucursales
(TASK-modulo-usuarios-perfiles-grupos-roles-sucursales). Cubre:
- Creacion atomica de usuario (User+Profile+grupos+sucursales) con sus validaciones.
- Permisos Django (DjangoModelPermissions + IsStaffUser) en los endpoints nuevos.
- Activar/desactivar (bloqueo de auto-desactivacion) y cambio de contraseña.

El login de panel_admin/ (PanelAdminAuthToken, /product/api-panel-admin-token-auth/)
se resolvio en TASK-login-panel-admin-backend (ver test_panel_admin_auth.py) y
deliberadamente no filtra por is_staff a nivel de login -- la barrera real para
este modulo son los permission_classes (IsStaffUser + DjangoModelPermissions) de
cada vista de custom_views/user_admin.py, ejercitados abajo con
create_staff_user_with_token (crea el usuario+token directo por ORM, sin pasar
por ningun endpoint de login).

Ver ADR-modulo-usuarios-perfiles-grupos-roles-sucursales-modelo-datos-permisos y
ADR-modulo-usuarios-perfiles-grupos-roles-sucursales-api-autenticacion-admin.
"""
from django.contrib.auth.models import User
from django.test import TestCase

from ..models import Profile
from . import helpers


class UserCreationTest(TestCase):
    def _auth_headers(self, token):
        return {'HTTP_AUTHORIZATION': f'Token {token.key}'}

    def test_admin_creates_user_with_groups_and_sucursales(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'auth', 'add_user')
        group1 = helpers.add_user_to_group(admin, 'caja')
        sucursal1 = helpers.create_sucursal(admin)
        sucursal2 = helpers.create_sucursal(admin)

        response = self.client.post(
            '/product/users',
            {
                'username': 'nuevo@test.com',
                'password': 'ContraseñaSegura123',
                'password_confirm': 'ContraseñaSegura123',
                'first_name': 'Nuevo',
                'last_name': 'Usuario',
                'email': 'nuevo@test.com',
                'phone_number': '70000001',
                'groups': [group1.id],
                'sucursales': [sucursal1.id, sucursal2.id],
            },
            content_type='application/json',
            **self._auth_headers(token),
        )

        self.assertEqual(response.status_code, 201, response.content)
        created = User.objects.get(username='nuevo@test.com')
        self.assertTrue(created.is_staff)
        self.assertTrue(created.is_active)
        self.assertEqual(Profile.objects.get(user=created).phone_number, '70000001')
        self.assertEqual(list(created.groups.values_list('name', flat=True)), ['caja'])
        self.assertEqual(created.sucursal_set.count(), 2)
        # La contraseña nunca se persiste en texto plano.
        self.assertNotEqual(created.password, 'ContraseñaSegura123')
        self.assertTrue(created.password.startswith('pbkdf2_') or created.check_password('ContraseñaSegura123'))

    def test_user_with_no_groups_and_no_sucursales_is_valid(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'auth', 'add_user')

        response = self.client.post(
            '/product/users',
            {
                'username': 'sinrelaciones@test.com',
                'password': 'ContraseñaSegura123',
                'password_confirm': 'ContraseñaSegura123',
            },
            content_type='application/json',
            **self._auth_headers(token),
        )

        self.assertEqual(response.status_code, 201, response.content)
        created = User.objects.get(username='sinrelaciones@test.com')
        self.assertEqual(created.groups.count(), 0)
        self.assertEqual(created.sucursal_set.count(), 0)
        self.assertTrue(Profile.objects.filter(user=created).exists())

    def test_duplicate_username_returns_400_not_500(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'auth', 'add_user')
        existing, _, _ = helpers.create_staff_user_with_token(username='repetido@test.com')

        response = self.client.post(
            '/product/users',
            {
                'username': 'repetido@test.com',
                'password': 'ContraseñaSegura123',
                'password_confirm': 'ContraseñaSegura123',
            },
            content_type='application/json',
            **self._auth_headers(token),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('username', response.json())

    def test_weak_password_returns_400(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'auth', 'add_user')

        response = self.client.post(
            '/product/users',
            {
                'username': 'passdebil@test.com',
                'password': '123',
                'password_confirm': '123',
            },
            content_type='application/json',
            **self._auth_headers(token),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('password', response.json())

    def test_password_confirmation_mismatch_returns_400(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'auth', 'add_user')

        response = self.client.post(
            '/product/users',
            {
                'username': 'nocoincide@test.com',
                'password': 'ContraseñaSegura123',
                'password_confirm': 'OtraContraseña456',
            },
            content_type='application/json',
            **self._auth_headers(token),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('password_confirm', response.json())

    def test_invalid_sucursal_id_does_not_leave_orphan_user(self):
        """Atomicidad: una sucursal inexistente rechaza la creacion completa,
        sin dejar un User/Profile a medio crear."""
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'auth', 'add_user')

        response = self.client.post(
            '/product/users',
            {
                'username': 'atomico@test.com',
                'password': 'ContraseñaSegura123',
                'password_confirm': 'ContraseñaSegura123',
                'sucursales': [999999],
            },
            content_type='application/json',
            **self._auth_headers(token),
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(username='atomico@test.com').exists())

    def test_create_without_add_user_permission_is_forbidden(self):
        admin, token, _ = helpers.create_staff_user_with_token()

        response = self.client.post(
            '/product/users',
            {
                'username': 'sinpermiso@test.com',
                'password': 'ContraseñaSegura123',
                'password_confirm': 'ContraseñaSegura123',
            },
            content_type='application/json',
            **self._auth_headers(token),
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(username='sinpermiso@test.com').exists())

    def test_non_staff_user_cannot_reach_endpoint(self):
        _, token, _ = helpers.create_staff_user_with_token(is_staff=False)

        response = self.client.get('/product/users', **self._auth_headers(token))

        self.assertEqual(response.status_code, 403)


class UserListTest(TestCase):
    def test_list_hides_inactive_users_by_default(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        active_user, _, _ = helpers.create_staff_user_with_token()
        inactive_user, _, _ = helpers.create_staff_user_with_token()
        inactive_user.is_active = False
        inactive_user.save(update_fields=['is_active'])
        Profile.objects.create(user=active_user)
        Profile.objects.create(user=inactive_user)

        response = self.client.get(
            '/product/users', HTTP_AUTHORIZATION=f'Token {token.key}'
        )

        self.assertEqual(response.status_code, 200)
        usernames = [row['username'] for row in response.json()['results']] if 'results' in response.json() else [row['username'] for row in response.json()]
        self.assertIn(active_user.username, usernames)
        self.assertNotIn(inactive_user.username, usernames)

    def test_list_include_inactive_shows_them(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        inactive_user, _, _ = helpers.create_staff_user_with_token()
        inactive_user.is_active = False
        inactive_user.save(update_fields=['is_active'])
        Profile.objects.create(user=inactive_user)

        response = self.client.get(
            '/product/users?include_inactive=true', HTTP_AUTHORIZATION=f'Token {token.key}'
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        rows = body['results'] if 'results' in body else body
        usernames = [row['username'] for row in rows]
        self.assertIn(inactive_user.username, usernames)


class UserToggleActiveTest(TestCase):
    def test_admin_can_deactivate_another_user(self):
        admin, admin_token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'auth', 'change_user')
        target, _, _ = helpers.create_staff_user_with_token()
        Profile.objects.create(user=target)

        response = self.client.patch(
            f'/product/users/{target.id}/toggle-active/',
            {'is_active': False},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Token {admin_token.key}',
        )

        self.assertEqual(response.status_code, 200)
        target.refresh_from_db()
        self.assertFalse(target.is_active)

    def test_user_cannot_deactivate_self(self):
        admin, admin_token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'auth', 'change_user')

        response = self.client.patch(
            f'/product/users/{admin.id}/toggle-active/',
            {'is_active': False},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Token {admin_token.key}',
        )

        self.assertEqual(response.status_code, 400)
        admin.refresh_from_db()
        self.assertTrue(admin.is_active)

    def test_toggle_without_change_user_permission_is_forbidden(self):
        admin, admin_token, _ = helpers.create_staff_user_with_token()
        target, _, _ = helpers.create_staff_user_with_token()
        Profile.objects.create(user=target)

        response = self.client.patch(
            f'/product/users/{target.id}/toggle-active/',
            {'is_active': False},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Token {admin_token.key}',
        )

        self.assertEqual(response.status_code, 403)


class UserSetPasswordTest(TestCase):
    def test_admin_can_set_new_password(self):
        admin, admin_token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'auth', 'change_user')
        target, _, _ = helpers.create_staff_user_with_token()
        Profile.objects.create(user=target)

        response = self.client.post(
            f'/product/users/{target.id}/set-password/',
            {'password': 'NuevaContraseña789', 'password_confirm': 'NuevaContraseña789'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Token {admin_token.key}',
        )

        self.assertEqual(response.status_code, 204)
        target.refresh_from_db()
        self.assertTrue(target.check_password('NuevaContraseña789'))
        self.assertNotIn('NuevaContraseña789', target.password)

    def test_weak_new_password_is_rejected(self):
        admin, admin_token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'auth', 'change_user')
        target, _, _ = helpers.create_staff_user_with_token()
        Profile.objects.create(user=target)

        response = self.client.post(
            f'/product/users/{target.id}/set-password/',
            {'password': '123', 'password_confirm': '123'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Token {admin_token.key}',
        )

        self.assertEqual(response.status_code, 400)
