from typing import Any
from django.http.request import HttpRequest
from django.contrib import admin
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
from django.contrib import messages
from ..Forms.nota_trabajo import NotaTrabajoForm
from ..business.orden_trabajo import Orden_Trabajo_Business
from ..models import Detalle_Nota_Trabajo, Proforma_Detail, Proforma_Header
from ..helper.pdf import PDFService
from django.http import FileResponse
import io
class ProformaDetailInLine(admin.TabularInline):
    fields = ['car_part', 
              'window_film', 
              'width', 
              'length',  
              'quantity',]
    readonly_fields = ['car_part', 
              'window_film', 
              'width', 
              'length',  
              'quantity',]
    model = Detalle_Nota_Trabajo
    min_num = 0
    max = 1
    extra = 0
    
class NotaTrabajoAdmin(admin.ModelAdmin):
    list_display = [ 
              'id', 
              'name', 
              'car_plate', 
              'car_model']
    inlines = [
        ProformaDetailInLine,
    ]
    search_fields = ['id',
                     'car_plate',
                     'car_model__name',
                     'proforma__id', 
                     'proforma__name',]
    form = NotaTrabajoForm
    orden_trabajo_busi =Orden_Trabajo_Business()
    list_per_page = 10
    actions =["print_nota_trabajo"]
    fieldsets = [('Proforma', {
                                'classes':[], 
                                "fields":['proforma',
                                          ]
                                }
                ),
                ("Cliente", {
                    'classes': [],
                    'fields': [ 
                               'name', 'car_model','car_plate'  ]
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
        if obj.cerrada is True:
            return False
        return True

    def get_readonly_fields(self, request, obj=None):
        # print ('admin obj', obj.sales_status )
        if obj is None:
            return []
        if obj.proforma is not None:
            print('proforma is not none')
            return ['proforma', 'responsable', 'name', 'car_plate', 'car_model']           
        return []
    
    @admin.action(description="crear nota de venta")
    def delete_proforma(self, request: HttpRequest, queryset: QuerySet):
        try:
           ## [self.orden_trabajo_business.delete_proforma(user= request.user, proforma=qs) for qs in list(queryset)]
           print('todo')
        except Exception as e:
            self.message_user(request=request,  message=str(e), level= messages.ERROR)
            
            
    @admin.action(description="Imprimir")
    def print_nota_trabajo(self, request: HttpRequest, queryset: QuerySet):
        # try:
            buffer = io.BytesIO()
            pdf = PDFService(buffer= buffer)
            # queryset[0] = queryset[0].select_related('proforma')
            prodorma_detail = Proforma_Detail.objects.select_related("car_part", "window_film")
            prodorma_detail = prodorma_detail.filter( proforma_header = queryset[0].proforma)
            pdf.create_nota_trabajo(detail=prodorma_detail, header=queryset[0].proforma)
            buffer.seek(0)
            filename = f'Nota Trabajo-{queryset[0].id}.pdf'
            return FileResponse(buffer, as_attachment=True, filename=filename)
    