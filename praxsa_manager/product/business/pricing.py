from decimal import Decimal
import logging

from .inventario import Inventario_Business


class Pricing_Business:

    def __init__(self) -> None:
        self.log_errors = logging.getLogger('django_admin')
        self.inventario_business = Inventario_Business()

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
