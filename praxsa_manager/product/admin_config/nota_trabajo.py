from typing import Any
from django.http.request import HttpRequest
from django.contrib import admin
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
from django.contrib import messages
from django.db import transaction
from ..Forms.nota_trabajo import NotaTrabajoForm
from ..business.proforma import Proforma_Business
from ..business.orden_trabajo import Orden_Trabajo_Business
from ..models import Detalle_Nota_Trabajo, Nota_Venta, Proforma_Detail
from ..helper.pdf import PDFService
from django.urls import reverse
from django.utils.html import format_html
from django.http import FileResponse
import io
class ProformaDetailInLine(admin.TabularInline):
    fields = [
            # 'car_part', 
              'window_film', 
              'width', 
              'length',  
            #   'quantity',
              ]
    readonly_fields = [
            #   'car_part', 
              'window_film', 
              'width', 
              'length',  
            #   'quantity',
              ]
    model = Detalle_Nota_Trabajo
    min_num = 0
    max = 1
    extra = 0
    
class NotaTrabajoAdmin(admin.ModelAdmin):
    list_display = [ 
              'get_nota_venta_id',
              'get_entrada_vehiculo_date_format',
              'car_model',
              'car_plate',
              'instaladar',
              'get_estado'
              ]
    inlines = [
        ProformaDetailInLine,
    ]
    search_fields = ['id',
                     'instaladar__name',
                     'car_plate',
                     'car_model__name',
                     'proforma__id', 
                     'proforma__name',
                     ]
    form = NotaTrabajoForm
    orden_trabajo_busi =Orden_Trabajo_Business()
    proforma_business = Proforma_Business()
    list_per_page = 10
    actions =["print_nota_trabajo", 'create_sales_note']
    fieldsets = [('Proforma', {
                                'classes':[], 
                                "fields":['proforma', 'codigo_garantia']
                                }
                ),
                ("Cliente", {
                    'classes': [],
                    'fields': [ 'name', 'car_model','car_plate'  ]
                }),
                ('Nota',{
                    'classes':[],
                    'fields':[
                        'entrada_vehiculo',
                        'salida_vehiculo',
                        'responsable',
                        'instaladar',
                        'observaciones'
                    ]
                })

                ]
    class Media:
        js=('product/nota_trabajo.js',)
    def get_nota_venta_id(self, obj):
        # link para ver la nota de trabajo
        link = reverse("admin:product_nota_trabajo_change", args=[ obj.id])
        # pero se visualiza el id de la proforma
        return format_html('<a href="{}">{}</a>', link, obj.proforma.id)
        # return obj.proforma.id
    get_nota_venta_id.short_description = 'Nota Trabajo'
    get_nota_venta_id.admin_order_field = 'proforma__id'

    def get_estado(self, obj):
        result= Nota_Venta.objects.filter(nota_trabajo=obj)
        if len(result) > 0:
           return 'Si'
        else:
            return 'No'
    get_estado.short_description = 'Finalizado'
    
    def get_entrada_vehiculo_date_format(self, obj):
        return obj.entrada_vehiculo.strftime("%d-%m-%Y %H:%M:%S")
    get_entrada_vehiculo_date_format.short_description = 'Fecha Ingreso'
    get_entrada_vehiculo_date_format.admin_order_field = 'entrada_vehiculo'
    
    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        qs = super().get_queryset(request)
        result = self.orden_trabajo_busi.get_nota_queryset_by_role(user = request.user, qs=qs)
        if result is None:
            self.message_user(request=request,  message=str('Asigne una sucursal al usuario'), level= messages.ERROR)
            return qs.filter(sucursal = -1)
        return  result

    def has_change_permission(self, request: HttpRequest, obj=None):
        if obj is None:
            return True
        if obj.is_close == False:
            return True

    def get_readonly_fields(self, request, obj=None):
        # print ('admin obj', obj.sales_status )
        if obj is None:
            return []
        if obj.proforma is not None:
            return ['proforma', 'responsable', 'name', 'car_plate', 'car_model']           
        return []
    
    @transaction.atomic
    def delete_queryset(self, request, queryset: QuerySet):
        try:
            [self.orden_trabajo_busi.delete_work_note(work_note=qs) for qs in list(queryset)]
        except Exception as e:
            self.message_user(request=request,  message=str(e), level= messages.ERROR)
    
    
    @transaction.atomic
    @admin.action(description="crear nota venta")
    def create_sales_note(self, request: HttpRequest, queryset: QuerySet):
        try:
            [self.proforma_business.crear_nota_venta( nota_trabajo=qs, user= request.user) for qs in list(queryset)]
        except Exception as e:
            self.message_user(request=request,  message=str(e), level= messages.ERROR)
            
            
    @admin.action(description="Imprimir")
    def print_nota_trabajo(self, request: HttpRequest, queryset: QuerySet):
        # try:
            buffer = io.BytesIO()
            pdf = PDFService(buffer= buffer)
            resumen_trabajo = Detalle_Nota_Trabajo.objects.select_related("window_film", 'nota_trabajo__proforma')
            proforma = queryset[0].proforma
            detalle_proforma = Proforma_Detail.objects.filter(proforma_header=proforma).select_related('inventario')
            resumen_trabajo = resumen_trabajo.filter( nota_trabajo =  queryset[0])
            print('-----------------------------------------------')
            print(detalle_proforma)
            pdf.create_nota_trabajo(detail=resumen_trabajo, nota_trabajo= queryset[0], proforma_detail = detalle_proforma)
            buffer.seek(0)
            filename = f'Nota Trabajo-{queryset[0].proforma.id}.pdf'
            return FileResponse(buffer, as_attachment=True, filename=filename)
    