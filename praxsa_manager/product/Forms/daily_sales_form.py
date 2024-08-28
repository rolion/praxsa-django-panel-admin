from django import forms
from django.forms import ModelForm

from praxsa_manager.product.Forms.nota_venta_form import NotaVentaForm
from ..models import Proforma_Detail, Car_Model_Part
from django.core.exceptions import ValidationError

class DailySalesForm(NotaVentaForm):

    installation_price = forms.DecimalField()
    discount = forms.DecimalField()
    total_pay = forms.DecimalField()