"""Tests del campo status persistido en Proforma_Header (TASK-009 / ADR-006).

Cubren las 4 transiciones reales de negocio (create_work_note, abrir_proforma,
crear_nota_venta, cerrar_pago) mas la que se descubrio necesaria durante la
implementacion (Orden_Trabajo_Business.delete_work_note, que tambien cambia
la relacion proforma<->nota_trabajo y por lo tanto el estado observable).

Cada test de transicion verifica ademas que `status` coincide con lo que
ProformaAdmin.get_estado() calcula por hasattr() sobre relaciones -- la
inferencia actual del admin no se toca en este cambio (sigue siendo la
"fuente visible" hoy), asi que el campo nuevo debe ser su espejo exacto.
"""
from decimal import Decimal

from django.contrib.admin.sites import AdminSite
from django.test import TestCase

from . import helpers
from ..admin_config.proforma_admin import ProformaAdmin
from ..business.orden_trabajo import Orden_Trabajo_Business
from ..business.pago import Pago_Business
from ..business.proforma import Proforma_Business
from ..models import Proforma_Header, instalador


class ProformaStatusFieldTestCase(TestCase):
    """Arma una proforma completa, lista para ejecutar create_work_note,
    reusando las fabricas de tests/helpers.py."""

    def setUp(self):
        self.user, _token = helpers.create_user_with_token()
        self.sucursal = helpers.create_sucursal(self.user)
        self.car_model = helpers.create_model()
        self.car_part = helpers.create_car_part()
        # width/length deben coincidir con los defaults de create_full_proforma
        # y create_window_film_reel (1.50) para que validate_proforma_detail
        # y reduce_inventory encuentren coincidencia exacta.
        helpers.create_car_model_part(car_model=self.car_model, car_part=self.car_part, width=Decimal('1.50'))
        self.window_film = helpers.create_window_film()
        reel = helpers.create_window_film_reel(window_film=self.window_film, width=Decimal('1.50'))
        helpers.create_inventario(sucursal=self.sucursal, bobina=reel, to_install=Decimal('50.00'))

        self.header, self.detail = helpers.create_full_proforma(
            user=self.user,
            sucursal=self.sucursal,
            car_model=self.car_model,
            car_part=self.car_part,
            window_film=self.window_film,
        )
        self.proforma_business = Proforma_Business()
        self.admin = ProformaAdmin(Proforma_Header, AdminSite())

    def assert_status_matches_admin(self, proforma):
        """Recarga desde la base (como haria el admin al listar) y compara
        el campo persistido contra la inferencia por hasattr() ya existente."""
        reloaded = Proforma_Header.objects.get(pk=proforma.pk)
        expected_label = self.admin.get_estado(reloaded)
        label_by_code = dict(Proforma_Header._meta.get_field('status').choices)
        self.assertEqual(label_by_code[reloaded.status], expected_label)
        return reloaded

    def test_proforma_recien_creada_status_default(self):
        self.assertEqual(self.header.status, 'proforma')
        self.assert_status_matches_admin(self.header)

    def test_create_work_note_setea_status_nota_trabajo(self):
        self.proforma_business.create_work_note(proforma=self.header, responsable=self.user)

        self.assertEqual(self.header.status, 'nota_trabajo')
        self.assert_status_matches_admin(self.header)

    def test_refresh_status_no_modifica_proforma_created_on(self):
        # Aislado a refresh_status() en si mismo (no a create_work_note()
        # completo): proforma_created_on es auto_now=True, y create_work_note
        # YA tiene su propio proforma.save() sin update_fields antes de
        # llegar a refresh_status (comportamiento preexistente, fuera de
        # alcance de este cambio). Lo que este test protege es que
        # refresh_status no sea una segunda causa adicional de ese mismo problema.
        helpers.create_nota_trabajo(proforma=self.header)
        fecha_antes = Proforma_Header.objects.get(pk=self.header.pk).proforma_created_on

        self.proforma_business.refresh_status(self.header)

        reloaded = Proforma_Header.objects.get(pk=self.header.pk)
        self.assertEqual(reloaded.proforma_created_on, fecha_antes)

    def test_abrir_proforma_no_revierte_status_porque_nota_trabajo_persiste(self):
        # abrir_proforma() devuelve el inventario y reabre el formulario
        # (is_close=False), pero no borra la Nota_trabajo ya creada -- por lo
        # tanto ProformaAdmin.get_estado() (que solo mira hasattr) sigue
        # mostrando 'Nota Trabajo' incluso despues de "abrir" la proforma, y
        # el status persistido debe reflejar exactamente lo mismo (no
        # "volver" a 'proforma', pese a que is_close si vuelve a False).
        self.proforma_business.create_work_note(proforma=self.header, responsable=self.user)
        self.assertEqual(self.header.status, 'nota_trabajo')

        self.proforma_business.abrir_proforma(proforma=self.header)

        self.assertFalse(self.header.is_close)
        self.assertEqual(self.header.status, 'nota_trabajo')
        self.assert_status_matches_admin(self.header)

    def test_eliminar_nota_trabajo_revierte_status_a_proforma(self):
        # Unico camino existente que remueve la relacion proforma->nota_trabajo
        # (a diferencia de abrir_proforma). No estaba en la lista original de
        # 4 transiciones del plan; se detecto durante la implementacion porque
        # sin sincronizar aca, status quedaria permanentemente desactualizado
        # despues de borrar una nota de trabajo.
        nota_trabajo = self.proforma_business.create_work_note(proforma=self.header, responsable=self.user)
        self.assertEqual(self.header.status, 'nota_trabajo')

        Orden_Trabajo_Business().delete_work_note(work_note=nota_trabajo)

        reloaded = self.assert_status_matches_admin(self.header)
        self.assertEqual(reloaded.status, 'proforma')

    def test_crear_nota_venta_setea_status_por_cobrar(self):
        nota_trabajo = self.proforma_business.create_work_note(proforma=self.header, responsable=self.user)
        nota_trabajo.codigo_garantia = 'GAR-0001'
        nota_trabajo.instaladar = instalador.objects.create(
            name='Instalador Test', address='Calle Test 1', phonenumber='70000002',
        )
        nota_trabajo.save()

        self.proforma_business.crear_nota_venta(nota_trabajo=nota_trabajo, user=self.user)

        self.assert_status_matches_admin_by_pk(self.header.pk, expected_status='por_cobrar')

    def test_cerrar_pago_setea_status_finalizado(self):
        nota_trabajo = self.proforma_business.create_work_note(proforma=self.header, responsable=self.user)
        nota_trabajo.codigo_garantia = 'GAR-0002'
        nota_trabajo.instaladar = instalador.objects.create(
            name='Instalador Test', address='Calle Test 1', phonenumber='70000003',
        )
        nota_trabajo.save()
        self.proforma_business.crear_nota_venta(nota_trabajo=nota_trabajo, user=self.user)
        nota_venta = nota_trabajo.nota_venta
        paiment = helpers.create_pago(nota_venta=nota_venta, created_by=self.user)

        Pago_Business().cerrar_pago(paiment)

        self.assert_status_matches_admin_by_pk(self.header.pk, expected_status='finalizado')

    def assert_status_matches_admin_by_pk(self, pk, expected_status):
        reloaded = Proforma_Header.objects.get(pk=pk)
        self.assertEqual(reloaded.status, expected_status)
        label_by_code = dict(Proforma_Header._meta.get_field('status').choices)
        self.assertEqual(label_by_code[reloaded.status], self.admin.get_estado(reloaded))
