from django.contrib.auth.models import Group, Permission, User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import authentication, generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Sucursal
from ..permissions import IsStaffUser
from ..serializer.group_serializer import GroupSerializer, PermissionSerializer
from ..serializer.sucursal_serializer import SucursalSerializer
from ..serializer.user_admin_serializer import UserAdminSerializer, UserCreateSerializer

_USER_QUERYSET = User.objects.select_related('profile').prefetch_related('groups', 'sucursal_set').order_by('username')


class UserListCreateView(generics.ListCreateAPIView):
    """Lista (solo activos por defecto, ?include_inactive=true para verlos
    todos) y crea usuarios administrativos (User+Profile+grupos+sucursales
    atomico, via UserCreateSerializer)."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsStaffUser, permissions.DjangoModelPermissions]
    queryset = _USER_QUERYSET

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get('include_inactive') != 'true':
            queryset = queryset.filter(is_active=True)
        return queryset

    def get_serializer_class(self):
        return UserCreateSerializer if self.request.method == 'POST' else UserAdminSerializer

    def create(self, request, *args, **kwargs):
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserAdminSerializer(user).data, status=status.HTTP_201_CREATED)


class UserDetailView(generics.RetrieveUpdateAPIView):
    """Ver (GET) y editar (PATCH) perfil/grupos/sucursales de un usuario.
    No toca password ni is_active (endpoints separados)."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsStaffUser, permissions.DjangoModelPermissions]
    queryset = _USER_QUERYSET
    serializer_class = UserAdminSerializer
    http_method_names = ['get', 'patch', 'head', 'options']


class UserSetPasswordView(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsStaffUser]

    def post(self, request, pk):
        if not request.user.has_perm('auth.change_user'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        password = request.data.get('password')
        password_confirm = request.data.get('password_confirm')
        if not password or password != password_confirm:
            return Response(
                {'password_confirm': ['Las contraseñas no coinciden.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            validate_password(password, user=user)
        except DjangoValidationError as exc:
            return Response({'password': list(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(password)
        user.save(update_fields=['password'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserToggleActiveView(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsStaffUser]

    def patch(self, request, pk):
        if not request.user.has_perm('auth.change_user'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if user.pk == request.user.pk:
            return Response(
                {'detail': 'No podés activar/desactivar tu propio usuario.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        is_active = request.data.get('is_active')
        if is_active is None:
            return Response({'is_active': ['Este campo es obligatorio.']}, status=status.HTTP_400_BAD_REQUEST)

        user.is_active = bool(is_active)
        user.save(update_fields=['is_active'])
        return Response(UserAdminSerializer(user).data, status=status.HTTP_200_OK)


class GroupListCreateView(generics.ListCreateAPIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsStaffUser, permissions.DjangoModelPermissions]
    queryset = Group.objects.prefetch_related('permissions').order_by('name')
    serializer_class = GroupSerializer


class GroupDetailView(generics.RetrieveUpdateDestroyAPIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsStaffUser, permissions.DjangoModelPermissions]
    queryset = Group.objects.prefetch_related('permissions')
    serializer_class = GroupSerializer


class PermissionListView(generics.ListAPIView):
    """Solo lectura -- catalogo de Permission de Django para poblar el
    selector de 'Roles' (permisos asignables a un Group) en el frontend."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsStaffUser]
    queryset = Permission.objects.select_related('content_type').order_by('content_type__app_label', 'codename')
    serializer_class = PermissionSerializer
    pagination_class = None


class SucursalListCreateView(generics.ListCreateAPIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsStaffUser, permissions.DjangoModelPermissions]
    queryset = Sucursal.objects.all().order_by('name')
    serializer_class = SucursalSerializer


class SucursalDetailView(generics.RetrieveUpdateDestroyAPIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsStaffUser, permissions.DjangoModelPermissions]
    queryset = Sucursal.objects.all()
    serializer_class = SucursalSerializer
