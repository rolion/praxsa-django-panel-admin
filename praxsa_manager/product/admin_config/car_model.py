from django.contrib import admin
from ..models import Car_Model_Part
class CarPartInLine(admin.TabularInline):
    model = Car_Model_Part
    max = 1
    extra = 0
    # form = CarModelPartForm

    
class CarModel(admin.ModelAdmin):
    list_display  = ['name', 'car_brand_id']
    inlines = [ CarPartInLine]
    list_per_page = 10