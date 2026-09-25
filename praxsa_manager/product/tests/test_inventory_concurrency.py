"""Test de concurrencia para TASK-011 (backlog #3, docs/integration-and-backlog.md).

Dos proformas compiten por el mismo stock de inventario, con stock exacto
para una sola operacion. Antes del fix (sin select_for_update en
reduce_inventory), las dos transacciones pueden leer el mismo `to_install`
antes de que cualquiera haga commit y ambas tienen exito -> sobreventa
(`to_install` termina negativo). Con `select_for_update()`, la segunda
transaccion debe esperar el lock, releer el stock ya actualizado, y fallar
correctamente con "no hay lamina disponible" en vez de sobrevender.

Usa TransactionTestCase (no TestCase) porque necesita dos conexiones de BD
reales ejecutando transacciones concurrentes de verdad -- TestCase envuelve
todo el test en una unica transaccion con savepoints, lo que no permite
simular dos transacciones independientes viendose (o no) entre si.
"""
import threading
from decimal import Decimal

from django.db import connection
from django.test import TransactionTestCase

from . import helpers
from ..business.proforma import Proforma_Business
from ..models import inventario as Inventario


class InventoryConcurrencyTestCase(TransactionTestCase):

    def setUp(self):
        self.user, _token = helpers.create_user_with_token()
        self.sucursal = helpers.create_sucursal(self.user)
        self.car_model = helpers.create_model()
        self.car_part = helpers.create_car_part()
        # width debe coincidir con el default de create_full_proforma (1.50)
        # para que validate_proforma_detail no rechace el detalle.
        helpers.create_car_model_part(car_model=self.car_model, car_part=self.car_part, width=Decimal('1.50'))
        self.window_film = helpers.create_window_film()
        reel = helpers.create_window_film_reel(window_film=self.window_film, width=Decimal('1.50'))

        # to_reduce en create_work_note = detalle.length * detalle.quantity =
        # 1.00 * 1 (defaults de create_full_proforma) = 1.00. Dejamos stock
        # exacto para UNA sola de las dos proformas.
        self.inventario = helpers.create_inventario(sucursal=self.sucursal, bobina=reel, to_install=Decimal('1.00'))

        self.header_a, _ = helpers.create_full_proforma(
            user=self.user, sucursal=self.sucursal, car_model=self.car_model,
            car_part=self.car_part, window_film=self.window_film,
        )
        self.header_b, _ = helpers.create_full_proforma(
            user=self.user, sucursal=self.sucursal, car_model=self.car_model,
            car_part=self.car_part, window_film=self.window_film,
        )

    def test_dos_create_work_note_concurrentes_no_sobrevenden_el_mismo_stock(self):
        barrier = threading.Barrier(2)
        results = {}

        def worker(key, header):
            try:
                barrier.wait(timeout=5)
                nota = Proforma_Business().create_work_note(proforma=header, responsable=self.user)
                results[key] = ('ok', nota)
            except Exception as e:
                results[key] = ('error', e)
            finally:
                connection.close()

        t1 = threading.Thread(target=worker, args=('a', self.header_a))
        t2 = threading.Thread(target=worker, args=('b', self.header_b))
        t1.start()
        t2.start()
        t1.join(timeout=15)
        t2.join(timeout=15)

        outcomes = {'a': results.get('a'), 'b': results.get('b')}
        successes = [o for o in outcomes.values() if o and o[0] == 'ok']
        failures = [o for o in outcomes.values() if o and o[0] == 'error']

        self.assertEqual(len(successes), 1, f'esperaba exactamente 1 exito, se obtuvo: {outcomes}')
        self.assertEqual(len(failures), 1, f'esperaba exactamente 1 fallo, se obtuvo: {outcomes}')
        self.assertIn('no hay lamina disponible', str(failures[0][1]))

        final = Inventario.objects.get(id=self.inventario.id)
        self.assertEqual(final.to_install, Decimal('0.00'))
        self.assertGreaterEqual(final.to_install, Decimal('0.00'))
