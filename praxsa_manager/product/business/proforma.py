from ..models import Sale_Header, Sucursal
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
    
    def get_proforma_queryset_by_role(self, user, qs):
        if user.is_superuser:
            return qs.filter(is_delete = False)
        sucursales = Sucursal.objects.filter(empleado__id = user.id)
        if len(sucursales) > 0:
            qs_result = qs.filter(sucursal__id = sucursales[0].id, is_delete = False)
        else:
            qs_result = qs.filter(sucursal = -1)
        
        return qs_result