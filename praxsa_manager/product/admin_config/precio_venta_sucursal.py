from ..Forms.pagos import PagosForm
from typing import Any
from django.contrib import admin
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
from django.contrib import messages
from ..models import Sucursal, Window_Film, precio_venta_sucursal
from ..Forms.precio_venta_sucursal_form import PrecioVentaSucursalForm
from ..business.precio_venta import Precio_Venta_Business
class PrecioVentaSucursalAdmin(admin.ModelAdmin):
    list_display = ['sucursal', 
                    'lamina',
                    'width',
                    'precio_venta']
    list_per_page = 10
    form = PrecioVentaSucursalForm
    
    precio_venta = Precio_Venta_Business()
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        user = request.user
        sucursales = Sucursal.objects.prefetch_related('empleado')
        sucursales = sucursales.filter(empleado__id = user.id, enable_to_install_windows_film = True).select_related()
        if db_field.name == "sucursal":
            # Filtrar sucursales (por ejemplo, solo las activas)
            kwargs["queryset"] = sucursales
            
        if db_field.name == 'lamina':
            laminas = Window_Film.objects.prefetch_related('bobina_lamina__bobina_inventario__sucursal')
            laminas = laminas.filter(bobina_lamina__bobina_inventario__sucursal__in  = sucursales).distinct()
            kwargs["queryset"] =  laminas
             
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def save_model(self, request, obj, form, change):
        if not change:
            # obj.sucursal = form.sucursal
            # obj.lamina = form.lamina
            # obj.width = form.width
            result = precio_venta_sucursal.objects.filter(sucursal = obj.sucursal, lamina = obj.lamina, width = obj.width)
            if len(result) > 0:
                messages.set_level(request, messages.ERROR) 
                messages.error(
                    request=request,
                    message=str('ya existe un precio para la lamina ' + obj.lamina.name + ' con el ancho '+ str(obj.width) +' para la sucursal '+ obj.sucursal.name))
                return
        super().save_model(request, obj, form, change)
    
    #  messages.set_level(request, messages.ERROR) 
    #         messages.error(
    #             request=request,
    #             message=str('no se puede eliminar proformas que ya estan registradas como notas de trabajo')
    
    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
            qs = super().get_queryset(request)
            result = self.precio_venta.get_precio_venta_sucursal_queryset_by_role(user = request.user, qs=qs)
            if result is None:
                self.message_user(request=request,  message=str('Asigne una sucursal al usuario'), level= messages.ERROR)
                return qs.filter(sucursal = -1)
            return  result