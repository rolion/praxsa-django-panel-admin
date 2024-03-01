from rest_framework import serializers
from datetime import datetime
from ..models import Client, Proforma_Detail, Proforma_Header
# from rest_framework.validators import UniqueValidator, Email


        
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
    class Meta: 
        model = Proforma_Header
        fields =  ["name", "email", "car_plate", "car_model_id", "total_price", 'carPartItems', 'phone_number', 'ci_nit', 'sucursal', 'created_by']
    
    def create(self, validate_data):
        try:
            items = validate_data.pop('carPartItems')
            invoice = Proforma_Header.objects.create(proforma_created_on=datetime.now(), **validate_data)
            for item in items:
                detail = Proforma_Detail(proforma_header=invoice, **item)
                detail.save()
            print('proforma created ', invoice.id)
            return invoice
        except Exception as e:
            print('algo salio mal -------> ', str(e))
            return None
        