"""Definiciones de las metricas del dashboard con datos de importes conocidos
(TASK-dashboard-taller-laminas, ADR-...-definiciones-metricas). Se llama a
Dashboard_Business con `hoy` fijo: no depende del reloj."""
from datetime import date, datetime
from decimal import Decimal

from django.test import TestCase

from ..business.dashboard import Dashboard_Business, estado_stock, meses_hasta
from ..helper import estados
from ..models import Detalle_Nota_Trabajo, Nota_trabajo, Proforma_Detail, Proforma_Header, inventario
from . import helpers
from .reportes_helpers import create_venta_cobrada, dia, linea

D = Decimal
HOY = date(2026, 9, 15)


class DashboardBase(TestCase):
    def setUp(self):
        self.user, self.token, _ = helpers.create_staff_user_with_token()
        self.sucursal = helpers.create_sucursal(self.user)
        self.negocio = Dashboard_Business()

    def venta(self, pagado_en, monto='100.00', **kwargs):
        return create_venta_cobrada(
            self.user, self.sucursal, [linea(1, price='100.00')], pagado_en=pagado_en, monto=monto, **kwargs
        )

    def proforma(self, creada=None, status='proforma', discount=None, **kwargs):
        header, detail = helpers.create_full_proforma(self.user, sucursal=self.sucursal, **kwargs)
        cambios = {'status': status}
        if creada is not None:
            cambios['proforma_created_on'] = creada
        if discount is not None:
            cambios['discount'] = D(discount)
        Proforma_Header.objects.filter(pk=header.pk).update(**cambios)
        header.refresh_from_db()
        return header, detail

    def nota(self, status=estados.NT_EN_PROCESO, entrada=None, salida=None, creada=None, proforma=None, **kwargs):
        header = proforma or self.proforma(status='en_trabajo')[0]
        nota = helpers.create_nota_trabajo(header, status=status, salida_vehiculo=salida, **kwargs)
        cambios = {}
        if entrada is not None:
            cambios['entrada_vehiculo'] = entrada
        if creada is not None:
            cambios['nota_venta_created_on'] = creada
        if cambios:
            Nota_trabajo.objects.filter(pk=nota.pk).update(**cambios)
            nota.refresh_from_db()
        return nota


class VentasTest(DashboardBase):
    def test_ventas_mes_variacion_y_exclusiones(self):
        self.venta(dia(2026, 9, 3), '100.00')
        self.venta(dia(2026, 9, 10), '50.00')
        self.venta(dia(2026, 8, 20), '80.00')
        self.venta(dia(2026, 7, 5), '999.00')  # dos meses atras: no cuenta
        self.venta(dia(2026, 9, 4), '500.00', nota_venta_status='por_cobrar', crear_pago=False)
        self.venta(dia(2026, 9, 5), '700.00', is_delete=True)
        ventas = self.negocio.ventas(self.user, HOY)
        self.assertEqual(ventas['mes'], D('150.00'))
        self.assertEqual(ventas['mes_anterior'], D('80.00'))
        self.assertEqual(ventas['variacion'], D('87.5'))

    def test_variacion_es_null_si_el_mes_previo_es_cero(self):
        self.venta(dia(2026, 9, 3), '100.00')
        ventas = self.negocio.ventas(self.user, HOY)
        self.assertEqual(ventas['mes_anterior'], D('0.00'))
        self.assertIsNone(ventas['variacion'])

    def test_enero_compara_con_diciembre_del_anio_anterior(self):
        self.venta(dia(2025, 12, 31), '40.00')
        self.venta(dia(2026, 1, 1), '60.00')
        ventas = self.negocio.ventas(self.user, date(2026, 1, 10))
        self.assertEqual((ventas['mes'], ventas['mes_anterior'], ventas['variacion']), (D('60.00'), D('40.00'), D('50.0')))

    def test_filtra_por_sucursal(self):
        otra = helpers.create_sucursal(self.user, name='Otra')
        create_venta_cobrada(self.user, otra, [linea(1)], pagado_en=dia(2026, 9, 3), monto='30.00')
        self.venta(dia(2026, 9, 3), '100.00')
        self.assertEqual(self.negocio.ventas(self.user, HOY, otra.id)['mes'], D('30.00'))
        self.assertEqual(self.negocio.ventas(self.user, HOY)['mes'], D('130.00'))


class KpisProformasTest(DashboardBase):
    def test_proformas_activas_solo_estado_proforma_no_borradas(self):
        self.proforma(discount='20.00')
        self.proforma()
        self.proforma(status='en_trabajo')
        borrada, _ = self.proforma()
        Proforma_Header.objects.filter(pk=borrada.pk).update(is_delete=True)
        activas = self.negocio.proformas_activas(self.user)
        self.assertEqual(activas, {'monto': D('320.00'), 'cantidad': 2})

    def test_conversion_por_cohorte_excluye_anuladas(self):
        septiembre = datetime(2026, 9, 5, 9)
        self.proforma(septiembre, 'proforma')
        self.proforma(septiembre, 'en_trabajo')
        self.proforma(septiembre, 'finalizado')
        self.proforma(septiembre, 'anulada')
        self.proforma(datetime(2026, 8, 5, 9), 'finalizado')
        conversion = self.negocio.conversion(self.user, HOY)
        self.assertEqual((conversion['convertidas'], conversion['emitidas']), (2, 3))
        self.assertEqual(conversion['porcentaje'], D('66.7'))

    def test_conversion_sin_proformas_es_null(self):
        conversion = self.negocio.conversion(self.user, HOY)
        self.assertEqual((conversion['convertidas'], conversion['emitidas']), (0, 0))
        self.assertIsNone(conversion['porcentaje'])

    def test_instalaciones_en_taller_y_terminadas_hoy(self):
        self.nota(estados.NT_EN_PROCESO)
        self.nota(estados.NT_EN_PROCESO, entrada=datetime(2026, 8, 1, 9))  # de cualquier fecha
        self.nota(estados.NT_TERMINADO, salida=datetime(2026, 9, 15, 11))
        self.nota(estados.NT_TERMINADO, salida=datetime(2026, 9, 14, 11))  # ayer: no cuenta
        self.nota(estados.NT_CANCELADA)
        self.assertEqual(self.negocio.instalaciones(self.user, HOY), {'en_taller': 2, 'terminadas_hoy': 1})

    def test_kpis_sin_permiso_de_ventas_devuelven_null(self):
        self.venta(dia(2026, 9, 3), '100.00')
        self.assertIsNone(self.negocio.kpis(self.user, HOY, con_ventas=False)['ventas'])
        self.assertEqual(self.negocio.kpis(self.user, HOY, con_ventas=True)['ventas']['mes'], D('100.00'))


class SerieTest(DashboardBase):
    def test_serie_completa_de_12_meses_con_ceros(self):
        self.proforma(datetime(2026, 9, 2, 9), 'proforma', discount='20.00')  # 150
        self.proforma(datetime(2026, 9, 3, 9), 'en_trabajo')  # 170
        self.proforma(datetime(2026, 9, 4, 9), 'anulada')  # excluida
        self.proforma(datetime(2026, 3, 4, 9), 'finalizado')  # 170
        venta = self.venta(dia(2026, 9, 3), '90.00')
        # la venta trae su propia proforma (100.00, no anulada): se fija su fecha para no depender del reloj
        Proforma_Header.objects.filter(pk=venta['proforma'].pk).update(proforma_created_on=datetime(2026, 9, 3, 9))
        serie = self.negocio.proformas_vs_ventas(self.user, HOY, 12, con_ventas=True)
        self.assertEqual(len(serie['meses']), 12)
        self.assertEqual((serie['meses'][0], serie['meses'][-1]), ('2025-10', '2026-09'))
        self.assertEqual(serie['cotizado'][-1], D('420.00'))  # 150 + 170 + 100 de la venta
        self.assertEqual(serie['cotizado'][serie['meses'].index('2026-03')], D('170.00'))
        self.assertEqual(serie['cotizado'][serie['meses'].index('2026-05')], D('0.00'))
        self.assertEqual(serie['vendido'][-1], D('90.00'))
        self.assertEqual(sum(serie['vendido']), D('90.00'))

    def test_vendido_es_null_sin_permiso(self):
        self.venta(dia(2026, 9, 3), '90.00')
        self.assertIsNone(self.negocio.proformas_vs_ventas(self.user, HOY, 6, con_ventas=False)['vendido'])

    def test_meses_hasta_cruza_el_anio(self):
        self.assertEqual(
            [m.strftime('%Y-%m') for m in meses_hasta(date(2026, 2, 10), 4)],
            ['2025-11', '2025-12', '2026-01', '2026-02'],
        )


class ConsumoTest(DashboardBase):
    def detalle(self, nota, film, length):
        return Detalle_Nota_Trabajo.objects.create(nota_trabajo=nota, window_film=film, width=D('1.50'), length=D(length))

    def test_suma_por_lamina_y_mes_sin_canceladas(self):
        a, b = helpers.create_window_film(name='Ceramica'), helpers.create_window_film(name='Seguridad 8mil')
        n1 = self.nota(creada=datetime(2026, 9, 2, 9))
        n2 = self.nota(creada=datetime(2026, 8, 2, 9))
        cancelada = self.nota(estados.NT_CANCELADA, creada=datetime(2026, 9, 3, 9))
        self.detalle(n1, a, '4.50')
        self.detalle(n1, b, '2.00')
        self.detalle(n2, a, '1.25')
        self.detalle(cancelada, a, '99.00')
        consumo = self.negocio.consumo_laminas(self.user, HOY, 12)
        series = {s['nombre']: s for s in consumo['series']}
        self.assertEqual(set(series), {'Ceramica', 'Seguridad 8mil'})
        self.assertEqual(series['Ceramica']['metros'][-1], D('4.50'))
        self.assertEqual(series['Ceramica']['metros'][-2], D('1.25'))
        self.assertEqual(series['Ceramica']['total'], D('5.75'))
        self.assertEqual(series['Seguridad 8mil']['total'], D('2.00'))

    def test_mas_de_seis_laminas_agrupa_el_resto_en_otras(self):
        nota = self.nota(creada=datetime(2026, 9, 2, 9))
        for i in range(8):
            self.detalle(nota, helpers.create_window_film(name=f'Lamina {i}'), str(10 - i))
        series = self.negocio.consumo_laminas(self.user, HOY, 12)['series']
        self.assertEqual(len(series), 7)
        self.assertEqual(series[-1]['nombre'], 'Otras')
        self.assertEqual(series[-1]['total'], D('7.00'))  # las dos menores: 4 + 3


class ItemsTest(DashboardBase):
    def test_cuenta_lineas_por_item_sin_anuladas(self):
        parabrisas, laterales = helpers.create_car_part(name='Parabrisas'), helpers.create_car_part(name='Laterales')
        for _ in range(3):
            self.proforma(datetime(2026, 9, 2, 9), car_part=parabrisas)
        self.proforma(datetime(2026, 9, 2, 9), car_part=laterales)
        self.proforma(datetime(2026, 9, 2, 9), 'anulada', car_part=parabrisas)
        items = self.negocio.items_solicitados(self.user, HOY, 12)
        self.assertEqual(items['total'], 4)
        self.assertEqual(items['items'], [{'nombre': 'Parabrisas', 'cantidad': 3}, {'nombre': 'Laterales', 'cantidad': 1}])

    def test_mas_de_cinco_items_agrupa_en_otros(self):
        for i in range(7):
            self.proforma(datetime(2026, 9, 2, 9), car_part=helpers.create_car_part(name=f'Item {i}'))
        items = self.negocio.items_solicitados(self.user, HOY, 12)
        self.assertEqual(len(items['items']), 6)
        self.assertEqual(items['items'][-1], {'nombre': 'Otros', 'cantidad': 2})

    def test_lineas_de_metro_lineal_sin_item_no_cuentan(self):
        header, detail = self.proforma(datetime(2026, 9, 2, 9))
        Proforma_Detail.objects.filter(pk=detail.pk).update(car_part=None)
        self.assertEqual(self.negocio.items_solicitados(self.user, HOY, 12)['total'], 0)


class StockTest(DashboardBase):
    def stock(self, metros, nombre, **kwargs):
        reel = helpers.create_window_film_reel(window_film=helpers.create_window_film(name=nombre))
        return helpers.create_inventario(sucursal=self.sucursal, bobina=reel, to_install=D(metros), **kwargs)

    def test_limites_de_los_umbrales(self):
        self.assertEqual(estado_stock(D('9.99')), 'critico')
        self.assertEqual(estado_stock(D('10')), 'bajo')
        self.assertEqual(estado_stock(D('29.99')), 'bajo')
        self.assertEqual(estado_stock(D('30')), 'ok')
        self.assertEqual(estado_stock(D('0')), 'critico')

    def test_por_defecto_solo_criticos_y_bajos_ordenados_por_metros(self):
        self.stock('45.00', 'Amplia')
        self.stock('12.00', 'Baja')
        self.stock('3.00', 'Critica')
        self.stock('0.00', 'Agotada')
        resultado = self.negocio.stock_critico(self.user)
        self.assertEqual([f['lamina'] for f in resultado['filas']], ['Agotada', 'Critica', 'Baja'])
        self.assertEqual([f['estado'] for f in resultado['filas']], ['critico', 'critico', 'bajo'])
        self.assertEqual(resultado['contadores'], {'criticos': 2, 'bajos': 1, 'ok': 1})
        self.assertEqual(len(self.negocio.stock_critico(self.user, todos=True)['filas']), 4)

    def test_suma_filas_del_grupo_y_cuenta_rollos_con_metros(self):
        film = helpers.create_window_film(name='Doble')
        reel = helpers.create_window_film_reel(window_film=film)
        helpers.create_inventario(sucursal=self.sucursal, bobina=reel, to_install=D('5.00'))
        helpers.create_inventario(sucursal=self.sucursal, bobina=reel, to_install=D('4.00'))
        helpers.create_inventario(sucursal=self.sucursal, bobina=reel, to_install=D('0.00'))
        fila = self.negocio.stock_critico(self.user)['filas'][0]
        self.assertEqual((fila['metros'], fila['rollos'], fila['estado']), (D('9.00'), 2, 'critico'))

    def test_excluye_inventario_inactivo(self):
        inv = self.stock('1.00', 'Inactiva')
        inventario.objects.filter(pk=inv.pk).update(is_active=False)
        self.assertEqual(self.negocio.stock_critico(self.user)['filas'], [])


class ColaTest(DashboardBase):
    def test_en_proceso_primero_terminadas_hoy_despues_y_maximo_10(self):
        for i in range(11):
            self.nota(entrada=datetime(2026, 9, 1, 8 + (i % 8), i))
        terminada = self.nota(estados.NT_TERMINADO, salida=datetime(2026, 9, 15, 10))
        self.nota(estados.NT_TERMINADO, salida=datetime(2026, 9, 14, 10))
        self.nota(estados.NT_CANCELADA)
        cola = self.negocio.cola_taller(self.user, HOY)
        self.assertEqual(cola['total'], 12)
        self.assertEqual(len(cola['filas']), 10)
        self.assertTrue(all(f['status'] == estados.NT_EN_PROCESO for f in cola['filas']))
        self.assertNotIn(terminada.id, [f['nota_trabajo_id'] for f in cola['filas']])

    def test_terminada_hoy_aparece_tras_las_en_proceso(self):
        self.nota(estados.NT_TERMINADO, salida=datetime(2026, 9, 15, 10))
        self.nota(estados.NT_EN_PROCESO, entrada=datetime(2026, 9, 14, 8))
        estados_cola = [f['status'] for f in self.negocio.cola_taller(self.user, HOY)['filas']]
        self.assertEqual(estados_cola, [estados.NT_EN_PROCESO, estados.NT_TERMINADO])

    def test_laminas_y_tecnico(self):
        film = helpers.create_window_film(name='Ceramica')
        nota = self.nota()
        Detalle_Nota_Trabajo.objects.create(nota_trabajo=nota, window_film=film, width=D('1.50'), length=D('3.00'))
        fila = self.negocio.cola_taller(self.user, HOY)['filas'][0]
        self.assertEqual(fila['laminas'], ['Ceramica'])
        self.assertIsNone(fila['instalador'])
        self.assertEqual(fila['cliente'], nota.name)


class RecientesTest(DashboardBase):
    def test_seis_mas_recientes_en_todos_los_estados(self):
        creadas = [self.proforma(status=s)[0].id for s in ['proforma'] * 5 + ['en_trabajo', 'anulada', 'finalizado']]
        recientes = self.negocio.proformas_recientes(self.user)
        self.assertEqual([p.id for p in recientes], sorted(creadas, reverse=True)[:6])
