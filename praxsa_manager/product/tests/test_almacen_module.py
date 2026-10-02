"""Tests del modulo Almacen (TASK-modulo-almacen): Laminas, Bobinas e
Inventario sobre los modelos ya existentes Window_Film/Window_Film_Reel/
inventario, que hasta este task solo se administraban por Django Admin.

Ver ADR-modulo-almacen-modelo-datos-imagen-soft-delete y
ADR-modulo-almacen-permisos-rol-frontend.
"""
import io
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test.client import BOUNDARY, encode_multipart
from PIL import Image

from ..models import Window_Film, Window_Film_Reel, inventario
from . import helpers


def _auth_headers(token):
    return {'HTTP_AUTHORIZATION': f'Token {token.key}'}


def _make_image_file(name='lamina.jpg', image_format='JPEG', size=(10, 10), content_type='image/jpeg'):
    buffer = io.BytesIO()
    Image.new('RGB', size, color='blue').save(buffer, format=image_format)
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.read(), content_type=content_type)


def _patch_multipart(client, url, data, **extra):
    """Ver test_vehicles_module.py::_patch_multipart -- self.client.patch()
    no auto-detecta multipart, hay que codificarlo a mano para mandar un
    archivo en un PATCH."""
    encoded = encode_multipart(BOUNDARY, data)
    return client.patch(url, encoded, content_type=f'multipart/form-data; boundary={BOUNDARY}', **extra)


def _grant_almacen_write_permissions(user):
    """Simula la configuracion manual del grupo `admin` (ver ADR-modulo-
    almacen-permisos-rol-frontend punto 2): permisos de escritura sobre los
    3 modelos de Almacen."""
    for codename in (
        'add_window_film', 'change_window_film', 'delete_window_film',
        'add_window_film_reel', 'change_window_film_reel', 'delete_window_film_reel',
        'add_inventario', 'change_inventario',
    ):
        helpers.grant_permission(user, 'product', codename)


class WindowFilmTest(TestCase):
    def test_create_lamina(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'add_window_film')

        response = self.client.post(
            '/product/almacen/laminas',
            {'name': 'Carbon 20%', 'description': 'polarizado oscuro'},
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 201, response.content)
        self.assertTrue(Window_Film.objects.filter(name='Carbon 20%').exists())

    def test_create_via_multipart_defaults_to_active(self):
        """Mismo bug reproducido y corregido en Vehiculos
        (REV-2026-09-26-modulo-vehiculos-01): un multipart/form-data sin
        `is_active` no debe dejar la Lamina inactiva -- `is_active` es de
        solo lectura en el serializer."""
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'add_window_film')

        response = self.client.post(
            '/product/almacen/laminas',
            {'name': 'CarbonMultipart', 'description': 'x'},
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 201, response.content)
        self.assertTrue(response.json()['is_active'])
        created = Window_Film.objects.get(name='CarbonMultipart')
        self.assertTrue(created.is_active)

    def test_edit_lamina(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'change_window_film')
        lamina = helpers.create_window_film(name='Carbon 20%')

        response = self.client.patch(
            f'/product/almacen/laminas/{lamina.id}/',
            {'description': 'nueva descripcion'},
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 200, response.content)
        lamina.refresh_from_db()
        self.assertEqual(lamina.description, 'nueva descripcion')

    def test_list_hides_inactive_laminas_by_default(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        active = helpers.create_window_film(name='Activa')
        inactive = helpers.create_window_film(name='Inactiva')
        inactive.is_active = False
        inactive.save(update_fields=['is_active'])

        response = self.client.get('/product/almacen/laminas', **_auth_headers(token))

        names = [row['name'] for row in response.json()]
        self.assertIn('Activa', names)
        self.assertNotIn('Inactiva', names)

    def test_list_include_inactive_shows_them(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        inactive = helpers.create_window_film(name='Inactiva')
        inactive.is_active = False
        inactive.save(update_fields=['is_active'])

        response = self.client.get('/product/almacen/laminas?include_inactive=true', **_auth_headers(token))

        names = [row['name'] for row in response.json()]
        self.assertIn('Inactiva', names)

    def test_search_by_name(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.create_window_film(name='Carbon 20%')
        helpers.create_window_film(name='Ceramico 30%')

        response = self.client.get('/product/almacen/laminas?search=carbon', **_auth_headers(token))

        names = [row['name'] for row in response.json()]
        self.assertEqual(names, ['Carbon 20%'])

    def test_toggle_active_soft_deletes(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'change_window_film')
        lamina = helpers.create_window_film()

        response = self.client.patch(
            f'/product/almacen/laminas/{lamina.id}/toggle-active/',
            {'is_active': False},
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 200)
        lamina.refresh_from_db()
        self.assertFalse(lamina.is_active)

    def test_non_staff_user_cannot_reach_endpoint(self):
        _, token, _ = helpers.create_staff_user_with_token(is_staff=False)

        response = self.client.get('/product/almacen/laminas', **_auth_headers(token))

        self.assertEqual(response.status_code, 403)


class WindowFilmImageTest(TestCase):
    def test_create_with_valid_image(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'add_window_film')

        response = self.client.post(
            '/product/almacen/laminas',
            {'name': 'Carbon 20%', 'description': 'x', 'image': _make_image_file()},
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 201, response.content)
        created = Window_Film.objects.get(name='Carbon 20%')
        self.assertTrue(created.image)
        self.assertTrue(response.json()['image'].startswith('http'))

    def test_create_without_image_is_valid(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'add_window_film')

        response = self.client.post(
            '/product/almacen/laminas',
            {'name': 'Carbon 20%', 'description': 'x'},
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 201, response.content)
        self.assertIsNone(response.json()['image'])

    def test_invalid_image_format_returns_400(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'add_window_film')
        fake_image = SimpleUploadedFile('nota.jpg', b'no soy una imagen de verdad', content_type='image/jpeg')

        response = self.client.post(
            '/product/almacen/laminas',
            {'name': 'Carbon 20%', 'description': 'x', 'image': fake_image},
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('image', response.json())
        self.assertFalse(Window_Film.objects.filter(name='Carbon 20%').exists())

    def test_image_too_large_returns_400(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'add_window_film')
        big_image = SimpleUploadedFile('grande.jpg', b'0' * (6 * 1024 * 1024), content_type='image/jpeg')

        response = self.client.post(
            '/product/almacen/laminas',
            {'name': 'Carbon 20%', 'description': 'x', 'image': big_image},
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('image', response.json())

    def test_replace_image_deletes_previous_file(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'change_window_film')
        lamina = helpers.create_window_film()
        lamina.image.save('original.jpg', _make_image_file(), save=True)
        original_path = lamina.image.path
        self.assertTrue(lamina.image.storage.exists(original_path))

        response = _patch_multipart(
            self.client,
            f'/product/almacen/laminas/{lamina.id}/',
            {'image': _make_image_file(name='nuevo.jpg')},
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(lamina.image.storage.exists(original_path))
        lamina.refresh_from_db()
        self.assertIn('nuevo', lamina.image.name)
        lamina.image.delete(save=False)

    def test_remove_image(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'change_window_film')
        lamina = helpers.create_window_film()
        lamina.image.save('original.jpg', _make_image_file(), save=True)

        response = self.client.patch(
            f'/product/almacen/laminas/{lamina.id}/',
            {'image': None},
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 200, response.content)
        lamina.refresh_from_db()
        self.assertFalse(lamina.image)


class WindowFilmReelTest(TestCase):
    def test_create_bobina(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'add_window_film_reel')
        lamina = helpers.create_window_film()

        response = self.client.post(
            '/product/almacen/bobinas',
            {'window_film': lamina.id, 'width': '1.50', 'length': '30.00', 'price': '120.00'},
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 201, response.content)
        self.assertTrue(Window_Film_Reel.objects.filter(window_film=lamina, width=Decimal('1.50')).exists())

    def test_edit_bobina(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'change_window_film_reel')
        reel = helpers.create_window_film_reel(price=Decimal('100.00'))

        response = self.client.patch(
            f'/product/almacen/bobinas/{reel.id}/',
            {'price': '150.00'},
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 200, response.content)
        reel.refresh_from_db()
        self.assertEqual(reel.price, Decimal('150.00'))

    def test_toggle_active_soft_deletes(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'change_window_film_reel')
        reel = helpers.create_window_film_reel()

        response = self.client.patch(
            f'/product/almacen/bobinas/{reel.id}/toggle-active/',
            {'is_active': False},
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 200)
        reel.refresh_from_db()
        self.assertFalse(reel.is_active)

    def test_toggle_active_does_not_affect_existing_inventario(self):
        """Ver ADR-modulo-almacen-modelo-datos-imagen-soft-delete punto 10:
        el soft-delete de Bobina no toca ninguna fila de inventario ya
        existente, a diferencia del bloqueo de integridad del borrado
        fisico del admin de Django."""
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'change_window_film_reel')
        reel = helpers.create_window_film_reel()
        inv = helpers.create_inventario(bobina=reel)

        response = self.client.patch(
            f'/product/almacen/bobinas/{reel.id}/toggle-active/',
            {'is_active': False},
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(inventario.objects.filter(pk=inv.pk).exists())

    def test_inactive_lamina_not_offered_as_choice_for_new_bobina(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'add_window_film_reel')
        lamina = helpers.create_window_film()
        lamina.is_active = False
        lamina.save(update_fields=['is_active'])

        response = self.client.post(
            '/product/almacen/bobinas',
            {'window_film': lamina.id, 'width': '1.50', 'length': '30.00', 'price': '120.00'},
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('window_film', response.json())

    def test_search_by_lamina_name(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        carbon = helpers.create_window_film(name='Carbon 20%')
        ceramico = helpers.create_window_film(name='Ceramico 30%')
        helpers.create_window_film_reel(window_film=carbon)
        helpers.create_window_film_reel(window_film=ceramico)

        response = self.client.get('/product/almacen/bobinas?search=carbon', **_auth_headers(token))

        names = [row['window_film_name'] for row in response.json()]
        self.assertEqual(names, ['Carbon 20%'])


class InventarioTest(TestCase):
    def test_admin_sees_all_sucursales(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.add_user_to_group(admin, 'admin')
        sucursal = helpers.create_sucursal(admin)
        inv = helpers.create_inventario(sucursal=sucursal)

        response = self.client.get('/product/almacen/inventario', **_auth_headers(token))

        self.assertEqual(response.status_code, 200)
        ids = [row['id'] for row in response.json()]
        self.assertIn(inv.id, ids)

    def test_non_admin_sees_only_own_sucursal(self):
        staff, token, _ = helpers.create_staff_user_with_token()
        own_sucursal = helpers.create_sucursal(staff)
        other_admin, _ = helpers.create_user_with_token()
        other_sucursal = helpers.create_sucursal(other_admin)
        own_inv = helpers.create_inventario(sucursal=own_sucursal)
        other_inv = helpers.create_inventario(sucursal=other_sucursal)

        response = self.client.get('/product/almacen/inventario', **_auth_headers(token))

        self.assertEqual(response.status_code, 200)
        ids = [row['id'] for row in response.json()]
        self.assertIn(own_inv.id, ids)
        self.assertNotIn(other_inv.id, ids)

    def test_user_without_sucursal_sees_empty_list_not_error(self):
        staff, token, _ = helpers.create_staff_user_with_token()

        response = self.client.get('/product/almacen/inventario', **_auth_headers(token))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_manage_updates_allowed_fields(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'change_inventario')
        inv = helpers.create_inventario(sucursal=helpers.create_sucursal(admin), to_install=Decimal('10.00'))

        response = self.client.patch(
            f'/product/almacen/inventario/{inv.id}/',
            {'to_install': '25.00', 'nro_lote': 'L999'},
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 200, response.content)
        inv.refresh_from_db()
        self.assertEqual(inv.to_install, Decimal('25.00'))
        self.assertEqual(inv.nro_lote, 'L999')

    def test_manage_ignores_fields_outside_allowed_scope(self):
        """quantity/original_length/date/sucursal/bobina quedan fuera del
        InventarioUpdateSerializer -- ver ADR-modulo-almacen-modelo-datos-
        imagen-soft-delete punto 8. Mandarlos no debe cambiarlos."""
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'change_inventario')
        own_sucursal = helpers.create_sucursal(admin)
        inv = helpers.create_inventario(sucursal=own_sucursal, quantity=5)
        other_sucursal = helpers.create_sucursal(admin)

        response = self.client.patch(
            f'/product/almacen/inventario/{inv.id}/',
            {'quantity': 999, 'sucursal': other_sucursal.id},
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 200, response.content)
        inv.refresh_from_db()
        self.assertEqual(inv.quantity, 5)
        self.assertNotEqual(inv.sucursal_id, other_sucursal.id)

    def test_manage_without_permission_is_forbidden(self):
        _, token, _ = helpers.create_staff_user_with_token()
        inv = helpers.create_inventario()

        response = self.client.patch(
            f'/product/almacen/inventario/{inv.id}/',
            {'to_install': '25.00'},
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 403)
        inv.refresh_from_db()
        self.assertNotEqual(inv.to_install, Decimal('25.00'))

    def test_list_hides_inactive_by_default(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.add_user_to_group(admin, 'admin')
        sucursal = helpers.create_sucursal(admin)
        active = helpers.create_inventario(sucursal=sucursal)
        inactive = helpers.create_inventario(sucursal=sucursal, to_install=Decimal('0.00'))
        inactive.is_active = False
        inactive.save(update_fields=['is_active'])

        response = self.client.get('/product/almacen/inventario', **_auth_headers(token))

        ids = [row['id'] for row in response.json()]
        self.assertIn(active.id, ids)
        self.assertNotIn(inactive.id, ids)

    def test_list_include_inactive_shows_them(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.add_user_to_group(admin, 'admin')
        inactive = helpers.create_inventario(sucursal=helpers.create_sucursal(admin), to_install=Decimal('0.00'))
        inactive.is_active = False
        inactive.save(update_fields=['is_active'])

        response = self.client.get('/product/almacen/inventario?include_inactive=true', **_auth_headers(token))

        ids = [row['id'] for row in response.json()]
        self.assertIn(inactive.id, ids)


class InventarioCreateTest(TestCase):
    def test_create_with_required_fields_applies_server_defaults(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'add_inventario')
        sucursal = helpers.create_sucursal(admin)
        reel = helpers.create_window_film_reel()

        response = self.client.post(
            '/product/almacen/inventario',
            {
                'sucursal': sucursal.id, 'bobina': reel.id, 'quantity': 3,
                'to_install': '50.00', 'precio_compra_mtr_lineal': '80.00',
                'precio_venta_mtr_lineal': '120.00', 'nro_lote': 'L001',
            },
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 201, response.content)
        created = inventario.objects.get(pk=response.json()['id'])
        self.assertEqual(created.installed, Decimal('0.00'))
        self.assertEqual(created.original_length, Decimal('50.00'))
        self.assertIsNotNone(created.date)
        self.assertTrue(created.is_active)

    def test_create_missing_required_field_returns_400(self):
        """nro_lote es obligatorio (corregido tras feedback del usuario en
        REV-2026-09-27-modulo-almacen-01 -- el panel anterior ya lo exigia
        en la practica, pese a que el modelo lo declara null=True)."""
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'add_inventario')
        sucursal = helpers.create_sucursal(admin)

        response = self.client.post(
            '/product/almacen/inventario',
            {'sucursal': sucursal.id, 'quantity': 1, 'to_install': '10.00'},
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 400)
        for field in ('bobina', 'precio_compra_mtr_lineal', 'precio_venta_mtr_lineal', 'nro_lote'):
            self.assertIn(field, response.json())

    def test_create_with_invalid_nro_lote_format_returns_400(self):
        """REV-2026-09-27-modulo-almacen-01: antes de este fix, un nro_lote
        no alfanumerico pasaba la validacion del serializer."""
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'add_inventario')
        sucursal = helpers.create_sucursal(admin)
        reel = helpers.create_window_film_reel()

        response = self.client.post(
            '/product/almacen/inventario',
            {
                'sucursal': sucursal.id, 'bobina': reel.id, 'quantity': 1,
                'to_install': '10.00', 'precio_compra_mtr_lineal': '80.00',
                'precio_venta_mtr_lineal': '120.00', 'nro_lote': 'L-999',
            },
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('nro_lote', response.json())
        self.assertFalse(inventario.objects.filter(nro_lote='L-999').exists())

    def test_create_with_nro_lote_too_long_returns_400_not_500(self):
        """REV-2026-09-27-modulo-almacen-01: antes de este fix, un nro_lote
        de mas de 15 caracteres pasaba la validacion del serializer y fallaba
        al guardar con una excepcion de base de datos no controlada."""
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'add_inventario')
        sucursal = helpers.create_sucursal(admin)
        reel = helpers.create_window_film_reel()

        response = self.client.post(
            '/product/almacen/inventario',
            {
                'sucursal': sucursal.id, 'bobina': reel.id, 'quantity': 1,
                'to_install': '10.00', 'precio_compra_mtr_lineal': '80.00',
                'precio_venta_mtr_lineal': '120.00', 'nro_lote': 'X' * 20,
            },
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('nro_lote', response.json())

    def test_create_with_numero_referencia_too_large_returns_400(self):
        """REV-2026-09-27-modulo-almacen-01: numero_referencia tambien
        perdia su MaxValueValidator al redeclararse explicitamente."""
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'add_inventario')
        sucursal = helpers.create_sucursal(admin)
        reel = helpers.create_window_film_reel()

        response = self.client.post(
            '/product/almacen/inventario',
            {
                'sucursal': sucursal.id, 'bobina': reel.id, 'quantity': 1,
                'to_install': '10.00', 'precio_compra_mtr_lineal': '80.00',
                'precio_venta_mtr_lineal': '120.00', 'nro_lote': 'L001',
                'numero_referencia': 99999999999,
            },
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('numero_referencia', response.json())

    def test_create_with_inactive_bobina_is_rejected(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'add_inventario')
        sucursal = helpers.create_sucursal(admin)
        reel = helpers.create_window_film_reel()
        reel.is_active = False
        reel.save(update_fields=['is_active'])

        response = self.client.post(
            '/product/almacen/inventario',
            {
                'sucursal': sucursal.id, 'bobina': reel.id, 'quantity': 1,
                'to_install': '10.00', 'precio_compra_mtr_lineal': '80.00',
                'precio_venta_mtr_lineal': '120.00', 'nro_lote': 'L001',
            },
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('bobina', response.json())

    def test_create_without_permission_is_forbidden(self):
        _, token, _ = helpers.create_staff_user_with_token()
        sucursal = helpers.create_sucursal(helpers.create_user_with_token()[0])
        reel = helpers.create_window_film_reel()

        response = self.client.post(
            '/product/almacen/inventario',
            {
                'sucursal': sucursal.id, 'bobina': reel.id, 'quantity': 1,
                'to_install': '10.00', 'precio_compra_mtr_lineal': '80.00',
                'precio_venta_mtr_lineal': '120.00', 'nro_lote': 'L001',
            },
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 403)


class InventarioToggleActiveTest(TestCase):
    def test_delete_blocked_when_to_install_greater_than_zero(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'change_inventario')
        inv = helpers.create_inventario(sucursal=helpers.create_sucursal(admin), to_install=Decimal('10.00'))

        response = self.client.patch(
            f'/product/almacen/inventario/{inv.id}/toggle-active/',
            {'is_active': False},
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 400)
        inv.refresh_from_db()
        self.assertTrue(inv.is_active)

    def test_delete_allowed_when_to_install_is_zero(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'change_inventario')
        inv = helpers.create_inventario(sucursal=helpers.create_sucursal(admin), to_install=Decimal('0.00'))

        response = self.client.patch(
            f'/product/almacen/inventario/{inv.id}/toggle-active/',
            {'is_active': False},
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 200, response.content)
        inv.refresh_from_db()
        self.assertFalse(inv.is_active)

    def test_reactivate_has_no_to_install_restriction(self):
        admin, token, _ = helpers.create_staff_user_with_token()
        helpers.grant_permission(admin, 'product', 'change_inventario')
        inv = helpers.create_inventario(sucursal=helpers.create_sucursal(admin), to_install=Decimal('10.00'))
        inv.is_active = False
        inv.save(update_fields=['is_active'])

        response = self.client.patch(
            f'/product/almacen/inventario/{inv.id}/toggle-active/',
            {'is_active': True},
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 200, response.content)
        inv.refresh_from_db()
        self.assertTrue(inv.is_active)

    def test_toggle_active_without_permission_is_forbidden(self):
        _, token, _ = helpers.create_staff_user_with_token()
        inv = helpers.create_inventario(to_install=Decimal('0.00'))

        response = self.client.patch(
            f'/product/almacen/inventario/{inv.id}/toggle-active/',
            {'is_active': False},
            content_type='application/json',
            **_auth_headers(token),
        )

        self.assertEqual(response.status_code, 403)


class AlmacenRolePermissionTest(TestCase):
    """El requerimiento exige que `almacen` solo pueda leer los 3 recursos,
    validado en backend (no solo ocultando botones en Angular) -- ver
    ADR-modulo-almacen-permisos-rol-frontend. Estos tests simulan el grupo
    `almacen` sin permisos de escritura (tal como se configuraria en
    produccion) y el grupo `admin` con permisos completos."""

    def test_almacen_role_can_read_but_not_write(self):
        almacen_user, token, _ = helpers.create_staff_user_with_token()
        helpers.add_user_to_group(almacen_user, 'almacen')
        lamina = helpers.create_window_film()
        reel = helpers.create_window_film_reel()
        inv = helpers.create_inventario()

        get_laminas = self.client.get('/product/almacen/laminas', **_auth_headers(token))
        get_bobinas = self.client.get('/product/almacen/bobinas', **_auth_headers(token))
        get_inventario = self.client.get('/product/almacen/inventario', **_auth_headers(token))
        self.assertEqual(get_laminas.status_code, 200)
        self.assertEqual(get_bobinas.status_code, 200)
        self.assertEqual(get_inventario.status_code, 200)

        post_lamina = self.client.post(
            '/product/almacen/laminas', {'name': 'Nueva', 'description': 'x'},
            content_type='application/json', **_auth_headers(token),
        )
        patch_lamina = self.client.patch(
            f'/product/almacen/laminas/{lamina.id}/', {'description': 'y'},
            content_type='application/json', **_auth_headers(token),
        )
        toggle_lamina = self.client.patch(
            f'/product/almacen/laminas/{lamina.id}/toggle-active/', {'is_active': False},
            content_type='application/json', **_auth_headers(token),
        )
        post_bobina = self.client.post(
            '/product/almacen/bobinas',
            {'window_film': lamina.id, 'width': '1.00', 'length': '10.00', 'price': '50.00'},
            content_type='application/json', **_auth_headers(token),
        )
        toggle_bobina = self.client.patch(
            f'/product/almacen/bobinas/{reel.id}/toggle-active/', {'is_active': False},
            content_type='application/json', **_auth_headers(token),
        )
        manage_inventario = self.client.patch(
            f'/product/almacen/inventario/{inv.id}/', {'to_install': '99.00'},
            content_type='application/json', **_auth_headers(token),
        )
        post_inventario = self.client.post(
            '/product/almacen/inventario',
            {
                'sucursal': inv.sucursal_id, 'bobina': reel.id, 'quantity': 1,
                'to_install': '10.00', 'precio_compra_mtr_lineal': '80.00',
                'precio_venta_mtr_lineal': '120.00', 'nro_lote': 'L001',
            },
            content_type='application/json', **_auth_headers(token),
        )
        toggle_inventario = self.client.patch(
            f'/product/almacen/inventario/{inv.id}/toggle-active/', {'is_active': False},
            content_type='application/json', **_auth_headers(token),
        )

        self.assertEqual(post_lamina.status_code, 403)
        self.assertEqual(patch_lamina.status_code, 403)
        self.assertEqual(toggle_lamina.status_code, 403)
        self.assertEqual(post_bobina.status_code, 403)
        self.assertEqual(toggle_bobina.status_code, 403)
        self.assertEqual(manage_inventario.status_code, 403)
        self.assertEqual(post_inventario.status_code, 403)
        self.assertEqual(toggle_inventario.status_code, 403)

    def test_admin_role_has_full_access(self):
        admin_user, token, _ = helpers.create_staff_user_with_token()
        helpers.add_user_to_group(admin_user, 'admin')
        _grant_almacen_write_permissions(admin_user)
        lamina = helpers.create_window_film()
        reel = helpers.create_window_film_reel()
        sucursal = helpers.create_sucursal(admin_user)  # el admin opera solo en su sucursal asignada
        inv = helpers.create_inventario(sucursal=sucursal)
        empty_inv = helpers.create_inventario(sucursal=sucursal, to_install=Decimal('0.00'))

        post_lamina = self.client.post(
            '/product/almacen/laminas', {'name': 'Nueva', 'description': 'x'},
            content_type='application/json', **_auth_headers(token),
        )
        toggle_lamina = self.client.patch(
            f'/product/almacen/laminas/{lamina.id}/toggle-active/', {'is_active': False},
            content_type='application/json', **_auth_headers(token),
        )
        toggle_bobina = self.client.patch(
            f'/product/almacen/bobinas/{reel.id}/toggle-active/', {'is_active': False},
            content_type='application/json', **_auth_headers(token),
        )
        manage_inventario = self.client.patch(
            f'/product/almacen/inventario/{inv.id}/', {'to_install': '99.00'},
            content_type='application/json', **_auth_headers(token),
        )
        # reel se desactivo arriba (toggle_bobina) -- usar una bobina activa
        # distinta para no chocar con la restriccion de selector del serializer.
        active_reel = helpers.create_window_film_reel()
        post_inventario = self.client.post(
            '/product/almacen/inventario',
            {
                'sucursal': inv.sucursal_id, 'bobina': active_reel.id, 'quantity': 1,
                'to_install': '10.00', 'precio_compra_mtr_lineal': '80.00',
                'precio_venta_mtr_lineal': '120.00', 'nro_lote': 'L001',
            },
            content_type='application/json', **_auth_headers(token),
        )
        toggle_inventario = self.client.patch(
            f'/product/almacen/inventario/{empty_inv.id}/toggle-active/', {'is_active': False},
            content_type='application/json', **_auth_headers(token),
        )

        self.assertEqual(post_lamina.status_code, 201, post_lamina.content)
        self.assertEqual(toggle_lamina.status_code, 200)
        self.assertEqual(toggle_bobina.status_code, 200)
        self.assertEqual(manage_inventario.status_code, 200, manage_inventario.content)
        self.assertEqual(post_inventario.status_code, 201, post_inventario.content)
        self.assertEqual(toggle_inventario.status_code, 200, toggle_inventario.content)
