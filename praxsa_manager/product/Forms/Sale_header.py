from django import forms
from django.forms import ModelForm
from ..models import Sale_Header
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from ..helper.proforma import Proforma_Helper

class SaleHeaderForm(ModelForm):

    helper = Proforma_Helper()
    
    def clean_codigo_garantia(self):
        status = self.cleaned_data['sales_status']
        if (status == self.helper.inst or status == self.helper.apr) and self.cleaned_data['codigo_garantia'] is None:
            raise ValidationError("porfavor agregue el codigo de garantia")
        return self.cleaned_data['codigo_garantia']
    
    def save(self, commit = True):
        instance = super(SaleHeaderForm, self).save(commit=False)
        # if instance.is_valid():
        print('instance ', instance)
        # sale_header = instance.sales_header_id
        # if sale_header.id is not None and ( self.is_proforma_installed(sale_header) or self.is_proforma_approved(sale_header)):
        #     print('actualizar inventario')
        #     inventario = self.is_inventory_valid(sucursal = sale_header.sucursal, lamina=instance.window_film_id.id, mtr_to_install = instance.length, width=instance.width)
        #     self.inv_helper.update_inventory(sucursal_id=sale_header.sucursal, bobina=inventario.bobina,length_to_reduce= instance.length)
        instance.save()
        return instance


    class Meta:
        model = Sale_Header
        fields = "__all__"