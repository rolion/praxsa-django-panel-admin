from rest_framework import serializers
from django.utils import timezone

from ..utils.exception.proforma import ProformaException
from ..models import Client, Proforma_Detail, Proforma_Header
from ..helper.proforma import Proforma_Helper
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
    helper = Proforma_Helper()
    class Meta: 
        model = Proforma_Header
        fields =  ["name", "email", "car_plate", "car_model_id", "total_price", 'carPartItems', 'phone_number', 'ci_nit', 'sucursal', 'created_by']
    
    def create(self, validate_data):
        try:
            items = validate_data.pop('carPartItems')
            # validate_data['origen'] = self.helper.origen_calculadora
            invoice = Proforma_Header.objects.create(proforma_created_on=timezone.now(),origen = self.helper.origen_calculadora, **validate_data)
            self.logger.warning(f'proforma created {invoice.id}')
            self.logger.warning(f'cliente {invoice.name}, modelo: {invoice.car_model_id.name}, total pagar: {invoice.total_price}')
            for item in items:
                detail = Proforma_Detail(proforma_header=invoice, **item)
                detail.save()
                self.logger.warning(f'detail  ancho: {detail.width}, lamina: {detail.window_film}, precio instalacion: {detail.installation_price}, cantidad: {detail.quantity} ,precio {detail.sub_total}, ')
            return invoice
        except Exception as e:
            self.logger.error(f'No se pudo crear la proforma {e}, data {validate_data}')
            print(e)
            raise ProformaException('No se pudo crear la proforma')
        