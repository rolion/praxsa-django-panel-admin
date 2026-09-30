from rest_framework import permissions


class IsStaffUser(permissions.BasePermission):
    """Requiere que el usuario autenticado sea staff (personal administrativo).
    Barrera adicional a DjangoModelPermissions para que un Client de proforma/
    nunca alcance los endpoints de gestion de usuarios/grupos/sucursales,
    aunque de alguna forma tuviera un Permission asignado por error."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class TienePermisoReporte(permissions.BasePermission):
    """Exige el permiso Django `view` del reporte (`view.permission_codename`, p. ej.
    `product.view_utilidades`). DjangoModelPermissions no exige permiso a los GET, por
    eso se verifica de forma explicita (ADR-reportes-utilidad-ventas-diarias-permisos)."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.has_perm(view.permission_codename))
