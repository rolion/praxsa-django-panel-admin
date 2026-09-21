"""Tests de TASK-002 (backlog #10, SEC-06): filtrado por sucursal en Pagos/Reportes
del admin. Cubre la capa business/helper (unitarios) y el wiring de cada
ModelAdmin.get_queryset afectado (integración)."""
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory, TestCase

from . import helpers
from ..admin_config.pagos import PagosAdmin
from ..admin_config.report_daily_sell import ReportDailySellAdmin
from ..admin_config.report_nota_trabajo import ReportNotaTrabajoAdmin
from ..admin_config.report_storage import ReportStorageAdmin
from ..admin_config.report_utilidad import ReportUtilidadAdmin
from ..business.inventario import Inventario_Business
from ..business.orden_trabajo import Orden_Trabajo_Business
from ..business.pago import Pago_Business
from ..helper.user import User_Helper
from ..models import (
    Proxy_Nota_trabajo,
    Proxy_Pagos,
    inventario_proxy,
    pago,
    utilidades,
)


class CanViewAllSucursalesTest(TestCase):
    helper = User_Helper()

    def test_admin_ve_todo(self):
        user, _ = helpers.create_user_with_token()
        helpers.add_user_to_group(user, 'Admin')
        self.assertTrue(self.helper.can_view_all_sucursales(user))

    def test_caja_ve_todo(self):
        user, _ = helpers.create_user_with_token()
        helpers.add_user_to_group(user, 'Caja')
        self.assertTrue(self.helper.can_view_all_sucursales(user))

    def test_supervisor_no_ve_todo(self):
        user, _ = helpers.create_user_with_token()
        helpers.add_user_to_group(user, 'Supervisor')
        self.assertFalse(self.helper.can_view_all_sucursales(user))

    def test_sin_grupo_no_ve_todo(self):
        user, _ = helpers.create_user_with_token()
        self.assertFalse(self.helper.can_view_all_sucursales(user))


class PagoBusinessQuerysetByRoleTest(TestCase):
    business = Pago_Business()

    def test_admin_ve_pagos_de_todas_las_sucursales(self):
        admin_user, _ = helpers.create_user_with_token()
        helpers.add_user_to_group(admin_user, 'Admin')
        owner_a, _ = helpers.create_user_with_token()
        sucursal_a = helpers.create_sucursal(owner_a)
        owner_b, _ = helpers.create_user_with_token()
        sucursal_b = helpers.create_sucursal(owner_b)
        chain_a = helpers.create_full_pago_chain(owner_a, sucursal=sucursal_a)
        chain_b = helpers.create_full_pago_chain(owner_b, sucursal=sucursal_b)

        result = self.business.get_pago_queryset_by_role(user=admin_user, qs=pago.objects.all())

        ids = set(result.values_list('id', flat=True))
        self.assertEqual(ids, {chain_a['pago'].id, chain_b['pago'].id})

    def test_caja_ve_pagos_de_todas_las_sucursales(self):
        caja_user, _ = helpers.create_user_with_token()
        helpers.add_user_to_group(caja_user, 'Caja')
        owner_a, _ = helpers.create_user_with_token()
        sucursal_a = helpers.create_sucursal(owner_a)
        owner_b, _ = helpers.create_user_with_token()
        sucursal_b = helpers.create_sucursal(owner_b)
        chain_a = helpers.create_full_pago_chain(owner_a, sucursal=sucursal_a)
        chain_b = helpers.create_full_pago_chain(owner_b, sucursal=sucursal_b)

        result = self.business.get_pago_queryset_by_role(user=caja_user, qs=pago.objects.all())

        ids = set(result.values_list('id', flat=True))
        self.assertEqual(ids, {chain_a['pago'].id, chain_b['pago'].id})

    def test_usuario_con_sucursal_solo_ve_la_propia(self):
        owner_a, _ = helpers.create_user_with_token()
        sucursal_a = helpers.create_sucursal(owner_a)
        owner_b, _ = helpers.create_user_with_token()
        sucursal_b = helpers.create_sucursal(owner_b)
        chain_a = helpers.create_full_pago_chain(owner_a, sucursal=sucursal_a)
        helpers.create_full_pago_chain(owner_b, sucursal=sucursal_b)

        result = self.business.get_pago_queryset_by_role(user=owner_a, qs=pago.objects.all())

        ids = set(result.values_list('id', flat=True))
        self.assertEqual(ids, {chain_a['pago'].id})

    def test_sin_sucursal_y_sin_rol_devuelve_none(self):
        user, _ = helpers.create_user_with_token()

        result = self.business.get_pago_queryset_by_role(user=user, qs=pago.objects.all())

        self.assertIsNone(result)


class InventarioBusinessQuerysetByRoleTest(TestCase):
    business = Inventario_Business()

    def test_admin_ve_inventario_de_todas_las_sucursales(self):
        admin_user, _ = helpers.create_user_with_token()
        helpers.add_user_to_group(admin_user, 'Admin')
        owner_a, _ = helpers.create_user_with_token()
        sucursal_a = helpers.create_sucursal(owner_a)
        owner_b, _ = helpers.create_user_with_token()
        sucursal_b = helpers.create_sucursal(owner_b)
        inv_a = helpers.create_inventario(sucursal=sucursal_a)
        inv_b = helpers.create_inventario(sucursal=sucursal_b)

        result = self.business.get_inventario_queryset_by_role(user=admin_user, qs=inventario_proxy.objects.all())

        ids = set(result.values_list('id', flat=True))
        self.assertEqual(ids, {inv_a.id, inv_b.id})

    def test_caja_ve_inventario_de_todas_las_sucursales(self):
        caja_user, _ = helpers.create_user_with_token()
        helpers.add_user_to_group(caja_user, 'Caja')
        owner_a, _ = helpers.create_user_with_token()
        sucursal_a = helpers.create_sucursal(owner_a)
        owner_b, _ = helpers.create_user_with_token()
        sucursal_b = helpers.create_sucursal(owner_b)
        inv_a = helpers.create_inventario(sucursal=sucursal_a)
        inv_b = helpers.create_inventario(sucursal=sucursal_b)

        result = self.business.get_inventario_queryset_by_role(user=caja_user, qs=utilidades.objects.all())

        ids = set(result.values_list('id', flat=True))
        self.assertEqual(ids, {inv_a.id, inv_b.id})

    def test_usuario_con_sucursal_solo_ve_la_propia(self):
        owner_a, _ = helpers.create_user_with_token()
        sucursal_a = helpers.create_sucursal(owner_a)
        owner_b, _ = helpers.create_user_with_token()
        sucursal_b = helpers.create_sucursal(owner_b)
        inv_a = helpers.create_inventario(sucursal=sucursal_a)
        helpers.create_inventario(sucursal=sucursal_b)

        result = self.business.get_inventario_queryset_by_role(user=owner_a, qs=inventario_proxy.objects.all())

        ids = set(result.values_list('id', flat=True))
        self.assertEqual(ids, {inv_a.id})

    def test_sin_sucursal_y_sin_rol_devuelve_none(self):
        user, _ = helpers.create_user_with_token()

        result = self.business.get_inventario_queryset_by_role(user=user, qs=inventario_proxy.objects.all())

        self.assertIsNone(result)


class OrdenTrabajoBusinessFinishNotaQuerysetTest(TestCase):
    business = Orden_Trabajo_Business()

    def test_admin_ve_notas_de_todas_las_sucursales(self):
        admin_user, _ = helpers.create_user_with_token()
        helpers.add_user_to_group(admin_user, 'Admin')
        owner_a, _ = helpers.create_user_with_token()
        sucursal_a = helpers.create_sucursal(owner_a)
        owner_b, _ = helpers.create_user_with_token()
        sucursal_b = helpers.create_sucursal(owner_b)
        chain_a = helpers.create_full_pago_chain(owner_a, sucursal=sucursal_a)
        chain_b = helpers.create_full_pago_chain(owner_b, sucursal=sucursal_b)

        result = self.business.get_finish_nota_queryset(user=admin_user, qs=Proxy_Nota_trabajo.objects.all())

        ids = set(result.values_list('id', flat=True))
        self.assertEqual(ids, {chain_a['nota_trabajo'].id, chain_b['nota_trabajo'].id})

    def test_caja_ve_notas_de_todas_las_sucursales(self):
        caja_user, _ = helpers.create_user_with_token()
        helpers.add_user_to_group(caja_user, 'Caja')
        owner_a, _ = helpers.create_user_with_token()
        sucursal_a = helpers.create_sucursal(owner_a)
        owner_b, _ = helpers.create_user_with_token()
        sucursal_b = helpers.create_sucursal(owner_b)
        chain_a = helpers.create_full_pago_chain(owner_a, sucursal=sucursal_a)
        chain_b = helpers.create_full_pago_chain(owner_b, sucursal=sucursal_b)

        result = self.business.get_finish_nota_queryset(user=caja_user, qs=Proxy_Nota_trabajo.objects.all())

        ids = set(result.values_list('id', flat=True))
        self.assertEqual(ids, {chain_a['nota_trabajo'].id, chain_b['nota_trabajo'].id})

    def test_usuario_con_sucursal_solo_ve_la_propia(self):
        owner_a, _ = helpers.create_user_with_token()
        sucursal_a = helpers.create_sucursal(owner_a)
        owner_b, _ = helpers.create_user_with_token()
        sucursal_b = helpers.create_sucursal(owner_b)
        chain_a = helpers.create_full_pago_chain(owner_a, sucursal=sucursal_a)
        helpers.create_full_pago_chain(owner_b, sucursal=sucursal_b)

        result = self.business.get_finish_nota_queryset(user=owner_a, qs=Proxy_Nota_trabajo.objects.all())

        ids = set(result.values_list('id', flat=True))
        self.assertEqual(ids, {chain_a['nota_trabajo'].id})

    def test_sin_sucursal_y_sin_rol_devuelve_none(self):
        user, _ = helpers.create_user_with_token()

        result = self.business.get_finish_nota_queryset(user=user, qs=Proxy_Nota_trabajo.objects.all())

        self.assertIsNone(result)


class AdminGetQuerysetWiringTest(TestCase):
    """Integración: instancia cada ModelAdmin real y verifica que su get_queryset
    no filtre por accidente (o deje de filtrar) — no alcanza con probar solo
    la capa business/, porque el bug más probable de este cambio es olvidar
    conectar el admin al método nuevo."""

    def setUp(self):
        self.factory = RequestFactory()
        self.site = AdminSite()

    def _request_for(self, user):
        request = self.factory.get('/admin/')
        request.user = user
        return request

    def test_pagos_admin_filtra_por_sucursal(self):
        owner_a, _ = helpers.create_user_with_token()
        sucursal_a = helpers.create_sucursal(owner_a)
        owner_b, _ = helpers.create_user_with_token()
        sucursal_b = helpers.create_sucursal(owner_b)
        chain_a = helpers.create_full_pago_chain(owner_a, sucursal=sucursal_a)
        helpers.create_full_pago_chain(owner_b, sucursal=sucursal_b)

        model_admin = PagosAdmin(model=pago, admin_site=self.site)
        result = model_admin.get_queryset(self._request_for(owner_a))

        ids = set(result.values_list('id', flat=True))
        self.assertEqual(ids, {chain_a['pago'].id})

    def test_report_daily_sell_admin_filtra_por_sucursal(self):
        owner_a, _ = helpers.create_user_with_token()
        sucursal_a = helpers.create_sucursal(owner_a)
        owner_b, _ = helpers.create_user_with_token()
        sucursal_b = helpers.create_sucursal(owner_b)
        chain_a = helpers.create_full_pago_chain(owner_a, sucursal=sucursal_a)
        helpers.create_full_pago_chain(owner_b, sucursal=sucursal_b)

        model_admin = ReportDailySellAdmin(model=Proxy_Pagos, admin_site=self.site)
        result = model_admin.get_queryset(self._request_for(owner_a))

        ids = set(result.values_list('id', flat=True))
        self.assertEqual(ids, {chain_a['pago'].id})

    def test_report_storage_admin_filtra_qs_y_aggregated_result(self):
        owner_a, _ = helpers.create_user_with_token()
        sucursal_a = helpers.create_sucursal(owner_a)
        owner_b, _ = helpers.create_user_with_token()
        sucursal_b = helpers.create_sucursal(owner_b)
        inv_a = helpers.create_inventario(sucursal=sucursal_a)
        helpers.create_inventario(sucursal=sucursal_b)

        model_admin = ReportStorageAdmin(model=inventario_proxy, admin_site=self.site)
        result = model_admin.get_queryset(self._request_for(owner_a))

        ids = set(result.values_list('id', flat=True))
        self.assertEqual(ids, {inv_a.id})
        aggregated_sucursales = {row['sucursal__id'] for row in model_admin.aggregated_result}
        self.assertEqual(aggregated_sucursales, {sucursal_a.id})

    def test_report_utilidad_admin_filtra_por_sucursal(self):
        # ReportUtilidadAdmin solo computa utilidad sobre inventario con un
        # detalle de proforma ya vendido (nota_venta existente) -- por eso
        # se arma la cadena completa en vez de un `inventario` suelto.
        owner_a, _ = helpers.create_user_with_token()
        sucursal_a = helpers.create_sucursal(owner_a)
        owner_b, _ = helpers.create_user_with_token()
        sucursal_b = helpers.create_sucursal(owner_b)
        inv_a = helpers.create_inventario(sucursal=sucursal_a)
        inv_b = helpers.create_inventario(sucursal=sucursal_b)
        helpers.create_full_pago_chain(owner_a, sucursal=sucursal_a, inventario=inv_a)
        helpers.create_full_pago_chain(owner_b, sucursal=sucursal_b, inventario=inv_b)

        model_admin = ReportUtilidadAdmin(model=utilidades, admin_site=self.site)
        result = model_admin.get_queryset(self._request_for(owner_a))

        ids = set(result.values_list('id', flat=True))
        self.assertEqual(ids, {inv_a.id})

    def test_report_nota_trabajo_admin_filtra_por_sucursal(self):
        owner_a, _ = helpers.create_user_with_token()
        sucursal_a = helpers.create_sucursal(owner_a)
        owner_b, _ = helpers.create_user_with_token()
        sucursal_b = helpers.create_sucursal(owner_b)
        chain_a = helpers.create_full_pago_chain(owner_a, sucursal=sucursal_a)
        helpers.create_full_pago_chain(owner_b, sucursal=sucursal_b)

        model_admin = ReportNotaTrabajoAdmin(model=Proxy_Nota_trabajo, admin_site=self.site)
        result = model_admin.get_queryset(self._request_for(owner_a))

        ids = set(result.values_list('id', flat=True))
        self.assertEqual(ids, {chain_a['nota_trabajo'].id})
