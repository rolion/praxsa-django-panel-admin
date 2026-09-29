"""Paridad de precio entre la API del panel (Ordenes) y el formulario del
Django Admin (CarModelPartForm), ver ADR-modulo-ordenes-proforma-nota-trabajo-
api-y-calculo punto 5: la orquestacion esta duplicada a proposito (el form no
se toca), asi que estos tests fijan que ambos caminos dan el mismo resultado."""
from decimal import Decimal

from django.test import TestCase

from ..Forms.car_model_part import CarModelPartForm
from ..helper.proforma import Proforma_Helper
from ..models import Proforma_Header
from . import helpers
from .ordenes_helpers import auth, instalacion_payload, make_scenario, metro_lineal_payload

URL = '/product/ordenes/proformas'


class PriceParityTest(TestCase):
    def setUp(self):
        self.s = make_scenario()
        self.headers = auth(self.s['token'])

    def _header(self, sales_type):
        return Proforma_Header.objects.create(
            name='Cliente', email='c@test.com', ci_nit='123', car_plate='ABC123',
            phone_number='70000001', sucursal=self.s['sucursal'], car_model_id=self.s['car_model'],
            sales_type=sales_type, created_by=self.s['user'],
        )

    def _form_data(self, header, **overrides):
        data = {
            'proforma_header': header.pk,
            'inventario': self.s['inventario'].pk,
            'car_part': self.s['car_part'].pk,
            'window_film': self.s['film'].pk,
            'width': '1.50', 'length': '1.00', 'quantity': '1',
            'installation_price': '1.00', 'window_film_price': '1.00', 'sub_total': '1.00',
        }
        data.update(overrides)
        return data

    def _assert_same(self, form_cleaned, api_line):
        for field in ('sub_total', 'window_film_price', 'installation_price'):
            self.assertEqual(Decimal(api_line[field]), form_cleaned[field], field)

    def _check(self, sales_type, form_overrides, api_payload):
        for with_override in (False, True):
            if with_override:
                helpers.create_precio_venta_sucursal(
                    self.s['sucursal'], self.s['film'], width=Decimal('1.50'), precio_venta=Decimal('137.35')
                )
            header = self._header(sales_type)
            form = CarModelPartForm(data=self._form_data(header, **form_overrides))
            self.assertTrue(form.is_valid(), form.errors)
            response = self.client.post(URL, api_payload, content_type='application/json', **self.headers)
            self.assertEqual(response.status_code, 201, response.content)
            self._assert_same(form.cleaned_data, response.json()['items'][0])

    def test_venta_instalacion_matches_admin_form(self):
        payload = instalacion_payload(self.s)
        payload['items'][0].update({'length': '1.75', 'quantity': 3})
        self._check(
            Proforma_Helper().tipo_venta_instalacion,
            {'length': '1.75', 'quantity': '3'},
            payload,
        )

    def test_venta_metro_lineal_matches_admin_form(self):
        payload = metro_lineal_payload(self.s)
        payload['items'][0]['length'] = '2.35'
        self._check(
            Proforma_Helper().tipo_venta_metro_lineal,
            {'length': '2.35', 'quantity': '0', 'installation_price': '0', 'car_part': ''},
            payload,
        )
