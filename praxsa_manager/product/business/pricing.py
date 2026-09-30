from decimal import Decimal, ROUND_HALF_UP
import logging

from ..helper.proforma import Proforma_Helper
from ..models import Car_Model_Part, precio_venta_sucursal
from ..utils.exception.proforma import ProformaException
from .inventario import Inventario_Business

_CENTS = Decimal('0.01')


class Pricing_Business:

    def __init__(self) -> None:
        self.log_errors = logging.getLogger('django_admin')
        self.inventario_business = Inventario_Business()

    def get_reel_catalog(self, sucursal_id):
        """Bobinas (lamina + ancho) con stock activo en la sucursal, con los
        metros disponibles y el precio unitario que `resolve_unit_price`
        resolveria para cada una -- la misma regla que usa el servidor al
        guardar una proforma, para que la vista previa del panel coincida con
        el importe persistido (ADR-modulo-ordenes-proforma-nota-trabajo-api-y-calculo).
        Numero constante de consultas (una de filas elegibles, una de overrides)."""
        rows = (
            self.inventario_business.eligible_rows(sucursal_id)
            .filter(bobina__window_film__is_active=True)
            .values_list('bobina__window_film__id', 'bobina__window_film__name', 'bobina__width',
                         'to_install', 'precio_venta_mtr_lineal')
        )
        grouped = {}
        for film_id, film_name, width, to_install, default_price in rows:
            key = (film_id, width)
            if key not in grouped:
                # Las filas llegan en orden FIFO: la primera fija el precio por defecto.
                grouped[key] = {'name': film_name, 'meters': Decimal('0'), 'default_price': default_price}
            grouped[key]['meters'] += to_install
        overrides = {
            (lamina_id, width): price
            for lamina_id, width, price in precio_venta_sucursal.objects.filter(sucursal_id=sucursal_id)
            .order_by('-id').values_list('lamina_id', 'width', 'precio_venta')
        }
        catalog = []
        for (film_id, width), data in sorted(grouped.items(), key=lambda item: (item[1]['name'], item[0][1])):
            override = overrides.get((film_id, width))
            catalog.append({
                'window_film': film_id,
                'window_film_name': data['name'],
                'width': width,
                'available_meters': data['meters'],
                'unit_price': override if override is not None else data['default_price'],
            })
        return catalog

    def has_stock_for_reel(self, sucursal_id, window_film, width):
        """True si hay stock activo de esa lamina con ese ancho **exacto** en
        la sucursal (reduce_inventory tambien exige ancho exacto)."""
        window_film_id = getattr(window_film, 'id', window_film)
        return self.inventario_business.eligible_rows(sucursal_id, window_film_id, width).exists()

    def get_available_meters(self, sucursal_id, window_film, width):
        """Metros que la aprobacion podria descontar hoy de esa lamina/ancho."""
        window_film_id = getattr(window_film, 'id', window_film)
        return self.inventario_business.get_available_meters(sucursal_id, window_film_id, width)

    def resolve_unit_price(self, sucursal_id, lamina_id, width):
        """Precio real por metro lineal para (sucursal, lámina, ancho **exacto**):
        override de precio_venta_sucursal si existe, si no el precio de venta
        de la fila de inventario que reduce_inventory consumiria primero (FIFO).
        Devuelve None si no hay ninguna fila elegible que cubra ese pedido."""
        if sucursal_id is None or lamina_id is None or width is None:
            return None
        row = self.inventario_business.eligible_rows(sucursal_id, lamina_id, Decimal(str(width))).first()
        if row is None:
            return None
        override = (
            precio_venta_sucursal.objects
            .filter(sucursal_id=sucursal_id, lamina_id=lamina_id, width=Decimal(str(width)))
            .order_by('-id')
            .values_list('precio_venta', flat=True)
            .first()
        )
        return override if override is not None else row.precio_venta_mtr_lineal


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


def _validate_available_meters(pricing_business, sucursal, window_film, width, required):
    """La linea no puede pedir mas metros de los que la aprobacion podria
    descontar hoy (suma de las filas elegibles). Es informativo: la garantia
    real la da reduce_inventory bajo bloqueo al aprobar."""
    available = pricing_business.get_available_meters(getattr(sucursal, 'id', None), window_film, width)
    if required > available:
        raise ProformaException(
            f'No hay metros suficientes de {window_film.name} con ancho {width} en la sucursal: '
            f'disponibles {available}, requeridos {required}.'
        )


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
        _validate_available_meters(pricing_business, sucursal, window_film, width, length * quantity)
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
        _validate_available_meters(pricing_business, sucursal, window_film, width, length)
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
