from typing import Union
from ..models import Car_Model_Part, Proforma_Header, Sucursal, Proforma_Detail, Nota_trabajo, Detalle_Nota_Trabajo, pago, Nota_Venta
from ..helper.proforma import Proforma_Helper
from .inventario import Inventario_Business
from ..utils.exception.nohaylaminas import NoHayLaminasDisponibles
from ..utils.exception.proforma import ProformaException, NotaVentaException
from django.db import IntegrityError, transaction
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
        self.log_errors = logging.getLogger('django_admin')
        self.log_debug= logging.getLogger('debug')
        self.helper = Proforma_Helper()

    def get_proforma_by_id(self, id):
        return Proforma_Header.objects.get(pk = id)

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
                    return proforma.save()
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
                    return self.orden_trabajo_bussiness.create_work_note(proforma=proforma, sumary=sumary,responsable= responsable)
            except IntegrityError as e:
                raise Exception(f'ya existe una nota de trabajo asignada a la Proforma {proforma.id}')
            except NoHayLaminasDisponibles as e:
                 raise Exception(str(e))
            except ProformaException as e:
                raise e
            except Exception as e:
                self.log_errors.error(f'algo salio mal, contactar administrador {e}')
                raise Exception('algo salio mal, contactar administrador')
        

    def crear_nota_venta(self, nota_trabajo, user):
        if nota_trabajo.proforma.is_close == False:
                    raise Exception(f'la proforma {nota_trabajo.proforma.id}, debe estar cerrada antes de crear la nota de venta')
        if nota_trabajo.codigo_garantia is not None:
            try:
                nota_venta = Nota_Venta()
                nota_venta.nota_trabajo = nota_trabajo
                nota_venta.name = nota_trabajo.proforma.name
                nota_venta.ci_nit = nota_trabajo.proforma.ci_nit
                nota_venta.total_price = nota_trabajo.proforma.total_price
                nota_venta.created_by = user
                nota_venta.created_on = datetime.now()
                nota_venta.save()
                nota_trabajo.is_close = True
                nota_trabajo.save()
            except Exception as e:
                self.log_errors.error(f'algo salio mal, contactar administrador {e}')
                raise Exception('algo salio mal, contactar administrador')
        else:
            raise Exception('Debe agregar el código de Garantía')

    
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
        

            