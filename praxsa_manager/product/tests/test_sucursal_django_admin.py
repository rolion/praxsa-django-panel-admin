"""Django Admin con la misma regla de sucursal que la API (ADR-inventario-alcance-
sucursal-django-admin-alcance-lectura-escritura, decision 7): lectura en todas las
sucursales asignadas (activas o no), escritura solo en las activas, sin excepcion
para el grupo admin, y sin estado compartido entre usuarios en `InventoryAdmin`."""
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory, TestCase

from ..admin_config.inventory import InventoryAdmin
from ..admin_config.nota_trabajo import NotaTrabajoAdmin
from ..admin_config.nota_venta import NotaVentaAdmin
from ..admin_config.pagos import PagosAdmin
from ..admin_config.precio_venta_sucursal import PrecioVentaSucursalAdmin
from ..admin_config.proforma_admin import ProformaAdmin
from ..business.orden_trabajo import Orden_Trabajo_Business
from ..business.pago import Pago_Business
from ..business.precio_venta import Precio_Venta_Business
from ..business.proforma import Proforma_Business
from ..models import (
    Nota_trabajo,
    Nota_Venta,
    Proforma_Header,
    inventario,
    pago,
    precio_venta_sucursal,
)
from . import helpers


def _request(user):
    request = RequestFactory().get('/admin/')
    request.user = user
    return request


def _desactivar(sucursal):
    sucursal.enable_to_install_windows_film = False
    sucursal.save(update_fields=['enable_to_install_windows_film'])


def _user(group=None, permissions=()):
    user, _ = helpers.create_user_with_token()
    user.is_staff = True
    user.save(update_fields=['is_staff'])
    if group:
        helpers.add_user_to_group(user, group)
    for codename in permissions:
        helpers.grant_permission(user, 'product', codename)
    return user


class InventoryAdminTest(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.model_admin = InventoryAdmin(inventario, self.site)
        self.user = _user(permissions=('add_inventario', 'change_inventario', 'delete_inventario'))
        self.activa = helpers.create_sucursal(self.user)
        self.segunda = helpers.create_sucursal(self.user)
        self.inactiva = helpers.create_sucursal(self.user)
        _desactivar(self.inactiva)
        self.ajena = helpers.create_sucursal(helpers.create_user_with_token()[0])
        self.inv_activa = helpers.create_inventario(sucursal=self.activa)
        self.inv_segunda = helpers.create_inventario(sucursal=self.segunda)
        self.inv_inactiva = helpers.create_inventario(sucursal=self.inactiva)
        self.inv_ajena = helpers.create_inventario(sucursal=self.ajena)

    def test_lectura_incluye_todas_las_asignadas_no_solo_la_primera(self):
        ids = set(self.model_admin.get_queryset(_request(self.user)).values_list('id', flat=True))
        self.assertEqual(ids, {self.inv_activa.id, self.inv_segunda.id, self.inv_inactiva.id})

    def test_grupo_admin_no_ve_las_ajenas(self):
        admin = _user(group='Admin')
        propia = helpers.create_sucursal(admin)
        inv = helpers.create_inventario(sucursal=propia)
        ids = set(self.model_admin.get_queryset(_request(admin)).values_list('id', flat=True))
        self.assertEqual(ids, {inv.id})

    def test_usuario_sin_sucursal_no_ve_nada(self):
        self.assertEqual(self.model_admin.get_queryset(_request(_user(group='Admin'))).count(), 0)

    def test_superusuario_ve_todo(self):
        superuser, _, _ = helpers.create_superuser_with_token()
        self.assertEqual(self.model_admin.get_queryset(_request(superuser)).count(), 4)

    def test_modificar_solo_en_sucursal_activa_asignada(self):
        request = _request(self.user)
        self.assertTrue(self.model_admin.has_change_permission(request, self.inv_activa))
        self.assertTrue(self.model_admin.has_delete_permission(request, self.inv_segunda))
        self.assertFalse(self.model_admin.has_change_permission(request, self.inv_inactiva))
        self.assertFalse(self.model_admin.has_delete_permission(request, self.inv_inactiva))
        self.assertFalse(self.model_admin.has_change_permission(request, self.inv_ajena))

    def test_agregar_requiere_alguna_sucursal_activa(self):
        self.assertTrue(self.model_admin.has_add_permission(_request(self.user)))
        solo_inactiva = _user(permissions=('add_inventario',))
        _desactivar(helpers.create_sucursal(solo_inactiva))
        self.assertFalse(self.model_admin.has_add_permission(_request(solo_inactiva)))
        self.assertFalse(self.model_admin.has_add_permission(_request(_user(permissions=('add_inventario',)))))

    def test_el_selector_de_sucursal_solo_ofrece_activas_asignadas(self):
        field = inventario._meta.get_field('sucursal')
        formfield = self.model_admin.formfield_for_foreignkey(field, _request(self.user))
        self.assertEqual(set(formfield.queryset.values_list('id', flat=True)), {self.activa.id, self.segunda.id})

    def test_la_configuracion_no_se_filtra_entre_usuarios(self):
        admin = _user(group='Admin')
        supervisor = _user(group='Supervisor')
        otro = _user(group='Caja')
        fields_antes = self.model_admin.fields
        readonly_antes = self.model_admin.readonly_fields

        self.assertEqual(self.model_admin.get_readonly_fields(_request(admin)), [])
        self.assertIn('sucursal', self.model_admin.get_fields(_request(admin)))
        self.assertIn('sucursal', self.model_admin.get_readonly_fields(_request(supervisor)))
        # el usuario "normal" que entra despues no hereda nada del admin ni del supervisor
        self.assertEqual(self.model_admin.get_readonly_fields(_request(otro)), [])
        self.assertNotEqual(self.model_admin.get_fields(_request(otro)), self.model_admin.full_access_fields)
        # la vista ya no reescribe atributos de la instancia compartida
        self.assertEqual(self.model_admin.fields, fields_antes)
        self.assertEqual(self.model_admin.readonly_fields, readonly_antes)

    def test_la_columna_sucursal_se_oculta_solo_con_una_unica_sucursal(self):
        uno = _user()
        helpers.create_sucursal(uno)
        self.assertNotIn('sucursal', self.model_admin.get_list_display(_request(uno)))
        self.assertIn('sucursal', self.model_admin.get_list_display(_request(self.user)))
        self.assertIn('sucursal', self.model_admin.get_list_display(_request(helpers.create_superuser_with_token()[0])))


class OrdenesAdminWriteRuleTest(TestCase):
    """El mixin en los ModelAdmin de Ordenes: se ve la fila de una sucursal inactiva
    pero no se modifica."""

    def setUp(self):
        self.site = AdminSite()
        self.user = _user(permissions=(
            'change_proforma_header', 'delete_proforma_header', 'change_nota_trabajo',
            'change_nota_venta', 'change_pago', 'delete_pago', 'change_precio_venta_sucursal',
        ))
        self.sucursal = helpers.create_sucursal(self.user)
        self.chain = helpers.create_full_pago_chain(self.user, sucursal=self.sucursal)
        self.proforma = self.chain['nota_trabajo'].proforma
        self.nota_venta = self.chain['nota_venta']
        self.pago = self.chain['pago']

    def _objects(self):
        return [
            (ProformaAdmin(Proforma_Header, self.site), self.proforma),
            (NotaTrabajoAdmin(Nota_trabajo, self.site), self.chain['nota_trabajo']),
            (NotaVentaAdmin(Nota_Venta, self.site), self.nota_venta),
            (PagosAdmin(pago, self.site), self.pago),
        ]

    def test_sucursal_inactiva_no_se_modifica_ni_se_elimina(self):
        # Los modelos de la cadena se crean abiertos (no cerrados) en los helpers.
        request = _request(self.user)
        for model_admin, obj in self._objects():
            self.assertTrue(model_admin.sucursal_writable_for(request, obj), model_admin)
        _desactivar(self.sucursal)
        for model_admin, obj in self._objects():
            self.assertFalse(model_admin.sucursal_writable_for(request, obj), model_admin)
            self.assertFalse(model_admin.has_change_permission(request, obj), model_admin)

    def test_sucursal_ajena_no_se_modifica(self):
        otro = _user(permissions=('change_proforma_header', 'change_nota_trabajo', 'change_nota_venta', 'change_pago'))
        helpers.create_sucursal(otro)
        request = _request(otro)
        for model_admin, obj in self._objects():
            self.assertFalse(model_admin.has_change_permission(request, obj), model_admin)

    def test_pago_en_sucursal_inactiva_no_se_puede_eliminar(self):
        _desactivar(self.sucursal)
        self.assertFalse(PagosAdmin(pago, self.site).has_delete_permission(_request(self.user), self.pago))

    def test_precio_por_sucursal_sigue_la_misma_regla(self):
        film = helpers.create_window_film()
        precio = helpers.create_precio_venta_sucursal(self.sucursal, film)
        model_admin = PrecioVentaSucursalAdmin(precio_venta_sucursal, self.site)
        request = _request(self.user)
        self.assertTrue(model_admin.has_change_permission(request, precio))
        _desactivar(self.sucursal)
        self.assertFalse(model_admin.has_change_permission(request, precio))
        self.assertEqual(model_admin.get_queryset(request).count(), 1)  # se sigue viendo


class MetodosLegadosDelegaTest(TestCase):
    """Los `*_by_role` del Django Admin delegan en el alcance del panel: todas las
    sucursales asignadas (no solo la primera), None sin sucursal."""

    def setUp(self):
        self.user = _user()
        self.a = helpers.create_sucursal(self.user)
        self.b = helpers.create_sucursal(self.user)
        self.chain_a = helpers.create_full_pago_chain(self.user, sucursal=self.a)
        self.chain_b = helpers.create_full_pago_chain(self.user, sucursal=self.b)
        self.sin_sucursal = _user()

    def test_proforma_nota_trabajo_nota_venta_y_pago_ven_todas_las_asignadas(self):
        proforma_business = Proforma_Business()
        proformas = proforma_business.get_proforma_queryset_by_role(self.user, Proforma_Header.objects.all())
        self.assertEqual(proformas.count(), 2)
        notas = Orden_Trabajo_Business().get_nota_queryset_by_role(self.user, Nota_trabajo.objects.all())
        self.assertEqual(notas.count(), 2)
        self.assertEqual(
            proforma_business.get_nota_trabajo_queryset_by_role(self.user, Nota_trabajo.objects.all()).count(), 2)
        self.assertEqual(
            proforma_business.get_nota_venta_queryset_by_role(self.user, Nota_Venta.objects.all()).count(), 2)
        self.assertEqual(Pago_Business().get_pago_queryset_by_role(self.user, pago.objects.all()).count(), 2)

    def test_sin_sucursal_devuelve_none(self):
        proforma_business = Proforma_Business()
        self.assertIsNone(proforma_business.get_proforma_queryset_by_role(self.sin_sucursal, Proforma_Header.objects.all()))
        self.assertIsNone(Orden_Trabajo_Business().get_nota_queryset_by_role(self.sin_sucursal, Nota_trabajo.objects.all()))
        self.assertIsNone(proforma_business.get_nota_venta_queryset_by_role(self.sin_sucursal, Nota_Venta.objects.all()))
        self.assertIsNone(Pago_Business().get_pago_queryset_by_role(self.sin_sucursal, pago.objects.all()))
        self.assertIsNone(Precio_Venta_Business().get_precio_venta_sucursal_queryset_by_role(
            self.sin_sucursal, precio_venta_sucursal.objects.all()))

    def test_grupo_admin_sin_sucursal_tampoco_ve_nada(self):
        admin = _user(group='Admin')
        self.assertIsNone(Proforma_Business().get_proforma_queryset_by_role(admin, Proforma_Header.objects.all()))

    def test_superusuario_ve_todo(self):
        superuser, _, _ = helpers.create_superuser_with_token()
        proformas = Proforma_Business().get_proforma_queryset_by_role(superuser, Proforma_Header.objects.all())
        self.assertEqual(proformas.count(), 2)

    def test_sucursal_inactiva_se_sigue_viendo(self):
        _desactivar(self.a)
        proformas = Proforma_Business().get_proforma_queryset_by_role(self.user, Proforma_Header.objects.all())
        self.assertEqual(proformas.count(), 2)
