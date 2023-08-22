from ..models import inventario
from django.core.exceptions import FieldError

class Inventory_helper():

    def get_bobina_by_sucursal_lamina_width(self, sucursal_id, lamina_id, width, length_to_sell):
        bobinas = list(inventario.objects.filter(sucursal_id = sucursal_id, bobina__window_film_id_id =lamina_id, bobina__width__gte = width,to_install__gte =length_to_sell).order_by('date'))
        
        if(len(bobinas) > 0):
            #import pdb; pdb.set_trace()
            return bobinas[0]
        
        raise FieldError('no hay laminas disponibles!')
    
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
