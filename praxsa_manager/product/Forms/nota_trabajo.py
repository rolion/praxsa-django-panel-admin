from django import forms
from django.forms import ModelForm
from ..models import Nota_trabajo
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from ..helper.proforma import Proforma_Helper

class NotaTrabajoForm(ModelForm):


    class Meta:
        model = Nota_trabajo
        fields = "__all__"