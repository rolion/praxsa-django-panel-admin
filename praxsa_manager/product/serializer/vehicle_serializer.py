from PIL import Image, UnidentifiedImageError
from rest_framework import serializers

from ..models import Car_Brand, Car_Model, Car_Model_Part, Car_Part

MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_FORMATS = {'JPEG', 'PNG', 'WEBP'}


class CarBrandSerializer(serializers.ModelSerializer):
    """CRUD de Marca (Car_Brand). `models_count` viene de una anotacion
    Count('car_model') en el queryset del listado, no se calcula aqui."""

    models_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Car_Brand
        fields = ['id', 'name', 'is_active', 'models_count']

    def validate_name(self, value):
        queryset = Car_Brand.objects.filter(name__iexact=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError('Ya existe una marca con este nombre.')
        return value


class CarPartSerializer(serializers.ModelSerializer):
    """CRUD de Item (Car_Part)."""

    class Meta:
        model = Car_Part
        fields = ['id', 'name', 'is_active']


def validate_car_model_image(image):
    """Valida tipo (jpg/png/webp, verificado con Pillow, no por extension) y
    tamaño (<= 5 MB). Ver ADR-modulo-vehiculos-almacenamiento-imagenes."""
    if image.size > MAX_IMAGE_SIZE_BYTES:
        raise serializers.ValidationError('La imagen no puede superar los 5 MB.')
    try:
        with Image.open(image) as img:
            img.verify()
            image_format = img.format
    except (UnidentifiedImageError, OSError):
        raise serializers.ValidationError('El archivo no es una imagen valida.')
    if image_format not in ALLOWED_IMAGE_FORMATS:
        raise serializers.ValidationError('Formato de imagen no permitido. Use JPG, PNG o WEBP.')
    image.seek(0)
    return image


class CarModelSerializer(serializers.ModelSerializer):
    """CRUD de Modelo (Car_Model). `car_brand_id` solo acepta marcas activas.
    `items_count` viene de una anotacion Count('car_model_part') en el
    queryset del listado, no se calcula aqui."""

    car_brand_id = serializers.PrimaryKeyRelatedField(
        queryset=Car_Brand.objects.filter(is_active=True)
    )
    car_brand_name = serializers.CharField(source='car_brand_id.name', read_only=True)
    items_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Car_Model
        fields = [
            'id', 'name', 'car_brand_id', 'car_brand_name', 'image',
            'is_active', 'items_count',
        ]

    def validate_name(self, value):
        queryset = Car_Model.objects.filter(name__iexact=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError('Ya existe un modelo con este nombre.')
        return value

    def validate_image(self, value):
        if value is None:
            return value
        return validate_car_model_image(value)

    def update(self, instance, validated_data):
        removing_image = 'image' in validated_data and validated_data['image'] is None
        replacing_image = 'image' in validated_data and validated_data['image'] is not None
        if (removing_image or replacing_image) and instance.image:
            instance.image.delete(save=False)
        return super().update(instance, validated_data)


class CarModelPartSerializer(serializers.ModelSerializer):
    """Asociacion Modelo<->Item (Car_Model_Part). Acepta un item ya existente
    (`car_part_id`) o crea uno nuevo (`new_car_part_name`), pero exige uno de
    los dos -- solo al crear (`self.instance is None`); al editar una
    asociacion ya existente (PATCH) no se permite cambiar el item, solo
    width/length/quantity/installation_price.

    width/length/quantity son obligatorios al crear (no se confia en los
    defaults del modelo) -- ver ADR-modulo-vehiculos-relacion-modelo-item.
    `installation_price` quedo oculto en el formulario del panel a pedido
    explicito del usuario (2026-09-26); se relaja aqui a opcional (usa el
    default del modelo, 0) en vez de forzar un valor desde el frontend --
    es exactamente el camino de rollback que el ADR ya habia previsto para
    este campo."""

    car_part_id = serializers.PrimaryKeyRelatedField(
        queryset=Car_Part.objects.filter(is_active=True), required=False, allow_null=True
    )
    car_part_name = serializers.CharField(source='car_part_id.name', read_only=True)
    new_car_part_name = serializers.CharField(required=False, allow_blank=False, write_only=True)
    width = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    length = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    quantity = serializers.IntegerField(min_value=1, required=True)
    installation_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)

    class Meta:
        model = Car_Model_Part
        fields = [
            'id', 'car_part_id', 'car_part_name', 'new_car_part_name',
            'width', 'length', 'quantity', 'installation_price',
        ]

    def validate(self, attrs):
        if self.instance is not None:
            return attrs
        car_part = attrs.get('car_part_id')
        new_name = attrs.get('new_car_part_name')
        if bool(car_part) == bool(new_name):
            raise serializers.ValidationError(
                'Debe indicar un item existente (car_part_id) o el nombre de uno nuevo (new_car_part_name), no ambos ni ninguno.'
            )
        if car_part is not None:
            car_model = self.context['car_model']
            if Car_Model_Part.objects.filter(car_model_id=car_model, car_part_id=car_part).exists():
                raise serializers.ValidationError('Este item ya esta asociado a este modelo.')
        return attrs

    def create(self, validated_data):
        car_part = validated_data.pop('car_part_id', None)
        new_name = validated_data.pop('new_car_part_name', None)
        if car_part is None:
            car_part = Car_Part.objects.create(name=new_name)
        return Car_Model_Part.objects.create(
            car_model_id=self.context['car_model'],
            car_part_id=car_part,
            **validated_data,
        )

    def update(self, instance, validated_data):
        # Editar una asociacion nunca cambia el item asociado, aunque el
        # cliente mande car_part_id/new_car_part_name -- se ignoran en vez
        # de aplicarlos (defensa en profundidad, no depende solo de que el
        # frontend no los mande).
        validated_data.pop('car_part_id', None)
        validated_data.pop('new_car_part_name', None)
        return super().update(instance, validated_data)
