from PIL import Image, UnidentifiedImageError
from rest_framework import serializers

MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_FORMATS = {'JPEG', 'PNG', 'WEBP'}


def validate_uploaded_image(image):
    """Valida tipo (jpg/png/webp, verificado con Pillow, no por extension) y
    tamaño (<= 5 MB). Compartida entre los serializers de Vehiculos y Almacen
    -- ver ADR-modulo-vehiculos-almacenamiento-imagenes y
    ADR-modulo-almacen-modelo-datos-imagen-soft-delete."""
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
