from decimal import Decimal
from django import forms
from django.forms import ModelForm
from ..models import Proforma_Header
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from ..helper.proforma import Proforma_Helper

class SaleHeaderForm(ModelForm):

    helper = Proforma_Helper()

    def clean_discount(self):
        cleaned_data = super().clean()
        cc_discount = cleaned_data.get("discount")
        cc_total_price = cleaned_data.get("total_price")
        
        if cc_discount.compare(0) == 0 or cc_discount.compare(cc_total_price*Decimal(0.5)) == 0:
            return cc_discount
        if cc_discount.compare(cc_total_price*Decimal(0.5)) ==1:
            raise ValidationError("El descuento no puede ser mayor que el 50% del precio total")
        return cc_discount
    
    def clean_discount_reason(self):
        cleaned_data = super().clean()
        cc_discount = cleaned_data.get("discount")
        cc_discount_reason = cleaned_data.get("discount_reason")
        if cc_discount is None:
            return cc_discount_reason
        if cc_discount.compare(0) == 1 and len(cc_discount_reason) == 0:
            raise ValidationError("Debe agregar el motivo del descuento o quien aprueba este descuento")
        
        return cc_discount_reason
    
    def clean_car_model_id(self):
        cleaned_data = super().clean()
        cc_sales_type = cleaned_data.get("sales_type")
        cc_car_model_id = cleaned_data.get("car_model_id")
        if cc_sales_type == 'venta_instalacion' and cc_car_model_id  is None:
            raise ValidationError("Tiene que seleccionar un modelo!")
        return cc_car_model_id
    
    def clean_car_plate(self):
        cleaned_data = super().clean()
        cc_sales_type = cleaned_data.get("sales_type")
        cc_car_plate = cleaned_data.get('car_plate')
        if cc_sales_type == 'venta_instalacion' and cc_car_plate  is None:
            raise ValidationError("Tiene que agregar el numero de placa!")
        return cc_car_plate

    class Meta:
        model = Proforma_Header
        fields = "__all__"