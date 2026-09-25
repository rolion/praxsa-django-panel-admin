"""TASK-007 / ADR-006: el admin de Django recalcula server-side el precio real
de proformas venta_instalacion (CarModelPartForm.clean() + ProformaAdmin.save_related
via Proforma_Business.recalculate_total_price), sin confiar en lo que envía el form
(calculado client-side por sales_event.js). venta_metro_lineal queda explícitamente
fuera de alcance (ver ADR-006) y se documenta como tal en un test dedicado.
"""
from decimal import Decimal

from django.contrib import admin
from django.forms import inlineformset_factory
from django.test import RequestFactory, TestCase

from ..admin_config.proforma_admin import ProformaAdmin
from ..business.proforma import Proforma_Business
from ..Forms.car_model_part import CarModelPartForm
from ..helper.proforma import Proforma_Helper
from ..models import Proforma_Detail, Proforma_Header
from . import helpers

INLINE_FIELDS = [
    'car_part', 'window_film', 'width', 'length',
    'quantity', 'installation_price', 'window_film_price', 'sub_total',
]


def _make_header(scenario, sales_type=None):
    helper = Proforma_Helper()
    user, _ = helpers.create_user_with_token()
    return Proforma_Header.objects.create(
        name='Cliente Test',
        email='cliente@test.com',
        ci_nit='1234567',
        car_plate='ABC123',
        phone_number='70000001',
        sucursal=scenario['sucursal'],
        car_model_id=scenario['car_model'],
        sales_type=sales_type or helper.tipo_venta_instalacion,
        created_by=user,
    )


class CarModelPartFormPriceRecalculationTest(TestCase):
    """Unidad: CarModelPartForm.clean() instanciado directo (sin pasar por el
    formset inline del admin), para aislar la lógica de recálculo de precio."""

    def setUp(self):
        self.scenario = helpers.build_full_scenario()
        self.header = _make_header(self.scenario)

    def _valid_data(self, **overrides):
        data = {
            'proforma_header': self.header.pk,
            'inventario': self.scenario['inventario'].pk,
            'car_part': self.scenario['car_part'].pk,
            'window_film': self.scenario['window_film'].pk,
            'width': '1.50',
            'length': '1.00',
            'quantity': '1',
            'installation_price': '999.00',
            'window_film_price': '1.00',
            'sub_total': '1.00',
        }
        data.update(overrides)
        return data

    def test_overwrites_manipulated_price_with_real_recalculated_value(self):
        form = CarModelPartForm(data=self._valid_data(quantity='2'))
        self.assertTrue(form.is_valid(), form.errors)
        # length(1.00) * quantity(2) * unit_price(120.00) + installation_price(50.00) * quantity(2)
        self.assertEqual(form.cleaned_data['sub_total'], Decimal('340.00'))
        self.assertEqual(form.cleaned_data['installation_price'], Decimal('50.00'))
        self.assertEqual(form.cleaned_data['window_film_price'], Decimal('120.00'))

    def test_rejects_when_car_model_part_missing(self):
        other_part = helpers.create_car_part()  # sin Car_Model_Part para este car_model
        form = CarModelPartForm(data=self._valid_data(car_part=other_part.pk))
        self.assertFalse(form.is_valid())
        self.assertIn('car_part', form.errors)
        self.assertEqual(Proforma_Detail.objects.count(), 0)

    def test_rejects_when_no_inventory_covers_requested_width(self):
        # ancho >= al de Car_Model_Part (pasa esa validación), pero ningún
        # rollo de inventario (width=1.50) cubre un pedido de 2.00.
        form = CarModelPartForm(data=self._valid_data(width='2.00'))
        self.assertFalse(form.is_valid())
        self.assertIn('window_film', form.errors)

    def test_venta_metro_lineal_price_still_trusted_from_client(self):
        """Fuera de alcance de ADR-006: venta_metro_lineal no se recalcula."""
        header = _make_header(self.scenario, sales_type=Proforma_Helper().tipo_venta_metro_lineal)
        form = CarModelPartForm(data=self._valid_data(
            proforma_header=header.pk,
            quantity='0',
            installation_price='0',
            sub_total='999.99',
            window_film_price='5.00',
        ))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['sub_total'], Decimal('999.99'))
        self.assertEqual(form.cleaned_data['window_film_price'], Decimal('5.00'))

    def test_reactivated_validation_width_insufficient(self):
        form = CarModelPartForm(data=self._valid_data(width='1.00'))
        self.assertFalse(form.is_valid())
        self.assertIn('window_film', form.errors)

    def test_reactivated_validation_quantity_required(self):
        form = CarModelPartForm(data=self._valid_data(quantity='0'))
        self.assertFalse(form.is_valid())
        self.assertIn('quantity', form.errors)

    def test_reactivated_validation_installation_price_required(self):
        form = CarModelPartForm(data=self._valid_data(installation_price='0'))
        self.assertFalse(form.is_valid())
        self.assertIn('installation_price', form.errors)

    def test_missing_quantity_is_rejected_not_a_crash(self):
        """REV-2026-09-23-001: reactivar sale_header expuso comparaciones sin
        proteger contra None cuando un campo requerido llega vacío — antes de
        la corrección, form.is_valid() lanzaba TypeError en vez de invalidar."""
        data = self._valid_data()
        del data['quantity']
        form = CarModelPartForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('quantity', form.errors)

    def test_missing_installation_price_is_rejected_not_a_crash(self):
        """REV-2026-09-23-001, ver test_missing_quantity_is_rejected_not_a_crash."""
        data = self._valid_data()
        del data['installation_price']
        form = CarModelPartForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('installation_price', form.errors)

    def test_missing_window_film_is_rejected_with_car_model_part_present(self):
        """REV-2026-09-23-002: rama nueva cc_window_film is None sin cobertura."""
        data = self._valid_data()
        del data['window_film']
        form = CarModelPartForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('window_film', form.errors)

    def test_missing_width_is_rejected_not_a_crash(self):
        """REV-2026-09-23-003: item_width_lte_film_width(width=None) lanzaba
        ValueError ('Cannot use None as a query value') en vez de invalidar."""
        data = self._valid_data()
        del data['width']
        form = CarModelPartForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('width', form.errors)

    def test_no_required_field_omission_crashes_the_form(self):
        """Guarda de regresión general: reactivar sale_header (2023 -> hoy)
        expuso, uno por uno en revisiones sucesivas, que quantity/installation_price
        (REV-001) y width (REV-003) no estaban protegidos contra None. En vez de
        seguir descubriéndolos de a uno, se barre cada campo requerido y se
        confirma que ninguna omisión crashea is_valid(), para ambos sales_type."""
        required_fields = ['car_part', 'window_film', 'width', 'length', 'quantity', 'installation_price']
        metro_lineal_header = _make_header(self.scenario, sales_type=Proforma_Helper().tipo_venta_metro_lineal)
        for header, label in [(self.header, 'venta_instalacion'), (metro_lineal_header, 'venta_metro_lineal')]:
            for field in required_fields:
                with self.subTest(sales_type=label, missing_field=field):
                    data = self._valid_data(proforma_header=header.pk)
                    if field != 'proforma_header':
                        del data[field]
                    form = CarModelPartForm(data=data)
                    try:
                        form.is_valid()
                    except Exception as exc:  # pragma: no cover - el assert de abajo documenta el fallo
                        self.fail(f"{label}: omitir '{field}' crasheó con {type(exc).__name__}: {exc}")

    def test_missing_quantity_and_installation_price_venta_metro_lineal_is_rejected_not_a_crash(self):
        """REV-2026-09-23-001: mismo patrón en la rama venta_metro_lineal
        (cc_installation_price.compare(0), cc_quantity > 0)."""
        header = _make_header(self.scenario, sales_type=Proforma_Helper().tipo_venta_metro_lineal)
        data = self._valid_data(proforma_header=header.pk, sub_total='120.00')
        del data['quantity']
        del data['installation_price']
        form = CarModelPartForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('quantity', form.errors)
        self.assertIn('installation_price', form.errors)


class ProformaBusinessRecalculateTotalPriceTest(TestCase):

    def setUp(self):
        self.scenario = helpers.build_full_scenario()
        self.business = Proforma_Business()

    def test_sums_sub_totals_of_existing_details(self):
        header, _ = helpers.create_full_proforma(
            user=self.scenario['user'], sucursal=self.scenario['sucursal'],
            car_model=self.scenario['car_model'], car_part=self.scenario['car_part'],
            window_film=self.scenario['window_film'],
            installation_price=Decimal('50.00'), window_film_price=Decimal('120.00'),
        )
        Proforma_Detail.objects.create(
            proforma_header=header, window_film=self.scenario['window_film'],
            car_part=self.scenario['car_part'], width=Decimal('1.50'), length=Decimal('2.00'),
            sub_total=Decimal('290.00'), installation_price=Decimal('50.00'),
            window_film_price=Decimal('120.00'), quantity=1,
        )
        header.total_price = Decimal('0')  # simula un total desincronizado
        header.save(update_fields=['total_price'])

        self.business.recalculate_total_price(header)

        header.refresh_from_db()
        self.assertEqual(header.total_price, Decimal('460.00'))

    def test_zero_when_no_details(self):
        header = _make_header(self.scenario)
        header.total_price = Decimal('999.00')
        header.save(update_fields=['total_price'])

        self.business.recalculate_total_price(header)

        header.refresh_from_db()
        self.assertEqual(header.total_price, Decimal('0'))


class _FakeHeaderForm:
    """Sustituto mínimo de SaleHeaderForm para invocar ProformaAdmin.save_related
    directo, sin pasar por el POST completo del admin (mismo nivel de test que
    AdminGetQuerysetWiringTest en TASK-002)."""

    def __init__(self, instance):
        self.instance = instance

    def save_m2m(self):
        pass


class ProformaAdminSaveRelatedIntegrationTest(TestCase):

    def setUp(self):
        self.scenario = helpers.build_full_scenario()
        self.header = _make_header(self.scenario)
        self.admin = ProformaAdmin(Proforma_Header, admin.site)
        self.factory = RequestFactory()
        self.DetailFormSet = inlineformset_factory(
            Proforma_Header, Proforma_Detail, form=CarModelPartForm,
            fields=INLINE_FIELDS, extra=0, can_delete=True,
        )

    def _request(self):
        request = self.factory.post(f'/admin/product/proforma_header/{self.header.pk}/change/')
        request.user = self.scenario['user']
        return request

    def test_creates_two_items_and_recalculates_total_price_ignoring_manipulated_values(self):
        data = {
            'items-TOTAL_FORMS': '2',
            'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0',
            'items-MAX_NUM_FORMS': '1000',
            'items-0-car_part': self.scenario['car_part'].pk,
            'items-0-window_film': self.scenario['window_film'].pk,
            'items-0-width': '1.50',
            'items-0-length': '1.00',
            'items-0-quantity': '1',
            'items-0-installation_price': '999.00',
            'items-0-window_film_price': '1.00',
            'items-0-sub_total': '1.00',
            'items-1-car_part': self.scenario['car_part'].pk,
            'items-1-window_film': self.scenario['window_film'].pk,
            'items-1-width': '1.50',
            'items-1-length': '2.00',
            'items-1-quantity': '1',
            'items-1-installation_price': '999.00',
            'items-1-window_film_price': '1.00',
            'items-1-sub_total': '1.00',
        }
        formset = self.DetailFormSet(data=data, instance=self.header, prefix='items')
        self.assertTrue(formset.is_valid(), formset.errors)

        self.admin.save_related(self._request(), _FakeHeaderForm(self.header), [formset], change=False)

        details = list(Proforma_Detail.objects.filter(proforma_header=self.header).order_by('length'))
        self.assertEqual(len(details), 2)
        self.assertEqual(details[0].sub_total, Decimal('170.00'))  # 1.00*1*120 + 50*1
        self.assertEqual(details[1].sub_total, Decimal('290.00'))  # 2.00*1*120 + 50*1
        self.assertEqual(details[0].installation_price, Decimal('50.00'))
        self.assertEqual(details[0].window_film_price, Decimal('120.00'))

        self.header.refresh_from_db()
        self.assertEqual(self.header.total_price, Decimal('460.00'))

    def test_deleting_an_item_recalculates_total_price_to_the_sum_of_survivors(self):
        detail_kept = Proforma_Detail.objects.create(
            proforma_header=self.header, window_film=self.scenario['window_film'],
            car_part=self.scenario['car_part'], width=Decimal('1.50'), length=Decimal('1.00'),
            sub_total=Decimal('170.00'), installation_price=Decimal('50.00'),
            window_film_price=Decimal('120.00'), quantity=1,
        )
        detail_removed = Proforma_Detail.objects.create(
            proforma_header=self.header, window_film=self.scenario['window_film'],
            car_part=self.scenario['car_part'], width=Decimal('1.50'), length=Decimal('2.00'),
            sub_total=Decimal('290.00'), installation_price=Decimal('50.00'),
            window_film_price=Decimal('120.00'), quantity=1,
        )
        self.header.total_price = Decimal('460.00')
        self.header.save(update_fields=['total_price'])

        data = {
            'items-TOTAL_FORMS': '2',
            'items-INITIAL_FORMS': '2',
            'items-MIN_NUM_FORMS': '0',
            'items-MAX_NUM_FORMS': '1000',
            'items-0-id': detail_kept.pk,
            'items-0-car_part': self.scenario['car_part'].pk,
            'items-0-window_film': self.scenario['window_film'].pk,
            'items-0-width': '1.50',
            'items-0-length': '1.00',
            'items-0-quantity': '1',
            'items-0-installation_price': '50.00',
            'items-0-window_film_price': '120.00',
            'items-0-sub_total': '170.00',
            'items-1-id': detail_removed.pk,
            'items-1-car_part': self.scenario['car_part'].pk,
            'items-1-window_film': self.scenario['window_film'].pk,
            'items-1-width': '1.50',
            'items-1-length': '2.00',
            'items-1-quantity': '1',
            'items-1-installation_price': '50.00',
            'items-1-window_film_price': '120.00',
            'items-1-sub_total': '290.00',
            'items-1-DELETE': 'on',
        }
        formset = self.DetailFormSet(data=data, instance=self.header, prefix='items')
        self.assertTrue(formset.is_valid(), formset.errors)

        self.admin.save_related(self._request(), _FakeHeaderForm(self.header), [formset], change=True)

        self.assertEqual(Proforma_Detail.objects.filter(proforma_header=self.header).count(), 1)
        self.header.refresh_from_db()
        self.assertEqual(self.header.total_price, Decimal('170.00'))
