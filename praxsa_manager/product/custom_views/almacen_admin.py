from django.db.models import Q
from rest_framework import authentication, generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..business.inventario import Inventario_Business
from ..models import Window_Film, Window_Film_Reel, inventario
from ..permissions import IsStaffUser
from ..serializer.almacen_serializer import (
    InventarioSerializer,
    InventarioUpdateSerializer,
    WindowFilmReelSerializer,
    WindowFilmSerializer,
)

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


class InventarioListView(generics.ListAPIView):
    """Consulta de Inventario, filtrada por sucursal del usuario (admin ve
    todas -- ver Inventario_Business.get_inventario_queryset_by_role).
    ?search= filtra por nombre de lamina o numero de lote."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsStaffUser]
    serializer_class = InventarioSerializer

    def get_queryset(self):
        queryset = inventario.objects.select_related('bobina', 'bobina__window_film', 'sucursal')
        business = Inventario_Business()
        queryset = business.get_inventario_queryset_by_role(self.request.user, queryset)
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(bobina__window_film__name__icontains=search) | Q(nro_lote__icontains=search)
            )
        return queryset


class InventarioUpdateView(generics.RetrieveUpdateAPIView):
    """"Gestionar" una fila de Inventario existente (solo admin) -- unicamente
    los campos de InventarioUpdateSerializer, nunca quantity/original_length/
    date/sucursal/bobina (ver ADR-modulo-almacen-modelo-datos-imagen-soft-delete
    punto 8)."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsStaffUser]
    queryset = inventario.objects.select_related('bobina', 'bobina__window_film', 'sucursal')
    http_method_names = ['get', 'patch', 'head', 'options']

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
