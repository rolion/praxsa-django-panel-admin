from ..models import pago, Proforma_Header, Nota_trabajo, Sucursal
from django.db import IntegrityError, transaction
from ..helper.user import User_Helper
from .orden_estado import Orden_Estado_Business
import logging

class Pago_Business:

    def __init__(self) -> None:
        self.user_helper = User_Helper()
        self.estado_business = Orden_Estado_Business()
        self.log_errors = logging.getLogger('django_admin')

    def get_panel_nota_venta_queryset(self, user, qs):
        """Alcance de notas de venta para el panel (API `ordenes/notas-venta`):
        las no borradas de las sucursales asignadas al usuario (activas o no,
        alcance de lectura); solo el superusuario ve todas; sin sucursal,
        ninguna (ADR-inventario-alcance-sucursal-django-admin-alcance-lectura-
        escritura)."""
        qs = qs.filter(nota_trabajo__proforma__is_delete=False).select_related(
            'nota_trabajo', 'nota_trabajo__proforma', 'nota_trabajo__proforma__sucursal', 'pago'
        ).order_by('-id')
        if self.user_helper.can_view_all_sucursales(user):
            return qs
        return qs.filter(nota_trabajo__proforma__sucursal_id__in=self.user_helper.get_readable_sucursal_ids(user))

    def get_panel_pago_queryset(self, user, qs):
        """Alcance de pagos para los reportes (panel y Django Admin): los de las
        sucursales asignadas al usuario; solo el superusuario ve todos; sin
        sucursal, ninguno (qs.none(), no None)."""
        if self.user_helper.can_view_all_sucursales(user):
            return qs
        return qs.filter(nota_venta__nota_trabajo__proforma__sucursal_id__in=self.user_helper.get_readable_sucursal_ids(user))

    def get_pago_queryset_by_role(self, user, qs):
        """Legado del Django Admin: delega en el alcance del panel. Conserva el
        contrato de devolver None cuando el usuario no tiene sucursal, que los
        ModelAdmin usan para mostrar "Asigne una sucursal al usuario"."""
        if not self.user_helper.can_view_all_sucursales(user) and not self.user_helper.has_assigned_sucursal(user):
            return None
        return self.get_panel_pago_queryset(user, qs)

    def cerrar_pago(self, paiment: pago):
        # Cierre contable: solo el flag; los estados los gobierna Orden_Estado_Business.
        return self.estado_business.cerrar_pago(paiment)
