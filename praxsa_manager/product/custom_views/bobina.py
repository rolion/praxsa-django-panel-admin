from rest_framework.views import APIView
from rest_framework import authentication, permissions
from rest_framework.response import Response
from rest_framework import status
from ..models import Window_Film_Reel
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

class BobinaView(APIView):
    
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk, format=None):
        try:
            bobina = Window_Film_Reel.objects.get(id = pk)
            return Response(data = {'bobina': bobina}  , status=status.HTTP_200_OK)

        except ObjectDoesNotExist:
            return Response(data='not found', status=status.HTTP_404_NOT_FOUND)
        except MultipleObjectsReturned:
            return Response(data='not found', status=status.HTTP_409_CONFLICT)