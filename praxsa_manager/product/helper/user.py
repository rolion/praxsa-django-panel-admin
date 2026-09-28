from ..models import Sucursal
class User_Helper():

    def to_lowercase(self, groups):
        return list(map(lambda group: group.lower(), groups))

    def is_request_user_admin(self, user):
        user_groups = self.to_lowercase(list(user.groups.values_list('name',flat = True)))
        
        return 'admin' in list(user_groups)
    
    def is_request_user_installer(self, user):
        user_groups = self.to_lowercase(list(user.groups.values_list('name',flat = True)))
        return 'instalador' in list(user_groups)
    
    def is_request_user_supervisor(self, user):
        user_groups = self.to_lowercase(list(user.groups.values_list('name',flat = True)))
        return 'supervisor' in list(user_groups)

    def is_request_user_caja(self, user):
        user_groups = self.to_lowercase(list(user.groups.values_list('name',flat = True)))
        return 'caja' in list(user_groups)

    def is_request_user_almacen(self, user):
        user_groups = self.to_lowercase(list(user.groups.values_list('name',flat = True)))
        return 'almacen' in list(user_groups)

    def can_view_all_sucursales(self, user):
        return self.is_request_user_admin(user)

    def has_assigned_sucursal(self, user):
        """Replica la condicion de sucursal que ya usa
        Inventario_Business.get_inventario_queryset_by_role, para que los
        admins de Django que consumen ese metodo puedan distinguir "el
        usuario no tiene sucursal asignada" de "el usuario tiene sucursal
        pero el reporte da 0 filas" -- ambos casos devuelven un queryset
        vacio desde que ese metodo dejo de devolver None (ver REV-2026-09-27-
        modulo-almacen-02)."""
        return Sucursal.objects.filter(empleado__id=user.id, enable_to_install_windows_film=True).exists()
