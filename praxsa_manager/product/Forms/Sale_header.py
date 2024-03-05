from django import forms
from django.forms import ModelForm
from ..models import Proforma_Header
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from ..helper.proforma import Proforma_Helper

class SaleHeaderForm(ModelForm):

    helper = Proforma_Helper()

    def clean_car_model_id(self):
        cleaned_data = super().clean()
        cc_sales_type = cleaned_data.get("sales_type")
        cc_car_model_id = cleaned_data.get("car_model_id")
        print(cc_car_model_id, cc_sales_type)
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