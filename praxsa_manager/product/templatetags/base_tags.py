from django import template

register = template.Library()

from ..models import Sucursal

@register.simple_tag
def user_sucursal(user):
    list_sucursales = Sucursal.objects.filter(empleado = user).values_list('name', flat=True)
    return ','.join(list_sucursales)