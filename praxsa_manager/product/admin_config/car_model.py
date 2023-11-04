from django.contrib import admin
from typing import Any
from ..models import Car_Model_Part
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
class CarPartInLine(admin.TabularInline):
    model = Car_Model_Part
    max = 1
    extra = 0
    # form = CarModelPartForm

    
class CarModel(admin.ModelAdmin):
    list_display  = ['name', 'car_brand_id']
    inlines = [ CarPartInLine]
    list_per_page = 10
    search_fields = [
                     'name','car_brand_id__name']
    
    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        qs = super().get_queryset(request)
        
        return  qs.select_related('car_brand_id')