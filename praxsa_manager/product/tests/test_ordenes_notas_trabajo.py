"""Tests del modulo Ordenes: notas de trabajo (TASK-modulo-ordenes-proforma-nota-trabajo)."""
from django.test import TestCase
from django.utils import timezone

from ..models import Nota_trabajo, instalador
from . import helpers
from .ordenes_helpers import auth, instalacion_payload, make_scenario

URL = '/product/ordenes/notas-trabajo'


def _installer(sucursal, name='Instalador Uno'):
    inst = instalador.objects.create(name=name, address='Calle 1', phonenumber='70000002')
    inst.sucursal.add(sucursal)
    return inst


class NotaTrabajoTest(TestCase):
    def setUp(self):
        self.s = make_scenario()
        self.headers = auth(self.s['token'])
        proforma_id = self.client.post(
            '/product/ordenes/proformas', instalacion_payload(self.s),
            content_type='application/json', **self.headers,
        ).json()['id']
        self.client.post(f'/product/ordenes/proformas/{proforma_id}/generar-nota-trabajo/', **self.headers)
        self.nota = Nota_trabajo.objects.get(proforma_id=proforma_id)
        self.url = f'{URL}/{self.nota.id}/'

    def _patch(self, payload):
        return self.client.patch(self.url, payload, content_type='application/json', **self.headers)

    def test_list_and_detail(self):
        rows = self.client.get(URL, **self.headers).json()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['proforma_id'], self.nota.proforma_id)
        self.assertEqual(rows[0]['status'], 'en_proceso')
        self.assertEqual(rows[0]['nota_venta']['status'], 'por_cobrar')
        self.assertNotIn('is_finalizada', rows[0])
        self.assertEqual(rows[0]['sucursal_name'], self.s['sucursal'].name)
        self.assertEqual(rows[0]['sucursal_id'], self.s['sucursal'].id)

        detail = self.client.get(self.url, **self.headers).json()
        self.assertEqual(detail['sales_type'], 'venta_instalacion')
        self.assertEqual(len(detail['resumen']), 1)
        self.assertEqual(len(detail['proforma_items']), 1)
        self.assertEqual(detail['responsable_name'], self.s['user'].username)

    def test_list_exposes_car_brand_name(self):
        self.assertIsNotNone(self.nota.car_model_id)
        row = self.client.get(URL, **self.headers).json()[0]
        self.assertEqual(row['car_brand_name'], self.nota.car_model.car_brand_id.name)
        self.assertEqual(row['car_model_name'], self.nota.car_model.name)

    def test_list_car_brand_name_is_null_without_model(self):
        Nota_trabajo.objects.filter(pk=self.nota.pk).update(car_model=None)
        row = self.client.get(URL, **self.headers).json()[0]
        self.assertIsNone(row['car_brand_name'])
        self.assertIsNone(row['car_model_name'])

    def test_list_car_brand_name_does_not_add_queries_per_row(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as before:
            self.client.get(URL, **self.headers)
        for _ in range(3):
            header, _detail = helpers.create_full_proforma(self.s['user'], sucursal=self.s['sucursal'])
            helpers.create_nota_trabajo(header, car_model=header.car_model_id)
        with CaptureQueriesContext(connection) as after:
            rows = self.client.get(URL, **self.headers).json()
        self.assertEqual(len(rows), 4)
        self.assertEqual(len(after), len(before))

    def test_list_search(self):
        self.assertEqual(len(self.client.get(URL, {'search': 'ABC123'}, **self.headers).json()), 1)
        self.assertEqual(len(self.client.get(URL, {'search': str(self.nota.proforma_id)}, **self.headers).json()), 1)
        self.assertEqual(self.client.get(URL, {'search': 'zzz'}, **self.headers).json(), [])

    def test_patch_operational_fields(self):
        inst = _installer(self.s['sucursal'])
        salida = timezone.now().isoformat()

        response = self._patch({
            'instaladar': inst.id, 'codigo_garantia': 'GAR-001',
            'salida_vehiculo': salida, 'observaciones': 'sin novedades',
        })

        self.assertEqual(response.status_code, 200, response.content)
        self.nota.refresh_from_db()
        self.assertEqual(self.nota.instaladar, inst)
        self.assertEqual(self.nota.codigo_garantia, 'GAR-001')
        self.assertEqual(self.nota.observaciones, 'sin novedades')
        self.assertIsNotNone(self.nota.salida_vehiculo)

    def test_readonly_fields_are_ignored(self):
        original_name = self.nota.name
        response = self._patch({'name': 'Otro', 'car_plate': 'ZZZ999', 'is_close': True, 'observaciones': 'ok'})

        self.assertEqual(response.status_code, 200, response.content)
        self.nota.refresh_from_db()
        self.assertEqual(self.nota.name, original_name)
        self.assertFalse(self.nota.is_close)

    def test_empty_codigo_garantia_becomes_null_and_does_not_collide(self):
        other = helpers.create_nota_trabajo(proforma=helpers.create_full_proforma(self.s['user'])[0])
        for nota in (self.nota, other):
            response = self.client.patch(
                f'{URL}/{nota.id}/', {'codigo_garantia': ''},
                content_type='application/json', **self.headers,
            )
            self.assertEqual(response.status_code, 200, response.content)
            nota.refresh_from_db()
            self.assertIsNone(nota.codigo_garantia)

    def test_duplicate_or_too_long_codigo_garantia_is_400(self):
        other = helpers.create_nota_trabajo(
            proforma=helpers.create_full_proforma(self.s['user'])[0], codigo_garantia='DUP-1'
        )
        self.assertEqual(other.codigo_garantia, 'DUP-1')
        self.assertEqual(self._patch({'codigo_garantia': 'DUP-1'}).status_code, 400)
        self.assertEqual(self._patch({'codigo_garantia': 'X' * 13}).status_code, 400)

    def test_installer_must_belong_to_proforma_sucursal(self):
        other_sucursal = helpers.create_sucursal(self.s['user'])
        foreign = _installer(other_sucursal, name='Ajeno')
        response = self._patch({'instaladar': foreign.id})
        self.assertEqual(response.status_code, 400)
        self.assertIn('instaladar', response.json())

    def test_note_not_en_proceso_cannot_be_edited(self):
        Nota_trabajo.objects.filter(pk=self.nota.pk).update(status='terminado')
        self.assertEqual(self._patch({'observaciones': 'x'}).status_code, 409)
        self.assertEqual(self.client.get(URL, **self.headers).json()[0]['status'], 'terminado')

    def test_requires_change_permission_and_no_create_or_delete(self):
        from .ordenes_helpers import make_staff
        user, token = make_staff(permissions=(), group='admin')
        self.assertEqual(
            self.client.patch(self.url, {'observaciones': 'x'}, content_type='application/json', **auth(token)).status_code,
            403,
        )
        self.assertEqual(self.client.get(self.url, **auth(token)).status_code, 200)
        self.assertEqual(self.client.post(URL, {}, content_type='application/json', **self.headers).status_code, 405)
        self.assertIn(self.client.delete(self.url, **self.headers).status_code, (403, 405))
        self.assertTrue(Nota_trabajo.objects.filter(pk=self.nota.pk).exists())
