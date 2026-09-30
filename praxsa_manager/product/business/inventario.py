from decimal import Decimal

from ..models import Inventario_Movimiento, Sucursal, Window_Film, inventario, precio_venta_sucursal
from django.db import transaction
from django.db.models import Sum, F, OuterRef, Subquery
from ..utils.exception.nohaylaminas import NoHayLaminasDisponibles
from ..helper.user import User_Helper
import logging

class Inventario_Business:

    def __init__(self) -> None:
        self.log_errors = logging.getLogger('django_admin')
        self.log_debug= logging.getLogger('debug')
        self.user_helper = User_Helper()

    def get_inventario_queryset_by_role(self, user, qs):
        try:
            if self.user_helper.can_view_all_sucursales(user):
                return qs
            sucursales = Sucursal.objects.prefetch_related('empleado')
            sucursales = sucursales.filter(empleado__id = user.id, enable_to_install_windows_film = True)
            if len(sucursales) > 0:
                qs_result = qs.filter(sucursal__id = sucursales[0].id)
            else:
                qs_result = qs.none()
            return qs_result
        except Exception as e:
            self.log_errors.error(f'algo salio mal, Inventario_Business - get_inventario_queryset_by_role {e}')
            return qs.none()

    def get_inventory_by_sucursal(self, sucursal):
        q = inventario.objects.select_related("bobina","bobina__window_film", "sucursal")
        q = q.order_by('bobina__window_film__id', '-date')
        # q = q.distinct("bobina__window_film_id__id")
        q = q.filter(sucursal = sucursal, sucursal__enable_to_install_windows_film = True, to_install__gt = 0)
        return q

    def eligible_rows(self, sucursal_id, window_film_id=None, width=None):
        """Unico criterio de filas de inventario que pueden vender metros:
        sucursal habilitada, fila y bobina activas, con saldo. Si se pasan
        lamina/ancho, el ancho es **exacto** (ADR-mejora-inventario-bobinas-
        regla-ancho-y-precio). Orden FIFO (`date`, `id`): es el mismo orden en
        que `reduce_inventory` consume las filas y el que define el precio por
        defecto."""
        rows = inventario.objects.filter(
            sucursal_id=sucursal_id,
            sucursal__enable_to_install_windows_film=True,
            is_active=True,
            bobina__is_active=True,
            to_install__gt=0,
        )
        if window_film_id is not None:
            rows = rows.filter(bobina__window_film_id=window_film_id)
        if width is not None:
            rows = rows.filter(bobina__width=width)
        return rows.order_by('date', 'id')

    def get_available_meters(self, sucursal_id, window_film_id, width):
        """Metros que `reduce_inventory` podria descontar hoy de esa lamina/ancho."""
        total = self.eligible_rows(sucursal_id, window_film_id, width).aggregate(total=Sum('to_install'))['total']
        return total if total is not None else Decimal('0')

    def reduce_inventory(self, sucursal, windows_film, width, length_to_reduce, proforma_detail=None, created_by=None):
        """Descuenta `length_to_reduce` metros repartiendolos FIFO entre las filas
        elegibles de esa lamina/ancho, bajo bloqueo (`select_for_update`, solo
        las filas de inventario). Si la suma disponible no alcanza, lanza
        NoHayLaminasDisponibles sin dejar ningun cambio. Devuelve la lista de
        asignaciones `(fila_de_inventario, metros)`, en el orden consumido, y
        registra un movimiento `egreso` por cada una."""
        length_to_reduce = Decimal(str(length_to_reduce))
        if length_to_reduce <= 0:
            raise NoHayLaminasDisponibles(f'los metros a descontar de {windows_film.name} {width} deben ser mayores a 0')
        sucursal_id = getattr(sucursal, 'id', sucursal)
        with transaction.atomic():
            rows = list(
                self.eligible_rows(sucursal_id, windows_film.id, width)
                .select_related('bobina', 'sucursal')
                .select_for_update(of=('self',))
            )
            self.log_debug.info(f'reduce_inventory {sucursal_id} {windows_film} {width} {length_to_reduce}: {len(rows)} filas elegibles')
            remaining = length_to_reduce
            assignments = []
            for row in rows:
                if remaining <= 0:
                    break
                taken = min(row.to_install, remaining)
                row.to_install = row.to_install - taken
                row.installed = row.installed + taken
                row.save(update_fields=['to_install', 'installed'])
                Inventario_Movimiento.objects.create(
                    inventario=row, proforma_detail=proforma_detail, tipo=Inventario_Movimiento.EGRESO,
                    metros=taken, created_by=created_by,
                )
                assignments.append((row, taken))
                remaining = remaining - taken
            if remaining > 0:
                raise NoHayLaminasDisponibles(f'no hay lamina disponible {windows_film.name} {width}')
            return assignments

    def return_detail_to_inventory(self, detalle, created_by=None):
        """Devuelve al inventario los metros que `detalle` tomo, exactamente
        fila por fila. Usa los movimientos del detalle (egresos menos
        devoluciones ya hechas); si no tiene movimientos pero si `inventario`
        (orden aprobada antes de existir el registro de movimientos), devuelve
        a esa fila `length * quantity`. Devuelve los metros devueltos; 0 si no
        habia nada que devolver (un detalle ya devuelto es idempotente)."""
        with transaction.atomic():
            net = {}
            movimientos = list(Inventario_Movimiento.objects.filter(proforma_detail=detalle).values_list('tipo', 'inventario_id', 'metros'))
            for tipo, inventario_id, metros in movimientos:
                signo = 1 if tipo == Inventario_Movimiento.EGRESO else -1
                net[inventario_id] = net.get(inventario_id, Decimal('0')) + signo * metros
            net = {inventario_id: metros for inventario_id, metros in net.items() if metros > 0}
            if net:
                returned = Decimal('0')
                for row in inventario.objects.select_for_update().filter(id__in=list(net)).order_by('date', 'id'):
                    metros = net[row.id]
                    row.to_install = row.to_install + metros
                    row.installed = row.installed - metros
                    row.save(update_fields=['to_install', 'installed'])
                    Inventario_Movimiento.objects.create(
                        inventario=row, proforma_detail=detalle, tipo=Inventario_Movimiento.DEVOLUCION,
                        metros=metros, created_by=created_by,
                    )
                    returned = returned + metros
                return returned
            if movimientos:
                return Decimal('0')  # todo lo descontado ya se devolvio
            if detalle.inventario_id is None:
                self.log_errors.error(f'detalle {detalle.pk} sin movimientos ni inventario asociado: no hay metros que devolver')
                return Decimal('0')
            to_add = detalle.length * Decimal(detalle.quantity) if detalle.quantity > 0 else detalle.length
            row = inventario.objects.select_for_update().get(id=detalle.inventario_id)
            row.to_install = row.to_install + to_add
            row.installed = row.installed - to_add
            row.save(update_fields=['to_install', 'installed'])
            return to_add

    def get_total_meters_window_film_in_inventory(self, sucursal_id, lamina_id, width):
        inventario_qs = inventario.objects.filter(sucursal_id=sucursal_id,to_install__gt=0)

        if lamina_id > 0:
            inventario_qs = inventario_qs.filter(
                bobina__window_film_id=lamina_id
            )

        if width > 0:
            inventario_qs = inventario_qs.filter(
                bobina__width__gte=width
            )

        inventario_qs = inventario_qs.values(
                "sucursal_id",
                "bobina__window_film__id",
                "bobina__window_film__name",
                "bobina__width",
                "precio_venta_mtr_lineal"
            ).annotate(
                total_metros=Sum("to_install"),

                precio_sucursal=Subquery(
                    precio_venta_sucursal.objects.filter(
                        sucursal_id=OuterRef("sucursal_id"),
                        lamina_id=OuterRef("bobina__window_film__id"),
                        width=OuterRef("bobina__width")
                    ).values("precio_venta")[:1]
                )
            ).order_by(
                "bobina__window_film__name",
                "bobina__width"
            )

        return inventario_qs

    def get_user_inventory_window_films(self, user):
        query = inventario.objects.select_related("bobina","bobina__window_film", "sucursal")
        query = query.filter(sucursal__enable_to_install_windows_film = True, sucursal__empleado = user)
        query = query.order_by('bobina__window_film__id', 'bobina__width','date').distinct('bobina__window_film__id')
        query = query.annotate(film_id = F('bobina__window_film__id'))
        query = query.values_list('film_id')
        films = Window_Film.objects.filter(id__in = query)
        return films

    def get_inventory_window_film_reel_widths(self, user):
        query = inventario.objects.select_related("bobina","bobina__window_film", "sucursal")
        query = query.filter(sucursal__empleado = user)
        query = query.order_by('bobina__width',).distinct('bobina__width')
        query = query.annotate( width = F('bobina__width'))
        return query
