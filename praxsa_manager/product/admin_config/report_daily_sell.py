from typing import Any
from django.http.request import HttpRequest
from django.contrib import admin
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
from django.contrib import messages
from django.db import transaction

from product.Forms.pagos import PagosForm
from product.Forms.nota_venta_form import NotaVentaForm
from product.business.user import User_Business
from product.helper.proforma import Proforma_Helper
from product.helper.user import User_Helper
# from ..Forms.daily_sales_form import NotaVentaForm
from ..business.proforma import Proforma_Business
from ..business.orden_trabajo import Orden_Trabajo_Business
from ..business.pago import Pago_Business
from ..models import Detalle_Nota_Trabajo, Nota_Venta, Proforma_Detail
from ..helper.pdf import PDFService
from django.urls import reverse
from django.utils.html import format_html
from django.http import FileResponse
import io
from datetime import datetime
from django.db.models import Count, Sum
from django.core import serializers
import functools

import json
from django.core.serializers.json import DjangoJSONEncoder

from django_admin_listfilter_dropdown.filters import DropdownFilter, RelatedDropdownFilter, ChoiceDropdownFilter
from rangefilter.filters import (
    DateRangeFilterBuilder,
    DateTimeRangeFilterBuilder,
    NumericRangeFilterBuilder,
    DateRangeQuickSelectListFilterBuilder,
)
    
class ReportDailySellAdmin(admin.ModelAdmin):
    list_display = [
                    'get_nota_venta_id',
                    'get_sales_type',
                    'get_nota_trabajo_id',
                    "get_client_name",
                    "get_model",
                    "get_costo_instalacion",
                    "get_sub_total",
                    "get_dicount",
                    'get_total_pagar',
                    ]
    list_filter = [
        ('nota_venta__nota_trabajo__proforma__sucursal', ChoiceDropdownFilter),
        ('created_on', 
         DateTimeRangeFilterBuilder(
                title="Pagado en",
                default_start=datetime.now(),
                default_end=datetime.now(),
            ),),
        ('nota_venta__nota_trabajo__proforma__sucursal', RelatedDropdownFilter),]
    
    actions =[]
    form = PagosForm
    list_per_page = 10
    proforma_business = Proforma_Business()
    user_business = User_Business()
    user_helper = User_Helper()
    proforma_helper = Proforma_Helper()
    pago_business = Pago_Business()

    def get_sales_type(self, obj):
        # link para ver la nota de trabajo
        # pero se visualiza el id de la proforma
        return obj.nota_venta.nota_trabajo.proforma.sales_type
    get_sales_type.short_description = 'Tipo Venta'
    
    def get_nota_venta_id(self, obj):
        # link para ver la nota de trabajo
        link = reverse("admin:product_nota_venta_change", args=[ obj.nota_venta.id])
        # pero se visualiza el id de la proforma
        return format_html('<a href="{}">{}</a>', link, obj.nota_venta.nota_trabajo.proforma.id)
    get_nota_venta_id.short_description = 'Nota Venta'
    get_nota_venta_id.admin_order_field = 'nota_venta__nota_trabajo__proforma__id'

    def get_nota_trabajo_id(self, obj):
        # link para ver la nota de trabajo
        link = reverse("admin:product_nota_trabajo_change", args=[ obj.nota_venta.nota_trabajo.id])
        # pero se visualiza el id de la proforma
        return format_html('<a href="{}">{}</a>', link, obj.nota_venta.nota_trabajo.id)
    get_nota_trabajo_id.short_description = 'Nota Trabajo'
    get_nota_trabajo_id.admin_order_field = 'nota_venta__nota_trabajo__id'

    def get_sub_total(self, obj):
        proforma = obj.nota_venta.nota_trabajo.proforma
        total = proforma.total_price
        return f'{total}Bs'
    get_sub_total.short_description = 'Sub Total'
    get_sub_total.admin_order_field = 'nota_venta__nota_trabajo__proform__total_price'
    
    def get_total_pagar(self, obj):
        proforma = obj.nota_venta.nota_trabajo.proforma
        total = proforma.total_price - proforma.discount
        return f'{total}Bs'
    get_total_pagar.short_description = 'Total Pagar'
    get_total_pagar.admin_order_field = 'nota_venta__nota_trabajo__proforma__total_price'
    
    def get_costo_instalacion(self, obj):
        items = list(obj.nota_venta.nota_trabajo.proforma.items.all())
        costos = [item.installation_price * item.quantity for item in items]
        costo_instalacion = functools.reduce(lambda acc, current: acc+current, costos )
        return f'{costo_instalacion}Bs'
    
    get_costo_instalacion.short_description = 'Costo Instalacion'
    #get_costo_instalacion.admin_order_field = 'costo_instalacion'
    
    def get_dicount(self, obj):
        dicount = obj.nota_venta.nota_trabajo.proforma.discount
        return f'{dicount}Bs'
    
    get_dicount.short_description = 'Descuento'
    get_dicount.admin_order_field = 'nota_venta__nota_trabajo__proforma__discount'
    
    def get_client_name(self, obj):
        name = obj.nota_venta.nota_trabajo.proforma.name
        return f'{name}'
    
    get_client_name.short_description = 'Cliente'
    get_client_name.admin_order_field = 'nota_venta__nota_trabajo__proforma__name'
    
    def get_model(self, obj):
        name = obj.nota_venta.nota_trabajo.proforma.car_model_id.name if obj.nota_venta.nota_trabajo.proforma.car_model_id else ""
        return f'{name}'
    
    get_model.short_description = 'Vehiculo'
    get_model.admin_order_field = 'nota_venta__nota_trabajo__proforma__car_model_id__name'
    
    
    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        qs = super().get_queryset(request)
        qs = qs.prefetch_related("nota_venta__nota_trabajo","nota_venta__nota_trabajo__proforma", "nota_venta__nota_trabajo__proforma__items")
        qs = qs.select_related("nota_venta__nota_trabajo__proforma__car_model_id", "nota_venta__nota_trabajo__proforma__sucursal")
        result = self.pago_business.get_pago_queryset_by_role(user = request.user, qs=qs)
        if result is None:
            self.message_user(request=request,  message=str('Asigne una sucursal al usuario'), level= messages.ERROR)
            return qs.filter(nota_venta__nota_trabajo__proforma__sucursal = -1)
        return  result
    
    def has_add_permission(self, request, obj=None):
        return False
    
    def has_change_permission(self, request: HttpRequest, obj: Any | None = ...) -> bool:
        return False
    
    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions