from typing import Any
from django import forms
from django.contrib import admin
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
from ..models import Proforma_Detail
from ..Forms.nota_venta_form import NotaVentaForm
from ..Forms.car_model_part import CarModelPartForm
from ..business.proforma import Proforma_Business
from ..business.user import User_Business
from ..business.inventario import Inventario_Business
from django.contrib import messages
from ..helper.user import User_Helper
from ..helper.proforma import Proforma_Helper
from django.http import HttpResponseRedirect
from ..helper.pdf import PDFService
from django.http import FileResponse
import io

# class SalesDetailInLine(admin.TabularInline):
#     fields = ['car_part', 
#               'window_film', 
#               'width', 
#               'length', 
#               'disponibilidad',
#               'window_film_price', 
#               'installation_price', 
#               'quantity',
#               'sub_total']
#     model = Proforma_Detail
#     min_num = 0
#     max = 1
#     extra = 0
#     form = CarModelPartForm
#     user_business = User_Business()
#     user_helper = User_Helper()
#     inv_business = Inventario_Business()
#     proforma_helper = Proforma_Helper()

#     def get_formset(self, request, obj=None, **kwargs):
#         formset = super(SalesDetailInLine, self).get_formset(request, obj, **kwargs)
#         widths = self.inv_business.get_inventory_window_film_reel_widths(request.user)
#         formset.form.base_fields['width'].widget = forms.Select(choices=widths.values_list('width', 'width'))
#         return formset

#     def formfield_for_foreignkey(self, db_field, request, **kwargs):
#             if db_field.name == "window_film":
#                     result = self.inv_business.get_user_inventory_window_films(request.user)
#                     kwargs["queryset"] = result
#             return super().formfield_for_foreignkey(db_field, request, **kwargs)
#     class Media:
#         js=('product/sales_event.js',)
        
    
class NotaVentaAdmin(admin.ModelAdmin):
    list_display = [
                    'id',
                    'nota_trabajo',
                    'total_price',
                    'view_notas_created_on'
                    ]
    search_fields = ['id','nota_trabajo__id','created_on', 'name',]
    form = NotaVentaForm
    list_per_page = 10
    actions =['gestion_pago', 'print_nota_venta']
    proforma_business = Proforma_Business()
    user_business = User_Business()
    user_helper = User_Helper()
    proforma_helper = Proforma_Helper()
    
    fieldsets = [('Nota Venta', {
                                'classes':[], 
                                "fields":[
                                          'nota_trabajo',
                                          
                                          ]
                                }
                ),
                ("Cliente", {
                    'classes': [],
                    'fields': [ 
                               'name', 
                               "ci_nit",
                               'total_price', ]
                }),
                ]
    
    @admin.display(empty_value="-", description='Nota Trabajo' )
    def view_nota_trabajo(self, obj):
        if obj is None:
             return ''
        if obj.nota_trabajo is None:
             return ''
        return obj.nota_trabajo.id
    
    @admin.display(empty_value="-", description='Creado en')
    def view_notas_created_on(self, obj):
        if obj is None:
             return ''
        return obj.created_on.strftime("%d-%m-%Y %H:%M:%S")

    
    def has_change_permission(self, request: HttpRequest, obj=None):
        if obj is None:
            return True
        if obj.is_close == False: 
            return True
        return False
    
    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return []
        return ['total_price', 'nota_trabajo']
    
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
                return HttpResponseRedirect(f'/admin/product/pago/add/?nota_venta={qs[0].id}')
        except Exception as e:
            self.message_user(request=request,  message=str(e), level= messages.ERROR)

    @admin.action(description="Imprimir Nota Venta")
    def print_nota_venta(self, request: HttpRequest, queryset: QuerySet):
        # try:
            buffer = io.BytesIO()
            pdf = PDFService(buffer= buffer)
            print('qs ', queryset[0])
            proforma = queryset[0].nota_trabajo.proforma
            codigo_garantia = queryset[0].nota_trabajo.codigo_garantia
            prodorma_detail = Proforma_Detail.objects.select_related("car_part", "window_film")
            prodorma_detail = prodorma_detail.filter( proforma_header = proforma)
            pdf.create_proforma(detail=prodorma_detail, header=proforma, codigo_garantia=codigo_garantia, title= 'Nota Venta')
            buffer.seek(0)
            filename = f'Nota Venta-{queryset[0].id}.pdf'
            return FileResponse(buffer, as_attachment=True, filename=filename)