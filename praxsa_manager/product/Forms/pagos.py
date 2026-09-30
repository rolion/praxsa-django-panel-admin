from ..helper import estados
from ..models import Nota_Venta, pago
from django.core.exceptions import ValidationError
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

    def clean(self):
        """Alta de pago: la nota de venta debe estar Por cobrar y el trabajo Terminado
        (Orden_Estado_Business.registrar_pago_instancia lo vuelve a verificar)."""
        cleaned = super().clean()
        if self.instance.pk is None:
            nota_venta_id = self.nota_venta_init or self.fields['nota_venta'].initial
            if nota_venta_id:
                nota_venta = Nota_Venta.objects.select_related('nota_trabajo').filter(pk=nota_venta_id).first()
                if nota_venta is not None:
                    if nota_venta.status != estados.NV_POR_COBRAR:
                        raise ValidationError('La nota de venta no está Por cobrar.')
                    if nota_venta.nota_trabajo.status != estados.NT_TERMINADO:
                        raise ValidationError('El trabajo aún no está terminado; no se puede registrar el pago.')
        return cleaned
