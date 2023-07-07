from django import forms
from django.forms import ModelForm
from .models import Sale_Detail, Window_Film_Reel, Car_Model_Part
from django.core.exceptions import ValidationError
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

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
    
    def clean(self):
        cleaned_data = super().clean()
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

        except ObjectDoesNotExist:
            self.add_error("car_part_id", 'item invalido')
            self.add_error("width", 'item invalido!')
            self.add_error("length", 'item invalido!')
            self.add_error("quantity", 'item invalido!')
    class Meta:
        model = Sale_Detail
        fields = "__all__"
        