from urllib.parse import urlencode

from django.shortcuts import redirect
from ..Forms.pagos import PagosForm
from typing import Any
from django.contrib import admin
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
from ..business.pago import Pago_Business
from ..business.orden_estado import Orden_Estado_Business
from django.contrib import messages
from django_admin_listfilter_dropdown.filters import DropdownFilter, RelatedDropdownFilter, ChoiceDropdownFilter
from rangefilter.filters import (
    DateRangeFilterBuilder,
    DateTimeRangeFilterBuilder,
    NumericRangeFilterBuilder,
    DateRangeQuickSelectListFilterBuilder,
)
from datetime import datetime
from ..models import Nota_Venta
class PagosAdmin(admin.ModelAdmin):
    list_display = ['nota_venta', 
                    'view_proforma_sucursal',
                    'view_proforma_monto',
                    'view_created_on',
                    'registro_contable',
                    'tipo_pago']
    # readonly_fields = ('nota_venta','monto')
    exclude =  ['cerrado','created_by']
    list_filter = [
      ('created_on', 
        DateTimeRangeFilterBuilder(
            title="Fecha Pago",
            default_start=datetime(2020, 1, 1),
            default_end=datetime(2030, 1, 1),
      ),),
    # ('instaladar', RelatedDropdownFilter),
    ('nota_venta__nota_trabajo__proforma__sucursal', RelatedDropdownFilter),
    ]
    actions = ['concluir_transaccion']
    list_per_page = 10
    form = PagosForm
    pago_business = Pago_Business()
    estado_business = Orden_Estado_Business()

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
        if request.method == 'POST':
            nota_venta_init = request.GET.get("nota_venta", None)
            nota_venta_init = request.POST.get('nota_venta', nota_venta_init)
            if nota_venta_init is not None:
                form.base_fields['nota_venta'].initial = nota_venta_init
        return form
    
    def add_view(self, request, form_url='', extra_context=None):
        """
        Agrega el parámetro al contexto en la vista de creación.
        """
        extra_context = extra_context or {}
        extra_context['nota_venta'] = request.GET.get('nota_venta', '') or request.POST.get('nota_venta', '')
        return super().add_view(request, form_url, extra_context)
    
    def get_readonly_fields(self, request, obj=None):
        if not obj:
            return []
        return ('nota_venta','monto')

    def get_form_kwargs(self, request, obj=None):
        """
        Pasar el parámetro GET al ModelForm al crearlo.
        """
        kwargs = super().get_form_kwargs(request, obj)
        if not obj:  # Solo en la creación
            kwargs.update({'nota_venta_init': request.GET.get("nota_venta", None) or request.POST.get('nota_venta', None)})
        return kwargs


    def save_model(self, request, obj, form, change):
        if not change:  # Solo establecer el valor si es un nuevo objeto
            nota_venta = request.GET.get("nota_venta", None)
           
            obj.nota_venta =  Nota_Venta.objects.select_related('nota_trabajo').get(id = nota_venta)
            # El servicio valida (nota de trabajo terminada, nota de venta por cobrar),
            # fija el monto y marca la nota de venta como pagada.
            self.estado_business.registrar_pago_instancia(obj, request.user)
            return
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        self.estado_business.anular_pago(obj)

    def delete_queryset(self, request, queryset):
        try:
            [self.estado_business.anular_pago(qs) for qs in list(queryset)]
        except Exception as e:
            self.message_user(request=request,  message=str(e), level= messages.ERROR)
        
    @admin.display(empty_value="", description='Sucursal' )
    def view_proforma_sucursal(self, obj):
        if obj is None:
             return ''
        if obj.nota_venta.nota_trabajo.proforma.sucursal is None:
             return ''
        return obj.nota_venta.nota_trabajo.proforma.sucursal.name

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
        # user = request.user
        # if user.is_superuser:
        #     return True
        if obj.cerrado == True:
            return False
        
        return True


    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        qs = super().get_queryset(request)
        qs = qs.select_related('nota_venta',
                                   'nota_venta__nota_trabajo',
                                   'nota_venta__nota_trabajo__proforma',
                                   'nota_venta__nota_trabajo__proforma__sucursal'
                                   )
        result = self.pago_business.get_pago_queryset_by_role(user = request.user, qs=qs)
        if result is None:
            self.message_user(request=request,  message=str('Asigne una sucursal al usuario'), level= messages.ERROR)
            return qs.filter(nota_venta__nota_trabajo__proforma__sucursal = -1)
        return  result
    
    @admin.action(description="concluir transaccion")
    def concluir_transaccion(self, request: HttpRequest, queryset: QuerySet):
        try:
            pb = Pago_Business()

            [pb.cerrar_pago(qs) for qs in list(queryset)]
            
        except Exception as e:
            self.message_user(request=request,  message=str(e), level= messages.ERROR)