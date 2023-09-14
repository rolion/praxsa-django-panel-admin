from typing import Any
from django import forms
from django.contrib import admin
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
from ..models import Proforma_Detail
from ..Forms.Sale_header import SaleHeaderForm
from ..Forms.car_model_part import CarModelPartForm
from ..business.proforma import Proforma_Business
from ..business.user import User_Business
from ..business.inventario import Inventario_Business
from django.contrib import messages
from ..helper.user import User_Helper
from ..helper.proforma import Proforma_Helper
from django.db import transaction


class SalesDetailInLine(admin.TabularInline):
    fields = ['car_part', 
              'window_film', 
              'width', 
              'length', 
              'disponibilidad',
              'window_film_price', 
              'installation_price', 
              'quantity',
              'sub_total']
    model = Proforma_Detail
    min_num = 0
    max = 1
    extra = 0
    form = CarModelPartForm
    user_business = User_Business()
    user_helper = User_Helper()
    inv_business = Inventario_Business()
    proforma_helper = Proforma_Helper()

    def get_formset(self, request, obj=None, **kwargs):
        formset = super(SalesDetailInLine, self).get_formset(request, obj, **kwargs)
        widths = self.inv_business.get_inventory_window_film_reel_widths(request.user)
        formset.form.base_fields['width'].widget = forms.Select(choices=widths.values_list('width', 'width'))
        return formset

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
            if db_field.name == "window_film":
                    result = self.inv_business.get_user_inventory_window_films(request.user)
                    kwargs["queryset"] = result
            return super().formfield_for_foreignkey(db_field, request, **kwargs)
    class Media:
        js=('product/sales_event.js',)
        
    
class ProformaAdmin(admin.ModelAdmin):
    list_display = [
                    'id',
                    'sales_status',
                    'sales_type',
                    'codigo_garantia',
                    'name', 
                    'car_model_id',
                    'total_price',
                    'proforma_created_on'
                    ]
    exclude =  ["is_delete", "is_paid"]
    inlines = [
        SalesDetailInLine,
    ]
    # readonly_fields = ['sales_status']
    form = SaleHeaderForm
    list_per_page = 10
    actions =["open_proforma","create_sales_note","create_work_note","delete_proforma", "fisical_delete_proforma"]
    proforma_business = Proforma_Business()
    user_business = User_Business()
    user_helper = User_Helper()
    proforma_helper = Proforma_Helper()
    
    fieldsets = [('Proforma', {
                                'classes':[], 
                                "fields":['sales_status',
                                          'sales_type',
                                          'sucursal',
                                          'codigo_garantia',
                                          'total_price',
                                          ]
                                }
                ),
                ("Cliente", {
                    'classes': [],
                    'fields': [ 
                               'name', 
                               "email", 
                               "ci_nit", 
                               "phone_number",  ]
                }),
                ('Vehiculo', {
                    'classes': [],
                    'fields': ["car_plate", 
                               "car_model_id"]
                })]
    
    def get_form(self, request, obj=None, **kwargs):
        form = super(ProformaAdmin, self).get_form(request, obj, **kwargs)
        if form.base_fields and 'sucursal' in form.base_fields:
            form.base_fields['sucursal'].initial = self.user_business.get_user_sucursal(username = request.user.username)
        return form
    
    def proforma_status(self, id):
        proforma = self.proforma_business.get_proforma_by_id(id)
        return proforma.sales_status

    def has_change_permission(self, request: HttpRequest, obj=None):
        if obj is None:
            return True
        if obj.sales_status == self.proforma_helper.prof:
            return True
        if obj.sales_status == self.proforma_helper.nov:
            return False
        return True

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        qs = super().get_queryset(request)
        result = self.proforma_business.get_proforma_queryset_by_role(user = request.user, qs=qs)
        if result is None:
            self.message_user(request=request,  message=str('Asigne una sucursal al usuario'), level= messages.ERROR)
            return qs.filter(sucursal = -1)
        return  result

    def get_readonly_fields(self, request, obj=None):
        # print ('admin obj', obj.sales_status )
        if obj is None:
            return ['sales_status']
        # if obj.sales_status == self.proforma_helper.nov:
        #     return "__all__"
        if obj.sales_status == self.proforma_helper.nov:
            return '__all__'
                    
        return ['sales_status']
    
    @admin.action(description="Eliminar Proforma")
    def delete_proforma(self, request: HttpRequest, queryset: QuerySet):
        try:
            [self.proforma_business.delete_proforma(user= request.user, proforma=qs) for qs in list(queryset)]
        except Exception as e:
            self.message_user(request=request,  message=str(e), level= messages.ERROR)

    @admin.action(description="abrir proforma")
    def open_proforma(self, request: HttpRequest, queryset: QuerySet):
        try:
            [self.proforma_business.abrir_proforma(proforma=qs) for qs in list(queryset)]
        except Exception as e:
            self.message_user(request=request,  message=str(e), level= messages.ERROR)

    @transaction.atomic
    @admin.action(description="crear nota venta")
    def create_sales_note(self, request: HttpRequest, queryset: QuerySet):
        try:
            [self.proforma_business.crear_nota_venta( proforma=qs) for qs in list(queryset)]
        except Exception as e:
            self.message_user(request=request,  message=str(e), level= messages.ERROR)

    @admin.action(description="crear nota trabajo")
    def create_work_note(self, request: HttpRequest, queryset: QuerySet):
        try:
            [self.proforma_business.create_work_note( proforma=qs, responsable = request.user) for qs in list(queryset)]
        except Exception as e:
            self.message_user(request=request,  message=str(e), level= messages.ERROR)

    @admin.action(description="Eliminacion Fisica")
    def fisical_delete_proforma(self, request: HttpRequest, queryset: QuerySet):
        try:
            [self.proforma_business.delete_fisica(user= request.user, proforma=qs) for qs in list(queryset)]
        except Exception as e:
            self.message_user(request=request,  message=str(e), level= messages.ERROR)

    @admin.action(description="Crear Pago")
    def crear_pago(self, request: HttpRequest, queryset: QuerySet):
        try:
            print('crear pago')
        except Exception as e:
            self.message_user(request=request,  message=str(e), level= messages.ERROR)

    