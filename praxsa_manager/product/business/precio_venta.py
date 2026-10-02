
from ..helper.user import User_Helper
import logging

from decimal import *
class Precio_Venta_Business:

    def __init__(self) -> None:
        self.log_errors = logging.getLogger('django_admin')
    
    def get_precio_venta_sucursal_queryset_by_role(self, user, qs):
        """Precios de las sucursales asignadas al usuario (activas o no, alcance
        de lectura); solo el superusuario ve todos. None si no tiene sucursal
        (los ModelAdmin lo usan para mostrar "Asigne una sucursal al usuario")."""
        helper = User_Helper()
        if not helper.can_view_all_sucursales(user) and not helper.has_assigned_sucursal(user):
            return None
        return qs.select_related('sucursal', 'lamina').filter(sucursal_id__in=helper.get_readable_sucursal_ids(user))
