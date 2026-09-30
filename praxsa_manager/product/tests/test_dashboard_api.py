"""API del dashboard del panel (TASK-dashboard-taller-laminas): alcance por sucursal,
permiso de ventas cobradas, ausencia de costos, solo lectura y equivalencia con el
reporte de Ventas Diarias. Ver ADR-dashboard-taller-laminas-api-agregados-alcance."""
import json
from datetime import date, datetime
from decimal import Decimal

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from ..business.dashboard import ultimo_dia
from ..models import Detalle_Nota_Trabajo
from . import helpers
from .ordenes_helpers import auth, make_staff
from .reportes_helpers import create_venta_cobrada, linea

BASE = '/product/dashboard'
ENDPOINTS = [
    'kpis', 'proformas-vs-ventas', 'consumo-laminas', 'items-solicitados', 'stock-critico',
    'cola-taller', 'proformas-recientes',
]
VENTAS = ('view_proxy_pagos',)
D = Decimal


def make_user(permissions=(), group=None, sucursal=True):
    user, token = make_staff(permissions=permissions, group=group)
    return user, token, (helpers.create_sucursal(user) if sucursal else None)


def get(client, token, endpoint, **params):
    return client.get(f'{BASE}/{endpoint}', params, **auth(token))


def claves(valor):
    """Todas las claves de un JSON anidado."""
    if isinstance(valor, dict):
        for clave, hijo in valor.items():
            yield clave
            yield from claves(hijo)
    elif isinstance(valor, list):
        for hijo in valor:
            yield from claves(hijo)


class AccesoTest(TestCase):
    def test_sin_token_401_y_sin_ser_staff_403(self):
        _, token = helpers.create_user_with_token()
        for endpoint in ENDPOINTS:
            self.assertEqual(self.client.get(f'{BASE}/{endpoint}').status_code, 401, endpoint)
            self.assertEqual(get(self.client, token, endpoint).status_code, 403, endpoint)

    def test_solo_lectura(self):
        _, token, _ = make_user(VENTAS)
        for endpoint in ENDPOINTS:
            for metodo in ('post', 'put', 'patch', 'delete'):
                respuesta = getattr(self.client, metodo)(f'{BASE}/{endpoint}', {}, **auth(token))
                self.assertEqual(respuesta.status_code, 405, f'{metodo} {endpoint}')

    def test_parametros_invalidos_400(self):
        _, token, _ = make_user()
        for params in ({'meses': 13}, {'meses': 0}, {'meses': 'x'}, {'sucursal': 'abc'}, {'sucursal': 0}):
            for endpoint in ENDPOINTS:
                self.assertEqual(get(self.client, token, endpoint, **params).status_code, 400, (endpoint, params))


class AlcanceTest(TestCase):
    def setUp(self):
        self.a_user, self.a_token, self.a_suc = make_user()
        self.b_user, self.b_token, self.b_suc = make_user()
        self.proforma_a, _ = helpers.create_full_proforma(self.a_user, sucursal=self.a_suc)
        self.proforma_b, _ = helpers.create_full_proforma(self.b_user, sucursal=self.b_suc)

    def ids_recientes(self, token, **params):
        respuesta = get(self.client, token, 'proformas-recientes', **params)
        self.assertEqual(respuesta.status_code, 200)
        return [p['id'] for p in respuesta.json()['proformas']]

    def test_empleado_solo_ve_su_sucursal(self):
        self.assertEqual(self.ids_recientes(self.a_token), [self.proforma_a.id])
        self.assertEqual(get(self.client, self.a_token, 'kpis').json()['proformas_activas']['cantidad'], 1)

    def test_sucursal_ajena_responde_404_en_todos_los_endpoints(self):
        for endpoint in ENDPOINTS:
            respuesta = get(self.client, self.a_token, endpoint, sucursal=self.b_suc.id)
            self.assertEqual(respuesta.status_code, 404, endpoint)

    def test_admin_ve_todo_y_puede_filtrar_por_sucursal(self):
        _, token, _ = make_user(group='admin', sucursal=False)
        self.assertCountEqual(self.ids_recientes(token), [self.proforma_a.id, self.proforma_b.id])
        self.assertEqual(self.ids_recientes(token, sucursal=self.b_suc.id), [self.proforma_b.id])
        kpis = get(self.client, token, 'kpis').json()
        self.assertEqual(kpis['proformas_activas']['cantidad'], 2)
        self.assertIsNone(kpis['sucursal'])
        self.assertEqual(get(self.client, token, 'kpis', sucursal=self.a_suc.id).json()['sucursal'], self.a_suc.id)

    def test_empleado_de_dos_sucursales_ve_ambas(self):
        segunda = helpers.create_sucursal(self.a_user, name='Segunda')
        otra, _ = helpers.create_full_proforma(self.a_user, sucursal=segunda)
        self.assertCountEqual(self.ids_recientes(self.a_token), [self.proforma_a.id, otra.id])
        self.assertEqual(self.ids_recientes(self.a_token, sucursal=segunda.id), [otra.id])

    def test_sin_sucursal_devuelve_vacio_y_el_indicador(self):
        _, token, _ = make_user(VENTAS, sucursal=False)
        kpis = get(self.client, token, 'kpis').json()
        self.assertTrue(kpis['sin_sucursal'])
        self.assertEqual(kpis['proformas_activas'], {'monto': '0.00', 'cantidad': 0})
        self.assertEqual(kpis['ventas']['mes'], '0.00')
        self.assertEqual(self.ids_recientes(token), [])
        self.assertEqual(get(self.client, token, 'cola-taller').json()['filas'], [])
        self.assertEqual(get(self.client, token, 'stock-critico').json()['filas'], [])
        self.assertFalse(get(self.client, self.a_token, 'kpis').json()['sin_sucursal'])


class PermisoVentasTest(TestCase):
    MONTO = '7654.32'

    def setUp(self):
        self.user, self.token, self.sucursal = make_user(())
        self.caja, self.caja_token = make_staff(VENTAS)
        self.sucursal.empleado.add(self.caja)
        create_venta_cobrada(
            self.user, self.sucursal, [linea(1)], pagado_en=datetime.now(), monto=self.MONTO,
        )

    def test_con_permiso_se_entregan_ventas_y_vendido(self):
        kpis = get(self.client, self.caja_token, 'kpis').json()
        self.assertEqual(kpis['ventas']['mes'], self.MONTO)
        serie = get(self.client, self.caja_token, 'proformas-vs-ventas').json()
        self.assertEqual(serie['vendido'][-1], self.MONTO)

    def test_sin_permiso_van_null_y_ningun_importe_de_venta_en_el_json(self):
        kpis = get(self.client, self.token, 'kpis')
        serie = get(self.client, self.token, 'proformas-vs-ventas')
        self.assertEqual((kpis.status_code, serie.status_code), (200, 200))
        self.assertIsNone(kpis.json()['ventas'])
        self.assertIsNone(serie.json()['vendido'])
        for endpoint in ENDPOINTS:
            contenido = get(self.client, self.token, endpoint).content.decode()
            self.assertNotIn(self.MONTO, contenido, endpoint)

    def test_el_resto_de_widgets_no_pide_el_permiso(self):
        for endpoint in ENDPOINTS:
            self.assertEqual(get(self.client, self.token, endpoint).status_code, 200, endpoint)


class SinCostosTest(TestCase):
    PROHIBIDAS = ('costo', 'utilidad', 'margen', 'precio_compra')

    def test_ninguna_respuesta_expone_costos_ni_utilidad(self):
        user, token, sucursal = make_user(VENTAS)
        venta = create_venta_cobrada(user, sucursal, [linea(2, price='100.00')], pagado_en=datetime.now())
        helpers.create_inventario(sucursal=sucursal, to_install=D('5.00'), precio_compra_mtr_lineal=D('80.00'))
        nota = venta['nota_venta'].nota_trabajo
        Detalle_Nota_Trabajo.objects.create(
            nota_trabajo=nota, window_film=venta['detalles'][0].window_film, width=D('1.50'), length=D('2.00')
        )
        for endpoint in ENDPOINTS:
            respuesta = get(self.client, token, endpoint, todos='true')
            self.assertEqual(respuesta.status_code, 200)
            for clave in claves(respuesta.json()):
                self.assertFalse(any(p in clave.lower() for p in self.PROHIBIDAS), (endpoint, clave))


class EquivalenciaConReporteTest(TestCase):
    """El total del dashboard debe ser el `cobrado` de Ventas Diarias para el mismo rango y sucursal."""

    def test_ventas_del_mes_y_serie_coinciden_con_el_reporte(self):
        user, token, sucursal = make_user(VENTAS)
        segunda = helpers.create_sucursal(user, name='Segunda')
        hoy = datetime.now()
        for monto, suc in (('120.50', sucursal), ('75.25', sucursal), ('40.00', segunda)):
            create_venta_cobrada(user, suc, [linea(1)], pagado_en=hoy, monto=monto)
        create_venta_cobrada(user, sucursal, [linea(1)], pagado_en=datetime(2020, 1, 5, 10), monto='999.00')
        create_venta_cobrada(user, sucursal, [linea(1)], pagado_en=hoy, monto='500.00', nota_venta_status='por_cobrar', crear_pago=False)
        inicio = date.today().replace(day=1)
        rango = {'desde': inicio.isoformat(), 'hasta': ultimo_dia(inicio).isoformat()}

        def cobrado(**extra):
            return D(self.client.get('/product/reportes/ventas-diarias', {**rango, **extra}, **auth(token)).json()['totales']['cobrado'])

        for extra in ({}, {'sucursal': sucursal.id}, {'sucursal': segunda.id}):
            kpis = get(self.client, token, 'kpis', **extra).json()
            serie = get(self.client, token, 'proformas-vs-ventas', **extra).json()
            esperado = cobrado(**extra)
            self.assertEqual(D(kpis['ventas']['mes']), esperado, extra)
            self.assertEqual(D(serie['vendido'][-1]), esperado, extra)
        self.assertEqual(D(get(self.client, token, 'kpis').json()['ventas']['mes']), D('235.75'))


class ConsultasTest(TestCase):
    def test_cola_y_recientes_no_hacen_una_consulta_por_fila(self):
        user, token, sucursal = make_user()
        for _ in range(12):
            header, _ = helpers.create_full_proforma(user, sucursal=sucursal)
            helpers.create_nota_trabajo(header)
        for endpoint in ('cola-taller', 'proformas-recientes'):
            with CaptureQueriesContext(connection) as consultas:
                respuesta = get(self.client, token, endpoint)
            self.assertEqual(respuesta.status_code, 200)
            self.assertLessEqual(len(consultas), 12, (endpoint, len(consultas)))
        self.assertEqual(len(get(self.client, token, 'cola-taller').json()['filas']), 10)
        self.assertEqual(len(get(self.client, token, 'proformas-recientes').json()['proformas']), 6)
