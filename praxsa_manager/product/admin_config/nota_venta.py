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
from django.http import HttpResponseRedirect

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
        
    
class NotaVentaAdmin(admin.ModelAdmin):
    list_display = [
                    'id',
                    'sales_type',
                    'codigo_garantia',
                    'name', 
                    'car_model_id',
                    'total_price',
                    'proforma_created_on',
                    'is_paid'
                    ]
    exclude =  ["is_delete", "is_paid"]
    inlines = [
        SalesDetailInLine,
    ]
    # readonly_fields = ['sales_status']
    form = SaleHeaderForm
    list_per_page = 10
    actions =['gestion_pago']
    proforma_business = Proforma_Business()
    user_business = User_Business()
    user_helper = User_Helper()
    proforma_helper = Proforma_Helper()
    
    fieldsets = [('Nota Venta', {
                                'classes':[], 
                                "fields":[
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
                }),
                ('Nota trabajo', {
                     'classes':[],
                     'fields':['view_notas_observaciones', 
                               'view_notas_entrada_vehiculo', 
                               'view_notas_salida_vehiculo']
                })
                ]
    @admin.display(empty_value="-", description='Observaciones' )
    def view_notas_observaciones(self, obj):
        if obj is None:
             return ''
        if obj.nota_trabajo is None:
             return ''
        return obj.nota_trabajo.observaciones
    
    @admin.display(empty_value="-", description='Entrada Vehiculo')
    def view_notas_entrada_vehiculo(self, obj):
        if obj is None:
             return ''
        if obj.nota_trabajo is None:
             return ''
        return obj.nota_trabajo.entrada_vehiculo.strftime("%d-%m-%Y %H:%M:%S")

    @admin.display(empty_value="-", description='Salida Vehiculo')
    def view_notas_salida_vehiculo(self, obj):
        if obj is None:
             return ''
        if obj.nota_trabajo is None:
             return ''
        return obj.nota_trabajo.salida_vehiculo.strftime("%d-%m-%Y %H:%M:%S")

    
    def has_change_permission(self, request: HttpRequest, obj=None):
        return False
    
    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        qs = super().get_queryset(request)
        result = self.proforma_business.get_nota_venta_queryset_by_role(user = request.user, qs=qs)
        if result is None:
            self.message_user(request=request,  message=str('Asigne una sucursal al usuario'), level= messages.ERROR)
            return qs.filter(sucursal = -1)
        return  result
    

    @admin.action(description="Gestionar Pago")
    def gestion_pago(self, request: HttpRequest, queryset: QuerySet):
        try:
            qs = list(queryset)
            if len(qs) > 0:
                pago = self.proforma_business.create_nota_venta_pago(proforma=qs[0], user=request.user)
                return HttpResponseRedirect(f'/admin/product/pago/{pago.id}/change')
        except Exception as e:
            self.message_user(request=request,  message=str(e), level= messages.ERROR)