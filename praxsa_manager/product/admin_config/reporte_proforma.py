from typing import Any
from django.http.request import HttpRequest
from django.contrib import admin
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
from django.contrib import messages
from django.db import transaction

from ..Forms.Sale_header import SaleHeaderForm
from ..Forms.nota_trabajo import NotaTrabajoForm
from ..business.proforma import Proforma_Business
from ..business.orden_trabajo import Orden_Trabajo_Business
from ..models import Detalle_Nota_Trabajo, Nota_Venta
from ..helper.pdf import PDFService
from django.urls import reverse
from django.utils.html import format_html
from django.http import FileResponse
import io
from datetime import datetime
from django_admin_listfilter_dropdown.filters import DropdownFilter, RelatedDropdownFilter, ChoiceDropdownFilter
from rangefilter.filters import (
    DateRangeFilterBuilder,
    DateTimeRangeFilterBuilder,
    NumericRangeFilterBuilder,
    DateRangeQuickSelectListFilterBuilder,
)
    
class ReportProformaAdmin(admin.ModelAdmin):
    list_display = [
                    'get_proforma_id',
                    'get_created_on_date_format',
                    'name', 
                    'car_model_id',
                    'car_plate',
                    'get_total_pagar',
                    'sucursal',
                    'sales_type',
                    'origen',
                    'created_by'
            #   'get_estado'
              ]
    list_filter = [
        ('sales_type', ChoiceDropdownFilter),
        ('sucursal', RelatedDropdownFilter),
        ('proforma_created_on', 
         DateTimeRangeFilterBuilder(
                title="Creado en",
                default_start=datetime(2020, 1, 1),
                default_end=datetime(2030, 1, 1),
            ),),]
    search_fields = ["id", 'sales_type', 'proforma_created_on', 'name', 'email', 'car_model_id__name', 'car_plate',]
    form = SaleHeaderForm
    orden_trabajo_busi =Orden_Trabajo_Business()
    proforma_business = Proforma_Business()
    list_per_page = 10
    # actions =["print_nota_trabajo", 'create_sales_note']
    
    def get_proforma_id(self, obj):
        # link para ver la nota de trabajo
        link = reverse("admin:product_proforma_header_change", args=[ obj.id])
        # pero se visualiza el id de la proforma
        return format_html('<a href="{}">{}</a>', link, obj.id)
    get_proforma_id.short_description = 'Proforma'
    get_proforma_id.admin_order_field = 'id'

    def get_sucursal(self, obj):
        return obj.proforma.sucursal.name
    get_sucursal.short_description = 'Sucursal'
    get_sucursal.admin_order_field = 'proforma__sucursal__name'
    
    
    def get_total_pagar(self, obj):
        return obj.total_price - obj.discount
    get_total_pagar.short_description = 'Total Pagar'
    get_total_pagar.admin_order_field = 'proforma__car_model_id__name'

    def get_tipo_venta(self, obj):
        return obj.proforma.sales_type.replace('_', ' ').title()
    get_tipo_venta.short_description = 'Tipo de venta'
    get_tipo_venta.admin_order_field = 'proforma__sales_type'


    def get_estado(self, obj):
        result= Nota_Venta.objects.filter(nota_trabajo=obj)
        if len(result) > 0:
           return 'Si'
        else:
            return 'No'
    get_estado.short_description = 'Finalizado'
    
    def get_created_on_date_format(self, obj):
        return obj.proforma_created_on.strftime("%d-%m-%Y %H:%M:%S")
    get_created_on_date_format.short_description = 'Creado en'
    get_created_on_date_format.admin_order_field = 'proforma_created_on'
    
    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        qs = super().get_queryset(request)
        result = self.proforma_business.get_proforma_queryset_by_role(user = request.user, qs=qs)
        if result is None:
            self.message_user(request=request,  message=str('Asigne una sucursal al usuario'), level= messages.ERROR)
            return qs.filter(sucursal = -1)
        return  result

    def has_change_permission(self, request: HttpRequest, obj=None):
        # if obj is None:
        #     return True
        # if obj.is_close == False:
        #     return True
        return False

    def get_readonly_fields(self, request, obj=None):
        # print ('admin obj', obj.sales_status )
        if obj is None:
            return []
        if obj.is_close == True:
            return '__all__'
                    
        return ['sucursal', ]
    
    @transaction.atomic
    def delete_queryset(self, request, queryset: QuerySet):
        try:
            # [self.orden_trabajo_busi.delete_work_note(work_note=qs) for qs in list(queryset)]
            pass
        except Exception as e:
            self.message_user(request=request,  message=str(e), level= messages.ERROR)
            
            
    @admin.action(description="Imprimir")
    def print_nota_trabajo(self, request: HttpRequest, queryset: QuerySet):
        # try:
            buffer = io.BytesIO()
            pdf = PDFService(buffer= buffer)
            resumen_trabajo = Detalle_Nota_Trabajo.objects.select_related("window_film", 'nota_trabajo__proforma')
            proforma = queryset[0].proforma
            resumen_trabajo = resumen_trabajo.filter( nota_trabajo =  queryset[0])
            pdf.create_nota_trabajo(detail=resumen_trabajo, nota_trabajo= queryset[0])
            buffer.seek(0)
            filename = f'Nota Trabajo-{queryset[0].id}.pdf'
            return FileResponse(buffer, as_attachment=True, filename=filename)
    