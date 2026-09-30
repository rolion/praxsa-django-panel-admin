from rest_framework import authentication, generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import instalador
from ..permissions import IsStaffUser
from ..serializer.instalador_precio_serializer import InstaladorSerializer

_STANDARD_PERMISSIONS = [permissions.IsAuthenticated, IsStaffUser, permissions.DjangoModelPermissions]


def _instaladores():
    return instalador.objects.prefetch_related('sucursal').order_by('name')


class InstaladorListCreateView(generics.ListCreateAPIView):
    """Lista (solo activos por defecto, ?include_inactive=true para verlos
    todos) y crea Instaladores. ?search= filtra por nombre."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = _STANDARD_PERMISSIONS
    serializer_class = InstaladorSerializer
    queryset = _instaladores()

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get('include_inactive') != 'true':
            queryset = queryset.filter(is_active=True)
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)
        return queryset


class InstaladorDetailView(generics.RetrieveUpdateAPIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = _STANDARD_PERMISSIONS
    serializer_class = InstaladorSerializer
    queryset = _instaladores()
    http_method_names = ['get', 'patch', 'head', 'options']


class InstaladorToggleActiveView(APIView):
    """"Eliminar"/"activar" un Instalador (borrado logico: hay Notas de Trabajo
    que lo referencian con on_delete=DO_NOTHING). Verifica `change_instalador`,
    misma convencion que los demas toggle-active del proyecto."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsStaffUser]

    def patch(self, request, pk):
        if not request.user.has_perm('product.change_instalador'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            instance = _instaladores().get(pk=pk)
        except instalador.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        is_active = request.data.get('is_active')
        if is_active is None:
            return Response({'is_active': ['Este campo es obligatorio.']}, status=status.HTTP_400_BAD_REQUEST)

        instance.is_active = bool(is_active)
        instance.save(update_fields=['is_active'])
        return Response(InstaladorSerializer(instance).data, status=status.HTTP_200_OK)
