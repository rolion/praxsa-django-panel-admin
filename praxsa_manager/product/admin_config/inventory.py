from typing import Any
from django.contrib import admin
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
from ..business.inventario import Inventario_Business
from ..helper.user import User_Helper
from ..Forms.inventario import InventarioForm
from .sucursal_scope import SucursalWritableAdminMixin


class InventoryAdmin(SucursalWritableAdminMixin, admin.ModelAdmin):
    list_display = ['sucursal',
                    'get_bobina_name',
                    'get_bobina_width',
                    'quantity',
                    'to_install',
                    'installed',
                    'nro_lote',
                    'numero_referencia',
                    'get_inventory_date_format']
    list_per_page = 10
    search_fields = ['sucursal__name', 'bobina__window_film__name', 'numero_referencia','nro_lote']
    form = InventarioForm
    # Campos que ve y edita quien tiene gestion completa (superusuario o grupo admin).
    full_access_fields = [
        'sucursal',
        'bobina',
        'quantity',
        'to_install',
        'installed',
        'nro_lote',
        'precio_compra_mtr_lineal',
        'precio_venta_mtr_lineal',
        'numero_referencia',
        'date']
    supervisor_readonly_fields = [
        'sucursal',
        'bobina',
        'quantity',
        'precio_compra_mtr_lineal',
        'to_install',
        'installed',
        'numero_referencia',
        'original_length',
        'date']

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

    def get_inventory_date_format(self, obj):
        return obj.date.strftime("%d-%m-%Y %H:%M:%S")
    get_inventory_date_format.short_description = 'Fecha'
    get_inventory_date_format.admin_order_field = 'date'

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        qs = super().get_queryset(request).select_related('bobina', "sucursal", "bobina__window_film")
        # Alcance de lectura: las sucursales asignadas al usuario (activas o no);
        # solo el superusuario ve todas. Sin sucursal, ninguna fila.
        return Inventario_Business().get_panel_inventario_queryset(request.user, qs)

    def _has_full_access(self, request):
        return request.user.is_superuser or User_Helper().is_request_user_admin(request.user)

    # Nada de estado en la instancia (es compartida por todas las peticiones del
    # proceso): list_display, fields y readonly_fields se calculan por peticion.
    def get_list_display(self, request):
        columns = [
            'get_bobina_name',
            'get_bobina_width',
            'quantity',
            'to_install',
            'installed',
            'nro_lote',
            'numero_referencia',
            'get_inventory_date_format']
        if self._has_full_access(request) or User_Helper().get_readable_sucursales(request.user).count() != 1:
            columns.insert(0, 'sucursal')
        return columns

    def get_fields(self, request, obj=None):
        if self._has_full_access(request):
            return list(self.full_access_fields)
        return super().get_fields(request, obj)

    def get_readonly_fields(self, request, obj=None):
        if not self._has_full_access(request) and User_Helper().is_request_user_supervisor(request.user):
            return list(self.supervisor_readonly_fields)
        return []
