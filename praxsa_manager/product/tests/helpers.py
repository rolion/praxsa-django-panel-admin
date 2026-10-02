"""Fábricas mínimas con el ORM para armar datos de prueba del app product."""
from decimal import Decimal

from django.contrib.auth.models import Group, Permission, User
from django.utils import timezone
from rest_framework.authtoken.models import Token

from ..models import (
    Car_Brand,
    Car_Model,
    Car_Model_Part,
    Car_Part,
    Nota_Venta,
    Nota_trabajo,
    Proforma_Detail,
    Proforma_Header,
    Sucursal,
    Window_Film,
    Window_Film_Reel,
    inventario,
    pago,
    precio_venta_sucursal,
)

_counter = [0]


def _unique(prefix):
    _counter[0] += 1
    return f'{prefix}{_counter[0]}'


def create_user_with_token(username=None, password='testpass123'):
    username = username or f'{_unique("user")}@test.com'
    user = User.objects.create_user(username=username, email=username, password=password)
    token = Token.objects.create(user=user)
    return user, token


def create_staff_user(username=None, password='testpass123'):
    """Usuario staff logueable por sesión (self.client.login), para endpoints
    protegidos por request.user.is_staff en vez de token DRF."""
    username = username or f'{_unique("staff")}@test.com'
    user = User.objects.create_user(username=username, email=username, password=password, is_staff=True)
    return user, password


def create_staff_user_with_token(username=None, password='testpass123', is_staff=True):
    """Usuario staff autenticable por Token DRF, para los endpoints nuevos del
    modulo de Usuarios (TASK-modulo-usuarios-perfiles-grupos-roles-sucursales),
    que usan authentication.TokenAuthentication + IsStaffUser."""
    username = username or f'{_unique("staffuser")}@test.com'
    user = User.objects.create_user(username=username, email=username, password=password, is_staff=is_staff)
    token = Token.objects.create(user=user)
    return user, token, password


def create_superuser_with_token(username=None, password='testpass123'):
    """Superusuario de Django (unica excepcion global al alcance por sucursal)
    autenticable por Token DRF. Es staff y tiene todos los permisos."""
    username = username or f'{_unique("superuser")}@test.com'
    user = User.objects.create_superuser(username=username, email=username, password=password)
    token = Token.objects.create(user=user)
    return user, token, password


def grant_permission(user, app_label, codename):
    permission = Permission.objects.get(content_type__app_label=app_label, codename=codename)
    user.user_permissions.add(permission)
    return permission


def add_user_to_group(user, group_name):
    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)
    return group


def create_sucursal(user, name=None, address='Calle Test 123'):
    sucursal = Sucursal.objects.create(
        name=name or _unique('Sucursal'),
        address=address,
        enable_to_install_windows_film=True,
        phone_number='70000000',
    )
    sucursal.empleado.add(user)
    return sucursal


def create_brand(name=None):
    return Car_Brand.objects.create(name=name or _unique('Marca'))


def create_model(brand=None, name=None):
    brand = brand or create_brand()
    return Car_Model.objects.create(car_brand_id=brand, name=name or _unique('Modelo'))


def create_car_part(name=None):
    return Car_Part.objects.create(name=name or _unique('Parte'))


def create_car_model_part(
    car_model=None,
    car_part=None,
    installation_price=Decimal('50.00'),
    width=Decimal('1.50'),
    length=Decimal('1.00'),
    quantity=1,
):
    car_model = car_model or create_model()
    car_part = car_part or create_car_part()
    return Car_Model_Part.objects.create(
        car_model_id=car_model,
        car_part_id=car_part,
        width=width,
        length=length,
        quantity=quantity,
        installation_price=installation_price,
    )


def create_window_film(name=None):
    return Window_Film.objects.create(
        name=name or _unique('Lamina'),
        description='descripcion de prueba',
        content=None,
    )


def create_window_film_reel(
    window_film=None,
    width=Decimal('1.50'),
    length=Decimal('30.00'),
    price=Decimal('120.00'),
):
    window_film = window_film or create_window_film()
    return Window_Film_Reel.objects.create(
        window_film=window_film,
        width=width,
        length=length,
        price=price,
    )


def create_inventario(
    sucursal=None,
    bobina=None,
    quantity=1,
    to_install=Decimal('50.00'),
    precio_venta_mtr_lineal=Decimal('120.00'),
    precio_compra_mtr_lineal=Decimal('80.00'),
):
    sucursal = sucursal or create_sucursal(create_user_with_token()[0])
    bobina = bobina or create_window_film_reel()
    return inventario.objects.create(
        sucursal=sucursal,
        bobina=bobina,
        quantity=quantity,
        to_install=to_install,
        installed=Decimal('0.00'),
        original_length=bobina.length,
        date=timezone.now(),
        precio_compra_mtr_lineal=precio_compra_mtr_lineal,
        precio_venta_mtr_lineal=precio_venta_mtr_lineal,
    )


def create_precio_venta_sucursal(sucursal, lamina, width=Decimal('1.50'), precio_venta=Decimal('150.00')):
    """Override de precio por sucursal para una lámina/ancho (rama 'precio_sucursal'
    del fallback precio_venta_sucursal -> inventario.precio_venta_mtr_lineal)."""
    return precio_venta_sucursal.objects.create(
        sucursal=sucursal,
        lamina=lamina,
        width=width,
        precio_venta=precio_venta,
    )


def create_full_proforma(
    user,
    sucursal=None,
    car_model=None,
    car_part=None,
    window_film=None,
    installation_price=Decimal('50.00'),
    window_film_price=Decimal('120.00'),
    inventario=None,
):
    """Crea una proforma completa (header + un detalle) directo con el ORM.
    Si se pasa `inventario`, el detalle queda enlazado a esa fila (necesario
    para admins como ReportUtilidadAdmin, que solo computan utilidad sobre
    inventario con un detalle de proforma asociado)."""
    sucursal = sucursal or create_sucursal(user)
    car_model = car_model or create_model()
    car_part = car_part or create_car_part()
    window_film = window_film or create_window_film()
    width = Decimal('1.50')
    length = Decimal('1.00')
    sub_total = installation_price + window_film_price

    header = Proforma_Header.objects.create(
        name='Cliente Test',
        email='cliente@test.com',
        ci_nit='1234567',
        car_plate='ABC123',
        phone_number='70000001',
        sucursal=sucursal,
        car_model_id=car_model,
        total_price=sub_total,
        created_by=user,
    )
    detail = Proforma_Detail.objects.create(
        proforma_header=header,
        inventario=inventario,
        window_film=window_film,
        car_part=car_part,
        width=width,
        length=length,
        sub_total=sub_total,
        installation_price=installation_price,
        window_film_price=window_film_price,
        quantity=1,
    )
    return header, detail


def create_nota_trabajo(proforma, **kwargs):
    defaults = dict(entrada_vehiculo=timezone.now(), name=proforma.name, car_plate=proforma.car_plate)
    defaults.update(kwargs)
    return Nota_trabajo.objects.create(proforma=proforma, **defaults)


def create_nota_venta(nota_trabajo, created_by, **kwargs):
    defaults = dict(
        name='Cliente Test',
        ci_nit='1234567',
        total_price=Decimal('170.00'),
        created_on=timezone.now(),
    )
    defaults.update(kwargs)
    return Nota_Venta.objects.create(nota_trabajo=nota_trabajo, created_by=created_by, **defaults)


def create_pago(nota_venta, created_by, **kwargs):
    defaults = dict(monto=nota_venta.total_price)
    defaults.update(kwargs)
    return pago.objects.create(nota_venta=nota_venta, created_by=created_by, **defaults)


def create_full_pago_chain(user, sucursal=None, inventario=None):
    """Arma proforma -> nota_trabajo -> nota_venta -> pago completos para una sucursal,
    listos para probar el filtrado por sucursal en Pagos/Reportes del admin."""
    header, _ = create_full_proforma(user=user, sucursal=sucursal, inventario=inventario)
    nota_trabajo = create_nota_trabajo(proforma=header, status='terminado')
    nota_venta = create_nota_venta(nota_trabajo=nota_trabajo, created_by=user, total_price=header.total_price, status='pagada')
    paiment = create_pago(nota_venta=nota_venta, created_by=user)
    return {
        'proforma': header,
        'nota_trabajo': nota_trabajo,
        'nota_venta': nota_venta,
        'pago': paiment,
    }


def build_full_scenario():
    """Arma un escenario completo (usuario, sucursal, modelo, item, bobina, inventario)
    listo para pegarle a los endpoints de /product/."""
    user, token = create_user_with_token()
    sucursal = create_sucursal(user)
    brand = create_brand()
    car_model = create_model(brand=brand)
    car_part = create_car_part()
    car_model_part = create_car_model_part(car_model=car_model, car_part=car_part)
    window_film = create_window_film()
    reel = create_window_film_reel(window_film=window_film)
    inv = create_inventario(sucursal=sucursal, bobina=reel)
    return {
        'user': user,
        'token': token,
        'sucursal': sucursal,
        'brand': brand,
        'car_model': car_model,
        'car_part': car_part,
        'car_model_part': car_model_part,
        'window_film': window_film,
        'reel': reel,
        'inventario': inv,
    }
