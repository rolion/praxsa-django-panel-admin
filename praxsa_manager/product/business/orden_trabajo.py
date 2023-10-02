from ..models import Proforma_Header, Proforma_Detail, Sucursal
from .inventario import Inventario_Business
class Orden_Trabajo_Business:


     def get_nota_queryset_by_role(self, user, qs):
        try:
            # sucursales = Sucursal.objects.prefetch_related('empleado').filter(empleado__id = user.id, enable_to_install_windows_film = True)
            # if user.is_superuser:
            #     return qs.filter(is_delete = False)
            sucursales = Sucursal.objects.prefetch_related('empleado')
            sucursales = sucursales.filter(empleado__id = user.id, enable_to_install_windows_film = True)
            if len(sucursales) > 0:
                qs_result = qs.select_related('proforma','proforma__sucursal', 'proforma__car_model_id__car_brand_id')
                qs_result = qs_result.filter(proforma__sucursal__id = sucursales[0].id, proforma__is_delete = False)
            else:
                qs_result = None
            return qs_result
        except Exception as e:
            print('algo salio mal, Orden_Trabajo_Business - get_nota_queryset_by_role', str(e))
            return None
