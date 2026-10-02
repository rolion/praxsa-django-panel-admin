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
from rest_framework.exceptions import APIException, NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from ..business.orden_estado import Orden_Estado_Business
from ..business.orden_trabajo import Orden_Trabajo_Business
from ..business.pago import Pago_Business
from ..business.pricing import Pricing_Business
from ..business.proforma import Proforma_Business
from ..helper.pdf import PDFService
from ..helper.proforma import Proforma_Helper
from ..helper.user import User_Helper
from ..helper import estados
from ..models import Nota_trabajo, Nota_Venta, Proforma_Detail, Proforma_Header, instalador, pago
from ..permissions import IsStaffUser
from ..serializer.ordenes_serializer import (
    NotaTrabajoDetailSerializer,
    NotaTrabajoListSerializer,
    NotaTrabajoUpdateSerializer,
    NotaVentaDetailSerializer,
    NotaVentaListSerializer,
    PagoInputSerializer,
    ProformaDetailSerializer,
    ProformaListSerializer,
    ProformaWriteSerializer,
    ReelCatalogSerializer,
)
from ..utils.exception.proforma import OrdenEstadoException, ProformaException

_STANDARD_PERMISSIONS = [permissions.IsAuthenticated, IsStaffUser, permissions.DjangoModelPermissions]
_STAFF_ONLY = [permissions.IsAuthenticated, IsStaffUser]
estados_globales = Proforma_Helper()


class Conflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'La operación entra en conflicto con el estado actual.'
    default_code = 'conflict'


def _proformas_in_scope(user):
    return Proforma_Business().get_panel_proforma_queryset(user, Proforma_Header.objects.all())


def _notas_in_scope(user):
    return Orden_Trabajo_Business().get_panel_nota_queryset(user, Nota_trabajo.objects.all())


def _notas_venta_in_scope(user):
    return Pago_Business().get_panel_nota_venta_queryset(user, Nota_Venta.objects.all())


def _get_in_scope_or_404(queryset, pk, what):
    obj = queryset.filter(pk=pk).first()
    if obj is None:
        raise NotFound(f'{what} no encontrada.')
    return obj


def _forbid_without_perm(user, codename):
    if not user.has_perm(f'product.{codename}'):
        raise PermissionDenied()


def _transition(fn, *args, **kwargs):
    """Ejecuta una transicion del servicio; una transicion invalida o una
    precondicion de negocio no cumplida responde 409 con el mensaje legible."""
    try:
        return fn(*args, **kwargs)
    except OrdenEstadoException as e:
        raise Conflict(str(e))


def _sucursal_in_scope_or_404(user, raw_sucursal_id):
    try:
        sucursal_id = int(raw_sucursal_id)
    except (TypeError, ValueError):
        raise NotFound('Sucursal no encontrada.')
    if not User_Helper().get_readable_sucursales(user).filter(pk=sucursal_id).exists():
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

    def update(self, request, *args, **kwargs):
        User_Helper().require_sucursal_writable(request.user, self.get_object().sucursal_id)
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        if serializer.instance.status != estados_globales.estado_proforma:
            raise Conflict('La proforma está aprobada o anulada (ya no es vigente) y no se puede editar.')
        serializer.save()


class ProformaGenerateNotaView(APIView):
    """Genera la Nota de Trabajo de una proforma: descuenta inventario y cierra
    la proforma, reutilizando Proforma_Business.create_work_note tal cual."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = _STAFF_ONLY

    def post(self, request, pk):
        if not request.user.has_perm('product.add_nota_trabajo'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        proforma_en_alcance = _get_in_scope_or_404(_proformas_in_scope(request.user), pk, 'Proforma')
        User_Helper().require_sucursal_writable(request.user, proforma_en_alcance.sucursal_id)
        try:
            with transaction.atomic():
                proforma = Proforma_Header.objects.select_for_update().get(pk=pk)
                if proforma.status != estados_globales.estado_proforma:
                    raise Conflict('La proforma ya fue aprobada o está anulada; no se puede generar la nota de trabajo.')
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

    def update(self, request, *args, **kwargs):
        User_Helper().require_sucursal_writable(request.user, self.get_object().proforma.sucursal_id)
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        nota = serializer.instance
        if nota.status != estados.NT_EN_PROCESO:
            raise Conflict('La nota de trabajo no está En proceso y no se puede editar.')
        serializer.save()


class ProformaAnularView(APIView):
    """Anula una proforma vigente (sin nota de trabajo activa)."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = _STAFF_ONLY

    def post(self, request, pk):
        _forbid_without_perm(request.user, 'delete_proforma_header')
        proforma_en_alcance = _get_in_scope_or_404(_proformas_in_scope(request.user), pk, 'Proforma')
        User_Helper().require_sucursal_writable(request.user, proforma_en_alcance.sucursal_id)
        _transition(Orden_Estado_Business().anular_proforma, Proforma_Header.objects.get(pk=pk))
        proforma = _proformas_in_scope(request.user).prefetch_related('items__car_part', 'items__window_film').get(pk=pk)
        return Response(ProformaDetailSerializer(proforma).data, status=status.HTTP_200_OK)


class _NotaTrabajoActionView(APIView):
    """Base de las acciones sobre una nota de trabajo (terminar, corregir,
    anular). `permission_codename` y `service_method` los define cada vista."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = _STAFF_ONLY
    permission_codename = None
    service_method = None

    def post(self, request, pk):
        _forbid_without_perm(request.user, self.permission_codename)
        nota = _get_in_scope_or_404(_notas_in_scope(request.user), pk, 'Nota de trabajo')
        User_Helper().require_sucursal_writable(request.user, nota.proforma.sucursal_id)
        _transition(getattr(Orden_Estado_Business(), self.service_method), nota)
        nota = _notas_in_scope(request.user).get(pk=pk)
        return Response(NotaTrabajoDetailSerializer(nota).data, status=status.HTTP_200_OK)


class NotaTrabajoTerminarView(_NotaTrabajoActionView):
    permission_codename = 'change_nota_trabajo'
    service_method = 'terminar_trabajo'


class NotaTrabajoCorregirView(_NotaTrabajoActionView):
    permission_codename = 'change_nota_trabajo'
    service_method = 'corregir_trabajo'


class NotaTrabajoAnularView(_NotaTrabajoActionView):
    permission_codename = 'delete_nota_trabajo'
    service_method = 'anular_nota_trabajo'


class NotaVentaListView(generics.ListAPIView):
    """Lista de Notas de Venta dentro del alcance del usuario. ?status=,
    ?search= (nº de proforma, cliente, CI/NIT, placa)."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = _STANDARD_PERMISSIONS
    serializer_class = NotaVentaListSerializer
    queryset = Nota_Venta.objects.all()

    def get_queryset(self):
        queryset = _notas_venta_in_scope(self.request.user)
        params = self.request.query_params
        if params.get('status'):
            queryset = queryset.filter(status=params['status'])
        search = params.get('search')
        if search:
            condition = (
                Q(name__icontains=search)
                | Q(ci_nit__icontains=search)
                | Q(nota_trabajo__car_plate__icontains=search)
            )
            if search.isdigit():
                condition |= Q(nota_trabajo__proforma_id=int(search))
            queryset = queryset.filter(condition)
        return queryset


class NotaVentaDetailView(generics.RetrieveAPIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = _STANDARD_PERMISSIONS
    serializer_class = NotaVentaDetailSerializer
    queryset = Nota_Venta.objects.all()

    def get_queryset(self):
        return _notas_venta_in_scope(self.request.user)


class _NotaVentaActionView(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = _STAFF_ONLY
    permission_codename = None

    def run(self, request, nota_venta):
        raise NotImplementedError

    def post(self, request, pk):
        _forbid_without_perm(request.user, self.permission_codename)
        nota_venta = _get_in_scope_or_404(_notas_venta_in_scope(request.user), pk, 'Nota de venta')
        User_Helper().require_sucursal_writable(request.user, nota_venta.nota_trabajo.proforma.sucursal_id)
        _transition(self.run, request, nota_venta)
        nota_venta = _notas_venta_in_scope(request.user).get(pk=pk)
        return Response(NotaVentaDetailSerializer(nota_venta).data, status=status.HTTP_200_OK)


class NotaVentaPagoView(_NotaVentaActionView):
    """Registra el pago de la nota de venta (trabajo terminado). El monto lo
    fija el servidor; cualquier `monto` enviado se ignora."""

    permission_codename = 'add_pago'

    def run(self, request, nota_venta):
        data = PagoInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        Orden_Estado_Business().registrar_pago(
            nota_venta, request.user, data.validated_data['tipo_pago'], data.validated_data.get('registro_contable'),
        )


class NotaVentaAnularPagoView(_NotaVentaActionView):
    permission_codename = 'delete_pago'

    def run(self, request, nota_venta):
        pago_obj = pago.objects.filter(nota_venta=nota_venta).first()
        if pago_obj is None:
            raise OrdenEstadoException('La nota de venta no tiene un pago registrado.')
        Orden_Estado_Business().anular_pago(pago_obj)


class NotaVentaAnularView(_NotaVentaActionView):
    permission_codename = 'delete_nota_venta'

    def run(self, request, nota_venta):
        Orden_Estado_Business().anular_nota_venta(nota_venta)


class OrdenesSucursalesView(APIView):
    """Sucursales del alcance de lectura del usuario en Ordenes (asignadas, activas
    o no; todas para el superusuario). `activa` permite al panel ofrecer solo las
    activas en los formularios de alta."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = _STAFF_ONLY

    def get(self, request):
        sucursales = User_Helper().get_readable_sucursales(request.user)
        return Response([
            {'id': s.id, 'name': s.name, 'address': s.address, 'activa': s.enable_to_install_windows_film}
            for s in sucursales
        ])


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
        instaladores = instalador.objects.filter(sucursal__id=sucursal_id, is_active=True).order_by('name')
        return Response([{'id': i.id, 'name': i.name} for i in instaladores])
