"""Comando precargar_imagenes_modelos (sin red: la API de Wikimedia se simula)."""
import io
import os
import shutil
import tempfile
from io import StringIO
from unittest import mock

from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from PIL import Image

from ..helper.imagenes import MAX_BYTES, MAX_WIDTH, MIN_WIDTH
from ..models import Car_Brand, Car_Model

MEDIA = tempfile.mkdtemp()


def _jpeg(width=1600, height=900):
    buf = io.BytesIO()
    Image.effect_noise((width, height), 60).convert('RGB').save(buf, 'JPEG', quality=90)
    return buf.getvalue()


def _pagina(title, width=2000, height=1200, mime='image/jpeg', license='CC BY-SA 4.0'):
    return {'title': title, 'imageinfo': [{
        'width': width, 'height': height, 'mime': mime, 'url': 'http://x/o.jpg', 'thumburl': 'http://x/t.jpg',
        'descriptionurl': 'http://x/page',
        'extmetadata': {'LicenseShortName': {'value': license}, 'Artist': {'value': '<a>Juan</a>'}}}]}


class FakeSession:
    def __init__(self, pages, image=None):
        self.headers = {}
        self.pages, self.image = pages, image or _jpeg()

    def get(self, url, **kwargs):
        resp = mock.Mock(content=self.image)
        resp.json.return_value = {'query': {'pages': dict(enumerate(self.pages))}}
        return resp


@override_settings(MEDIA_ROOT=MEDIA)
class PrecargarImagenesModelosTest(TestCase):

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        marca = Car_Brand.objects.create(name='Toyota')
        self.hilux = Car_Model.objects.create(car_brand_id=marca, name='Hilux')
        self.report = os.path.join(MEDIA, 'r.csv')

    def correr(self, pages, **kw):
        with mock.patch('requests.Session', return_value=FakeSession(pages, **kw)):
            out = StringIO()
            call_command('precargar_imagenes_modelos', report=self.report, delay=0, stdout=out)
        self.hilux.refresh_from_db()
        return out.getvalue()

    def test_guarda_imagen_webp_dentro_de_limites(self):
        self.correr([_pagina('File:Toyota Hilux 2020.jpg')])
        self.assertTrue(self.hilux.image)
        self.assertLessEqual(self.hilux.image.size, MAX_BYTES)
        with Image.open(self.hilux.image) as img:
            self.assertEqual(img.format, 'WEBP')
            self.assertTrue(MIN_WIDTH <= img.width <= MAX_WIDTH)

    def test_descarta_licencia_no_libre_pequena_vertical_o_de_otro_modelo(self):
        self.correr([
            _pagina('File:Toyota Hilux a.jpg', license='All rights reserved'),
            _pagina('File:Toyota Hilux b.jpg', width=300, height=200),
            _pagina('File:Toyota Hilux c.jpg', width=900, height=1400),
            _pagina('File:Toyota Corolla.jpg'),
            _pagina('File:Toyota Hilux.svg', mime='image/svg+xml'),
        ])
        self.assertFalse(self.hilux.image)

    def test_descarta_fotos_de_interior_motor_logo(self):
        self.correr([_pagina('File:Toyota Hilux interior.jpg')])
        self.assertFalse(self.hilux.image)

    def test_procesa_modelos_con_image_null(self):
        Car_Model.objects.filter(pk=self.hilux.pk).update(image=None)
        self.correr([_pagina('File:Toyota Hilux 2020.jpg')])
        self.assertTrue(self.hilux.image)

    def test_no_pisa_imagen_existente(self):
        self.hilux.image.save('a.webp', ContentFile(b'x'))
        previo = self.hilux.image.name
        self.correr([_pagina('File:Toyota Hilux.jpg')])
        self.assertEqual(self.hilux.image.name, previo)

    def test_dry_run_no_guarda(self):
        with mock.patch('requests.Session', return_value=FakeSession([_pagina('File:Toyota Hilux.jpg')])):
            call_command('precargar_imagenes_modelos', report=self.report, delay=0, dry_run=True, stdout=StringIO())
        self.hilux.refresh_from_db()
        self.assertFalse(self.hilux.image)
        with open(self.report, encoding='utf-8-sig') as fh:
            self.assertIn('simulada', fh.read())
