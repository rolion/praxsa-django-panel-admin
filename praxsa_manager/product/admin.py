from django.contrib import admin

admin.site.site_header = 'Praxsa Panel Admin'

from .models import Car_Brand, Car_Model, Car_Part, Car_Model_Part, Window_Film, Window_Film_Reel, Window_Film_Reel_Storage, Client, pago

from .models import Proforma_Header, Sucursal, inventario, Nota_trabajo #, instalador_sucursal
# from .admin_config.car_model_winfow_film_part import CarModelWindowFilmPart
from .admin_config.car_brand import CarBrand
from .admin_config.car_model import CarModel
from .admin_config.car_model_part import CarModelPart
from .admin_config.window_film import WindowFilm
from .admin_config.window_film_reel import WindowFilmReel
from .admin_config.window_film_reel_storage import WindowFilmReelStorage
from .admin_config.proforma_admin import ProformaAdmin
from .admin_config.inventory import InventoryAdmin
from .admin_config.nota_trabajo import NotaTrabajoAdmin
from .admin_config.nota_venta import NotaVentaAdmin
from .admin_config.pagos import PagosAdmin

# admin.site.disable_action("delete_selected")
admin.site.register(Car_Brand, CarBrand)
admin.site.register(Car_Model, CarModel)
admin.site.register(Car_Model_Part, CarModelPart)
admin.site.register(Car_Part)
admin.site.register(Sucursal)
admin.site.register(inventario, InventoryAdmin)
# admin.site.register(instalador_sucursal)
admin.site.register(Window_Film, WindowFilm)
admin.site.register(Window_Film_Reel, WindowFilmReel)
admin.site.register(Window_Film_Reel_Storage, WindowFilmReelStorage)
admin.site.register(Client)
admin.site.register(Proforma_Header, ProformaAdmin)
admin.site.register(Nota_trabajo, NotaTrabajoAdmin)
admin.site.register(pago, PagosAdmin)
class NotaVenta(Proforma_Header):
    class Meta:
        verbose_name = 'Nota Venta'
        ordering = ["-id","-proforma_created_on","-nota_venta_created_on"]
        proxy = True

    def __str__(self) -> str:
        prefijo = 'Nota Veta'
        return f'{prefijo} {self.id}'

        

admin.site.register(NotaVenta, NotaVentaAdmin)
