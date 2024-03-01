from ..models import Proforma_Header, Proforma_Detail, Sucursal, Nota_trabajo, Detalle_Nota_Trabajo
from .inventario import Inventario_Business
from django.db import IntegrityError, transaction
from django.core.exceptions import ObjectDoesNotExist
from datetime import datetime
class Orden_Trabajo_Business:


    def get_nota_queryset_by_role(self, user, qs):
        try:
            sucursales = Sucursal.objects.prefetch_related('empleado')
            sucursales = sucursales.filter(empleado__id = user.id, enable_to_install_windows_film = True)
            if len(sucursales) > 0:
                qs_result = qs.select_related('proforma','proforma__sucursal', 'proforma__car_model_id__car_brand_id')
                qs_result = qs_result.filter(proforma__sucursal__id = sucursales[0].id, proforma__is_delete = False)
            else:
                qs_result = None
            return qs_result
        except Exception as e:
            print('algo salio mal, Orden_Trabajo_Business - get_nota_queryset_by_role', str(e))
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
            pass
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
            nota_trabajo.entrada_vehiculo = datetime.now()
        except Exception as e:
            print(e)
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
