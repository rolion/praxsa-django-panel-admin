"""Comando importar_imagenes_modelos: empareja "Marca - Modelo.<ext>" con el Car_Model."""
import io
import shutil
import tempfile
from io import StringIO
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from PIL import Image

from ..helper.imagenes import MAX_BYTES, MAX_WIDTH, MIN_WIDTH, reducir_a_webp
from ..management.commands.importar_imagenes_modelos import CARPETA_SEED
from ..models import Car_Brand, Car_Model

MEDIA = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA)
class ImportarImagenesModelosTest(TestCase):

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        marca = Car_Brand.objects.create(name='CHERY')
        self.qq = Car_Model.objects.create(car_brand_id=marca, name='QQ')
        self.otro = Car_Model.objects.create(car_brand_id=marca, name='Tiggo')
        self.carpeta = Path(tempfile.mkdtemp(dir=MEDIA))

    def archivo(self, nombre, fmt='JPEG', size=(2400, 1350), modo='RGB'):
        buf = io.BytesIO()
        Image.effect_noise(size, 60).convert(modo).save(buf, fmt)
        (self.carpeta / nombre).write_bytes(buf.getvalue())

    def correr(self, **kw):
        out = StringIO()
        call_command('importar_imagenes_modelos', carpeta=str(self.carpeta), stdout=out, **kw)
        return out.getvalue()

    def test_empareja_tolerando_espacios_y_mayusculas_y_reduce(self):
        self.archivo('chery -qq.jfif')
        salida = self.correr()
        self.qq.refresh_from_db()
        self.assertTrue(self.qq.image)
        self.assertLessEqual(self.qq.image.size, MAX_BYTES)
        with Image.open(self.qq.image) as img:
            self.assertEqual((img.format, img.width <= MAX_WIDTH), ('WEBP', True))
        self.assertIn('CHERY - Tiggo', salida)  # reportado como modelo sin archivo

    def test_archivo_sin_modelo_se_reporta_y_dry_run_no_guarda(self):
        self.archivo('CHERY - Inexistente.png', 'PNG')
        self.archivo('CHERY - QQ.png', 'PNG')
        salida = self.correr(dry_run=True)
        self.qq.refresh_from_db()
        self.assertFalse(self.qq.image)
        self.assertIn('CHERY - Inexistente.png', salida)

    def test_conserva_transparencia(self):
        img = Image.effect_noise((1200, 700), 60).convert('RGBA')
        img.paste((0, 0, 0, 0), (0, 0, 600, 700))  # mitad transparente
        img.save(self.carpeta / 'CHERY - QQ.png')
        self.correr()
        self.qq.refresh_from_db()
        with Image.open(self.qq.image) as img:
            self.assertIn('A', img.getbands())

    def test_carpeta_por_defecto_es_el_seed_versionado(self):
        self.assertEqual(CARPETA_SEED.parts[-3:], ('product', 'seed_data', 'car_models'))
        self.assertTrue(CARPETA_SEED.is_dir())

    def test_no_pisa_imagen_existente_por_defecto(self):
        self.qq.image.save('subida.webp', ContentFile(b'x'))
        previo = self.qq.image.name
        self.archivo('CHERY - QQ.png', 'PNG')
        salida = self.correr()
        self.qq.refresh_from_db()
        self.assertEqual(self.qq.image.name, previo)
        self.assertIn('Omitidos', salida)

    def test_asigna_si_el_archivo_de_la_imagen_ya_no_existe(self):
        Car_Model.objects.filter(pk=self.qq.pk).update(image='car_models/inexistente.webp')
        self.archivo('CHERY - QQ.png', 'PNG')
        self.correr()
        self.qq.refresh_from_db()
        self.assertNotEqual(self.qq.image.name, 'car_models/inexistente.webp')
        self.assertTrue(self.qq.image.storage.exists(self.qq.image.name))

    def test_forzar_reemplaza_y_borra_la_anterior(self):
        self.qq.image.save('subida.webp', ContentFile(b'x'))
        anterior = self.qq.image.name
        self.archivo('CHERY - QQ.png', 'PNG')
        self.correr(forzar=True)
        self.qq.refresh_from_db()
        self.assertNotEqual(self.qq.image.name, anterior)
        self.assertFalse(self.qq.image.storage.exists(anterior))
        self.assertTrue(self.qq.image.storage.exists(self.qq.image.name))

    def test_exportar_a_escribe_webp_reducidos_sin_tocar_la_bd(self):
        self.archivo('chery -qq.jfif')
        destino = Path(tempfile.mkdtemp(dir=MEDIA)) / 'salida'
        self.correr(exportar_a=str(destino))
        self.qq.refresh_from_db()
        self.assertFalse(self.qq.image)
        archivo = destino / 'CHERY - QQ.webp'
        self.assertTrue(archivo.exists())
        self.assertLessEqual(archivo.stat().st_size, MAX_BYTES)


class ReducirAWebpTest(TestCase):

    def _bytes(self, size, fmt='JPEG'):
        buf = io.BytesIO()
        Image.effect_noise(size, 60).convert('RGB').save(buf, fmt)
        return buf.getvalue()

    def test_respeta_peso_y_ancho(self):
        data = reducir_a_webp(self._bytes((3000, 1700)))
        self.assertLessEqual(len(data), MAX_BYTES)
        with Image.open(io.BytesIO(data)) as img:
            self.assertTrue(MIN_WIDTH <= img.width <= MAX_WIDTH)

    def test_imagen_demasiado_chica_devuelve_none(self):
        self.assertIsNone(reducir_a_webp(self._bytes((300, 200))))

    def test_archivo_que_no_es_imagen_lanza_error(self):
        with self.assertRaises(OSError):
            reducir_a_webp(b'no soy una imagen')
