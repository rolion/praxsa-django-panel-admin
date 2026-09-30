"""Backfill y reverso de la migracion 0111_estados_orden
(ADR-estados-...-maquina-de-estados, decision 4)."""
import importlib
from decimal import Decimal

from django.apps import apps as django_apps
from django.test import TestCase

from . import helpers
from ..models import Nota_trabajo, Nota_Venta, Proforma_Header, pago

migration = importlib.import_module('product.migrations.0111_estados_orden')


class BackfillEstadosTest(TestCase):
    def setUp(self):
        self.user, _ = helpers.create_user_with_token()
        self.sucursal = helpers.create_sucursal(self.user)

    def proforma(self, is_close, discount=Decimal('0')):
        header, _ = helpers.create_full_proforma(user=self.user, sucursal=self.sucursal)
        Proforma_Header.objects.filter(pk=header.pk).update(is_close=is_close, discount=discount, status='nota_trabajo')
        return Proforma_Header.objects.get(pk=header.pk)

    def build_cases(self):
        # A: nota abierta (proforma cerrada, sin nota de venta) -> en_proceso + nota de venta por_cobrar
        self.a = self.proforma(is_close=True, discount=Decimal('20.00'))
        self.nota_a = helpers.create_nota_trabajo(proforma=self.a)
        # B: proforma "abierta" con nota viva (modelo anterior: inventario ya devuelto) -> cancelada, sin nota de venta
        self.b = self.proforma(is_close=False)
        self.nota_b = helpers.create_nota_trabajo(proforma=self.b)
        # C: nota de venta sin pago -> terminado / por_cobrar
        self.c = self.proforma(is_close=True)
        self.nota_c = helpers.create_nota_trabajo(proforma=self.c, is_close=True)
        self.nv_c = helpers.create_nota_venta(self.nota_c, created_by=self.user)
        # D: nota de venta con pago -> terminado / pagada
        self.d = self.proforma(is_close=True)
        self.nota_d = helpers.create_nota_trabajo(proforma=self.d, is_close=True)
        self.nv_d = helpers.create_nota_venta(self.nota_d, created_by=self.user)
        self.pago_d = helpers.create_pago(self.nv_d, created_by=self.user)
        # E: nota de trabajo sin proforma -> se omite
        self.nota_e = Nota_trabajo.objects.create(name='Huerfana', car_plate='X')

    def test_backfill_de_cada_combinacion(self):
        self.build_cases()

        migration.backfill_estados(django_apps, None)

        nota_a = Nota_trabajo.objects.get(pk=self.nota_a.pk)
        self.assertEqual(nota_a.status, 'en_proceso')
        self.assertFalse(nota_a.is_close)
        nv_a = Nota_Venta.objects.get(nota_trabajo=nota_a)
        self.assertEqual(nv_a.status, 'por_cobrar')
        self.assertEqual(nv_a.total_price, self.a.total_price - Decimal('20.00'))
        self.assertEqual(nv_a.created_by, self.user)
        self.assertEqual(Proforma_Header.objects.get(pk=self.a.pk).status, 'en_trabajo')

        nota_b = Nota_trabajo.objects.get(pk=self.nota_b.pk)
        self.assertEqual(nota_b.status, 'cancelada')
        self.assertTrue(nota_b.is_close)
        self.assertFalse(Nota_Venta.objects.filter(nota_trabajo=nota_b).exists())
        header_b = Proforma_Header.objects.get(pk=self.b.pk)
        self.assertEqual(header_b.status, 'proforma')
        self.assertFalse(header_b.is_close)

        self.assertEqual(Nota_trabajo.objects.get(pk=self.nota_c.pk).status, 'terminado')
        self.assertEqual(Nota_Venta.objects.get(pk=self.nv_c.pk).status, 'por_cobrar')
        self.assertEqual(Proforma_Header.objects.get(pk=self.c.pk).status, 'por_cobrar')

        self.assertEqual(Nota_trabajo.objects.get(pk=self.nota_d.pk).status, 'terminado')
        nv_d = Nota_Venta.objects.get(pk=self.nv_d.pk)
        self.assertEqual(nv_d.status, 'pagada')
        self.assertTrue(nv_d.is_close)
        self.assertEqual(Proforma_Header.objects.get(pk=self.d.pk).status, 'finalizado')

        nota_e = Nota_trabajo.objects.get(pk=self.nota_e.pk)
        self.assertEqual(nota_e.status, 'en_proceso')
        self.assertFalse(Nota_Venta.objects.filter(nota_trabajo=nota_e).exists())

    def test_backfill_es_idempotente(self):
        self.build_cases()
        migration.backfill_estados(django_apps, None)
        cantidad = Nota_Venta.objects.count()
        migration.backfill_estados(django_apps, None)
        self.assertEqual(Nota_Venta.objects.count(), cantidad)
        self.assertEqual(Proforma_Header.objects.get(pk=self.d.pk).status, 'finalizado')

    def test_reverso_elimina_solo_las_notas_de_venta_que_el_modelo_anterior_no_conocia(self):
        self.build_cases()
        migration.backfill_estados(django_apps, None)
        creada_por_backfill = Nota_Venta.objects.get(nota_trabajo_id=self.nota_a.pk)

        migration.reverse_estados(django_apps, None)

        self.assertFalse(Nota_Venta.objects.filter(pk=creada_por_backfill.pk).exists())
        self.assertTrue(Nota_Venta.objects.filter(pk=self.nv_c.pk).exists())
        self.assertTrue(Nota_Venta.objects.filter(pk=self.nv_d.pk).exists())
        self.assertTrue(pago.objects.filter(pk=self.pago_d.pk).exists())
        # vocabulario anterior de Proforma_Header.status
        self.assertEqual(Proforma_Header.objects.get(pk=self.a.pk).status, 'nota_trabajo')
        self.assertEqual(Proforma_Header.objects.get(pk=self.c.pk).status, 'por_cobrar')
        self.assertEqual(Proforma_Header.objects.get(pk=self.d.pk).status, 'finalizado')
