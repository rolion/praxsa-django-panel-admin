from django import forms
from django.forms import ModelForm
from ..models import Sale_Header
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from ..helper.proforma import Proforma_Helper

class SaleHeaderForm(ModelForm):

    helper = Proforma_Helper()
        
    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('sales_status')
        if (status == self.helper.nov) and cleaned_data.get('codigo_garantia') is None:
            raise ValidationError("porfavor agregue el codigo de garantia")


    class Meta:
        model = Sale_Header
        fields = "__all__"