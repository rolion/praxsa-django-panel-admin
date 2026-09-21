"""Tests para el ítem #5 del backlog (TASK-002): get_inventory/get_layer_info
siguen públicos con throttling; get_bobina se cierra a staff."""
from django.core.cache import cache
from django.test import TestCase, override_settings

from . import helpers


class GetInventoryEndpointTest(TestCase):
    def test_get_inventory_returns_200_and_current_shape_without_auth(self):
        scenario = helpers.build_full_scenario()
        sucursal = scenario['sucursal']
        window_film = scenario['window_film']

        response = self.client.get(
            f"/product/get_inventory/{sucursal.id}/{window_film.id}/1.50"
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('inventario', data)
        self.assertEqual(len(data['inventario']), 1)
        row = data['inventario'][0]
        for key in (
            'bobina_film_name',
            'bobina_film_id',
            'bobina_width',
            'bobina_metros_disponibles',
            'bobina_price',
            'bobina_id',
        ):
            self.assertIn(key, row)
        self.assertEqual(row['bobina_film_name'], window_film.name)


class GetLayerInfoEndpointTest(TestCase):
    def test_get_layer_info_returns_200_and_current_shape_without_auth(self):
        window_film = helpers.create_window_film()

        response = self.client.get(f"/product/layer/{window_film.id}")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('layer', data)
        self.assertEqual(data['layer']['name'], window_film.name)
        self.assertIn('content', data['layer'])


@override_settings(REST_FRAMEWORK={
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly'
    ],
    'DEFAULT_THROTTLE_RATES': {'public_catalog': '2/min'},
})
class PublicCatalogThrottleTest(TestCase):
    """Tasa baja vía override_settings para que el test sea rápido y determinístico
    (ver PLAN-2026-09-21-public-endpoints-protection.md, Test strategy)."""

    def setUp(self):
        cache.clear()
        # SimpleRateThrottle.THROTTLE_RATES se resuelve una sola vez al importar
        # el módulo (no reacciona a la señal setting_changed de override_settings),
        # así que se fuerza la relectura para que la tasa baja de este test aplique.
        from rest_framework.throttling import SimpleRateThrottle
        from rest_framework.settings import api_settings
        api_settings.reload()
        SimpleRateThrottle.THROTTLE_RATES = api_settings.DEFAULT_THROTTLE_RATES

    def tearDown(self):
        cache.clear()
        from rest_framework.throttling import SimpleRateThrottle
        from rest_framework.settings import api_settings
        api_settings.reload()
        SimpleRateThrottle.THROTTLE_RATES = api_settings.DEFAULT_THROTTLE_RATES

    def test_get_inventory_returns_429_after_exceeding_rate(self):
        scenario = helpers.build_full_scenario()
        url = f"/product/get_inventory/{scenario['sucursal'].id}/{scenario['window_film'].id}/1.50"

        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.get(url).status_code, 200)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 429)

    def test_get_layer_info_returns_429_after_exceeding_rate(self):
        window_film = helpers.create_window_film()
        url = f"/product/layer/{window_film.id}"

        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.get(url).status_code, 200)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 429)


class GetBobinaEndpointTest(TestCase):
    def test_get_bobina_returns_403_for_anonymous_user(self):
        reel = helpers.create_window_film_reel()

        response = self.client.get(f"/product/bobina/{reel.id}")

        self.assertEqual(response.status_code, 403)

    def test_get_bobina_returns_403_for_authenticated_non_staff_user(self):
        user, password = helpers.create_staff_user()
        user.is_staff = False
        user.save()
        reel = helpers.create_window_film_reel()

        self.client.login(username=user.username, password=password)
        response = self.client.get(f"/product/bobina/{reel.id}")

        self.assertEqual(response.status_code, 403)

    def test_get_bobina_returns_200_and_current_shape_for_staff_user(self):
        user, password = helpers.create_staff_user()
        reel = helpers.create_window_film_reel()

        self.client.login(username=user.username, password=password)
        response = self.client.get(f"/product/bobina/{reel.id}")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('bobina', data)
        self.assertEqual(data['bobina']['window_film'], reel.window_film.id)
        self.assertIn('width', data['bobina'])
        self.assertIn('length', data['bobina'])
        self.assertIn('price', data['bobina'])
