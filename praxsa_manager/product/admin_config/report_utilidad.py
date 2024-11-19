from typing import Any
from django.http.request import HttpRequest
from django.contrib import admin
from django.db.models.query import QuerySet
from django.http.request import HttpRequest


# from ..Forms.daily_sales_form import NotaVentaForm
from ..models import inventario

import io
from datetime import datetime
from django.db.models import Count, Sum, Q, F
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
    
    def get_utilidad(self, obj):
        return str( round(obj.sum_film_utilidad,2))+" Bs"
    get_utilidad.short_description = 'Utilidad Lamina'
    get_utilidad.admin_order_field = 'sum_film_utilidad'
    
    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        qs = super().get_queryset(request)
        qs = inventario.objects.all().select_related(
            "sucursal","bobina", "bobina__window_film").filter(lamina_inventario__proforma_header__nota_trabajo__nota_venta__isnull=False).annotate(
                sum_film_utilidad=Sum(F("lamina_inventario__window_film_price") * F("lamina_inventario__length")))
            
        # print("qs-->", list(qs))
        return  qs