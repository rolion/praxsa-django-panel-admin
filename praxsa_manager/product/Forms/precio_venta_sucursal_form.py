from ..models import precio_venta_sucursal
from django import forms
from django.forms import ModelForm
class PrecioVentaSucursalForm(ModelForm):

    

    class Meta:
        model = precio_venta_sucursal
        fields = "__all__"