from decimal import Decimal

from rest_framework import serializers

from ..helper.user import User_Helper
from ..models import Window_Film, instalador, precio_venta_sucursal


class InstaladorSerializer(serializers.ModelSerializer):
    """CRUD de Instalador. `is_active` de solo lectura a proposito -- mismo
    motivo que WindowFilmSerializer: "eliminar"/"activar" solo pasa por el
    endpoint toggle-active dedicado (ver ADR-agrupacion-menu-instalador-
    precio-sucursal-api-permisos-borrado, decision 3)."""

    sucursal_names = serializers.SerializerMethodField()
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = instalador
        fields = ['id', 'name', 'address', 'phonenumber', 'sucursal', 'sucursal_names', 'is_active']

    def get_sucursal_names(self, obj):
        return [sucursal.name for sucursal in obj.sucursal.all()]


class PrecioVentaSucursalSerializer(serializers.ModelSerializer):
    """CRUD de Precio por sucursal (override del precio del inventario para una
    sucursal + lamina + ancho). La unicidad de esa terna se valida aca porque
    la tabla no tiene constraint en base (BIZ-07, decision 6 del ADR)."""

    lamina = serializers.PrimaryKeyRelatedField(queryset=Window_Film.objects.filter(is_active=True))
    lamina_name = serializers.CharField(source='lamina.name', read_only=True)
    sucursal_name = serializers.CharField(source='sucursal.name', read_only=True)

    class Meta:
        model = precio_venta_sucursal
        fields = ['id', 'sucursal', 'sucursal_name', 'lamina', 'lamina_name', 'width', 'precio_venta']

    def validate_width(self, value):
        if value <= Decimal('0'):
            raise serializers.ValidationError('El ancho debe ser mayor a 0.')
        return value

    def validate_precio_venta(self, value):
        if value <= Decimal('0'):
            raise serializers.ValidationError('El precio de venta debe ser mayor a 0.')
        return value

    def validate_sucursal(self, value):
        request = self.context.get('request')
        if request is not None:
            in_scope = User_Helper().get_sucursales_in_scope(request.user)
            if not in_scope.filter(pk=value.pk).exists():
                raise serializers.ValidationError('La sucursal no está disponible para tu usuario.')
        return value

    def validate(self, attrs):
        current = self.instance
        sucursal = attrs.get('sucursal', current.sucursal if current else None)
        lamina = attrs.get('lamina', current.lamina if current else None)
        width = attrs.get('width', current.width if current else None)
        if sucursal is not None and lamina is not None and width is not None:
            duplicates = precio_venta_sucursal.objects.filter(sucursal=sucursal, lamina=lamina, width=width)
            if current is not None:
                duplicates = duplicates.exclude(pk=current.pk)
            if duplicates.exists():
                raise serializers.ValidationError(
                    f'Ya existe un precio para la lámina {lamina.name} con el ancho {width} '
                    f'en la sucursal {sucursal.name}.'
                )
        return attrs
