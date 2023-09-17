from ..Forms.pagos import PagosForm
from typing import Any
from django.contrib import admin
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
from ..business.pago import Pago_Business
from django.contrib import messages
class PagosAdmin(admin.ModelAdmin):
    list_display = ['proforma', 
                    'view_proforma_monto',
                    'view_created_on',
                    'tipo_pago']
    exclude =  ['cerrado','created_by']
    actions = ['concluir_transaccion']
    list_per_page = 10
    form = PagosForm

    @admin.display(empty_value="0", description='Monto' )
    def view_proforma_monto(self, obj):
        if obj is None:
             return ''
        if obj.proforma is None:
             return ''
        return obj.proforma.total_price
    @admin.display(empty_value="0", description='Fecha' )
    def view_created_on(self, obj):
        if obj is None:
             return ''
        return obj.created_on.strftime("%d-%m-%Y %H:%M:%S")
    

    def has_change_permission(self, request: HttpRequest, obj=None):
        if obj is None:
            return True
        return not obj.cerrado


    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        qs = super().get_queryset(request)
        result = qs.select_related('proforma')
        return  result
    
    @admin.action(description="concluir transaccion")
    def concluir_transaccion(self, request: HttpRequest, queryset: QuerySet):
        try:
            pb = Pago_Business()
            [pb.cerrar_pago(qs) for qs in list(queryset)]
            
        except Exception as e:
            self.message_user(request=request,  message=str(e), level= messages.ERROR)