from ..models import Sucursal, Window_Film, inventario
from django.db.models import Sum, F
from ..utils.exception.nohaylaminas import NoHayLaminasDisponibles
class Inventario_Business:
    
    def get_inventory_by_sucursal(self, sucursal):
        q = inventario.objects.select_related("bobina","bobina__window_film", "sucursal")
        q = q.order_by('bobina__window_film__id', 'date')
        # q = q.distinct("bobina__window_film_id__id")
        q = q.filter(sucursal = sucursal, sucursal__enable_to_install_windows_film = True)
        return q
    
    def get_inventory_film_available_film_by_sucursal(self, sucursal):
        q = self.get_inventory_by_sucursal(sucursal=sucursal)
        q = q.values_list("bobina__window_film__id")
        result = Window_Film.objects.filter(pk__in = q)
        return result
    
    def update_inventory(self, sucursal, windows_film, width, length_to_reduce):
        query = inventario.objects.select_related('bobina', 'sucursal', 'bobina__window_film')
        query = query.filter(sucursal = sucursal, bobina__window_film = windows_film, bobina__width = width, to_install__gte = length_to_reduce).order_by('date')[:1]
        if(query.exists()):
            bobina_inventario = query[0]
            bobina_inventario.to_install = bobina_inventario.to_install - length_to_reduce
            bobina_inventario.installed = bobina_inventario.installed + length_to_reduce
            return bobina_inventario.save()
        raise NoHayLaminasDisponibles(f'no hay lamina disponible {windows_film.name}')
        #return False
    
    def is_window_film_available(self, sucursal_id, bobina, width, to_install):
        query = inventario.objects.select_related('bobina', 'sucursal')
        query = query.filter(sucursal__id = sucursal_id, bobina__id = bobina, width__gte=width, to_install__gte = to_install).order_by('date','width')
        if len(query) > 0:
            return True
        return False
    
    def get_total_meters_window_film_in_inventory(self, sucursal_id):
        query = inventario.objects.select_related('sucursal','bobina', 'bobina__window_film')
        query = query.values("bobina__window_film__id", "bobina__window_film__name", "bobina__width")
        return query.annotate(total=Sum("to_install")).filter(sucursal__id = sucursal_id)
    
    def available_window_film_reel_in_inventory_to_sell(self, sucursal, windows_film, width, total_length_to_sell):
        query = inventario.objects.select_related('sucursal','bobina', 'bobina__window_film')
        query = query.filter(bobina__window_film = windows_film, bobina__width = width, sucursal = sucursal)
        query = query.order_by('bobina__window_film__id','bobina__width', 'date')
        return query.filter(to_install__gte = total_length_to_sell) 
    
    # inventario.objects.select_related('sucursal','bobina', 'bobina__window_film').filter(bobina__window_film = 2, bobina__width = 0.5, sucursal = 1).order_by('bobina__window_film__id','bobina__width', 'date').filter(to_install__gte = 100) 
    
    def get_inventory_window_film(self, sucursal):
        query = inventario.objects.select_related("bobina","bobina__window_film", "sucursal")
        query = query.filter(sucursal = sucursal, sucursal__enable_to_install_windows_film = True)
        query = query.order_by('bobina__window_film__id', 'bobina__width','date').distinct('bobina__window_film__id')
        query = query.annotate(film_id = F('bobina__window_film__id'))
        query = query.values_list('film_id')
        films = Window_Film.objects.filter(id__in = query)
        return films
    
    def get_user_inventory_window_films(self, user):
        query = inventario.objects.select_related("bobina","bobina__window_film", "sucursal")
        query = query.filter(sucursal__enable_to_install_windows_film = True, sucursal__empleado = user)
        query = query.order_by('bobina__window_film__id', 'bobina__width','date').distinct('bobina__window_film__id')
        query = query.annotate(film_id = F('bobina__window_film__id'))
        query = query.values_list('film_id')
        films = Window_Film.objects.filter(id__in = query)
        return films
    

    # query = inventario.objects.select_related("bobina","bobina__window_film", "sucursal").filter(sucursal__enable_to_install_windows_film = True, sucursal__empleado = 1).order_by('bobina__window_film__id', 'bobina__width','date').distinct('bobina__window_film__id').annotate(film_id = F('bobina__window_film__id')).values_list('film_id')
    
    def get_inventory_window_film_reel_widths(self, user):
        query = inventario.objects.select_related("bobina","bobina__window_film", "sucursal", "sucursal")
        query = query.filter(sucursal__empleado = user)
        query = query.order_by('bobina__width',).distinct('bobina__width')
        query = query.annotate( width = F('bobina__width'))
        return query
