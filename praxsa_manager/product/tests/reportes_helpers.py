"""Fabrica de ventas cobradas con importes conocidos para los tests de los
reportes de Ventas Diarias y Utilidad (TASK-reportes-utilidad-ventas-diarias)."""
from datetime import datetime
from decimal import Decimal

from ..models import Inventario_Movimiento, Nota_Venta, Proforma_Detail, Proforma_Header, pago
from . import helpers

INSTALACION = 'venta_instalacion'
METRO_LINEAL = 'venta_metro_lineal'


def linea(length, quantity=0, price='100.00', install='0.00', inventario=None, movimientos=None, window_film=None):
    """Descripcion de una linea. `movimientos` = [(inventario, metros)] de egresos;
    `inventario` = FK legado de la linea (primera fila usada)."""
    return {
        'length': Decimal(str(length)), 'quantity': quantity, 'price': Decimal(str(price)),
        'install': Decimal(str(install)), 'inventario': inventario, 'movimientos': movimientos or [],
        'window_film': window_film,
    }


def create_venta_cobrada(
    user,
    sucursal,
    lineas,
    sales_type=INSTALACION,
    discount='0.00',
    tipo_pago='efec',
    pagado_en=None,
    nota_venta_status='pagada',
    crear_pago=True,
    is_delete=False,
    monto=None,
):
    """Proforma -> nota de trabajo -> nota de venta -> pago con las lineas dadas.
    Devuelve dict con 'proforma', 'nota_venta', 'pago' (None si crear_pago=False) y 'detalles'."""
    discount = Decimal(str(discount))
    detalles_datos = []
    total = Decimal('0.00')
    for datos in lineas:
        metros = datos['length'] * datos['quantity'] if datos['quantity'] > 0 else datos['length']
        sub_total = metros * datos['price'] + datos['install'] * datos['quantity']
        total += sub_total
        detalles_datos.append((datos, sub_total))
    header = Proforma_Header.objects.create(
        name='Cliente Test', email='cliente@test.com', ci_nit='1234567', car_plate='ABC123',
        phone_number='70000001', sucursal=sucursal, total_price=total, discount=discount,
        sales_type=sales_type, created_by=user, is_delete=is_delete,
    )
    detalles = []
    for datos, sub_total in detalles_datos:
        detalle = Proforma_Detail.objects.create(
            proforma_header=header, inventario=datos['inventario'],
            window_film=datos['window_film'] or helpers.create_window_film(), width=Decimal('1.50'),
            length=datos['length'], sub_total=sub_total, installation_price=datos['install'],
            window_film_price=datos['price'], quantity=datos['quantity'],
        )
        for inventario_obj, metros in datos['movimientos']:
            Inventario_Movimiento.objects.create(
                inventario=inventario_obj, proforma_detail=detalle,
                tipo=Inventario_Movimiento.EGRESO, metros=Decimal(str(metros)),
            )
        detalles.append(detalle)
    nota_trabajo = helpers.create_nota_trabajo(proforma=header, status='terminado')
    nota_venta = helpers.create_nota_venta(
        nota_trabajo=nota_trabajo, created_by=user, total_price=total - discount, status=nota_venta_status,
    )
    pago_obj = None
    if crear_pago:
        pago_obj = helpers.create_pago(
            nota_venta=nota_venta, created_by=user, tipo_pago=tipo_pago,
            **({} if monto is None else {'monto': Decimal(str(monto))}),
        )
        if pagado_en is not None:
            pago.objects.filter(pk=pago_obj.pk).update(created_on=pagado_en)
            pago_obj.refresh_from_db()
    return {'proforma': header, 'nota_venta': nota_venta, 'pago': pago_obj, 'detalles': detalles}


def registrar_devolucion(detalle, inventario_obj, metros):
    return Inventario_Movimiento.objects.create(
        inventario=inventario_obj, proforma_detail=detalle,
        tipo=Inventario_Movimiento.DEVOLUCION, metros=Decimal(str(metros)),
    )


def dia(anio, mes, dia_, hora=10, minuto=0):
    return datetime(anio, mes, dia_, hora, minuto)
