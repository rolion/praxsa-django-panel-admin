"""Tests del modulo de Vehiculos (TASK-modulo-vehiculos): Marcas, Modelos e
Items sobre los modelos ya existentes Car_Brand/Car_Model/Car_Part/
Car_Model_Part, que hasta este task solo se administraban por Django Admin.

Ver ADR-modulo-vehiculos-relacion-modelo-item, ADR-modulo-vehiculos-soft-delete
y ADR-modulo-vehiculos-almacenamiento-imagenes.
"""
import io
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test.client import BOUNDARY, encode_multipart
from PIL import Image

from ..models import Car_Brand, Car_Model, Car_Model_Part, Car_Part
from . import helpers


def _auth_headers(token):
    return {'HTTP_AUTHORIZATION': f'Token {token.key}'}


def _make_image_file(name='vehiculo.jpg', image_format='JPEG', size=(10, 10), content_type='image/jpeg'):
    buffer = io.BytesIO()
    Image.new('RGB', size, color='red').save(buffer, format=image_format)
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.read(), content_type=content_type)


def _patch_multipart(client, url, data, **extra):
    """self.client.patch() usa 'application/octet-stream' como content_type
    por defecto (a diferencia de post(), que auto-detecta multipart) -- hay
    que codificar el multipart a mano para poder mandar un archivo en un PATCH."""
    encoded = encode_multipart(BOUNDARY, data)
    return client.patch(url, encoded, content_type=f'multipart/form-data; boundary={BOUNDARY}', **extra)


class CarBrandTest(TestCase):
    def test_create_brand(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'add_car_brand')

        response = self.client.post(
            '/product/vehicles/brands',
            {'name': 'Toyota'},
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 201, response.content)
        self.assertTrue(Car_Brand.objects.filter(name='Toyota').exists())

    def test_create_duplicate_name_returns_400(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'add_car_brand')
        helpers.create_brand(name='Toyota')

        response = self.client.post(
            '/product/vehicles/brands',
            {'name': 'Toyota'},
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('name', response.json())

    def test_edit_brand(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'change_car_brand')
        brand = helpers.create_brand(name='Toyota')

        response = self.client.patch(
            f'/product/vehicles/brands/{brand.id}/',
            {'name': 'Toyota Motors'},
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 200, response.content)
        brand.refresh_from_db()
        self.assertEqual(brand.name, 'Toyota Motors')

    def test_view_brand_includes_models_count(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        brand = helpers.create_brand()
        helpers.create_model(brand=brand)
        helpers.create_model(brand=brand)

        response = self.client.get(f'/product/vehicles/brands/{brand.id}/', **_auth_headers(token))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['models_count'], 2)

    def test_list_hides_inactive_brands_by_default(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        active = helpers.create_brand(name='Activa')
        inactive = helpers.create_brand(name='Inactiva')
        inactive.is_active = False
        inactive.save(update_fields=['is_active'])

        response = self.client.get('/product/vehicles/brands', **_auth_headers(token))

        self.assertEqual(response.status_code, 200)
        names = [row['name'] for row in response.json()]
        self.assertIn('Activa', names)
        self.assertNotIn('Inactiva', names)

    def test_list_include_inactive_shows_them(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        inactive = helpers.create_brand(name='Inactiva')
        inactive.is_active = False
        inactive.save(update_fields=['is_active'])

        response = self.client.get('/product/vehicles/brands?include_inactive=true', **_auth_headers(token))

        names = [row['name'] for row in response.json()]
        self.assertIn('Inactiva', names)

    def test_search_by_name(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.create_brand(name='Toyota')
        helpers.create_brand(name='Nissan')

        response = self.client.get('/product/vehicles/brands?search=toy', **_auth_headers(token))

        names = [row['name'] for row in response.json()]
        self.assertEqual(names, ['Toyota'])

    def test_toggle_active_soft_deletes(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'change_car_brand')
        brand = helpers.create_brand()

        response = self.client.patch(
            f'/product/vehicles/brands/{brand.id}/toggle-active/',
            {'is_active': False},
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 200)
        brand.refresh_from_db()
        self.assertFalse(brand.is_active)

    def test_inactive_brand_not_offered_as_choice_for_new_model(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'add_car_model')
        brand = helpers.create_brand()
        brand.is_active = False
        brand.save(update_fields=['is_active'])

        response = self.client.post(
            '/product/vehicles/models',
            {'name': 'Corolla', 'car_brand_id': brand.id},
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('car_brand_id', response.json())

    def test_create_without_permission_is_forbidden(self):
        _, token, _ = helpers.create_staff_user_with_token()

        response = self.client.post(
            '/product/vehicles/brands',
            {'name': 'Toyota'},
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 403)

    def test_non_staff_user_cannot_reach_endpoint(self):
        _, token, _ = helpers.create_staff_user_with_token(is_staff=False)

        response = self.client.get('/product/vehicles/brands', **_auth_headers(token))

        self.assertEqual(response.status_code, 403)


class CarPartTest(TestCase):
    def test_create_part(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'add_car_part')

        response = self.client.post(
            '/product/vehicles/parts',
            {'name': 'Parabrisas delantero'},
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 201, response.content)
        self.assertTrue(Car_Part.objects.filter(name='Parabrisas delantero').exists())

    def test_edit_part(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'change_car_part')
        part = helpers.create_car_part(name='Ventana')

        response = self.client.patch(
            f'/product/vehicles/parts/{part.id}/',
            {'name': 'Ventana lateral'},
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 200, response.content)
        part.refresh_from_db()
        self.assertEqual(part.name, 'Ventana lateral')

    def test_view_part(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        part = helpers.create_car_part(name='Luneta trasera')

        response = self.client.get(f'/product/vehicles/parts/{part.id}/', **_auth_headers(token))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['name'], 'Luneta trasera')

    def test_list_hides_inactive_parts_by_default(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        active = helpers.create_car_part(name='Activo')
        inactive = helpers.create_car_part(name='Inactivo')
        inactive.is_active = False
        inactive.save(update_fields=['is_active'])

        response = self.client.get('/product/vehicles/parts', **_auth_headers(token))

        names = [row['name'] for row in response.json()]
        self.assertIn('Activo', names)
        self.assertNotIn('Inactivo', names)

    def test_search_by_name(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.create_car_part(name='Parabrisas delantero')
        helpers.create_car_part(name='Ventana lateral')

        response = self.client.get('/product/vehicles/parts?search=parabrisas', **_auth_headers(token))

        names = [row['name'] for row in response.json()]
        self.assertEqual(names, ['Parabrisas delantero'])

    def test_toggle_active_soft_deletes(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'change_car_part')
        part = helpers.create_car_part()

        response = self.client.patch(
            f'/product/vehicles/parts/{part.id}/toggle-active/',
            {'is_active': False},
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 200)
        part.refresh_from_db()
        self.assertFalse(part.is_active)


class CarModelTest(TestCase):
    def test_create_model_with_brand(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'add_car_model')
        brand = helpers.create_brand()

        response = self.client.post(
            '/product/vehicles/models',
            {'name': 'Corolla', 'car_brand_id': brand.id},
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 201, response.content)
        created = Car_Model.objects.get(name='Corolla')
        self.assertEqual(created.car_brand_id_id, brand.id)

    def test_brand_is_required(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'add_car_model')

        response = self.client.post(
            '/product/vehicles/models',
            {'name': 'Corolla'},
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('car_brand_id', response.json())

    def test_duplicate_model_name_returns_400(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'add_car_model')
        brand = helpers.create_brand()
        helpers.create_model(brand=brand, name='Corolla')

        response = self.client.post(
            '/product/vehicles/models',
            {'name': 'Corolla', 'car_brand_id': brand.id},
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('name', response.json())

    def test_edit_model(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'change_car_model')
        brand = helpers.create_brand()
        car_model = helpers.create_model(brand=brand, name='Corolla')

        response = self.client.patch(
            f'/product/vehicles/models/{car_model.id}/',
            {'name': 'Corolla XLI'},
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 200, response.content)
        car_model.refresh_from_db()
        self.assertEqual(car_model.name, 'Corolla XLI')

    def test_view_model_includes_brand_name_and_items_count(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        brand = helpers.create_brand(name='Toyota')
        car_model = helpers.create_model(brand=brand, name='Corolla')
        helpers.create_car_model_part(car_model=car_model)

        response = self.client.get(f'/product/vehicles/models/{car_model.id}/', **_auth_headers(token))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['car_brand_name'], 'Toyota')
        self.assertEqual(data['items_count'], 1)

    def test_toggle_active_soft_deletes(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'change_car_model')
        car_model = helpers.create_model()

        response = self.client.patch(
            f'/product/vehicles/models/{car_model.id}/toggle-active/',
            {'is_active': False},
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 200)
        car_model.refresh_from_db()
        self.assertFalse(car_model.is_active)

    def test_search_by_model_name(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        brand = helpers.create_brand(name='Toyota')
        helpers.create_model(brand=brand, name='Corolla')
        helpers.create_model(brand=brand, name='Hilux')

        response = self.client.get('/product/vehicles/models?search=corolla', **_auth_headers(token))

        names = [row['name'] for row in response.json()]
        self.assertEqual(names, ['Corolla'])

    def test_search_by_brand_name(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        toyota = helpers.create_brand(name='Toyota')
        nissan = helpers.create_brand(name='Nissan')
        helpers.create_model(brand=toyota, name='Corolla')
        helpers.create_model(brand=nissan, name='Sentra')

        response = self.client.get('/product/vehicles/models?search=toyota', **_auth_headers(token))

        names = [row['name'] for row in response.json()]
        self.assertEqual(names, ['Corolla'])

    def test_filter_by_brand(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        toyota = helpers.create_brand(name='Toyota')
        nissan = helpers.create_brand(name='Nissan')
        helpers.create_model(brand=toyota, name='Corolla')
        helpers.create_model(brand=nissan, name='Sentra')

        response = self.client.get(f'/product/vehicles/models?car_brand_id={toyota.id}', **_auth_headers(token))

        names = [row['name'] for row in response.json()]
        self.assertEqual(names, ['Corolla'])


class CarModelImageTest(TestCase):
    def test_create_with_valid_image(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'add_car_model')
        brand = helpers.create_brand()

        response = self.client.post(
            '/product/vehicles/models',
            {'name': 'Corolla', 'car_brand_id': brand.id, 'image': _make_image_file()},
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 201, response.content)
        created = Car_Model.objects.get(name='Corolla')
        self.assertTrue(created.image)
        self.assertTrue(response.json()['image'].startswith('http'))

    def test_create_without_image_is_valid(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'add_car_model')
        brand = helpers.create_brand()

        response = self.client.post(
            '/product/vehicles/models',
            {'name': 'Corolla', 'car_brand_id': brand.id},
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 201, response.content)
        self.assertIsNone(response.json()['image'])

    def test_invalid_image_format_returns_400(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'add_car_model')
        brand = helpers.create_brand()
        fake_image = SimpleUploadedFile('nota.jpg', b'no soy una imagen de verdad', content_type='image/jpeg')

        response = self.client.post(
            '/product/vehicles/models',
            {'name': 'Corolla', 'car_brand_id': brand.id, 'image': fake_image},
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('image', response.json())
        self.assertFalse(Car_Model.objects.filter(name='Corolla').exists())

    def test_image_too_large_returns_400(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'add_car_model')
        brand = helpers.create_brand()
        big_image = SimpleUploadedFile('grande.jpg', b'0' * (6 * 1024 * 1024), content_type='image/jpeg')

        response = self.client.post(
            '/product/vehicles/models',
            {'name': 'Corolla', 'car_brand_id': brand.id, 'image': big_image},
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('image', response.json())

    def test_replace_image_deletes_previous_file(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'change_car_model')
        brand = helpers.create_brand()
        car_model = helpers.create_model(brand=brand)
        car_model.image.save('original.jpg', _make_image_file(), save=True)
        original_path = car_model.image.path
        self.assertTrue(car_model.image.storage.exists(original_path))

        response = _patch_multipart(
            self.client,
            f'/product/vehicles/models/{car_model.id}/',
            {'image': _make_image_file(name='nuevo.jpg')},
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(car_model.image.storage.exists(original_path))
        car_model.refresh_from_db()
        self.assertIn('nuevo', car_model.image.name)
        car_model.image.delete(save=False)

    def test_remove_image(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'change_car_model')
        brand = helpers.create_brand()
        car_model = helpers.create_model(brand=brand)
        car_model.image.save('original.jpg', _make_image_file(), save=True)

        response = self.client.patch(
            f'/product/vehicles/models/{car_model.id}/',
            {'image': None},
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 200, response.content)
        car_model.refresh_from_db()
        self.assertFalse(car_model.image)


class CarModelItemsAssociationTest(TestCase):
    def test_add_existing_item_to_model(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'add_car_model_part')
        car_model = helpers.create_model()
        car_part = helpers.create_car_part(name='Parabrisas')

        response = self.client.post(
            f'/product/vehicles/models/{car_model.id}/items/',
            {
                'car_part_id': car_part.id,
                'width': '1.50',
                'length': '1.00',
                'quantity': 1,
                'installation_price': '80.00',
            },
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 201, response.content)
        association = Car_Model_Part.objects.get(car_model_id=car_model, car_part_id=car_part)
        self.assertEqual(association.installation_price, Decimal('80.00'))

    def test_add_new_item_to_model(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'add_car_model_part')
        car_model = helpers.create_model()

        response = self.client.post(
            f'/product/vehicles/models/{car_model.id}/items/',
            {
                'new_car_part_name': 'Ventana lateral izquierda',
                'width': '0.80',
                'length': '0.60',
                'quantity': 1,
                'installation_price': '40.00',
            },
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 201, response.content)
        self.assertTrue(Car_Part.objects.filter(name='Ventana lateral izquierda').exists())
        self.assertTrue(
            Car_Model_Part.objects.filter(
                car_model_id=car_model, car_part_id__name='Ventana lateral izquierda'
            ).exists()
        )

    def test_missing_pricing_fields_returns_400(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'add_car_model_part')
        car_model = helpers.create_model()
        car_part = helpers.create_car_part()

        response = self.client.post(
            f'/product/vehicles/models/{car_model.id}/items/',
            {'car_part_id': car_part.id},
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 400)
        for field in ('width', 'length', 'quantity', 'installation_price'):
            self.assertIn(field, response.json())

    def test_duplicate_association_returns_400_not_500(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'add_car_model_part')
        car_model = helpers.create_model()
        car_part = helpers.create_car_part()
        helpers.create_car_model_part(car_model=car_model, car_part=car_part)

        response = self.client.post(
            f'/product/vehicles/models/{car_model.id}/items/',
            {
                'car_part_id': car_part.id,
                'width': '1.00',
                'length': '1.00',
                'quantity': 1,
                'installation_price': '10.00',
            },
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 400)

    def test_list_items_of_a_model(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        car_model = helpers.create_model()
        helpers.create_car_model_part(car_model=car_model, car_part=helpers.create_car_part(name='Item 1'))
        helpers.create_car_model_part(car_model=car_model, car_part=helpers.create_car_part(name='Item 2'))

        response = self.client.get(f'/product/vehicles/models/{car_model.id}/items/', **_auth_headers(token))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)

    def test_remove_association_does_not_affect_existing_proforma(self):
        """Desasociar un item de un modelo borra la fila Car_Model_Part, pero
        no debe afectar ninguna Proforma_Detail ya creada -- ver ADR-modulo-
        vehiculos-relacion-modelo-item (Proforma_Detail copia sus propios
        valores, no referencia viva a Car_Model_Part)."""
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'delete_car_model_part')
        user, _ = helpers.create_user_with_token()
        car_model_part = helpers.create_car_model_part()
        header, detail = helpers.create_full_proforma(
            user=user, car_model=car_model_part.car_model_id, car_part=car_model_part.car_part_id
        )

        response = self.client.delete(
            f'/product/vehicles/models/{car_model_part.car_model_id_id}/items/{car_model_part.id}/',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Car_Model_Part.objects.filter(pk=car_model_part.pk).exists())
        detail.refresh_from_db()
        self.assertEqual(detail.installation_price, Decimal('50.00'))

    def test_add_item_without_permission_is_forbidden(self):
        _, token, _ = helpers.create_staff_user_with_token()
        car_model = helpers.create_model()

        response = self.client.post(
            f'/product/vehicles/models/{car_model.id}/items/',
            {
                'new_car_part_name': 'Item',
                'width': '1.00',
                'length': '1.00',
                'quantity': 1,
                'installation_price': '10.00',
            },
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 403)
