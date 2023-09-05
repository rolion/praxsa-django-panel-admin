from typing import Any
from django.contrib import admin
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
from ..models import  Sucursal
from ..helper.user import User_Helper
from ..Forms.inventario import InventarioForm
    
class InventoryAdmin(admin.ModelAdmin):
    list_display = ['sucursal', 
                    'get_bobina_name',
                    'get_bobina_width',
                    'quantity',
                    'to_install',
                    'installed',
                    'date']
    list_per_page = 10
    form = InventarioForm
    class Media:
        js=('product/inventario.js',)
        

    def get_bobina_width(self, obj):
        return obj.bobina.width
    get_bobina_width.short_description = 'Ancho Bobina'
    get_bobina_width.admin_order_field = 'bobina__width'

    def get_bobina_name(self, obj):
        return obj.bobina.window_film.name
    get_bobina_name.short_description = 'Lamina'
    get_bobina_name.admin_order_field = 'bobina__window_film__name'

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        qs = super().get_queryset(request).select_related('bobina', "sucursal", "bobina__window_film")
        helper = User_Helper()

        if request.user.is_superuser or helper.is_request_user_admin(request.user):
            return qs
        
        sucursales = Sucursal.objects.filter(empleado__id = request.user.id)
        if len(sucursales) > 0:
            qs_result = qs.filter(sucursal__id = sucursales[0].id)
        else:
            qs_result = qs.filter(sucursal_id = -1)
        
        return qs_result
    
    def changelist_view(self, request, extra_context=None):
        helper = User_Helper()
        if request.user.is_superuser or helper.is_request_user_admin(request.user):
            self.list_display = [
                    'sucursal', 
                    'get_bobina_name',
                    'get_bobina_width',
                    'quantity',
                    'to_install',
                    'installed',
                    'date']
            self.fields = [
                    'sucursal', 
                    'bobina',
                    'quantity',
                    'to_install',
                    'installed',
                    'precio_compra_mtr_lineal',
                    'precio_venta_mtr_lineal']
            self.readonly_fields = []
        elif helper.is_request_user_supervisor(request.user):
            self.list_display = [ 
                    'get_bobina_name',
                    'get_bobina_width',
                    'quantity',
                    'to_install',
                    'installed',
                    'date']
            self.readonly_fields = [
                    'sucursal',
                    'bobina',
                    'quantity',
                    'precio_compra_mtr_lineal',
                    'to_install',
                    'installed',
                    'date']
        else:
            self.list_display = []
        return super(InventoryAdmin, self).changelist_view(request, extra_context)

