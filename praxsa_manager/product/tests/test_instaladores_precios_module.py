"""Tests de Instaladores y Precios por sucursal (TASK-agrupacion-menu-
instalador-precio-sucursal). Ver ADR-agrupacion-menu-instalador-precio-
sucursal-api-permisos-borrado y PLAN-2026-09-30-agrupacion-menu-instalador-
precio-sucursal."""
from decimal import Decimal
from io import StringIO

from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from ..business.pricing import Pricing_Business
from ..management.commands.asignar_permisos_instalador_precio import PERMISOS_POR_GRUPO
from ..models import Nota_trabajo, instalador, precio_venta_sucursal
from . import helpers
from .ordenes_helpers import auth, instalacion_payload, make_scenario

INSTALADORES = '/product/instaladores'
PRECIOS = '/product/almacen/precios-sucursal'

INSTALADOR_PERMISSIONS = ('add_instalador', 'change_instalador', 'delete_instalador')
PRECIO_PERMISSIONS = (
    'add_precio_venta_sucursal', 'change_precio_venta_sucursal', 'delete_precio_venta_sucursal',
)


def _staff(permissions=(), group=None):
    """Usuario staff con token; `permissions` simula la configuracion manual
    del grupo `admin` y `group` lo mete en ese grupo por nombre."""
    user, token, _ = helpers.create_staff_user_with_token()
    for codename in permissions:
        helpers.grant_permission(user, 'product', codename)
    if group:
        helpers.add_user_to_group(user, group)
    return user, token


def _admin():
    return _staff(INSTALADOR_PERMISSIONS + PRECIO_PERMISSIONS, group='admin')


def _make_instalador(sucursal, name='Instalador Uno', is_active=True):
    inst = instalador.objects.create(
        name=name, address='Calle 1', phonenumber='70000002', is_active=is_active
    )
    inst.sucursal.add(sucursal)
    return inst


def _call(client, method, url, payload=None, token=None):
    if payload is None:
        return getattr(client, method)(url, **auth(token))
    return getattr(client, method)(url, payload, content_type='application/json', **auth(token))


class InstaladorApiTest(TestCase):
    def setUp(self):
        self.admin, self.admin_token = _admin()
        self.sucursal = helpers.create_sucursal(self.admin)

    def _payload(self, **overrides):
        payload = {
            'name': 'Juan', 'address': 'Av. Test 1', 'phonenumber': '70012345',
            'sucursal': [self.sucursal.id],
        }
        payload.update(overrides)
        return payload

    def test_create_with_sucursales(self):
        response = _call(self.client, 'post', INSTALADORES, self._payload(), self.admin_token)
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body['sucursal'], [self.sucursal.id])
        self.assertEqual(body['sucursal_names'], [self.sucursal.name])
        self.assertTrue(body['is_active'])

    def test_create_requires_at_least_one_sucursal_and_valid_phone(self):
        response = _call(self.client, 'post', INSTALADORES, self._payload(sucursal=[]), self.admin_token)
        self.assertEqual(response.status_code, 400)
        self.assertIn('sucursal', response.json())
        response = _call(self.client, 'post', INSTALADORES, self._payload(phonenumber='abc'), self.admin_token)
        self.assertEqual(response.status_code, 400)
        self.assertIn('phonenumber', response.json())

    def test_list_only_active_by_default_and_all_with_include_inactive(self):
        _make_instalador(self.sucursal, name='Activo')
        _make_instalador(self.sucursal, name='Baja', is_active=False)
        names = [r['name'] for r in _call(self.client, 'get', INSTALADORES, token=self.admin_token).json()]
        self.assertEqual(names, ['Activo'])
        names = [r['name'] for r in self.client.get(
            INSTALADORES, {'include_inactive': 'true'}, **auth(self.admin_token)).json()]
        self.assertEqual(names, ['Activo', 'Baja'])

    def test_search_by_name(self):
        _make_instalador(self.sucursal, name='Pedro')
        _make_instalador(self.sucursal, name='Maria')
        rows = self.client.get(INSTALADORES, {'search': 'ped'}, **auth(self.admin_token)).json()
        self.assertEqual([r['name'] for r in rows], ['Pedro'])

    def test_patch_updates_fields_but_not_is_active(self):
        inst = _make_instalador(self.sucursal)
        response = _call(
            self.client, 'patch', f'{INSTALADORES}/{inst.id}/',
            {'name': 'Nuevo', 'is_active': False}, self.admin_token,
        )
        self.assertEqual(response.status_code, 200, response.content)
        inst.refresh_from_db()
        self.assertEqual(inst.name, 'Nuevo')
        self.assertTrue(inst.is_active)

    def test_toggle_active_deactivates_and_reactivates(self):
        inst = _make_instalador(self.sucursal)
        url = f'{INSTALADORES}/{inst.id}/toggle-active/'
        response = _call(self.client, 'patch', url, {'is_active': False}, self.admin_token)
        self.assertEqual(response.status_code, 200, response.content)
        inst.refresh_from_db()
        self.assertFalse(inst.is_active)
        _call(self.client, 'patch', url, {'is_active': True}, self.admin_token)
        inst.refresh_from_db()
        self.assertTrue(inst.is_active)
        self.assertEqual(_call(self.client, 'patch', url, {}, self.admin_token).status_code, 400)
        missing = f'{INSTALADORES}/999999/toggle-active/'
        self.assertEqual(
            _call(self.client, 'patch', missing, {'is_active': False}, self.admin_token).status_code, 404)

    def test_no_physical_delete(self):
        inst = _make_instalador(self.sucursal)
        response = _call(self.client, 'delete', f'{INSTALADORES}/{inst.id}/', token=self.admin_token)
        self.assertEqual(response.status_code, 405)
        self.assertTrue(instalador.objects.filter(pk=inst.pk).exists())

    def test_read_only_staff_can_read_but_not_write(self):
        _, token = _staff()
        inst = _make_instalador(self.sucursal)
        self.assertEqual(_call(self.client, 'get', INSTALADORES, token=token).status_code, 200)
        self.assertEqual(_call(self.client, 'get', f'{INSTALADORES}/{inst.id}/', token=token).status_code, 200)
        self.assertEqual(_call(self.client, 'post', INSTALADORES, self._payload(), token).status_code, 403)
        self.assertEqual(
            _call(self.client, 'patch', f'{INSTALADORES}/{inst.id}/', {'name': 'X'}, token).status_code, 403)
        toggle = f'{INSTALADORES}/{inst.id}/toggle-active/'
        self.assertEqual(_call(self.client, 'patch', toggle, {'is_active': False}, token).status_code, 403)
        inst.refresh_from_db()
        self.assertTrue(inst.is_active)

    def test_non_staff_and_anonymous_are_rejected(self):
        _, token, _ = helpers.create_staff_user_with_token(is_staff=False)
        self.assertEqual(_call(self.client, 'get', INSTALADORES, token=token).status_code, 403)
        self.assertEqual(self.client.get(INSTALADORES).status_code, 401)


class PrecioVentaSucursalApiTest(TestCase):
    def setUp(self):
        self.admin, self.admin_token = _admin()
        self.sucursal = helpers.create_sucursal(self.admin)
        self.film = helpers.create_window_film()

    def _payload(self, **overrides):
        payload = {
            'sucursal': self.sucursal.id, 'lamina': self.film.id,
            'width': '1.50', 'precio_venta': '150.00',
        }
        payload.update(overrides)
        return payload

    def test_create_and_list(self):
        response = _call(self.client, 'post', PRECIOS, self._payload(), self.admin_token)
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body['sucursal_name'], self.sucursal.name)
        self.assertEqual(body['lamina_name'], self.film.name)
        self.assertEqual(Decimal(body['precio_venta']), Decimal('150.00'))
        rows = _call(self.client, 'get', PRECIOS, token=self.admin_token).json()
        self.assertEqual(len(rows), 1)

    def test_duplicate_sucursal_lamina_width_is_rejected(self):
        helpers.create_precio_venta_sucursal(self.sucursal, self.film)
        response = _call(self.client, 'post', PRECIOS, self._payload(), self.admin_token)
        self.assertEqual(response.status_code, 400)
        self.assertIn('non_field_errors', response.json())
        self.assertEqual(precio_venta_sucursal.objects.count(), 1)

    def test_same_lamina_with_other_width_or_sucursal_is_allowed(self):
        helpers.create_precio_venta_sucursal(self.sucursal, self.film)
        self.assertEqual(
            _call(self.client, 'post', PRECIOS, self._payload(width='1.20'), self.admin_token).status_code, 201)
        other = helpers.create_sucursal(self.admin)
        self.assertEqual(
            _call(self.client, 'post', PRECIOS, self._payload(sucursal=other.id), self.admin_token).status_code,
            201)

    def test_editing_own_row_does_not_trip_uniqueness_but_collision_does(self):
        mine = helpers.create_precio_venta_sucursal(self.sucursal, self.film)
        other = helpers.create_precio_venta_sucursal(self.sucursal, self.film, width=Decimal('1.20'))
        response = _call(
            self.client, 'patch', f'{PRECIOS}/{mine.id}/', {'precio_venta': '175.00'}, self.admin_token)
        self.assertEqual(response.status_code, 200, response.content)
        mine.refresh_from_db()
        self.assertEqual(mine.precio_venta, Decimal('175.00'))
        response = _call(self.client, 'patch', f'{PRECIOS}/{other.id}/', {'width': '1.50'}, self.admin_token)
        self.assertEqual(response.status_code, 400)

    def test_non_positive_values_and_inactive_lamina_are_rejected(self):
        for overrides, field in (
            ({'width': '0'}, 'width'),
            ({'precio_venta': '0'}, 'precio_venta'),
            ({'precio_venta': '-5'}, 'precio_venta'),
        ):
            response = _call(self.client, 'post', PRECIOS, self._payload(**overrides), self.admin_token)
            self.assertEqual(response.status_code, 400)
            self.assertIn(field, response.json())
        self.film.is_active = False
        self.film.save()
        response = _call(self.client, 'post', PRECIOS, self._payload(), self.admin_token)
        self.assertEqual(response.status_code, 400)
        self.assertIn('lamina', response.json())

    def test_delete_removes_row_and_price_falls_back_to_inventory(self):
        s = make_scenario()
        helpers.add_user_to_group(s['user'], 'admin')
        for codename in PRECIO_PERMISSIONS:
            helpers.grant_permission(s['user'], 'product', codename)
        row = helpers.create_precio_venta_sucursal(
            s['sucursal'], s['film'], width=s['reel'].width, precio_venta=Decimal('999.00'))
        pricing = Pricing_Business()
        self.assertEqual(
            pricing.resolve_unit_price(s['sucursal'].id, s['film'].id, s['reel'].width), Decimal('999.00'))

        response = _call(self.client, 'delete', f'{PRECIOS}/{row.id}/', token=s['token'])
        self.assertEqual(response.status_code, 204)
        self.assertFalse(precio_venta_sucursal.objects.filter(pk=row.pk).exists())
        self.assertEqual(
            pricing.resolve_unit_price(s['sucursal'].id, s['film'].id, s['reel'].width),
            s['inventario'].precio_venta_mtr_lineal,
        )

    def test_search_and_sucursal_filters(self):
        other_film = helpers.create_window_film(name='Ceramica Especial')
        other_sucursal = helpers.create_sucursal(self.admin)
        helpers.create_precio_venta_sucursal(self.sucursal, self.film)
        helpers.create_precio_venta_sucursal(other_sucursal, other_film)
        rows = self.client.get(PRECIOS, {'search': 'ceramica'}, **auth(self.admin_token)).json()
        self.assertEqual([r['lamina_name'] for r in rows], ['Ceramica Especial'])
        rows = self.client.get(PRECIOS, {'sucursal': self.sucursal.id}, **auth(self.admin_token)).json()
        self.assertEqual([r['lamina_name'] for r in rows], [self.film.name])

    def test_read_only_staff_can_read_but_not_write(self):
        user, token = _staff()
        own = helpers.create_sucursal(user)
        row = helpers.create_precio_venta_sucursal(own, self.film)
        self.assertEqual(_call(self.client, 'get', PRECIOS, token=token).status_code, 200)
        self.assertEqual(_call(self.client, 'get', f'{PRECIOS}/{row.id}/', token=token).status_code, 200)
        self.assertEqual(
            _call(self.client, 'post', PRECIOS, self._payload(sucursal=own.id), token).status_code, 403)
        self.assertEqual(
            _call(self.client, 'patch', f'{PRECIOS}/{row.id}/', {'precio_venta': '1'}, token).status_code, 403)
        self.assertEqual(_call(self.client, 'delete', f'{PRECIOS}/{row.id}/', token=token).status_code, 403)
        self.assertTrue(precio_venta_sucursal.objects.filter(pk=row.pk).exists())

    def test_non_admin_only_sees_and_writes_own_sucursales(self):
        user, token = _staff(PRECIO_PERMISSIONS)
        own = helpers.create_sucursal(user)
        own_row = helpers.create_precio_venta_sucursal(own, self.film)
        foreign_row = helpers.create_precio_venta_sucursal(self.sucursal, self.film)

        ids = [r['id'] for r in _call(self.client, 'get', PRECIOS, token=token).json()]
        self.assertEqual(ids, [own_row.id])
        self.assertEqual(_call(self.client, 'get', f'{PRECIOS}/{foreign_row.id}/', token=token).status_code, 404)
        self.assertEqual(
            _call(self.client, 'delete', f'{PRECIOS}/{foreign_row.id}/', token=token).status_code, 404)
        response = _call(
            self.client, 'post', PRECIOS, self._payload(sucursal=self.sucursal.id, width='1.10'), token)
        self.assertEqual(response.status_code, 400)
        self.assertIn('sucursal', response.json())
        response = _call(self.client, 'post', PRECIOS, self._payload(sucursal=own.id, width='1.10'), token)
        self.assertEqual(response.status_code, 201, response.content)

    def test_admin_sees_every_sucursal(self):
        other_user, _ = _staff()
        other = helpers.create_sucursal(other_user)
        helpers.create_precio_venta_sucursal(other, self.film)
        helpers.create_precio_venta_sucursal(self.sucursal, self.film)
        rows = _call(self.client, 'get', PRECIOS, token=self.admin_token).json()
        self.assertEqual(len(rows), 2)


class OrdenesInstaladorInactivoTest(TestCase):
    def setUp(self):
        self.s = make_scenario()
        self.headers = auth(self.s['token'])

    def _nota(self):
        proforma_id = self.client.post(
            '/product/ordenes/proformas', instalacion_payload(self.s),
            content_type='application/json', **self.headers,
        ).json()['id']
        self.client.post(f'/product/ordenes/proformas/{proforma_id}/generar-nota-trabajo/', **self.headers)
        return Nota_trabajo.objects.get(proforma_id=proforma_id)

    def test_catalog_excludes_inactive_installers(self):
        _make_instalador(self.s['sucursal'], name='Activo')
        _make_instalador(self.s['sucursal'], name='Baja', is_active=False)
        rows = self.client.get(
            '/product/ordenes/catalogo/instaladores', {'sucursal': self.s['sucursal'].id}, **self.headers
        ).json()
        self.assertEqual([r['name'] for r in rows], ['Activo'])

    def test_cannot_assign_inactive_installer_but_existing_assignment_survives(self):
        nota = self._nota()
        url = f'/product/ordenes/notas-trabajo/{nota.id}/'
        baja = _make_instalador(self.s['sucursal'], name='Baja', is_active=False)
        response = self.client.patch(url, {'instaladar': baja.id}, content_type='application/json', **self.headers)
        self.assertEqual(response.status_code, 400)
        self.assertIn('instaladar', response.json())

        Nota_trabajo.objects.filter(pk=nota.pk).update(instaladar=baja)
        response = self.client.patch(
            url, {'instaladar': baja.id, 'observaciones': 'sigue asignado'},
            content_type='application/json', **self.headers,
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['instalador_name'], 'Baja')


class InstaladorDefaultActiveTest(TestCase):
    def test_new_installers_default_to_active(self):
        user, _ = _staff()
        sucursal = helpers.create_sucursal(user)
        inst = instalador.objects.create(name='X', address='y', phonenumber='70000003')
        inst.sucursal.add(sucursal)
        self.assertTrue(instalador.objects.get(pk=inst.pk).is_active)


def _codenames(group):
    return set(group.permissions.values_list('codename', flat=True))


class AsignarPermisosInstaladorPrecioTest(TestCase):
    def correr(self, *args):
        out = StringIO()
        call_command('asignar_permisos_instalador_precio', *args, stdout=out)
        return out.getvalue()

    def test_asigna_permisos_de_escritura_al_grupo_admin_y_es_idempotente(self):
        Group.objects.create(name='Admin')
        Group.objects.create(name='Caja')
        self.correr()
        self.assertEqual(_codenames(Group.objects.get(name='Admin')), set(PERMISOS_POR_GRUPO['Admin']))
        self.assertEqual(_codenames(Group.objects.get(name='Caja')), set())
        salida = self.correr()
        self.assertIn('agregados 0', salida)
        self.assertEqual(_codenames(Group.objects.get(name='Admin')), set(PERMISOS_POR_GRUPO['Admin']))

    def test_dry_run_no_escribe(self):
        Group.objects.create(name='Admin')
        salida = self.correr('--dry-run')
        self.assertIn('se agregarían', salida)
        self.assertEqual(_codenames(Group.objects.get(name='Admin')), set())

    def test_grupo_inexistente_falla_sin_cambios(self):
        Group.objects.create(name='Administrador')
        with self.assertRaises(CommandError) as ctx:
            self.correr()
        self.assertIn('Admin', str(ctx.exception))
        self.assertIn('Administrador', str(ctx.exception))
        self.assertEqual(_codenames(Group.objects.get(name='Administrador')), set())
