"""Flujo completo de punta a punta por API, con el calculo de precios real, para
los dos tipos de venta: proforma -> nota de trabajo -> nota de venta -> pago.

En cada paso se verifica el estado global de la proforma, el de la nota de
trabajo y de la nota de venta, el descuento de inventario, los importes
(descuento incluido) y el pago (TASK-estados-proforma-nota-trabajo-nota-venta)."""
from decimal import Decimal

from django.test import TestCase

from ..models import Nota_trabajo, Nota_Venta, Proforma_Header, instalador, inventario, pago
from . import helpers
from .ordenes_helpers import WRITE_PERMISSIONS, auth, instalacion_payload, make_scenario, metro_lineal_payload

PERMISOS = WRITE_PERMISSIONS + (
    'delete_proforma_header', 'delete_nota_trabajo', 'delete_nota_venta', 'add_pago', 'delete_pago',
)

BASE = '/product/ordenes'
PROFORMAS = f'{BASE}/proformas'
NOTAS = f'{BASE}/notas-trabajo'
VENTAS = f'{BASE}/notas-venta'


class FlujoBase(TestCase):
    def setUp(self):
        self.s = make_scenario(permissions=PERMISOS, to_install=Decimal('50.00'))
        self.headers = auth(self.s['token'])

    # -- utilidades
    def crear(self, payload):
        response = self.client.post(PROFORMAS, payload, content_type='application/json', **self.headers)
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()

    def post(self, url, body=None):
        return self.client.post(url, body or {}, content_type='application/json', **self.headers)

    def aprobar(self, proforma_id):
        response = self.post(f'{PROFORMAS}/{proforma_id}/generar-nota-trabajo/')
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def resumen(self, nota):
        """(ancho, largo) del resumen de laminas de la nota de trabajo como Decimal."""
        filas = self.client.get(f'{NOTAS}/{nota.pk}/', **self.headers).json()['resumen']
        return [(Decimal(str(f['width'])), Decimal(str(f['length']))) for f in filas]

    def inv(self):
        return inventario.objects.get(pk=self.s['inventario'].pk)

    def estado(self, proforma_id):
        return Proforma_Header.objects.get(pk=proforma_id).status

    def completar_datos_de_instalacion(self, nota):
        inst = instalador.objects.create(name='Instalador', address='Calle 1', phonenumber='70000002')
        inst.sucursal.add(self.s['sucursal'])
        response = self.client.patch(
            f'{NOTAS}/{nota.pk}/', {'instaladar': inst.id, 'codigo_garantia': f'GAR-{nota.pk}'},
            content_type='application/json', **self.headers,
        )
        self.assertEqual(response.status_code, 200, response.content)


class VentaConInstalacionTest(FlujoBase):
    """Item del modelo: 1.50 x 1.00; lamina 120 Bs/m; instalacion 50 Bs por unidad.
    2 unidades: 1.00 * 2 * 120 + 50 * 2 = 340 Bs y 2.00 m de inventario."""

    def test_flujo_completo_con_descuento(self):
        creada = self.crear(instalacion_payload(self.s, discount='40.00', discount_reason='cliente frecuente'))
        proforma_id = creada['id']
        self.assertEqual(creada['status'], 'proforma')
        self.assertEqual(Decimal(creada['total_price']), Decimal('340.00'))
        self.assertEqual(Decimal(creada['total_a_pagar']), Decimal('300.00'))
        self.assertEqual(self.inv().to_install, Decimal('50.00'))  # la proforma no descuenta inventario

        # aprobar: estado, inventario, nota de trabajo y nota de venta
        aprobada = self.aprobar(proforma_id)
        self.assertEqual(aprobada['status'], 'en_trabajo')
        self.assertTrue(aprobada['is_close'])
        self.assertEqual(self.inv().to_install, Decimal('48.00'))
        self.assertEqual(self.inv().installed, Decimal('2.00'))
        nota = Nota_trabajo.objects.get(proforma_id=proforma_id)
        self.assertEqual(nota.status, 'en_proceso')
        self.assertEqual(self.resumen(nota), [(Decimal('1.50'), Decimal('2.00'))])
        nv = Nota_Venta.objects.get(nota_trabajo=nota)
        self.assertEqual((nv.status, nv.total_price), ('por_cobrar', Decimal('300.00')))

        # sin pago mientras el trabajo no este terminado
        self.assertEqual(self.post(f'{VENTAS}/{nv.pk}/pago/').status_code, 409)
        self.assertEqual(pago.objects.count(), 0)

        # terminar exige garantia e instalador
        self.assertEqual(self.post(f'{NOTAS}/{nota.pk}/terminar/').status_code, 409)
        self.completar_datos_de_instalacion(nota)
        terminada = self.post(f'{NOTAS}/{nota.pk}/terminar/')
        self.assertEqual(terminada.status_code, 200, terminada.content)
        self.assertEqual(terminada.json()['status'], 'terminado')
        self.assertEqual(self.estado(proforma_id), 'por_cobrar')
        self.assertEqual(self.inv().to_install, Decimal('48.00'))

        # pago: el monto es el total con descuento; la proforma queda finalizada
        pagado = self.post(f'{VENTAS}/{nv.pk}/pago/', {'tipo_pago': 'efec'})
        self.assertEqual(pagado.status_code, 200, pagado.content)
        self.assertEqual(pagado.json()['status'], 'pagada')
        self.assertEqual(Decimal(pagado.json()['pago']['monto']), Decimal('300.00'))
        self.assertEqual(pagado.json()['pago']['tipo_pago'], 'efec')
        self.assertEqual(self.estado(proforma_id), 'finalizado')
        self.assertEqual(self.inv().to_install, Decimal('48.00'))
        self.assertEqual(self.client.get(PROFORMAS, {'status': 'finalizado'}, **self.headers).json()[0]['id'], proforma_id)

    def test_lineas_de_la_misma_lamina_se_suman_en_el_resumen_y_en_el_inventario(self):
        item = instalacion_payload(self.s)['items'][0]
        creada = self.crear(instalacion_payload(self.s, items=[
            dict(item, quantity=1), dict(item, quantity=3),
        ]))
        self.aprobar(creada['id'])
        nota = Nota_trabajo.objects.get(proforma_id=creada['id'])
        self.assertEqual(self.resumen(nota), [(Decimal('1.50'), Decimal('4.00'))])
        self.assertEqual(self.inv().to_install, Decimal('46.00'))

    def test_anular_antes_de_terminar_devuelve_el_inventario_y_reabre_la_proforma(self):
        creada = self.crear(instalacion_payload(self.s))
        self.aprobar(creada['id'])
        self.assertEqual(self.inv().to_install, Decimal('48.00'))
        nota = Nota_trabajo.objects.get(proforma_id=creada['id'])

        response = self.post(f'{NOTAS}/{nota.pk}/anular/')

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.inv().to_install, Decimal('50.00'))
        self.assertEqual(self.inv().installed, Decimal('0.00'))
        self.assertEqual(self.estado(creada['id']), 'proforma')
        self.assertEqual(Nota_Venta.objects.get(nota_trabajo=nota).status, 'anulada')
        # se puede volver a aprobar y descuenta una sola vez
        self.aprobar(creada['id'])
        self.assertEqual(self.inv().to_install, Decimal('48.00'))
        self.assertEqual(self.estado(creada['id']), 'en_trabajo')

    def test_sin_stock_al_aprobar_no_cambia_nada(self):
        primera = self.crear(instalacion_payload(self.s))
        segunda = self.crear(instalacion_payload(self.s))
        inv = self.inv()
        inv.to_install = Decimal('2.00')  # alcanza solo para una de las dos
        inv.save()
        self.aprobar(primera['id'])

        response = self.post(f'{PROFORMAS}/{segunda["id"]}/generar-nota-trabajo/')

        self.assertEqual(response.status_code, 409, response.content)
        self.assertEqual(self.estado(segunda['id']), 'proforma')
        self.assertFalse(Nota_trabajo.objects.filter(proforma_id=segunda['id']).exists())
        self.assertEqual(self.inv().to_install, Decimal('0.00'))


class VentaPorMetroLinealTest(FlujoBase):
    """3.50 m de lamina a 120 Bs/m = 420 Bs; sin item, cantidad ni instalacion."""

    def test_flujo_completo_con_descuento_sin_garantia_ni_instalador(self):
        creada = self.crear(metro_lineal_payload(self.s, discount='20.00', discount_reason='mayorista'))
        proforma_id = creada['id']
        self.assertEqual(creada['sales_type'], 'venta_metro_lineal')
        self.assertEqual(creada['status'], 'proforma')
        self.assertEqual(Decimal(creada['total_price']), Decimal('420.00'))
        self.assertEqual(Decimal(creada['total_a_pagar']), Decimal('400.00'))

        aprobada = self.aprobar(proforma_id)
        self.assertEqual(aprobada['status'], 'en_trabajo')
        self.assertEqual(self.inv().to_install, Decimal('46.50'))  # 50 - 3.50, sin multiplicar por cantidad
        self.assertEqual(self.inv().installed, Decimal('3.50'))
        nota = Nota_trabajo.objects.get(proforma_id=proforma_id)
        self.assertEqual(self.resumen(nota), [(Decimal('1.50'), Decimal('3.50'))])
        nv = Nota_Venta.objects.get(nota_trabajo=nota)
        self.assertEqual((nv.status, nv.total_price), ('por_cobrar', Decimal('400.00')))

        # metro lineal: se termina sin codigo de garantia ni instalador
        terminada = self.post(f'{NOTAS}/{nota.pk}/terminar/')
        self.assertEqual(terminada.status_code, 200, terminada.content)
        self.assertEqual(self.estado(proforma_id), 'por_cobrar')

        pagado = self.post(f'{VENTAS}/{nv.pk}/pago/', {'tipo_pago': 'trans', 'registro_contable': '1234/26'})
        self.assertEqual(pagado.status_code, 200, pagado.content)
        self.assertEqual(Decimal(pagado.json()['pago']['monto']), Decimal('400.00'))
        self.assertEqual(pagado.json()['pago']['registro_contable'], '1234/26')
        self.assertEqual(self.estado(proforma_id), 'finalizado')
        self.assertEqual(self.inv().to_install, Decimal('46.50'))

    def test_anular_devuelve_exactamente_los_metros_descontados(self):
        creada = self.crear(metro_lineal_payload(self.s))
        self.aprobar(creada['id'])
        nota = Nota_trabajo.objects.get(proforma_id=creada['id'])
        self.assertEqual(self.inv().to_install, Decimal('46.50'))

        self.assertEqual(self.post(f'{NOTAS}/{nota.pk}/anular/').status_code, 200)

        self.assertEqual(self.inv().to_install, Decimal('50.00'))
        self.assertEqual(self.inv().installed, Decimal('0.00'))
        self.assertEqual(self.estado(creada['id']), 'proforma')

    def test_eliminar_la_nota_desde_el_admin_tambien_devuelve_los_metros(self):
        # regresion: delete_work_note multiplicaba por quantity=0 y no devolvia nada en metro lineal
        from ..business.orden_trabajo import Orden_Trabajo_Business
        creada = self.crear(metro_lineal_payload(self.s))
        self.aprobar(creada['id'])
        nota = Nota_trabajo.objects.get(proforma_id=creada['id'])

        Orden_Trabajo_Business().delete_work_note(nota)

        self.assertEqual(self.inv().to_install, Decimal('50.00'))
        self.assertEqual(self.estado(creada['id']), 'proforma')

    def test_sin_stock_al_aprobar_no_cambia_nada(self):
        primera = self.crear(metro_lineal_payload(self.s, items=[
            {'window_film': self.s['film'].id, 'width': '1.50', 'length': '30.00'}]))
        segunda = self.crear(metro_lineal_payload(self.s, items=[
            {'window_film': self.s['film'].id, 'width': '1.50', 'length': '30.00'}]))
        self.aprobar(primera['id'])

        response = self.post(f'{PROFORMAS}/{segunda["id"]}/generar-nota-trabajo/')

        self.assertEqual(response.status_code, 409, response.content)
        self.assertEqual(self.estado(segunda['id']), 'proforma')
        self.assertEqual(self.inv().to_install, Decimal('20.00'))


class GestionDePagosTest(FlujoBase):
    def aprobada_y_terminada(self):
        creada = self.crear(metro_lineal_payload(self.s))
        self.aprobar(creada['id'])
        nota = Nota_trabajo.objects.get(proforma_id=creada['id'])
        self.assertEqual(self.post(f'{NOTAS}/{nota.pk}/terminar/').status_code, 200)
        return creada['id'], Nota_Venta.objects.get(nota_trabajo=nota)

    def test_tipos_de_pago_efectivo_y_tarjeta_qr(self):
        for tipo, etiqueta in (('efec', 'Efectivo'), ('trans', 'Targeta/QR')):
            _, nv = self.aprobada_y_terminada()
            pagado = self.post(f'{VENTAS}/{nv.pk}/pago/', {'tipo_pago': tipo})
            self.assertEqual(pagado.status_code, 200, pagado.content)
            self.assertEqual(pagado.json()['pago']['tipo_pago_label'], etiqueta)

    def test_pago_anulado_puede_registrarse_de_nuevo(self):
        proforma_id, nv = self.aprobada_y_terminada()
        self.post(f'{VENTAS}/{nv.pk}/pago/', {'tipo_pago': 'efec'})
        self.assertEqual(self.estado(proforma_id), 'finalizado')

        self.assertEqual(self.post(f'{VENTAS}/{nv.pk}/anular-pago/').status_code, 200)
        self.assertEqual(self.estado(proforma_id), 'por_cobrar')
        self.assertEqual(pago.objects.count(), 0)

        segundo = self.post(f'{VENTAS}/{nv.pk}/pago/', {'tipo_pago': 'trans'})
        self.assertEqual(segundo.status_code, 200, segundo.content)
        self.assertEqual(self.estado(proforma_id), 'finalizado')
        self.assertEqual(pago.objects.get().tipo_pago, 'trans')

    def test_una_nota_pagada_no_se_puede_anular_ni_volver_a_pagar(self):
        proforma_id, nv = self.aprobada_y_terminada()
        self.post(f'{VENTAS}/{nv.pk}/pago/', {'tipo_pago': 'efec'})
        self.assertEqual(self.post(f'{VENTAS}/{nv.pk}/pago/', {'tipo_pago': 'efec'}).status_code, 409)
        self.assertEqual(self.post(f'{VENTAS}/{nv.pk}/anular/').status_code, 409)
        self.assertEqual(pago.objects.count(), 1)
        self.assertEqual(self.estado(proforma_id), 'finalizado')

    def test_el_registro_contable_no_se_repite_entre_pagos(self):
        _, primera = self.aprobada_y_terminada()
        _, segunda = self.aprobada_y_terminada()
        self.assertEqual(self.post(f'{VENTAS}/{primera.pk}/pago/', {'registro_contable': '1234/26'}).status_code, 200)
        repetido = self.post(f'{VENTAS}/{segunda.pk}/pago/', {'registro_contable': '1234/26'})
        self.assertEqual(repetido.status_code, 409, repetido.content)
        self.assertEqual(Nota_Venta.objects.get(pk=segunda.pk).status, 'por_cobrar')
        self.assertEqual(pago.objects.count(), 1)
