"""Precarga la imagen de los Modelos de vehiculo (`Car_Model.image`) desde
Wikimedia Commons (fotos con licencia libre).

Solo toca modelos activos SIN imagen; nunca pisa una imagen existente. Cada foto
se redimensiona y se reencoda a WEBP para quedar liviana pero no diminuta
(ver product/helper/imagenes.py). Deja un CSV con la
fuente, autor y licencia de cada foto usada, y con los modelos que no se
encontraron para completarlos a mano desde el admin. Idempotente: se puede
correr por tandas (`--limit`) o repetir para reintentar los que faltaron."""
import csv
import re
import time

import requests
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db.models import Q
from PIL import UnidentifiedImageError

from product.helper.imagenes import MAX_WIDTH, reducir_a_webp
from product.models import Car_Model

API_URL = 'https://commons.wikimedia.org/w/api.php'
# Wikimedia exige un User-Agent identificable.
USER_AGENT = 'PraxsaPanelAdmin/1.0 (precarga de imagenes de modelos; roleonm@gmail.com)'
MIN_SOURCE_WIDTH = 800     # foto original: descarta miniaturas/logos
ALLOWED_MIMES = {'image/jpeg', 'image/png', 'image/webp'}
FREE_LICENSE = re.compile(r'^(cc[ -]|public domain|pd|gfdl)', re.I)
NOISE_TITLE = re.compile(r'interior|engine|motor|dashboard|logo|badge|emblem|wheel|diagram|map|cutaway|detail', re.I)


def _tokens(text):
    return [t for t in re.split(r'[^a-z0-9]+', text.lower()) if t]


def _plain(value):
    return re.sub(r'<[^>]+>', '', value or '').strip()


class Command(BaseCommand):
    help = 'Descarga desde Wikimedia Commons la imagen de los modelos activos que no tienen una.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=0, help='Maximo de modelos a procesar (0 = todos).')
        parser.add_argument('--brand', help='Procesa solo la marca indicada (nombre exacto, sin distinguir mayusculas).')
        parser.add_argument('--dry-run', action='store_true', help='Busca y reporta, pero no guarda imagenes.')
        parser.add_argument('--report', default='precarga_imagenes_modelos.csv', help='Ruta del CSV de resultados.')
        parser.add_argument('--delay', type=float, default=1.0, help='Segundos de espera entre modelos (cortesia a la API).')

    def handle(self, *args, **options):
        # `image` es nullable: las filas viejas tienen NULL, las nuevas sin foto ''.
        qs = (Car_Model.objects.filter(is_active=True).filter(Q(image='') | Q(image__isnull=True))
              .select_related('car_brand_id').order_by('car_brand_id__name', 'name'))
        if options['brand']:
            qs = qs.filter(car_brand_id__name__iexact=options['brand'])
        if options['limit']:
            qs = qs[:options['limit']]

        session = requests.Session()
        session.headers['User-Agent'] = USER_AGENT
        rows, found = [], 0
        modelos = list(qs)
        self.stdout.write(f'{len(modelos)} modelo(s) sin imagen a procesar.')

        for i, modelo in enumerate(modelos, 1):
            marca = modelo.car_brand_id.name
            resultado = self._procesar(session, modelo, marca, options['dry_run'])
            found += resultado['estado'] != 'no_encontrada'
            rows.append(resultado)
            self.stdout.write(f"[{i}/{len(modelos)}] {marca} {modelo.name}: {resultado['estado']}")
            time.sleep(options['delay'])

        with open(options['report'], 'w', newline='', encoding='utf-8-sig') as fh:
            writer = csv.DictWriter(fh, fieldnames=['marca', 'modelo', 'estado', 'bytes', 'archivo_origen', 'autor', 'licencia', 'url_pagina'])
            writer.writeheader()
            writer.writerows(rows)
        self.stdout.write(self.style.SUCCESS(
            f'Listo: {found} con imagen, {len(modelos) - found} sin encontrar. Reporte: {options["report"]}'))

    def _procesar(self, session, modelo, marca, dry_run):
        base = {'marca': marca, 'modelo': modelo.name, 'bytes': '', 'archivo_origen': '',
                'autor': '', 'licencia': '', 'url_pagina': ''}
        try:
            candidato = self._buscar(session, marca, modelo.name)
            if not candidato:
                return {**base, 'estado': 'no_encontrada'}
            data = self._preparar(session, candidato['thumburl'])
        except (requests.RequestException, UnidentifiedImageError, OSError, ValueError) as exc:
            return {**base, 'estado': f'error: {exc.__class__.__name__}'}
        if data is None:
            return {**base, 'estado': 'no_encontrada'}

        if not dry_run:
            modelo.image.save(f'{modelo.pk}.webp', ContentFile(data), save=False)
            modelo.save(update_fields=['image'])
        return {**base, 'estado': 'simulada' if dry_run else 'guardada', 'bytes': len(data),
                'archivo_origen': candidato['title'], 'autor': candidato['author'],
                'licencia': candidato['license'], 'url_pagina': candidato['page']}

    def _buscar(self, session, marca, nombre):
        """Mejor foto libre de Commons para marca+modelo, o None."""
        params = {
            'action': 'query', 'format': 'json', 'generator': 'search', 'gsrnamespace': 6,
            'gsrsearch': f'{marca} {nombre} filetype:bitmap', 'gsrlimit': 20,
            'prop': 'imageinfo', 'iiprop': 'url|size|mime|extmetadata', 'iiurlwidth': MAX_WIDTH,
        }
        resp = session.get(API_URL, params=params, timeout=20)
        resp.raise_for_status()
        paginas = (resp.json().get('query') or {}).get('pages', {}).values()

        # Sin años sueltos ('320i - 1987'): el titulo los trae antes del nombre.
        frase = ' '.join(t for t in _tokens(nombre) if not re.fullmatch(r'(19|20)\d\d', t))
        requeridos = _tokens(nombre) + _tokens(marca)
        mejor, mejor_score = None, 0
        for pagina in paginas:
            info = (pagina.get('imageinfo') or [None])[0]
            if not info or info.get('mime') not in ALLOWED_MIMES:
                continue
            if info['width'] < MIN_SOURCE_WIDTH or info['width'] < info['height']:
                continue  # chica, o vertical (no sirve para tarjeta del modelo)
            meta = info.get('extmetadata') or {}
            licencia = _plain((meta.get('LicenseShortName') or {}).get('value'))
            if not FREE_LICENSE.match(licencia):
                continue
            titulo = pagina['title']
            titulo_tokens = set(_tokens(titulo))
            if f' {frase} ' not in f" {' '.join(_tokens(titulo))} ":
                continue  # el titulo debe contener el nombre del modelo completo y contiguo
            score = sum(t in titulo_tokens for t in requeridos)
            score -= 3 if NOISE_TITLE.search(titulo) else 0
            if score > mejor_score:
                mejor_score = score
                mejor = {'title': titulo, 'thumburl': info.get('thumburl') or info['url'],
                         'page': info.get('descriptionurl', ''), 'license': licencia,
                         'author': _plain((meta.get('Artist') or {}).get('value'))}
        return mejor

    def _preparar(self, session, url):
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        return reducir_a_webp(resp.content)
