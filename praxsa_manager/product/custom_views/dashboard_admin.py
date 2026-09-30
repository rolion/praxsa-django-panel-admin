"""API de solo lectura del dashboard del panel (panel_admin/) -- ver
ADR-dashboard-taller-laminas-api-agregados-alcance y -definiciones-metricas.

Staff + Token; el alcance por sucursal sale de los `get_panel_*` existentes y una
sucursal fuera de alcance responde 404. Solo lo que muestra ventas cobradas
exige `product.view_proxy_pagos` (el permiso de Ventas Diarias): sin el, el
bloque va `null`. Ninguna respuesta incluye costo, utilidad ni margen."""
from datetime import date

from django.utils import timezone
from rest_framework import authentication, permissions
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from ..business.dashboard import Dashboard_Business
from ..helper.dashboard import PERMISO_VENTAS
from ..helper.user import User_Helper
from ..permissions import IsStaffUser
from ..serializer.dashboard_serializer import (
    ColaTallerSerializer,
    ConsumoLaminasSerializer,
    DashboardParamsSerializer,
    ItemsSolicitadosSerializer,
    KpisSerializer,
    ProformasVsVentasSerializer,
    StockCriticoSerializer,
)
from ..serializer.ordenes_serializer import ProformaListSerializer


class _DashboardView(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsStaffUser]
    http_method_names = ['get', 'head', 'options']

    def _parametros(self, request):
        serializer = DashboardParamsSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data
        sucursal_id = params.get('sucursal')
        if sucursal_id is not None and not User_Helper().get_sucursales_in_scope(request.user).filter(id=sucursal_id).exists():
            raise NotFound('Sucursal no encontrada.')
        return params

    def _encabezado(self, params):
        return {'generado': timezone.now(), 'sucursal': params.get('sucursal')}

    def _puede_ver_ventas(self, request):
        return request.user.has_perm(PERMISO_VENTAS)

    def _ok(self, serializer_class, datos):
        return Response(serializer_class(datos).data)


class DashboardKpisView(_DashboardView):
    """GET dashboard/kpis[?sucursal=]"""

    def get(self, request):
        params = self._parametros(request)
        negocio = Dashboard_Business()
        sin_sucursal = negocio.sin_sucursal(request.user)
        datos = negocio.kpis(
            request.user, date.today(), params.get('sucursal'), con_ventas=self._puede_ver_ventas(request),
        )
        datos.update(self._encabezado(params), sin_sucursal=sin_sucursal)
        return self._ok(KpisSerializer, datos)


class DashboardProformasVsVentasView(_DashboardView):
    """GET dashboard/proformas-vs-ventas[?meses=&sucursal=]"""

    def get(self, request):
        params = self._parametros(request)
        datos = Dashboard_Business().proformas_vs_ventas(
            request.user, date.today(), params['meses'], params.get('sucursal'),
            con_ventas=self._puede_ver_ventas(request),
        )
        datos.update(self._encabezado(params))
        return self._ok(ProformasVsVentasSerializer, datos)


class DashboardConsumoLaminasView(_DashboardView):
    """GET dashboard/consumo-laminas[?meses=&sucursal=]"""

    def get(self, request):
        params = self._parametros(request)
        datos = Dashboard_Business().consumo_laminas(
            request.user, date.today(), params['meses'], params.get('sucursal')
        )
        datos.update(self._encabezado(params))
        return self._ok(ConsumoLaminasSerializer, datos)


class DashboardItemsSolicitadosView(_DashboardView):
    """GET dashboard/items-solicitados[?meses=&sucursal=]"""

    def get(self, request):
        params = self._parametros(request)
        datos = Dashboard_Business().items_solicitados(
            request.user, date.today(), params['meses'], params.get('sucursal')
        )
        datos.update(self._encabezado(params))
        return self._ok(ItemsSolicitadosSerializer, datos)


class DashboardStockCriticoView(_DashboardView):
    """GET dashboard/stock-critico[?todos=true&sucursal=]"""

    def get(self, request):
        params = self._parametros(request)
        datos = Dashboard_Business().stock_critico(request.user, params.get('sucursal'), params['todos'])
        datos.update(self._encabezado(params))
        return self._ok(StockCriticoSerializer, datos)


class DashboardColaTallerView(_DashboardView):
    """GET dashboard/cola-taller[?sucursal=]"""

    def get(self, request):
        params = self._parametros(request)
        datos = Dashboard_Business().cola_taller(request.user, date.today(), params.get('sucursal'))
        datos.update(self._encabezado(params))
        return self._ok(ColaTallerSerializer, datos)


class DashboardProformasRecientesView(_DashboardView):
    """GET dashboard/proformas-recientes[?sucursal=] -- mismo serializer del listado de proformas."""

    def get(self, request):
        params = self._parametros(request)
        proformas = Dashboard_Business().proformas_recientes(request.user, params.get('sucursal'))
        return Response({
            **{k: (v.isoformat() if hasattr(v, 'isoformat') else v) for k, v in self._encabezado(params).items()},
            'proformas': ProformaListSerializer(proformas, many=True).data,
        })
