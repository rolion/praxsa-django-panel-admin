"""Serializers del dashboard del panel (ver ADR-dashboard-taller-laminas-api-agregados-alcance).

Cada respuesta declara EXPLICITAMENTE sus campos: ninguna incluye costo, utilidad
ni margen (eso es solo del reporte de Utilidad) y las ventas cobradas viajan
unicamente cuando la vista las incluye (`null` = el usuario no tiene permiso)."""
from rest_framework import serializers

from ..helper.dashboard import MESES_DEFECTO, MESES_MAX


def _money(**kwargs):
    return serializers.DecimalField(max_digits=14, decimal_places=2, **kwargs)


def _pct():
    return serializers.DecimalField(max_digits=6, decimal_places=1, allow_null=True)


class DashboardParamsSerializer(serializers.Serializer):
    sucursal = serializers.IntegerField(required=False, min_value=1)
    meses = serializers.IntegerField(required=False, min_value=1, max_value=MESES_MAX, default=MESES_DEFECTO)
    todos = serializers.BooleanField(required=False, default=False)


class _EncabezadoSerializer(serializers.Serializer):
    generado = serializers.DateTimeField()
    sucursal = serializers.IntegerField(allow_null=True)


class VentasSerializer(serializers.Serializer):
    mes = _money()
    mes_anterior = _money()
    variacion = _pct()


class ProformasActivasSerializer(serializers.Serializer):
    monto = _money()
    cantidad = serializers.IntegerField()


class ConversionSerializer(serializers.Serializer):
    convertidas = serializers.IntegerField()
    emitidas = serializers.IntegerField()
    porcentaje = _pct()


class InstalacionesSerializer(serializers.Serializer):
    en_taller = serializers.IntegerField()
    terminadas_hoy = serializers.IntegerField()


class KpisSerializer(_EncabezadoSerializer):
    ventas = VentasSerializer(allow_null=True)
    proformas_activas = ProformasActivasSerializer()
    conversion = ConversionSerializer()
    instalaciones = InstalacionesSerializer()
    sin_sucursal = serializers.BooleanField()


class ProformasVsVentasSerializer(_EncabezadoSerializer):
    meses = serializers.ListField(child=serializers.CharField())
    cotizado = serializers.ListField(child=_money())
    vendido = serializers.ListField(child=_money(), allow_null=True)


class SerieMetrosSerializer(serializers.Serializer):
    nombre = serializers.CharField()
    metros = serializers.ListField(child=_money())
    total = _money()


class ConsumoLaminasSerializer(_EncabezadoSerializer):
    meses = serializers.ListField(child=serializers.CharField())
    series = SerieMetrosSerializer(many=True)


class ItemSolicitadoSerializer(serializers.Serializer):
    nombre = serializers.CharField()
    cantidad = serializers.IntegerField()


class ItemsSolicitadosSerializer(_EncabezadoSerializer):
    total = serializers.IntegerField()
    items = ItemSolicitadoSerializer(many=True)


class StockFilaSerializer(serializers.Serializer):
    sucursal_id = serializers.IntegerField()
    sucursal = serializers.CharField()
    lamina_id = serializers.IntegerField()
    lamina = serializers.CharField()
    ancho = _money()
    metros = _money()
    rollos = serializers.IntegerField()
    estado = serializers.CharField()


class StockContadoresSerializer(serializers.Serializer):
    criticos = serializers.IntegerField()
    bajos = serializers.IntegerField()
    ok = serializers.IntegerField()


class StockUmbralesSerializer(serializers.Serializer):
    critico = _money()
    bajo = _money()


class StockCriticoSerializer(_EncabezadoSerializer):
    contadores = StockContadoresSerializer()
    umbrales = StockUmbralesSerializer()
    filas = StockFilaSerializer(many=True)


class ColaFilaSerializer(serializers.Serializer):
    nota_trabajo_id = serializers.IntegerField()
    proforma_id = serializers.IntegerField()
    cliente = serializers.CharField()
    modelo = serializers.CharField(allow_null=True)
    placa = serializers.CharField(allow_null=True)
    laminas = serializers.ListField(child=serializers.CharField())
    status = serializers.CharField()
    status_label = serializers.CharField()
    instalador = serializers.CharField(allow_null=True)
    entrada_vehiculo = serializers.DateTimeField(allow_null=True)


class ColaTallerSerializer(_EncabezadoSerializer):
    total = serializers.IntegerField()
    filas = ColaFilaSerializer(many=True)
