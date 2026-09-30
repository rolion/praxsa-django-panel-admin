"""API de estados, notas de venta y pagos (TASK-estados-proforma-nota-trabajo-nota-venta):
cadena completa aprobar -> terminar -> pagar, retrocesos, alcance por sucursal y
permisos por grupo (asignados con el comando asignar_permisos_estados)."""
from decimal import Decimal
from io import StringIO

from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase

from ..models import Nota_trabajo, Nota_Venta, Proforma_Header, instalador, inventario, pago
from . import helpers
from .ordenes_helpers import auth, instalacion_payload, make_scenario, make_staff

BASE = '/product/ordenes'
PROFORMAS = f'{BASE}/proformas'
NOTAS = f'{BASE}/notas-trabajo'
VENTAS = f'{BASE}/notas-venta'


class OrdenApiBase(TestCase):
    """El dueno (make_scenario) tiene todos los permisos de escritura de proforma/nota;
    los usuarios por grupo reciben los suyos con el comando asignar_permisos_estados."""

    def setUp(self):
        self.s = make_scenario()
        self.owner_headers = auth(self.s['token'])
        for nombre in ('Admin', 'Caja', 'Vendedor', 'Almacen'):
            Group.objects.get_or_create(name=nombre)
        call_command('asignar_permisos_estados', stdout=StringIO())
        self.users = {}
        for nombre in ('Caja', 'Vendedor', 'Almacen'):
            user, token = make_staff(permissions=(), group=nombre)
            self.s['sucursal'].empleado.add(user)
            self.users[nombre] = auth(token)

    # -- construccion de ordenes en cada etapa
    def nueva_proforma(self):
        return self.client.post(PROFORMAS, instalacion_payload(self.s), content_type='application/json',
                                **self.owner_headers).json()['id']

    def aprobada(self):
        proforma_id = self.nueva_proforma()
        self.assertEqual(self.client.post(f'{PROFORMAS}/{proforma_id}/generar-nota-trabajo/', **self.owner_headers).status_code, 200)
        nota = Nota_trabajo.objects.get(proforma_id=proforma_id)
        return proforma_id, nota, Nota_Venta.objects.get(nota_trabajo=nota)

    def terminada(self):
        proforma_id, nota, nv = self.aprobada()
        inst = instalador.objects.create(name='Instalador', address='Calle 1', phonenumber='70000002')
        inst.sucursal.add(self.s['sucursal'])
        Nota_trabajo.objects.filter(pk=nota.pk).update(codigo_garantia=f'G{nota.pk}', instaladar=inst)
        response = self.client.post(f'{NOTAS}/{nota.pk}/terminar/', **self.owner_headers)
        self.assertEqual(response.status_code, 200, response.content)
        return proforma_id, nota, nv

    def post(self, url, headers, body=None):
        return self.client.post(url, body or {}, content_type='application/json', **headers)

    def to_install(self):
        return inventario.objects.get(pk=self.s['inventario'].pk).to_install


class CadenaCompletaTest(OrdenApiBase):
    def test_aprobar_terminar_pagar(self):
        proforma_id, nota, nv = self.aprobada()
        detalle = self.client.get(f'{PROFORMAS}/{proforma_id}/', **self.owner_headers).json()
        self.assertEqual(detalle['status'], 'en_trabajo')
        self.assertEqual(self.to_install(), Decimal('48.00'))
        self.assertEqual(nv.status, 'por_cobrar')

        # no se puede pagar con el trabajo en proceso
        response = self.post(f'{VENTAS}/{nv.pk}/pago/', self.users['Caja'], {'tipo_pago': 'efec'})
        self.assertEqual(response.status_code, 409, response.content)
        self.assertIn('terminado', response.json()['detail'])

        # no se puede terminar sin garantia / instalador
        self.assertEqual(self.post(f'{NOTAS}/{nota.pk}/terminar/', self.users['Almacen']).status_code, 409)

        inst = instalador.objects.create(name='Instalador', address='Calle 1', phonenumber='70000002')
        inst.sucursal.add(self.s['sucursal'])
        patch = self.client.patch(f'{NOTAS}/{nota.pk}/', {'instaladar': inst.id, 'codigo_garantia': 'GAR-1'},
                                  content_type='application/json', **self.owner_headers)
        self.assertEqual(patch.status_code, 200, patch.content)

        terminada = self.post(f'{NOTAS}/{nota.pk}/terminar/', self.users['Almacen'])
        self.assertEqual(terminada.status_code, 200, terminada.content)
        self.assertEqual(terminada.json()['status'], 'terminado')
        self.assertEqual(terminada.json()['nota_venta']['status'], 'por_cobrar')
        self.assertIsNotNone(terminada.json()['salida_vehiculo'])
        self.assertEqual(self.client.get(f'{PROFORMAS}/{proforma_id}/', **self.owner_headers).json()['status'], 'por_cobrar')

        # la nota terminada ya no se edita
        edit = self.client.patch(f'{NOTAS}/{nota.pk}/', {'observaciones': 'x'}, content_type='application/json', **self.owner_headers)
        self.assertEqual(edit.status_code, 409)

        pagado = self.post(f'{VENTAS}/{nv.pk}/pago/', self.users['Caja'],
                           {'tipo_pago': 'trans', 'registro_contable': '1234/26', 'monto': '1.00'})
        self.assertEqual(pagado.status_code, 200, pagado.content)
        data = pagado.json()
        self.assertEqual(data['status'], 'pagada')
        self.assertEqual(data['pago']['monto'], str(nv.total_price))  # el monto del cliente se ignora
        self.assertEqual(data['pago']['tipo_pago'], 'trans')
        self.assertFalse(data['pago']['cerrado'])
        self.assertEqual(self.client.get(f'{PROFORMAS}/{proforma_id}/', **self.owner_headers).json()['status'], 'finalizado')

    def test_doble_pago_deja_un_solo_pago(self):
        _, _, nv = self.terminada()
        self.assertEqual(self.post(f'{VENTAS}/{nv.pk}/pago/', self.users['Caja']).status_code, 200)
        self.assertEqual(self.post(f'{VENTAS}/{nv.pk}/pago/', self.users['Caja']).status_code, 409)
        self.assertEqual(pago.objects.filter(nota_venta=nv).count(), 1)

    def test_tipo_de_pago_invalido_es_400(self):
        _, _, nv = self.terminada()
        self.assertEqual(self.post(f'{VENTAS}/{nv.pk}/pago/', self.users['Caja'], {'tipo_pago': 'bitcoin'}).status_code, 400)
        self.assertEqual(self.post(f'{VENTAS}/{nv.pk}/pago/', self.users['Caja'], {'registro_contable': 'xx'}).status_code, 400)
        self.assertEqual(pago.objects.count(), 0)

    def test_anular_pago_y_corregir_trabajo(self):
        proforma_id, nota, nv = self.terminada()
        self.post(f'{VENTAS}/{nv.pk}/pago/', self.users['Caja'])
        # con pago no se corrige el trabajo
        self.assertEqual(self.post(f'{NOTAS}/{nota.pk}/corregir/', self.users['Almacen']).status_code, 409)

        anulado = self.post(f'{VENTAS}/{nv.pk}/anular-pago/', self.users['Caja'])
        self.assertEqual(anulado.status_code, 200, anulado.content)
        self.assertEqual(anulado.json()['status'], 'por_cobrar')
        self.assertIsNone(anulado.json()['pago'])
        self.assertEqual(self.client.get(f'{PROFORMAS}/{proforma_id}/', **self.owner_headers).json()['status'], 'por_cobrar')

        corregida = self.post(f'{NOTAS}/{nota.pk}/corregir/', self.users['Almacen'])
        self.assertEqual(corregida.status_code, 200, corregida.content)
        self.assertEqual(corregida.json()['status'], 'en_proceso')

    def test_pago_cerrado_no_se_anula(self):
        _, _, nv = self.terminada()
        self.post(f'{VENTAS}/{nv.pk}/pago/', self.users['Caja'])
        pago.objects.filter(nota_venta=nv).update(cerrado=True)
        self.assertEqual(self.post(f'{VENTAS}/{nv.pk}/anular-pago/', self.users['Caja']).status_code, 409)
        self.assertEqual(pago.objects.filter(nota_venta=nv).count(), 1)

    def test_anular_pago_sin_pago_es_409(self):
        _, _, nv = self.terminada()
        self.assertEqual(self.post(f'{VENTAS}/{nv.pk}/anular-pago/', self.users['Caja']).status_code, 409)


class AnulacionesApiTest(OrdenApiBase):
    def assert_reabierta(self, proforma_id, nota, nv):
        self.assertEqual(Nota_trabajo.objects.get(pk=nota.pk).status, 'cancelada')
        self.assertEqual(Nota_Venta.objects.get(pk=nv.pk).status, 'anulada')
        self.assertEqual(Proforma_Header.objects.get(pk=proforma_id).status, 'proforma')
        self.assertEqual(self.to_install(), Decimal('50.00'))

    def test_anular_nota_de_trabajo_equivale_a_reabrir(self):
        proforma_id, nota, nv = self.aprobada()
        response = self.post(f'{NOTAS}/{nota.pk}/anular/', self.users['Almacen'])
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['status'], 'cancelada')
        self.assert_reabierta(proforma_id, nota, nv)
        # la proforma vuelve a poder editarse y reaprobarse
        edit = self.client.patch(f'{PROFORMAS}/{proforma_id}/', {'name': 'Editada'}, content_type='application/json', **self.owner_headers)
        self.assertEqual(edit.status_code, 200, edit.content)
        again = self.client.post(f'{PROFORMAS}/{proforma_id}/generar-nota-trabajo/', **self.owner_headers)
        self.assertEqual(again.status_code, 200, again.content)
        self.assertEqual(Nota_trabajo.objects.filter(proforma_id=proforma_id).count(), 1)

    def test_anular_nota_de_venta_hace_lo_mismo(self):
        proforma_id, nota, nv = self.aprobada()
        response = self.post(f'{VENTAS}/{nv.pk}/anular/', self.users['Caja'])
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['status'], 'anulada')
        self.assert_reabierta(proforma_id, nota, nv)

    def test_con_trabajo_terminado_no_se_anula(self):
        _, nota, nv = self.terminada()
        self.assertEqual(self.post(f'{NOTAS}/{nota.pk}/anular/', self.users['Almacen']).status_code, 409)
        self.assertEqual(self.post(f'{VENTAS}/{nv.pk}/anular/', self.users['Caja']).status_code, 409)

    def test_anular_proforma_vigente(self):
        proforma_id = self.nueva_proforma()
        response = self.post(f'{PROFORMAS}/{proforma_id}/anular/', self.users['Vendedor'])
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['status'], 'anulada')
        self.assertEqual(self.client.get(PROFORMAS, {'status': 'anulada'}, **self.owner_headers).json()[0]['id'], proforma_id)
        # anulada: no se edita ni se aprueba
        self.assertEqual(self.client.patch(f'{PROFORMAS}/{proforma_id}/', {'name': 'X'}, content_type='application/json',
                                           **self.owner_headers).status_code, 409)
        self.assertEqual(self.client.post(f'{PROFORMAS}/{proforma_id}/generar-nota-trabajo/', **self.owner_headers).status_code, 409)

    def test_no_se_anula_una_proforma_aprobada(self):
        proforma_id, _, _ = self.aprobada()
        self.assertEqual(self.post(f'{PROFORMAS}/{proforma_id}/anular/', self.users['Vendedor']).status_code, 409)


class PermisosPorGrupoTest(OrdenApiBase):
    def test_almacen_no_aprueba_ni_cobra_ni_anula_la_venta(self):
        proforma_id = self.nueva_proforma()
        headers = self.users['Almacen']
        self.assertEqual(self.post(f'{PROFORMAS}/{proforma_id}/generar-nota-trabajo/', headers).status_code, 403)
        self.assertEqual(self.post(f'{PROFORMAS}/{proforma_id}/anular/', headers).status_code, 403)
        _, nota, nv = self.terminada()
        self.assertEqual(self.post(f'{VENTAS}/{nv.pk}/pago/', headers).status_code, 403)
        self.assertEqual(self.post(f'{VENTAS}/{nv.pk}/anular/', headers).status_code, 403)
        self.assertEqual(self.post(f'{VENTAS}/{nv.pk}/anular-pago/', headers).status_code, 403)
        self.assertEqual(Nota_Venta.objects.get(pk=nv.pk).status, 'por_cobrar')

    def test_caja_cobra_y_anula_ventas_pero_no_termina_ni_anula_trabajo(self):
        _, nota, nv = self.aprobada()
        headers = self.users['Caja']
        self.assertEqual(self.post(f'{NOTAS}/{nota.pk}/terminar/', headers).status_code, 403)
        self.assertEqual(self.post(f'{NOTAS}/{nota.pk}/corregir/', headers).status_code, 403)
        self.assertEqual(self.post(f'{NOTAS}/{nota.pk}/anular/', headers).status_code, 403)
        self.assertEqual(self.post(f'{PROFORMAS}/{nota.proforma_id}/generar-nota-trabajo/', headers).status_code, 403)
        self.assertEqual(self.post(f'{VENTAS}/{nv.pk}/anular/', headers).status_code, 200)

    def test_vendedor_aprueba_anula_y_edita_proformas_pero_no_termina_trabajo(self):
        headers = self.users['Vendedor']
        proforma_id = self.nueva_proforma()
        edit = self.client.patch(f'{PROFORMAS}/{proforma_id}/', {'name': 'Editada'}, content_type='application/json', **headers)
        self.assertEqual(edit.status_code, 200, edit.content)
        aprobar = self.post(f'{PROFORMAS}/{proforma_id}/generar-nota-trabajo/', headers)
        self.assertEqual(aprobar.status_code, 200, aprobar.content)
        nota = Nota_trabajo.objects.get(proforma_id=proforma_id)
        self.assertEqual(self.post(f'{NOTAS}/{nota.pk}/terminar/', headers).status_code, 403)
        self.assertEqual(self.post(f'{NOTAS}/{nota.pk}/anular/', headers).status_code, 403)
        otra = self.nueva_proforma()
        self.assertEqual(self.post(f'{PROFORMAS}/{otra}/anular/', headers).status_code, 200)

    def test_sin_permiso_de_pago_es_403(self):
        _, _, nv = self.terminada()
        user, token = make_staff(permissions=(), group='Sin permisos')
        self.s['sucursal'].empleado.add(user)
        self.assertEqual(self.post(f'{VENTAS}/{nv.pk}/pago/', auth(token)).status_code, 403)
        self.assertEqual(pago.objects.count(), 0)


class AlcanceNotasVentaTest(OrdenApiBase):
    def test_listado_y_detalle_con_filtros(self):
        proforma_id, nota, nv = self.aprobada()
        rows = self.client.get(VENTAS, **self.users['Caja']).json()
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row['id'], nv.pk)
        self.assertEqual(row['status'], 'por_cobrar')
        self.assertEqual(row['work_status'], 'en_proceso')
        self.assertEqual(row['proforma_id'], proforma_id)
        self.assertEqual(row['sucursal_id'], self.s['sucursal'].id)
        self.assertEqual(len(self.client.get(VENTAS, {'status': 'pagada'}, **self.users['Caja']).json()), 0)
        self.assertEqual(len(self.client.get(VENTAS, {'status': 'por_cobrar'}, **self.users['Caja']).json()), 1)
        self.assertEqual(len(self.client.get(VENTAS, {'search': str(proforma_id)}, **self.users['Caja']).json()), 1)
        self.assertEqual(len(self.client.get(VENTAS, {'search': 'ABC123'}, **self.users['Caja']).json()), 1)
        self.assertEqual(self.client.get(VENTAS, {'search': 'zzz'}, **self.users['Caja']).json(), [])
        detalle = self.client.get(f'{VENTAS}/{nv.pk}/', **self.users['Caja']).json()
        self.assertIsNone(detalle['pago'])
        self.assertEqual(detalle['car_plate'], 'ABC123')

    def test_usuario_de_otra_sucursal_no_ve_ni_opera_la_nota(self):
        _, _, nv = self.terminada()
        ajeno, token = make_staff(permissions=(), group='Caja')
        helpers.create_sucursal(ajeno)
        headers = auth(token)
        self.assertEqual(self.client.get(VENTAS, **headers).json(), [])
        self.assertEqual(self.client.get(f'{VENTAS}/{nv.pk}/', **headers).status_code, 404)
        self.assertEqual(self.post(f'{VENTAS}/{nv.pk}/pago/', headers).status_code, 404)
        self.assertEqual(self.post(f'{VENTAS}/{nv.pk}/anular/', headers).status_code, 404)
        self.assertEqual(pago.objects.count(), 0)

    def test_usuario_sin_sucursal_recibe_lista_vacia(self):
        self.aprobada()
        user, token = make_staff(permissions=(), group='Caja')
        self.assertEqual(self.client.get(VENTAS, **auth(token)).json(), [])

    def test_admin_ve_todas_las_sucursales(self):
        self.aprobada()
        admin, token = make_staff(permissions=(), group='admin')
        self.assertEqual(len(self.client.get(VENTAS, **auth(token)).json()), 1)

    def test_no_staff_es_403(self):
        user, token, _ = helpers.create_staff_user_with_token(is_staff=False)
        self.assertEqual(self.client.get(VENTAS, **auth(token)).status_code, 403)

    def test_notas_de_trabajo_de_otra_sucursal_no_se_operan(self):
        _, nota, _ = self.aprobada()
        ajeno, token = make_staff(permissions=(), group='Almacen')
        helpers.create_sucursal(ajeno)
        self.assertEqual(self.post(f'{NOTAS}/{nota.pk}/terminar/', auth(token)).status_code, 404)
        self.assertEqual(self.post(f'{NOTAS}/{nota.pk}/anular/', auth(token)).status_code, 404)
