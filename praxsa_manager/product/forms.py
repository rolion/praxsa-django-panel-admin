from django import forms
from django.forms import ModelForm
from .models import Sale_Detail

class CarModelPartForm(ModelForm):
    a = forms.Select()
    class Meta:
        model = Sale_Detail
        fields = "__all__"
        
    # def clean(self):
    #     print('clean data----', self.cleaned_data)
    #     return self.cleaned_data
        
    # def clean_car_model_part_id(self):
    #     # car_part_id = self.cleaned_data['car_model_part_id']
    #     print('car_model_part_id-------', self.cleaned_data)
    #     return True