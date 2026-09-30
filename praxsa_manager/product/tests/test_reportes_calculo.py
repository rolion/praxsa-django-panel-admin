"""Calculo de los reportes de ventas cobradas y utilidad
(TASK-reportes-utilidad-ventas-diarias, ADR-...-calculo-y-api). Importes elegidos
para poder verificarse a mano."""
from datetime import date
from decimal import Decimal

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from ..business.reportes import ReporteParametroInvalido, Reportes_Business, validar_rango
from . import helpers
from .reportes_helpers import INSTALACION, METRO_LINEAL, create_venta_cobrada, dia, linea, registrar_devolucion

D = Decimal


class ReportesCalculoTest(TestCase):

    def setUp(self):
        self.user, _ = helpers.create_user_with_token()
        self.sucursal = helpers.create_sucursal(self.user)
        self.business = Reportes_Business()
        self.inv80 = helpers.create_inventario(sucursal=self.sucursal, precio_compra_mtr_lineal=D('80.00'))
        self.inv60 = helpers.create_inventario(sucursal=self.sucursal, precio_compra_mtr_lineal=D('60.00'))

    def ventas(self, **filtros):
        pagos = self.business.filtrar_pagos(self.business.pagos_cobrados(), **filtros)
        return self.business.calcular_ventas(pagos)

    def una_venta(self):
        ventas = self.ventas()
        self.assertEqual(len(ventas), 1)
        return ventas[0]

    # -- definiciones
    def test_venta_con_instalacion_y_descuento(self):
        # metros 2 x 2 = 4; lamina 4 x 120 = 480; instalacion 50 x 2 = 100; costo 4 x 80 = 320
        create_venta_cobrada(self.user, self.sucursal, discount='30.00', lineas=[
            linea(2, quantity=2, price='120.00', install='50.00', inventario=self.inv80, movimientos=[(self.inv80, 4)]),
        ])
        venta = self.una_venta()
        self.assertEqual(venta['venta_lamina'], D('480.00'))
        self.assertEqual(venta['instalacion'], D('100.00'))
        self.assertEqual(venta['bruto'], D('580.00'))
        self.assertEqual(venta['descuento'], D('30.00'))
        self.assertEqual(venta['cobrado'], D('550.00'))
        self.assertEqual(venta['costo_compra'], D('320.00'))
        self.assertEqual(venta['utilidad_antes'], D('160.00'))
        self.assertEqual(venta['utilidad_despues'], D('130.00'))
        self.assertEqual(venta['margen'], D('23.64'))
        self.assertFalse(venta['costo_incompleto'])
        self.assertEqual(venta['sales_type'], INSTALACION)

    def test_venta_metro_lineal_sin_cantidad_ni_instalacion(self):
        create_venta_cobrada(self.user, self.sucursal, sales_type=METRO_LINEAL, lineas=[
            linea('3.50', quantity=0, price='100.00', inventario=self.inv60, movimientos=[(self.inv60, '3.50')]),
        ])
        venta = self.una_venta()
        self.assertEqual(venta['venta_lamina'], D('350.00'))
        self.assertEqual(venta['instalacion'], D('0.00'))
        self.assertEqual(venta['costo_compra'], D('210.00'))
        self.assertEqual(venta['utilidad_antes'], D('140.00'))
        self.assertEqual(venta['utilidad_despues'], D('140.00'))
        self.assertEqual(venta['margen'], D('40.00'))

    def test_descuento_mayor_a_la_utilidad_da_utilidad_negativa(self):
        create_venta_cobrada(self.user, self.sucursal, sales_type=METRO_LINEAL, discount='150.00', lineas=[
            linea(2, price='100.00', inventario=self.inv80, movimientos=[(self.inv80, 2)]),
        ])
        venta = self.una_venta()
        self.assertEqual(venta['utilidad_antes'], D('40.00'))
        self.assertEqual(venta['utilidad_despues'], D('-110.00'))
        self.assertEqual(venta['cobrado'], D('50.00'))

    def test_la_instalacion_no_entra_en_la_utilidad(self):
        create_venta_cobrada(self.user, self.sucursal, lineas=[
            linea(1, quantity=1, price='100.00', install='500.00', inventario=self.inv80, movimientos=[(self.inv80, 1)]),
        ])
        venta = self.una_venta()
        self.assertEqual(venta['instalacion'], D('500.00'))
        self.assertEqual(venta['utilidad_antes'], D('20.00'))

    # -- costo por fila de inventario
    def test_linea_repartida_en_dos_lotes_con_precios_distintos(self):
        create_venta_cobrada(self.user, self.sucursal, sales_type=METRO_LINEAL, lineas=[
            linea(5, price='100.00', inventario=self.inv80, movimientos=[(self.inv80, 3), (self.inv60, 2)]),
        ])
        venta = self.una_venta()
        self.assertEqual(venta['costo_compra'], D('360.00'))  # 3 x 80 + 2 x 60
        self.assertEqual(venta['utilidad_antes'], D('140.00'))
        self.assertFalse(venta['costo_incompleto'])

    def test_las_devoluciones_se_descuentan_del_costo(self):
        resultado = create_venta_cobrada(self.user, self.sucursal, sales_type=METRO_LINEAL, lineas=[
            linea(5, price='100.00', inventario=self.inv80, movimientos=[(self.inv80, 5)]),
        ])
        registrar_devolucion(resultado['detalles'][0], self.inv80, 1)
        self.assertEqual(self.una_venta()['costo_compra'], D('320.00'))  # (5 - 1) x 80

    def test_venta_anterior_a_los_movimientos_usa_el_lote_de_la_linea(self):
        create_venta_cobrada(self.user, self.sucursal, sales_type=METRO_LINEAL, lineas=[
            linea(2, price='100.00', inventario=self.inv80),
        ])
        venta = self.una_venta()
        self.assertEqual(venta['costo_compra'], D('160.00'))
        self.assertFalse(venta['costo_incompleto'])

    def test_linea_sin_movimientos_ni_lote_marca_costo_incompleto(self):
        create_venta_cobrada(self.user, self.sucursal, sales_type=METRO_LINEAL, lineas=[linea(2, price='100.00')])
        venta = self.una_venta()
        self.assertEqual(venta['costo_compra'], D('0.00'))
        self.assertEqual(venta['utilidad_antes'], D('200.00'))
        self.assertTrue(venta['costo_incompleto'])

    def test_lote_con_precio_de_compra_cero_marca_costo_incompleto(self):
        sin_precio = helpers.create_inventario(sucursal=self.sucursal, precio_compra_mtr_lineal=D('0.00'))
        create_venta_cobrada(self.user, self.sucursal, sales_type=METRO_LINEAL, lineas=[
            linea(2, price='100.00', inventario=sin_precio, movimientos=[(sin_precio, 2)]),
        ])
        self.assertTrue(self.una_venta()['costo_incompleto'])

    def test_movimientos_totalmente_devueltos_marcan_costo_incompleto(self):
        resultado = create_venta_cobrada(self.user, self.sucursal, sales_type=METRO_LINEAL, lineas=[
            linea(2, price='100.00', inventario=self.inv80, movimientos=[(self.inv80, 2)]),
        ])
        registrar_devolucion(resultado['detalles'][0], self.inv80, 2)
        venta = self.una_venta()
        self.assertEqual(venta['costo_compra'], D('0.00'))
        self.assertTrue(venta['costo_incompleto'])

    def test_proforma_sin_items_no_rompe_el_reporte(self):
        create_venta_cobrada(self.user, self.sucursal, lineas=[])
        venta = self.una_venta()
        self.assertEqual(venta['bruto'], D('0.00'))
        self.assertEqual(venta['cobrado'], D('0.00'))
        self.assertIsNone(venta['margen'])
        self.assertTrue(venta['costo_incompleto'])

    # -- que ventas cuentan
    def test_solo_cuentan_las_ventas_cobradas_y_vigentes(self):
        cobrada = create_venta_cobrada(self.user, self.sucursal, lineas=[linea(1, price='100.00', inventario=self.inv80)])
        create_venta_cobrada(self.user, self.sucursal, nota_venta_status='por_cobrar', lineas=[linea(1, inventario=self.inv80)])
        create_venta_cobrada(self.user, self.sucursal, nota_venta_status='anulada', lineas=[linea(1, inventario=self.inv80)])
        create_venta_cobrada(self.user, self.sucursal, crear_pago=False, lineas=[linea(1, inventario=self.inv80)])
        create_venta_cobrada(self.user, self.sucursal, is_delete=True, lineas=[linea(1, inventario=self.inv80)])
        self.assertEqual([v['pago_id'] for v in self.ventas()], [cobrada['pago'].id])

    # -- fechas y filtros
    def test_rango_de_fechas_incluye_ambos_extremos_por_fecha_del_pago(self):
        dentro_inicio = create_venta_cobrada(self.user, self.sucursal, lineas=[linea(1)], pagado_en=dia(2026, 9, 1, 0, 0))
        dentro_fin = create_venta_cobrada(self.user, self.sucursal, lineas=[linea(1)], pagado_en=dia(2026, 9, 3, 23, 59))
        create_venta_cobrada(self.user, self.sucursal, lineas=[linea(1)], pagado_en=dia(2026, 8, 31, 23, 59))
        create_venta_cobrada(self.user, self.sucursal, lineas=[linea(1)], pagado_en=dia(2026, 9, 4, 0, 0))
        ids = {v['pago_id'] for v in self.ventas(desde=date(2026, 9, 1), hasta=date(2026, 9, 3))}
        self.assertEqual(ids, {dentro_inicio['pago'].id, dentro_fin['pago'].id})

    def test_filtros_por_sucursal_tipo_de_venta_y_tipo_de_pago(self):
        otra = helpers.create_sucursal(self.user)
        base = create_venta_cobrada(self.user, self.sucursal, lineas=[linea(1)])
        create_venta_cobrada(self.user, otra, lineas=[linea(1)])
        metro = create_venta_cobrada(self.user, self.sucursal, sales_type=METRO_LINEAL, tipo_pago='trans', lineas=[linea(1)])
        self.assertEqual({v['pago_id'] for v in self.ventas(sucursal_id=self.sucursal.id)},
                         {base['pago'].id, metro['pago'].id})
        self.assertEqual([v['pago_id'] for v in self.ventas(sales_type=METRO_LINEAL)], [metro['pago'].id])
        self.assertEqual([v['pago_id'] for v in self.ventas(tipo_pago='trans')], [metro['pago'].id])

    def test_validar_rango(self):
        validar_rango(date(2026, 1, 1), date(2026, 12, 31))  # 365 dias
        validar_rango(date(2024, 1, 1), date(2024, 12, 31))  # 366 dias (bisiesto), limite
        with self.assertRaises(ReporteParametroInvalido):
            validar_rango(date(2026, 9, 2), date(2026, 9, 1))
        with self.assertRaises(ReporteParametroInvalido):
            validar_rango(date(2025, 1, 1), date(2026, 1, 2))

    # -- resumenes
    def test_totales_y_desgloses_cuadran_con_las_filas(self):
        create_venta_cobrada(self.user, self.sucursal, discount='30.00', tipo_pago='efec', lineas=[
            linea(2, quantity=2, price='120.00', install='50.00', inventario=self.inv80, movimientos=[(self.inv80, 4)]),
        ])
        create_venta_cobrada(self.user, self.sucursal, sales_type=METRO_LINEAL, tipo_pago='trans', lineas=[
            linea('3.50', price='100.00', inventario=self.inv60, movimientos=[(self.inv60, '3.50')]),
        ])
        create_venta_cobrada(self.user, self.sucursal, sales_type=METRO_LINEAL, lineas=[linea(1, price='100.00')])
        ventas = self.ventas()
        resumen = self.business.resumir(ventas)
        totales = resumen['totales']
        self.assertEqual(totales['ventas'], 3)
        for campo in ('bruto', 'descuento', 'cobrado', 'venta_lamina', 'instalacion', 'costo_compra', 'utilidad_antes', 'utilidad_despues'):
            self.assertEqual(totales[campo], sum(v[campo] for v in ventas), campo)
        self.assertEqual(totales['ventas_costo_incompleto'], 1)
        # bruto - descuento = cobrado por venta y en el total
        for venta in ventas:
            self.assertEqual(venta['bruto'] - venta['descuento'], venta['cobrado'])
        self.assertEqual(totales['bruto'] - totales['descuento'], totales['cobrado'])
        por_tipo = {fila['sales_type']: fila for fila in resumen['por_tipo_venta']}
        self.assertEqual(por_tipo[INSTALACION]['ventas'], 1)
        self.assertEqual(por_tipo[METRO_LINEAL]['ventas'], 2)
        self.assertEqual(por_tipo[INSTALACION]['instalacion'], D('100.00'))
        por_pago = {fila['tipo_pago']: fila for fila in resumen['por_tipo_pago']}
        self.assertEqual(por_pago['efec']['ventas'], 2)
        self.assertEqual(por_pago['trans']['cobrado'], D('350.00'))

    def test_desgloses_incluyen_los_tipos_sin_ventas(self):
        resumen = self.business.resumir([])
        self.assertEqual({f['sales_type'] for f in resumen['por_tipo_venta']}, {INSTALACION, METRO_LINEAL})
        self.assertEqual({f['tipo_pago'] for f in resumen['por_tipo_pago']}, {'efec', 'trans'})
        self.assertEqual(resumen['totales']['ventas'], 0)
        self.assertIsNone(resumen['totales']['margen'])

    def test_por_lamina_cuenta_una_vez_la_linea_repartida_en_dos_lotes(self):
        film = helpers.create_window_film()
        create_venta_cobrada(self.user, self.sucursal, sales_type=METRO_LINEAL, lineas=[
            linea(5, price='100.00', window_film=film, inventario=self.inv80, movimientos=[(self.inv80, 3), (self.inv60, 2)]),
        ])
        filas = self.business.resumir(self.ventas())['por_lamina']
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]['metros'], D('5.00'))
        self.assertEqual(filas[0]['venta_lamina'], D('500.00'))
        self.assertEqual(filas[0]['costo_compra'], D('360.00'))
        self.assertEqual(filas[0]['utilidad_antes'], D('140.00'))

    def test_por_lote_acumula_tramos_de_ventas_cobradas(self):
        create_venta_cobrada(self.user, self.sucursal, sales_type=METRO_LINEAL, lineas=[
            linea(5, price='100.00', inventario=self.inv80, movimientos=[(self.inv80, 3), (self.inv60, 2)]),
        ])
        create_venta_cobrada(self.user, self.sucursal, sales_type=METRO_LINEAL, lineas=[
            linea(2, price='100.00', inventario=self.inv80),  # legado, sin movimientos
        ])
        create_venta_cobrada(self.user, self.sucursal, sales_type=METRO_LINEAL, nota_venta_status='por_cobrar', lineas=[
            linea(9, price='100.00', inventario=self.inv80, movimientos=[(self.inv80, 9)]),
        ])
        lotes = self.business.calcular_por_lote([self.inv80.id, self.inv60.id])
        self.assertEqual(lotes[self.inv80.id]['metros'], D('5.00'))          # 3 + 2 legado
        self.assertEqual(lotes[self.inv80.id]['venta_lamina'], D('500.00'))  # 300 + 200
        self.assertEqual(lotes[self.inv80.id]['costo_compra'], D('400.00'))  # 5 x 80
        self.assertEqual(lotes[self.inv80.id]['utilidad_antes'], D('100.00'))
        self.assertEqual(lotes[self.inv60.id]['metros'], D('2.00'))
        self.assertEqual(lotes[self.inv60.id]['costo_compra'], D('120.00'))

    def test_numero_de_consultas_constante(self):
        def armar(n):
            for _ in range(n):
                create_venta_cobrada(self.user, self.sucursal, lineas=[
                    linea(1, quantity=1, price='100.00', install='10.00', inventario=self.inv80, movimientos=[(self.inv80, 1)]),
                    linea(2, quantity=1, price='100.00', install='10.00', inventario=self.inv60, movimientos=[(self.inv60, 2)]),
                ])

        armar(2)
        with CaptureQueriesContext(connection) as pocas:
            self.ventas()
        armar(6)
        with CaptureQueriesContext(connection) as muchas:
            self.assertEqual(len(self.ventas()), 8)
        self.assertEqual(len(pocas), len(muchas))
