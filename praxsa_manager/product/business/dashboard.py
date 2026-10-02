"""Consultas agregadas del dashboard del panel (todas de solo lectura). Ver
ADR-dashboard-taller-laminas-api-agregados-alcance y -definiciones-metricas.

Reglas:
- El alcance por sucursal sale SIEMPRE de los metodos `get_panel_*` existentes
  (sucursales asignadas al usuario; solo el superusuario ve todo; sin sucursal,
  nada). Sin sucursal elegida, "Todas" = las activas de su alcance.
- Las ventas cobradas se toman de `Reportes_Business` (`pagos_cobrados`,
  `filtrar_pagos`): `cobrado = pago.monto`, igual que Ventas Diarias. No se
  calculan costos ni utilidad aqui.
- Todo el dinero es Decimal. Con USE_TZ=False las fechas son naive locales;
  `hoy` se recibe como parametro (nunca `timezone.localdate()`).
"""
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Case, Count, DecimalField, ExpressionWrapper, F, IntegerField, Prefetch, Q, Sum, Value, When
from django.db.models.functions import TruncMonth

from ..helper import estados
from ..helper.dashboard import (
    COLA_MAX, CONSUMO_MAX_SERIES, ITEMS_MAX, RECIENTES_MAX, STOCK_BAJO, STOCK_BAJO_METROS,
    STOCK_CRITICO, STOCK_CRITICO_METROS, STOCK_OK,
)
from ..helper.proforma import Proforma_Helper
from ..helper.user import User_Helper
from ..models import Detalle_Nota_Trabajo, Nota_trabajo, Proforma_Detail, Proforma_Header, inventario
from .inventario import Inventario_Business
from .orden_trabajo import Orden_Trabajo_Business
from .pago import Pago_Business
from .proforma import Proforma_Business
from .reportes import Reportes_Business, q2

CERO = Decimal('0.00')
_DINERO = DecimalField(max_digits=14, decimal_places=2)


def primer_dia(fecha):
    return fecha.replace(day=1)


def ultimo_dia(fecha):
    siguiente = (fecha.replace(day=28) + timedelta(days=4)).replace(day=1)
    return siguiente - timedelta(days=1)


def mes_anterior(fecha):
    return primer_dia(primer_dia(fecha) - timedelta(days=1))


def meses_hasta(hoy, cantidad):
    """Primer dia de cada uno de los ultimos `cantidad` meses, el actual al final."""
    meses = [primer_dia(hoy)]
    while len(meses) < cantidad:
        meses.insert(0, mes_anterior(meses[0]))
    return meses


def clave_mes(fecha):
    return fecha.strftime('%Y-%m')


def porcentaje(numerador, denominador):
    if not denominador:
        return None
    return (Decimal(numerador) * 100 / Decimal(denominador)).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)


def estado_stock(metros):
    if metros < STOCK_CRITICO_METROS:
        return STOCK_CRITICO
    if metros < STOCK_BAJO_METROS:
        return STOCK_BAJO
    return STOCK_OK


class Dashboard_Business:

    def __init__(self):
        self.user_helper = User_Helper()
        self.reportes = Reportes_Business()
        self.pago_business = Pago_Business()
        self.helper = Proforma_Helper()

    # ------------------------------------------------------------------ alcance
    def sin_sucursal(self, user):
        return (
            not self.user_helper.can_view_all_sucursales(user)
            and not self.user_helper.has_assigned_sucursal(user)
        )

    def _sucursal_ids(self, user, sucursal_id):
        """[sucursal elegida] o, sin elegir, las sucursales activas del alcance
        del usuario (las inactivas solo se ven si se eligen explicitamente)."""
        if sucursal_id is not None:
            return [sucursal_id]
        return self.user_helper.get_writable_sucursal_ids(user)

    def _proformas(self, user, sucursal_id):
        qs = Proforma_Business().get_panel_proforma_queryset(user, Proforma_Header.objects.all())
        return qs.filter(sucursal_id__in=self._sucursal_ids(user, sucursal_id))

    def _notas(self, user, sucursal_id):
        qs = Orden_Trabajo_Business().get_panel_nota_queryset(user, Nota_trabajo.objects.all())
        return qs.filter(proforma__sucursal_id__in=self._sucursal_ids(user, sucursal_id))

    def _pagos(self, user, desde, hasta, sucursal_id):
        qs = self.pago_business.get_panel_pago_queryset(user, self.reportes.pagos_cobrados())
        return self.reportes.filtrar_pagos(
            qs, desde=desde, hasta=hasta, sucursal_ids=self._sucursal_ids(user, sucursal_id)
        ).order_by()

    def _inventario(self, user, sucursal_id):
        qs = inventario.objects.filter(
            is_active=True, bobina__is_active=True, bobina__window_film__is_active=True,
            sucursal__enable_to_install_windows_film=True,
        )
        qs = Inventario_Business().get_panel_inventario_queryset(user, qs)
        return qs.filter(sucursal_id=sucursal_id) if sucursal_id is not None else qs

    def _emitidas(self, proformas):
        """Proformas emitidas (no anuladas); la anulada no cuenta como cotizada."""
        return proformas.exclude(status=self.helper.estado_anulada)

    # ------------------------------------------------------------------ KPIs
    def _total_cobrado(self, user, desde, hasta, sucursal_id):
        total = self._pagos(user, desde, hasta, sucursal_id).aggregate(total=Sum('monto'))['total']
        return q2(total or CERO)

    def ventas(self, user, hoy, sucursal_id=None):
        """Ventas cobradas del mes actual y del mes previo (mismos criterios que Ventas Diarias)."""
        inicio = primer_dia(hoy)
        previo = mes_anterior(hoy)
        mes = self._total_cobrado(user, inicio, ultimo_dia(inicio), sucursal_id)
        anterior = self._total_cobrado(user, previo, ultimo_dia(previo), sucursal_id)
        variacion = None
        if anterior > 0:
            variacion = ((mes - anterior) / anterior * 100).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
        return {'mes': mes, 'mes_anterior': anterior, 'variacion': variacion}

    def proformas_activas(self, user, sucursal_id=None):
        activas = self._proformas(user, sucursal_id).filter(status=self.helper.estado_proforma)
        datos = activas.order_by().aggregate(
            monto=Sum(ExpressionWrapper(F('total_price') - F('discount'), output_field=_DINERO)),
            cantidad=Count('id'),
        )
        return {'monto': q2(datos['monto'] or CERO), 'cantidad': datos['cantidad']}

    def conversion(self, user, hoy, sucursal_id=None):
        """Por cohorte de emision del mes: convertidas (ya tienen orden) / emitidas (no anuladas)."""
        inicio = primer_dia(hoy)
        emitidas = self._emitidas(self._proformas(user, sucursal_id)).filter(
            proforma_created_on__date__gte=inicio, proforma_created_on__date__lte=ultimo_dia(inicio),
        ).order_by()
        convertidas_estados = [
            self.helper.estado_en_trabajo, self.helper.estado_por_cobrar, self.helper.estado_finalizado,
        ]
        datos = emitidas.aggregate(
            emitidas=Count('id'), convertidas=Count('id', filter=Q(status__in=convertidas_estados)),
        )
        return {
            'convertidas': datos['convertidas'], 'emitidas': datos['emitidas'],
            'porcentaje': porcentaje(datos['convertidas'], datos['emitidas']),
        }

    def instalaciones(self, user, hoy, sucursal_id=None):
        notas = self._notas(user, sucursal_id).order_by()
        datos = notas.aggregate(
            en_taller=Count('id', filter=Q(status=estados.NT_EN_PROCESO)),
            terminadas_hoy=Count('id', filter=Q(status=estados.NT_TERMINADO, salida_vehiculo__date=hoy)),
        )
        return {'en_taller': datos['en_taller'], 'terminadas_hoy': datos['terminadas_hoy']}

    def kpis(self, user, hoy, sucursal_id=None, con_ventas=False):
        return {
            'ventas': self.ventas(user, hoy, sucursal_id) if con_ventas else None,
            'proformas_activas': self.proformas_activas(user, sucursal_id),
            'conversion': self.conversion(user, hoy, sucursal_id),
            'instalaciones': self.instalaciones(user, hoy, sucursal_id),
        }

    # ------------------------------------------------------------------ graficas
    def _por_mes(self, filas):
        return {clave_mes(fila['mes']): fila['total'] for fila in filas}

    def proformas_vs_ventas(self, user, hoy, meses, sucursal_id=None, con_ventas=False):
        rango = meses_hasta(hoy, meses)
        claves = [clave_mes(mes) for mes in rango]
        inicio = rango[0]
        cotizadas = self._emitidas(self._proformas(user, sucursal_id)).filter(
            proforma_created_on__date__gte=inicio,
        ).order_by().annotate(mes=TruncMonth('proforma_created_on')).values('mes').annotate(
            total=Sum(ExpressionWrapper(F('total_price') - F('discount'), output_field=_DINERO))
        )
        cotizado = self._por_mes(cotizadas)
        resultado = {'meses': claves, 'cotizado': [q2(cotizado.get(c) or CERO) for c in claves], 'vendido': None}
        if con_ventas:
            cobros = self._pagos(user, inicio, None, sucursal_id).annotate(
                mes=TruncMonth('created_on')
            ).values('mes').annotate(total=Sum('monto'))
            vendido = self._por_mes(cobros)
            resultado['vendido'] = [q2(vendido.get(c) or CERO) for c in claves]
        return resultado

    def consumo_laminas(self, user, hoy, meses, sucursal_id=None):
        """Metros consumidos por lamina y mes (resumen de la nota de trabajo, sin canceladas)."""
        rango = meses_hasta(hoy, meses)
        claves = [clave_mes(mes) for mes in rango]
        notas = self._notas(user, sucursal_id).exclude(status=estados.NT_CANCELADA).filter(
            nota_venta_created_on__date__gte=rango[0],
        ).values('pk')
        filas = Detalle_Nota_Trabajo.objects.filter(nota_trabajo__in=notas).order_by().annotate(
            mes=TruncMonth('nota_trabajo__nota_venta_created_on')
        ).values('mes', 'window_film__name').annotate(total=Sum('length'))
        por_lamina = {}
        for fila in filas:
            nombre = fila['window_film__name'] or 'Sin lámina'
            metros = por_lamina.setdefault(nombre, {})
            clave = clave_mes(fila['mes'])
            metros[clave] = metros.get(clave, CERO) + fila['total']
        orden = sorted(por_lamina, key=lambda n: (-sum(por_lamina[n].values()), n))
        principales, otras = orden[:CONSUMO_MAX_SERIES], orden[CONSUMO_MAX_SERIES:]
        series = []
        for nombre in principales:
            series.append(self._serie_metros(nombre, por_lamina[nombre], claves))
        if otras:
            resto = {}
            for nombre in otras:
                for clave, metros in por_lamina[nombre].items():
                    resto[clave] = resto.get(clave, CERO) + metros
            series.append(self._serie_metros('Otras', resto, claves))
        return {'meses': claves, 'series': series}

    def _serie_metros(self, nombre, metros_por_mes, claves):
        metros = [q2(metros_por_mes.get(c) or CERO) for c in claves]
        return {'nombre': nombre, 'metros': metros, 'total': sum(metros, CERO)}

    def items_solicitados(self, user, hoy, meses, sucursal_id=None):
        """Lineas de proforma por item del vehiculo (solo ventas con instalacion: el metro lineal no tiene item)."""
        inicio = meses_hasta(hoy, meses)[0]
        proformas = self._emitidas(self._proformas(user, sucursal_id)).filter(
            proforma_created_on__date__gte=inicio,
        ).values('pk')
        filas = list(
            Proforma_Detail.objects.filter(proforma_header__in=proformas, car_part__isnull=False)
            .order_by().values('car_part__name').annotate(cantidad=Count('id'))
            .order_by('-cantidad', 'car_part__name')
        )
        items = [{'nombre': f['car_part__name'], 'cantidad': f['cantidad']} for f in filas[:ITEMS_MAX]]
        resto = sum(f['cantidad'] for f in filas[ITEMS_MAX:])
        if resto:
            items.append({'nombre': 'Otros', 'cantidad': resto})
        return {'total': sum(f['cantidad'] for f in filas), 'items': items}

    # ------------------------------------------------------------------ inventario
    def stock_critico(self, user, sucursal_id=None, todos=False):
        filas = list(
            self._inventario(user, sucursal_id).order_by().values(
                'sucursal_id', 'sucursal__name', 'bobina__window_film_id', 'bobina__window_film__name', 'bobina__width',
            ).annotate(metros=Sum('to_install'), rollos=Count('id', filter=Q(to_install__gt=0)))
        )
        grupos = []
        for fila in filas:
            metros = q2(fila['metros'] or CERO)
            grupos.append({
                'sucursal_id': fila['sucursal_id'], 'sucursal': fila['sucursal__name'],
                'lamina_id': fila['bobina__window_film_id'], 'lamina': fila['bobina__window_film__name'],
                'ancho': q2(fila['bobina__width']), 'metros': metros, 'rollos': fila['rollos'],
                'estado': estado_stock(metros),
            })
        contadores = {
            'criticos': sum(1 for g in grupos if g['estado'] == STOCK_CRITICO),
            'bajos': sum(1 for g in grupos if g['estado'] == STOCK_BAJO),
            'ok': sum(1 for g in grupos if g['estado'] == STOCK_OK),
        }
        if not todos:
            grupos = [g for g in grupos if g['estado'] != STOCK_OK]
        grupos.sort(key=lambda g: (g['metros'], g['lamina'] or '', g['sucursal'] or ''))
        return {
            'contadores': contadores, 'filas': grupos,
            'umbrales': {'critico': STOCK_CRITICO_METROS, 'bajo': STOCK_BAJO_METROS},
        }

    # ------------------------------------------------------------------ taller
    def cola_taller(self, user, hoy, sucursal_id=None):
        """Notas en proceso mas las terminadas hoy; en proceso primero, luego por ingreso."""
        notas = self._notas(user, sucursal_id).filter(
            Q(status=estados.NT_EN_PROCESO) | Q(status=estados.NT_TERMINADO, salida_vehiculo__date=hoy)
        )
        total = notas.count()
        prioridad = Case(
            When(status=estados.NT_EN_PROCESO, then=Value(0)), default=Value(1), output_field=IntegerField()
        )
        filas = notas.select_related('proforma__car_model_id', 'car_model', 'instaladar').prefetch_related(
            Prefetch('detalle_trabajo', queryset=Detalle_Nota_Trabajo.objects.select_related('window_film'))
        ).annotate(prioridad=prioridad).order_by('prioridad', F('entrada_vehiculo').asc(nulls_last=True), 'id')[:COLA_MAX]
        resultado = []
        for nota in filas:
            modelo = nota.car_model or nota.proforma.car_model_id
            detalles = sorted(nota.detalle_trabajo.all(), key=lambda d: -d.length)
            laminas = []
            for detalle in detalles:
                nombre = detalle.window_film.name if detalle.window_film_id else None
                if nombre and nombre not in laminas:
                    laminas.append(nombre)
            resultado.append({
                'nota_trabajo_id': nota.id, 'proforma_id': nota.proforma_id, 'cliente': nota.name,
                'modelo': modelo.name if modelo else None, 'placa': nota.car_plate or None,
                'laminas': laminas, 'status': nota.status, 'status_label': nota.get_status_display(),
                'instalador': nota.instaladar.name if nota.instaladar_id else None,
                'entrada_vehiculo': nota.entrada_vehiculo,
            })
        return {'total': total, 'filas': resultado}

    def proformas_recientes(self, user, sucursal_id=None):
        return list(self._proformas(user, sucursal_id).order_by('-id')[:RECIENTES_MAX])
