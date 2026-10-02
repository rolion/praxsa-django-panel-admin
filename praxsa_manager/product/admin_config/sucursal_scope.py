from operator import attrgetter

from ..helper.user import User_Helper
from ..models import Sucursal


class SucursalWritableAdminMixin:
    """Regla de escritura por sucursal para los ModelAdmin del Django Admin (ADR-
    inventario-alcance-sucursal-django-admin-alcance-lectura-escritura, decision
    7): una fila solo se agrega o modifica si su sucursal esta asignada al usuario
    y activa; si no, la fila se ve (lectura) pero el formulario queda de solo
    lectura. `sucursal_obj_path` es la ruta (con puntos) desde el objeto hasta el
    id de su sucursal.

    Los ModelAdmin que sobreescriben `has_change_permission` deben llamar a
    `sucursal_writable_for(request, obj)` antes de sus propias reglas."""

    sucursal_obj_path = 'sucursal_id'

    def obj_sucursal_id(self, obj):
        try:
            return attrgetter(self.sucursal_obj_path)(obj)
        except AttributeError:
            return None

    def sucursal_writable_for(self, request, obj):
        if obj is None:
            return True
        return User_Helper().is_sucursal_writable(request.user, self.obj_sucursal_id(obj))

    def has_add_permission(self, request, *args, **kwargs):
        if not super().has_add_permission(request, *args, **kwargs):
            return False
        return User_Helper().get_writable_sucursales(request.user).exists()

    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and self.sucursal_writable_for(request, obj)

    def has_delete_permission(self, request, obj=None):
        return super().has_delete_permission(request, obj) and self.sucursal_writable_for(request, obj)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'sucursal' and db_field.related_model is Sucursal:
            kwargs['queryset'] = User_Helper().get_writable_sucursales(request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
