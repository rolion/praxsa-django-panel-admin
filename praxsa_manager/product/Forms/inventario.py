from django import forms
from django.forms import ModelForm
from ..models import inventario
from django.core.exceptions import ValidationError
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

class InventarioForm(ModelForm):

    def clean_to_install(self):
        cleaned_data = super().clean()
        to_install = cleaned_data.get("to_install")
        if to_install.compare(0) == -1: # to install < 0
            raise ValidationError("no puede ser negativo!")
        return to_install
        
    def clean_installed(self):
        cleaned_data = super().clean()
        installed = cleaned_data.get("installed")
        if installed.compare(0) == -1: # installed < 0
            raise ValidationError("no puede ser negativo!")
        return installed
    class Meta:
        model = inventario
        fields = "__all__"