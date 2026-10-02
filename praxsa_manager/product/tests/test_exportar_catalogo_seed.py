"""Comando exportar_catalogo_seed (TASK-despliegue-nuevo-servidor-inicializacion-db)."""
import json
import shutil
import tempfile
from decimal import Decimal
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase

from ..models import Car_Brand, Car_Model, Car_Model_Part, Car_Part


class ExportarCatalogoSeedTest(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dir = tempfile.mkdtemp()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(cls.dir, ignore_errors=True)

    def setUp(self):
        self.salida = Path(self.dir) / 'catalogo.json'
        chery = Car_Brand.objects.create(name='CHERY')
        audi = Car_Brand.objects.create(name='Audi', is_active=False)
        self.qq = Car_Model.objects.create(car_brand_id=chery, name='QQ')
        self.a1 = Car_Model.objects.create(car_brand_id=audi, name='A1', is_active=False)
        self.parabrisas = Car_Part.objects.create(name='Parabrisas')
        Car_Part.objects.create(name='Luneta')
        Car_Model_Part.objects.create(car_model_id=self.qq, car_part_id=self.parabrisas, width=Decimal('0.70'),
                                      length=Decimal('1.00'), quantity=2, installation_price=Decimal('50.00'))

    def exportar(self):
        out = StringIO()
        call_command('exportar_catalogo_seed', '--salida', str(self.salida), stdout=out)
        return out.getvalue()

    def test_exporta_por_nombres_ordenado_y_con_decimales_como_texto(self):
        self.exportar()
        data = json.loads(self.salida.read_text(encoding='utf-8'))
        self.assertEqual(data['marcas'], [{'nombre': 'Audi', 'activo': False}, {'nombre': 'CHERY', 'activo': True}])
        self.assertEqual(data['modelos'], [{'marca': 'Audi', 'nombre': 'A1', 'activo': False},
                                           {'marca': 'CHERY', 'nombre': 'QQ', 'activo': True}])
        self.assertEqual([i['nombre'] for i in data['items']], ['Luneta', 'Parabrisas'])
        self.assertEqual(data['modelo_items'], [{'modelo': 'QQ', 'item': 'Parabrisas', 'ancho': '0.70',
                                                 'largo': '1.00', 'cantidad': 2, 'precio_instalacion': '50.00'}])

    def test_dos_corridas_producen_el_mismo_archivo(self):
        self.exportar()
        primero = self.salida.read_bytes()
        self.exportar()
        self.assertEqual(self.salida.read_bytes(), primero)
        self.assertNotIn(b'\r', primero)

    def test_omite_y_reporta_modelo_item_sin_item(self):
        Car_Model_Part.objects.create(car_model_id=self.a1, car_part_id=None)
        salida = self.exportar()
        data = json.loads(self.salida.read_text(encoding='utf-8'))
        self.assertEqual(len(data['modelo_items']), 1)
        self.assertIn('Omitidos (1)', salida)
        self.assertIn('A1', salida)

    def test_no_escribe_en_la_base(self):
        antes = (Car_Brand.objects.count(), Car_Model.objects.count(), Car_Part.objects.count(),
                 Car_Model_Part.objects.count())
        self.exportar()
        self.assertEqual(antes, (Car_Brand.objects.count(), Car_Model.objects.count(), Car_Part.objects.count(),
                                 Car_Model_Part.objects.count()))
