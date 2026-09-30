"""Tests del servicio de transiciones de la orden (TASK-estados-proforma-nota-trabajo-nota-venta).

Cubren la tabla de transiciones, el estado global derivado y cada transicion de
Orden_Estado_Business (efectos, precondiciones y retrocesos), mas los delegadores
legados y la paridad con lo que muestran los admins."""
import itertools
from decimal import Decimal

from django.contrib.admin.sites import AdminSite
from django.test import TestCase

from . import helpers
from ..admin_config.nota_trabajo import NotaTrabajoAdmin
from ..admin_config.nota_venta import NotaVentaAdmin
from ..admin_config.proforma_admin import ProformaAdmin
from ..business.orden_estado import Orden_Estado_Business
from ..business.orden_trabajo import Orden_Trabajo_Business
from ..business.pago import Pago_Business
from ..business.proforma import Proforma_Business
from ..helper import estados
from ..models import Nota_trabajo, Nota_Venta, Proforma_Detail, Proforma_Header, instalador, inventario, pago
from ..utils.exception.proforma import OrdenEstadoException, OrdenTrabajo


class OrdenEstadoBase(TestCase):
    def setUp(self):
        self.user, _token = helpers.create_user_with_token()
        self.sucursal = helpers.create_sucursal(self.user)
        self.car_model = helpers.create_model()
        self.car_part = helpers.create_car_part()
        helpers.create_car_model_part(car_model=self.car_model, car_part=self.car_part, width=Decimal('1.50'))
        self.window_film = helpers.create_window_film()
        reel = helpers.create_window_film_reel(window_film=self.window_film, width=Decimal('1.50'))
        self.inv = helpers.create_inventario(sucursal=self.sucursal, bobina=reel, to_install=Decimal('50.00'))
        self.header, self.detail = helpers.create_full_proforma(
            user=self.user, sucursal=self.sucursal, car_model=self.car_model,
            car_part=self.car_part, window_film=self.window_film,
        )
        self.svc = Orden_Estado_Business()

    def to_install(self):
        return inventario.objects.get(pk=self.inv.pk).to_install

    def reload_header(self):
        return Proforma_Header.objects.get(pk=self.header.pk)

    def aprobar(self):
        return self.svc.aprobar_proforma(self.header, self.user)

    def preparar_para_terminar(self, nota):
        nota.codigo_garantia = f'GAR-{nota.pk}'
        nota.instaladar = instalador.objects.create(name='Instalador', address='Calle 1', phonenumber='70000002')
        nota.save()

    def terminar(self, nota):
        self.preparar_para_terminar(nota)
        return self.svc.terminar_trabajo(nota)


class TablaDeTransicionesTest(TestCase):
    def test_solo_las_transiciones_declaradas_estan_permitidas(self):
        nt = [s for s, _ in estados.NT_STATUS_CHOICES]
        nv = [s for s, _ in estados.NV_STATUS_CHOICES]
        for documento, valores in ((estados.DOC_NOTA_TRABAJO, nt), (estados.DOC_NOTA_VENTA, nv)):
            for desde, hasta in itertools.product(valores, valores):
                esperado = (documento, desde, hasta) in estados.TRANSICIONES
                with self.subTest(documento=documento, desde=desde, hasta=hasta):
                    self.assertEqual(estados.transicion_permitida(documento, desde, hasta), esperado)

    def test_transicion_invalida_lanza_excepcion_de_negocio(self):
        svc = Orden_Estado_Business()
        with self.assertRaises(OrdenEstadoException):
            svc._validar(estados.DOC_NOTA_TRABAJO, estados.NT_TERMINADO, estados.NT_CANCELADA)
        with self.assertRaises(OrdenEstadoException):
            svc._validar(estados.DOC_NOTA_VENTA, estados.NV_PAGADA, estados.NV_ANULADA)
        svc._validar(estados.DOC_NOTA_TRABAJO, estados.NT_EN_PROCESO, estados.NT_TERMINADO)


class CalcularEstadoOrdenTest(OrdenEstadoBase):
    def test_sin_nota_de_trabajo_es_proforma(self):
        self.assertEqual(self.svc.calcular_estado_orden(self.header), 'proforma')

    def test_matriz_de_estados_hijos_a_estado_global(self):
        nota = helpers.create_nota_trabajo(proforma=self.header, status=estados.NT_CANCELADA)
        self.assertEqual(self.svc.calcular_estado_orden(self.header), 'proforma')
        nota.status = estados.NT_EN_PROCESO
        nota.save()
        self.assertEqual(self.svc.calcular_estado_orden(self.header), 'en_trabajo')
        nota.status = estados.NT_TERMINADO
        nota.save()
        self.assertEqual(self.svc.calcular_estado_orden(self.header), 'por_cobrar')
        nv = helpers.create_nota_venta(nota, created_by=self.user, status=estados.NV_PAGADA)
        self.assertEqual(self.svc.calcular_estado_orden(self.header), 'finalizado')
        nv.status = estados.NV_POR_COBRAR
        nv.save()
        self.assertEqual(self.svc.calcular_estado_orden(self.header), 'por_cobrar')

    def test_anulada_se_conserva(self):
        self.header.status = 'anulada'
        self.assertEqual(self.svc.calcular_estado_orden(self.header), 'anulada')

    def test_refrescar_no_modifica_proforma_created_on(self):
        antes = self.reload_header().proforma_created_on
        helpers.create_nota_trabajo(proforma=self.header)
        self.svc.refrescar(self.header)
        self.assertEqual(self.reload_header().proforma_created_on, antes)
        self.assertEqual(self.reload_header().status, 'en_trabajo')
        self.assertTrue(self.reload_header().is_close)


class AprobarProformaTest(OrdenEstadoBase):
    def test_crea_nota_de_trabajo_y_nota_de_venta_y_descuenta_inventario(self):
        self.header.discount = Decimal('20.00')
        self.header.save()

        nota = self.aprobar()

        self.assertEqual(nota.status, estados.NT_EN_PROCESO)
        self.assertFalse(nota.is_close)
        self.assertIsNotNone(nota.entrada_vehiculo)
        self.assertEqual(nota.responsable, self.user)
        nv = Nota_Venta.objects.get(nota_trabajo=nota)
        self.assertEqual(nv.status, estados.NV_POR_COBRAR)
        self.assertEqual(nv.total_price, self.header.total_price - Decimal('20.00'))
        self.assertEqual(nv.created_by, self.user)
        self.assertFalse(nv.is_close)
        header = self.reload_header()
        self.assertEqual(header.status, 'en_trabajo')
        self.assertTrue(header.is_close)
        self.assertEqual(self.to_install(), Decimal('49.00'))

    def test_aprobar_dos_veces_falla_sin_efectos(self):
        self.aprobar()
        with self.assertRaises(OrdenEstadoException):
            self.aprobar()
        self.assertEqual(self.to_install(), Decimal('49.00'))
        self.assertEqual(Nota_Venta.objects.count(), 1)

    def test_sin_stock_no_deja_cambios_parciales(self):
        self.inv.to_install = Decimal('0.50')
        self.inv.save()
        with self.assertRaises(Exception):
            self.aprobar()
        self.assertEqual(Nota_trabajo.objects.count(), 0)
        self.assertEqual(Nota_Venta.objects.count(), 0)
        self.assertEqual(self.reload_header().status, 'proforma')

    def test_reaprobar_tras_anular_reutiliza_documentos_y_refresca_el_total(self):
        nota = self.aprobar()
        nv = Nota_Venta.objects.get(nota_trabajo=nota)
        self.svc.anular_nota_trabajo(nota)
        Proforma_Header.objects.filter(pk=self.header.pk).update(total_price=Decimal('300.00'))
        self.header.refresh_from_db()

        nota2 = self.aprobar()

        self.assertEqual(nota2.pk, nota.pk)
        nv2 = Nota_Venta.objects.get(nota_trabajo=nota2)
        self.assertEqual(nv2.pk, nv.pk)
        self.assertEqual(nv2.status, estados.NV_POR_COBRAR)
        self.assertEqual(nv2.total_price, Decimal('300.00'))
        self.assertEqual(nota2.status, estados.NT_EN_PROCESO)
        self.assertIsNone(nota2.salida_vehiculo)
        self.assertEqual(self.to_install(), Decimal('49.00'))
        self.assertEqual(self.reload_header().status, 'en_trabajo')

    def test_proforma_anulada_no_se_puede_aprobar(self):
        self.svc.anular_proforma(self.header)
        with self.assertRaises(OrdenEstadoException):
            self.aprobar()


class TrabajoTest(OrdenEstadoBase):
    def setUp(self):
        super().setUp()
        self.nota = self.aprobar()

    def test_terminar_exige_garantia_e_instalador_en_venta_con_instalacion(self):
        with self.assertRaisesRegex(OrdenEstadoException, 'Garantía'):
            self.svc.terminar_trabajo(self.nota)
        self.nota.codigo_garantia = 'GAR-1'
        self.nota.save()
        with self.assertRaisesRegex(OrdenEstadoException, 'Instalador'):
            self.svc.terminar_trabajo(self.nota)
        self.assertEqual(Nota_trabajo.objects.get(pk=self.nota.pk).status, estados.NT_EN_PROCESO)

    def test_terminar_fija_estado_salida_y_estado_global(self):
        self.terminar(self.nota)

        nota = Nota_trabajo.objects.get(pk=self.nota.pk)
        self.assertEqual(nota.status, estados.NT_TERMINADO)
        self.assertTrue(nota.is_close)
        self.assertIsNotNone(nota.salida_vehiculo)
        self.assertEqual(Nota_Venta.objects.get(nota_trabajo=nota).status, estados.NV_POR_COBRAR)
        self.assertEqual(self.reload_header().status, 'por_cobrar')

    def test_terminar_en_metro_lineal_no_exige_garantia_ni_instalador(self):
        Proforma_Header.objects.filter(pk=self.header.pk).update(sales_type='venta_metro_lineal')
        self.svc.terminar_trabajo(self.nota)
        self.assertEqual(Nota_trabajo.objects.get(pk=self.nota.pk).status, estados.NT_TERMINADO)

    def test_terminar_dos_veces_falla(self):
        self.terminar(self.nota)
        with self.assertRaises(OrdenEstadoException):
            self.svc.terminar_trabajo(self.nota)

    def test_corregir_vuelve_a_en_proceso(self):
        self.terminar(self.nota)
        self.svc.corregir_trabajo(self.nota)
        self.assertEqual(Nota_trabajo.objects.get(pk=self.nota.pk).status, estados.NT_EN_PROCESO)
        self.assertFalse(Nota_trabajo.objects.get(pk=self.nota.pk).is_close)
        self.assertEqual(self.reload_header().status, 'en_trabajo')

    def test_corregir_una_nota_en_proceso_falla(self):
        with self.assertRaises(OrdenEstadoException):
            self.svc.corregir_trabajo(self.nota)

    def test_corregir_con_pago_falla(self):
        self.terminar(self.nota)
        nv = Nota_Venta.objects.get(nota_trabajo=self.nota)
        self.svc.registrar_pago(nv, self.user, 'efec')
        with self.assertRaisesRegex(OrdenEstadoException, 'pago'):
            self.svc.corregir_trabajo(self.nota)


class PagoTest(OrdenEstadoBase):
    def setUp(self):
        super().setUp()
        self.nota = self.aprobar()
        self.nv = Nota_Venta.objects.get(nota_trabajo=self.nota)

    def test_no_se_puede_pagar_con_el_trabajo_en_proceso(self):
        with self.assertRaisesRegex(OrdenEstadoException, 'terminado'):
            self.svc.registrar_pago(self.nv, self.user, 'efec')
        self.assertEqual(pago.objects.count(), 0)
        self.assertEqual(Nota_Venta.objects.get(pk=self.nv.pk).status, estados.NV_POR_COBRAR)

    def test_registrar_pago_fija_monto_del_servidor_y_finaliza(self):
        self.terminar(self.nota)

        registrado = self.svc.registrar_pago(self.nv, self.user, 'trans', '1234/26')

        self.assertEqual(registrado.monto, self.nv.total_price)
        self.assertEqual(registrado.tipo_pago, 'trans')
        self.assertEqual(registrado.registro_contable, '1234/26')
        self.assertFalse(registrado.cerrado)
        self.assertEqual(registrado.created_by, self.user)
        nv = Nota_Venta.objects.get(pk=self.nv.pk)
        self.assertEqual(nv.status, estados.NV_PAGADA)
        self.assertTrue(nv.is_close)
        self.assertEqual(self.reload_header().status, 'finalizado')

    def test_monto_del_cliente_se_ignora(self):
        self.terminar(self.nota)
        nuevo = pago(nota_venta=self.nv, tipo_pago='efec', monto=Decimal('1.00'))
        registrado = self.svc.registrar_pago_instancia(nuevo, self.user)
        self.assertEqual(registrado.monto, self.nv.total_price)

    def test_no_hay_doble_pago(self):
        self.terminar(self.nota)
        self.svc.registrar_pago(self.nv, self.user, 'efec')
        with self.assertRaises(OrdenEstadoException):
            self.svc.registrar_pago(self.nv, self.user, 'efec')
        self.assertEqual(pago.objects.count(), 1)

    def test_registro_contable_repetido_se_rechaza_sin_dejar_la_nota_pagada(self):
        otro = helpers.create_full_pago_chain(self.user, sucursal=self.sucursal)
        pago.objects.filter(pk=otro['pago'].pk).update(registro_contable='1234/26')
        self.terminar(self.nota)
        with self.assertRaisesRegex(OrdenEstadoException, 'registro contable'):
            self.svc.registrar_pago(self.nv, self.user, 'efec', '1234/26')
        self.assertEqual(Nota_Venta.objects.get(pk=self.nv.pk).status, estados.NV_POR_COBRAR)

    def test_anular_pago_vuelve_a_por_cobrar(self):
        self.terminar(self.nota)
        registrado = self.svc.registrar_pago(self.nv, self.user, 'efec')

        self.svc.anular_pago(registrado)

        self.assertFalse(pago.objects.filter(nota_venta=self.nv).exists())
        nv = Nota_Venta.objects.get(pk=self.nv.pk)
        self.assertEqual(nv.status, estados.NV_POR_COBRAR)
        self.assertFalse(nv.is_close)
        self.assertEqual(self.reload_header().status, 'por_cobrar')

    def test_pago_cerrado_no_se_anula(self):
        self.terminar(self.nota)
        registrado = self.svc.registrar_pago(self.nv, self.user, 'efec')
        self.svc.cerrar_pago(registrado)
        with self.assertRaisesRegex(OrdenEstadoException, 'cerrado'):
            self.svc.anular_pago(registrado)
        self.assertTrue(pago.objects.filter(nota_venta=self.nv).exists())

    def test_cerrar_pago_solo_cambia_el_flag(self):
        self.terminar(self.nota)
        registrado = self.svc.registrar_pago(self.nv, self.user, 'efec')

        Pago_Business().cerrar_pago(registrado)

        self.assertTrue(pago.objects.get(pk=registrado.pk).cerrado)
        self.assertEqual(Nota_Venta.objects.get(pk=self.nv.pk).status, estados.NV_PAGADA)
        self.assertEqual(self.reload_header().status, 'finalizado')


class AnulacionesTest(OrdenEstadoBase):
    def setUp(self):
        super().setUp()
        self.nota = self.aprobar()
        self.nv = Nota_Venta.objects.get(nota_trabajo=self.nota)

    def assert_orden_cancelada(self):
        self.assertEqual(Nota_trabajo.objects.get(pk=self.nota.pk).status, estados.NT_CANCELADA)
        self.assertEqual(Nota_Venta.objects.get(pk=self.nv.pk).status, estados.NV_ANULADA)
        self.assertEqual(self.to_install(), Decimal('50.00'))
        self.assertIsNone(Proforma_Detail.objects.get(pk=self.detail.pk).inventario)
        header = self.reload_header()
        self.assertEqual(header.status, 'proforma')
        self.assertFalse(header.is_close)

    def test_anular_nota_de_trabajo_equivale_a_reabrir(self):
        self.svc.anular_nota_trabajo(self.nota)
        self.assert_orden_cancelada()

    def test_anular_nota_de_venta_hace_lo_mismo(self):
        self.svc.anular_nota_venta(self.nv)
        self.assert_orden_cancelada()

    def test_con_el_trabajo_terminado_no_se_puede_anular(self):
        self.terminar_nota()
        with self.assertRaisesRegex(OrdenEstadoException, 'terminado'):
            self.svc.anular_nota_trabajo(self.nota)
        with self.assertRaisesRegex(OrdenEstadoException, 'terminado'):
            self.svc.anular_nota_venta(self.nv)
        self.assertEqual(self.to_install(), Decimal('49.00'))

    def test_nota_de_venta_pagada_pide_anular_el_pago(self):
        self.terminar_nota()
        self.svc.registrar_pago(self.nv, self.user, 'efec')
        with self.assertRaisesRegex(OrdenEstadoException, 'pago'):
            self.svc.anular_nota_venta(self.nv)
        with self.assertRaises(OrdenEstadoException):
            self.svc.anular_nota_trabajo(self.nota)

    def test_anular_dos_veces_falla(self):
        self.svc.anular_nota_trabajo(self.nota)
        with self.assertRaises(OrdenEstadoException):
            self.svc.anular_nota_trabajo(self.nota)
        with self.assertRaises(OrdenEstadoException):
            self.svc.anular_nota_venta(self.nv)

    def terminar_nota(self):
        self.preparar_para_terminar(self.nota)
        self.svc.terminar_trabajo(self.nota)


class AnularProformaTest(OrdenEstadoBase):
    def test_anula_una_proforma_vigente(self):
        self.svc.anular_proforma(self.header)
        header = self.reload_header()
        self.assertEqual(header.status, 'anulada')
        self.assertTrue(header.is_close)

    def test_no_anula_una_proforma_aprobada(self):
        self.aprobar()
        with self.assertRaises(OrdenEstadoException):
            self.svc.anular_proforma(self.header)

    def test_se_puede_anular_tras_reabrir(self):
        nota = self.aprobar()
        self.svc.anular_nota_trabajo(nota)
        self.svc.anular_proforma(self.header)
        self.assertEqual(self.reload_header().status, 'anulada')


class EliminarNotaDeTrabajoTest(OrdenEstadoBase):
    def test_eliminar_en_proceso_devuelve_inventario_y_borra_la_nota_de_venta(self):
        nota = self.aprobar()
        Orden_Trabajo_Business().delete_work_note(nota)
        self.assertEqual(Nota_trabajo.objects.count(), 0)
        self.assertEqual(Nota_Venta.objects.count(), 0)
        self.assertEqual(self.to_install(), Decimal('50.00'))
        self.assertEqual(self.reload_header().status, 'proforma')

    def test_eliminar_una_nota_cancelada_no_falla_ni_devuelve_dos_veces(self):
        nota = self.aprobar()
        self.svc.anular_nota_trabajo(nota)
        Orden_Trabajo_Business().delete_work_note(nota)
        self.assertEqual(Nota_trabajo.objects.count(), 0)
        self.assertEqual(self.to_install(), Decimal('50.00'))

    def test_no_se_elimina_con_nota_de_venta_pagada(self):
        nota = self.aprobar()
        self.preparar_para_terminar(nota)
        self.svc.terminar_trabajo(nota)
        nv = Nota_Venta.objects.get(nota_trabajo=nota)
        self.svc.registrar_pago(nv, self.user, 'efec')
        with self.assertRaises(OrdenTrabajo):
            Orden_Trabajo_Business().delete_work_note(nota)
        self.assertEqual(Nota_trabajo.objects.count(), 1)

    def test_no_se_elimina_una_nota_terminada(self):
        nota = self.aprobar()
        self.preparar_para_terminar(nota)
        self.svc.terminar_trabajo(nota)
        with self.assertRaises(OrdenTrabajo):
            Orden_Trabajo_Business().delete_work_note(nota)
        self.assertEqual(self.to_install(), Decimal('49.00'))


class DelegadoresLegadosYAdminsTest(OrdenEstadoBase):
    def test_proforma_business_delega_en_el_servicio(self):
        business = Proforma_Business()
        nota = business.create_work_note(proforma=self.header, responsable=self.user)
        self.assertEqual(self.header.status, 'en_trabajo')
        business.abrir_proforma(proforma=self.header)
        self.assertEqual(Nota_trabajo.objects.get(pk=nota.pk).status, estados.NT_CANCELADA)
        self.assertEqual(self.reload_header().status, 'proforma')

    def test_los_admins_muestran_el_estado_persistido(self):
        proforma_admin = ProformaAdmin(Proforma_Header, AdminSite())
        nota_admin = NotaTrabajoAdmin(Nota_trabajo, AdminSite())
        venta_admin = NotaVentaAdmin(Nota_Venta, AdminSite())

        self.assertEqual(proforma_admin.get_estado(self.reload_header()), 'Proforma')
        nota = self.aprobar()
        nv = Nota_Venta.objects.get(nota_trabajo=nota)
        self.assertEqual(proforma_admin.get_estado(self.reload_header()), 'En trabajo')
        self.assertEqual(nota_admin.get_estado(nota), 'En proceso')
        self.assertEqual(venta_admin.get_estado(nv), 'Por cobrar')
        self.terminar(nota)
        self.assertEqual(proforma_admin.get_estado(self.reload_header()), 'Por Cobrar')
        self.assertEqual(nota_admin.get_estado(Nota_trabajo.objects.get(pk=nota.pk)), 'Terminado')
        self.svc.registrar_pago(nv, self.user, 'efec')
        self.assertEqual(proforma_admin.get_estado(self.reload_header()), 'Finalizado')
        self.assertEqual(venta_admin.get_estado(Nota_Venta.objects.get(pk=nv.pk)), 'Pagada')
