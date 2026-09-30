"""Tests de TASK-mejora-inventario-bobinas: asignacion FIFO multi-fila con
movimientos, devolucion fila por fila, regla de ancho exacto, precio
determinista, validacion de metros, catalogo sin N+1, unicidad de precios y
concurrencia (ADR-mejora-inventario-bobinas-asignacion-y-movimientos /
-regla-ancho-y-precio)."""
import io
import threading
from datetime import timedelta
from decimal import Decimal

from django.contrib.admin.sites import AdminSite
from django.core.management import call_command
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import RequestFactory, TestCase, TransactionTestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from . import helpers
from .test_orden_estado_service import OrdenEstadoBase
from ..admin_config.report_storage import ReportStorageAdmin
from ..admin_config.report_utilidad import ReportUtilidadAdmin
from ..business.inventario import Inventario_Business
from ..business.pricing import Pricing_Business, build_line_pricing
from ..helper.pdf import PDFService
from ..helper.proforma import Proforma_Helper
from ..models import (Detalle_Nota_Trabajo, Inventario_Movimiento, Proforma_Detail, Window_Film_Reel, inventario,
                      inventario_proxy, precio_venta_sucursal, utilidades)
from ..utils.exception.nohaylaminas import NoHayLaminasDisponibles
from ..utils.exception.proforma import ProformaException


class InventarioBase(TestCase):
    def setUp(self):
        self.user, _ = helpers.create_user_with_token()
        self.sucursal = helpers.create_sucursal(self.user)
        self.film = helpers.create_window_film()
        self.reel = helpers.create_window_film_reel(window_film=self.film, width=Decimal('1.50'))
        self.business = Inventario_Business()

    def make_row(self, meters, days_ago=0, price=Decimal('120.00'), reel=None, sucursal=None):
        row = helpers.create_inventario(
            sucursal=sucursal or self.sucursal, bobina=reel or self.reel,
            to_install=Decimal(meters), precio_venta_mtr_lineal=price,
        )
        inventario.objects.filter(pk=row.pk).update(date=timezone.now() - timedelta(days=days_ago))
        return inventario.objects.get(pk=row.pk)

    def make_detail(self):
        _header, detail = helpers.create_full_proforma(user=self.user, sucursal=self.sucursal, window_film=self.film)
        return detail

    def to_install(self, row):
        return inventario.objects.get(pk=row.pk).to_install

    def reduce(self, meters, detail=None):
        return self.business.reduce_inventory(
            sucursal=self.sucursal, windows_film=self.film, width=Decimal('1.50'),
            length_to_reduce=Decimal(meters), proforma_detail=detail,
        )


class AsignacionTest(InventarioBase):
    def test_una_fila_suficiente(self):
        row = self.make_row('50.00')
        assignments = self.reduce('20.00')
        self.assertEqual([(r.pk, m) for r, m in assignments], [(row.pk, Decimal('20.00'))])
        refreshed = inventario.objects.get(pk=row.pk)
        self.assertEqual(refreshed.to_install, Decimal('30.00'))
        self.assertEqual(refreshed.installed, Decimal('20.00'))
        movement = Inventario_Movimiento.objects.get()
        self.assertEqual((movement.tipo, movement.metros, movement.inventario_id), ('egreso', Decimal('20.00'), row.pk))

    def test_reparte_fifo_entre_varias_filas(self):
        newer = self.make_row('30.00', days_ago=1)
        older = self.make_row('30.00', days_ago=10)
        detail = self.make_detail()
        assignments = self.reduce('50.00', detail=detail)

        self.assertEqual([(r.pk, m) for r, m in assignments], [(older.pk, Decimal('30.00')), (newer.pk, Decimal('20.00'))])
        self.assertEqual(self.to_install(older), Decimal('0.00'))
        self.assertEqual(self.to_install(newer), Decimal('10.00'))
        movements = Inventario_Movimiento.objects.filter(proforma_detail=detail, tipo='egreso')
        self.assertEqual(sum(m.metros for m in movements), Decimal('50.00'))
        self.assertEqual(movements.count(), 2)

    def test_suma_insuficiente_no_deja_cambios(self):
        a = self.make_row('30.00', days_ago=2)
        b = self.make_row('30.00', days_ago=1)
        with self.assertRaises(NoHayLaminasDisponibles):
            self.reduce('70.00')
        self.assertEqual(self.to_install(a), Decimal('30.00'))
        self.assertEqual(self.to_install(b), Decimal('30.00'))
        self.assertFalse(Inventario_Movimiento.objects.exists())

    def test_metros_no_positivos_se_rechazan(self):
        self.make_row('30.00')
        with self.assertRaises(NoHayLaminasDisponibles):
            self.reduce('0')

    def test_filas_no_elegibles_se_excluyen(self):
        good = self.make_row('10.00')
        inactive_row = self.make_row('100.00')
        inventario.objects.filter(pk=inactive_row.pk).update(is_active=False)
        inactive_reel = Window_Film_Reel.objects.create(
            window_film=self.film, width=Decimal('1.50'), length=Decimal('30.00'), price=Decimal('1.00'), is_active=False)
        self.make_row('100.00', reel=inactive_reel)
        other_width = helpers.create_window_film_reel(window_film=self.film, width=Decimal('2.00'))
        self.make_row('100.00', reel=other_width)
        other_sucursal = helpers.create_sucursal(self.user)
        self.make_row('100.00', sucursal=other_sucursal)

        self.assertEqual(self.business.get_available_meters(self.sucursal.id, self.film.id, Decimal('1.50')), Decimal('10.00'))
        with self.assertRaises(NoHayLaminasDisponibles):
            self.reduce('11.00')
        self.assertEqual(self.to_install(good), Decimal('10.00'))

    def test_sucursal_deshabilitada_no_vende(self):
        self.make_row('50.00')
        self.sucursal.enable_to_install_windows_film = False
        self.sucursal.save()
        with self.assertRaises(NoHayLaminasDisponibles):
            self.reduce('1.00')


class DevolucionTest(InventarioBase):
    def test_devuelve_exactamente_lo_descontado_fila_por_fila(self):
        older = self.make_row('30.00', days_ago=10)
        newer = self.make_row('30.00', days_ago=1)
        detail = self.make_detail()
        self.reduce('50.00', detail=detail)

        returned = self.business.return_detail_to_inventory(detail)

        self.assertEqual(returned, Decimal('50.00'))
        for row in (older, newer):
            refreshed = inventario.objects.get(pk=row.pk)
            self.assertEqual(refreshed.to_install, Decimal('30.00'))
            self.assertEqual(refreshed.installed, Decimal('0.00'))
        returns = Inventario_Movimiento.objects.filter(proforma_detail=detail, tipo='devolucion')
        self.assertEqual(sorted(m.metros for m in returns), [Decimal('20.00'), Decimal('30.00')])

    def test_devolver_dos_veces_es_idempotente(self):
        row = self.make_row('30.00')
        detail = self.make_detail()
        self.reduce('10.00', detail=detail)
        self.business.return_detail_to_inventory(detail)
        self.assertEqual(self.business.return_detail_to_inventory(detail), Decimal('0'))
        self.assertEqual(self.to_install(row), Decimal('30.00'))

    def test_detalle_anterior_a_los_movimientos_devuelve_a_su_fila(self):
        row = self.make_row('30.00')
        inventario.objects.filter(pk=row.pk).update(to_install=Decimal('24.00'), installed=Decimal('6.00'))
        detail = self.make_detail()
        Proforma_Detail.objects.filter(pk=detail.pk).update(inventario=row, length=Decimal('2.00'), quantity=3)
        detail.refresh_from_db()

        returned = self.business.return_detail_to_inventory(detail)

        self.assertEqual(returned, Decimal('6.00'))
        refreshed = inventario.objects.get(pk=row.pk)
        self.assertEqual((refreshed.to_install, refreshed.installed), (Decimal('30.00'), Decimal('0.00')))

    def test_detalle_sin_movimientos_ni_inventario_no_falla(self):
        detail = self.make_detail()
        with self.assertLogs('django_admin', level='ERROR'):
            self.assertEqual(self.business.return_detail_to_inventory(detail), Decimal('0'))


class CicloDeLaOrdenConRepartoTest(OrdenEstadoBase):
    """Aprobar / anular / re-aprobar / borrar con stock repartido en dos filas
    (regresion de test_orden_estado_service con el nuevo reparto)."""

    def setUp(self):
        super().setUp()
        inventario.objects.filter(pk=self.inv.pk).update(to_install=Decimal('30.00'), date=timezone.now() - timedelta(days=5))
        self.inv2 = helpers.create_inventario(sucursal=self.sucursal, bobina=self.inv.bobina, to_install=Decimal('30.00'))
        Proforma_Detail.objects.filter(pk=self.detail.pk).update(length=Decimal('25.00'), quantity=2)  # 50 m

    def saldos(self):
        return (inventario.objects.get(pk=self.inv.pk).to_install, inventario.objects.get(pk=self.inv2.pk).to_install)

    def test_aprobar_reparte_y_anular_devuelve_a_cada_fila(self):
        nota = self.aprobar()
        self.assertEqual(self.saldos(), (Decimal('0.00'), Decimal('10.00')))
        detail = Proforma_Detail.objects.get(pk=self.detail.pk)
        self.assertEqual(detail.inventario_id, self.inv.pk)  # primera fila usada
        self.assertEqual(Inventario_Movimiento.objects.filter(proforma_detail=detail, tipo='egreso').count(), 2)

        self.svc.anular_nota_trabajo(nota)
        self.assertEqual(self.saldos(), (Decimal('30.00'), Decimal('30.00')))
        self.assertIsNone(Proforma_Detail.objects.get(pk=self.detail.pk).inventario)

        self.aprobar()  # re-aprobar vuelve a asignar
        self.assertEqual(self.saldos(), (Decimal('0.00'), Decimal('10.00')))

    def test_borrar_la_nota_desde_admin_devuelve_a_cada_fila(self):
        from ..business.orden_trabajo import Orden_Trabajo_Business
        nota = self.aprobar()
        Orden_Trabajo_Business().delete_work_note(nota)
        self.assertEqual(self.saldos(), (Decimal('30.00'), Decimal('30.00')))

    def test_borrar_una_nota_ya_cancelada_no_devuelve_dos_veces(self):
        from ..business.orden_trabajo import Orden_Trabajo_Business
        nota = self.aprobar()
        self.svc.anular_nota_trabajo(nota)
        Orden_Trabajo_Business().delete_work_note(nota)
        self.assertEqual(self.saldos(), (Decimal('30.00'), Decimal('30.00')))

    def test_stock_insuficiente_no_aprueba_ni_descuenta(self):
        Proforma_Detail.objects.filter(pk=self.detail.pk).update(length=Decimal('40.00'), quantity=2)  # 80 m > 60 m
        with self.assertRaises(Exception):
            self.aprobar()
        self.assertEqual(self.saldos(), (Decimal('30.00'), Decimal('30.00')))
        self.assertEqual(self.reload_header().status, 'proforma')


class PdfYReportesConRepartoTest(OrdenEstadoBase):
    """Criterio de aceptacion 10 del plan: la hoja de trabajo en PDF y los reportes de
    almacen y utilidades siguen funcionando con una linea repartida en dos lotes
    (REV-2026-09-30-mejora-inventario-bobinas-02). Solo verifica que se generan y que los
    saldos agregados son correctos; que muestren todos los lotes esta diferido."""

    def setUp(self):
        super().setUp()
        inventario.objects.filter(pk=self.inv.pk).update(
            to_install=Decimal('30.00'), nro_lote='L100', date=timezone.now() - timedelta(days=5))
        self.inv2 = helpers.create_inventario(sucursal=self.sucursal, bobina=self.inv.bobina, to_install=Decimal('30.00'))
        inventario.objects.filter(pk=self.inv2.pk).update(nro_lote='L200')
        Proforma_Detail.objects.filter(pk=self.detail.pk).update(length=Decimal('25.00'), quantity=2)  # 50 m
        self.nota = self.aprobar()

    def request(self):
        request = RequestFactory().get('/admin/')
        request.user = self.user
        return request

    def test_pdf_de_la_hoja_de_trabajo(self):
        buffer = io.BytesIO()
        resumen = Detalle_Nota_Trabajo.objects.select_related('window_film', 'nota_trabajo__proforma').filter(nota_trabajo=self.nota)
        detalle = Proforma_Detail.objects.filter(proforma_header=self.nota.proforma).select_related('inventario')
        PDFService(buffer=buffer).create_nota_trabajo(detail=resumen, nota_trabajo=self.nota, proforma_detail=detalle)
        self.assertGreater(len(buffer.getvalue()), 500)

    def test_reporte_de_almacen_suma_los_dos_lotes(self):
        admin_storage = ReportStorageAdmin(model=inventario_proxy, admin_site=AdminSite())
        list(admin_storage.get_queryset(self.request()))
        (row,) = list(admin_storage.aggregated_result)
        self.assertEqual(row['total_to_install'], Decimal('10.00'))
        self.assertEqual(row['total_installed'], Decimal('50.00'))

    def test_reporte_de_utilidades_se_genera(self):
        admin_utilidad = ReportUtilidadAdmin(model=utilidades, admin_site=AdminSite())
        rows = list(admin_utilidad.get_queryset(self.request()))
        self.assertGreaterEqual(len(rows), 1)
        self.assertTrue(all(row.sum_film_utilidad is not None for row in rows))


class PrecioYAnchoTest(InventarioBase):
    def setUp(self):
        super().setUp()
        self.pricing = Pricing_Business()

    def resolve(self, width='1.50'):
        return self.pricing.resolve_unit_price(self.sucursal.id, self.film.id, Decimal(width))

    def test_ancho_exacto_no_toma_una_bobina_mas_ancha(self):
        self.make_row('50.00')
        self.assertIsNone(self.resolve('1.00'))
        self.assertFalse(self.pricing.has_stock_for_reel(self.sucursal.id, self.film, Decimal('1.00')))
        self.assertEqual(self.resolve('1.50'), Decimal('120.00'))

    def test_override_de_sucursal_tiene_prioridad(self):
        self.make_row('50.00')
        helpers.create_precio_venta_sucursal(self.sucursal, self.film, width=Decimal('1.50'), precio_venta=Decimal('150.00'))
        self.assertEqual(self.resolve(), Decimal('150.00'))

    def test_con_lotes_de_distinto_precio_usa_la_fila_fifo(self):
        older = self.make_row('10.00', days_ago=10, price=Decimal('100.00'))
        self.make_row('10.00', days_ago=1, price=Decimal('200.00'))
        self.assertEqual(self.resolve(), Decimal('100.00'))
        inventario.objects.filter(pk=older.pk).update(to_install=Decimal('0.00'))
        self.assertEqual(self.resolve(), Decimal('200.00'))

    def test_sin_stock_devuelve_none(self):
        self.assertIsNone(self.resolve())
        self.assertIsNone(self.pricing.resolve_unit_price(self.sucursal.id, None, Decimal('1.50')))

    def test_el_precio_es_decimal_sin_perdida(self):
        self.make_row('50.00', price=Decimal('120.35'))
        price = self.resolve()
        self.assertIsInstance(price, Decimal)
        self.assertEqual(price, Decimal('120.35'))


class ValidacionDeMetrosTest(InventarioBase):
    def setUp(self):
        super().setUp()
        self.car_model = helpers.create_model()
        self.car_part = helpers.create_car_part()
        helpers.create_car_model_part(car_model=self.car_model, car_part=self.car_part, width=Decimal('1.50'))
        self.helper = Proforma_Helper()

    def line(self, length, quantity, car_part=True):
        return {'car_part': self.car_part if car_part else None, 'window_film': self.film, 'width': Decimal('1.50'),
                'length': Decimal(length), 'quantity': quantity}

    def test_instalacion_multiplica_largo_por_cantidad(self):
        self.make_row('30.00')
        self.make_row('20.00')
        result = build_line_pricing(self.helper.tipo_venta_instalacion, self.car_model, self.sucursal, self.line('10.00', 5))
        self.assertEqual(result['quantity'], 5)  # 50 m disponibles sumando dos filas
        with self.assertRaises(ProformaException) as ctx:
            build_line_pricing(self.helper.tipo_venta_instalacion, self.car_model, self.sucursal, self.line('10.00', 6))
        self.assertIn('No hay metros suficientes', str(ctx.exception))

    def test_metro_lineal_usa_solo_el_largo(self):
        self.make_row('30.00')
        result = build_line_pricing(self.helper.tipo_venta_metro_lineal, None, self.sucursal, self.line('30.00', 0, car_part=False))
        self.assertEqual(result['sub_total'], Decimal('3600.00'))
        with self.assertRaises(ProformaException):
            build_line_pricing(self.helper.tipo_venta_metro_lineal, None, self.sucursal, self.line('30.01', 0, car_part=False))


class CatalogoTest(InventarioBase):
    def test_contenido_precio_y_orden(self):
        other_film = helpers.create_window_film()
        reel_b = helpers.create_window_film_reel(window_film=other_film, width=Decimal('1.00'))
        self.make_row('10.00', days_ago=5, price=Decimal('100.00'))
        self.make_row('15.00', days_ago=1, price=Decimal('200.00'))
        self.make_row('7.00', reel=reel_b, price=Decimal('80.00'))
        helpers.create_precio_venta_sucursal(self.sucursal, other_film, width=Decimal('1.00'), precio_venta=Decimal('95.00'))

        catalog = Pricing_Business().get_reel_catalog(self.sucursal.id)

        by_film = {item['window_film']: item for item in catalog}
        self.assertEqual(by_film[self.film.id]['available_meters'], Decimal('25.00'))
        self.assertEqual(by_film[self.film.id]['unit_price'], Decimal('100.00'))  # fila FIFO
        self.assertEqual(by_film[other_film.id]['unit_price'], Decimal('95.00'))  # override
        self.assertEqual([i['window_film_name'] for i in catalog], sorted(i['window_film_name'] for i in catalog))

    def test_cantidad_de_consultas_no_crece_con_las_bobinas(self):
        self.make_row('10.00')
        with CaptureQueriesContext(connection) as one:
            Pricing_Business().get_reel_catalog(self.sucursal.id)
        for _ in range(4):
            film = helpers.create_window_film()
            self.make_row('5.00', reel=helpers.create_window_film_reel(window_film=film, width=Decimal('1.50')))
        with CaptureQueriesContext(connection) as many:
            catalog = Pricing_Business().get_reel_catalog(self.sucursal.id)
        self.assertEqual(len(catalog), 5)
        self.assertEqual(len(one), len(many))


class UnicidadDePreciosTest(TestCase):
    def test_no_admite_duplicados(self):
        user, _ = helpers.create_user_with_token()
        sucursal = helpers.create_sucursal(user)
        film = helpers.create_window_film()
        helpers.create_precio_venta_sucursal(sucursal, film)
        with self.assertRaises(IntegrityError), transaction.atomic():
            helpers.create_precio_venta_sucursal(sucursal, film)
        helpers.create_precio_venta_sucursal(sucursal, film, width=Decimal('2.00'))  # otro ancho: permitido


class MigracionUnicidadDePreciosTest(TransactionTestCase):
    ANTERIOR = ('product', '0113_inventario_movimiento')
    ACTUAL = ('product', '0114_precio_venta_sucursal_unico')

    def tearDown(self):
        call_command('migrate', 'product', self.ACTUAL[1], verbosity=0)

    def historic(self):
        apps = MigrationExecutor(connection).loader.project_state([self.ANTERIOR]).apps
        return (apps.get_model('product', 'Sucursal'), apps.get_model('product', 'Window_Film'),
                apps.get_model('product', 'precio_venta_sucursal'))

    def test_con_duplicados_aborta_sin_modificar_datos_y_sin_duplicados_aplica(self):
        call_command('migrate', 'product', self.ANTERIOR[1], verbosity=0)
        Sucursal, Film, Precio = self.historic()
        sucursal = Sucursal.objects.create(name='S', address='A', enable_to_install_windows_film=True, phone_number='70000000')
        film = Film.objects.create(name='F', description='d')
        for price in ('10.00', '20.00'):
            Precio.objects.create(sucursal=sucursal, lamina=film, width=Decimal('1.50'), precio_venta=Decimal(price))

        with self.assertRaises(RuntimeError) as ctx:
            call_command('migrate', 'product', self.ACTUAL[1], verbosity=0)
        self.assertIn('precios duplicados', str(ctx.exception))
        self.assertEqual(Precio.objects.count(), 2)  # no se borro nada

        Precio.objects.filter(precio_venta=Decimal('20.00')).delete()
        call_command('migrate', 'product', self.ACTUAL[1], verbosity=0)
        self.assertEqual(precio_venta_sucursal.objects.count(), 1)

    def test_reverso_elimina_la_restriccion(self):
        call_command('migrate', 'product', self.ANTERIOR[1], verbosity=0)
        Sucursal, Film, Precio = self.historic()
        sucursal = Sucursal.objects.create(name='S', address='A', enable_to_install_windows_film=True, phone_number='70000000')
        film = Film.objects.create(name='F', description='d')
        Precio.objects.create(sucursal=sucursal, lamina=film, width=Decimal('1.50'), precio_venta=Decimal('10.00'))
        Precio.objects.create(sucursal=sucursal, lamina=film, width=Decimal('1.50'), precio_venta=Decimal('20.00'))
        self.assertEqual(Precio.objects.count(), 2)
        Precio.objects.all().delete()  # tearDown vuelve a aplicar la restriccion


class ConcurrenciaTest(TransactionTestCase):
    """Dos aprobaciones simultaneas sobre las mismas filas (Postgres real): el
    bloqueo impide el descuento doble y el saldo negativo."""

    def test_dos_descuentos_concurrentes_no_exceden_el_stock(self):
        user, _ = helpers.create_user_with_token()
        sucursal = helpers.create_sucursal(user)
        film = helpers.create_window_film()
        reel = helpers.create_window_film_reel(window_film=film, width=Decimal('1.50'))
        row = helpers.create_inventario(sucursal=sucursal, bobina=reel, to_install=Decimal('30.00'))
        barrier = threading.Barrier(2)
        results = []

        def worker():
            try:
                barrier.wait(timeout=10)
                with transaction.atomic():
                    Inventario_Business().reduce_inventory(sucursal, film, Decimal('1.50'), Decimal('20.00'))
                results.append('ok')
            except NoHayLaminasDisponibles:
                results.append('sin_stock')
            except Exception as e:  # pragma: no cover - deja evidencia en el assert
                results.append(repr(e))
            finally:
                connection.close()

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        self.assertEqual(sorted(results), ['ok', 'sin_stock'])
        refreshed = inventario.objects.get(pk=row.pk)
        self.assertEqual(refreshed.to_install, Decimal('10.00'))
        self.assertEqual(refreshed.installed, Decimal('20.00'))
        self.assertEqual(sum(m.metros for m in Inventario_Movimiento.objects.filter(tipo='egreso')), Decimal('20.00'))

    def test_dos_devoluciones_concurrentes_del_mismo_detalle_devuelven_una_sola_vez(self):
        """REV-2026-09-30-mejora-inventario-bobinas-01: delete_work_note no bloquea la
        proforma, asi que la propia devolucion debe ser segura ante llamadas simultaneas."""
        user, _ = helpers.create_user_with_token()
        sucursal = helpers.create_sucursal(user)
        film = helpers.create_window_film()
        reel = helpers.create_window_film_reel(window_film=film, width=Decimal('1.50'))
        row = helpers.create_inventario(sucursal=sucursal, bobina=reel, to_install=Decimal('30.00'))
        _header, detail = helpers.create_full_proforma(user=user, sucursal=sucursal, window_film=film)
        Inventario_Business().reduce_inventory(sucursal, film, Decimal('1.50'), Decimal('10.00'), proforma_detail=detail)
        barrier = threading.Barrier(2)
        errors = []

        def worker():
            try:
                barrier.wait(timeout=10)
                with transaction.atomic():
                    Inventario_Business().return_detail_to_inventory(detail)
            except Exception as e:  # pragma: no cover - deja evidencia en el assert
                errors.append(repr(e))
            finally:
                connection.close()

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        self.assertEqual(errors, [])
        refreshed = inventario.objects.get(pk=row.pk)
        self.assertEqual((refreshed.to_install, refreshed.installed), (Decimal('30.00'), Decimal('0.00')))
        devoluciones = Inventario_Movimiento.objects.filter(proforma_detail=detail, tipo='devolucion')
        self.assertEqual(sum(m.metros for m in devoluciones), Decimal('10.00'))
