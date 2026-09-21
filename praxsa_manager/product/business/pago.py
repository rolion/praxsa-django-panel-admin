from ..models import pago, Proforma_Header, Nota_trabajo, Sucursal
from django.db import IntegrityError, transaction
from ..helper.user import User_Helper
import logging

class Pago_Business:

    def __init__(self) -> None:
        self.user_helper = User_Helper()
        self.log_errors = logging.getLogger('django_admin')

    def get_pago_queryset_by_role(self, user, qs):
        try:
            if self.user_helper.can_view_all_sucursales(user):
                return qs
            sucursales = Sucursal.objects.prefetch_related('empleado')
            sucursales = sucursales.filter(empleado__id = user.id, enable_to_install_windows_film = True)
            if len(sucursales) > 0:
                qs_result = qs.filter(nota_venta__nota_trabajo__proforma__sucursal__id = sucursales[0].id)
            else:
                qs_result = None
            return qs_result
        except Exception as e:
            self.log_errors.error(f'algo salio mal, Pago_Business - get_pago_queryset_by_role {e}')
            return None

    @transaction.atomic
    def cerrar_pago(self,paiment: pago):
        try:
            with transaction.atomic():
                paiment.cerrado = True
                paiment.save()
                nota_venta = proforma = paiment.nota_venta
                nota_venta.is_close = True
                nota_venta.save()
                proforma = paiment.nota_venta.nota_trabajo.proforma
                proforma.is_close = True
                proforma.save()
                nota_trabajo = proforma.nota_trabajo
                nota_trabajo.is_close = True
                nota_trabajo.save()
        except Exception as e:
            print(str(e))
            raise Exception('algo salio mal, contacte al administrador')
            pass