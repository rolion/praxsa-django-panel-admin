"""Reduccion de imagenes de Modelos de vehiculo a WEBP liviano (compartido por los
comandos `precargar_imagenes_modelos` e `importar_imagenes_modelos`)
-- ver ADR-carga-imagenes-modelos-despliegue-distribucion-imagenes."""
import io

from PIL import Image

MIN_WIDTH = 500            # tamaño final minimo (ni muy pequeña)
MAX_WIDTH = 900            # tamaño final maximo
MAX_BYTES = 150 * 1024     # peso final maximo (muy por debajo del tope de 5 MB del admin)


def reducir_a_webp(content):
    """Bytes de imagen -> bytes WEBP (MIN_WIDTH..MAX_WIDTH, <= MAX_BYTES, conserva
    transparencia si la trae), o None si no se logra sin quedar muy chica.
    Lanza UnidentifiedImageError/OSError si `content` no es una imagen."""
    with Image.open(io.BytesIO(content)) as img:
        img = img.convert('RGBA' if 'A' in img.getbands() or 'transparency' in img.info else 'RGB')
    width = min(img.width, MAX_WIDTH)
    while width >= MIN_WIDTH:
        copia = img.resize((width, round(img.height * width / img.width)), Image.LANCZOS) if width != img.width else img
        for quality in (85, 75, 65, 55):
            buf = io.BytesIO()
            copia.save(buf, 'WEBP', quality=quality, method=6)
            if buf.tell() <= MAX_BYTES:
                return buf.getvalue()
        width = int(width * 0.85)
    return None
