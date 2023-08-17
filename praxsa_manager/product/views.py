from django.shortcuts import render
from django.http.response import JsonResponse
from django.template import loader
from .models import Car_Model_Part, Window_Film_Reel, Car_Brand, Car_Model, Car_Part, Window_Film
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import permissions
from .serializer.client_serializer import ClientSerializer
from django.db import transaction

from django.http import HttpResponse


def index(request):
    latest_brand_list = Car_Brand.objects.order_by("id")
    # template = loader.get_template("product/index.html")
    context = {
        "latest_brand_list": latest_brand_list,
    }
    # return HttpResponse(template.render(context, request))
    return render(request, "product/index.html", context)

def get_car_part_info(request, car_model_id):
    car_part = Car_Model_Part.objects.select_related("car_part_id").filter(car_model_id = car_model_id)
    items = list(map(lambda part: {'part_id': part.car_part_id.id, 
                                   'name': part.car_part_id.name, 
                                   'quantity': part.quantity, 
                                   'width': part.width, 
                                   'length': part.length, 
                                   'installation_price': part.installation_price
                                   }, car_part))
    films = Window_Film_Reel.objects.select_related('window_film_id').all()
    window_film = list(map(lambda film: {'name': film.window_film_id.name, 
                                         'reel_id':film.id, 
                                         'price': film.price, 
                                         'film_id': film.window_film_id.id, 
                                         'width': film.width
                                         }, films ))
    return JsonResponse(data={'items': items, 
                              'window_film': window_film
                              }, safe=False)

def get_layer_info(request, layer_id):
    film = Window_Film.objects.get(pk = layer_id)
    print('film -->', film)
    return JsonResponse(data={'layer': {'name': film.name, 'content': film.content} }, safe=False)

def get_call_info(request):
    """
    return calculator information, brand, models, car parts and car part price
    """
    car_brands = Car_Brand.objects.all()
    brands = list(map(lambda brand: {'id': brand.id, 'name': brand.name}, car_brands))
    car_models = Car_Model.objects.select_related('car_brand_id').all().order_by('name')
    models = list(map(lambda model: {'id': model.id, 'name':model.name, "brand_id": model.car_brand_id.id}, car_models))
    car_parts = Car_Part.objects.all()
    parts = list(map(lambda part: {'id': part.id, 'name': part.name}, car_parts))
    car_model_parts = Car_Model_Part.objects.all()
    model_parts = list(map(lambda model_part: {'id': model_part.id, 
                                               'width': model_part.width, 
                                               'length': model_part.length,
                                               'quantity': model_part.quantity, 
                                               'model_id': model_part.car_model_id.id, 
                                               'part_id': model_part.car_part_id.id,
                                               'part_name': model_part.car_part_id.name,
                                               'installation_price': float(model_part.installation_price)}, car_model_parts))
    window_films = Window_Film.objects.all()
    films = list(map(lambda film: {'id': film.id, 'name': film.name}, window_films))
    window_film_reels = Window_Film_Reel.objects.select_related('window_film_id').all()
    window_film = list(map(lambda film: {'name': film.window_film_id.name, 
                                         'reel_id':film.id, 
                                         'price': float(film.price), 
                                         'film_id': film.window_film_id.id,
                                         'width': film.width,
                                         'film_name': film.window_film_id.name
                                         }, window_film_reels ))
    return JsonResponse(data={'brands': brands, 
                              'models': models, 
                              'parts': parts, 
                              'model_parts': model_parts, 
                              'films': films, 
                              'car_part_film_price': window_film}, safe=False)
    
@api_view(['POST'])
@permission_classes((permissions.AllowAny,))
@transaction.atomic
def create_client(request, format=None):
    serializer = ClientSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(data=serializer.data, status= status.HTTP_201_CREATED)
    return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)