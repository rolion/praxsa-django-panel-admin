from ..models import Sucursal, Window_Film, inventario
from ..helper.proforma import Proforma_Helper
class Inventario_Business:
    
    def get_inventory_by_sucursal(self, sucursal):
        q = inventario.objects.select_related("bobina","bobina__window_film_id", "sucursal")
        q = q.order_by('bobina__window_film_id__id', 'date')
        # q = q.distinct("bobina__window_film_id__id")
        q = q.filter(sucursal = sucursal, 
                     sucursal__enable_to_install_windows_film = True)
        return q
    
    def get_inventory_film_available_film_by_sucursal(self, sucursal):
        q = self.get_inventory_by_sucursal(sucursal=sucursal)
        q = q.values_list("bobina__window_film_id__id")
        result = Window_Film.objects.filter(pk__in = q)
        return result
    
    def update_inventory(self, sucursal_id, bobina, length_to_reduce):
        invs = list(inventario.objects.filter(sucursal_id = sucursal_id, bobina= bobina, to_install__gte = length_to_reduce).order_by('date'))
        if(len(invs) > 0):
            try:
                bobina_inventario = invs[0]
                bobina_inventario.to_install = bobina_inventario.to_install - length_to_reduce
                bobina_inventario.installed = bobina_inventario.installed + length_to_reduce
                return bobina_inventario.save()
            except Exception as e:
                print('exception ', str(e))
        raise Exception('no hay laminas disponibles')
