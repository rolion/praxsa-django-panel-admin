"""Acciones de Django Admin re-cableadas al servicio de estados
(TASK-estados-proforma-nota-trabajo-nota-venta, plan Fase 3)."""
from decimal import Decimal
from unittest import mock

from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory

from . import helpers
from .test_orden_estado_service import OrdenEstadoBase
from ..admin_config.nota_trabajo import NotaTrabajoAdmin
from ..admin_config.nota_venta import NotaVentaAdmin
from ..admin_config.pagos import PagosAdmin
from ..admin_config.proforma_admin import ProformaAdmin
from ..Forms.pagos import PagosForm
from ..helper import estados
from ..models import Nota_trabajo, Nota_Venta, Proforma_Header, pago


class AdminAccionesTest(OrdenEstadoBase):
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.site = AdminSite()

    def request(self, path='/', **params):
        request = self.factory.get(path, params)
        request.user = self.user
        return request

    def test_accion_crear_nota_trabajo_aprueba_la_proforma(self):
        admin = ProformaAdmin(Proforma_Header, self.site)
        admin.create_work_note(self.request(), Proforma_Header.objects.filter(pk=self.header.pk))
        nota = Nota_trabajo.objects.get(proforma=self.header)
        self.assertEqual(nota.status, estados.NT_EN_PROCESO)
        self.assertEqual(Nota_Venta.objects.get(nota_trabajo=nota).status, estados.NV_POR_COBRAR)

    def test_accion_repetida_informa_el_error_sin_duplicar_inventario(self):
        admin = ProformaAdmin(Proforma_Header, self.site)
        queryset = Proforma_Header.objects.filter(pk=self.header.pk)
        admin.create_work_note(self.request(), queryset)
        with mock.patch.object(admin, 'message_user') as message_user:
            admin.create_work_note(self.request(), Proforma_Header.objects.filter(pk=self.header.pk))
        self.assertTrue(message_user.called)
        self.assertEqual(self.to_install(), Decimal('49.00'))

    def test_accion_abrir_proforma_anula_la_nota_de_trabajo(self):
        nota = self.aprobar()
        admin = ProformaAdmin(Proforma_Header, self.site)
        admin.open_proforma(self.request(), Proforma_Header.objects.filter(pk=self.header.pk))
        self.assertEqual(Nota_trabajo.objects.get(pk=nota.pk).status, estados.NT_CANCELADA)
        self.assertEqual(self.reload_header().status, 'proforma')

    def test_accion_anular_proforma(self):
        admin = ProformaAdmin(Proforma_Header, self.site)
        admin.anular_proforma(self.request(), Proforma_Header.objects.filter(pk=self.header.pk))
        self.assertEqual(self.reload_header().status, 'anulada')

    def test_accion_marcar_trabajo_terminado(self):
        nota = self.aprobar()
        self.preparar_para_terminar(nota)
        admin = NotaTrabajoAdmin(Nota_trabajo, self.site)
        admin.terminar_trabajo(self.request(), Nota_trabajo.objects.filter(pk=nota.pk))
        self.assertEqual(Nota_trabajo.objects.get(pk=nota.pk).status, estados.NT_TERMINADO)

    def test_accion_anular_nota_de_venta(self):
        nota = self.aprobar()
        nv = Nota_Venta.objects.get(nota_trabajo=nota)
        NotaVentaAdmin(Nota_Venta, self.site).anular_nota_venta(self.request(), Nota_Venta.objects.filter(pk=nv.pk))
        self.assertEqual(Nota_Venta.objects.get(pk=nv.pk).status, estados.NV_ANULADA)
        self.assertEqual(self.reload_header().status, 'proforma')


class AdminPagosTest(OrdenEstadoBase):
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.admin = PagosAdmin(pago, AdminSite())
        self.nota = self.aprobar()
        self.nv = Nota_Venta.objects.get(nota_trabajo=self.nota)

    def request(self, **params):
        request = self.factory.get('/admin/product/pago/add/', params)
        request.user = self.user
        return request

    def test_alta_de_pago_por_admin_usa_el_servicio_y_fija_el_monto(self):
        self.terminar(self.nota)
        nuevo = pago(nota_venta=self.nv, tipo_pago='efec', monto=Decimal('1.00'))

        self.admin.save_model(self.request(nota_venta=self.nv.pk), nuevo, form=None, change=False)

        self.assertIsNotNone(nuevo.pk)
        self.assertEqual(pago.objects.get(pk=nuevo.pk).monto, self.nv.total_price)
        self.assertEqual(Nota_Venta.objects.get(pk=self.nv.pk).status, estados.NV_PAGADA)
        self.assertEqual(self.reload_header().status, 'finalizado')

    def test_formulario_rechaza_el_pago_con_el_trabajo_en_proceso(self):
        form = PagosForm({'tipo_pago': 'efec', 'monto': '100'}, nota_venta_init=self.nv.pk)
        self.assertFalse(form.is_valid())
        self.assertIn('terminado', ' '.join(form.non_field_errors()))

    def test_concluir_transaccion_solo_cierra_el_pago(self):
        self.terminar(self.nota)
        registrado = self.svc.registrar_pago(self.nv, self.user, 'efec')
        self.admin.concluir_transaccion(self.request(), pago.objects.filter(pk=registrado.pk))
        self.assertTrue(pago.objects.get(pk=registrado.pk).cerrado)
        self.assertEqual(Nota_Venta.objects.get(pk=self.nv.pk).status, estados.NV_PAGADA)

    def test_eliminar_pago_desde_admin_lo_anula(self):
        self.terminar(self.nota)
        registrado = self.svc.registrar_pago(self.nv, self.user, 'efec')
        self.admin.delete_model(self.request(), registrado)
        self.assertFalse(pago.objects.filter(nota_venta=self.nv).exists())
        self.assertEqual(Nota_Venta.objects.get(pk=self.nv.pk).status, estados.NV_POR_COBRAR)
        self.assertEqual(self.reload_header().status, 'por_cobrar')
