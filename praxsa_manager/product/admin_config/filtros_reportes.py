"""Filtros laterales reutilizables de los reportes/listados del Django Admin
(TASK-filtros-busqueda-reportes)."""
from django.contrib import admin
from django_admin_listfilter_dropdown.filters import ChoiceDropdownFilter

from ..helper.user import User_Helper


def sucursal_en_alcance_filter(path, title='Sucursal'):
    """Filtro de sucursal cuyas opciones son solo las sucursales disponibles para
    el usuario (las asignadas al usuario, activas o no; todas solo para el superusuario).
    `path` es la ruta al campo FK de sucursal desde el modelo del admin."""

    class SucursalEnAlcanceFilter(admin.SimpleListFilter):
        # nombre simple: Django solo acepta parametros con rutas relacionadas si estan en list_filter como campo
        parameter_name = 'sucursal'

        def lookups(self, request, model_admin):
            return [(s.id, s.name) for s in User_Helper().get_readable_sucursales(request.user)]

        def queryset(self, request, queryset):
            if self.value():
                return queryset.filter(**{f'{path}__id': self.value()})
            return queryset

    SucursalEnAlcanceFilter.title = title
    return SucursalEnAlcanceFilter


def estado_filter(title):
    """Desplegable de choices con titulo propio: varios filtros comparten el campo
    `status` y el titulo por defecto seria "Estado" en todos."""

    class EstadoFilter(ChoiceDropdownFilter):
        def __init__(self, field, request, params, model, model_admin, field_path):
            super().__init__(field, request, params, model, model_admin, field_path)
            self.title = title

    return EstadoFilter
