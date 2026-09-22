from decimal import Decimal

from rest_framework import serializers
from django.utils import timezone

from ..utils.exception.proforma import ProformaException
from ..models import Car_Model_Part, Client, Proforma_Detail, Proforma_Header
from ..helper.proforma import Proforma_Helper
from ..business.pricing import Pricing_Business, calculate_subtotal_venta_instalacion
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
    pricing_business = Pricing_Business()
    class Meta:
        model = Proforma_Header
        fields =  ["name", "email", "car_plate", "car_model_id", "total_price", 'carPartItems', 'phone_number', 'ci_nit', 'sucursal', 'created_by']

    def validate(self, data):
        """El precio nunca se confía del cliente: se recalcula acá con los precios
        reales (Car_Model_Part.installation_price + precio_venta_sucursal/inventario)
        y se sobrescribe antes de que create() persista validated_data. Ver ADR-004."""
        car_model = data.get('car_model_id')
        sucursal = data.get('sucursal')
        total_price = Decimal('0')
        for item in data.get('carPartItems', []):
            car_part = item.get('car_part')
            car_model_part = Car_Model_Part.objects.filter(car_model_id=car_model, car_part_id=car_part).first()
            if car_model_part is None:
                raise serializers.ValidationError(
                    f'No existe información de precio de instalación para el ítem {car_part} en el modelo {car_model}.'
                )
            window_film = item.get('window_film')
            unit_price = self.pricing_business.resolve_unit_price(
                sucursal_id=getattr(sucursal, 'id', None),
                lamina_id=getattr(window_film, 'id', None),
                width=item.get('width'),
            )
            if unit_price is None:
                raise serializers.ValidationError(
                    f'No hay precio disponible para la lámina/ancho solicitado en la sucursal seleccionada (ítem {car_part}).'
                )
            item['installation_price'] = car_model_part.installation_price
            item['window_film_price'] = unit_price
            item['sub_total'] = calculate_subtotal_venta_instalacion(
                length=item.get('length'),
                quantity=item.get('quantity'),
                unit_price=unit_price,
                installation_price=car_model_part.installation_price,
            )
            total_price += item['sub_total']
        data['total_price'] = total_price
        return data

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
        