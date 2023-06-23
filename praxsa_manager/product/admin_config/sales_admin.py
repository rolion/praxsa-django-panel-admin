from django.contrib import admin
from ..models import Sale_Detail
from ..forms import CarModelPartForm

class SalesDetailInLine(admin.TabularInline):
    model = Sale_Detail
    min_num = 1
    form = CarModelPartForm
    
    class Media:
        js=('product/sales_event.js',)
        
    
class SalesAdmin(admin.ModelAdmin):
    list_display = [
        'id',
                    'sales_status',
                    'client_id', 
                    'car_model_id',
                    'total_price',
                    'date']
    inlines = [
        SalesDetailInLine,
    ]
    list_per_page = 10