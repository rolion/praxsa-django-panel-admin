"""Filtros de busqueda de los reportes Proforma, Nota Trabajo y de la pantalla de Notas
de Venta del Django Admin (TASK-filtros-busqueda-reportes)."""
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.urls import reverse

from ..admin_config.filtros_reportes import sucursal_en_alcance_filter
from ..admin_config.report_daily_sell import ReportDailySellAdmin
from ..business.orden_trabajo import Orden_Trabajo_Business
from ..models import Proxy_Nota_trabajo, instalador
from . import helpers


def _ids(response):
    return {obj.id for obj in response.context['cl'].result_list}


class FiltroSucursalEnAlcanceTest(TestCase):

    def _lookups(self, user):
        request = RequestFactory().get('/admin/')
        request.user = user
        filtro = sucursal_en_alcance_filter('sucursal')(request, {}, Proxy_Nota_trabajo, AdminSite())
        return {valor for valor, _ in filtro.lookups(request, None)}

    def test_superusuario_ve_todas_las_sucursales(self):
        superuser, _, _ = helpers.create_superuser_with_token()
        owner, _ = helpers.create_user_with_token()
        a, b = helpers.create_sucursal(owner), helpers.create_sucursal(owner)
        self.assertEqual(self._lookups(superuser), {a.id, b.id})

    def test_admin_solo_ve_las_suyas(self):
        admin_user, _ = helpers.create_user_with_token()
        helpers.add_user_to_group(admin_user, 'Admin')
        propia = helpers.create_sucursal(admin_user)
        helpers.create_sucursal(helpers.create_user_with_token()[0])
        self.assertEqual(self._lookups(admin_user), {propia.id})

    def test_usuario_normal_solo_ve_las_suyas(self):
        user, _ = helpers.create_user_with_token()
        otro, _ = helpers.create_user_with_token()
        propia_1, propia_2 = helpers.create_sucursal(user), helpers.create_sucursal(user)
        helpers.create_sucursal(otro)
        self.assertEqual(self._lookups(user), {propia_1.id, propia_2.id})

    def test_sucursal_deshabilitada_se_ofrece_para_consulta(self):
        user, _ = helpers.create_user_with_token()
        sucursal = helpers.create_sucursal(user)
        sucursal.enable_to_install_windows_film = False
        sucursal.save()
        self.assertEqual(self._lookups(user), {sucursal.id})


class ReportesFiltrosBase(TestCase):

    def setUp(self):
        self.admin_user = User.objects.create_superuser('root@test.com', 'root@test.com', 'pw12345678')
        helpers.add_user_to_group(self.admin_user, 'Admin')
        self.client.force_login(self.admin_user)
        self.owner, _ = helpers.create_user_with_token()
        self.sucursal_a = helpers.create_sucursal(self.owner)
        self.sucursal_b = helpers.create_sucursal(self.owner)
        self.marca_1, self.marca_2 = helpers.create_brand(), helpers.create_brand()
        self.modelo_1 = helpers.create_model(self.marca_1)
        self.modelo_2 = helpers.create_model(self.marca_2)

    def cadena(self, sucursal, modelo, nt_status='terminado', nv_status='pagada', instalador_obj=None):
        header, _ = helpers.create_full_proforma(self.owner, sucursal=sucursal, car_model=modelo)
        nota_trabajo = helpers.create_nota_trabajo(header, status=nt_status, car_model=modelo, instaladar=instalador_obj)
        nota_venta = helpers.create_nota_venta(nota_trabajo, self.owner, status=nv_status)
        return header, nota_trabajo, nota_venta


class ReporteProformaFiltrosTest(ReportesFiltrosBase):
    url = 'admin:product_proxy_proforma_changelist'

    def test_filtra_por_sucursal_marca_modelo_y_estado(self):
        p1, _, _ = self.cadena(self.sucursal_a, self.modelo_1)
        p2, _, _ = self.cadena(self.sucursal_b, self.modelo_2)
        p2.status = 'anulada'
        p2.save()
        url = reverse(self.url)
        base = {'proforma_created_on__range__gte_0': '', 'proforma_created_on__range__lte_0': ''}

        self.assertEqual(_ids(self.client.get(url, {**base, 'sucursal': self.sucursal_a.id})), {p1.id})
        self.assertEqual(_ids(self.client.get(url, {**base, 'car_model_id__car_brand_id__id__exact': self.marca_2.id})), {p2.id})
        self.assertEqual(_ids(self.client.get(url, {**base, 'car_model_id__id__exact': self.modelo_1.id})), {p1.id})
        self.assertEqual(_ids(self.client.get(url, {**base, 'status__exact': 'anulada'})), {p2.id})

    def test_fecha_por_defecto_es_hoy(self):
        p1, _, _ = self.cadena(self.sucursal_a, self.modelo_1)
        respuesta = self.client.get(reverse(self.url))
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn(p1.id, _ids(respuesta))

    def test_filtros_expuestos(self):
        contenido = self.client.get(reverse(self.url)).content.decode()
        for titulo in ('Sucursal', 'Marca', 'Modelo', 'Estado', 'Creado en'):
            self.assertIn(titulo, contenido)


class ReporteNotaTrabajoFiltrosTest(ReportesFiltrosBase):
    url = 'admin:product_proxy_nota_trabajo_changelist'

    def setUp(self):
        super().setUp()
        self.inst_1 = instalador.objects.create(name='Inst1', address='x', phonenumber='70000001')
        self.inst_2 = instalador.objects.create(name='Inst2', address='x', phonenumber='70000002')

    def test_lista_los_tres_estados(self):
        _, nt1, _ = self.cadena(self.sucursal_a, self.modelo_1, nt_status='en_proceso')
        _, nt2, _ = self.cadena(self.sucursal_a, self.modelo_1, nt_status='terminado')
        _, nt3, _ = self.cadena(self.sucursal_a, self.modelo_1, nt_status='cancelada')
        self.assertEqual(_ids(self.client.get(reverse(self.url))), {nt1.id, nt2.id, nt3.id})

    def test_filtra_por_estado_sucursal_marca_modelo_instalador_y_cobro(self):
        _, nt1, _ = self.cadena(self.sucursal_a, self.modelo_1, 'en_proceso', 'por_cobrar', self.inst_1)
        _, nt2, _ = self.cadena(self.sucursal_b, self.modelo_2, 'terminado', 'pagada', self.inst_2)
        url = reverse(self.url)

        self.assertEqual(_ids(self.client.get(url, {'status__exact': 'en_proceso'})), {nt1.id})
        self.assertEqual(_ids(self.client.get(url, {'sucursal': self.sucursal_b.id})), {nt2.id})
        self.assertEqual(_ids(self.client.get(url, {'car_model__car_brand_id__id__exact': self.marca_1.id})), {nt1.id})
        self.assertEqual(_ids(self.client.get(url, {'car_model__id__exact': self.modelo_2.id})), {nt2.id})
        self.assertEqual(_ids(self.client.get(url, {'instaladar__id__exact': self.inst_1.id})), {nt1.id})
        self.assertEqual(_ids(self.client.get(url, {'nota_venta__status__exact': 'pagada'})), {nt2.id})

    def test_nota_sin_nota_venta_aparece_sin_filtro_y_no_con_filtro_de_cobro(self):
        header, _ = helpers.create_full_proforma(self.owner, sucursal=self.sucursal_a, car_model=self.modelo_1)
        nt = helpers.create_nota_trabajo(header, status='en_proceso', car_model=self.modelo_1)
        url = reverse(self.url)
        self.assertIn(nt.id, _ids(self.client.get(url)))
        self.assertNotIn(nt.id, _ids(self.client.get(url, {'nota_venta__status__exact': 'por_cobrar'})))

    def test_nota_sin_fecha_de_entrada_es_visible_sin_filtro_de_fecha(self):
        header, _ = helpers.create_full_proforma(self.owner, sucursal=self.sucursal_a, car_model=self.modelo_1)
        nt = helpers.create_nota_trabajo(header, status='en_proceso', entrada_vehiculo=None)
        self.assertIn(nt.id, _ids(self.client.get(reverse(self.url))))

    def test_filtros_expuestos(self):
        self.cadena(self.sucursal_a, self.modelo_1)
        contenido = self.client.get(reverse(self.url)).content.decode()
        for titulo in ('Sucursal', 'Marca', 'Modelo', 'Instalador', 'Estado', 'Cobro'):
            self.assertIn(titulo, contenido)

    def test_get_finish_nota_queryset_por_defecto_solo_terminadas(self):
        _, nt_proceso, _ = self.cadena(self.sucursal_a, self.modelo_1, nt_status='en_proceso')
        _, nt_terminada, _ = self.cadena(self.sucursal_a, self.modelo_1, nt_status='terminado')
        negocio = Orden_Trabajo_Business()
        qs = Proxy_Nota_trabajo.objects.all()
        self.assertEqual(
            {n.id for n in negocio.get_finish_nota_queryset(user=self.admin_user, qs=qs)}, {nt_terminada.id})
        self.assertEqual(
            {n.id for n in negocio.get_finish_nota_queryset(user=self.admin_user, qs=qs, solo_terminadas=False)},
            {nt_proceso.id, nt_terminada.id})


class NotaVentaFiltrosTest(ReportesFiltrosBase):
    url = 'admin:product_nota_venta_changelist'

    def setUp(self):
        super().setUp()
        # get_nota_venta_queryset_by_role no tiene atajo Admin (ADR-002, fuera de alcance):
        # el usuario de prueba es empleado de ambas sucursales.
        self.admin_user.groups.clear()
        self.usuario = self.owner
        self.usuario.is_staff = True
        self.usuario.is_superuser = True
        self.usuario.save()
        self.client.force_login(self.usuario)

    def test_filtra_por_sucursal_trabajo_y_cobro(self):
        _, nt1, nv1 = self.cadena(self.sucursal_a, self.modelo_1, 'en_proceso', 'por_cobrar')
        _, nt2, nv2 = self.cadena(self.sucursal_b, self.modelo_2, 'terminado', 'pagada')
        url = reverse(self.url)

        # el alcance legado solo muestra la primera sucursal; ambas vienen del mismo usuario
        self.assertEqual(_ids(self.client.get(url, {'status__exact': 'por_cobrar'})) & {nv1.id, nv2.id}, {nv1.id})
        self.assertEqual(_ids(self.client.get(url, {'nota_trabajo__status__exact': 'en_proceso'})) & {nv1.id, nv2.id}, {nv1.id})
        self.assertEqual(
            _ids(self.client.get(url, {'sucursal': self.sucursal_a.id})) & {nv1.id, nv2.id},
            {nv1.id})

    def test_filtra_por_rango_de_fecha(self):
        _, _, nv_viejo = self.cadena(self.sucursal_a, self.modelo_1)
        _, _, nv_nuevo = self.cadena(self.sucursal_a, self.modelo_1)
        from datetime import datetime
        from django.utils import timezone
        nv_viejo.created_on = timezone.make_aware(datetime(2020, 1, 15, 10, 0))
        nv_viejo.save()
        respuesta = self.client.get(reverse(self.url), {
            'created_on__range__gte_0': '2020-01-01', 'created_on__range__gte_1': '00:00:00',
            'created_on__range__lte_0': '2020-01-31', 'created_on__range__lte_1': '23:59:59',
        })
        self.assertEqual(_ids(respuesta) & {nv_viejo.id, nv_nuevo.id}, {nv_viejo.id})

    def test_filtros_expuestos(self):
        self.cadena(self.sucursal_a, self.modelo_1)
        contenido = self.client.get(reverse(self.url)).content.decode()
        for titulo in ('Sucursal', 'Trabajo', 'Cobro', 'Fecha'):
            self.assertIn(titulo, contenido)

    def test_usuario_sin_sucursal_ve_lista_vacia_sin_error(self):
        sin_sucursal = User.objects.create_superuser('nosuc@test.com', 'nosuc@test.com', 'pw12345678')
        self.client.force_login(sin_sucursal)
        respuesta = self.client.get(reverse(self.url))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(_ids(respuesta), set())


class VentasDiariaSinCambiosTest(TestCase):

    def test_list_filter_de_ventas_diaria_intacto(self):
        nombres = [f if isinstance(f, str) else f[0] for f in ReportDailySellAdmin.list_filter]
        self.assertEqual(nombres, [
            'created_on',
            'nota_venta__nota_trabajo__proforma__sucursal',
            'nota_venta__nota_trabajo__proforma__sales_type',
            'tipo_pago',
        ])
