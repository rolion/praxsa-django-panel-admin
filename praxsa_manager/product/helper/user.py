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
