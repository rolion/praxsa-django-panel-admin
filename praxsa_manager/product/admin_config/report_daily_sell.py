"""Reporte Ventas Diaria (Django Admin, solo lectura). Las cifras salen de
`Reportes_Business` (misma implementacion que la API del panel; ver
ADR-reportes-utilidad-ventas-diarias-calculo-y-api): solo ventas cobradas, importes
del pago y de la proforma congelados al cobrar, sin costos ni utilidad."""
from datetime import datetime, time
from typing import Any

from django.contrib import admin, messages
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
from django.urls import reverse
from django.utils.html import format_html
from django_admin_listfilter_dropdown.filters import ChoiceDropdownFilter, RelatedDropdownFilter
from rangefilter.filters import DateTimeRangeFilter

from ..business.pago import Pago_Business
from ..business.reportes import Reportes_Business
from ..helper.user import User_Helper
from ..models import Proxy_Pagos


def _bs(value):
    return f'{value} Bs'


class ReportDailySellAdmin(admin.ModelAdmin):
    list_display = [
        'get_nota_venta_id',
        'created_on',
        'get_sales_type',
        'get_nota_trabajo_id',
        'get_client_name',
        'get_model',
        'tipo_pago',
        'get_venta_lamina',
        'get_instalacion',
        'get_bruto',
        'get_descuento',
        'get_cobrado',
    ]
    list_filter = [
        ('created_on', DateTimeRangeFilter),
        ('nota_venta__nota_trabajo__proforma__sucursal', RelatedDropdownFilter),
        ('nota_venta__nota_trabajo__proforma__sales_type', ChoiceDropdownFilter),
        ('tipo_pago', ChoiceDropdownFilter),
    ]
    list_per_page = 10
    reportes_business = Reportes_Business()
    pago_business = Pago_Business()
    user_helper = User_Helper()

    # -- filtro de fecha: por defecto el dia de hoy, calculado en cada request
    def get_rangefilter_created_on_title(self, request, field_path):
        return 'Pagado en'

    def get_rangefilter_created_on_default(self, request):
        hoy = datetime.now().date()
        return datetime.combine(hoy, time.min), datetime.combine(hoy, time.max)

    # -- columnas (los importes vienen del calculo compartido, ya adjuntado a cada fila)
    def _venta(self, obj):
        return getattr(obj, '_venta', None)

    @admin.display(description='Nota Venta', ordering='nota_venta__nota_trabajo__proforma__id')
    def get_nota_venta_id(self, obj):
        link = reverse('admin:product_nota_venta_change', args=[obj.nota_venta_id])
        return format_html('<a href="{}">{}</a>', link, obj.nota_venta.nota_trabajo.proforma_id)

    @admin.display(description='Tipo Venta')
    def get_sales_type(self, obj):
        return obj.nota_venta.nota_trabajo.proforma.get_sales_type_display()

    @admin.display(description='Nota Trabajo', ordering='nota_venta__nota_trabajo__id')
    def get_nota_trabajo_id(self, obj):
        link = reverse('admin:product_nota_trabajo_change', args=[obj.nota_venta.nota_trabajo_id])
        return format_html('<a href="{}">{}</a>', link, obj.nota_venta.nota_trabajo_id)

    @admin.display(description='Cliente', ordering='nota_venta__nota_trabajo__proforma__name')
    def get_client_name(self, obj):
        return obj.nota_venta.nota_trabajo.proforma.name

    @admin.display(description='Vehiculo', ordering='nota_venta__nota_trabajo__proforma__car_model_id__name')
    def get_model(self, obj):
        modelo = obj.nota_venta.nota_trabajo.proforma.car_model_id
        return modelo.name if modelo else ''

    @admin.display(description='Lamina')
    def get_venta_lamina(self, obj):
        return _bs(self._venta(obj)['venta_lamina'])

    @admin.display(description='Instalacion')
    def get_instalacion(self, obj):
        return _bs(self._venta(obj)['instalacion'])

    @admin.display(description='Bruto')
    def get_bruto(self, obj):
        return _bs(self._venta(obj)['bruto'])

    @admin.display(description='Descuento')
    def get_descuento(self, obj):
        return _bs(self._venta(obj)['descuento'])

    @admin.display(description='Cobrado')
    def get_cobrado(self, obj):
        return _bs(self._venta(obj)['cobrado'])

    # -- datos
    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        qs = self.reportes_business.pagos_cobrados(super().get_queryset(request))
        qs = qs.select_related(
            'nota_venta__nota_trabajo__proforma__car_model_id',
            'nota_venta__nota_trabajo__proforma__sucursal',
        )
        if not self.user_helper.can_view_all_sucursales(request.user) and not self.user_helper.has_assigned_sucursal(request.user):
            self.message_user(request=request, message='Asigne una sucursal al usuario', level=messages.ERROR)
            return qs.none()
        return self.pago_business.get_panel_pago_queryset(request.user, qs)

    def get_changelist_instance(self, request):
        """Adjunta el calculo a cada fila de la pagina (una sola pasada, sin N+1) y
        agrega los totales de TODO el filtro como mensaje sobre la tabla."""
        changelist = super().get_changelist_instance(request)
        pagina = list(changelist.result_list)
        calculadas = {
            venta['pago_id']: venta
            for venta in self.reportes_business.calcular_ventas(Proxy_Pagos.objects.filter(pk__in=[o.pk for o in pagina]))
        } if pagina else {}
        for obj in pagina:
            obj._venta = calculadas.get(obj.pk)
        if pagina:
            self._mostrar_totales(request, changelist.queryset)
        return changelist

    def _mostrar_totales(self, request, pagos_qs):
        resumen = self.reportes_business.resumir(self.reportes_business.calcular_ventas(pagos_qs))
        totales = resumen['totales']
        por_tipo = ' | '.join(
            f'{fila["label"]}: {fila["ventas"]} ({_bs(fila["cobrado"])})' for fila in resumen['por_tipo_venta']
        )
        self.message_user(
            request,
            f'Totales del filtro: {totales["ventas"]} ventas | Bruto {_bs(totales["bruto"])} | '
            f'Descuento {_bs(totales["descuento"])} | Cobrado {_bs(totales["cobrado"])} | {por_tipo}',
            level=messages.INFO,
        )

    # -- solo lectura
    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
