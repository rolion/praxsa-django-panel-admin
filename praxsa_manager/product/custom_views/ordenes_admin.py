"""API del modulo Ordenes (Proformas y Notas de Trabajo) para panel_admin/ --
ver ADR-modulo-ordenes-proforma-nota-trabajo-api-y-calculo y
ADR-modulo-ordenes-proforma-nota-trabajo-alcance-permisos.

Todas las vistas exigen staff + Token; el alcance por sucursal se aplica
siempre desde el queryset (un objeto ajeno responde 404, no 403)."""
import io

from django.db import transaction
from django.db.models import Q
from django.http import FileResponse
from rest_framework import authentication, generics, permissions, status
from rest_framework.exceptions import APIException, NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from ..business.orden_trabajo import Orden_Trabajo_Business
from ..business.pricing import Pricing_Business
from ..business.proforma import Proforma_Business
from ..helper.pdf import PDFService
from ..helper.user import User_Helper
from ..models import Nota_trabajo, Proforma_Detail, Proforma_Header, instalador
from ..permissions import IsStaffUser
from ..serializer.ordenes_serializer import (
    NotaTrabajoDetailSerializer,
    NotaTrabajoListSerializer,
    NotaTrabajoUpdateSerializer,
    ProformaDetailSerializer,
    ProformaListSerializer,
    ProformaWriteSerializer,
    ReelCatalogSerializer,
)
from ..utils.exception.proforma import ProformaException

_STANDARD_PERMISSIONS = [permissions.IsAuthenticated, IsStaffUser, permissions.DjangoModelPermissions]
_STAFF_ONLY = [permissions.IsAuthenticated, IsStaffUser]


class Conflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'La operación entra en conflicto con el estado actual.'
    default_code = 'conflict'


def _proformas_in_scope(user):
    return Proforma_Business().get_panel_proforma_queryset(user, Proforma_Header.objects.all())


def _notas_in_scope(user):
    return Orden_Trabajo_Business().get_panel_nota_queryset(user, Nota_trabajo.objects.all())


def _sucursal_in_scope_or_404(user, raw_sucursal_id):
    try:
        sucursal_id = int(raw_sucursal_id)
    except (TypeError, ValueError):
        raise NotFound('Sucursal no encontrada.')
    if not User_Helper().get_sucursales_in_scope(user).filter(pk=sucursal_id).exists():
        raise NotFound('Sucursal no encontrada.')
    return sucursal_id


class ProformaListCreateView(generics.ListCreateAPIView):
    """Lista (dentro del alcance del usuario) y crea proformas. ?search=
    (id, nombre, placa, modelo), ?sales_type=, ?status=."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = _STANDARD_PERMISSIONS
    queryset = Proforma_Header.objects.all()

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProformaWriteSerializer
        return ProformaListSerializer

    def get_queryset(self):
        queryset = _proformas_in_scope(self.request.user)
        params = self.request.query_params
        search = params.get('search')
        if search:
            condition = (
                Q(name__icontains=search)
                | Q(car_plate__icontains=search)
                | Q(car_model_id__name__icontains=search)
            )
            if search.isdigit():
                condition |= Q(id=int(search))
            queryset = queryset.filter(condition)
        if params.get('sales_type'):
            queryset = queryset.filter(sales_type=params['sales_type'])
        if params.get('status'):
            queryset = queryset.filter(status=params['status'])
        return queryset


class ProformaDetailView(generics.RetrieveUpdateAPIView):
    """Detalle y edicion (PATCH) de una proforma. Una proforma cerrada no se
    edita (409)."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = _STANDARD_PERMISSIONS
    queryset = Proforma_Header.objects.all()
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return ProformaWriteSerializer
        return ProformaDetailSerializer

    def get_queryset(self):
        return _proformas_in_scope(self.request.user).prefetch_related(
            'items__car_part', 'items__window_film'
        )

    def perform_update(self, serializer):
        if serializer.instance.is_close:
            raise Conflict('La proforma está cerrada (ya tiene nota de trabajo) y no se puede editar.')
        serializer.save()


class ProformaGenerateNotaView(APIView):
    """Genera la Nota de Trabajo de una proforma: descuenta inventario y cierra
    la proforma, reutilizando Proforma_Business.create_work_note tal cual."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = _STAFF_ONLY

    def post(self, request, pk):
        if not request.user.has_perm('product.add_nota_trabajo'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        if not _proformas_in_scope(request.user).filter(pk=pk).exists():
            raise NotFound('Proforma no encontrada.')
        try:
            with transaction.atomic():
                proforma = Proforma_Header.objects.select_for_update().get(pk=pk)
                if proforma.is_close:
                    raise Conflict('La proforma ya está cerrada; ya tiene nota de trabajo.')
                nota = Proforma_Business().create_work_note(proforma=proforma, responsable=request.user)
                if nota is None:
                    raise ProformaException('No se pudo generar la nota de trabajo.')
        except APIException:
            raise
        except Exception as e:
            # El negocio ya devuelve mensajes legibles (sin stock, ancho, etc.) o
            # uno generico; nunca detalles internos.
            return Response({'detail': str(e)}, status=status.HTTP_409_CONFLICT)
        proforma = _proformas_in_scope(request.user).prefetch_related(
            'items__car_part', 'items__window_film'
        ).get(pk=pk)
        return Response(ProformaDetailSerializer(proforma).data, status=status.HTTP_200_OK)


class ProformaPdfView(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = _STAFF_ONLY

    def get(self, request, pk):
        try:
            proforma = _proformas_in_scope(request.user).get(pk=pk)
        except Proforma_Header.DoesNotExist:
            raise NotFound('Proforma no encontrada.')
        if not proforma.sucursal_id:
            raise Conflict('La proforma no tiene sucursal asignada; no se puede generar el PDF.')
        details = Proforma_Detail.objects.select_related(
            'car_part', 'window_film', 'proforma_header'
        ).filter(proforma_header=proforma)
        if not details.exists():
            raise Conflict('La proforma no tiene líneas; no se puede generar el PDF.')
        buffer = io.BytesIO()
        PDFService(buffer=buffer).create_proforma(detail=details, header=proforma)
        buffer.seek(0)
        return FileResponse(
            buffer, as_attachment=True, filename=f'proforma-{proforma.id}.pdf',
            content_type='application/pdf',
        )


class NotaTrabajoListView(generics.ListAPIView):
    """Lista de Notas de Trabajo dentro del alcance del usuario. ?search=
    (nº de proforma, nombre, placa, modelo, instalador)."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = _STANDARD_PERMISSIONS
    serializer_class = NotaTrabajoListSerializer
    queryset = Nota_trabajo.objects.all()

    def get_queryset(self):
        queryset = _notas_in_scope(self.request.user)
        search = self.request.query_params.get('search')
        if search:
            condition = (
                Q(name__icontains=search)
                | Q(car_plate__icontains=search)
                | Q(car_model__name__icontains=search)
                | Q(instaladar__name__icontains=search)
            )
            if search.isdigit():
                condition |= Q(proforma_id=int(search))
            queryset = queryset.filter(condition)
        return queryset


class NotaTrabajoDetailView(generics.RetrieveUpdateAPIView):
    """Detalle y edicion operativa de una Nota de Trabajo. Con nota de venta
    ya generada no se edita (409)."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = _STANDARD_PERMISSIONS
    queryset = Nota_trabajo.objects.all()
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return NotaTrabajoUpdateSerializer
        return NotaTrabajoDetailSerializer

    def get_queryset(self):
        return _notas_in_scope(self.request.user)

    def perform_update(self, serializer):
        nota = serializer.instance
        if nota.is_close or hasattr(nota, 'nota_venta'):
            raise Conflict('La nota de trabajo ya tiene nota de venta y no se puede editar.')
        serializer.save()


class OrdenesSucursalesView(APIView):
    """Sucursales que el usuario puede usar en Ordenes."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = _STAFF_ONLY

    def get(self, request):
        sucursales = User_Helper().get_sucursales_in_scope(request.user)
        return Response([{'id': s.id, 'name': s.name, 'address': s.address} for s in sucursales])


class OrdenesBobinasView(APIView):
    """Bobinas (lamina + ancho) con stock en una sucursal, con metros
    disponibles y precio unitario resuelto. ?sucursal= obligatorio."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = _STAFF_ONLY

    def get(self, request):
        sucursal_id = _sucursal_in_scope_or_404(request.user, request.query_params.get('sucursal'))
        catalog = Pricing_Business().get_reel_catalog(sucursal_id)
        return Response(ReelCatalogSerializer(catalog, many=True).data)


class OrdenesInstaladoresView(APIView):
    """Instaladores de una sucursal. ?sucursal= obligatorio."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = _STAFF_ONLY

    def get(self, request):
        sucursal_id = _sucursal_in_scope_or_404(request.user, request.query_params.get('sucursal'))
        instaladores = instalador.objects.filter(sucursal__id=sucursal_id).order_by('name')
        return Response([{'id': i.id, 'name': i.name} for i in instaladores])
