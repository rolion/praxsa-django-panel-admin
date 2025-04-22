from rest_framework.views import APIView
from rest_framework import authentication, permissions
from rest_framework.response import Response
from rest_framework import status

from ..utils.exception.proforma import ProformaException
from ..models import Client, Proforma_Header, Proforma_Detail
from ..serializer.invoice_serializer import SalesHeaderSerializer
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core import serializers
from ..models import Client
from datetime import datetime
from django.db import transaction

class InvoiceView(APIView):
    
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic 
    def post(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                user = request.user
                request.data['created_by']= user.id
                serializer = SalesHeaderSerializer(data=request.data)
                if serializer.is_valid():
                    invoice = serializer.save()
                    return Response(data={"id": invoice.id}, status= status.HTTP_201_CREATED)
                return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except ProformaException as e:
            return Response(data=str(e),  status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response(data=serializer.errors, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get(self, request, pk, format=None):
        try:
            invoice = Proforma_Header.objects.select_related('car_model_id', 'sucursal').get(id = pk)
            # if invoice.client_id.id == client.id:
            details = Proforma_Detail.objects.select_related('car_part','window_film').filter(proforma_header = invoice)
           
            items = list(map(lambda item: {'car_part_id': item.car_part.id, 
                                            'car_part_name': item.car_part.name, 
                                            'width': item.width, 
                                            'length': item.length, 
                                            'sub_total': item.sub_total, 
                                            'quantity': item.quantity, 
                                            'window_film_id': item.window_film.id, 
                                            'window_film_name': item.window_film.name,
                                            }, details))
            
            data = {
                    'id': pk,
                    'name': invoice.name,
                    'email': invoice.email,
                    'ci_nit': invoice.ci_nit,
                    'sucursal_name': invoice.sucursal.name,
                    'sucursal': invoice.sucursal.id,
                    'car_plate': invoice.car_plate,
                    'phone_number': invoice.phone_number,
                    'car_model_id': invoice.car_model_id.id,
                    'car_model_name': invoice.car_model_id.name,
                    "car_brand_name": invoice.car_model_id.car_brand_id.name,
                    'total_price': invoice.total_price,
                    'proforma_created_on': invoice.proforma_created_on.strftime("%d/%m/%Y"),
                    'carPartItems': items}
            return Response(data = data  , status=status.HTTP_200_OK)
            # else:
            #     return Response(data ={'not allowed'}  , status=status.HTTP_401_UNAUTHORIZED)
        except ObjectDoesNotExist:
            return Response(data='not found', status=status.HTTP_404_NOT_FOUND)
        except MultipleObjectsReturned:
            return Response(data='not found', status=status.HTTP_409_CONFLICT)
        
class ListUserInvoice(APIView):
    """
    View to list all user's invoice.

    * Requires token authentication.
    """
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        print(request.user.id)
        list_invoice = list(map( lambda invoice: {
                    'name': invoice.name,
                    'email': invoice.email,
                    'ci_nit': invoice.ci_nit,
                    'car_plate': invoice.car_plate,
                    'phone_number': invoice.phone_number,
                    'car_model_id': invoice.car_model_id.id,
                    'car_model_name': invoice.car_model_id.name,
                    'total_price': invoice.total_price,
                    'date': invoice.proforma_created_on.strftime("%d%m/%Y"),
                    'id': invoice.id
                    
            },Proforma_Header.objects.filter(created_by= request.user.id) ))
        count = Proforma_Header.objects.filter(created_by= request.user.id).count()
        data = {
            "recordsTotal": count,
            "recordsFiltered": count,
            "data":list_invoice
        }
        return Response(data = data,status=status.HTTP_200_OK)
        # return Response(data = 'ok',status=status.HTTP_200_OK)
        
        
        
        