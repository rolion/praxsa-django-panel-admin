from django.contrib import admin

admin.site.site_header = 'Praxsa Panel Admin'

from .models import Car_Brand, Car_Model, Car_Part, Car_Model_Part, Window_Film, Window_Film_Reel, Window_Film_Reel_Storage, Client, Sale_Header, Sale_Detail, Sucursal, inventario, instalador_sucursal
# from .admin_config.car_model_winfow_film_part import CarModelWindowFilmPart
from .admin_config.car_brand import CarBrand
from .admin_config.car_model import CarModel
from .admin_config.car_model_part import CarModelPart
from .admin_config.window_film import WindowFilm
from .admin_config.window_film_reel import WindowFilmReel
from .admin_config.window_film_reel_storage import WindowFilmReelStorage
from .admin_config.sales_admin import SalesAdmin

# admin.site.disable_action("delete_selected")
admin.site.register(Car_Brand, CarBrand)
admin.site.register(Car_Model, CarModel)
admin.site.register(Car_Model_Part, CarModelPart)
admin.site.register(Car_Part)
admin.site.register(Sucursal)
admin.site.register(inventario)
admin.site.register(instalador_sucursal)
admin.site.register(Window_Film, WindowFilm)
admin.site.register(Window_Film_Reel, WindowFilmReel)
admin.site.register(Window_Film_Reel_Storage, WindowFilmReelStorage)
admin.site.register(Client)
admin.site.register(Sale_Header, SalesAdmin)
