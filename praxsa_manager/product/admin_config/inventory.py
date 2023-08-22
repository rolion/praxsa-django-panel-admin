from typing import Any
from django.contrib import admin
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
from ..models import  instalador_sucursal
from ..helper.user import User_Helper
from ..Forms.inventario import InventarioForm
    
class InventoryAdmin(admin.ModelAdmin):
    list_display = ['sucursal_id', 
                    'bobina',
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
    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        qs = super().get_queryset(request)
        helper = User_Helper()
        if request.user.is_superuser or helper.is_user_admin(request.user):
            return qs
        sucursales = instalador_sucursal.objects.filter(instalador = request.user)
        if len(sucursales) > 0:
            qs_result = qs.filter(sucursal_id = sucursales[0].sucursal_id)
        else:
            qs_result = qs.filter(sucursal_id = -1)
        
        return qs_result
    
    def changelist_view(self, request, extra_context=None):
        helper = User_Helper()
        if request.user.is_superuser or helper.is_user_admin(request.user):
            self.list_display = ['sucursal_id', 
                    'bobina',
                    'get_bobina_width',
                    'quantity',
                    'to_install',
                    'installed',
                    'date']
        elif helper.is_user_installer(request.user):
            self.list_display = [ 
                    'bobina',
                    'quantity',
                    'to_install',
                    'installed',
                    'date']
            self.readonly_fields = [
                    'bobina',
                    'quantity',
                    'to_install',
                    'installed',
                    'date']
        else:
            self.list_display = []
        return super(InventoryAdmin, self).changelist_view(request, extra_context)
