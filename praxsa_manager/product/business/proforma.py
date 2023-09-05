from ..models import Sale_Header, Sucursal, Sale_Detail
from ..helper.proforma import Proforma_Helper
class Proforma_Business:

    def __init__(self) -> None:
        self.helper = Proforma_Helper()

    def get_proforma_by_id(self, id):
        return Sale_Header.objects.get(pk = id)

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
    def crear_nota_venta(self, proforma):
        if proforma.sales_status == self.helper.prof:
            try:
                ## todo validar inventario
                ## si el inventario es valido, descontar del inventario
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
                Sale_Detail.objects.filter(sales_header_id = proforma).delete()
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
            