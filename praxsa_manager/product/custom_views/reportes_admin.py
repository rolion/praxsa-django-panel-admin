"""API de solo lectura de los reportes Ventas Diarias y Utilidad para panel_admin/
(ver ADR-reportes-utilidad-ventas-diarias-calculo-y-api y -permisos).

Staff + Token + permiso Django `view` del reporte (403 si falta). El alcance por
sucursal se aplica siempre desde el queryset; una sucursal fuera de alcance
responde 404. Todo el calculo vive en `business/reportes.py`."""
from rest_framework import authentication, permissions
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from ..business.pago import Pago_Business
from ..business.reportes import ReporteParametroInvalido, Reportes_Business, validar_rango
from ..helper.user import User_Helper
from ..permissions import IsStaffUser, TienePermisoReporte
from ..serializer.reportes_serializer import (
    LaminaUtilidadRowSerializer,
    ReporteParamsSerializer,
    ResumenUtilidadSerializer,
    ResumenUtilidadTipoVentaSerializer,
    ResumenVentasDiariasSerializer,
    ResumenVentasTipoPagoSerializer,
    ResumenVentasTipoVentaSerializer,
    VentaDiariaRowSerializer,
    VentaUtilidadRowSerializer,
)


class _ReporteView(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsStaffUser, TienePermisoReporte]
    permission_codename = ''

    def _parametros(self, request):
        serializer = ReporteParamsSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data
        try:
            validar_rango(params['desde'], params['hasta'])
        except ReporteParametroInvalido as error:
            raise ValidationError({'detail': str(error)})
        return params

    def _sucursal_ids(self, request, params):
        """Sucursales a consultar (ADR-...-filtro-multisucursal-reportes): las pedidas
        (`sucursal` y/o `sucursales`), todas dentro del alcance de lectura del usuario
        (404 si alguna no lo esta); sin pedir ninguna, "Todas" = las sucursales
        activas de su alcance."""
        user_helper = User_Helper()
        pedidas = list(params.get('sucursales') or [])
        if params.get('sucursal') is not None:
            pedidas.append(params['sucursal'])
        pedidas = list(dict.fromkeys(pedidas))
        if not pedidas:
            return user_helper.get_writable_sucursal_ids(request.user)
        visibles = user_helper.get_readable_sucursales(request.user).filter(id__in=pedidas).count()
        if visibles != len(pedidas):
            raise NotFound('Sucursal no encontrada.')
        return pedidas

    def _ventas(self, request, params):
        """(negocio, ventas calculadas, sin_sucursal) dentro del alcance del usuario."""
        user_helper = User_Helper()
        sucursal_ids = self._sucursal_ids(request, params)
        business = Reportes_Business()
        pagos = Pago_Business().get_panel_pago_queryset(request.user, business.pagos_cobrados())
        pagos = business.filtrar_pagos(
            pagos, desde=params['desde'], hasta=params['hasta'], sucursal_ids=sucursal_ids,
            sales_type=params.get('sales_type'), tipo_pago=params.get('tipo_pago'),
        )
        sin_sucursal = not user_helper.can_view_all_sucursales(request.user) and not user_helper.has_assigned_sucursal(request.user)
        ventas = [] if sin_sucursal else business.calcular_ventas(pagos)
        return business, ventas, sin_sucursal


class ReporteVentasDiariasView(_ReporteView):
    """GET reportes/ventas-diarias?desde=&hasta=[&sucursal=&sales_type=&tipo_pago=]"""

    permission_codename = 'product.view_proxy_pagos'

    def get(self, request):
        params = self._parametros(request)
        business, ventas, sin_sucursal = self._ventas(request, params)
        resumen = business.resumir(ventas)
        return Response({
            'rows': VentaDiariaRowSerializer(ventas, many=True).data,
            'totales': ResumenVentasDiariasSerializer(resumen['totales']).data,
            'por_tipo_venta': ResumenVentasTipoVentaSerializer(resumen['por_tipo_venta'], many=True).data,
            'por_tipo_pago': ResumenVentasTipoPagoSerializer(resumen['por_tipo_pago'], many=True).data,
            'sin_sucursal': sin_sucursal,
        })


class ReporteUtilidadView(_ReporteView):
    """GET reportes/utilidad?desde=&hasta=[&sucursal=&sales_type=] (el tipo de pago no aplica)."""

    permission_codename = 'product.view_utilidades'

    def get(self, request):
        params = self._parametros(request)
        params.pop('tipo_pago', None)
        business, ventas, sin_sucursal = self._ventas(request, params)
        resumen = business.resumir(ventas)
        return Response({
            'ventas': VentaUtilidadRowSerializer(ventas, many=True).data,
            'por_lamina': LaminaUtilidadRowSerializer(resumen['por_lamina'], many=True).data,
            'totales': ResumenUtilidadSerializer(resumen['totales']).data,
            'por_tipo_venta': ResumenUtilidadTipoVentaSerializer(resumen['por_tipo_venta'], many=True).data,
            'sin_sucursal': sin_sucursal,
        })
