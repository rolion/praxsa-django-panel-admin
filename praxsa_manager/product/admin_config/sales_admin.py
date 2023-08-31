from typing import Any
from django.contrib import admin
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
from ..models import Sale_Detail, Sale_Detail, Window_Film, inventario
from ..Forms.Sale_header import SaleHeaderForm
from ..Forms.car_model_part import CarModelPartForm
from ..business.proforma import Proforma_Business
from ..business.user import User_Business
from ..business.inventario import Inventario_Business
from django.contrib import messages
from ..helper.user import User_Helper
from ..helper.proforma import Proforma_Helper
from datetime import datetime

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
    min_num = 0
    max = 1
    extra = 0
    form = CarModelPartForm
    user_business = User_Business()
    user_helper = User_Helper()
    inv_business = Inventario_Business()
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
            if db_field.name == "window_film_id":
                # if request.user.is_superuser or self.user_helper.is_request_user_admin(request.user):
                #     result = Window_Film.objects.all()
                # else:
                    sucursal = self.user_business.get_user_sucursal(request.user.username)
                    if sucursal is not None:
                        result = self.inv_business.get_inventory_film_available_film_by_sucursal(sucursal=sucursal)
                    else:
                        if request.user.is_superuser or self.user_helper.is_request_user_admin(request.user):
                            result = Window_Film.objects.all()
                        self.message_user(request=request,  message=str('agregar sucursal a usuario'), level= messages.ERROR)
                    kwargs["queryset"] = result
            return super().formfield_for_foreignkey(db_field, request, **kwargs)
    class Media:
        js=('product/sales_event.js',)
        
    
class SalesAdmin(admin.ModelAdmin):
    list_display = [
                    'id',
                    'sales_status',
                    'sales_type',
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
    actions =["delete_proforma", "fisical_delete_proforma"]
    proforma_business = Proforma_Business()
    user_business = User_Business()
    user_helper = User_Helper()
    proforma_helper = Proforma_Helper()
    fieldsets = [('Proforma', {
                                'classes':[], 
                                "fields":['sales_status','sales_type','sucursal','codigo_garantia','total_price','date']
                                }
                ),
                ("Cliente", {
                    'classes': [],
                    'fields': ["client_id", 'name', "email", "ci_nit", "phone_number",  ]
                }),
                ('Vehiculo', {
                    'classes': [],
                    'fields': ["car_plate", "car_model_id"]
                })]
    
    def get_form(self, request, obj=None, **kwargs):
        form = super(SalesAdmin, self).get_form(request, obj, **kwargs)
        if form.base_fields:
            form.base_fields['sucursal'].initial = self.user_business.get_user_sucursal(username = request.user.username)
            form.base_fields['date'].initial = datetime.now()
        ## print('form ', form.base_fields)
        return form
    
    def proforma_status(self, id):
        proforma = self.proforma_business.get_proforma_by_id(id)
        return proforma.sales_status

    def has_change_permission(self, request: HttpRequest, obj=None):
        if obj is None:
            return False
        if request.user.is_superuser:
            return True
        if obj.sales_status == self.proforma_helper.req or (obj.id is not None and self.proforma_status(obj.id) == self.proforma_helper.req):
            return True
        if self.user_helper.is_request_user_admin(request.user):
            return True
        return False
        # return True
    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        qs = super().get_queryset(request)
        result = self.proforma_business.get_proforma_queryset_by_role(user = request.user, qs=qs)
        if result is None:
            self.message_user(request=request,  message=str('Asigne una sucursal al usuario'), level= messages.ERROR)
            return qs.filter(sucursal = -1)
        return  result
    
    @admin.action(description="Eliminar Proforma")
    def delete_proforma(self, request: HttpRequest, queryset: QuerySet):
        try:
            [self.proforma_business.delete_proforma(user= request.user, proforma=qs) for qs in list(queryset)]
        except Exception as e:
            self.message_user(request=request,  message=str(e), level= messages.ERROR)

    @admin.action(description="Eliminacion Fisica")
    def fisical_delete_proforma(self, request: HttpRequest, queryset: QuerySet):
        try:
            [self.proforma_business.delete_fisica(user= request.user, proforma=qs) for qs in list(queryset)]
        except Exception as e:
            self.message_user(request=request,  message=str(e), level= messages.ERROR)

    