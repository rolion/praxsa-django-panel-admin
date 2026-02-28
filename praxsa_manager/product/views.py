from django.shortcuts import render
from django.http.response import JsonResponse, HttpResponseBadRequest
from django.template import loader

from .helper.proforma import Proforma_Helper
from .models import Car_Model_Part, Window_Film_Reel, Car_Brand, Car_Model, Car_Part, Window_Film, Sucursal, Proforma_Header
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import permissions
from .serializer.client_serializer import ClientSerializer
from django.db import transaction
from rest_framework import status
from .models import Window_Film_Reel, inventario
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from .business.inventario import Inventario_Business

from django.db.models import OuterRef, Subquery
from django.db.models.functions import Coalesce
from django.db.models import F
from .models import precio_venta_sucursal


from django.http import HttpResponse
import traceback


def index(request):
    latest_brand_list = Car_Brand.objects.order_by("id")
    # template = loader.get_template("product/index.html")
    context = {
        "latest_brand_list": latest_brand_list,
    }
    # return HttpResponse(template.render(context, request))
    return render(request, "product/index.html", context)

def get_bobina(request, pk):
    try:
            bobina = Window_Film_Reel.objects.select_related('window_film').get(id = pk)
            # return Response(data = {'bobina': bobina}  , status=status.HTTP_200_OK)
            return JsonResponse(data={'bobina': {
                'window_film': bobina.window_film.id,
                'width': bobina.width,
                'length': bobina.length,
                'price': bobina.price
            }
                              }, safe=False)

    except ObjectDoesNotExist:
            return HttpResponseBadRequest(data='not found', status=status.HTTP_404_NOT_FOUND)
    except MultipleObjectsReturned:
            return HttpResponseBadRequest(data='not found', status=status.HTTP_409_CONFLICT)

def get_car_part_info(request, car_model_id, sucursal_id):
    '''devuelve la informacion de item del auto seleccionado'''
    
    try:
        inv_business = Inventario_Business()

        # -------------------------
        # INVENTARIO CON PRECIO SUCURSAL
        # -------------------------

        inventario = (
            inv_business.get_inventory_by_sucursal(sucursal=sucursal_id)
            .select_related("bobina__window_film")
            .annotate(
                precio_sucursal=Subquery(
                    precio_venta_sucursal.objects.filter(
                        sucursal_id=sucursal_id,
                        lamina_id=OuterRef("bobina__window_film_id"),
                        width=OuterRef("bobina__width"),
                    ).values("precio_venta")[:1]
                ),
                precio_final=Coalesce(
                    F("precio_sucursal"),
                    F("precio_venta_mtr_lineal"),
                ),
            )
        )

        # -------------------------
        # PARTES DEL AUTO
        # -------------------------

        items = []

        if car_model_id > 0:
            car_parts = (
                Car_Model_Part.objects.select_related("car_part_id")
                .filter(car_model_id=car_model_id)
            )

            for part in car_parts:
                items.append({
                    "part_id": part.car_part_id.id,
                    "name": part.car_part_id.name,
                    "quantity": part.quantity,
                    "width": part.width,
                    "length": part.length,
                    "installation_price": part.installation_price,
                })

        # -------------------------
        # WIDTHS DISPONIBLES
        # -------------------------

        widths = inv_business.get_inventory_window_film_reel_widths(request.user)
        inv_width = list(widths.values_list("width", flat=True))

        # -------------------------
        # INVENTARIO SERIALIZADO
        # -------------------------

        window_film = []

        for inv in inventario:
            window_film.append({
                "name": inv.bobina.window_film.name,
                "reel_id": inv.bobina.id,
                "price": float(inv.precio_final or 0),
                "film_id": inv.bobina.window_film.id,
                "width": inv.bobina.width,
                "disponibilidad": inv.to_install,
            })

        return JsonResponse(
            data={
                "items": items,
                "window_film": window_film,
                "inv_widths": inv_width,
            },
            safe=False,
        )

    except Exception as e:
        print("algo salio mal -->", str(e))
        return JsonResponse(
            data={"error": True, "message": "algo salio mal"},
            status=500
        )
    
def get_proforma_car_part_info(request, proforma_id):
    '''devuelve la informacion de item del auto seleccionado'''
    try:
        proforma = Proforma_Header.objects.select_related('sucursal', 'car_model_id').get(pk= proforma_id)
        helper = Proforma_Helper()
        sales_type = proforma.sales_type
        if sales_type == helper.tipo_venta_instalacion:
            inv_Business = Inventario_Business()
            inventario = inv_Business.get_inventory_by_sucursal(sucursal=proforma.sucursal.id)
            items = []
            if(proforma.car_model_id.id >0):
                car_part = Car_Model_Part.objects.select_related("car_part_id").filter(car_model_id = proforma.car_model_id.id)
                items = list(map(lambda part: {'part_id': part.car_part_id.id, 
                                            'name': part.car_part_id.name, 
                                            'quantity': part.quantity, 
                                            'width': part.width, 
                                            'length': part.length, 
                                            'installation_price': part.installation_price
                                            }, car_part))
            widths = inv_Business.get_inventory_window_film_reel_widths(request.user)
            inv_width = list(map(lambda w: w, widths.values_list('width', flat=True)))
            
            window_film = list(map(lambda inv: {'name': inv.bobina.window_film.name, 
                                                'reel_id':inv.bobina.id, 
                                                'price': inv.precio_venta_mtr_lineal, 
                                                'film_id': inv.bobina.window_film.id, 
                                                'width': inv.bobina.width
                                                }, inventario ))
            return JsonResponse(data={'items': items, 
                                    'window_film': window_film,
                                    'inv_widths': inv_width,
                                    'sales_type': proforma.sales_type
                                    }, safe=False)
        else:
            return JsonResponse(data={'items': [], 
                                    'window_film': [],
                                    'inv_widths': [],
                                    'sales_type': proforma.sales_type
                                    }, safe=False)
    except Exception as e:
        print('algo salio mal -->', str(e))
        return JsonResponse(data={'error':True, 'message': 'algo salio mal'}, status=500)


def get_layer_info(request, layer_id):
    try:
        film = Window_Film.objects.get(pk = layer_id)
        return JsonResponse(data={'layer': {'name': film.name, 'content': film.content} }, safe=False)
    except Exception as e:
        print('algo salio mal -->', str(e))
        return JsonResponse(data={'error':True, 'message': 'algo salio mal'}, status=500)

def get_inventory(request, sucursal_id, lamina_id, width):
    """"
     return sucursal inventory
    """
    try:
        inv_buss = Inventario_Business()
        query = inv_buss.get_total_meters_window_film_in_inventory(sucursal_id=sucursal_id, lamina_id=lamina_id, width=float(width))
        inv = []
        for i in query:

            precio = (
                i['precio_sucursal']
                if i['precio_sucursal'] is not None
                else i['precio_venta_mtr_lineal']
            )

            inv.append({
                'bobina_film_name': i['bobina__window_film__name'],
                'bobina_film_id': i['bobina__window_film__id'],
                'bobina_width': i['bobina__width'],
                'bobina_metros_disponibles': float(i['total_metros']),
                'bobina_price': float(precio),
                'bobina_id': i['bobina__window_film__id'],
            })
        print('inventario',inv)
        return JsonResponse(data={'inventario': inv}, safe=False)
    except Exception as e:
        print('algo salio mal -->', str(e))
        return JsonResponse(data={'error':True, 'message': 'algo salio mal'}, status=500)
    

def get_calculator_info(request):
    """
    return calculator information, brand, models, car parts and car part price
    """
    try:
        car_brands = Car_Brand.objects.all()
        brands = list(map(lambda brand: {'id': brand.id, 'name': brand.name}, car_brands))
        car_models = Car_Model.objects.select_related('car_brand_id').all().order_by('name')
        models = list(map(lambda model: {'id': model.id, 'name':model.name, "brand_id": model.car_brand_id.id}, car_models))
        car_parts = Car_Part.objects.all()
        parts = list(map(lambda part: {'id': part.id, 'name': part.name}, car_parts))
        sucursales_query = Sucursal.objects.all().filter(enable_to_install_windows_film = True)
        sucursales = list(map(lambda sucursal: {
            'id': sucursal.id,
            'name': sucursal.name,
            'addres': sucursal.address

        }, sucursales_query))
        window_films = Window_Film.objects.all()
        films = list(map(lambda film: {'id': film.id, 'name': film.name}, window_films))
        return JsonResponse(data={'brands': brands, 
                                'models': models, 
                                'parts': parts,
                                'films': films, 
                                #   'car_part_film_price': window_film,
                                'sucursales': sucursales}, safe=False)
    except Exception as e:
        print('algo salio mal -->', str(e))
        return JsonResponse(data={'error':True, 'message': 'algo salio mal'}, status=500)

def get_item_film_inventory(request, sucursal_id, car_model_id, item_id):
    """Retur all film available for the item in the selected sucursal"""
    try:
        car_parts = Car_Model_Part.objects.filter(car_model_id = car_model_id).filter(car_part_id=item_id)
        if len(car_parts) == 0:
            return JsonResponse(data={'error':True, 'message': 'item not found'}, status=404)
        car_part = car_parts[0]
        
        query = inventario.objects.select_related("bobina","bobina__window_film", "sucursal")
        query = query.filter(sucursal__id = sucursal_id, 
                             sucursal__enable_to_install_windows_film = True, 
                             to_install__gte=car_part.length, 
                             bobina__width__gte = car_part.width)
        query = query.order_by('bobina__window_film__id',
                               'bobina__width',
                               'bobina__window_film__id',
                               'bobina__window_film__name',
                               'precio_venta_mtr_lineal',
                               'date')
        query = query.distinct('bobina__window_film__id')
        query = query.values('bobina__window_film__id','bobina__window_film__name', "precio_venta_mtr_lineal", "bobina__id", 'bobina__width')
        result =list(map(lambda result: {'price': result["precio_venta_mtr_lineal"], 
                                         'bobina_id': result["bobina__id"], 
                                         'width': result["bobina__width"], 
                                         'film_id': result["bobina__window_film__id"], 
                                         'film_name':result["bobina__window_film__name"]}, query))
        return JsonResponse(data={'films': result}, safe=False)
    except Exception as e:
        return JsonResponse(data={'error':True, 'message': 'algo salio mal'}, status=500)
    return True

def get_model_parts(request, model_id):
    """Returns model parts"""
    try:
        car_model_parts = Car_Model_Part.objects.all().filter(car_model_id= model_id)
        model_parts = list(map(lambda model_part: {'id': model_part.id, 
                                                'width': model_part.width, 
                                                'length': model_part.length,
                                                'quantity': model_part.quantity, 
                                                'model_id': model_part.car_model_id.id, 
                                                'part_id': model_part.car_part_id.id,
                                                'part_name': model_part.car_part_id.name,
                                                'installation_price': float(model_part.installation_price)}, car_model_parts))
        return JsonResponse(data={'car_parts': model_parts}, safe=False)
    except Exception as e:
        print('algo salio mal -->', str(e))
        return JsonResponse(data={'error':True, 'message': 'algo salio mal'}, status=500)

    
@api_view(['POST'])
@permission_classes((permissions.AllowAny,))
@transaction.atomic
def create_client(request, format=None):
    serializer = ClientSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(data=serializer.data, status= status.HTTP_201_CREATED)
    return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)