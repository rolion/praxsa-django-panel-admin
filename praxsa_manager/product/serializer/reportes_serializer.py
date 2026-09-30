"""Serializers de los reportes de Ventas Diarias y Utilidad del panel (ver
ADR-reportes-utilidad-ventas-diarias-calculo-y-api / -permisos).

Cada reporte declara EXPLICITAMENTE los campos que devuelve: el de Ventas Diarias
no contiene ningun campo de costo, utilidad ni margen (esta accesible para Caja),
y por eso no comparte serializers de fila con el de Utilidad."""
from rest_framework import serializers

from ..business.reportes import TIPOS_PAGO, TIPOS_VENTA


def _money():
    return serializers.DecimalField(max_digits=14, decimal_places=2)


class ReporteParamsSerializer(serializers.Serializer):
    desde = serializers.DateField()
    hasta = serializers.DateField()
    sucursal = serializers.IntegerField(required=False, min_value=1)
    sales_type = serializers.ChoiceField(choices=TIPOS_VENTA, required=False)
    tipo_pago = serializers.ChoiceField(choices=TIPOS_PAGO, required=False)


class _VentaBaseSerializer(serializers.Serializer):
    nota_venta_id = serializers.IntegerField()
    nota_trabajo_id = serializers.IntegerField()
    proforma_id = serializers.IntegerField()
    fecha = serializers.DateTimeField()
    cliente = serializers.CharField()
    sales_type = serializers.CharField()
    sales_type_label = serializers.CharField()
    sucursal_id = serializers.IntegerField(allow_null=True)
    sucursal_name = serializers.CharField()
    venta_lamina = _money()
    instalacion = _money()
    bruto = _money()
    descuento = _money()
    cobrado = _money()


class VentaDiariaRowSerializer(_VentaBaseSerializer):
    """Fila de Ventas Diarias: datos del cobro, sin costos ni utilidad."""
    pago_id = serializers.IntegerField()
    vehiculo = serializers.CharField()
    tipo_pago = serializers.CharField()
    tipo_pago_label = serializers.CharField()
    registro_contable = serializers.CharField(allow_null=True)
    cerrado = serializers.BooleanField()


class VentaUtilidadRowSerializer(_VentaBaseSerializer):
    """Fila de Utilidad: una por nota de venta cobrada."""
    costo_compra = _money()
    utilidad_antes = _money()
    utilidad_despues = _money()
    margen = serializers.DecimalField(max_digits=14, decimal_places=2, allow_null=True)
    costo_incompleto = serializers.BooleanField()


class _ResumenVentasSerializer(serializers.Serializer):
    ventas = serializers.IntegerField()
    venta_lamina = _money()
    instalacion = _money()
    bruto = _money()
    descuento = _money()
    cobrado = _money()


class ResumenVentasDiariasSerializer(_ResumenVentasSerializer):
    pass


class ResumenVentasTipoVentaSerializer(_ResumenVentasSerializer):
    sales_type = serializers.CharField()
    label = serializers.CharField()


class ResumenVentasTipoPagoSerializer(_ResumenVentasSerializer):
    tipo_pago = serializers.CharField()
    label = serializers.CharField()


class ResumenUtilidadSerializer(_ResumenVentasSerializer):
    costo_compra = _money()
    utilidad_antes = _money()
    utilidad_despues = _money()
    margen = serializers.DecimalField(max_digits=14, decimal_places=2, allow_null=True)
    ventas_costo_incompleto = serializers.IntegerField()


class ResumenUtilidadTipoVentaSerializer(ResumenUtilidadSerializer):
    sales_type = serializers.CharField()
    label = serializers.CharField()


class LaminaUtilidadRowSerializer(serializers.Serializer):
    sucursal_id = serializers.IntegerField(allow_null=True)
    sucursal_name = serializers.CharField()
    window_film_id = serializers.IntegerField(allow_null=True)
    window_film_name = serializers.CharField(allow_null=True)
    width = serializers.DecimalField(max_digits=14, decimal_places=2)
    metros = serializers.DecimalField(max_digits=14, decimal_places=2)
    venta_lamina = _money()
    costo_compra = _money()
    utilidad_antes = _money()
