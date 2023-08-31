from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns

from . import views
from rest_framework.authtoken import views as rf_token
from .custom_views.auth_token import CustomAuthToken
from .custom_views.invoice import InvoiceView, ListUserInvoice
from .custom_views.bobina import BobinaView
app_name = 'product'
urlpatterns = [
    # ex: /polls/
    # path("", views.index, name="index"),
    # ex: /polls/5/
    # path("<int:car_brand_id>/car_brand/", views.car_brand, name="car_brand"),
    # # ex: /polls/5/results/
    # path("<int:car_model_id>/car_model/", views.car_model, name="car_model"),
    # # ex: /polls/5/vote/
    # path("<int:window_film_id>/window_film/", views.window_film, name="window_film"),
    path('get_car_part_info/<int:car_model_id>/<int:sucursal_id>', views.get_car_part_info, name= 'get_car_part_info'),
    path('get_call_info', views.get_call_info, name='get_call_info'),
    path('create_client', views.create_client, name='create_client'),
    path('api-token-auth/', CustomAuthToken.as_view()),
    path('invoice', InvoiceView.as_view()),
    path('invoice/<int:pk>/', InvoiceView.as_view()),
    path('invoice/all', ListUserInvoice.as_view()),
    path('bobina/<int:pk>', views.get_bobina, name='get_bobina'),
    path('layer/<int:layer_id>', views.get_layer_info, name='get_layer_info')
]
urlpatterns = format_suffix_patterns(urlpatterns)