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
        """Alcance de notas de venta para el panel (API `ordenes/notas-venta`),
        mismo criterio que proformas/notas de trabajo: admin ve todas las no
        borradas; el resto, las de todas sus sucursales habilitadas; sin
        sucursal, ninguna (ADR-...-alcance-permisos)."""
        qs = qs.filter(nota_trabajo__proforma__is_delete=False).select_related(
            'nota_trabajo', 'nota_trabajo__proforma', 'nota_trabajo__proforma__sucursal', 'pago'
        ).order_by('-id')
        if self.user_helper.can_view_all_sucursales(user):
            return qs
        return qs.filter(nota_trabajo__proforma__sucursal_id__in=self.user_helper.get_enabled_sucursal_ids(user))

    def get_pago_queryset_by_role(self, user, qs):
        try:
            if self.user_helper.can_view_all_sucursales(user):
                return qs
            sucursales = Sucursal.objects.prefetch_related('empleado')
            sucursales = sucursales.filter(empleado__id = user.id, enable_to_install_windows_film = True)
            if len(sucursales) > 0:
                qs_result = qs.filter(nota_venta__nota_trabajo__proforma__sucursal__id = sucursales[0].id)
            else:
                qs_result = None
            return qs_result
        except Exception as e:
            self.log_errors.error(f'algo salio mal, Pago_Business - get_pago_queryset_by_role {e}')
            return None

    def cerrar_pago(self, paiment: pago):
        # Cierre contable: solo el flag; los estados los gobierna Orden_Estado_Business.
        return self.estado_business.cerrar_pago(paiment)
