from typing import Union
from ..models import Car_Model_Part, Proforma_Header, Sucursal, Proforma_Detail, Nota_trabajo, Detalle_Nota_Trabajo, pago, Nota_Venta
from ..helper.proforma import Proforma_Helper
from ..helper.user import User_Helper
from .inventario import Inventario_Business
from ..utils.exception.nohaylaminas import NoHayLaminasDisponibles
from ..utils.exception.proforma import ProformaException, NotaVentaException
from django.db import IntegrityError, transaction
from django.db.models import Sum
from datetime import datetime
from ..business.orden_trabajo import Orden_Trabajo_Business
from .orden_estado import Orden_Estado_Business
from decimal import *
from ..helper.proforma import Proforma_Helper
import logging

class Proforma_Business:

    def __init__(self) -> None:
        self.helper = Proforma_Helper()
        self.inv_bussiness = Inventario_Business()
        self.orden_trabajo_bussiness = Orden_Trabajo_Business()
        self.estado_business = Orden_Estado_Business()
        self.user_helper = User_Helper()
        self.log_errors = logging.getLogger('django_admin')
        self.log_debug= logging.getLogger('debug')
        self.helper = Proforma_Helper()

    def get_proforma_by_id(self, id):
        return Proforma_Header.objects.get(pk = id)

    def refresh_status(self, proforma):
        # Delegador: el estado global lo calcula Orden_Estado_Business (ADR maquina-de-estados).
        return self.estado_business.refrescar(proforma)


    
    def abrir_proforma(self, proforma):
        """Reabrir == anular la nota de trabajo (ADR: anular NT equivale a reabrir)."""
        nota = Nota_trabajo.objects.filter(proforma=proforma).first()
        if nota is None:
            raise Exception(f'la proforma {proforma.id} no tiene nota de trabajo')
        self.estado_business.anular_nota_trabajo(nota)
        return proforma

    
    def validate_proforma_detail(self, proforma_details:list[Proforma_Detail]):
        for detalle in proforma_details:
            width= detalle.width
            proforma_header= detalle.proforma_header
            car_model = proforma_header.car_model_id
            car_part = detalle.car_part
            car_part_item = Car_Model_Part.objects.select_related('car_part_id').get(car_part_id = car_part, car_model_id = car_model)
            if width < car_part_item.width:
                raise ProformaException(f'En la proforma {proforma_header.id}, el item {car_part.name} tiene un ancho de {car_part_item.width}, seleccione un acho de lamina mayor a igual a {car_part_item.width}')

        return True
    
    def create_work_note(self, proforma, responsable):
        # Delegador: aprobar la proforma (descuenta inventario, crea nota de trabajo y nota de venta).
        return self.estado_business.aprobar_proforma(proforma=proforma, responsable=responsable)

        
    
    @transaction.atomic
    def convertir_venta_metro_lineal(self, proforma: Proforma_Header):
        if proforma.is_close == True:
            raise Exception(f'la proforma {proforma.id}, ya esta cerrada!')
        if proforma.sales_type == self.helper.tipo_venta_metro_lineal:
            raise Exception(f'la proforma {proforma.id} ya es de tipo venta por metro lineal')
        
        detalles = Proforma_Detail.objects.filter(proforma_header = proforma)
        if len(detalles) == 0:
            raise Exception(f'la proforma {proforma.id} no tiene detalle')
        
        sumary = []
        total = Decimal('0.0')
        try: 
            with transaction.atomic():
                for detalle in list(detalles):
                    item_index = next((i for i, item in enumerate(sumary) 
                                                        if item.window_film == detalle.window_film and item.width == detalle.width ), 
                                                        None)
                    if item_index is not None:
                        item =sumary[item_index]
                        item.length = item.length + detalle.length
                        item.sub_total = item.length * item.window_film_price * item.quantity
                        
                    else:
                        new_detalle = Proforma_Detail()
                        new_detalle.proforma_header = proforma
                        new_detalle.width = detalle.width
                        new_detalle.sub_total = 0
                        new_detalle.window_film = detalle.window_film
                        new_detalle.length = detalle.length
                        new_detalle.quantity = detalle.quantity
                        new_detalle.window_film_price = detalle.window_film_price
                        new_detalle.sub_total = new_detalle.length * new_detalle.window_film_price * new_detalle.quantity
                        
                        sumary.append(new_detalle)
                    detalle.delete()
                for new_item in list(sumary):
                    total = total + new_item.sub_total
                    new_item.save()
                proforma.sales_type = self.helper.tipo_venta_metro_lineal
                proforma.total_price = total
                proforma.save()
        except Exception as e:
            self.log_errors.error(f'algo salio mal, contactar administrador {e}')
            raise Exception('algo salio mal, contactar administrador')

    def recalculate_total_price(self, proforma):
        """Recalcula Proforma_Header.total_price como la suma real de los
        sub_total de sus Proforma_Detail actuales (ver ADR-006, TASK-007).
        Agnóstico de sales_type: agrupa lo que ya haya en BD, sin recalcular
        el sub_total de cada ítem (eso lo hace CarModelPartForm.clean())."""
        total = Proforma_Detail.objects.filter(proforma_header=proforma).aggregate(
            total=Sum('sub_total')
        )['total']
        proforma.total_price = total if total is not None else Decimal('0')
        proforma.save(update_fields=['total_price'])


    def delete_fisica(self, user, proforma):
        try:
            if user.is_superuser:
                Proforma_Detail.objects.filter(proforma_header = proforma).delete()
                return proforma.delete()
            else:
                print(f'user ${user.username} intento borrar una proforma ${proforma.id}')
        except Exception as e:
            self.log_errors.error(f'algo salio mal, contactar administrador {e}')
            raise Exception('algo sali mal, contactar administrador')
        raise Exception('no se puede eliminar una proforma aprobada o instalada')
    
    def _legacy_none_without_sucursal(self, user):
        """Contrato de los metodos `*_by_role` del Django Admin: None cuando el
        usuario no tiene ninguna sucursal asignada (los ModelAdmin lo usan para
        mostrar "Asigne una sucursal al usuario"); el superusuario nunca."""
        return not self.user_helper.can_view_all_sucursales(user) and not self.user_helper.has_assigned_sucursal(user)

    def get_proforma_queryset_by_role(self, user, qs):
        """Legado del Django Admin: delega en el alcance del panel."""
        if self._legacy_none_without_sucursal(user):
            return None
        return self.get_panel_proforma_queryset(user, qs)

    def get_panel_proforma_queryset(self, user, qs):
        """Alcance de proformas para el panel (API `ordenes/proformas`): las no
        borradas de las sucursales asignadas al usuario (activas o no, alcance
        de lectura); solo el superusuario ve todas; sin sucursal, ninguna. Ver
        ADR-inventario-alcance-sucursal-django-admin-alcance-lectura-escritura."""
        qs = qs.filter(is_delete=False).select_related(
            'sucursal', 'car_model_id', 'car_model_id__car_brand_id', 'nota_trabajo'
        )
        if self.user_helper.can_view_all_sucursales(user):
            return qs
        return qs.filter(sucursal_id__in=self.user_helper.get_readable_sucursal_ids(user))

    def get_nota_venta_queryset_by_role(self, user, qs):
        """Legado del Django Admin: delega en el alcance del panel."""
        if self._legacy_none_without_sucursal(user):
            return None
        from .pago import Pago_Business  # import local: pago.py importa orden_estado
        return Pago_Business().get_panel_nota_venta_queryset(user, qs)

    def get_nota_trabajo_queryset_by_role(self, user, qs):
        """Legado del Django Admin: delega en el alcance del panel."""
        if self._legacy_none_without_sucursal(user):
            return None
        return self.orden_trabajo_bussiness.get_panel_nota_queryset(user, qs)

        
        

            