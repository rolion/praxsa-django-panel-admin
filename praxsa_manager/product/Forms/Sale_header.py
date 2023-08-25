from django import forms
from django.forms import ModelForm
from ..models import Sale_Header

class SaleHeaderForm(ModelForm):

    class Meta:
        model = Sale_Header
        fields = "__all__"