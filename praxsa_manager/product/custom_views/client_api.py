"""API del cliente final para panel_admin/ (ADR-pricing-calculator-screen-registro-y-api-cliente).

- `client/register`: alta de cuenta (publica, con throttle).
- `client/me`: perfil del cliente autenticado.
- `client/proformas`: proformas propias, solo lectura.

Los endpoints autenticados filtran siempre por `request.user` y no reciben ids de otro
usuario (ADR-006-idor)."""
from rest_framework import authentication, permissions, status
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from ..models import Client, Proforma_Header
from ..serializer.client_register_serializer import ClientRegisterSerializer


class ClientRegisterThrottle(AnonRateThrottle):
    """Limita el autoregistro por IP. Scope propio para ajustar la tasa por configuracion
    (`DEFAULT_THROTTLE_RATES['client_register']`)."""
    scope = 'client_register'


class ClientRegisterView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ClientRegisterThrottle]

    def post(self, request):
        serializer = ClientRegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        user = serializer.save()
        return Response({'username': user.username}, status=status.HTTP_201_CREATED)


class ClientMeView(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        client = Client.objects.filter(user_id=request.user).first()
        if client is None:
            return Response({'detail': 'El usuario no tiene perfil de cliente.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({
            'name': client.name,
            'lastname': client.last_name,
            'email': request.user.email,
            'phone_number': client.phone_number,
            'car_plate': client.car_plate,
            'ci_nit': client.ci_nit,
        })


class ClientProformasView(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        proformas = (
            Proforma_Header.objects
            .filter(created_by=request.user, is_delete=False)
            .select_related('car_model_id__car_brand_id')
            .order_by('-proforma_created_on', '-id')
        )
        data = [
            {
                'id': proforma.id,
                'date': proforma.proforma_created_on.isoformat(),
                'car_brand_name': proforma.car_model_id.car_brand_id.name if proforma.car_model_id else '',
                'car_model_name': proforma.car_model_id.name if proforma.car_model_id else '',
                'car_plate': proforma.car_plate or '',
                'total_price': str(proforma.total_price),
            }
            for proforma in proformas
        ]
        return Response(data)
