"""Reporte Utilidades (Django Admin, solo lectura): una fila por lote de inventario
con lo vendido, su costo de compra y la utilidad (venta de lamina - costo, antes de
descuento), acumulado de todas las ventas cobradas. Las cifras salen de
`Reportes_Business` (misma implementacion que la API del panel; ver
ADR-reportes-utilidad-ventas-diarias-calculo-y-api). El detalle por periodo, con y
sin descuento, esta en el panel."""
from typing import Any

from django.contrib import admin, messages
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
from django_admin_listfilter_dropdown.filters import RelatedDropdownFilter

from ..business.inventario import Inventario_Business
from ..business.reportes import Reportes_Business
from ..helper.user import User_Helper


def _bs(value):
    return f'{value} Bs'


class ReportUtilidadAdmin(admin.ModelAdmin):
    list_display = [
        'sucursal',
        'bobina',
        'precio_compra_mtr_lineal',
        'precio_venta_mtr_lineal',
        'get_metros',
        'get_venta',
        'get_costo',
        'get_utilidad',
    ]
    list_filter = [
        ('sucursal', RelatedDropdownFilter),
        ('bobina', RelatedDropdownFilter),
    ]
    list_per_page = 10
    reportes_business = Reportes_Business()
    inventario_business = Inventario_Business()
    user_helper = User_Helper()

    def _lote(self, obj):
        return getattr(obj, '_lote', None)

    @admin.display(description='Metros vendidos')
    def get_metros(self, obj):
        return self._lote(obj)['metros']

    @admin.display(description='Venta Lamina')
    def get_venta(self, obj):
        return _bs(self._lote(obj)['venta_lamina'])

    @admin.display(description='Costo Compra')
    def get_costo(self, obj):
        lote = self._lote(obj)
        aviso = ' (costo incompleto)' if lote['costo_incompleto'] else ''
        return _bs(lote['costo_compra']) + aviso

    @admin.display(description='Utilidad Lamina')
    def get_utilidad(self, obj):
        return _bs(self._lote(obj)['utilidad_antes'])

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        base_qs = super().get_queryset(request)
        if not self.user_helper.can_view_all_sucursales(request.user) and not self.user_helper.has_assigned_sucursal(request.user):
            self.message_user(request=request, message='Asigne una sucursal al usuario', level=messages.ERROR)
            return base_qs.none()
        base_qs = self.inventario_business.get_panel_inventario_queryset(request.user, base_qs)
        return self.reportes_business.lotes_con_ventas(base_qs).select_related('sucursal', 'bobina', 'bobina__window_film')

    def get_changelist_instance(self, request):
        """Adjunta a cada lote de la pagina lo vendido y su costo (una sola pasada) y agrega
        el total de TODO el filtro como mensaje sobre la tabla."""
        changelist = super().get_changelist_instance(request)
        pagina = list(changelist.result_list)
        if pagina:
            calculado = self.reportes_business.calcular_por_lote([obj.pk for obj in pagina])
            for obj in pagina:
                obj._lote = calculado[obj.pk]
            todos = self.reportes_business.calcular_por_lote(list(changelist.queryset.values_list('pk', flat=True)))
            venta = sum(fila['venta_lamina'] for fila in todos.values())
            costo = sum(fila['costo_compra'] for fila in todos.values())
            self.message_user(
                request,
                f'Totales del filtro: Venta lamina {_bs(venta)} | Costo de compra {_bs(costo)} | '
                f'Utilidad lamina {_bs(venta - costo)}',
                level=messages.INFO,
            )
        return changelist

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
