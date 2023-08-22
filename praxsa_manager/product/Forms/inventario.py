from django import forms
from django.forms import ModelForm
from ..models import inventario
from django.core.exceptions import ValidationError
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

class InventarioForm(ModelForm):

    def clean(self):
        cleaned_data = super().clean()
        to_install = cleaned_data.get("to_install")
        quantity = cleaned_data.get("quantity")
        installed = cleaned_data.get("installed")
        if to_install < installed:
            self.add_error("los metros disponibles no pueden ser menor a los metros instalados")

    class Meta:
        model = inventario
        fields = "__all__"