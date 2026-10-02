"""Exporta el catalogo de vehiculos (marcas, modelos, items y modelo-item) de la
BD actual a un JSON versionable que luego carga `inicializar_datos`
(ADR-despliegue-nuevo-servidor-inicializacion-db-inicializacion-datos-seed).

Herramienta de desarrollo: no escribe en la BD y no se ejecuta en el servidor. El
JSON referencia todo por nombre (nunca por id), esta ordenado para que dos
corridas sobre los mismos datos produzcan el mismo archivo, y guarda los
decimales como texto. Las imagenes de los modelos no se exportan: se cargan con
`importar_imagenes_modelos`."""
import json
from pathlib import Path

from django.core.management.base import BaseCommand

from product.models import Car_Brand, Car_Model, Car_Model_Part, Car_Part

SALIDA_POR_DEFECTO = Path(__file__).resolve().parents[2] / 'seed_data' / 'catalogo.json'


def construir_catalogo():
    """Devuelve (catalogo, omitidos): `omitidos` lista los modelo-item sin item."""
    marcas = [
        {'nombre': b.name, 'activo': b.is_active}
        for b in Car_Brand.objects.order_by('name')
    ]
    modelos = [
        {'marca': m.car_brand_id.name, 'nombre': m.name, 'activo': m.is_active}
        for m in Car_Model.objects.select_related('car_brand_id').order_by('car_brand_id__name', 'name')
    ]
    items = [
        {'nombre': p.name, 'activo': p.is_active}
        for p in Car_Part.objects.order_by('name')
    ]
    modelo_items = []
    omitidos = []
    relaciones = Car_Model_Part.objects.select_related('car_model_id', 'car_part_id').order_by(
        'car_model_id__name', 'car_part_id__name', 'id')
    for r in relaciones:
        if r.car_part_id is None:
            omitidos.append(f'{r.car_model_id.name} (modelo-item #{r.pk} sin item)')
            continue
        modelo_items.append({
            'modelo': r.car_model_id.name,
            'item': r.car_part_id.name,
            'ancho': str(r.width),
            'largo': str(r.length),
            'cantidad': r.quantity,
            'precio_instalacion': str(r.installation_price),
        })
    return {'marcas': marcas, 'modelos': modelos, 'items': items, 'modelo_items': modelo_items}, omitidos


class Command(BaseCommand):
    help = 'Exporta marcas, modelos, items y modelo-item de la BD a un JSON para el seed (solo desarrollo).'

    def add_arguments(self, parser):
        parser.add_argument('--salida', default=str(SALIDA_POR_DEFECTO),
                            help='Archivo JSON de salida (por defecto product/seed_data/catalogo.json).')

    def handle(self, *args, **options):
        catalogo, omitidos = construir_catalogo()
        salida = Path(options['salida'])
        salida.parent.mkdir(parents=True, exist_ok=True)
        # newline='\n': mismo archivo en Windows y Linux (diffs estables en git).
        with open(salida, 'w', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps(catalogo, ensure_ascii=False, indent=2) + '\n')
        self.stdout.write(
            f'Exportado a {salida}: {len(catalogo["marcas"])} marcas, {len(catalogo["modelos"])} modelos, '
            f'{len(catalogo["items"])} items, {len(catalogo["modelo_items"])} modelo-item.'
        )
        if omitidos:
            self.stdout.write(self.style.WARNING(f'Omitidos ({len(omitidos)}):'))
            for o in omitidos:
                self.stdout.write(f'  - {o}')
