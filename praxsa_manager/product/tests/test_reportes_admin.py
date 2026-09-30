"""Reportes Ventas Diaria y Utilidades en Django Admin: solo lectura real, columnas
calculadas por pagina y totales del filtro (TASK-reportes-utilidad-ventas-diarias)."""
from datetime import datetime
from decimal import Decimal

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.urls import reverse

from ..admin_config.report_daily_sell import ReportDailySellAdmin
from ..admin_config.report_utilidad import ReportUtilidadAdmin
from ..models import Proxy_Pagos, utilidades
from . import helpers
from .reportes_helpers import METRO_LINEAL, create_venta_cobrada, linea


class ReportesAdminTest(TestCase):

    def setUp(self):
        self.superuser = User.objects.create_superuser('root@test.com', 'root@test.com', 'pw12345678')
        self.owner, _ = helpers.create_user_with_token()
        self.sucursal = helpers.create_sucursal(self.owner)
        self.inv = helpers.create_inventario(sucursal=self.sucursal, precio_compra_mtr_lineal=Decimal('80.00'))
        helpers.add_user_to_group(self.superuser, 'Admin')  # el alcance total lo da el grupo Admin
        self.client.force_login(self.superuser)

    def venta(self, **kwargs):
        return create_venta_cobrada(self.owner, self.sucursal, pagado_en=datetime.now(), **kwargs)

    # -- Ventas Diaria
    def test_ventas_diaria_muestra_columnas_calculadas_y_totales(self):
        self.venta(discount='30.00', lineas=[
            linea(2, quantity=2, price='120.00', install='50.00', inventario=self.inv, movimientos=[(self.inv, 4)]),
        ])
        respuesta = self.client.get(reverse('admin:product_proxy_pagos_changelist'))
        self.assertEqual(respuesta.status_code, 200)
        contenido = respuesta.content.decode()
        for esperado in ('480.00 Bs', '100.00 Bs', '580.00 Bs', '30.00 Bs', '550.00 Bs'):
            self.assertIn(esperado, contenido)
        self.assertIn('Totales del filtro: 1 ventas', contenido)

    def test_ventas_diaria_no_muestra_costos_ni_utilidad(self):
        self.venta(lineas=[linea(1, price='100.00', inventario=self.inv, movimientos=[(self.inv, 1)])])
        contenido = self.client.get(reverse('admin:product_proxy_pagos_changelist')).content.decode()
        self.assertNotIn('Costo Compra', contenido)
        self.assertNotIn('Utilidad Lamina', contenido)
        self.assertNotIn('Costo de compra', contenido)

    def test_ventas_diaria_con_proforma_sin_items_no_rompe(self):
        self.venta(lineas=[])
        respuesta = self.client.get(reverse('admin:product_proxy_pagos_changelist'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('0.00 Bs', respuesta.content.decode())

    def test_ventas_diaria_ordenar_por_columnas_de_base_de_datos_no_falla(self):
        self.venta(lineas=[linea(1, price='100.00')])
        for columna in range(1, 9):
            self.assertEqual(
                self.client.get(reverse('admin:product_proxy_pagos_changelist'), {'o': str(columna)}).status_code, 200, columna)

    def test_ventas_diaria_excluye_ventas_no_cobradas(self):
        self.venta(nota_venta_status='por_cobrar', lineas=[linea(1, price='100.00')])
        contenido = self.client.get(reverse('admin:product_proxy_pagos_changelist')).content.decode()
        self.assertNotIn('Totales del filtro', contenido)

    def test_ventas_diaria_es_solo_lectura_incluso_para_superusuario(self):
        cadena = self.venta(lineas=[linea(1, price='100.00')])
        request = RequestFactory().get('/')
        request.user = self.superuser
        model_admin = ReportDailySellAdmin(model=Proxy_Pagos, admin_site=AdminSite())
        self.assertFalse(model_admin.has_add_permission(request))
        self.assertFalse(model_admin.has_change_permission(request))
        self.assertFalse(model_admin.has_delete_permission(request))
        # tampoco por URL directa
        url = reverse('admin:product_proxy_pagos_delete', args=[cadena['pago'].pk])
        self.assertEqual(self.client.post(url, {'post': 'yes'}).status_code, 403)
        self.assertTrue(type(cadena['pago']).objects.filter(pk=cadena['pago'].pk).exists())

    # -- Reporte Utilidades
    def test_utilidades_muestra_lote_con_venta_costo_y_utilidad(self):
        self.venta(sales_type=METRO_LINEAL, lineas=[
            linea(5, price='100.00', inventario=self.inv, movimientos=[(self.inv, 5)]),
        ])
        respuesta = self.client.get(reverse('admin:product_utilidades_changelist'))
        self.assertEqual(respuesta.status_code, 200)
        contenido = respuesta.content.decode()
        for esperado in ('500.00 Bs', '400.00 Bs', '100.00 Bs'):  # venta, costo, utilidad
            self.assertIn(esperado, contenido)
        self.assertIn('Totales del filtro', contenido)

    def test_utilidades_solo_lista_lotes_con_ventas_cobradas(self):
        sin_ventas = helpers.create_inventario(sucursal=self.sucursal)
        self.venta(nota_venta_status='por_cobrar', lineas=[linea(1, inventario=sin_ventas, movimientos=[(sin_ventas, 1)])])
        request = RequestFactory().get('/')
        request.user = self.superuser
        model_admin = ReportUtilidadAdmin(model=utilidades, admin_site=AdminSite())
        self.assertEqual(list(model_admin.get_queryset(request)), [])

    def test_utilidades_es_solo_lectura_incluso_para_superusuario(self):
        request = RequestFactory().get('/')
        request.user = self.superuser
        model_admin = ReportUtilidadAdmin(model=utilidades, admin_site=AdminSite())
        self.assertFalse(model_admin.has_add_permission(request))
        self.assertFalse(model_admin.has_change_permission(request))
        self.assertFalse(model_admin.has_delete_permission(request))
        url = reverse('admin:product_utilidades_delete', args=[self.inv.pk])
        self.assertEqual(self.client.post(url, {'post': 'yes'}).status_code, 403)
        self.assertTrue(type(self.inv).objects.filter(pk=self.inv.pk).exists())

    def test_utilidades_usuario_con_dos_sucursales_ve_lotes_de_ambas(self):
        otra = helpers.create_sucursal(self.owner)
        inv_otra = helpers.create_inventario(sucursal=otra)
        self.venta(sales_type=METRO_LINEAL, lineas=[linea(1, inventario=self.inv, movimientos=[(self.inv, 1)])])
        create_venta_cobrada(self.owner, otra, sales_type=METRO_LINEAL, lineas=[
            linea(1, inventario=inv_otra, movimientos=[(inv_otra, 1)])])
        request = RequestFactory().get('/')
        request.user = self.owner
        model_admin = ReportUtilidadAdmin(model=utilidades, admin_site=AdminSite())
        ids = set(model_admin.get_queryset(request).values_list('id', flat=True))
        self.assertEqual(ids, {self.inv.id, inv_otra.id})
