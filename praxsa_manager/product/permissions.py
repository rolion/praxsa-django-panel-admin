from rest_framework import permissions


class IsStaffUser(permissions.BasePermission):
    """Requiere que el usuario autenticado sea staff (personal administrativo).
    Barrera adicional a DjangoModelPermissions para que un Client de proforma/
    nunca alcance los endpoints de gestion de usuarios/grupos/sucursales,
    aunque de alguna forma tuviera un Permission asignado por error."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)
