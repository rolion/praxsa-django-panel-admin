from rest_framework import serializers

from ..models import Window_Film, Window_Film_Reel, inventario
from .image_validation import validate_uploaded_image


class WindowFilmSerializer(serializers.ModelSerializer):
    """CRUD de Lamina (Window_Film). `is_active` de solo lectura a proposito
    -- mismo motivo que CarBrandSerializer/CarModelSerializer
    (REV-2026-09-26-modulo-vehiculos-01): un ModelSerializer sin
    read_only=True interpreta un multipart/form-data sin ese campo como
    False, dejando una Lamina creada desde el panel (que manda FormData por
    la imagen) inactiva e invisible al instante. "Eliminar"/"activar" solo
    pasa por el endpoint toggle-active dedicado."""

    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = Window_Film
        fields = ['id', 'name', 'description', 'content', 'image', 'is_active']

    def validate_image(self, value):
        if value is None:
            return value
        return validate_uploaded_image(value)

    def update(self, instance, validated_data):
        removing_image = 'image' in validated_data and validated_data['image'] is None
        replacing_image = 'image' in validated_data and validated_data['image'] is not None
        if (removing_image or replacing_image) and instance.image:
            instance.image.delete(save=False)
        return super().update(instance, validated_data)


class WindowFilmReelSerializer(serializers.ModelSerializer):
    """CRUD de Bobina (Window_Film_Reel). `window_film` solo acepta laminas
    activas (mismo criterio que car_brand_id en CarModelSerializer -- no se
    puede asociar una bobina nueva a una lamina ya eliminada). `is_active`
    de solo lectura -- ver WindowFilmSerializer."""

    window_film = serializers.PrimaryKeyRelatedField(
        queryset=Window_Film.objects.filter(is_active=True)
    )
    window_film_name = serializers.CharField(source='window_film.name', read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = Window_Film_Reel
        fields = [
            'id', 'window_film', 'window_film_name', 'width', 'length', 'price', 'is_active',
        ]


class InventarioSerializer(serializers.ModelSerializer):
    """Lectura completa de una fila de Inventario, para el listado (ambos
    roles). La edicion (solo admin) usa InventarioUpdateSerializer, con un
    subconjunto de campos -- ver ADR-modulo-almacen-modelo-datos-imagen-soft-delete
    punto 8."""

    sucursal_name = serializers.CharField(source='sucursal.name', read_only=True)
    window_film_name = serializers.CharField(source='bobina.window_film.name', read_only=True)
    bobina_width = serializers.DecimalField(
        source='bobina.width', max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = inventario
        fields = [
            'id', 'sucursal', 'sucursal_name', 'bobina', 'window_film_name', 'bobina_width',
            'quantity', 'to_install', 'installed', 'original_length', 'date',
            'numero_referencia', 'precio_compra_mtr_lineal', 'precio_venta_mtr_lineal',
            'nro_lote',
        ]


class InventarioUpdateSerializer(serializers.ModelSerializer):
    """`PATCH` de "Gestionar Inventario" (solo admin) -- unicamente los
    campos que no rompen la trazabilidad de instalaciones ya generada por
    Inventario_Business (ver ADR-modulo-almacen-modelo-datos-imagen-soft-delete
    punto 8, decision explicita de excluir quantity/original_length/date/
    sucursal/bobina)."""

    class Meta:
        model = inventario
        fields = [
            'to_install', 'installed', 'precio_compra_mtr_lineal',
            'precio_venta_mtr_lineal', 'nro_lote',
        ]
