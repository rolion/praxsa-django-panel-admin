"""Smoke tests: un test por endpoint de /product/, status code + shape básico."""
import json
from decimal import Decimal

from django.test import TestCase

from . import helpers


class CreateClientEndpointTest(TestCase):
    def test_create_client_returns_201_and_client_shape(self):
        payload = {
            'email': 'nuevo.cliente@test.com',
            'password': 'supersecreta123',
            'name': 'Nuevo',
            'lastname': 'Cliente',
            'phone_number': '71234567',
            'ci_nit': '9876543',
        }
        response = self.client.post(
            '/product/create_client',
            data=json.dumps(payload),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['email'], payload['email'])
        self.assertEqual(data['name'], payload['name'])
        self.assertEqual(data['lastname'], payload['lastname'])
        self.assertEqual(data['phone_number'], payload['phone_number'])


class CalculatorInfoEndpointTest(TestCase):
    def test_calculator_info_returns_200_and_expected_shape(self):
        scenario = helpers.build_full_scenario()

        response = self.client.get('/product/calculator_info')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        for key in ('brands', 'models', 'parts', 'films', 'sucursales'):
            self.assertIn(key, data)

        brand_ids = [b['id'] for b in data['brands']]
        self.assertIn(scenario['brand'].id, brand_ids)

        model_ids = [m['id'] for m in data['models']]
        self.assertIn(scenario['car_model'].id, model_ids)

        sucursal_ids = [s['id'] for s in data['sucursales']]
        self.assertIn(scenario['sucursal'].id, sucursal_ids)


class InvoiceCreateEndpointTest(TestCase):
    def test_invoice_post_returns_201_and_created_id(self):
        scenario = helpers.build_full_scenario()
        token = scenario['token']

        payload = {
            'name': 'Cliente Invoice',
            'email': 'invoice@test.com',
            'car_plate': 'XYZ999',
            'car_model_id': scenario['car_model'].id,
            'total_price': '170.00',
            'phone_number': '70000002',
            'ci_nit': '7654321',
            'sucursal': scenario['sucursal'].id,
            'carPartItems': [
                {
                    'car_part': scenario['car_part'].id,
                    'width': '1.50',
                    'length': '1.00',
                    'quantity': 1,
                    'window_film': scenario['window_film'].id,
                    'installation_price': '50.00',
                    'window_film_price': '120.00',
                    'sub_total': '170.00',
                }
            ],
        }

        response = self.client.post(
            '/product/invoice',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Token {token.key}',
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn('id', data)

    def test_invoice_post_without_token_returns_401(self):
        response = self.client.post(
            '/product/invoice',
            data=json.dumps({}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 401)


class InvoiceRetrieveEndpointTest(TestCase):
    def test_invoice_get_returns_200_and_expected_shape(self):
        user, token = helpers.create_user_with_token()
        sucursal = helpers.create_sucursal(user)
        car_model = helpers.create_model()
        header, detail = helpers.create_full_proforma(
            user=user,
            sucursal=sucursal,
            car_model=car_model,
        )

        response = self.client.get(
            f'/product/invoice/{header.id}/',
            HTTP_AUTHORIZATION=f'Token {token.key}',
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['id'], header.id)
        self.assertEqual(data['name'], header.name)
        self.assertEqual(data['sucursal'], sucursal.id)
        self.assertEqual(Decimal(str(data['total_price'])), header.total_price)
        self.assertEqual(len(data['carPartItems']), 1)
        self.assertEqual(data['carPartItems'][0]['car_part_id'], detail.car_part.id)


class ListUserInvoiceEndpointTest(TestCase):
    def test_invoice_all_returns_200_and_expected_shape(self):
        user, token = helpers.create_user_with_token()
        sucursal = helpers.create_sucursal(user)
        helpers.create_full_proforma(user=user, sucursal=sucursal)
        helpers.create_full_proforma(user=user, sucursal=sucursal)

        response = self.client.get(
            '/product/invoice/all',
            HTTP_AUTHORIZATION=f'Token {token.key}',
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['recordsTotal'], 2)
        self.assertEqual(data['recordsFiltered'], 2)
        self.assertEqual(len(data['data']), 2)
