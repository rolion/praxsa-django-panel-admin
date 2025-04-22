from typing import Any
from django import forms
from django.contrib import admin
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
from ..models import Nota_trabajo, Proforma_Detail
from ..Forms.Sale_header import SaleHeaderForm
from ..Forms.car_model_part import CarModelPartForm
from ..business.proforma import Proforma_Business
from ..business.user import User_Business
from ..business.inventario import Inventario_Business
from django.contrib import messages
from ..helper.user import User_Helper
from ..helper.proforma import Proforma_Helper
from django.db import transaction
from ..helper.pdf import PDFService
from django.http import FileResponse
from django_admin_listfilter_dropdown.filters import DropdownFilter, RelatedDropdownFilter, ChoiceDropdownFilter
import io
import logging


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
    exclude =  ["inventario"]
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
    log_errors = logging.getLogger('django_admin')
    log_debug= logging.getLogger('debug')
    
    list_display = [
                    'id',
                    # 'sales_status',
                    'sales_type',
                    'name', 
                    'car_model_id',
                    'get_total_pagar',
                    'get_proforma_date_format',
                    'get_estado'
                    ]
    exclude =  ["is_delete", "is_paid", 'created_by', 'is_close']
    inlines = [
        SalesDetailInLine,
    ]
    search_fields = ["id", 'sales_type', 'proforma_created_on', 'name', 'email', 'car_model_id__name']
    # readonly_fields = ['sales_status']
    form = SaleHeaderForm
    list_per_page = 10
    actions =["open_proforma", "create_sales_note", "create_work_note", "print_proforma", "convertir_proforma_metro_lineal"]
    proforma_business = Proforma_Business()
    user_business = User_Business()
    user_helper = User_Helper()
    proforma_helper = Proforma_Helper()
    def get_total_pagar(self, obj):
        total = obj.total_price - obj.discount
        return f'{total} Bs'
    get_total_pagar.short_description = 'Total Pagar'
    get_total_pagar.admin_order_field = 'total_price'
    def get_proforma_date_format(self, obj):
        return obj.proforma_created_on.strftime("%d-%m-%Y %H:%M:%S")
    get_proforma_date_format.short_description = 'Fecha'
    get_proforma_date_format.admin_order_field = 'proforma_created_on'

    def get_estado(self, obj):
        estado = 'Proforma'
        if(hasattr(obj, 'nota_trabajo')):
           estado = 'Nota Trabajo'
        else:
            return estado
        if(hasattr(obj.nota_trabajo, 'nota_venta')):
             estado = 'Por Cobrar'
        else:
            return estado
        if(hasattr(obj.nota_trabajo.nota_venta, 'pago')):
             estado = 'Finalizado'

        return estado
       
    get_estado.short_description = 'Estado'
    
    fieldsets = [('Proforma', {
                                'classes':[], 
                                "fields":[
                                    # 'sales_status',
                                          'sales_type',
                                          'sucursal',
                                          'total_price',
                                          ]
                                }
                ),
                ("Descuento",{
                     'classes': [],
                     'fields': [ 
                               'discount',
                               "discount_reason",  ]
                }),
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
    
    def save_related(self, request, form, formsets, change):
        to_reduce = 0
        to_add = 0
        proforma = form.instance
        if change == True:
            for formset in formsets:
                formset.save(commit=False)
                if formset.model == Proforma_Detail:
                    for deleted_data in formset.deleted_objects:
                        to_reduce = to_reduce + deleted_data.sub_total
                    
            proforma.total_price = proforma.total_price - to_reduce
            # proforma.origen = self.proforma_helper.origin_portal
            proforma.save()
        super(ProformaAdmin, self).save_related(request, form, formsets, change)

    def has_change_permission(self, request: HttpRequest, obj=None):
        if obj is None:
            return True
        if obj.is_close == False:
            return True
        return False

    def changelist_view(self, request, extra_context=None):
        user_groups = list(request.user.groups.values_list('name',flat = True))
        is_admin = 'Admin' in user_groups
        if is_admin == True:
            self.list_display = [
                    'id',
                    'sales_type',
                    'name', 
                    'sucursal',
                    'car_model_id',
                    'get_total_pagar',
                    'get_proforma_date_format',
                    'get_estado'
                    ]
            self.list_filter = [
                ('sales_type', ChoiceDropdownFilter),
                ('sucursal', RelatedDropdownFilter),]
        return super(ProformaAdmin, self).changelist_view(request, extra_context)
    
    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        qs = super().get_queryset(request)
        result = self.proforma_business.get_proforma_queryset_by_role(user = request.user, qs=qs)
        if result is None:
            self.message_user(request=request,  message=str('Asigne una sucursal al usuario'), level= messages.ERROR)
            return qs.filter(sucursal = -1)
        return  result

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return []
        if obj.is_close == True:
            return '__all__'
                    
        return ['sucursal', 'sales_type' ]
    
    def save_model(self, request, obj, form, change):
        obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    @transaction.atomic
    def delete_queryset(self, request, qs: QuerySet):
        idsQS = qs.all()
        ids = idsQS.values_list('id', flat=True)
        inventory_list = Nota_trabajo.objects.select_related('proforma').filter(proforma__id__in = ids)
        if len(inventory_list) > 0:
            messages.set_level(request, messages.ERROR) 
            messages.error(
                request=request,
                message=str('no se puede eliminar proformas que ya estan registradas como notas de trabajo')
            )
        else:
            try:
                with transaction.atomic():
                    for entry in list(qs):
                        entry.is_delete = True
                        entry.save()
            except Exception as e:
                self.log_debug.info(str(e))
                messages.set_level(request, messages.ERROR) 
                messages.error(
                    request=request,
                    message=str('Algo salio mal, contactar al adminsitrador')
                )
    
    @admin.action(description="Eliminar Proforma")
    def delete_proforma(self, request: HttpRequest, queryset: QuerySet):
        try:
            [self.proforma_business.delete_proforma(user= request.user, proforma=qs) for qs in list(queryset)]
        except Exception as e:
            self.log_debug.info(str(e))
            self.message_user(request=request,  message=str(e), level= messages.ERROR)

    @admin.action(description="abrir proforma")
    def open_proforma(self, request: HttpRequest, queryset: QuerySet):
        try:
            [self.proforma_business.abrir_proforma(proforma=qs) for qs in list(queryset)]
        except Exception as e:
            self.log_debug.info(str(e))
            self.message_user(request=request,  message=str(e), level= messages.ERROR)
            
    @admin.action(description="Convertir a Venta Metro Lineal")
    def convertir_proforma_metro_lineal(self, request: HttpRequest, queryset: QuerySet):
        try:
            [self.proforma_business.convertir_venta_metro_lineal(proforma=qs) for qs in list(queryset)]
        except Exception as e:
            self.log_debug.info(str(e))
            self.message_user(request=request,  message=str(e), level= messages.ERROR)

    @admin.action(description="crear/actualizar nota trabajo")
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


    @admin.action(description="Imprimir")
    def print_proforma(self, request: HttpRequest, queryset: QuerySet):
        # try:
            buffer = io.BytesIO()
            pdf = PDFService(buffer= buffer)
            prodorma_detail = Proforma_Detail.objects.select_related("car_part", "window_film")
            prodorma_detail = prodorma_detail.filter( proforma_header = queryset[0])
            pdf.create_proforma(detail=prodorma_detail, header=queryset[0])
            buffer.seek(0)
            filename = f'proforma-{queryset[0].id}.pdf'
            return FileResponse(buffer, as_attachment=True, filename=filename)


    