from typing import Any
from django.contrib import admin
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
from ..models import Sale_Detail, Sucursal, Sale_Detail
from ..Forms.Sale_header import SaleHeaderForm
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from ..Forms.car_model_part import CarModelPartForm
from ..business.proforma import Proforma_Business
from django.contrib import messages
from ..helper.user import User_Helper
from ..helper.proforma import Proforma_Helper

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
    max = 1
    extra = 0
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
    exclude =  ["is_delete"]
    inlines = [
        SalesDetailInLine,
    ]
    form = SaleHeaderForm
    list_per_page = 10
    actions =["delete_proforma"]
    proforma_business = Proforma_Business()
    user_helper = User_Helper()
    proforma_helper = Proforma_Helper()

    def has_change_permission(self, request: HttpRequest, obj=None):
        if request.user.is_superuser:
            return True
        if obj is None:
            return False
        if obj.sales_status == self.proforma_helper.req:
            return True
        if self.user_helper.is_user_admin(request.user):
            return True
        return False
    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        qs = super().get_queryset(request)
        return self.proforma_business.get_proforma_queryset_by_role(user = request.user, qs=qs)
    
    @admin.action(description="Eliminar Proforma")
    def delete_proforma(self, request: HttpRequest, queryset: QuerySet):
        try:
            [self.proforma_business.delete_proforma(user= request.user, proforma=qs) for qs in list(queryset)]
        except Exception as e:
            self.message_user(request=request,  message=str(e), level= messages.ERROR)

    