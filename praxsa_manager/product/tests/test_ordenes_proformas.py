"""Tests del modulo Ordenes: proformas (TASK-modulo-ordenes-proforma-nota-trabajo).
Ver ADR-modulo-ordenes-proforma-nota-trabajo-api-y-calculo."""
from decimal import Decimal

from django.test import TestCase

from ..models import Nota_trabajo, Proforma_Detail, Proforma_Header, inventario
from . import helpers
from .ordenes_helpers import auth, instalacion_payload, make_scenario, make_staff, metro_lineal_payload

URL = '/product/ordenes/proformas'


class ProformaCreateTest(TestCase):
    def setUp(self):
        self.s = make_scenario()
        self.headers = auth(self.s['token'])

    def _post(self, payload):
        return self.client.post(URL, payload, content_type='application/json', **self.headers)

    def test_create_instalacion_recalculates_price_ignoring_client_values(self):
        payload = instalacion_payload(self.s, total_price='1.00')
        payload['items'][0].update({'sub_total': '1.00', 'installation_price': '999', 'window_film_price': '1'})

        response = self._post(payload)

        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        line = data['items'][0]
        # largo 1.00 * cantidad 2 * 120.00 + instalacion 50.00 * 2
        self.assertEqual(Decimal(line['sub_total']), Decimal('340.00'))
        self.assertEqual(Decimal(line['installation_price']), Decimal('50.00'))
        self.assertEqual(Decimal(line['window_film_price']), Decimal('120.00'))
        self.assertEqual(Decimal(data['total_price']), Decimal('340.00'))
        header = Proforma_Header.objects.get(pk=data['id'])
        self.assertEqual(header.created_by, self.s['user'])
        self.assertEqual(header.status, 'proforma')
        self.assertFalse(header.is_close)

    def test_create_metro_lineal_without_model_or_item(self):
        response = self._post(metro_lineal_payload(self.s))

        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        line = data['items'][0]
        self.assertEqual(Decimal(line['sub_total']), Decimal('420.00'))  # 3.50 * 120.00
        self.assertIsNone(line['car_part'])
        self.assertEqual(line['quantity'], 0)
        self.assertEqual(Decimal(line['installation_price']), Decimal('0'))
        self.assertIsNone(data['car_model_id'])

    def test_metro_lineal_accepts_an_optional_car_model(self):
        response = self._post(metro_lineal_payload(self.s, car_model_id=self.s['car_model'].id, car_plate='XYZ789'))

        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        self.assertEqual(data['car_model_id'], self.s['car_model'].id)
        self.assertEqual(data['car_model_name'], self.s['car_model'].name)
        line = data['items'][0]
        self.assertIsNone(line['car_part'])
        self.assertEqual(Decimal(line['sub_total']), Decimal('420.00'))  # el modelo no cambia el precio

    def test_metro_lineal_rejects_an_inactive_car_model(self):
        self.s['car_model'].is_active = False
        self.s['car_model'].save()
        response = self._post(metro_lineal_payload(self.s, car_model_id=self.s['car_model'].id))
        self.assertEqual(response.status_code, 400)
        self.assertIn('car_model_id', response.json())

    def test_total_is_sum_of_lines_and_total_a_pagar_subtracts_discount(self):
        payload = metro_lineal_payload(self.s, discount='20.00', discount_reason='cliente frecuente')
        payload['items'].append({'window_film': self.s['film'].id, 'width': '1.50', 'length': '1.00'})

        response = self._post(payload)

        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        self.assertEqual(Decimal(data['total_price']), Decimal('540.00'))
        self.assertEqual(Decimal(data['total_a_pagar']), Decimal('520.00'))

    def test_price_uses_precio_venta_sucursal_override(self):
        helpers.create_precio_venta_sucursal(
            self.s['sucursal'], self.s['film'], width=Decimal('1.50'), precio_venta=Decimal('150.00')
        )

        response = self._post(metro_lineal_payload(self.s))

        self.assertEqual(Decimal(response.json()['items'][0]['sub_total']), Decimal('525.00'))

    def test_metro_lineal_rejects_item_and_quantity(self):
        payload = metro_lineal_payload(self.s)
        payload['items'][0]['car_part'] = self.s['car_part'].id
        self.assertEqual(self._post(payload).status_code, 400)

        payload = metro_lineal_payload(self.s)
        payload['items'][0]['quantity'] = 2
        self.assertEqual(self._post(payload).status_code, 400)
        self.assertEqual(Proforma_Header.objects.count(), 0)

    def test_instalacion_requires_model_plate_and_item(self):
        self.assertEqual(self._post(instalacion_payload(self.s, car_model_id=None)).status_code, 400)
        self.assertEqual(self._post(instalacion_payload(self.s, car_plate='')).status_code, 400)
        payload = instalacion_payload(self.s)
        payload['items'][0]['car_part'] = None
        self.assertEqual(self._post(payload).status_code, 400)

    def test_instalacion_rejects_item_of_another_model_and_zero_quantity(self):
        other_part = helpers.create_car_part()
        payload = instalacion_payload(self.s)
        payload['items'][0]['car_part'] = other_part.id
        response = self._post(payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn('items', response.json())

        payload = instalacion_payload(self.s)
        payload['items'][0]['quantity'] = 0
        self.assertEqual(self._post(payload).status_code, 400)

    def test_rejects_film_narrower_than_item(self):
        narrow = helpers.create_window_film_reel(window_film=self.s['film'], width=Decimal('1.00'))
        helpers.create_inventario(sucursal=self.s['sucursal'], bobina=narrow)
        payload = instalacion_payload(self.s)
        payload['items'][0]['width'] = '1.00'  # item requiere 1.50

        response = self._post(payload)

        self.assertEqual(response.status_code, 400)
        self.assertIn('items', response.json())

    def test_rejects_non_exact_width_and_missing_stock(self):
        payload = metro_lineal_payload(self.s)
        payload['items'][0]['width'] = '1.20'  # no hay bobina de 1.20
        self.assertEqual(self._post(payload).status_code, 400)

        self.s['inventario'].to_install = Decimal('0')
        self.s['inventario'].save()
        self.assertEqual(self._post(metro_lineal_payload(self.s)).status_code, 400)

    def test_rejects_inactive_film_model_and_item(self):
        self.s['film'].is_active = False
        self.s['film'].save()
        self.assertEqual(self._post(metro_lineal_payload(self.s)).status_code, 400)
        self.s['film'].is_active = True
        self.s['film'].save()

        self.s['car_model'].is_active = False
        self.s['car_model'].save()
        self.assertEqual(self._post(instalacion_payload(self.s)).status_code, 400)
        self.s['car_model'].is_active = True
        self.s['car_model'].save()

        self.s['car_part'].is_active = False
        self.s['car_part'].save()
        self.assertEqual(self._post(instalacion_payload(self.s)).status_code, 400)

    def test_requires_at_least_one_line(self):
        self.assertEqual(self._post(metro_lineal_payload(self.s, items=[])).status_code, 400)
        payload = metro_lineal_payload(self.s)
        del payload['items']
        self.assertEqual(self._post(payload).status_code, 400)

    def test_discount_rules_use_server_recalculated_total(self):
        # total real 420.00: 50% = 210.00
        over = self._post(metro_lineal_payload(self.s, discount='210.01', discount_reason='x'))
        self.assertEqual(over.status_code, 400)
        self.assertIn('discount', over.json())

        no_reason = self._post(metro_lineal_payload(self.s, discount='10.00'))
        self.assertEqual(no_reason.status_code, 400)
        self.assertIn('discount_reason', no_reason.json())

        ok = self._post(metro_lineal_payload(self.s, discount='210.00', discount_reason='aprobado'))
        self.assertEqual(ok.status_code, 201, ok.content)

    def test_model_validators_are_kept(self):
        for field, value in (
            ('email', 'no-es-email'), ('phone_number', 'abc'), ('car_plate', 'X' * 11),
            ('name', 'N' * 401),
        ):
            payload = instalacion_payload(self.s, **{field: value})
            response = self._post(payload)
            self.assertEqual(response.status_code, 400, (field, response.content))
            self.assertIn(field, response.json())

    def test_required_customer_fields(self):
        for field in ('name', 'email', 'ci_nit', 'phone_number', 'sales_type', 'sucursal'):
            payload = metro_lineal_payload(self.s)
            del payload[field]
            self.assertEqual(self._post(payload).status_code, 400, field)

    def test_failed_line_creates_nothing(self):
        payload = metro_lineal_payload(self.s)
        payload['items'].append({'window_film': self.s['film'].id, 'width': '9.99', 'length': '1'})
        self.assertEqual(self._post(payload).status_code, 400)
        self.assertEqual(Proforma_Header.objects.count(), 0)
        self.assertEqual(Proforma_Detail.objects.count(), 0)


class ProformaListDetailTest(TestCase):
    def setUp(self):
        self.s = make_scenario()
        self.headers = auth(self.s['token'])
        created = self.client.post(
            URL, instalacion_payload(self.s), content_type='application/json', **self.headers
        )
        self.proforma_id = created.json()['id']

    def test_list_returns_row_without_lines(self):
        response = self.client.get(URL, **self.headers)

        self.assertEqual(response.status_code, 200)
        rows = response.json()
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row['id'], self.proforma_id)
        self.assertEqual(row['status'], 'proforma')
        self.assertIsNone(row['nota_trabajo_id'])
        self.assertNotIn('items', row)
        self.assertEqual(row['car_model_name'], self.s['car_model'].name)

    def test_list_filters(self):
        self.client.post(URL, metro_lineal_payload(self.s), content_type='application/json', **self.headers)
        self.assertEqual(len(self.client.get(URL, **self.headers).json()), 2)
        by_type = self.client.get(URL, {'sales_type': 'venta_metro_lineal'}, **self.headers).json()
        self.assertEqual([r['sales_type'] for r in by_type], ['venta_metro_lineal'])
        by_search = self.client.get(URL, {'search': 'ABC123'}, **self.headers).json()
        self.assertEqual([r['id'] for r in by_search], [self.proforma_id])
        by_id = self.client.get(URL, {'search': str(self.proforma_id)}, **self.headers).json()
        self.assertEqual([r['id'] for r in by_id], [self.proforma_id])
        self.assertEqual(self.client.get(URL, {'status': 'finalizado'}, **self.headers).json(), [])

    def test_detail_includes_lines(self):
        response = self.client.get(f'{URL}/{self.proforma_id}/', **self.headers)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['items']), 1)
        self.assertEqual(data['items'][0]['car_part_name'], self.s['car_part'].name)
        self.assertEqual(data['email'], 'cliente@test.com')

    def test_deleted_proforma_is_not_visible(self):
        Proforma_Header.objects.filter(pk=self.proforma_id).update(is_delete=True)
        self.assertEqual(self.client.get(f'{URL}/{self.proforma_id}/', **self.headers).status_code, 404)
        self.assertEqual(self.client.get(URL, **self.headers).json(), [])


class ProformaUpdateTest(TestCase):
    def setUp(self):
        self.s = make_scenario()
        self.headers = auth(self.s['token'])
        created = self.client.post(
            URL, instalacion_payload(self.s), content_type='application/json', **self.headers
        )
        self.proforma_id = created.json()['id']
        self.url = f'{URL}/{self.proforma_id}/'

    def _patch(self, payload):
        return self.client.patch(self.url, payload, content_type='application/json', **self.headers)

    def test_patch_header_only_keeps_lines_and_total(self):
        response = self._patch({'name': 'Nuevo Nombre'})

        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(data['name'], 'Nuevo Nombre')
        self.assertEqual(len(data['items']), 1)
        self.assertEqual(Decimal(data['total_price']), Decimal('340.00'))

    def test_patch_replaces_lines_and_recalculates_total(self):
        items = [{
            'car_part': self.s['car_part'].id, 'window_film': self.s['film'].id,
            'width': '1.50', 'length': '2.00', 'quantity': 1,
        }]

        response = self._patch({'items': items})

        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(len(data['items']), 1)
        self.assertEqual(Decimal(data['total_price']), Decimal('290.00'))  # 2*120 + 50
        self.assertEqual(Proforma_Detail.objects.filter(proforma_header_id=self.proforma_id).count(), 1)

    def test_failed_replacement_keeps_previous_lines(self):
        response = self._patch({'items': [{'window_film': self.s['film'].id, 'width': '9.99', 'length': '1'}]})

        self.assertEqual(response.status_code, 400)
        header = Proforma_Header.objects.get(pk=self.proforma_id)
        self.assertEqual(header.total_price, Decimal('340.00'))
        self.assertEqual(header.items.count(), 1)

    def test_sales_type_and_sucursal_are_immutable(self):
        self.assertEqual(self._patch({'sales_type': 'venta_metro_lineal'}).status_code, 400)
        other = helpers.create_sucursal(self.s['user'])
        self.assertEqual(self._patch({'sucursal': other.id}).status_code, 400)
        # el mismo valor si se acepta
        self.assertEqual(self._patch({'sucursal': self.s['sucursal'].id}).status_code, 200)

    def test_closed_proforma_cannot_be_edited(self):
        Proforma_Header.objects.filter(pk=self.proforma_id).update(status='en_trabajo', is_close=True)
        self.assertEqual(self._patch({'name': 'X'}).status_code, 409)

    def test_discount_is_validated_against_stored_total_on_header_patch(self):
        self.assertEqual(self._patch({'discount': '170.01', 'discount_reason': 'x'}).status_code, 400)
        self.assertEqual(self._patch({'discount': '170.00', 'discount_reason': 'x'}).status_code, 200)

    def test_put_and_delete_are_not_allowed(self):
        self.assertEqual(self.client.put(self.url, {}, content_type='application/json', **self.headers).status_code, 405)
        # DELETE lo corta DjangoModelPermissions (403) antes que el 405; lo importante es que no borre.
        self.assertIn(self.client.delete(self.url, **self.headers).status_code, (403, 405))
        self.assertTrue(Proforma_Header.objects.filter(pk=self.proforma_id).exists())


class ProformaGenerateNotaTest(TestCase):
    def setUp(self):
        self.s = make_scenario()
        self.headers = auth(self.s['token'])
        created = self.client.post(
            URL, instalacion_payload(self.s), content_type='application/json', **self.headers
        )
        self.proforma_id = created.json()['id']
        self.url = f'{URL}/{self.proforma_id}/generar-nota-trabajo/'

    def test_generates_note_reduces_inventory_and_closes_proforma(self):
        response = self.client.post(self.url, **self.headers)

        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertTrue(data['is_close'])
        self.assertEqual(data['status'], 'en_trabajo')
        self.assertIsNotNone(data['nota_trabajo_id'])
        nota = Nota_trabajo.objects.get(pk=data['nota_trabajo_id'])
        self.assertEqual(nota.responsable, self.s['user'])
        inv = inventario.objects.get(pk=self.s['inventario'].pk)
        self.assertEqual(inv.to_install, Decimal('48.00'))  # largo 1.00 * cantidad 2

    def test_second_call_returns_409(self):
        self.client.post(self.url, **self.headers)
        self.assertEqual(self.client.post(self.url, **self.headers).status_code, 409)
        inv = inventario.objects.get(pk=self.s['inventario'].pk)
        self.assertEqual(inv.to_install, Decimal('48.00'))

    def test_without_stock_returns_409_and_leaves_no_partial_changes(self):
        inv = self.s['inventario']
        inv.to_install = Decimal('1.00')
        inv.save()

        response = self.client.post(self.url, **self.headers)

        self.assertEqual(response.status_code, 409, response.content)
        self.assertIn('detail', response.json())
        header = Proforma_Header.objects.get(pk=self.proforma_id)
        self.assertFalse(header.is_close)
        self.assertEqual(Nota_trabajo.objects.count(), 0)
        inv.refresh_from_db()
        self.assertEqual(inv.to_install, Decimal('1.00'))

    def test_requires_add_nota_trabajo_permission(self):
        user, token = make_staff(permissions=('add_proforma_header',))
        helpers.add_user_to_group(user, 'admin')
        response = self.client.post(self.url, **auth(token))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Nota_trabajo.objects.count(), 0)


class ProformaPdfTest(TestCase):
    def setUp(self):
        self.s = make_scenario()
        self.headers = auth(self.s['token'])

    def _create(self, payload):
        return self.client.post(URL, payload, content_type='application/json', **self.headers).json()['id']

    def test_pdf_for_both_sales_types(self):
        for payload in (instalacion_payload(self.s), metro_lineal_payload(self.s)):
            proforma_id = self._create(payload)
            response = self.client.get(f'{URL}/{proforma_id}/pdf/', **self.headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Content-Type'], 'application/pdf')
            self.assertIn(f'proforma-{proforma_id}.pdf', response['Content-Disposition'])
            self.assertTrue(b''.join(response.streaming_content).startswith(b'%PDF'))

    def test_pdf_without_sucursal_returns_409(self):
        proforma_id = self._create(metro_lineal_payload(self.s))
        # Una proforma legada sin sucursal solo la ve el superusuario (fuera del alcance de sucursal).
        _, admin_token, _ = helpers.create_superuser_with_token()
        Proforma_Header.objects.filter(pk=proforma_id).update(sucursal=None)
        response = self.client.get(f'{URL}/{proforma_id}/pdf/', **auth(admin_token))
        self.assertEqual(response.status_code, 409)
