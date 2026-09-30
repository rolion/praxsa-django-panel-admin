"""API del cliente final para panel_admin/ (TASK-pricing-calculator-screen,
ADR-pricing-calculator-screen-registro-y-api-cliente y ...-sesion-cliente-aislamiento).

Cubre: registro (`client/register`), perfil (`client/me`), lista propia
(`client/proformas`), guardado con `POST invoice` como cliente, aislamiento (un token
de cliente no alcanza los endpoints de administracion) y el catalogo publico
(`calculator_info`) sin inactivos y con imagen."""
import json
import shutil
import tempfile
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.authtoken.models import Token
from rest_framework.settings import api_settings
from rest_framework.throttling import SimpleRateThrottle

from ..models import Client, Proforma_Header
from . import helpers
from .test_invoice_pricing import build_invoice_payload

REGISTER_URL = '/product/client/register'
ME_URL = '/product/client/me'
PROFORMAS_URL = '/product/client/proformas'
LOGIN_URL = '/product/api-panel-admin-token-auth/'

# Mismo patron que test_public_catalog_endpoints: la tasa real se captura al importar.
_ORIGINAL_THROTTLE_RATES = SimpleRateThrottle.THROTTLE_RATES


def register_payload(**overrides):
    payload = {
        'name': 'Ana',
        'lastname': 'Gomez',
        'email': 'ana@test.com',
        'phone_number': '70000001',
        'car_plate': 'ABC123',
        'password': 'Sup3r-segura-2026',
    }
    payload.update(overrides)
    return payload


def post_json(client, url, payload, **extra):
    return client.post(url, data=json.dumps(payload), content_type='application/json', **extra)


def make_client_user(email='cliente@test.com', plate='XYZ789'):
    user = User.objects.create_user(username=email, email=email, password='testpass123', first_name='Cli', last_name='Ente')
    Client.objects.create(name='Cli', last_name='Ente', phone_number='70000002', ci_nit='', car_plate=plate, user_id=user)
    token = Token.objects.create(user=user)
    return user, token


def auth(token):
    return {'HTTP_AUTHORIZATION': f'Token {token.key}'}


class ClientRegisterTest(TestCase):
    def setUp(self):
        cache.clear()

    def test_register_creates_non_staff_user_and_client_with_plate(self):
        response = post_json(self.client, REGISTER_URL, register_payload())

        self.assertEqual(response.status_code, 201)
        user = User.objects.get(email='ana@test.com')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.groups.count(), 0)
        self.assertEqual(user.user_permissions.count(), 0)
        self.assertEqual(user.first_name, 'Ana')
        client = Client.objects.get(user_id=user)
        self.assertEqual(client.car_plate, 'ABC123')
        self.assertEqual(client.phone_number, '70000001')
        self.assertEqual(client.ci_nit, '')

    def test_username_defaults_to_the_email(self):
        post_json(self.client, REGISTER_URL, register_payload())
        self.assertTrue(User.objects.filter(username='ana@test.com').exists())

    def test_custom_username_is_used(self):
        response = post_json(self.client, REGISTER_URL, register_payload(username='ana.g'))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), {'username': 'ana.g'})
        self.assertTrue(User.objects.filter(username='ana.g', email='ana@test.com').exists())

    def test_privileges_in_the_payload_are_ignored(self):
        response = post_json(self.client, REGISTER_URL, register_payload(is_staff=True, is_superuser=True, groups=[1]))
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(email='ana@test.com')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_response_does_not_expose_password_or_token(self):
        response = post_json(self.client, REGISTER_URL, register_payload())
        body = response.json()
        self.assertNotIn('password', body)
        self.assertNotIn('token', body)
        self.assertEqual(Token.objects.count(), 0)

    def test_duplicate_email_is_rejected_case_insensitive(self):
        post_json(self.client, REGISTER_URL, register_payload())
        response = post_json(self.client, REGISTER_URL, register_payload(email='ANA@test.com', username='otro'))
        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.json())
        self.assertEqual(User.objects.count(), 1)

    def test_duplicate_username_is_rejected_case_insensitive(self):
        post_json(self.client, REGISTER_URL, register_payload(username='ana.g'))
        response = post_json(self.client, REGISTER_URL, register_payload(email='otra@test.com', username='ANA.G'))
        self.assertEqual(response.status_code, 400)
        self.assertIn('username', response.json())

    def test_username_with_spaces_is_rejected(self):
        response = post_json(self.client, REGISTER_URL, register_payload(username='ana g'))
        self.assertEqual(response.status_code, 400)
        self.assertIn('username', response.json())

    def test_username_equal_to_another_users_email_is_rejected(self):
        make_client_user(email='viejo@test.com')
        response = post_json(self.client, REGISTER_URL, register_payload(username='viejo@test.com'))
        self.assertEqual(response.status_code, 400)

    def test_weak_passwords_are_rejected(self):
        for password in ('12345678', 'password', 'abc', 'ana@test.com'):
            with self.subTest(password=password):
                response = post_json(self.client, REGISTER_URL, register_payload(password=password))
                self.assertEqual(response.status_code, 400)
                self.assertIn('password', response.json())
        self.assertEqual(User.objects.count(), 0)

    def test_invalid_phone_and_plate_are_rejected(self):
        self.assertEqual(post_json(self.client, REGISTER_URL, register_payload(phone_number='123')).status_code, 400)
        self.assertEqual(post_json(self.client, REGISTER_URL, register_payload(phone_number='70000abc1')).status_code, 400)
        self.assertEqual(post_json(self.client, REGISTER_URL, register_payload(car_plate='ABCDEFGHIJK')).status_code, 400)

    def test_required_fields(self):
        response = post_json(self.client, REGISTER_URL, {})
        self.assertEqual(response.status_code, 400)
        for field in ('name', 'lastname', 'email', 'phone_number', 'car_plate', 'password'):
            self.assertIn(field, response.json())

    def test_new_account_can_log_in_with_the_panel_endpoint_as_non_staff(self):
        post_json(self.client, REGISTER_URL, register_payload(username='ana.g'))

        response = post_json(self.client, LOGIN_URL, {'username': 'ana.g', 'password': 'Sup3r-segura-2026'})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body['token'])
        self.assertFalse(body['is_staff'])
        self.assertEqual(body['groups'], [])
        self.assertEqual(body['permissions'], [])

    def test_create_client_legacy_endpoint_keeps_working(self):
        response = post_json(self.client, '/product/create_client', {
            'email': 'legacy@test.com', 'password': 'abc', 'name': 'Leg', 'lastname': 'Acy',
            'phone_number': '70000009', 'ci_nit': '123',
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Client.objects.get(user_id__email='legacy@test.com').car_plate, '')


@override_settings(REST_FRAMEWORK={
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly'],
    'DEFAULT_THROTTLE_RATES': {'public_catalog': '60/min', 'client_register': '2/min'},
})
class ClientRegisterThrottleTest(TestCase):
    def setUp(self):
        cache.clear()
        api_settings.reload()
        SimpleRateThrottle.THROTTLE_RATES = api_settings.DEFAULT_THROTTLE_RATES

    def tearDown(self):
        cache.clear()
        SimpleRateThrottle.THROTTLE_RATES = _ORIGINAL_THROTTLE_RATES

    def test_register_returns_429_after_exceeding_the_rate(self):
        for index in range(2):
            response = post_json(self.client, REGISTER_URL, register_payload(email=f'u{index}@test.com'))
            self.assertEqual(response.status_code, 201)
        response = post_json(self.client, REGISTER_URL, register_payload(email='u9@test.com'))
        self.assertEqual(response.status_code, 429)


class ClientMeTest(TestCase):
    def test_returns_the_profile_of_the_authenticated_client(self):
        user, token = make_client_user(plate='PLA111')

        response = self.client.get(ME_URL, **auth(token))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            'name': 'Cli', 'lastname': 'Ente', 'email': 'cliente@test.com',
            'phone_number': '70000002', 'car_plate': 'PLA111', 'ci_nit': '',
        })

    def test_requires_authentication(self):
        self.assertEqual(self.client.get(ME_URL).status_code, 401)
        self.assertEqual(self.client.get(ME_URL, HTTP_AUTHORIZATION='Token invalido').status_code, 401)

    def test_returns_404_for_a_user_without_client_profile(self):
        _staff, token, _password = helpers.create_staff_user_with_token()
        self.assertEqual(self.client.get(ME_URL, **auth(token)).status_code, 404)


class ClientProformasTest(TestCase):
    def setUp(self):
        self.scenario = helpers.build_full_scenario()
        self.user, self.token = make_client_user()

    def _create_proforma(self, user, plate='AAA111', **extra):
        return Proforma_Header.objects.create(
            name='Cliente', email='c@test.com', ci_nit='1', car_plate=plate, phone_number='70000001',
            sucursal=self.scenario['sucursal'], car_model_id=self.scenario['car_model'],
            total_price=Decimal('170.50'), created_by=user, **extra,
        )

    def test_lists_only_own_proformas_not_deleted_newest_first(self):
        first = self._create_proforma(self.user, plate='AAA111')
        second = self._create_proforma(self.user, plate='BBB222')
        self._create_proforma(self.user, plate='DEL000', is_delete=True)
        other_user, _other_token = make_client_user(email='otro@test.com')
        self._create_proforma(other_user, plate='OTR999')
        self._create_proforma(self.scenario['user'], plate='STF888')

        response = self.client.get(PROFORMAS_URL, **auth(self.token))

        self.assertEqual(response.status_code, 200)
        rows = response.json()
        self.assertEqual([row['id'] for row in rows], [second.id, first.id])
        self.assertEqual({row['car_plate'] for row in rows}, {'AAA111', 'BBB222'})

    def test_row_shape(self):
        proforma = self._create_proforma(self.user)

        row = self.client.get(PROFORMAS_URL, **auth(self.token)).json()[0]

        self.assertEqual(set(row), {'id', 'date', 'car_brand_name', 'car_model_name', 'car_plate', 'total_price'})
        self.assertEqual(row['id'], proforma.id)
        self.assertEqual(row['car_brand_name'], self.scenario['brand'].name)
        self.assertEqual(row['car_model_name'], self.scenario['car_model'].name)
        self.assertEqual(row['total_price'], '170.50')
        self.assertIn('T', row['date'])

    def test_empty_list_for_a_client_without_proformas(self):
        self.assertEqual(self.client.get(PROFORMAS_URL, **auth(self.token)).json(), [])

    def test_requires_authentication(self):
        self.assertEqual(self.client.get(PROFORMAS_URL).status_code, 401)

    def test_uses_a_constant_number_of_queries(self):
        for _ in range(3):
            self._create_proforma(self.user)
        with self.assertNumQueries(2):  # token + lista con select_related
            self.client.get(PROFORMAS_URL, **auth(self.token))


class ClientInvoiceFlowTest(TestCase):
    """Un cliente guarda una proforma con `POST invoice` (el servidor recalcula el
    precio) y la ve en su lista."""

    def test_client_saves_an_invoice_and_sees_it_in_its_list(self):
        scenario = helpers.build_full_scenario()
        _user, token = make_client_user()
        payload = build_invoice_payload(scenario, sub_total='1.00', installation_price='0', window_film_price='1.00')
        payload['ci_nit'] = None

        response = post_json(self.client, '/product/invoice', payload, **auth(token))

        self.assertEqual(response.status_code, 201)
        invoice_id = response.json()['id']
        header = Proforma_Header.objects.get(id=invoice_id)
        self.assertEqual(header.total_price, Decimal('170.00'))  # recalculado: 1*1*120 + 50
        self.assertEqual(header.created_by.email, 'cliente@test.com')
        rows = self.client.get(PROFORMAS_URL, **auth(token)).json()
        self.assertEqual([row['id'] for row in rows], [invoice_id])
        self.assertEqual(rows[0]['total_price'], '170.00')


class ClientIsolationTest(TestCase):
    """Un token de cliente (no staff) no alcanza los recursos de administracion: la
    barrera real sigue en el servidor (IsStaffUser), el guard del frontend es solo UX."""

    def test_client_token_gets_403_on_admin_endpoints(self):
        _user, token = make_client_user()
        urls = [
            '/product/ordenes/proformas',
            '/product/ordenes/notas-trabajo',
            '/product/ordenes/notas-venta',
            '/product/ordenes/catalogo/sucursales',
            '/product/ordenes/catalogo/bobinas?sucursal=1',
            '/product/vehicles/models',
            '/product/vehicles/brands',
            '/product/almacen/laminas',
            '/product/almacen/bobinas',
            '/product/users',
            '/product/groups',
            '/product/sucursales',
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url, **auth(token)).status_code, 403)

    def test_client_token_cannot_create_an_order_through_the_admin_api(self):
        _user, token = make_client_user()
        response = post_json(self.client, '/product/ordenes/proformas', {}, **auth(token))
        self.assertEqual(response.status_code, 403)


_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class CalculatorInfoPublicCatalogTest(TestCase):
    """`calculator_info` alimenta la calculadora sin sesion: solo activos y con imagen."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_MEDIA_ROOT, ignore_errors=True)

    def test_excludes_inactive_brands_models_parts_and_films(self):
        scenario = helpers.build_full_scenario()
        inactive_brand = helpers.create_brand()
        inactive_brand.is_active = False
        inactive_brand.save()
        inactive_model = helpers.create_model(brand=scenario['brand'])
        inactive_model.is_active = False
        inactive_model.save()
        inactive_part = helpers.create_car_part()
        inactive_part.is_active = False
        inactive_part.save()
        inactive_film = helpers.create_window_film()
        inactive_film.is_active = False
        inactive_film.save()

        data = self.client.get('/product/calculator_info').json()

        self.assertIn(scenario['brand'].id, [b['id'] for b in data['brands']])
        self.assertNotIn(inactive_brand.id, [b['id'] for b in data['brands']])
        self.assertIn(scenario['car_model'].id, [m['id'] for m in data['models']])
        self.assertNotIn(inactive_model.id, [m['id'] for m in data['models']])
        self.assertIn(scenario['car_part'].id, [p['id'] for p in data['parts']])
        self.assertNotIn(inactive_part.id, [p['id'] for p in data['parts']])
        self.assertIn(scenario['window_film'].id, [f['id'] for f in data['films']])
        self.assertNotIn(inactive_film.id, [f['id'] for f in data['films']])

    def test_models_include_image_url_or_null_and_keep_existing_keys(self):
        scenario = helpers.build_full_scenario()
        with_image = helpers.create_model(brand=scenario['brand'])
        with_image.image = SimpleUploadedFile('hilux.png', b'\x89PNG\r\n\x1a\n', content_type='image/png')
        with_image.save()

        data = self.client.get('/product/calculator_info').json()

        self.assertEqual(set(data), {'brands', 'models', 'parts', 'films', 'sucursales'})
        by_id = {m['id']: m for m in data['models']}
        self.assertIsNone(by_id[scenario['car_model'].id]['image'])
        self.assertTrue(by_id[with_image.id]['image'].startswith('http'))
        self.assertIn('car_models/', by_id[with_image.id]['image'])
        for key in ('id', 'name', 'brand_id'):
            self.assertIn(key, by_id[with_image.id])
