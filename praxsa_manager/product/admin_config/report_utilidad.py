from typing import Any
from django.http.request import HttpRequest
from django.contrib import admin
from django.db.models.query import QuerySet
from django.http.request import HttpRequest

from product.helper.proforma import Proforma_Helper


# from ..Forms.daily_sales_form import NotaVentaForm
from ..models import inventario

import io
from datetime import datetime
from django.db.models import Count, Sum, Q, F, Case, When
import functools


from django_admin_listfilter_dropdown.filters import DropdownFilter, RelatedDropdownFilter, ChoiceDropdownFilter
from rangefilter.filters import (
    DateRangeFilterBuilder,
    DateTimeRangeFilterBuilder,
    NumericRangeFilterBuilder,
    DateRangeQuickSelectListFilterBuilder,
)
    
class ReportUtilidadAdmin(admin.ModelAdmin):
    
    list_display = [
        "sucursal",
        "bobina",
        "precio_compra_mtr_lineal",
        "precio_venta_mtr_lineal",
        "get_utilidad"
    ]
    
    list_filter = [
        ('sucursal', ChoiceDropdownFilter),
        ('sucursal', RelatedDropdownFilter),
        ('bobina', RelatedDropdownFilter)]
    
    def get_utilidad(self, obj):
        return str( round(obj.sum_film_utilidad,2))+" Bs"
    get_utilidad.short_description = 'Utilidad Lamina'
    get_utilidad.admin_order_field = 'sum_film_utilidad'
    
    helper = Proforma_Helper()
    
    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        
        qs = super().get_queryset(request)
        qs = inventario.objects.all().select_related(
            "sucursal","bobina", "bobina__window_film").filter(lamina_inventario__proforma_header__nota_trabajo__nota_venta__isnull=False).annotate(
                sum_film_utilidad=Sum(Case(
                    When(lamina_inventario__proforma_header__sales_type=self.helper.tipo_venta_metro_lineal, 
                         then=F("lamina_inventario__window_film_price") * F("lamina_inventario__length")),
                    When(lamina_inventario__proforma_header__sales_type=self.helper.tipo_venta_instalacion, 
                         then=F("lamina_inventario__window_film_price") * (F("lamina_inventario__length") * F("lamina_inventario__quantity")))   
                         )))
        return  qs
    
    def has_add_permission(self, request, obj=None):
        return False
    
    def has_change_permission(self, request: HttpRequest, obj: Any | None = ...) -> bool:
        return False
    
    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions