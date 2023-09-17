from ..models import pago
from django import forms
from django.forms import ModelForm
class PagosForm(ModelForm):

    class Meta:
        model = pago
        fields = "__all__"