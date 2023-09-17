from ..models import Proforma_Header, Sucursal, Proforma_Detail, Nota_trabajo, Detalle_Nota_Trabajo, pago
from ..helper.proforma import Proforma_Helper
from .inventario import Inventario_Business
from ..utils.exception.nohaylaminas import NoHayLaminasDisponibles
from ..utils.exception.proforma import ProformaException, NotaVentaException
from django.db import IntegrityError, transaction
class Proforma_Business:

    def __init__(self) -> None:
        self.helper = Proforma_Helper()
        self.inv_bussiness = Inventario_Business()

    def get_proforma_by_id(self, id):
        return Proforma_Header.objects.get(pk = id)

    def delete_proforma(self, user, proforma):
        if proforma.sales_status == self.helper.req  :
            proforma.is_delete = True
            try:
                return proforma.save()
            except Exception as e:
                print('algo salio mal ->>', str(e))
                raise Exception('algo sali mal, contactar administrador')
        raise Exception('no se puede eliminar una proforma aprobada o instalada')
    
    def abrir_proforma(self, proforma):
        if proforma.sales_status is not self.helper.nov:
            try:
                proforma.sales_status = self.helper.prof
                return proforma.save()
            except Exception as e:
                print('algo salio mal ->>', str(e))
                raise Exception('algo salio mal, contactar administrador')
    
    @transaction.atomic
    def create_work_note(self, proforma, responsable):
        if proforma.sales_status == self.helper.prof:
            if proforma.codigo_garantia is None:
                raise Exception(f'Agregue el codigo de garantia en proforma {proforma.id}')
            try:
                with transaction.atomic():
                    detalles = Proforma_Detail.objects.select_related('proforma_header', 'window_film','proforma_header__sucursal' ).filter(proforma_header = proforma)
                    if detalles.exists():
                        for detalle in list(detalles):
                            to_reduce = detalle.length
                            to_reduce = to_reduce * detalle.quantity if detalle.quantity > 0 else to_reduce
                            self.inv_bussiness.update_inventory(sucursal = detalle.proforma_header.sucursal, windows_film =detalle.window_film, width = detalle.width, length_to_reduce = to_reduce)
                        proforma.sales_status = self.helper.nov
                    proforma.save()
                    nota_trabajo = Nota_trabajo()
                    nota_trabajo.proforma = proforma
                    nota_trabajo.name = proforma.name
                    nota_trabajo.car_model = proforma.car_model_id
                    nota_trabajo.car_plate = proforma.car_plate
                    nota_trabajo.responsable = responsable
                    nota_trabajo.save()
                    for detalle in list(detalles):
                        detalle_nota_trabajo = Detalle_Nota_Trabajo()
                        detalle_nota_trabajo.detalle_proforma= detalle
                        detalle_nota_trabajo.nota_trabajo = nota_trabajo
                        detalle_nota_trabajo.car_part = detalle.car_part
                        detalle_nota_trabajo.window_film = detalle.window_film
                        detalle_nota_trabajo.width = detalle.width
                        detalle_nota_trabajo.length = detalle.length
                        detalle_nota_trabajo.quantity = detalle.quantity
                        detalle_nota_trabajo.save()
                    return nota_trabajo
            except IntegrityError as e:
                raise Exception(f'ya existe una nota de trabajo asignada a la Proforma {proforma.id}')
            except NoHayLaminasDisponibles as e:
                 raise Exception(str(e))
            except Exception as e:
                print('algo salio mal ->>', str(e))
                print('error type', type(e))
                raise Exception('algo salio mal, contactar administrador')
        else:
            raise Exception('la proforma debe estar cerrada antes de crear la nota de venta')
        

    def crear_nota_venta(self, proforma):
        if proforma.sales_status == self.helper.prof:
            if proforma.codigo_garantia is None:
                raise Exception(f'Agregue el codigo de garantia en proforma {proforma.id}')
            try:
                detalles = Proforma_Detail.objects.select_related('proforma_header', 'window_film','proforma_header__sucursal' ).filter(proforma_header = proforma)
                if detalles.exists():
                    for detalle in list(detalles):
                        to_reduce = detalle.length
                        to_reduce = to_reduce * detalle.quantity if detalle.quantity > 0 else to_reduce
                        self.inv_bussiness.update_inventory(sucursal = detalle.proforma_header.sucursal, windows_film =detalle.window_film, width = detalle.width, length_to_reduce = to_reduce)
                    proforma.sales_status = self.helper.nov
                return proforma.save()
            except Exception as e:
                print('algo salio mal ->>', str(e))
                raise Exception('algo salio mal, contactar administrador')
        else:
            raise Exception('la proforma debe estar cerrada antes de crear la nota de venta')
    
    def delete_fisica(self, user, proforma):
        try:
            if user.is_superuser:
                Proforma_Detail.objects.filter(proforma_header = proforma).delete()
                return proforma.delete()
            else:
                print(f'user ${user.username} intento borrar una proforma ${proforma.id}')
        except Exception as e:
            print('algo salio mal ->>', str(e))
            raise Exception('algo sali mal, contactar administrador')
        raise Exception('no se puede eliminar una proforma aprobada o instalada')
    
    def get_proforma_queryset_by_role(self, user, qs):
        try:
            sucursales = Sucursal.objects.prefetch_related('empleado').filter(empleado__id = user.id, enable_to_install_windows_film = True)
            # if user.is_superuser:
            #     return qs.filter(is_delete = False)
            sucursales = Sucursal.objects.prefetch_related('empleado').filter(empleado__id = user.id, enable_to_install_windows_film = True)
            if len(sucursales) > 0:
                qs_result = qs.select_related('sucursal').filter(sucursal__id = sucursales[0].id, is_delete = False)
            else:
                qs_result = None
            return qs_result
        except Exception as e:
            print('algo salio mal, Proforma_Business - get_proforma_queryset_by_role', str(e))
            return None
        
    def get_nota_venta_queryset_by_role(self, user, qs):
        try:
            sucursales = Sucursal.objects.prefetch_related('empleado').filter(empleado__id = user.id, enable_to_install_windows_film = True)
            # if user.is_superuser:
            #     return qs.filter(is_delete = False)
            sucursales = Sucursal.objects.prefetch_related('empleado').filter(empleado__id = user.id, enable_to_install_windows_film = True)
            if len(sucursales) > 0:
                qs_result = qs.select_related('sucursal','nota_trabajo').filter(sucursal__id = sucursales[0].id, is_delete = False, sales_status = self.helper.nov)
            else:
                qs_result = None
            return qs_result
        except Exception as e:
            print('algo salio mal, Proforma_Business - get_proforma_queryset_by_role', str(e))
            return None
        
    def create_nota_venta_pago(self, proforma, user):
        if user is None:
            raise NotaVentaException('el usuario es requerido para la gestion del pago')
        if proforma is None:
            raise NotaVentaException('la nota venta no puede ser nula')
        if proforma.sales_status != self.helper.nov:
            raise NotaVentaException(f'proforma {proforma.id} no es una nota venta')
        
        paidment = pago()
        paidment.proforma = proforma
        paidment.cerrado = False
        paidment.created_by = user
        paidment.save()
        return paidment
        

            