from django.db.models import Q
from rest_framework import authentication, generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..business.inventario import Inventario_Business
from ..helper.user import User_Helper
from ..models import Window_Film, Window_Film_Reel, inventario, precio_venta_sucursal
from ..permissions import IsStaffUser
from ..serializer.almacen_serializer import (
    InventarioCreateSerializer,
    InventarioSerializer,
    InventarioUpdateSerializer,
    WindowFilmReelSerializer,
    WindowFilmSerializer,
)
from ..serializer.instalador_precio_serializer import PrecioVentaSucursalSerializer

_STANDARD_PERMISSIONS = [permissions.IsAuthenticated, IsStaffUser, permissions.DjangoModelPermissions]


class WindowFilmListCreateView(generics.ListCreateAPIView):
    """Lista (solo activas por defecto, ?include_inactive=true para verlas
    todas) y crea Laminas. ?search= filtra por nombre."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = _STANDARD_PERMISSIONS
    serializer_class = WindowFilmSerializer
    queryset = Window_Film.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get('include_inactive') != 'true':
            queryset = queryset.filter(is_active=True)
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)
        return queryset


class WindowFilmDetailView(generics.RetrieveUpdateAPIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = _STANDARD_PERMISSIONS
    serializer_class = WindowFilmSerializer
    queryset = Window_Film.objects.all()
    http_method_names = ['get', 'patch', 'head', 'options']


class WindowFilmToggleActiveView(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsStaffUser]

    def patch(self, request, pk):
        if not request.user.has_perm('product.change_window_film'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            window_film = Window_Film.objects.get(pk=pk)
        except Window_Film.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        is_active = request.data.get('is_active')
        if is_active is None:
            return Response({'is_active': ['Este campo es obligatorio.']}, status=status.HTTP_400_BAD_REQUEST)

        window_film.is_active = bool(is_active)
        window_film.save(update_fields=['is_active'])
        return Response(WindowFilmSerializer(window_film).data, status=status.HTTP_200_OK)


class WindowFilmReelListCreateView(generics.ListCreateAPIView):
    """Lista (solo activas por defecto) y crea Bobinas. ?search= filtra por
    nombre de la lamina asociada."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = _STANDARD_PERMISSIONS
    serializer_class = WindowFilmReelSerializer
    queryset = Window_Film_Reel.objects.select_related('window_film')

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get('include_inactive') != 'true':
            queryset = queryset.filter(is_active=True)
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(window_film__name__icontains=search)
        return queryset


class WindowFilmReelDetailView(generics.RetrieveUpdateAPIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = _STANDARD_PERMISSIONS
    serializer_class = WindowFilmReelSerializer
    queryset = Window_Film_Reel.objects.select_related('window_film')
    http_method_names = ['get', 'patch', 'head', 'options']


class WindowFilmReelToggleActiveView(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsStaffUser]

    def patch(self, request, pk):
        if not request.user.has_perm('product.change_window_film_reel'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            reel = Window_Film_Reel.objects.select_related('window_film').get(pk=pk)
        except Window_Film_Reel.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        is_active = request.data.get('is_active')
        if is_active is None:
            return Response({'is_active': ['Este campo es obligatorio.']}, status=status.HTTP_400_BAD_REQUEST)

        reel.is_active = bool(is_active)
        reel.save(update_fields=['is_active'])
        return Response(WindowFilmReelSerializer(reel).data, status=status.HTTP_200_OK)


def _inventario_in_scope(user):
    """Filas de inventario que el usuario puede ver y operar: todas para admin,
    las de todas sus sucursales habilitadas para el resto (ver ADR-almacen-
    permisos-sucursal-filtros-alcance-inventario, decision 1)."""
    queryset = inventario.objects.select_related('bobina', 'bobina__window_film', 'sucursal')
    return Inventario_Business().get_panel_inventario_queryset(user, queryset)


class AlmacenSucursalesView(APIView):
    """Sucursales habilitadas que el usuario puede usar en Almacen: todas para
    admin, las suyas para el resto. Alimenta el selector de sucursal de
    Inventario."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsStaffUser]

    def get(self, request):
        sucursales = User_Helper().get_sucursales_in_scope(request.user)
        return Response([{'id': s.id, 'name': s.name} for s in sucursales])


class InventarioListView(generics.ListCreateAPIView):
    """Consulta (dentro del alcance del usuario -- admin ve todas las
    sucursales, el resto las suyas, ver `_inventario_in_scope`) y alta manual
    (requiere `add_inventario` y una sucursal dentro del alcance, ver
    InventarioCreateSerializer) de Inventario. ?search= filtra por nombre de
    lamina o numero de lote; ?sucursal= y ?window_film= (ids) filtran dentro
    del alcance. Solo activas por defecto, ?include_inactive=true para verlas
    todas -- mismo patron que Lamina/Bobina."""

    authentication_classes = [authentication.TokenAuthentication]
    serializer_class = InventarioSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated(), IsStaffUser(), permissions.DjangoModelPermissions()]
        return [permissions.IsAuthenticated(), IsStaffUser()]

    def get_serializer_class(self):
        return InventarioCreateSerializer if self.request.method == 'POST' else InventarioSerializer

    def get_queryset(self):
        queryset = _inventario_in_scope(self.request.user)
        params = self.request.query_params
        if params.get('include_inactive') != 'true':
            queryset = queryset.filter(is_active=True)
        sucursal = params.get('sucursal')
        if sucursal and sucursal.isdigit():
            queryset = queryset.filter(sucursal_id=int(sucursal))
        window_film = params.get('window_film')
        if window_film and window_film.isdigit():
            queryset = queryset.filter(bobina__window_film_id=int(window_film))
        search = params.get('search')
        if search:
            queryset = queryset.filter(
                Q(bobina__window_film__name__icontains=search) | Q(nro_lote__icontains=search)
            )
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = InventarioCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(InventarioSerializer(instance).data, status=status.HTTP_201_CREATED)


class InventarioToggleActiveView(APIView):
    """"Eliminar"/"activar" una fila de Inventario dentro del alcance del
    usuario (`change_inventario`, fila fuera del alcance -> 404). Desactivar
    solo se permite si `to_install == 0` -- ver ADR-modulo-almacen-modelo-
    datos-imagen-soft-delete, seccion "Actualizacion": toda la logica de
    negocio de venta/instalacion (business/inventario.py) ya filtra
    to_install > 0, asi que una fila con to_install == 0 ya es invisible
    para esa logica de todos modos; esta restriccion evita que "eliminar"
    oculte stock que el sistema todavia pudiera vender. Reactivar no tiene
    esa restriccion. Verifica `change_inventario` (no `delete_inventario`),
    misma convencion que los demas toggle-active del proyecto."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsStaffUser]

    def patch(self, request, pk):
        if not request.user.has_perm('product.change_inventario'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            inv = _inventario_in_scope(request.user).get(pk=pk)
        except inventario.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        is_active = request.data.get('is_active')
        if is_active is None:
            return Response({'is_active': ['Este campo es obligatorio.']}, status=status.HTTP_400_BAD_REQUEST)
        is_active = bool(is_active)

        if not is_active and inv.to_install != 0:
            return Response(
                {'detail': 'No se puede eliminar un inventario con metros disponibles para instalar.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        inv.is_active = is_active
        inv.save(update_fields=['is_active'])
        return Response(InventarioSerializer(inv).data, status=status.HTTP_200_OK)


class InventarioUpdateView(generics.RetrieveUpdateAPIView):
    """"Gestionar" una fila de Inventario existente dentro del alcance del
    usuario (`change_inventario`; fila fuera del alcance -> 404) --
    unicamente los campos de InventarioUpdateSerializer, nunca quantity/
    original_length/date/sucursal/bobina (ver ADR-modulo-almacen-modelo-datos-
    imagen-soft-delete punto 8)."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsStaffUser]
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_queryset(self):
        return _inventario_in_scope(self.request.user)

    def get_serializer_class(self):
        return InventarioSerializer if self.request.method == 'GET' else InventarioUpdateSerializer

    def patch(self, request, *args, **kwargs):
        if not request.user.has_perm('product.change_inventario'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return super().patch(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        response.data = InventarioSerializer(self.get_object()).data
        return response


def _precios_in_scope(user):
    """Precios por sucursal de las sucursales que el usuario puede usar: todas
    para admin, las suyas para el resto (User_Helper.get_sucursales_in_scope,
    ver ADR-agrupacion-menu-instalador-precio-sucursal-api-permisos-borrado,
    decision 5)."""
    sucursales = User_Helper().get_sucursales_in_scope(user)
    return precio_venta_sucursal.objects.select_related('sucursal', 'lamina').filter(
        sucursal__in=sucursales
    ).order_by('sucursal__name', 'lamina__name', 'width')


class PrecioVentaSucursalListCreateView(generics.ListCreateAPIView):
    """Lista y crea Precios por sucursal. ?sucursal= filtra por sucursal y
    ?search= por nombre de lamina."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = _STANDARD_PERMISSIONS
    serializer_class = PrecioVentaSucursalSerializer
    queryset = precio_venta_sucursal.objects.all()

    def get_queryset(self):
        queryset = _precios_in_scope(self.request.user)
        sucursal = self.request.query_params.get('sucursal')
        if sucursal and sucursal.isdigit():
            queryset = queryset.filter(sucursal_id=int(sucursal))
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(lamina__name__icontains=search)
        return queryset


class PrecioVentaSucursalDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Detalle, edicion y borrado fisico de un Precio por sucursal (tabla hoja:
    nada la referencia; al borrarla la cotizacion vuelve al precio del
    inventario, ver business/pricing.py)."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = _STANDARD_PERMISSIONS
    serializer_class = PrecioVentaSucursalSerializer
    queryset = precio_venta_sucursal.objects.all()
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return _precios_in_scope(self.request.user)
