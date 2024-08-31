from ..Forms.pagos import PagosForm
from typing import Any
from django.contrib import admin
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
from ..business.pago import Pago_Business
from django.contrib import messages
from datetime import datetime
from ..models import Nota_Venta
class PagosAdmin(admin.ModelAdmin):
    list_display = ['nota_venta', 
                    'view_proforma_monto',
                    'view_created_on',
                    'tipo_pago']
    exclude =  ['cerrado','created_by']
    actions = ['concluir_transaccion']
    list_per_page = 10
    form = PagosForm

    def get_form(self, request, obj=None, **kwargs):
        form = super(PagosAdmin, self).get_form(request, obj, **kwargs)
        if (request.GET):
            pago_form = PagosForm(request.GET)
            pago_form.is_valid()
            venta = Nota_Venta.objects.select_related('nota_trabajo').get(id = pago_form.cleaned_data['nota_venta'].id)
            form.base_fields['monto'].initial = venta.total_price
            form.base_fields['monto'].disabled = True
        return form
    
    # def get_readonly_fields(self, request, obj=None):
    #     print('obj', obj)
    #     if obj is None:
    #         return []
    #     return ['monto', ]

    def save_model(self, request, obj, form, change):
        obj.created_by = request.user
        obj.created_on = datetime.now()
        obj.cerrado = True
        super().save_model(request, obj, form, change)

    @admin.display(empty_value="0", description='Monto' )
    def view_proforma_monto(self, obj):
        if obj is None:
             return ''
        if obj.nota_venta.nota_trabajo.proforma is None:
             return ''
        return obj.nota_venta.total_price
    @admin.display(empty_value="0", description='Fecha' )
    def view_created_on(self, obj):
        if obj is None:
             return ''
        return obj.created_on.strftime("%d-%m-%Y %H:%M:%S")
    

    def has_change_permission(self, request: HttpRequest, obj=None):
        if obj is None:
            return True
        user = request.user
        if  user.groups.filter(name='Admin').exists() or user.is_superuser:
            return True
        return False


    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        qs = super().get_queryset(request)
        result = qs.select_related('nota_venta',
                                   'nota_venta__nota_trabajo',
                                   'nota_venta__nota_trabajo__proforma')
        return  result
    
    @admin.action(description="concluir transaccion")
    def concluir_transaccion(self, request: HttpRequest, queryset: QuerySet):
        try:
            pb = Pago_Business()

            [pb.cerrar_pago(qs) for qs in list(queryset)]
            
        except Exception as e:
            self.message_user(request=request,  message=str(e), level= messages.ERROR)