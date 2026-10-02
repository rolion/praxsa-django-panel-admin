from ..models import Sucursal
from ..utils.exception.sucursal import SucursalInactiva


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
        """Unica excepcion global al alcance por sucursal: el superusuario de
        Django. El grupo admin ya no la tiene (ver ADR-inventario-alcance-
        sucursal-django-admin-alcance-lectura-escritura, decision 1)."""
        return bool(user.is_superuser)

    def get_readable_sucursales(self, user):
        """Sucursales cuyos datos el usuario puede VER: las asignadas a su
        cuenta (`Sucursal.empleado`), activas o no; el superusuario, todas."""
        sucursales = Sucursal.objects.all()
        if self.can_view_all_sucursales(user):
            return sucursales.order_by('name')
        return sucursales.filter(empleado__id=user.id).distinct().order_by('name')

    def get_writable_sucursales(self, user):
        """Sucursales donde el usuario puede AGREGAR o MODIFICAR: las de lectura
        que ademas estan activas (`enable_to_install_windows_film`)."""
        return self.get_readable_sucursales(user).filter(enable_to_install_windows_film=True)

    def get_readable_sucursal_ids(self, user):
        return list(self.get_readable_sucursales(user).values_list('id', flat=True))

    def get_writable_sucursal_ids(self, user):
        return list(self.get_writable_sucursales(user).values_list('id', flat=True))

    def is_sucursal_writable(self, user, sucursal_id):
        return self.get_writable_sucursales(user).filter(pk=sucursal_id).exists()

    def require_sucursal_writable(self, user, sucursal_id):
        """Guarda de toda modificacion de una fila existente: la sucursal de la
        fila debe estar activa y en el alcance del usuario; si no, 409. Se
        llama despues del 404 de alcance de lectura y del 403 de permiso."""
        if not self.is_sucursal_writable(user, sucursal_id):
            raise SucursalInactiva()

    def has_assigned_sucursal(self, user):
        """El usuario tiene alguna sucursal en su alcance de lectura. Permite
        distinguir "no tiene sucursal asignada" de "el reporte da 0 filas"
        (ver REV-2026-09-27-modulo-almacen-02)."""
        return self.get_readable_sucursales(user).exists()
