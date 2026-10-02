"""API de los reportes Ventas Diarias y Utilidad: permisos, alcance por sucursal,
validacion y contenido (TASK-reportes-utilidad-ventas-diarias)."""
from decimal import Decimal

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from . import helpers
from .reportes_helpers import METRO_LINEAL, create_venta_cobrada, dia, linea

VENTAS = '/product/reportes/ventas-diarias'
UTILIDAD = '/product/reportes/utilidad'
RANGO = {'desde': '2026-09-01', 'hasta': '2026-09-30'}
CAMPOS_DE_COSTO = {'costo_compra', 'utilidad_antes', 'utilidad_despues', 'margen', 'costo_incompleto',
                   'ventas_costo_incompleto', 'por_lamina'}


def _claves(datos, acumulado=None):
    """Todas las claves que aparecen en cualquier nivel de un JSON."""
    acumulado = set() if acumulado is None else acumulado
    if isinstance(datos, dict):
        for clave, valor in datos.items():
            acumulado.add(clave)
            _claves(valor, acumulado)
    elif isinstance(datos, list):
        for item in datos:
            _claves(item, acumulado)
    return acumulado


class ReportesApiTestBase(TestCase):

    def setUp(self):
        self.owner, _ = helpers.create_user_with_token()
        self.sucursal_a = helpers.create_sucursal(self.owner)
        self.sucursal_b = helpers.create_sucursal(self.owner)
        self.inv_a = helpers.create_inventario(sucursal=self.sucursal_a, precio_compra_mtr_lineal=Decimal('80.00'))
        self.inv_b = helpers.create_inventario(sucursal=self.sucursal_b, precio_compra_mtr_lineal=Decimal('80.00'))
        self.venta_a = create_venta_cobrada(
            self.owner, self.sucursal_a, pagado_en=dia(2026, 9, 10), lineas=[
                linea(2, quantity=2, price='120.00', install='50.00', inventario=self.inv_a, movimientos=[(self.inv_a, 4)]),
            ])
        self.venta_b = create_venta_cobrada(
            self.owner, self.sucursal_b, sales_type=METRO_LINEAL, tipo_pago='trans', pagado_en=dia(2026, 9, 11), lineas=[
                linea(3, price='100.00', inventario=self.inv_b, movimientos=[(self.inv_b, 3)]),
            ])

    def usuario(self, grupo=None, permisos=(), sucursales=(), staff=True):
        user, token, _ = helpers.create_staff_user_with_token(is_staff=staff)
        if grupo:
            helpers.add_user_to_group(user, grupo)
        for codename in permisos:
            helpers.grant_permission(user, 'product', codename)
        for sucursal in sucursales:
            sucursal.empleado.add(user)
        return user, token

    def get(self, url, token=None, **params):
        headers = {'HTTP_AUTHORIZATION': f'Token {token.key}'} if token else {}
        return self.client.get(url, params, **headers)


class ReportesPermisosTest(ReportesApiTestBase):

    def test_sin_token_es_401(self):
        self.assertEqual(self.get(VENTAS, **RANGO).status_code, 401)

    def test_no_staff_es_403(self):
        _, token = self.usuario(permisos=['view_proxy_pagos', 'view_utilidades'], staff=False)
        self.assertEqual(self.get(VENTAS, token, **RANGO).status_code, 403)

    def test_sin_permiso_es_403_en_ambos_reportes(self):
        _, token = self.usuario(grupo='Vendedor', sucursales=[self.sucursal_a])
        self.assertEqual(self.get(VENTAS, token, **RANGO).status_code, 403)
        self.assertEqual(self.get(UTILIDAD, token, **RANGO).status_code, 403)

    def test_admin_con_ambos_permisos_accede_a_ambos(self):
        _, token = self.usuario(grupo='Admin', permisos=['view_proxy_pagos', 'view_utilidades'], sucursales=[self.sucursal_a, self.sucursal_b])
        self.assertEqual(self.get(VENTAS, token, **RANGO).status_code, 200)
        self.assertEqual(self.get(UTILIDAD, token, **RANGO).status_code, 200)

    def test_caja_ve_ventas_diarias_pero_no_utilidad(self):
        _, token = self.usuario(grupo='Caja', permisos=['view_proxy_pagos'], sucursales=[self.sucursal_a])
        self.assertEqual(self.get(VENTAS, token, **RANGO).status_code, 200)
        self.assertEqual(self.get(UTILIDAD, token, **RANGO).status_code, 403)

    def test_ventas_diarias_no_expone_costos_utilidad_ni_margenes(self):
        _, token = self.usuario(grupo='Admin', permisos=['view_proxy_pagos'], sucursales=[self.sucursal_a, self.sucursal_b])
        respuesta = self.get(VENTAS, token, **RANGO)
        self.assertEqual(respuesta.status_code, 200)
        self.assertGreater(len(respuesta.json()['rows']), 0)
        self.assertFalse(_claves(respuesta.json()) & CAMPOS_DE_COSTO)


class ReportesAlcanceTest(ReportesApiTestBase):

    def test_admin_con_ambas_sucursales_las_ve_todas(self):
        _, token = self.usuario(grupo='Admin', permisos=['view_proxy_pagos'], sucursales=[self.sucursal_a, self.sucursal_b])
        filas = self.get(VENTAS, token, **RANGO).json()['rows']
        self.assertEqual({f['nota_venta_id'] for f in filas},
                         {self.venta_a['nota_venta'].id, self.venta_b['nota_venta'].id})

    def test_admin_solo_ve_su_sucursal_asignada(self):
        _, token = self.usuario(grupo='Admin', permisos=['view_proxy_pagos'], sucursales=[self.sucursal_a])
        filas = self.get(VENTAS, token, **RANGO).json()['rows']
        self.assertEqual([f['nota_venta_id'] for f in filas], [self.venta_a['nota_venta'].id])
        self.assertEqual(self.get(VENTAS, token, sucursal=self.sucursal_b.id, **RANGO).status_code, 404)

    def test_admin_sin_sucursal_no_ve_nada(self):
        _, token = self.usuario(grupo='Admin', permisos=['view_proxy_pagos'])
        datos = self.get(VENTAS, token, **RANGO).json()
        self.assertEqual(datos['rows'], [])
        self.assertTrue(datos['sin_sucursal'])

    def test_superusuario_ve_todas_las_sucursales(self):
        _, token, _ = helpers.create_superuser_with_token()
        datos = self.get(VENTAS, token, **RANGO).json()
        self.assertEqual({f['nota_venta_id'] for f in datos['rows']},
                         {self.venta_a['nota_venta'].id, self.venta_b['nota_venta'].id})
        self.assertFalse(datos['sin_sucursal'])


class ReportesMultiSucursalTest(ReportesApiTestBase):
    """?sucursales=1,2 (ADR-...-filtro-multisucursal-reportes): lista dentro del alcance
    de lectura; sin pedir ninguna, "Todas" = las activas del alcance."""

    def setUp(self):
        super().setUp()
        _, self.token = self.usuario(
            grupo='Caja', permisos=['view_proxy_pagos', 'view_utilidades'],
            sucursales=[self.sucursal_a, self.sucursal_b])

    def ids(self, **params):
        filas = self.get(VENTAS, self.token, **params, **RANGO).json()['rows']
        return {f['nota_venta_id'] for f in filas}

    def test_lista_separada_por_comas(self):
        self.assertEqual(self.ids(sucursales=f'{self.sucursal_a.id},{self.sucursal_b.id}'),
                         {self.venta_a['nota_venta'].id, self.venta_b['nota_venta'].id})
        self.assertEqual(self.ids(sucursales=str(self.sucursal_b.id)), {self.venta_b['nota_venta'].id})

    def test_sucursales_y_sucursal_se_unen(self):
        self.assertEqual(self.ids(sucursales=str(self.sucursal_a.id), sucursal=self.sucursal_b.id),
                         {self.venta_a['nota_venta'].id, self.venta_b['nota_venta'].id})

    def test_sucursal_ajena_en_la_lista_es_404(self):
        ajena = helpers.create_sucursal(helpers.create_user_with_token()[0])
        respuesta = self.get(VENTAS, self.token, sucursales=f'{self.sucursal_a.id},{ajena.id}', **RANGO)
        self.assertEqual(respuesta.status_code, 404)

    def test_formato_invalido_es_400(self):
        for valor in ('abc', '1,,2', '1,a', ',1'):
            self.assertEqual(self.get(VENTAS, self.token, sucursales=valor, **RANGO).status_code, 400, valor)

    def test_todas_excluye_sucursales_inactivas_por_defecto(self):
        self.sucursal_b.enable_to_install_windows_film = False
        self.sucursal_b.save(update_fields=['enable_to_install_windows_film'])
        self.assertEqual(self.ids(), {self.venta_a['nota_venta'].id})

    def test_sucursal_inactiva_se_puede_pedir_explicitamente(self):
        self.sucursal_b.enable_to_install_windows_film = False
        self.sucursal_b.save(update_fields=['enable_to_install_windows_film'])
        self.assertEqual(self.ids(sucursal=self.sucursal_b.id), {self.venta_b['nota_venta'].id})
        self.assertEqual(self.ids(sucursales=f'{self.sucursal_a.id},{self.sucursal_b.id}'),
                         {self.venta_a['nota_venta'].id, self.venta_b['nota_venta'].id})

    def test_utilidad_acepta_la_lista(self):
        respuesta = self.get(UTILIDAD, self.token, sucursales=str(self.sucursal_a.id), **RANGO)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual({v['nota_venta_id'] for v in respuesta.json()['ventas']}, {self.venta_a['nota_venta'].id})

    def test_empleado_solo_ve_sus_sucursales_y_todas_las_suyas(self):
        _, token_a = self.usuario(grupo='Caja', permisos=['view_proxy_pagos'], sucursales=[self.sucursal_a])
        filas = self.get(VENTAS, token_a, **RANGO).json()['rows']
        self.assertEqual([f['nota_venta_id'] for f in filas], [self.venta_a['nota_venta'].id])
        _, token_ab = self.usuario(grupo='Caja', permisos=['view_proxy_pagos'], sucursales=[self.sucursal_a, self.sucursal_b])
        self.assertEqual(len(self.get(VENTAS, token_ab, **RANGO).json()['rows']), 2)

    def test_sucursal_ajena_en_el_filtro_es_404(self):
        _, token = self.usuario(grupo='Caja', permisos=['view_proxy_pagos'], sucursales=[self.sucursal_a])
        self.assertEqual(self.get(VENTAS, token, sucursal=self.sucursal_b.id, **RANGO).status_code, 404)
        self.assertEqual(self.get(VENTAS, token, sucursal=self.sucursal_a.id, **RANGO).status_code, 200)

    def test_sin_sucursal_devuelve_vacio_con_indicador(self):
        _, token = self.usuario(grupo='Caja', permisos=['view_proxy_pagos'])
        datos = self.get(VENTAS, token, **RANGO).json()
        self.assertEqual(datos['rows'], [])
        self.assertTrue(datos['sin_sucursal'])
        self.assertEqual(datos['totales']['ventas'], 0)

    def test_con_sucursal_y_sin_ventas_no_activa_el_indicador(self):
        vacia = helpers.create_sucursal(helpers.create_user_with_token()[0])
        _, token = self.usuario(grupo='Caja', permisos=['view_proxy_pagos'], sucursales=[vacia])
        datos = self.get(VENTAS, token, **RANGO).json()
        self.assertEqual(datos['rows'], [])
        self.assertFalse(datos['sin_sucursal'])


class ReportesValidacionTest(ReportesApiTestBase):

    def setUp(self):
        super().setUp()
        _, self.token = self.usuario(grupo='Admin', permisos=['view_proxy_pagos', 'view_utilidades'], sucursales=[self.sucursal_a, self.sucursal_b])

    def test_desde_y_hasta_son_obligatorios(self):
        self.assertEqual(self.get(VENTAS, self.token).status_code, 400)
        self.assertEqual(self.get(VENTAS, self.token, desde='2026-09-01').status_code, 400)
        self.assertEqual(self.get(UTILIDAD, self.token, hasta='2026-09-01').status_code, 400)

    def test_formato_de_fecha_invalido(self):
        self.assertEqual(self.get(VENTAS, self.token, desde='01/09/2026', hasta='2026-09-30').status_code, 400)

    def test_rango_invertido_y_rango_excesivo(self):
        invertido = self.get(VENTAS, self.token, desde='2026-09-30', hasta='2026-09-01')
        self.assertEqual(invertido.status_code, 400)
        self.assertIn('fecha inicial', str(invertido.json()))
        self.assertEqual(self.get(UTILIDAD, self.token, desde='2025-01-01', hasta='2026-09-30').status_code, 400)

    def test_valores_desconocidos_de_filtro(self):
        self.assertEqual(self.get(VENTAS, self.token, sales_type='otro', **RANGO).status_code, 400)
        self.assertEqual(self.get(VENTAS, self.token, tipo_pago='otro', **RANGO).status_code, 400)
        self.assertEqual(self.get(VENTAS, self.token, sucursal='abc', **RANGO).status_code, 400)


class ReportesContenidoTest(ReportesApiTestBase):

    def setUp(self):
        super().setUp()
        _, self.token = self.usuario(grupo='Admin', permisos=['view_proxy_pagos', 'view_utilidades'], sucursales=[self.sucursal_a, self.sucursal_b])

    def test_ventas_diarias_filtra_por_tipo_de_venta_y_de_pago(self):
        solo_metro = self.get(VENTAS, self.token, sales_type=METRO_LINEAL, **RANGO).json()
        self.assertEqual([f['nota_venta_id'] for f in solo_metro['rows']], [self.venta_b['nota_venta'].id])
        solo_efec = self.get(VENTAS, self.token, tipo_pago='efec', **RANGO).json()
        self.assertEqual([f['nota_venta_id'] for f in solo_efec['rows']], [self.venta_a['nota_venta'].id])

    def test_ventas_diarias_totales_y_desgloses(self):
        datos = self.get(VENTAS, self.token, **RANGO).json()
        self.assertEqual(datos['totales']['ventas'], 2)
        self.assertEqual(datos['totales']['cobrado'], '880.00')   # 580 + 300
        self.assertEqual(datos['totales']['instalacion'], '100.00')
        por_tipo = {f['sales_type']: f for f in datos['por_tipo_venta']}
        self.assertEqual(por_tipo['venta_instalacion']['cobrado'], '580.00')
        self.assertEqual(por_tipo['venta_metro_lineal']['cobrado'], '300.00')
        por_pago = {f['tipo_pago']: f for f in datos['por_tipo_pago']}
        self.assertEqual(por_pago['trans']['cobrado'], '300.00')

    def test_utilidad_devuelve_costos_utilidad_y_detalle_por_lamina(self):
        datos = self.get(UTILIDAD, self.token, **RANGO).json()
        self.assertEqual(datos['totales']['costo_compra'], '560.00')       # 320 + 240
        self.assertEqual(datos['totales']['utilidad_antes'], '220.00')     # 160 + 60
        self.assertEqual(len(datos['ventas']), 2)
        self.assertEqual(len(datos['por_lamina']), 2)
        self.assertEqual(datos['totales']['ventas_costo_incompleto'], 0)

    def test_una_venta_fuera_del_rango_de_fechas_no_aparece(self):
        fuera = create_venta_cobrada(self.owner, self.sucursal_a, pagado_en=dia(2026, 10, 1), lineas=[linea(1, price='100.00')])
        datos = self.get(UTILIDAD, self.token, **RANGO).json()
        self.assertNotIn(fuera['nota_venta'].id, [f['nota_venta_id'] for f in datos['ventas']])

    def test_los_importes_se_serializan_como_texto_decimal(self):
        fila = self.get(VENTAS, self.token, **RANGO).json()['rows'][0]
        for campo in ('venta_lamina', 'instalacion', 'bruto', 'descuento', 'cobrado'):
            self.assertIsInstance(fila[campo], str)

    def test_numero_de_consultas_no_crece_con_las_ventas(self):
        def consultas():
            with CaptureQueriesContext(connection) as capturadas:
                self.assertEqual(self.get(UTILIDAD, self.token, **RANGO).status_code, 200)
            return len(capturadas)

        antes = consultas()
        for indice in range(5):
            create_venta_cobrada(self.owner, self.sucursal_a, pagado_en=dia(2026, 9, 12 + indice), lineas=[
                linea(1, quantity=1, price='100.00', install='10.00', inventario=self.inv_a, movimientos=[(self.inv_a, 1)]),
            ])
        self.assertEqual(consultas(), antes)
