from rest_framework import status
from rest_framework.exceptions import APIException


class SucursalInactiva(APIException):
    """Escritura sobre una sucursal que el usuario puede ver pero no operar
    (sucursal inactiva). Responde 409, igual que las demas reglas de estado
    de negocio del panel (ver ADR-inventario-alcance-sucursal-django-admin-
    alcance-lectura-escritura, decision 4)."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = 'La sucursal está inactiva: solo lectura.'
    default_code = 'sucursal_inactiva'
