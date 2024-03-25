from rest_framework import serializers
from django.utils import timezone

from ..utils.exception.proforma import ProformaException
from ..models import Client, Proforma_Detail, Proforma_Header
import logging


        
class SaleDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proforma_Detail
        fields = [
            "car_part",
            "width",
            "length",
            "quantity",
            "window_film",
            'installation_price',
            'window_film_price',
            "sub_total"
        ]
        
class SalesHeaderSerializer(serializers.ModelSerializer):
    carPartItems = SaleDetailSerializer(many=True)
    logger = logging.getLogger('calculadora')
    class Meta: 
        model = Proforma_Header
        fields =  ["name", "email", "car_plate", "car_model_id", "total_price", 'carPartItems', 'phone_number', 'ci_nit', 'sucursal', 'created_by']
    
    def create(self, validate_data):
        try:
            items = validate_data.pop('carPartItems')
            invoice = Proforma_Header.objects.create(proforma_created_on=timezone.now(), **validate_data)
            self.logger.warning(f'proforma created {invoice.id}')
            self.logger.warning(f'cliente {invoice.name}, modelo: {invoice.car_model_id.name}, total pagar: {invoice.total_price}')
            for item in items:
                detail = Proforma_Detail(proforma_header=invoice, **item)
                detail.save()
                self.logger.warning(f'detail  ancho: {detail.width}, lamina: {detail.window_film}, precio instalacion: {detail.installation_price}, cantidad: {detail.quantity} ,precio {detail.sub_total}, ')
            return invoice
        except Exception as e:
            self.logger.error(f'No se pudo crear la proforma {e}, data {validate_data}')
            raise ProformaException('No se pudo crear la proforma')
        