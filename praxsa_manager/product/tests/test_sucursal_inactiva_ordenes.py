"""Sucursal inactiva = solo lectura en Ordenes (ADR-inventario-alcance-sucursal-
django-admin-alcance-lectura-escritura, decisiones 3 y 4): se pueden ver proformas,
notas de trabajo y notas de venta de una sucursal inactiva asignada, pero toda
modificacion responde 409 y no cambia nada; fuera del alcance de lectura sigue
siendo 404."""
from decimal import Decimal

from ..models import Nota_trabajo, Nota_Venta, Proforma_Header, inventario, pago
from . import helpers
from .ordenes_helpers import auth, metro_lineal_payload
from .test_ordenes_notas_venta_pagos import NOTAS, PROFORMAS, VENTAS, OrdenApiBase

WRITE_CODENAMES = (
    'delete_proforma_header', 'delete_nota_trabajo', 'add_pago', 'delete_pago', 'delete_nota_venta',
)


class SucursalInactivaOrdenesTest(OrdenApiBase):
    def setUp(self):
        super().setUp()
        for codename in WRITE_CODENAMES:
            helpers.grant_permission(self.s['user'], 'product', codename)

    def desactivar(self):
        sucursal = self.s['sucursal']
        sucursal.enable_to_install_windows_film = False
        sucursal.save(update_fields=['enable_to_install_windows_film'])

    def assert_conflict(self, response):
        self.assertEqual(response.status_code, 409, response.content)
        self.assertIn('inactiva', response.json()['detail'])

    # -- lectura sigue funcionando
    def test_reading_everything_still_works(self):
        proforma_id, nota, nv = self.terminada()
        self.desactivar()

        for url in (f'{PROFORMAS}/{proforma_id}/', f'{NOTAS}/{nota.pk}/', f'{VENTAS}/{nv.pk}/'):
            response = self.client.get(url, **self.owner_headers)
            self.assertEqual(response.status_code, 200, url)
            self.assertFalse(response.json()['sucursal_activa'], url)
        for url in (PROFORMAS, NOTAS, VENTAS):
            rows = self.client.get(url, **self.owner_headers).json()
            self.assertEqual(len(rows), 1, url)
            self.assertFalse(rows[0]['sucursal_activa'], url)

    def test_active_sucursal_is_flagged_active(self):
        proforma_id = self.nueva_proforma()
        detail = self.client.get(f'{PROFORMAS}/{proforma_id}/', **self.owner_headers).json()
        self.assertTrue(detail['sucursal_activa'])

    # -- proformas
    def test_cannot_create_proforma(self):
        self.desactivar()
        response = self.client.post(
            PROFORMAS, metro_lineal_payload(self.s), content_type='application/json', **self.owner_headers)
        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(Proforma_Header.objects.count(), 0)

    def test_cannot_edit_proforma(self):
        proforma_id = self.nueva_proforma()
        self.desactivar()
        response = self.client.patch(
            f'{PROFORMAS}/{proforma_id}/', {'name': 'Otro'}, content_type='application/json', **self.owner_headers)
        self.assert_conflict(response)
        self.assertNotEqual(Proforma_Header.objects.get(pk=proforma_id).name, 'Otro')

    def test_cannot_generate_work_note(self):
        proforma_id = self.nueva_proforma()
        self.desactivar()
        self.assert_conflict(self.post(f'{PROFORMAS}/{proforma_id}/generar-nota-trabajo/', self.owner_headers))
        self.assertEqual(Nota_trabajo.objects.count(), 0)
        self.assertEqual(self.to_install(), Decimal('50.00'))

    def test_cannot_annul_proforma(self):
        proforma_id = self.nueva_proforma()
        self.desactivar()
        self.assert_conflict(self.post(f'{PROFORMAS}/{proforma_id}/anular/', self.owner_headers))
        self.assertEqual(Proforma_Header.objects.get(pk=proforma_id).status, 'proforma')

    # -- notas de trabajo
    def test_cannot_edit_work_note(self):
        _, nota, _ = self.aprobada()
        self.desactivar()
        response = self.client.patch(
            f'{NOTAS}/{nota.pk}/', {'observaciones': 'x'}, content_type='application/json', **self.owner_headers)
        self.assert_conflict(response)

    def test_cannot_finish_correct_or_annul_work_note(self):
        _, nota, _ = self.aprobada()
        self.desactivar()
        for accion in ('terminar', 'corregir', 'anular'):
            self.assert_conflict(self.post(f'{NOTAS}/{nota.pk}/{accion}/', self.owner_headers))
        self.assertEqual(Nota_trabajo.objects.get(pk=nota.pk).status, 'en_proceso')

    # -- notas de venta
    def test_cannot_pay_or_annul_sale_note(self):
        _, _, nv = self.terminada()
        self.desactivar()
        self.assert_conflict(self.post(f'{VENTAS}/{nv.pk}/pago/', self.owner_headers, {'tipo_pago': 'efec'}))
        self.assert_conflict(self.post(f'{VENTAS}/{nv.pk}/anular/', self.owner_headers))
        self.assertFalse(pago.objects.filter(nota_venta=nv).exists())
        self.assertEqual(Nota_Venta.objects.get(pk=nv.pk).status, 'por_cobrar')

    def test_cannot_annul_payment(self):
        _, _, nv = self.terminada()
        self.assertEqual(
            self.post(f'{VENTAS}/{nv.pk}/pago/', self.owner_headers, {'tipo_pago': 'efec'}).status_code, 200)
        self.desactivar()
        self.assert_conflict(self.post(f'{VENTAS}/{nv.pk}/anular-pago/', self.owner_headers))
        self.assertTrue(pago.objects.filter(nota_venta=nv).exists())

    # -- 404 fuera del alcance de lectura sigue primando sobre el 409
    def test_foreign_sucursal_is_404_not_409(self):
        proforma_id = self.nueva_proforma()
        self.desactivar()
        _, token, _ = helpers.create_staff_user_with_token()
        for codename in ('change_proforma_header', 'delete_proforma_header'):
            helpers.grant_permission(token.user, 'product', codename)
        helpers.create_sucursal(token.user)

        self.assertEqual(
            self.client.patch(f'{PROFORMAS}/{proforma_id}/', {'name': 'x'}, content_type='application/json',
                              **auth(token)).status_code, 404)
        self.assertEqual(self.post(f'{PROFORMAS}/{proforma_id}/anular/', auth(token)).status_code, 404)

    def test_superuser_is_also_read_only_on_inactive_sucursal(self):
        proforma_id = self.nueva_proforma()
        self.desactivar()
        _, token, _ = helpers.create_superuser_with_token()

        self.assertEqual(self.client.get(f'{PROFORMAS}/{proforma_id}/', **auth(token)).status_code, 200)
        self.assert_conflict(self.client.patch(
            f'{PROFORMAS}/{proforma_id}/', {'name': 'x'}, content_type='application/json', **auth(token)))

    def test_inventory_row_unchanged_when_write_is_rejected(self):
        proforma_id = self.nueva_proforma()
        self.desactivar()
        self.post(f'{PROFORMAS}/{proforma_id}/generar-nota-trabajo/', self.owner_headers)
        inv = inventario.objects.get(pk=self.s['inventario'].pk)
        self.assertEqual(inv.to_install, Decimal('50.00'))
