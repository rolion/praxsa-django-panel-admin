from decimal import Decimal, ROUND_HALF_UP
import logging

from django.db.models import Sum

from ..helper.proforma import Proforma_Helper
from ..models import Car_Model_Part, inventario
from ..utils.exception.proforma import ProformaException
from .inventario import Inventario_Business

_CENTS = Decimal('0.01')


class Pricing_Business:

    def __init__(self) -> None:
        self.log_errors = logging.getLogger('django_admin')
        self.inventario_business = Inventario_Business()

    def get_reel_catalog(self, sucursal_id):
        """Bobinas (lamina + ancho) con stock activo en la sucursal, con los
        metros disponibles y el precio unitario resuelto por
        `resolve_unit_price` -- la misma fuente que usa el servidor al
        guardar una proforma, para que la vista previa del panel coincida con
        el importe persistido (ADR-modulo-ordenes-proforma-nota-trabajo-api-y-calculo)."""
        rows = (
            inventario.objects.filter(
                sucursal_id=sucursal_id,
                sucursal__enable_to_install_windows_film=True,
                is_active=True,
                to_install__gt=0,
                bobina__is_active=True,
                bobina__window_film__is_active=True,
            )
            .values('bobina__window_film__id', 'bobina__window_film__name', 'bobina__width')
            .annotate(available_meters=Sum('to_install'))
            .order_by('bobina__window_film__name', 'bobina__width')
        )
        catalog = []
        for row in rows:
            unit_price = self.resolve_unit_price(
                sucursal_id=sucursal_id,
                lamina_id=row['bobina__window_film__id'],
                width=row['bobina__width'],
            )
            if unit_price is None:
                continue
            catalog.append({
                'window_film': row['bobina__window_film__id'],
                'window_film_name': row['bobina__window_film__name'],
                'width': row['bobina__width'],
                'available_meters': row['available_meters'],
                'unit_price': unit_price,
            })
        return catalog

    def has_stock_for_reel(self, sucursal_id, window_film, width):
        """True si hay stock activo de esa lamina con ese ancho **exacto** en
        la sucursal (reduce_inventory tambien exige ancho exacto)."""
        return inventario.objects.filter(
            sucursal_id=sucursal_id,
            sucursal__enable_to_install_windows_film=True,
            is_active=True,
            to_install__gt=0,
            bobina__is_active=True,
            bobina__window_film=window_film,
            bobina__width=width,
        ).exists()

    def resolve_unit_price(self, sucursal_id, lamina_id, width):
        """Precio real por metro lineal para (sucursal, lámina, ancho): override de
        precio_venta_sucursal si existe, si no el default de inventario.precio_venta_mtr_lineal.
        Devuelve None si no hay ninguna fila de inventario que cubra ese pedido."""
        rows = self.inventario_business.get_total_meters_window_film_in_inventory(
            sucursal_id=sucursal_id, lamina_id=lamina_id, width=float(width)
        )
        row = rows.first()
        if row is None:
            return None
        precio_sucursal = row['precio_sucursal']
        return precio_sucursal if precio_sucursal is not None else row['precio_venta_mtr_lineal']


def calculate_subtotal_venta_instalacion(length: Decimal, quantity: int, unit_price: Decimal, installation_price: Decimal) -> Decimal:
    """Fórmula de subtotal para sales_type='venta_instalacion' (único caso alcanzable
    desde SalesHeaderSerializer, ver TASK-005) - misma fórmula que ya usan Angular
    (formulario.component.ts:238) y sales_event.js (rama venta_instalacion)."""
    return (length * quantity * unit_price) + (installation_price * quantity)


def calculate_subtotal_venta_metro_lineal(length: Decimal, unit_price: Decimal) -> Decimal:
    """Fórmula de subtotal para sales_type='venta_metro_lineal' (creación directa de un
    ítem, no la conversión masiva de convertir_venta_metro_lineal). Sin término de
    quantity: CarModelPartForm.clean() prohíbe quantity>0 para este caso (ver TASK-010),
    misma fórmula que ya usa sales_event.js (rama else de calculate_subtotal)."""
    return length * unit_price


def build_line_pricing(sales_type, car_model, sucursal, line, pricing_business=None):
    """Precio real de una linea de proforma para la API del panel (Ordenes).

    Recibe los datos crudos de la linea (`car_part`, `window_film`, `width`,
    `length`, `quantity`) y devuelve `installation_price`, `window_film_price`,
    `sub_total` y `quantity` recalculados en servidor -- nunca se confia en lo
    que envie el cliente (ADR-004/ADR-006/TASK-010). Las formulas son las de
    calculate_subtotal_venta_*; aqui solo se orquestan las reglas que hoy
    vive en CarModelPartForm.clean() (que no se toca, ver ADR-modulo-ordenes-
    proforma-nota-trabajo-api-y-calculo punto 5). Lanza ProformaException con
    un mensaje legible cuando la linea no es valida."""
    helper = Proforma_Helper()
    pricing_business = pricing_business or Pricing_Business()
    window_film = line.get('window_film')
    width = line.get('width')
    length = line.get('length')
    car_part = line.get('car_part')
    quantity = line.get('quantity') or 0

    if window_film is None or width is None:
        raise ProformaException('Seleccione una bobina (lámina y ancho).')
    if length is None or length <= 0:
        raise ProformaException('El largo/los metros deben ser mayores a 0.')
    if not pricing_business.has_stock_for_reel(getattr(sucursal, 'id', None), window_film, width):
        raise ProformaException(
            f'No hay bobina de {window_film.name} con ancho {width} disponible en la sucursal.'
        )
    unit_price = pricing_business.resolve_unit_price(
        sucursal_id=sucursal.id, lamina_id=window_film.id, width=width
    )
    if unit_price is None:
        raise ProformaException('No hay precio disponible para la lámina/ancho solicitado en esa sucursal.')

    if sales_type == helper.tipo_venta_instalacion:
        if car_part is None:
            raise ProformaException('Seleccione un item del vehículo.')
        if car_model is None:
            raise ProformaException('Seleccione un modelo de vehículo.')
        model_part = Car_Model_Part.objects.filter(car_model_id=car_model, car_part_id=car_part).first()
        if model_part is None:
            raise ProformaException(
                f'No existe información de precio de instalación para el item {car_part.name} en el modelo {car_model.name}.'
            )
        if quantity < 1:
            raise ProformaException('La cantidad debe ser al menos 1.')
        if width < model_part.width:
            raise ProformaException(
                f'El item {car_part.name} requiere un ancho de lámina mayor o igual a {model_part.width}.'
            )
        sub_total = calculate_subtotal_venta_instalacion(
            length=length,
            quantity=quantity,
            unit_price=unit_price,
            installation_price=model_part.installation_price,
        ).quantize(_CENTS, rounding=ROUND_HALF_UP)
        return {
            'quantity': quantity,
            'installation_price': model_part.installation_price,
            'window_film_price': unit_price,
            'sub_total': sub_total,
        }

    if sales_type == helper.tipo_venta_metro_lineal:
        if car_part is not None:
            raise ProformaException('La venta por metro lineal no lleva item de vehículo.')
        if quantity > 0:
            raise ProformaException('La venta por metro lineal no lleva cantidad.')
        sub_total = calculate_subtotal_venta_metro_lineal(
            length=length, unit_price=unit_price
        ).quantize(_CENTS, rounding=ROUND_HALF_UP)
        return {
            'quantity': 0,
            'installation_price': Decimal('0.00'),
            'window_film_price': unit_price,
            'sub_total': sub_total,
        }

    raise ProformaException('Tipo de venta no válido.')
