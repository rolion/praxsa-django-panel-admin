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
        print('metod is inventory valid, sucursal ', sucursal)
        return self.inv_helper.get_bobina_by_sucursal_lamina_width(sucursal_id=sucursal, lamina_id=lamina,width=width, length_to_sell= mtr_to_install )
        
    
    def clean(self):
        cleaned_data = super().clean()
        # print('clean data', cleaned_data)
        cc_width = cleaned_data.get('width')
        cc_length = cleaned_data.get('length')
        cc_car_part_id = cleaned_data.get('car_part_id')
        cc_window_film_id = cleaned_data.get("window_film_id")
        cc_film_price = cleaned_data.get("window_film_price")
        cc_window_film_price =  cleaned_data.get("window_film_price")
        cc_intallation_price = cleaned_data.get("installation_price")
        cc_quantity = cleaned_data.get("quantity")
        cc_sub_total = cleaned_data.get("sub_total")
        aux_sub_total = int(cc_quantity) * (float(cc_intallation_price) + float(cc_window_film_price))
        if not aux_sub_total == float(cc_sub_total):
            self.add_error("sub_total", 'sub total invalido')

        try:
            Window_Film_Reel.objects.get(window_film_id=cc_window_film_id,price=cc_film_price)
        except ObjectDoesNotExist:
            self.add_error("window_film_id", 'lamina invalida')
            self.add_error("window_film_price", 'precio invalido')
        
        try:
            Car_Model_Part.objects.get(car_part_id=cc_car_part_id, 
                                                  width = cc_width, 
                                                  length = cc_length,
                                                  quantity = cc_quantity)
        except MultipleObjectsReturned:
            print('multiple object returned')

        except ObjectDoesNotExist:
            self.add_error("car_part_id", 'item invalido')
            self.add_error("width", 'item invalido!')
            self.add_error("length", 'item invalido!')
            self.add_error("quantity", 'item invalido!')

        sale_header = cleaned_data.get("sales_header_id")
        
        if self.is_proforma_approved(sale_header):
            # validar la cantidad de metros disponibles en el inventario
            try:
                self.is_inventory_valid(sucursal = sale_header.sucursal, lamina=cc_window_film_id.id, mtr_to_install = cc_length, width=cc_width)
            except FieldError as e: 
                self.add_error('window_film_id', str(e))
        if self.is_proforma_installed(sale_header):
            # todo, reducir la cantidad de inventario
            try:
                inventario = self.is_inventory_valid(sucursal = sale_header.sucursal, lamina=cc_window_film_id.id, mtr_to_install = cc_length, width=cc_width)
                print('inventario bobina', inventario.bobina)
                self.inv_helper.update_inventory(sucursal_id=sale_header.sucursal, bobina=inventario.bobina,length_to_reduce= cc_length)
            except FieldError as e: 
                self.add_error('window_film_id', str(e))
            except Exception as e:
                self.add_error('window_film_id', str(e))

    def update_inventory(self, sucursal, bobina, length_to_reduce):
        self.inv_helper.update_inventory(sucursal_id= sucursal, bobina= bobina, length_to_reduce=length_to_reduce)

    class Meta:
        model = Sale_Detail
        fields = "__all__"
        