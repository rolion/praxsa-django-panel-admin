"""Tests de TASK-008 (backlog #4, IDOR): `InvoiceView.get` filtra por `created_by`;
`get_proforma_car_part_info` exige staff y queda acotado por sucursal/rol vía
`Proforma_Business.get_proforma_queryset_by_role` (mismo método que ya usa
`ProformaAdmin.get_queryset`). Ver ADR-006."""
from django.test import TestCase

from . import helpers


class InvoiceViewGetOwnershipTest(TestCase):
    def test_owner_can_read_own_invoice(self):
        owner, token = helpers.create_user_with_token()
        header, _ = helpers.create_full_proforma(owner)

        response = self.client.get(
            f'/product/invoice/{header.id}/',
            HTTP_AUTHORIZATION=f'Token {token.key}',
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['id'], header.id)
        self.assertEqual(data['name'], header.name)

    def test_user_cannot_read_another_users_invoice(self):
        owner, _ = helpers.create_user_with_token()
        header, _ = helpers.create_full_proforma(owner)
        other_user, other_token = helpers.create_user_with_token()

        response = self.client.get(
            f'/product/invoice/{header.id}/',
            HTTP_AUTHORIZATION=f'Token {other_token.key}',
        )

        self.assertEqual(response.status_code, 404)

    def test_nonexistent_pk_still_returns_404(self):
        _, token = helpers.create_user_with_token()

        response = self.client.get(
            '/product/invoice/999999/',
            HTTP_AUTHORIZATION=f'Token {token.key}',
        )

        self.assertEqual(response.status_code, 404)


class GetProformaCarPartInfoAuthorizationTest(TestCase):
    def test_anonymous_request_returns_403(self):
        owner, _ = helpers.create_user_with_token()
        header, _ = helpers.create_full_proforma(owner)

        response = self.client.get(f'/product/get_proforma_car_part_info/{header.id}')

        self.assertEqual(response.status_code, 403)

    def test_authenticated_non_staff_returns_403(self):
        user, password = helpers.create_staff_user()
        user.is_staff = False
        user.save()
        owner, _ = helpers.create_user_with_token()
        header, _ = helpers.create_full_proforma(owner)

        self.client.login(username=user.username, password=password)
        response = self.client.get(f'/product/get_proforma_car_part_info/{header.id}')

        self.assertEqual(response.status_code, 403)

    def test_admin_group_staff_can_see_any_sucursal(self):
        admin_user, password = helpers.create_staff_user()
        helpers.add_user_to_group(admin_user, 'Admin')
        owner, _ = helpers.create_user_with_token()
        header, _ = helpers.create_full_proforma(owner)

        self.client.login(username=admin_user.username, password=password)
        response = self.client.get(f'/product/get_proforma_car_part_info/{header.id}')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['sales_type'], header.sales_type)
        self.assertIn('items', data)
        self.assertIn('window_film', data)
        self.assertIn('inv_widths', data)

    def test_staff_of_same_sucursal_can_see_proforma(self):
        owner, _ = helpers.create_user_with_token()
        header, _ = helpers.create_full_proforma(owner)
        staff_user, password = helpers.create_staff_user()
        header.sucursal.empleado.add(staff_user)

        self.client.login(username=staff_user.username, password=password)
        response = self.client.get(f'/product/get_proforma_car_part_info/{header.id}')

        self.assertEqual(response.status_code, 200)

    def test_staff_of_other_sucursal_gets_404(self):
        owner, _ = helpers.create_user_with_token()
        header, _ = helpers.create_full_proforma(owner)
        staff_user, password = helpers.create_staff_user()
        helpers.create_sucursal(staff_user)  # sucursal distinta a la de la proforma

        self.client.login(username=staff_user.username, password=password)
        response = self.client.get(f'/product/get_proforma_car_part_info/{header.id}')

        self.assertEqual(response.status_code, 404)

    def test_staff_without_sucursal_gets_403(self):
        staff_user, password = helpers.create_staff_user()
        owner, _ = helpers.create_user_with_token()
        header, _ = helpers.create_full_proforma(owner)

        self.client.login(username=staff_user.username, password=password)
        response = self.client.get(f'/product/get_proforma_car_part_info/{header.id}')

        self.assertEqual(response.status_code, 403)

    def test_nonexistent_proforma_returns_404_for_valid_staff(self):
        admin_user, password = helpers.create_staff_user()
        helpers.add_user_to_group(admin_user, 'Admin')

        self.client.login(username=admin_user.username, password=password)
        response = self.client.get('/product/get_proforma_car_part_info/999999')

        self.assertEqual(response.status_code, 404)
