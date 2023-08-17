from typing import Any
from django.contrib import admin
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
from ..models import Sale_Detail, instalador_sucursal
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from ..forms import CarModelPartForm

class SalesDetailInLine(admin.TabularInline):
    fields = ['car_part_id', 
              'window_film_id', 
              'width', 
              'length', 
              'window_film_price', 
              'installation_price', 
              'quantity', 
              'sub_total']
    model = Sale_Detail
    min_num = 1
    form = CarModelPartForm
    
    class Media:
        js=('product/sales_event.js',)
        
    
class SalesAdmin(admin.ModelAdmin):
    list_display = [
                    'id',
                    'sales_status',
                    'codigo_garantia',
                    'client_id', 
                    'car_model_id',
                    'total_price',
                    'date'
                    ]
    inlines = [
        SalesDetailInLine,
    ]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        sucursales = instalador_sucursal.objects.filter(instalador = request.user)
        if len(sucursales) > 0:
            qs_result = qs.filter(sucursal = sucursales[0].sucursal_id)
        else:
            qs_result = qs.filter(sucursal = -1)
        
        return qs_result
    
    list_per_page = 10