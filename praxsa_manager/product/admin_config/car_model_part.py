from django.contrib import admin
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
from typing import Any
from ..models import Car_Model_Part
    
class CarModelPart(admin.ModelAdmin):
    list_display = ['car_model_id', 
                    'car_part_id', 
                    "width", 
                    'length',
                    'quantity']
    list_per_page = 10

    search_fields = ['id',
                     'car_model_id__name',
                     'car_part_id__name',
                     'width', 
                     'length',]
    
    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        qs = super().get_queryset(request)
        
        return  qs.select_related('car_model_id', 'car_part_id__name',)