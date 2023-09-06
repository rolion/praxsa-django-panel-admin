from django import forms
from django.core.exceptions import FieldError
from django.forms import ModelForm
from ..models import Sale_Detail, Window_Film_Reel, Car_Model_Part, Window_Film
from django.core.exceptions import ValidationError
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from ..helper.proforma import Proforma_Helper
from ..helper.inventory import Inventory_helper
from ..business.inventario import Inventario_Business

class CarItemField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.description

class CarModelPartForm(ModelForm):
    
    disponibilidad = forms.IntegerField(required=False, initial = 0, disabled=True)
    proforma_helper = Proforma_Helper()
    inv_helper = Inventory_helper()
    inv_bussiness = Inventario_Business()

    def is_proforma_approved(self, proforma):
        return proforma.sales_status == self.proforma_helper.apr
    
    def is_proforma_installed(self, proforma):
        return proforma.sales_status == self.proforma_helper.inst
    
    def is_inventory_valid(self, sucursal, lamina, mtr_to_install, width):
        return self.inv_helper.get_bobina_by_sucursal_lamina_width(sucursal_id=sucursal, lamina_id=lamina,width=width, length_to_sell= mtr_to_install )
    
    def clean_sub_total(self):
        cleaned_data = super().clean()
        cc_sub_total = cleaned_data.get("sub_total")
        if not cc_sub_total.compare(0) == 1:
            raise ValidationError("sub total invalido, no puede ser 0")
        return cc_sub_total
    
    # def clean_window_film(self):
    #     cleaned_data = super().clean()
    #     cc_window_film = cleaned_data.get("window_film")
    #     try:
    #         query = Window_Film.objects.filter(id = cc_window_film)
    #         if query.exists() == False:
    #             raise ValidationError('lamina no valida')
    #         return cc_window_film
    #     except Exception as e:
    #         print('algo salio mal -->', str(e))
    #         raise ValidationError('algo salio mal, contactar al adminsitrador')
        
    def clean_length(self):
        cleaned_data = super().clean()
        cc_length = cleaned_data.get("length")
        if cc_length > 0:
            return cc_length
        else:
            raise ValidationError('tiene que ser mayor a 0')
    
    def item_width_lte_film_width(self, item, model, width):
        query = Car_Model_Part.objects.select_related('car_part_id', 'car_model_id').filter(car_model_id = model, car_part_id = item, width__lte = width)
        return query.exists()

    
    def clean(self):
        cleaned_data = super().clean()
        cc_width = cleaned_data.get('width')
        cc_car_part_id = cleaned_data.get('car_part')
        cc_quantity = cleaned_data.get('quantity')
        cc_installation_price = cleaned_data.get('installation_price')
        cc_length = cleaned_data.get('length')
        sale_header = cleaned_data.get("sales_header")
        cc_window_film = cleaned_data.get("window_film")

        if cc_length is None:
            self.add_error('length','este campo es requerido')
            return
        if sale_header.sales_type == self.proforma_helper.tipo_venta_instalacion:
        
            if self.item_width_lte_film_width(cc_car_part_id, sale_header.car_model_id, cc_width) == False:
                self.add_error('window_film','el ancho de la bobina es menor que el ancho del item')
            if cc_quantity < 1:
                self.add_error('quantity','campo requerido')
            if cc_installation_price < 1:
                self.add_error('installation_price','campo requerido')
            available_reel = self.inv_bussiness.available_window_film_reel_in_inventory_to_sell(width=cc_width, 
                                                                                                windows_film=cc_window_film, 
                                                                                                sucursal=sale_header.sucursal, 
                                                                                                total_length_to_sell=cc_length * cc_quantity)

        if sale_header.sales_type == self.proforma_helper.tipo_venta_metro_lineal:
        #     if cc_car_part_id is not None:
        #         self.add_error('car_part_id','este campo no es requerido')
            if cc_quantity > 0:
                self.add_error('quantity','campo no requerido')
            if cc_installation_price.compare(0) == 1:
                self.add_error('installation_price','campo no requerido')
            available_reel = self.inv_bussiness.available_window_film_reel_in_inventory_to_sell(width=cc_width, 
                                                                                                windows_film=cc_window_film, 
                                                                                                sucursal=sale_header.sucursal, 
                                                                                                total_length_to_sell=cc_length)
        if available_reel.exists() is False:
            self.add_error('window_film','no hay disponibilidad de lamina')

    def update_inventory(self, sucursal, bobina, length_to_reduce):
        self.inv_helper.update_inventory(sucursal_id= sucursal, bobina= bobina, length_to_reduce=length_to_reduce)

    class Meta:
        model = Sale_Detail
        fields = "__all__"
        