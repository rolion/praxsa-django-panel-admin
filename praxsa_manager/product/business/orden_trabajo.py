from decimal import Decimal
from ..helper import estados
from ..models import Proforma_Header, Proforma_Detail, Sucursal, Nota_trabajo, Detalle_Nota_Trabajo, Nota_Venta, pago
from .inventario import Inventario_Business
from ..helper.user import User_Helper
from ..utils.exception.proforma import OrdenTrabajo
from django.db import IntegrityError, transaction
from django.core.exceptions import ObjectDoesNotExist
# from datetime import datetime
from django.utils import timezone
import logging

class Orden_Trabajo_Business:

    def __init__(self) -> None:
        self.log_errors = logging.getLogger('django_admin')
        self.log_debug= logging.getLogger('debug')
        self.user_helper = User_Helper()

    def get_nota_queryset_by_role(self, user, qs):
        try:
            sucursales = Sucursal.objects.prefetch_related('empleado')
            sucursales = sucursales.filter(empleado__id = user.id, enable_to_install_windows_film = True)
            if len(sucursales) > 0:
                qs_result = qs.select_related('proforma','proforma__sucursal','instaladar', 'proforma__car_model_id__car_brand_id')
                qs_result = qs_result.filter(proforma__sucursal__id = sucursales[0].id, proforma__is_delete = False)
            else:
                qs_result = None
            return qs_result
        except Exception as e:
            print('algo salio mal, Orden_Trabajo_Business - get_nota_queryset_by_role', str(e))
            return None
        
    def get_panel_nota_queryset(self, user, qs):
        """Alcance de notas de trabajo para el panel (API `ordenes/notas-trabajo`).
        Metodo nuevo, sin tocar los legados: admin ve todas las de proformas no
        borradas; el resto, las de todas sus sucursales habilitadas; sin
        sucursal, ninguna. Ver ADR-modulo-ordenes-proforma-nota-trabajo-alcance-permisos."""
        qs = qs.filter(proforma__is_delete=False).select_related(
            'proforma', 'proforma__sucursal', 'proforma__car_model_id',
            'instaladar', 'car_model', 'car_model__car_brand_id', 'responsable', 'nota_venta',
        )
        if self.user_helper.can_view_all_sucursales(user):
            return qs
        return qs.filter(proforma__sucursal_id__in=self.user_helper.get_enabled_sucursal_ids(user))

    def get_finish_nota_queryset(self, user, qs, solo_terminadas=True):
        try:
            qs_result = qs.select_related('proforma','proforma__sucursal','instaladar', 'proforma__car_model_id','proforma__car_model_id__car_brand_id')
            qs_result = qs_result.filter(proforma__is_delete = False)
            if solo_terminadas:
                qs_result = qs_result.filter(status=estados.NT_TERMINADO)
            if self.user_helper.can_view_all_sucursales(user):
                return qs_result
            sucursales = Sucursal.objects.prefetch_related('empleado')
            sucursales = sucursales.filter(empleado__id = user.id, enable_to_install_windows_film = True)
            if len(sucursales) > 0:
                qs_result = qs_result.filter(proforma__sucursal__id = sucursales[0].id)
            else:
                qs_result = None
            return qs_result
        except Exception as e:
            print('algo salio mal, Orden_Trabajo_Business - get_finish_nota_queryset', str(e))
            return None

    @transaction.atomic   
    def delete_work_note_sumary(self, proforma):
        try:
            with transaction.atomic():
                work_note = Nota_trabajo.objects.get(proforma = proforma)
                summaries = Detalle_Nota_Trabajo.objects.filter(nota_trabajo = work_note)
                for summary in summaries:
                    summary.delete()
        except Exception as e:
            self.log_errors.error(f'no se pudo eliminar el resumen de la nota de trabajo {e}')
            pass

    def delete_work_note(self, work_note: Nota_trabajo ):
        try:
            with transaction.atomic():
                nota_venta = Nota_Venta.objects.filter(nota_trabajo = work_note).first()
                if nota_venta is not None and (nota_venta.status == estados.NV_PAGADA or pago.objects.filter(nota_venta=nota_venta).exists()):
                    raise OrdenTrabajo(f'No se puede eliminar la nota de trabajo, porque su nota de venta Nro. {nota_venta.id} ya está pagada')
                if work_note.status == estados.NT_TERMINADO:
                    raise OrdenTrabajo('No se puede eliminar una nota de trabajo terminada; corrija el trabajo (vuelva a En proceso) antes de eliminarla')
                summaries = Detalle_Nota_Trabajo.objects.filter(nota_trabajo = work_note)
                for summary in summaries:
                    summary.delete()
                proforma = work_note.proforma

                # Si la nota estaba cancelada, el inventario ya se devolvio y detalle.inventario es None.
                if work_note.status != estados.NT_CANCELADA:
                    for detalle in Proforma_Detail.objects.filter(proforma_header = proforma):
                        Inventario_Business().return_detail_to_inventory(detalle)
                        if detalle.inventario_id is not None:
                            detalle.inventario = None
                            detalle.save(update_fields=['inventario'])
                if nota_venta is not None:
                    nota_venta.delete()
                work_note.delete()
                # Import diferido: orden_estado.py importa este modulo (Orden_Trabajo_Business),
                # un import a nivel de modulo aca crearia un ciclo.
                from .orden_estado import Orden_Estado_Business
                # work_note.delete() no limpia el cache en memoria de proforma.nota_trabajo
                # (quedaria apuntando al registro ya borrado); refresh_from_db lo fuerza a
                # recalcularse contra la base antes de recomputar el estado.
                proforma.refresh_from_db()
                Orden_Estado_Business().refrescar(proforma)

        except OrdenTrabajo as e:
            raise e
        except Exception as e:
            self.log_errors.error(f'contactar administrado {e}')
            raise OrdenTrabajo('contactar administrado')
    @transaction.atomic 
    def create_work_note(self, proforma, sumary, responsable):
        try:
            with transaction.atomic():
                nota_trabajo = Nota_trabajo.objects.get(proforma = proforma)
                old_sumary = Detalle_Nota_Trabajo.objects.filter(nota_trabajo = nota_trabajo)
                for item in old_sumary:
                    item.delete()
        except ObjectDoesNotExist  as e:
            nota_trabajo = Nota_trabajo()
            nota_trabajo.entrada_vehiculo = timezone.now()
        except Exception as e:
            self.log_errors.error(f'no se pudo crear la nota de trabajo {e}')
            return None
        nota_trabajo.proforma = proforma
        nota_trabajo.name = proforma.name
        nota_trabajo.car_model = proforma.car_model_id
        nota_trabajo.car_plate = proforma.car_plate
        nota_trabajo.responsable = responsable
        nota_trabajo.save()
        for sumary_item in sumary:
            detalle_nota_trabajo = Detalle_Nota_Trabajo()
            detalle_nota_trabajo.nota_trabajo = nota_trabajo
            detalle_nota_trabajo.window_film = sumary_item["window_film"]
            detalle_nota_trabajo.width = sumary_item["width"]
            detalle_nota_trabajo.length = sumary_item["length"]
            detalle_nota_trabajo.save()
        return nota_trabajo
