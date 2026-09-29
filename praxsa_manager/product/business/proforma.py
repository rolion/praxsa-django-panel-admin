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
from decimal import *
from ..helper.proforma import Proforma_Helper
import logging

class Proforma_Business:

    def __init__(self) -> None:
        self.helper = Proforma_Helper()
        self.inv_bussiness = Inventario_Business()
        self.orden_trabajo_bussiness = Orden_Trabajo_Business()
        self.user_helper = User_Helper()
        self.log_errors = logging.getLogger('django_admin')
        self.log_debug= logging.getLogger('debug')
        self.helper = Proforma_Helper()

    def get_proforma_by_id(self, id):
        return Proforma_Header.objects.get(pk = id)

    def refresh_status(self, proforma):
        # Misma logica y mismo orden que ProformaAdmin.get_estado (admin_config/proforma_admin.py),
        # para que el campo persistido nunca diverja de lo que el admin ya muestra hoy (TASK-009/ADR-006).
        status = self.helper.estado_proforma
        if hasattr(proforma, 'nota_trabajo'):
            status = self.helper.estado_nota_trabajo
        else:
            proforma.status = status
            proforma.save(update_fields=['status'])
            return proforma
        if hasattr(proforma.nota_trabajo, 'nota_venta'):
            status = self.helper.estado_por_cobrar
        else:
            proforma.status = status
            proforma.save(update_fields=['status'])
            return proforma
        if hasattr(proforma.nota_trabajo.nota_venta, 'pago'):
            status = self.helper.estado_finalizado
        proforma.status = status
        proforma.save(update_fields=['status'])
        return proforma

    def delete_proforma(self, user, proforma):
        if proforma.sales_status == self.helper.req  :
            proforma.is_delete = True
            try:
                return proforma.save()
            except Exception as e:
                self.log_errors.error(f'algo sali mal, contactar administrador {e}')
                raise Exception('algo sali mal, contactar administrador')
        self.log_errors.error(f'no se puede eliminar una proforma aprobada o instalada {e}')
        raise Exception('no se puede eliminar una proforma aprobada o instalada')
    
    @transaction.atomic
    def abrir_proforma(self, proforma):
        if proforma.is_close == True:
            try:
                with transaction.atomic():
                    detalles = Proforma_Detail.objects.select_related('proforma_header', 'window_film','proforma_header__sucursal' )
                    detalles = detalles.filter(proforma_header = proforma)
                    proforma.is_close = False
                    if detalles.exists():
                        for detalle in list(detalles):
                            to_add = detalle.length
                            to_add = to_add * Decimal(detalle.quantity) if detalle.quantity > 0 else to_add
                            result = self.inv_bussiness.return_to_inventory(detail_inventory= detalle.inventario,
                                                                   length_to_add = to_add)
                            if result is not True:
                                self.log_errors.error(f'no se actualizo el inventario {e}')
                                raise Exception('no se actualizo el inventario')
                    proforma.save()
                    return self.refresh_status(proforma)
            except Exception as e:
                self.log_errors.error(f'algo salio mal, contactar administrador {e}')
                raise Exception('algo salio mal, contactar administrador')
    
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
    
    @transaction.atomic
    def create_work_note(self, proforma, responsable):
        # if proforma.sales_status == self.helper.prof:
            try:
                with transaction.atomic():
                    detalles = Proforma_Detail.objects.select_related('proforma_header', 'window_film','proforma_header__sucursal' )
                    detalles = detalles.filter(proforma_header = proforma)
                    sumary = []
                    
                    if detalles.exists():
                        if proforma.sales_type == self.helper.tipo_venta_instalacion:
                            self.validate_proforma_detail(detalles)
                        for detalle in list(detalles):
                            to_reduce = detalle.length
                            to_reduce = to_reduce * Decimal(detalle.quantity) if detalle.quantity > 0 else to_reduce
                            # update inventory
                            inventario = self.inv_bussiness.reduce_inventory(sucursal = detalle.proforma_header.sucursal, 
                                                                windows_film =detalle.window_film, 
                                                                width = detalle.width, 
                                                                length_to_reduce = to_reduce)
                            detalle.inventario = inventario
                            detalle.save()
                            item_index = next((i for i, item in enumerate(sumary) 
                                               if item["window_film"] == detalle.window_film and item["width"] == inventario.bobina.width ), 
                                               None)
                            if item_index is not None:
                                sumary[item_index]['length'] = sumary[item_index]['length'] + to_reduce
                            else:
                                sumary.append({"window_film": detalle.window_film, "width": inventario.bobina.width, 'length':  to_reduce})
                    proforma.is_close = True
                    proforma.save()
                    nota_trabajo = self.orden_trabajo_bussiness.create_work_note(proforma=proforma, sumary=sumary,responsable= responsable)
                    self.refresh_status(proforma)
                    return nota_trabajo
            except IntegrityError as e:
                raise Exception(f'ya existe una nota de trabajo asignada a la Proforma {proforma.id}')
            except NoHayLaminasDisponibles as e:
                 raise Exception(str(e))
            except ProformaException as e:
                raise e
            except Exception as e:
                self.log_errors.error(f'algo salio mal, contactar administrador {e}')
                raise Exception('algo salio mal, contactar administrador')
        
    
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

    def crear_nota_venta(self, nota_trabajo, user):
        if nota_trabajo.proforma.is_close == False:
                    raise Exception(f'la proforma {nota_trabajo.proforma.id}, debe estar cerrada antes de crear la nota de venta')
        if nota_trabajo.proforma.sales_type == self.helper.tipo_venta_instalacion and nota_trabajo.codigo_garantia is  None:
            raise Exception('Debe agregar el código de Garantía')
        
        if nota_trabajo.proforma.sales_type == self.helper.tipo_venta_instalacion and nota_trabajo.instaladar is  None:
            raise Exception('Debe agregar un Instalador')
        try:
            nota_venta = Nota_Venta()
            nota_venta.nota_trabajo = nota_trabajo
            nota_venta.name = nota_trabajo.proforma.name
            nota_venta.ci_nit = nota_trabajo.proforma.ci_nit
            nota_venta.total_price = nota_trabajo.proforma.total_price - nota_trabajo.proforma.discount
            nota_venta.created_by = user
            nota_venta.created_on = datetime.now()
            nota_venta.save()
            nota_trabajo.is_close = True
            nota_trabajo.save()
            self.refresh_status(nota_trabajo.proforma)
        except Exception as e:
            self.log_errors.error(f'algo salio mal, contactar administrador {e}')
            raise Exception('algo salio mal, contactar administrador')

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
    
    def get_proforma_queryset_by_role(self, user, qs):
        try:
            user_groups = list(user.groups.values_list('name',flat = True))
            is_admin = 'Admin' in user_groups
            if is_admin == True:
                qs_result = qs.select_related('sucursal', 'car_model_id','car_model_id__car_brand_id')
                qs_result = qs_result.filter(is_delete = False)
            else:
                sucursales = Sucursal.objects.prefetch_related('empleado')
                sucursales = sucursales.filter(empleado__id = user.id, enable_to_install_windows_film = True)
                if len(sucursales) > 0:
                    qs_result = qs.select_related('sucursal', 'car_model_id','car_model_id__car_brand_id')
                    qs_result = qs_result.filter(sucursal__id = sucursales[0].id, is_delete = False)
                else:
                    qs_result = None
            
            return qs_result
        except Exception as e:
            self.log_errors.error(f'algo salio mal, Proforma_Business - get_proforma_queryset_by_role {e}')
            return None
        
    def get_panel_proforma_queryset(self, user, qs):
        """Alcance de proformas para el panel (API `ordenes/proformas`). Metodo
        nuevo, sin tocar get_proforma_queryset_by_role (que sigue alimentando
        Django Admin): admin (case-insensitive) ve todas las no borradas; el
        resto, las de todas sus sucursales habilitadas; sin sucursal, ninguna.
        Ver ADR-modulo-ordenes-proforma-nota-trabajo-alcance-permisos."""
        qs = qs.filter(is_delete=False).select_related(
            'sucursal', 'car_model_id', 'car_model_id__car_brand_id', 'nota_trabajo'
        )
        if self.user_helper.can_view_all_sucursales(user):
            return qs
        return qs.filter(sucursal_id__in=self.user_helper.get_enabled_sucursal_ids(user))

    def get_nota_venta_queryset_by_role(self, user, qs):
        try:
            sucursales = Sucursal.objects.prefetch_related('empleado').filter(empleado__id = user.id, enable_to_install_windows_film = True)
            
            sucursales = Sucursal.objects.prefetch_related('empleado').filter(empleado__id = user.id, enable_to_install_windows_film = True)
            if len(sucursales) > 0:
                qs_result = qs.select_related('nota_trabajo', 'nota_trabajo__proforma', 'nota_trabajo__proforma__sucursal')
                qs_result =qs_result.filter(nota_trabajo__proforma__sucursal__id = sucursales[0].id)
            else:
                qs_result = None
            return qs_result
        except Exception as e:
            self.log_errors.error(f'algo salio mal, Proforma_Business - get_proforma_queryset_by_role {e}')
            return None
        
    def get_nota_trabajo_queryset_by_role(self, user, qs):
        try:
            sucursales = Sucursal.objects.prefetch_related('empleado').filter(empleado__id = user.id, enable_to_install_windows_film = True)
            # if user.is_superuser:
            #     return qs.filter(is_delete = False)
            sucursales = Sucursal.objects.prefetch_related('empleado').filter(empleado__id = user.id, enable_to_install_windows_film = True)
            if len(sucursales) > 0:
                qs_result = qs.select_related('proforma__sucursal').filter(proforma__sucursal__id = sucursales[0].id, proforma__is_delete = False)
            else:
                qs_result = None
            return qs_result
        except Exception as e:
            self.log_errors.error(f'algo salio mal, Proforma_Business - get_proforma_queryset_by_role {e}')
            return None
        
    def create_nota_venta_pago(self, proforma, user):
        if user is None:
            raise NotaVentaException('el usuario es requerido para la gestion del pago')
        if proforma is None:
            raise NotaVentaException('la nota venta no puede ser nula')
        # if proforma.sales_status != self.helper.nov:
        #     raise NotaVentaException(f'proforma {proforma.id} no es una nota venta')
        
        paidment = pago()
        paidment.proforma = proforma
        paidment.cerrado = False
        paidment.created_by = user
        paidment.save()
        return paidment
        

            