from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
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


class PanelAdminAuthToken(ObtainAuthToken):
    """Login para panel_admin/: no depende de Client (los usuarios de este panel
    no pasan por el registro de cliente de proforma/) y no verifica rol/is_staff
    (decisión de negocio explícita: por ahora cualquier usuario válido entra).

    Los endpoints de gestión de usuarios/grupos/sucursales (custom_views/user_admin.py)
    igual exigen is_staff + permisos Django en cada vista -- este endpoint solo
    decide quién puede autenticarse, no qué puede hacer una vez autenticado."""

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        response = {
            'token': token.key,
            'user_id': user.pk,
            'username': user.username,
            'name': user.first_name,
            'lastname': user.last_name,
        }
        return Response(response)
