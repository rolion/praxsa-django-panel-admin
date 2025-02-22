from ..models import pago
from django import forms
from django.forms import ModelForm
class PagosForm(ModelForm):

    

    class Meta:
        model = pago
        fields = "__all__"
        
    def __init__(self, *args, **kwargs):
        self.nota_venta_init= kwargs.pop('nota_venta_init', None)  # Recibir parámetro extra
        super().__init__(*args, **kwargs)
        
        if self.nota_venta_init:
            self.fields['nota_venta'].initial = self.nota_venta_init  # Asignar el valor inicial
        
        # self.fields['nota_venta'].widget.attrs['disabled'] =  'disabled'
        
    def clean_nota_venta(self):
        """
        Dado que el campo está disabled y no se envía en el POST,
        forzamos el valor de nota_venta al valor inicial o al valor recibido.
        """
        # Se puede usar self.nota_venta_value o el initial del campo.
        return self.nota_venta_init or self.fields['nota_venta'].initial