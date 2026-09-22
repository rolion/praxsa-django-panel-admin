from typing import Any
from django.http.request import HttpRequest
from django.contrib import admin
from django.contrib import messages
from django.db.models.query import QuerySet
from django.http.request import HttpRequest

from product.helper.proforma import Proforma_Helper
from ..business.inventario import Inventario_Business

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
    inventario_business = Inventario_Business()

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:

        base_qs = super().get_queryset(request)
        base_qs = self.inventario_business.get_inventario_queryset_by_role(user = request.user, qs=base_qs)
        if base_qs is None:
            self.message_user(request=request,  message=str('Asigne una sucursal al usuario'), level= messages.ERROR)
            base_qs = super().get_queryset(request).filter(sucursal = -1)

        qs = base_qs.select_related(
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