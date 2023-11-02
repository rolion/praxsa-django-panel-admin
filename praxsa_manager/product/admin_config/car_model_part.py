from django.contrib import admin

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