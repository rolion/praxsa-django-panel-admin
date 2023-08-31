from django import forms
from django.core.exceptions import FieldError
from django.forms import ModelForm
from ..models import Sale_Detail, Window_Film_Reel, Car_Model_Part
from django.core.exceptions import ValidationError
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from ..helper.proforma import Proforma_Helper
from ..helper.inventory import Inventory_helper

class CarModelPartForm(ModelForm):
    # sub_total =  forms.DecimalField(max_digits=10, decimal_places=2, disabled= True)
    fields = ('car_part_id', 
              'window_film_id', 
              'width', 
              'length', 
              'window_film_price', 
              'installation_price', 
              'quantity', 
              'sub_total')
    proforma_helper = Proforma_Helper()
    inv_helper = Inventory_helper()

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
    
    # def clean_car_part_id(self):
    #     try:
    #         cleaned_data = super().clean()
    #         cc_car_part_id = cleaned_data.get('cc_car_part_id')
    #         Car_Model_Part.objects.get(car_part_id=cc_car_part_id)
    #     except MultipleObjectsReturned:
    #         print('multiple object returned')
    #     except ObjectDoesNotExist:
    #         raise ValidationError("item invalido ", cc_car_part_id)
    #     return cc_car_part_id
    
    def clean_window_film_id(self):
        cleaned_data = super().clean()
        cc_window_film_id = cleaned_data.get("window_film_id")
        # cc_film_price = cleaned_data.get("window_film_price")
        try:

            Window_Film_Reel.objects.filter(window_film_id=cc_window_film_id)

        except ObjectDoesNotExist:
            # self.add_error("window_film_id", 'lamina invalida')
            raise ValidationError("lamina invalida")
        return cc_window_film_id

    
    def clean(self):
        cleaned_data = super().clean()
        cc_width = cleaned_data.get('width')
        cc_length = cleaned_data.get('length')
        cc_window_film_id = cleaned_data.get("window_film_id")
        cc_car_part_id = cleaned_data.get('car_part_id')
        cc_quantity = cleaned_data.get('quantity')
        cc_installation_price = cleaned_data.get('installation_price')
        sale_header = cleaned_data.get("sales_header_id")
        cc_sale_type = cleaned_data.get("sales_type")

        if sale_header.sales_type == self.proforma_helper.tipo_venta_metro_lineal:
            if cc_car_part_id is not None:
                self.add_error('car_part_id','este campo no es requerido en una venta por metro lineal, deseleccione el item')
            if cc_quantity > 0:
                self.add_error('quantity','este campo no es requerido en una venta por metro lineal, colocar en 0')
            if cc_installation_price.compare(0) == 1: # installation price es mayo que 0
                self.add_error('installation_price','este campo no es requerido en una venta por metro lineal, colocar en 0')
        else:
            if cc_car_part_id is None:
                self.add_error('car_part_id','Seleccione un item')
            if cc_quantity == 0:
                self.add_error('quantity','en una venta con instalacion, no puede ser 0')
            if cc_installation_price.compare(0) == -1: # installation price es meno que 0
                self.add_error('installation_price','en una venta por metro lineal, puede ser 0')
            

        if sale_header.id is not None and (self.is_proforma_approved(sale_header) or self.is_proforma_installed(sale_header)):
            # validar la cantidad de metros disponibles en el inventario
            try:
                self.is_inventory_valid(sucursal = sale_header.sucursal, lamina=cc_window_film_id.id, mtr_to_install = cc_length, width=cc_width)
            except FieldError as e: 
                self.add_error('window_film_id', str(e))
                return
        # if sale_header.id is not None and self.is_proforma_installed(sale_header):
        #     # todo, reducir la cantidad de inventario
        #     try:
        #         inventario = self.is_inventory_valid(sucursal = sale_header.sucursal, lamina=cc_window_film_id.id, mtr_to_install = cc_length, width=cc_width)
        #         print('inventario bobina', inventario.bobina)
        #         self.inv_helper.update_inventory(sucursal_id=sale_header.sucursal, bobina=inventario.bobina,length_to_reduce= cc_length)
        #     except FieldError as e: 
        #         self.add_error('window_film_id', str(e))
        #         # return
        #     except Exception as e:
        #         self.add_error('window_film_id', str(e))
                # return
        print('clean called!1')

    # def save(self, commit = True):
    #     instance = super(CarModelPartForm, self).save(commit=False)
    #     # if instance.is_valid():
    #     print(f'header id {instance.sales_header_id.id}, header status {instance.sales_header_id.sales_status}, header type {instance.sales_header_id.sales_type}')
    #     sale_header = instance.sales_header_id
    #     if sale_header.id is not None and ( self.is_proforma_installed(sale_header) or self.is_proforma_approved(sale_header)):
    #         print('actualizar inventario')
    #         inventario = self.is_inventory_valid(sucursal = sale_header.sucursal, lamina=instance.window_film_id.id, mtr_to_install = instance.length, width=instance.width)
    #         self.inv_helper.update_inventory(sucursal_id=sale_header.sucursal, bobina=inventario.bobina,length_to_reduce= instance.length)
    #     instance.save()
    #     return instance


    def update_inventory(self, sucursal, bobina, length_to_reduce):
        self.inv_helper.update_inventory(sucursal_id= sucursal, bobina= bobina, length_to_reduce=length_to_reduce)

    class Meta:
        model = Sale_Detail
        fields = "__all__"
        