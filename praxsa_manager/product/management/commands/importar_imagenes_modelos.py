"""Importa imagenes de Modelos desde una carpeta de archivos nombrados
"Marca - Modelo.<ext>". Empareja por nombre (sin distinguir mayusculas ni espacios
alrededor de los guiones), reduce cada una a WEBP liviano (ver
`product/helper/imagenes.py`) y la asigna a `Car_Model.image`.

Por defecto lee `product/seed_data/car_models/` (viaja en la imagen Docker) y NO
pisa modelos que ya tienen una imagen cuyo archivo existe (por ejemplo, subida
desde el admin); `--forzar` las reemplaza. `--exportar-a DIR` no toca la BD:
escribe los WEBP reducidos de `--carpeta` en DIR como "Marca - Modelo.webp", que
es como se genera el set versionado desde los originales. Nunca borra los
archivos de origen. Reporta archivos sin modelo, errores y modelos sin archivo
-- ver ADR-carga-imagenes-modelos-despliegue-distribucion-imagenes."""
import re
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from PIL import UnidentifiedImageError

from product.helper.imagenes import reducir_a_webp
from product.models import Car_Model

EXTENSIONES = {'.png', '.jpg', '.jpeg', '.jfif', '.webp'}
CARPETA_SEED = Path(__file__).resolve().parents[2] / 'seed_data' / 'car_models'


def _clave(texto):
    return re.sub(r'\s+', ' ', re.sub(r'\s*-\s*', ' - ', texto)).strip().casefold()


def _tiene_imagen_valida(modelo):
    return bool(modelo.image) and modelo.image.storage.exists(modelo.image.name)


class Command(BaseCommand):
    help = 'Asigna a cada Modelo la imagen de la carpeta cuyo nombre sea "Marca - Modelo".'

    def add_arguments(self, parser):
        parser.add_argument('--carpeta', default=str(CARPETA_SEED),
                            help='Carpeta con los archivos (por defecto product/seed_data/car_models).')
        parser.add_argument('--dry-run', action='store_true', help='Muestra el emparejamiento sin guardar.')
        parser.add_argument('--forzar', action='store_true',
                            help='Reemplaza tambien la imagen de los modelos que ya tienen una.')
        parser.add_argument('--exportar-a', metavar='DIR',
                            help='No toca la BD: escribe en DIR los WEBP reducidos de --carpeta como "Marca - Modelo.webp".')

    def handle(self, *args, **options):
        carpeta = Path(options['carpeta'])
        if not carpeta.is_dir():
            raise CommandError(f'No existe la carpeta {carpeta}.')
        exportar = Path(options['exportar_a']) if options['exportar_a'] else None
        if exportar and not options['dry_run']:
            exportar.mkdir(parents=True, exist_ok=True)

        modelos = {_clave(f'{m.car_brand_id.name} - {m.name}'): m
                   for m in Car_Model.objects.select_related('car_brand_id')}
        archivos = sorted(f for f in carpeta.iterdir() if f.suffix.lower() in EXTENSIONES)
        usados, omitidos, sin_modelo, errores = set(), [], [], []
        hechos = 0

        for archivo in archivos:
            modelo = modelos.get(_clave(archivo.stem))
            if not modelo:
                sin_modelo.append(archivo.name)
                continue
            usados.add(modelo.pk)
            if not exportar and not options['forzar'] and _tiene_imagen_valida(modelo):
                omitidos.append(f'{modelo.car_brand_id.name} - {modelo.name}')
                continue
            try:
                data = reducir_a_webp(archivo.read_bytes())
            except (UnidentifiedImageError, OSError) as exc:
                errores.append(f'{archivo.name} ({exc.__class__.__name__})')
                continue
            if data is None:
                errores.append(f'{archivo.name} (no se pudo reducir al peso maximo)')
                continue
            self.stdout.write(f'{archivo.name} -> {modelo.pk} ({len(data) // 1024} KB)')
            hechos += 1
            if options['dry_run']:
                continue
            if exportar:
                (exportar / f'{modelo.car_brand_id.name.strip()} - {modelo.name.strip()}.webp').write_bytes(data)
                continue
            anterior = modelo.image.name if modelo.image else None
            modelo.image.save(f'{modelo.pk}.webp', ContentFile(data), save=False)
            modelo.save(update_fields=['image'])
            if anterior and anterior != modelo.image.name and modelo.image.storage.exists(anterior):
                modelo.image.storage.delete(anterior)

        verbo = 'exportadas' if exportar else 'importadas'
        if options['dry_run']:
            verbo = 'simuladas'
        self.stdout.write(self.style.SUCCESS(f'{hechos} imagen(es) {verbo}, {len(omitidos)} omitida(s) por tener ya imagen.'))
        faltantes = [f'{m.car_brand_id.name} - {m.name}' for m in modelos.values() if m.pk not in usados]
        for titulo, lista in (('Omitidos (ya tienen imagen; usa --forzar para reemplazar)', omitidos),
                              ('Archivos sin modelo', sin_modelo), ('Errores', errores),
                              ('Modelos sin archivo', faltantes)):
            if lista:
                self.stdout.write(self.style.WARNING(f'{titulo} ({len(lista)}):\n  ' + '\n  '.join(lista)))
