"""Tests de precio para POST /product/invoice (SalesHeaderSerializer). Ver TASK-005 / ADR-004.

Antes de este cambio, el servidor persistía el precio tal como lo mandaba el
cliente sin verificarlo (bug BIZ-01). InvoicePriceRecalculationTest documenta
el comportamiento corregido: el servidor siempre recalcula y sobrescribe el
precio real, sin importar lo que envía el cliente. Ninguno de estos tests
debería seguir pasando si esa protección se rompe.
"""
import json
from decimal import Decimal

from django.test import SimpleTestCase, TestCase

from ..business.pricing import Pricing_Business, calculate_subtotal_venta_instalacion
from ..models import Proforma_Detail, Proforma_Header
from . import helpers


def build_invoice_payload(scenario, sub_total, installation_price, window_film_price,
                           quantity=1, width=None, length='1.00', car_part=None, window_film=None):
    return {
        'name': 'Cliente Pricing',
        'email': 'pricing@test.com',
        'car_plate': 'PRC001',
        'car_model_id': scenario['car_model'].id,
        'total_price': str(sub_total),
        'phone_number': '70000003',
        'ci_nit': '1112223',
        'sucursal': scenario['sucursal'].id,
        'carPartItems': [
            {
                'car_part': (car_part or scenario['car_part']).id,
                'width': str(width if width is not None else scenario['car_model_part'].width),
                'length': length,
                'quantity': quantity,
                'window_film': (window_film or scenario['window_film']).id,
                'installation_price': str(installation_price),
                'window_film_price': str(window_film_price),
                'sub_total': str(sub_total),
            }
        ],
    }


class InvoicePriceRecalculationTest(TestCase):
    """El servidor recalcula y sobrescribe siempre el precio, ignorando lo que
    manda el cliente (decisión de negocio confirmada en ADR-004)."""

    def test_manipulated_price_is_overwritten_with_the_real_one(self):
        scenario = helpers.build_full_scenario()
        # precio real: installation_price=50.00 (car_model_part), window_film=120.00 (inventario, sin override)
        # length=1.00 (cliente), quantity=1 -> subtotal real = 1*1*120 + 50*1 = 170.00
        payload = build_invoice_payload(
            scenario,
            sub_total='1.00',
            installation_price='0.00',
            window_film_price='1.00',
        )

        response = self.client.post(
            '/product/invoice',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Token {scenario["token"].key}',
        )

        self.assertEqual(response.status_code, 201)
        header = Proforma_Header.objects.get(id=response.json()['id'])
        detail = Proforma_Detail.objects.get(proforma_header=header)
        self.assertEqual(header.total_price, Decimal('170.00'))
        self.assertEqual(detail.sub_total, Decimal('170.00'))
        self.assertEqual(detail.installation_price, Decimal('50.00'))
        self.assertEqual(detail.window_film_price, Decimal('120.00'))

    def test_uses_sucursal_price_override_when_it_exists(self):
        scenario = helpers.build_full_scenario()
        helpers.create_precio_venta_sucursal(
            sucursal=scenario['sucursal'],
            lamina=scenario['window_film'],
            width=scenario['car_model_part'].width,
            precio_venta=Decimal('200.00'),
        )
        payload = build_invoice_payload(scenario, sub_total='999.00', installation_price='0', window_film_price='0')

        response = self.client.post(
            '/product/invoice',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Token {scenario["token"].key}',
        )

        self.assertEqual(response.status_code, 201)
        detail = Proforma_Detail.objects.get(proforma_header_id=response.json()['id'])
        # override de sucursal (200.00) en vez del fallback de inventario (120.00)
        self.assertEqual(detail.window_film_price, Decimal('200.00'))
        self.assertEqual(detail.sub_total, Decimal('250.00'))  # 1*1*200 + 50*1

    def test_recalculates_correctly_with_quantity_greater_than_one(self):
        scenario = helpers.build_full_scenario()
        payload = build_invoice_payload(
            scenario, sub_total='1.00', installation_price='0', window_film_price='0',
            quantity=3, length='2.00',
        )

        response = self.client.post(
            '/product/invoice',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Token {scenario["token"].key}',
        )

        self.assertEqual(response.status_code, 201)
        detail = Proforma_Detail.objects.get(proforma_header_id=response.json()['id'])
        # (2.00 * 3 * 120.00) + (50.00 * 3) = 720.00 + 150.00
        self.assertEqual(detail.sub_total, Decimal('870.00'))
        self.assertEqual(detail.quantity, 3)

    def test_length_width_quantity_are_still_trusted_from_the_client(self):
        """Fuera de alcance de TASK-005 (ver ADR-004): solo se valida precio, no
        dimensiones. El cliente puede pedir un ancho/largo/cantidad distinto del
        canónico de Car_Model_Part y el servidor lo respeta tal cual."""
        scenario = helpers.build_full_scenario()
        payload = build_invoice_payload(
            scenario, sub_total='1.00', installation_price='0', window_film_price='0',
            quantity=5, length='3.00', width='1.00',
        )

        response = self.client.post(
            '/product/invoice',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Token {scenario["token"].key}',
        )

        self.assertEqual(response.status_code, 201)
        detail = Proforma_Detail.objects.get(proforma_header_id=response.json()['id'])
        self.assertEqual(detail.width, Decimal('1.00'))
        self.assertEqual(detail.length, Decimal('3.00'))
        self.assertEqual(detail.quantity, 5)
        # (3.00 * 5 * 120.00) + (50.00 * 5) = 1800.00 + 250.00
        self.assertEqual(detail.sub_total, Decimal('2050.00'))


class InvoicePriceUnresolvableTest(TestCase):
    """Cuando el precio real no se puede resolver, se rechaza (400) y no se crea nada."""

    def test_400_when_car_model_part_does_not_exist_for_the_item(self):
        scenario = helpers.build_full_scenario()
        other_part = helpers.create_car_part()  # no asociado a scenario['car_model'] via Car_Model_Part
        payload = build_invoice_payload(
            scenario, sub_total='170.00', installation_price='50.00', window_film_price='120.00',
            car_part=other_part,
        )

        response = self.client.post(
            '/product/invoice',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Token {scenario["token"].key}',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Proforma_Header.objects.count(), 0)

    def test_400_when_no_inventory_covers_the_requested_film_and_width(self):
        scenario = helpers.build_full_scenario()
        other_film = helpers.create_window_film()  # sin inventario para la sucursal
        payload = build_invoice_payload(
            scenario, sub_total='170.00', installation_price='50.00', window_film_price='120.00',
            window_film=other_film,
        )

        response = self.client.post(
            '/product/invoice',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Token {scenario["token"].key}',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Proforma_Header.objects.count(), 0)


class PricingBusinessUnitTest(TestCase):
    """resolve_unit_price necesita BD (consulta inventario/precio_venta_sucursal)."""

    def setUp(self):
        self.pricing_business = Pricing_Business()

    def test_resolve_unit_price_uses_sucursal_override_when_present(self):
        scenario = helpers.build_full_scenario()
        helpers.create_precio_venta_sucursal(
            sucursal=scenario['sucursal'],
            lamina=scenario['window_film'],
            width=scenario['reel'].width,
            precio_venta=Decimal('999.00'),
        )

        price = self.pricing_business.resolve_unit_price(
            sucursal_id=scenario['sucursal'].id,
            lamina_id=scenario['window_film'].id,
            width=scenario['reel'].width,
        )

        self.assertEqual(price, Decimal('999.00'))

    def test_resolve_unit_price_falls_back_to_inventario_default(self):
        scenario = helpers.build_full_scenario()

        price = self.pricing_business.resolve_unit_price(
            sucursal_id=scenario['sucursal'].id,
            lamina_id=scenario['window_film'].id,
            width=scenario['reel'].width,
        )

        self.assertEqual(price, Decimal('120.00'))

    def test_resolve_unit_price_returns_none_when_nothing_matches(self):
        scenario = helpers.build_full_scenario()
        other_film = helpers.create_window_film()

        price = self.pricing_business.resolve_unit_price(
            sucursal_id=scenario['sucursal'].id,
            lamina_id=other_film.id,
            width=Decimal('1.50'),
        )

        self.assertIsNone(price)


class CalculateSubtotalVentaInstalacionTest(SimpleTestCase):
    """Función pura, sin BD."""

    def test_multiplies_by_quantity_and_adds_installation(self):
        subtotal = calculate_subtotal_venta_instalacion(
            length=Decimal('2.00'), quantity=3,
            unit_price=Decimal('120.00'), installation_price=Decimal('50.00'),
        )
        self.assertEqual(subtotal, Decimal('870.00'))

    def test_quantity_one(self):
        subtotal = calculate_subtotal_venta_instalacion(
            length=Decimal('1.00'), quantity=1,
            unit_price=Decimal('120.00'), installation_price=Decimal('50.00'),
        )
        self.assertEqual(subtotal, Decimal('170.00'))
