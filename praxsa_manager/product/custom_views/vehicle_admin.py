from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import authentication, generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Car_Brand, Car_Model, Car_Model_Part, Car_Part
from ..permissions import IsStaffUser
from ..serializer.vehicle_serializer import (
    CarBrandSerializer,
    CarModelPartSerializer,
    CarModelSerializer,
    CarPartSerializer,
)

_STANDARD_PERMISSIONS = [permissions.IsAuthenticated, IsStaffUser, permissions.DjangoModelPermissions]


class CarBrandListCreateView(generics.ListCreateAPIView):
    """Lista (solo activas por defecto, ?include_inactive=true para verlas
    todas) y crea marcas. ?search= filtra por nombre."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = _STANDARD_PERMISSIONS
    serializer_class = CarBrandSerializer
    queryset = Car_Brand.objects.annotate(models_count=Count('car_model', distinct=True))

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get('include_inactive') != 'true':
            queryset = queryset.filter(is_active=True)
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)
        return queryset


class CarBrandDetailView(generics.RetrieveUpdateAPIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = _STANDARD_PERMISSIONS
    serializer_class = CarBrandSerializer
    queryset = Car_Brand.objects.annotate(models_count=Count('car_model', distinct=True))
    http_method_names = ['get', 'patch', 'head', 'options']


class CarBrandToggleActiveView(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsStaffUser]

    def patch(self, request, pk):
        if not request.user.has_perm('product.change_car_brand'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            brand = Car_Brand.objects.get(pk=pk)
        except Car_Brand.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        is_active = request.data.get('is_active')
        if is_active is None:
            return Response({'is_active': ['Este campo es obligatorio.']}, status=status.HTTP_400_BAD_REQUEST)

        brand.is_active = bool(is_active)
        brand.save(update_fields=['is_active'])
        brand.models_count = brand.car_model_set.count()
        return Response(CarBrandSerializer(brand).data, status=status.HTTP_200_OK)


class CarPartListCreateView(generics.ListCreateAPIView):
    """Lista (solo activos por defecto) y crea items. ?search= filtra por nombre."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = _STANDARD_PERMISSIONS
    serializer_class = CarPartSerializer
    queryset = Car_Part.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get('include_inactive') != 'true':
            queryset = queryset.filter(is_active=True)
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)
        return queryset


class CarPartDetailView(generics.RetrieveUpdateAPIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = _STANDARD_PERMISSIONS
    serializer_class = CarPartSerializer
    queryset = Car_Part.objects.all()
    http_method_names = ['get', 'patch', 'head', 'options']


class CarPartToggleActiveView(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsStaffUser]

    def patch(self, request, pk):
        if not request.user.has_perm('product.change_car_part'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            part = Car_Part.objects.get(pk=pk)
        except Car_Part.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        is_active = request.data.get('is_active')
        if is_active is None:
            return Response({'is_active': ['Este campo es obligatorio.']}, status=status.HTTP_400_BAD_REQUEST)

        part.is_active = bool(is_active)
        part.save(update_fields=['is_active'])
        return Response(CarPartSerializer(part).data, status=status.HTTP_200_OK)


class CarModelListCreateView(generics.ListCreateAPIView):
    """Lista (solo activos por defecto) y crea modelos. ?search= filtra por
    nombre de modelo o de marca; ?car_brand_id= filtra por marca."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = _STANDARD_PERMISSIONS
    serializer_class = CarModelSerializer
    queryset = Car_Model.objects.select_related('car_brand_id').annotate(
        items_count=Count('car_model_part', distinct=True)
    )

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get('include_inactive') != 'true':
            queryset = queryset.filter(is_active=True)
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(car_brand_id__name__icontains=search)
            )
        car_brand_id = self.request.query_params.get('car_brand_id')
        if car_brand_id:
            queryset = queryset.filter(car_brand_id=car_brand_id)
        return queryset


class CarModelDetailView(generics.RetrieveUpdateAPIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = _STANDARD_PERMISSIONS
    serializer_class = CarModelSerializer
    queryset = Car_Model.objects.select_related('car_brand_id').annotate(
        items_count=Count('car_model_part', distinct=True)
    )
    http_method_names = ['get', 'patch', 'head', 'options']


class CarModelToggleActiveView(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsStaffUser]

    def patch(self, request, pk):
        if not request.user.has_perm('product.change_car_model'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            car_model = Car_Model.objects.get(pk=pk)
        except Car_Model.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        is_active = request.data.get('is_active')
        if is_active is None:
            return Response({'is_active': ['Este campo es obligatorio.']}, status=status.HTTP_400_BAD_REQUEST)

        car_model.is_active = bool(is_active)
        car_model.save(update_fields=['is_active'])
        return Response(CarModelSerializer(car_model, context={'request': request}).data, status=status.HTTP_200_OK)


class CarModelItemsView(generics.ListCreateAPIView):
    """Items (Car_Model_Part) asociados a un Modelo puntual. GET lista, POST
    asocia (item nuevo o existente + width/length/quantity/installation_price
    -- ver ADR-modulo-vehiculos-relacion-modelo-item)."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = _STANDARD_PERMISSIONS
    serializer_class = CarModelPartSerializer

    def get_car_model(self):
        return get_object_or_404(Car_Model, pk=self.kwargs['model_id'])

    def get_queryset(self):
        return Car_Model_Part.objects.filter(
            car_model_id=self.kwargs['model_id']
        ).select_related('car_part_id')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['car_model'] = self.get_car_model()
        return context


class CarModelItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Ver/editar/quitar una asociacion Modelo<->Item puntual. PATCH solo
    permite tocar width/length/quantity/installation_price -- no cambia el
    item asociado (car_part_id), ver CarModelPartSerializer.validate().
    DELETE = borrado fisico de la fila Car_Model_Part, no del Car_Part ni
    del Car_Model -- ver ADR-modulo-vehiculos-relacion-modelo-item: seguro
    para el historial de proformas ya creadas, que copian sus propios
    valores."""

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = _STANDARD_PERMISSIONS
    serializer_class = CarModelPartSerializer
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return Car_Model_Part.objects.filter(
            car_model_id=self.kwargs['model_id']
        ).select_related('car_part_id')
