"""Fabricas compartidas por los tests del modulo Ordenes
(TASK-modulo-ordenes-proforma-nota-trabajo)."""
from decimal import Decimal

from . import helpers

WRITE_PERMISSIONS = (
    'add_proforma_header', 'change_proforma_header', 'add_nota_trabajo', 'change_nota_trabajo',
)


def auth(token):
    return {'HTTP_AUTHORIZATION': f'Token {token.key}'}


def make_staff(permissions=WRITE_PERMISSIONS, group=None):
    user, token, _ = helpers.create_staff_user_with_token()
    for codename in permissions:
        helpers.grant_permission(user, 'product', codename)
    if group:
        helpers.add_user_to_group(user, group)
    return user, token


def make_scenario(user=None, permissions=WRITE_PERMISSIONS, to_install=Decimal('50.00')):
    """Usuario staff con permisos, su sucursal y un modelo/item/lamina/bobina
    con inventario (ancho 1.50, precio 120.00; item 1.50 x 1.00, instalacion 50.00)."""
    if user is None:
        user, token = make_staff(permissions)
    else:
        token = None
    sucursal = helpers.create_sucursal(user)
    car_model = helpers.create_model()
    car_part = helpers.create_car_part()
    helpers.create_car_model_part(car_model=car_model, car_part=car_part)
    film = helpers.create_window_film()
    reel = helpers.create_window_film_reel(window_film=film)
    inv = helpers.create_inventario(sucursal=sucursal, bobina=reel, to_install=to_install)
    return {
        'user': user, 'token': token, 'sucursal': sucursal, 'car_model': car_model,
        'car_part': car_part, 'film': film, 'reel': reel, 'inventario': inv,
    }


def instalacion_payload(s, **overrides):
    payload = {
        'sales_type': 'venta_instalacion',
        'sucursal': s['sucursal'].id,
        'name': 'Cliente Panel',
        'email': 'cliente@test.com',
        'ci_nit': '1234567',
        'phone_number': '70000001',
        'car_plate': 'ABC123',
        'car_model_id': s['car_model'].id,
        'discount': '0',
        'items': [{
            'car_part': s['car_part'].id,
            'window_film': s['film'].id,
            'width': '1.50',
            'length': '1.00',
            'quantity': 2,
        }],
    }
    payload.update(overrides)
    return payload


def metro_lineal_payload(s, **overrides):
    payload = {
        'sales_type': 'venta_metro_lineal',
        'sucursal': s['sucursal'].id,
        'name': 'Cliente Metro',
        'email': 'cliente@test.com',
        'ci_nit': '1234567',
        'phone_number': '70000001',
        'discount': '0',
        'items': [{'window_film': s['film'].id, 'width': '1.50', 'length': '3.50'}],
    }
    payload.update(overrides)
    return payload
