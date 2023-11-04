from django import forms
from django.forms import ModelForm
from ..models import Proforma_Header
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from ..helper.proforma import Proforma_Helper

class SaleHeaderForm(ModelForm):

    helper = Proforma_Helper()

    class Meta:
        model = Proforma_Header
        fields = "__all__"