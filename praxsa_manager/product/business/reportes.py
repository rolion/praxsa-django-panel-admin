"""Calculo unico de los reportes de ventas cobradas y utilidad (Ventas Diarias y
Utilidad). Lo usan la API del panel y los ModelAdmin de Django Admin: ninguna
otra parte recalcula estas cifras. Ver
ADR-reportes-utilidad-ventas-diarias-calculo-y-api (con su Actualizacion 1).

Reglas (todo en Decimal, cada linea se redondea a centavos y todo lo demas es
suma de lineas ya redondeadas, por lo que tablas y totales siempre cuadran):
- Solo cuentan ventas cobradas: existe `pago`, la nota de venta esta `pagada`
  y la proforma no esta borrada. La fecha del reporte es la del pago.
- metros = largo * cantidad (si cantidad > 0), si no largo (igual que al
  descontar inventario en Orden_Estado_Business.aprobar_proforma).
- venta_lamina = metros * precio lamina; instalacion = precio instalacion *
  cantidad; bruto = venta_lamina + instalacion.
- costo de compra = suma por fila de inventario de (egresos - devoluciones) *
  precio_compra_mtr_lineal. Sin movimientos (venta anterior al registro de
  movimientos) se usa `detalle.inventario`; sin ninguno de los dos, o con
  precio de compra 0, el costo queda incompleto (`costo_incompleto`).
- utilidad_antes = venta_lamina - costo; utilidad_despues = utilidad_antes -
  descuento (la instalacion no entra en la utilidad).
- cobrado = pago.monto.
"""
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Q

from ..helper import estados
from ..helper.pagos import Pagos_Helper
from ..helper.proforma import Proforma_Helper
from ..models import Inventario_Movimiento, Proforma_Detail, inventario, pago

CENTS = Decimal('0.01')
CERO = Decimal('0.00')
MAX_DIAS_RANGO = 366

_proforma_helper = Proforma_Helper()
_pagos_helper = Pagos_Helper()

TIPOS_VENTA = [value for value, _ in _proforma_helper.tipo_venta]
TIPOS_PAGO = [value for value, _ in _pagos_helper.types]
_TIPO_VENTA_LABELS = dict(_proforma_helper.tipo_venta)
_TIPO_PAGO_LABELS = dict(_pagos_helper.types)


class ReporteParametroInvalido(ValueError):
    """Parametros de filtro invalidos (la API responde 400)."""


def q2(value):
    return Decimal(value).quantize(CENTS, rounding=ROUND_HALF_UP)


def validar_rango(desde, hasta):
    if desde > hasta:
        raise ReporteParametroInvalido('La fecha inicial no puede ser mayor que la final.')
    if (hasta - desde).days + 1 > MAX_DIAS_RANGO:
        raise ReporteParametroInvalido(f'El rango no puede superar {MAX_DIAS_RANGO} días.')


def metros_de_linea(length, quantity):
    return length * quantity if quantity > 0 else length


def _vacio():
    return {
        'ventas': 0, 'bruto': CERO, 'descuento': CERO, 'cobrado': CERO, 'venta_lamina': CERO,
        'instalacion': CERO, 'costo_compra': CERO, 'utilidad_antes': CERO, 'utilidad_despues': CERO,
        'ventas_costo_incompleto': 0,
    }


def _acumular(destino, venta):
    destino['ventas'] += 1
    for campo in ('bruto', 'descuento', 'cobrado', 'venta_lamina', 'instalacion', 'costo_compra',
                  'utilidad_antes', 'utilidad_despues'):
        destino[campo] += venta[campo]
    if venta['costo_incompleto']:
        destino['ventas_costo_incompleto'] += 1


def _cerrar(resumen):
    base = resumen['bruto'] - resumen['descuento']
    resumen['margen'] = q2(resumen['utilidad_despues'] / base * 100) if base > 0 else None
    return resumen


def _condicion_cobrada(prefijo):
    """Q de "linea de una venta cobrada y vigente" a partir de la ruta hasta la proforma."""
    return Q(**{
        f'{prefijo}is_delete': False,
        f'{prefijo}nota_trabajo__nota_venta__status': estados.NV_PAGADA,
        f'{prefijo}nota_trabajo__nota_venta__pago__isnull': False,
    })


class Reportes_Business:

    # ------------------------------------------------------------------ consultas base
    def pagos_cobrados(self, qs=None):
        """Pagos de ventas cobradas y vigentes, sin filtros de alcance. `qs` permite partir
        del queryset de un ModelAdmin (proxy) en vez de `pago.objects`."""
        qs = pago.objects.all() if qs is None else qs
        return qs.filter(
            nota_venta__status=estados.NV_PAGADA,
            nota_venta__nota_trabajo__proforma__is_delete=False,
        )

    def lotes_con_ventas(self, qs):
        """Filas de inventario (de `qs`) que alguna venta cobrada consumio, por movimientos
        o por el FK legado de la linea."""
        con_movimientos = Inventario_Movimiento.objects.filter(
            _condicion_cobrada('proforma_detail__proforma_header__')).values('inventario_id')
        legado = Proforma_Detail.objects.filter(
            _condicion_cobrada('proforma_header__'), inventario_id__isnull=False).values('inventario_id')
        return qs.filter(Q(pk__in=con_movimientos) | Q(pk__in=legado))

    def filtrar_pagos(self, qs, desde=None, hasta=None, sucursal_id=None, sales_type=None, tipo_pago=None):
        """Filtros del reporte sobre un queryset de `pago`. Fechas locales (USE_TZ=False),
        ambos extremos inclusive."""
        if desde is not None:
            qs = qs.filter(created_on__date__gte=desde)
        if hasta is not None:
            qs = qs.filter(created_on__date__lte=hasta)
        if sucursal_id is not None:
            qs = qs.filter(nota_venta__nota_trabajo__proforma__sucursal_id=sucursal_id)
        if sales_type:
            qs = qs.filter(nota_venta__nota_trabajo__proforma__sales_type=sales_type)
        if tipo_pago:
            qs = qs.filter(tipo_pago=tipo_pago)
        return qs

    # ------------------------------------------------------------------ lineas
    def _calcular_lineas(self, detalles_qs):
        """{id de linea: datos calculados} para las lineas de `detalles_qs`, en un numero
        constante de consultas (lineas, movimientos, precios de lote)."""
        lineas = list(detalles_qs.values(
            'id', 'proforma_header_id', 'window_film_id', 'window_film__name', 'width', 'length',
            'quantity', 'window_film_price', 'installation_price', 'inventario_id',
        ))
        if not lineas:
            return {}
        movimientos = defaultdict(lambda: defaultdict(lambda: Decimal('0')))
        con_movimientos = set()
        for detalle_id, inventario_id, tipo, metros in Inventario_Movimiento.objects.filter(
            proforma_detail_id__in=[linea['id'] for linea in lineas]
        ).values_list('proforma_detail_id', 'inventario_id', 'tipo', 'metros'):
            con_movimientos.add(detalle_id)
            signo = 1 if tipo == Inventario_Movimiento.EGRESO else -1
            movimientos[detalle_id][inventario_id] += signo * metros
        ids_lote = {inv for netos in movimientos.values() for inv in netos}
        ids_lote |= {linea['inventario_id'] for linea in lineas if linea['inventario_id'] is not None}
        precios = dict(inventario.objects.filter(id__in=ids_lote).values_list('id', 'precio_compra_mtr_lineal'))

        resultado = {}
        for linea in lineas:
            metros = metros_de_linea(linea['length'], linea['quantity'])
            venta_lamina = q2(metros * linea['window_film_price'])
            instalacion = q2(linea['installation_price'] * linea['quantity'])
            tramos = []  # (inventario_id, metros del tramo)
            if linea['id'] in con_movimientos:
                tramos = [(inv, neto) for inv, neto in movimientos[linea['id']].items() if neto > 0]
            elif linea['inventario_id'] is not None:
                tramos = [(linea['inventario_id'], metros)]
            costo = CERO
            incompleto = not tramos
            for inventario_id, metros_tramo in tramos:
                precio = precios.get(inventario_id, CERO)
                if not precio:
                    incompleto = True
                costo += q2(metros_tramo * precio)
            resultado[linea['id']] = {
                'id': linea['id'],
                'proforma_id': linea['proforma_header_id'],
                'window_film_id': linea['window_film_id'],
                'window_film_name': linea['window_film__name'],
                'width': linea['width'],
                'metros': metros,
                'window_film_price': linea['window_film_price'],
                'venta_lamina': venta_lamina,
                'instalacion': instalacion,
                'costo_compra': costo,
                'costo_incompleto': incompleto,
                'tramos': tramos,
                'precios': {inv: precios.get(inv, CERO) for inv, _ in tramos},
            }
        return resultado

    # ------------------------------------------------------------------ ventas
    def calcular_ventas(self, pagos_qs):
        """Una fila por venta cobrada (pago), mas reciente primero."""
        pagos = list(
            pagos_qs.select_related(
                'nota_venta', 'nota_venta__nota_trabajo', 'nota_venta__nota_trabajo__proforma',
                'nota_venta__nota_trabajo__proforma__sucursal', 'nota_venta__nota_trabajo__proforma__car_model_id',
            ).order_by('-created_on', '-id')
        )
        if not pagos:
            return []
        lineas_qs = Proforma_Detail.objects.filter(
            proforma_header__nota_trabajo__nota_venta__pago__in=pagos_qs.values('pk')
        )
        lineas_por_proforma = defaultdict(list)
        for linea in self._calcular_lineas(lineas_qs).values():
            lineas_por_proforma[linea['proforma_id']].append(linea)

        ventas = []
        for pago_obj in pagos:
            nota_venta = pago_obj.nota_venta
            nota_trabajo = nota_venta.nota_trabajo
            proforma = nota_trabajo.proforma
            lineas = sorted(lineas_por_proforma.get(proforma.id, []), key=lambda l: l['id'])
            venta_lamina = sum((l['venta_lamina'] for l in lineas), CERO)
            instalacion = sum((l['instalacion'] for l in lineas), CERO)
            costo = sum((l['costo_compra'] for l in lineas), CERO)
            descuento = q2(proforma.discount)
            bruto = venta_lamina + instalacion
            utilidad_antes = venta_lamina - costo
            utilidad_despues = utilidad_antes - descuento
            base = bruto - descuento
            ventas.append({
                'pago_id': pago_obj.id,
                'nota_venta_id': nota_venta.id,
                'nota_trabajo_id': nota_trabajo.id,
                'proforma_id': proforma.id,
                'fecha': pago_obj.created_on,
                'cliente': proforma.name,
                'vehiculo': proforma.car_model_id.name if proforma.car_model_id else '',
                'sales_type': proforma.sales_type,
                'sales_type_label': _TIPO_VENTA_LABELS.get(proforma.sales_type, proforma.sales_type),
                'sucursal_id': proforma.sucursal_id,
                'sucursal_name': proforma.sucursal.name if proforma.sucursal_id else '',
                'tipo_pago': pago_obj.tipo_pago,
                'tipo_pago_label': _TIPO_PAGO_LABELS.get(pago_obj.tipo_pago, pago_obj.tipo_pago),
                'registro_contable': pago_obj.registro_contable,
                'cerrado': pago_obj.cerrado,
                'venta_lamina': venta_lamina,
                'instalacion': instalacion,
                'bruto': bruto,
                'descuento': descuento,
                'cobrado': q2(pago_obj.monto),
                'costo_compra': costo,
                'utilidad_antes': utilidad_antes,
                'utilidad_despues': utilidad_despues,
                'margen': q2(utilidad_despues / base * 100) if base > 0 else None,
                'costo_incompleto': (not lineas) or any(l['costo_incompleto'] for l in lineas),
                'lineas': lineas,
            })
        return ventas

    def resumir(self, ventas):
        """Totales del periodo, desgloses por tipo de venta y de pago, y detalle por lamina."""
        totales = _vacio()
        por_tipo_venta = {tipo: _vacio() for tipo in TIPOS_VENTA}
        por_tipo_pago = {tipo: _vacio() for tipo in TIPOS_PAGO}
        por_lamina = {}
        for venta in ventas:
            _acumular(totales, venta)
            _acumular(por_tipo_venta.setdefault(venta['sales_type'], _vacio()), venta)
            _acumular(por_tipo_pago.setdefault(venta['tipo_pago'], _vacio()), venta)
            for linea in venta['lineas']:
                clave = (venta['sucursal_id'], linea['window_film_id'], linea['width'])
                fila = por_lamina.setdefault(clave, {
                    'sucursal_id': venta['sucursal_id'], 'sucursal_name': venta['sucursal_name'],
                    'window_film_id': linea['window_film_id'], 'window_film_name': linea['window_film_name'],
                    'width': linea['width'], 'metros': Decimal('0'), 'venta_lamina': CERO, 'costo_compra': CERO,
                })
                fila['metros'] += linea['metros']
                fila['venta_lamina'] += linea['venta_lamina']
                fila['costo_compra'] += linea['costo_compra']
        detalle_lamina = sorted(por_lamina.values(), key=lambda f: (f['sucursal_name'], f['window_film_name'] or '', f['width']))
        for fila in detalle_lamina:
            fila['utilidad_antes'] = fila['venta_lamina'] - fila['costo_compra']
        return {
            'totales': _cerrar(totales),
            'por_tipo_venta': [
                {'sales_type': tipo, 'label': _TIPO_VENTA_LABELS.get(tipo, tipo), **_cerrar(datos)}
                for tipo, datos in por_tipo_venta.items()
            ],
            'por_tipo_pago': [
                {'tipo_pago': tipo, 'label': _TIPO_PAGO_LABELS.get(tipo, tipo), **_cerrar(datos)}
                for tipo, datos in por_tipo_pago.items()
            ],
            'por_lamina': detalle_lamina,
        }

    # ------------------------------------------------------------------ por lote (Django Admin)
    def calcular_por_lote(self, inventario_ids):
        """{id de inventario: {metros, venta_lamina, costo_compra, utilidad_antes, costo_incompleto}}
        acumulado de todas las ventas cobradas que consumieron cada lote (tramo = linea x lote)."""
        ids = set(inventario_ids)
        if not ids:
            return {}
        detalles = Proforma_Detail.objects.filter(_condicion_cobrada('proforma_header__')).filter(
            Q(movimientos_inventario__inventario_id__in=ids) | Q(inventario_id__in=ids)
        ).distinct()
        resultado = {inv: {'metros': Decimal('0'), 'venta_lamina': CERO, 'costo_compra': CERO,
                           'utilidad_antes': CERO, 'costo_incompleto': False} for inv in ids}
        for linea in self._calcular_lineas(detalles).values():
            for inventario_id, metros in linea['tramos']:
                if inventario_id not in ids:
                    continue
                fila = resultado[inventario_id]
                precio = linea['precios'][inventario_id]
                fila['metros'] += metros
                fila['venta_lamina'] += q2(metros * linea['window_film_price'])
                fila['costo_compra'] += q2(metros * precio)
                if not precio:
                    fila['costo_incompleto'] = True
        for fila in resultado.values():
            fila['utilidad_antes'] = fila['venta_lamina'] - fila['costo_compra']
        return resultado
