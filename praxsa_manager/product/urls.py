from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns

from . import views
from rest_framework.authtoken import views as rf_token
from .custom_views.auth_token import CustomAuthToken
from .custom_views.invoice import InvoiceView, ListUserInvoice
from .custom_views.bobina import BobinaView
app_name = 'product'
urlpatterns = [
    path('get_car_part_info/<int:car_model_id>/<int:sucursal_id>', views.get_car_part_info, name= 'get_car_part_info'),
    path('get_proforma_car_part_info/<int:proforma_id>', views.get_proforma_car_part_info, name= 'get_car_part_info'),
    # 
    path('calculator_info', views.get_calculator_info, name='get_calculator_info'),
    path('model_parts/<int:model_id>', views.get_model_parts,name = 'get_model_parts'),
    path('get_inventory/<int:sucursal_id>', views.get_inventory, name='get_inventory'),
    path('create_client', views.create_client, name='create_client'),
    path('api-token-auth/', CustomAuthToken.as_view()),
    path('invoice', InvoiceView.as_view()),
    path('invoice/<int:pk>/', InvoiceView.as_view()),
    path('invoice/all', ListUserInvoice.as_view()),
    path('bobina/<int:pk>', views.get_bobina, name='get_bobina'),
    path('layer/<int:layer_id>', views.get_layer_info, name='get_layer_info')
]
urlpatterns = format_suffix_patterns(urlpatterns)