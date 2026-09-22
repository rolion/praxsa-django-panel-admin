from ..models import Sucursal, Window_Film, inventario, precio_venta_sucursal
from django.db.models import Sum, F, OuterRef, Subquery
from ..utils.exception.nohaylaminas import NoHayLaminasDisponibles
from ..helper.user import User_Helper
import logging

class Inventario_Business:

    def __init__(self) -> None:
        self.log_errors = logging.getLogger('django_admin')
        self.log_debug= logging.getLogger('debug')
        self.user_helper = User_Helper()

    def get_inventario_queryset_by_role(self, user, qs):
        try:
            if self.user_helper.can_view_all_sucursales(user):
                return qs
            sucursales = Sucursal.objects.prefetch_related('empleado')
            sucursales = sucursales.filter(empleado__id = user.id, enable_to_install_windows_film = True)
            if len(sucursales) > 0:
                qs_result = qs.filter(sucursal__id = sucursales[0].id)
            else:
                qs_result = None
            return qs_result
        except Exception as e:
            self.log_errors.error(f'algo salio mal, Inventario_Business - get_inventario_queryset_by_role {e}')
            return None

    def get_inventory_by_sucursal(self, sucursal):
        q = inventario.objects.select_related("bobina","bobina__window_film", "sucursal")
        q = q.order_by('bobina__window_film__id', '-date')
        # q = q.distinct("bobina__window_film_id__id")
        q = q.filter(sucursal = sucursal, sucursal__enable_to_install_windows_film = True, to_install__gt = 0)
        return q
    
    def get_inventory_film_available_film_by_sucursal(self, sucursal):
        q = self.get_inventory_by_sucursal(sucursal=sucursal)
        q = q.values_list("bobina__window_film__id")
        q = q.annotate(
                    precio_venta_sucursal=Subquery(
                        precio_venta_sucursal.objects.filter(
                            sucursal=OuterRef("sucursal"),
                            lamina=OuterRef('bobina__window_film'),
                            width = OuterRef('bobina__width')
                        ).values("precio_venta")[:1]  # Trae solo un valor de precio si hay múltiples coincidencias
                    )
                )
        return q.annotate(total=Sum("to_install")).filter(sucursal__id = sucursal.id).order_by('bobina__window_film__name','bobina__width' )
        # result = Window_Film.objects.filter(pk__in = q)
        return result
    
    def reduce_inventory(self, sucursal, windows_film, width, length_to_reduce):
        query = inventario.objects.select_related('bobina', 'sucursal', 'bobina__window_film')
        query = query.filter(sucursal = sucursal, 
                             bobina__window_film = windows_film, 
                             bobina__width = width, 
                             to_install__gte = length_to_reduce)
        query = query.order_by('bobina__width','date')[:1]
        self.log_debug.info(f'{sucursal}, {windows_film}, {width}, {length_to_reduce}')
        self.log_debug.info(f'inventario existe {query.exists()}')
        self.log_debug.info(f'width {width}, film {windows_film}')
        self.log_debug.info(query.query)
        
        if(query.exists()):
            bobina_inventario = query[0]
            bobina_inventario.to_install = bobina_inventario.to_install - length_to_reduce
            bobina_inventario.installed = bobina_inventario.installed + length_to_reduce
            bobina_inventario.save()
            return bobina_inventario
        raise NoHayLaminasDisponibles(f'no hay lamina disponible {windows_film.name} {width}')
        #return False
    
    def return_to_inventory(self, detail_inventory, length_to_add):
        try:
            inv = inventario.objects.select_related('bobina', 'sucursal')
            inv = inv.get(id = detail_inventory.id)
            inv.to_install = inv.to_install + length_to_add
            inv.installed = inv.installed - length_to_add
            inv.save()
            return True
        except Exception as e:
            self.log_errors.error(f'no se pudo actualizar el inventario -> {e}')
            return False
        
    def is_window_film_available(self, sucursal_id, bobina, width, to_install):
        query = inventario.objects.select_related('bobina', 'sucursal')
        query = query.filter(sucursal__id = sucursal_id, bobina__id = bobina, width__gte=width, to_install__gte = to_install).order_by('date','width')
        if len(query) > 0:
            return True
        return False
    
    def get_total_meters_window_film_in_inventory(self, sucursal_id, lamina_id, width):
        inventario_qs = inventario.objects.filter(sucursal_id=sucursal_id,to_install__gt=0)
           
        if lamina_id > 0:
            inventario_qs = inventario_qs.filter(
                bobina__window_film_id=lamina_id
            )

        if width > 0:
            inventario_qs = inventario_qs.filter(
                bobina__width__gte=width
            )

        inventario_qs = inventario_qs.values(
                "sucursal_id",
                "bobina__window_film__id",
                "bobina__window_film__name",
                "bobina__width",
                "precio_venta_mtr_lineal"
            ).annotate(
                total_metros=Sum("to_install"),

                precio_sucursal=Subquery(
                    precio_venta_sucursal.objects.filter(
                        sucursal_id=OuterRef("sucursal_id"),
                        lamina_id=OuterRef("bobina__window_film__id"),
                        width=OuterRef("bobina__width")
                    ).values("precio_venta")[:1]
                )
            ).order_by(
                "bobina__window_film__name",
                "bobina__width"
            )

        return inventario_qs
    
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
        query = inventario.objects.select_related("bobina","bobina__window_film", "sucursal")
        query = query.filter(sucursal__empleado = user)
        query = query.order_by('bobina__width',).distinct('bobina__width')
        query = query.annotate( width = F('bobina__width'))
        return query
