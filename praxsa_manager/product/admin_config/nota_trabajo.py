from django.http.request import HttpRequest
from django.contrib import admin
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
from django.contrib import messages
from ..Forms.nota_trabajo import NotaTrabajoForm
from ..models import Detalle_Nota_Trabajo
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
    form = NotaTrabajoForm
    list_per_page = 10
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
    