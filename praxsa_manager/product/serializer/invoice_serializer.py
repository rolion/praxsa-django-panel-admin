from rest_framework import serializers
from datetime import datetime
from ..models import Client, Proforma_Detail, Proforma_Header
# from rest_framework.validators import UniqueValidator, Email


        
class SaleDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proforma_Detail
        fields = [
            "car_part_id",
            "width",
            "length",
            "price",
            "quantity",
            "window_film_id",
            'installation_price',
            'window_film_price',
            "price"
        ]
        
class SalesHeaderSerializer(serializers.ModelSerializer):
    carPartItems = SaleDetailSerializer(many=True)
    class Meta: 
        model = Proforma_Header
        fields =  ["client_id", "name", "email", "car_plate", "car_model_id", "total_price", 'carPartItems', 'phone_number', 'ci_nit']
    
    def create(self, validate_data):
        items = validate_data.pop('carPartItems')
        invoice = Proforma_Header.objects.create(date=datetime.now(), **validate_data)
        
        for item in items:
            Proforma_Detail.objects.create(sales_header_id=invoice, **item)
            
        return invoice
        