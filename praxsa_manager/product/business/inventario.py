from ..models import Sucursal, Window_Film, inventario
from ..helper.proforma import Proforma_Helper
class Inventario_Business:
    
    def get_window_film_available_in_storage(sucursal):
        q = inventario.objects.select_related("bobinas","bobinas__window_film_id")
        q = q.filter(sucursal = sucursal, to_install__gt = 0)
        q =q.values("bobina__window_film_id_id", "bobina__window_film_id__name")
        return q