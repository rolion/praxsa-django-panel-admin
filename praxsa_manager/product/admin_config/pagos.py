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
    # readonly_fields = ('nota_venta',)
    exclude =  ['cerrado','created_by']
    actions = ['concluir_transaccion']
    list_per_page = 10
    form = PagosForm

    # def get_form(self, request, obj=None, **kwargs):
    #     form = super(PagosAdmin, self).get_form(request, obj, **kwargs)
    #     # if (request.GET):
    #         # pago_form = PagosForm(request.GET)
    #         # pago_form.is_valid()
    #         # venta = Nota_Venta.objects.select_related('nota_trabajo').get(id = pago_form.cleaned_data['nota_venta'].id)
    #         # form.base_fields['monto'].initial = venta.total_price
    #         # form.base_fields['monto'].disabled = True
    #         # print('base fieds-->>', form.base_fields)
    #     nota_venta_init = request.GET.get("nota_venta", None)
    #     kwargs['form'] = self.form  # Asegurar que se use el ModelForm
    #     form = super().get_form(request, obj, **kwargs)
    #     form.base_fields['nota_venta'].initial = nota_venta_init  # Asignar el valor inicial
    #     pago_form = PagosForm(request.GET)
    #     pago_form.is_valid()
    #     venta = Nota_Venta.objects.select_related('nota_trabajo').get(id = pago_form.cleaned_data['nota_venta'].id)
    #     form.base_fields['monto'].initial = venta.total_price
    #     form.base_fields['monto'].disabled = True
    #     return form
        # return form
    
    # def get_readonly_fields(self, request, obj=None):
    #     print('obj', obj)
    #     if obj is None:
    #         return []
    #     return ['nota_venta', ]
    # def get_changeform_initial_data(self, request):
    #     """
    #     Sobreescribe la función para obtener valores iniciales desde GET.
    #     """
    #     initial = super().get_changeform_initial_data(request)
    #     nota_venta_id = request.GET.get("nota_venta")  # Obtener el parámetro GET
    #     if nota_venta_id:
    #         nota_venta = Nota_Venta.objects.select_related('nota_trabajo').get(id = nota_venta_id)
    #         initial["nota_venta"] = nota_venta
    #         initial["monto"] = nota_venta.total_price
    #     return initial
    def get_form(self, request, obj=None, **kwargs):
        """
        Personaliza el formulario para recibir el valor de GET y pasarlo al ModelForm.
        """
        form = super().get_form(request, obj, **kwargs)
        if (request.GET):
            nota_venta_init = request.GET.get("nota_venta", None)
            kwargs['form'] = self.form  # Asegurar que se use el ModelForm
            pago_form = PagosForm(request.GET)
            pago_form.is_valid()
            venta = Nota_Venta.objects.select_related('nota_trabajo').get(id = nota_venta_init)
            form.base_fields['nota_venta'].disabled = True
            form.base_fields['monto'].initial = venta.total_price
            form.base_fields['monto'].disabled = True
        return form

    def get_form_kwargs(self, request, obj=None):
        """
        Pasar el parámetro GET al ModelForm al crearlo.
        """
        kwargs = super().get_form_kwargs(request, obj)
        if not obj:  # Solo en la creación
            print("---->>")
            kwargs.update({'nota_venta_init': request.GET.get("nota_venta", None)})
        return kwargs


    def save_model(self, request, obj, form, change):
        if not change:  # Solo establecer el valor si es un nuevo objeto
            nota_venta = request.GET.get("nota_venta", None)
           
            obj.nota_venta =  Nota_Venta.objects.select_related('nota_trabajo').get(id = nota_venta)
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
        if obj.cerrado == True:
            return False
        if user.is_superuser:
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