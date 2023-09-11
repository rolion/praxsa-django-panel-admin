from rest_framework.views import APIView
from rest_framework import authentication, permissions
from rest_framework.response import Response
from rest_framework import status
from ..models import Client, Proforma_Header, Proforma_Detail
from ..serializer.invoice_serializer import SalesHeaderSerializer
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core import serializers
from ..models import Client
from datetime import datetime

class InvoiceView(APIView):
    
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    
    def post(self, request, *args, **kwargs):
        user = request.user
        client = Client.objects.get(user_id = user)
        # import pdb; pdb.set_trace()
        request.data['client_id']= client.id
        print('data ', request.data)
        serializer = SalesHeaderSerializer(data=request.data)
        if serializer.is_valid():
            invoice = serializer.save()
            return Response(data={"id": invoice.id}, status= status.HTTP_201_CREATED)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get(self, request, pk, format=None):
        try:
            client = Client.objects.get(user_id= request.user)
            invoice = Proforma_Header.objects.get(id = pk)
            if invoice.client_id.id == client.id:
                details = Proforma_Detail.objects.filter(sales_header_id = invoice)
                items = list(map(lambda item: {'car_part_id': item.car_part_id.id, 
                                               'car_part_name': item.car_part_id.name, 
                                               'width': item.width, 
                                               'length': item.length, 
                                               'sub_total': item.price, 
                                               'quantity': item.quantity, 
                                               'window_film_id': item.window_film_id.id, 
                                               'window_film_name': item.window_film_id.name,
                                               }, details))
                
                data = {'name': invoice.name,
                        'clien_id': invoice.client_id.id,
                        'email': invoice.email,
                        'ci_nit': invoice.ci_nit,
                        'car_plate': invoice.car_plate,
                        'phone_number': invoice.phone_number,
                        'car_model_id': invoice.car_model_id.id,
                        'car_model_name': invoice.car_model_id.name,
                        "car_brand_name": invoice.car_model_id.car_brand_id.name,
                        'total_price': invoice.total_price,
                        'date': invoice.date.strftime("%d/%m/%Y"),
                        'status': invoice.sales_status,
                        'carPartItems': items}
                return Response(data = data  , status=status.HTTP_200_OK)
            else:
                return Response(data ={'not allowed'}  , status=status.HTTP_401_UNAUTHORIZED)
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
        print(request.user)
        client = Client.objects.get(user_id = request.user)
        print(client)
        list_invoice = list(map( lambda invoice: {
                    'name': invoice.name,
                    'client_id': invoice.client_id.id,
                    'email': invoice.email,
                    'ci_nit': invoice.ci_nit,
                    'car_plate': invoice.car_plate,
                    'phone_number': invoice.phone_number,
                    'car_model_id': invoice.car_model_id.id,
                    'car_model_name': invoice.car_model_id.name,
                    'total_price': invoice.total_price,
                    'date': invoice.date.strftime("%d%m/%Y"),
                    'status': invoice.sales_status,
                    'id': invoice.id
                    
            },Proforma_Header.objects.filter(client_id= client) ))
        print(list_invoice)
        count = Proforma_Header.objects.filter(client_id= client).count()
        data = {
            "recordsTotal": count,
            "recordsFiltered": count,
            "data":list_invoice
        }
        return Response(data = data,status=status.HTTP_200_OK)
        # return Response(data = 'ok',status=status.HTTP_200_OK)
        
        
        
        