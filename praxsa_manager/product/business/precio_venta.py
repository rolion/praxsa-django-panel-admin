
from ..models import  Sucursal
import logging

from decimal import *
class Precio_Venta_Business:

    def __init__(self) -> None:
        self.log_errors = logging.getLogger('django_admin')
    
    def get_precio_venta_sucursal_queryset_by_role(self, user, qs):
        try:
            sucursales = Sucursal.objects.prefetch_related('empleado')
            sucursales = sucursales.filter(empleado__id = user.id, enable_to_install_windows_film = True)
            if len(sucursales) > 0:
                qs_result = qs.select_related('sucursal', 'lamina')
                qs_result = qs_result.filter(sucursal__id = sucursales[0].id)
            else:
                qs_result = None
            
            return qs_result
        except Exception as e:
            self.log_errors.error(f'algo salio mal, Precio_Venta_Business - get_precio_venta_sucursal_queryset_by_role {e}')
            return None