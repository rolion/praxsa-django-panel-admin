from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework import status
from ..models import Client

class CustomAuthToken(ObtainAuthToken):

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        client = Client.objects.get(user_id = user)
        response = {
            'token': token.key,
            'user_id': user.pk,
            'email': user.email,
            'name': user.first_name,
            'lastname': user.last_name,
            'phone_number': client.phone_number,
            'ci_nit': client.ci_nit
        }
        if client:
            response['name'] = client.name
            response['lastname'] = client.last_name
            response['phone_number'] = client.phone_number
            response['ci_nit'] = client.ci_nit
        return Response(response)


class StaffAuthToken(ObtainAuthToken):
    """Login para el personal administrativo (panel_admin/). Aislado de
    CustomAuthToken, que asume que todo usuario autenticado tiene un Client
    asociado (Client.objects.get) y rompe (500) para un usuario de staff sin
    ese registro (ver ADR-modulo-usuarios-perfiles-grupos-roles-sucursales-api-autenticacion-admin)."""

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        if not user.is_staff:
            return Response(
                {'detail': 'Este usuario no tiene acceso al panel administrativo.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_staff': user.is_staff,
            'groups': list(user.groups.values_list('name', flat=True)),
        })