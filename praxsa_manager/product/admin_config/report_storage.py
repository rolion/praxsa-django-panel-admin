from typing import Any
from django.http.request import HttpRequest
from django.contrib import admin
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
from django.contrib import messages
from django.db import transaction

from product.Forms.pagos import PagosForm
from product.business.user import User_Business
from product.business.inventario import Inventario_Business
from product.helper.proforma import Proforma_Helper
from product.helper.user import User_Helper
from django.urls import reverse
from django.utils.html import format_html
from django.db.models import Count, Sum, Avg
import functools

from django_admin_listfilter_dropdown.filters import DropdownFilter, RelatedDropdownFilter, ChoiceDropdownFilter
from rangefilter.filters import (
    DateRangeFilterBuilder,
    DateTimeRangeFilterBuilder,
    NumericRangeFilterBuilder,
    DateRangeQuickSelectListFilterBuilder,
)
    
class ReportStorageAdmin(admin.ModelAdmin):
    list_display = [
        "sucursal",
        "get_lamina_name",
        "get_width",
        "get_metros_disponibles"
    ]
    
    search_fields = ["bobina__window_film__name",]
    
    list_filter = [
        ('sucursal', RelatedDropdownFilter),]
    
    actions =[]
    list_per_page = 10
    inventario_business = Inventario_Business()
    user_helper = User_Helper()

    def get_lamina_name(self, obj):
        # link para ver la nota de trabajo
        # pero se visualiza el id de la proforma
        return obj.bobina.window_film.name
    get_lamina_name.short_description = 'Lamina'
    
    def get_width(self, obj):
        # link para ver la nota de trabajo
        # pero se visualiza el id de la proforma
        return obj.bobina.width
    get_width.short_description = 'Ancho'
    
    def get_metros_disponibles(self, obj):
        # link para ver la nota de trabajo
        # pero se visualiza el id de la proforma
        metrod_disponibles =  next(inv["total_to_install"] for inv in self.aggregated_result if  inv["sucursal__id"]== obj.sucursal.id and inv["bobina__window_film__id"]== obj.bobina.window_film.id and inv["bobina__width"] == obj.bobina.width)
        return metrod_disponibles
    get_metros_disponibles.short_description = 'Metros disponibles'
    
    aggregated_result = []
    
    
    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        qs = super().get_queryset(request)
        base_qs = self.inventario_business.get_inventario_queryset_by_role(user = request.user, qs=qs)
        # get_inventario_queryset_by_role ya no devuelve None (ver REV-2026-09-27-
        # modulo-almacen-02) -- se replica aca la misma condicion de sucursal
        # que ese metodo usa, para no confundir "sin sucursal asignada" con
        # "el reporte da 0 filas legitimamente" (ambos casos dan un queryset vacio).
        if not self.user_helper.can_view_all_sucursales(request.user) and not self.user_helper.has_assigned_sucursal(request.user):
            self.message_user(request=request,  message=str('Asigne una sucursal al usuario'), level= messages.ERROR)
            base_qs = qs.filter(sucursal = -1)

        result = base_qs.select_related("sucursal", "bobina", "bobina__window_film")
        result = result.values("sucursal__id","sucursal__name", "bobina__window_film__id","bobina__window_film__name", "bobina__width")
        result = result.annotate(total_to_install=Sum('to_install'))
        result = result.annotate(total_installed = Sum('installed'))
        result = result.annotate(avg_costo_compra = Sum('precio_compra_mtr_lineal'))
        result = result.order_by("sucursal__name", "bobina__window_film__name", "bobina__width")
        self.aggregated_result= result
        return base_qs.select_related("sucursal", "bobina", "bobina__window_film").distinct("sucursal__id","bobina__window_film__id", "bobina__width").order_by("sucursal__id","bobina__window_film__id", "bobina__width")
    
    def has_add_permission(self, request, obj=None):
        return False
    
    def has_change_permission(self, request: HttpRequest, obj: Any | None = ...) -> bool:
        return False
    
    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions