from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator, EmailValidator
from django.contrib.auth.models import User
from tinymce.models import HTMLField
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .helper.proforma import Proforma_Helper


class Car_Brand(models.Model):
    name = models.CharField( max_length=200, verbose_name="Nombre")
    class Meta:
        ordering = ['name']
        verbose_name = 'Marca'
    def __str__(self):
        return self.name
    
class Car_Model(models.Model):
    car_brand_id = models.ForeignKey(Car_Brand, on_delete=models.DO_NOTHING, verbose_name="Marca")
    name = models.CharField(max_length=200, verbose_name="Nombre")
    class Meta:
        ordering = ['car_brand_id']
        verbose_name = 'Modelo'
    def __str__(self):
        return self.name
    
class Car_Part(models.Model):
    name = models.CharField(max_length=200, verbose_name="Nombre")
    class Meta:
        ordering = ['name']
        verbose_name = 'Item'
    def __str__(self):
        return self.name
    
class Car_Model_Part(models.Model):
    car_model_id =  models.ForeignKey(Car_Model, on_delete=models.DO_NOTHING, verbose_name="Modelo")
    car_part_id =  models.ForeignKey(Car_Part, on_delete=models.DO_NOTHING, null=True, verbose_name="Item")
    width = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Ancho")
    length = models.DecimalField(max_digits=10, decimal_places=2,  default=0, verbose_name="Largo")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Cantidad")
    installation_price = models.DecimalField(max_digits=10,decimal_places=2, default=0, verbose_name="Precio Instalación")
    class Meta:
        verbose_name = 'Modelo Item'
        
    def __str__(self):
        return f'{self.car_part_id.name} - {self.car_model_id.name}'
    
class Window_Film(models.Model):
    name = models.CharField(max_length=200, verbose_name="Nombre")
    description= models.TextField()
    content = HTMLField(null=True)
    class Meta:
        ordering = ['name']
        verbose_name = 'Lamina'
    def __str__(self):
        return self.name
    
class Window_Film_Reel(models.Model):
    window_film_id = models.ForeignKey(Window_Film,
                                       related_name="bobina_lamina",
                                       on_delete=models.DO_NOTHING, 
                                       verbose_name="Lamina")
    width = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Ancho")
    length = models.DecimalField(max_digits=10, decimal_places=2,  verbose_name="Largo")
    price = models.DecimalField(max_digits=10, decimal_places=2,  verbose_name="Precio")
    quantity = models.PositiveIntegerField(verbose_name="Cantidad")
    class Meta:
        ordering = ['window_film_id']
        verbose_name = 'Bobina'
        
    def __str__(self):
        return self.window_film_id.name
    
class Window_Film_Reel_Storage(models.Model):
    window_film_reel_id = models.ForeignKey(Window_Film_Reel, on_delete=models.DO_NOTHING, verbose_name="Bobina")
    total_length= models.PositiveIntegerField(verbose_name="Largo Total")
    class Meta:
        ordering = ['window_film_reel_id']
        verbose_name = 'Almacen Bobina'
    
class Client(models.Model):
    name = models.CharField(max_length=400)
    last_name = models.CharField(max_length=400, verbose_name="lastname")
    phone_number = models.CharField(validators=[RegexValidator('(\+)*\d{7,11}')], verbose_name="Numero Telefónico")
    ci_nit = models.CharField(validators=[RegexValidator('\d*')], verbose_name="CI/NIT")
    user_id = models.ForeignKey(User, on_delete=models.DO_NOTHING, verbose_name='Usuario', null=True)
    class Meta: 
        verbose_name = 'Cliente'
        ordering = ['last_name', 'name']
    def __str__(self):
        return f'{self.name} {self.last_name}'
    
class Sucursal(models.Model):
    name = models.CharField(max_length=20, default=" ", null=False, verbose_name="Nombre")
    address = models.CharField(max_length=400, default=" ", null=False, verbose_name="direccion")
    enable_to_install_windows_film = models.BooleanField(default=True, verbose_name="Habilitado")
    empleado = models.ManyToManyField(User, verbose_name='Empleados')
    # administrador = models.ManyToManyField(User, verbose_name='Admin Sucursal')
    def __str__(self):
        return f'{self.name}'

class inventario(models.Model):
    sucursal = models.ForeignKey(Sucursal, on_delete=models.DO_NOTHING, verbose_name="Sucursal",related_name="sucursal_inventario")
    bobina = models.ForeignKey(Window_Film_Reel, on_delete=models.DO_NOTHING, verbose_name="Bobina", related_name="bobina_inventario")
    quantity = models.PositiveIntegerField(verbose_name="Cantidad")
    to_install = models.DecimalField(max_digits=10, decimal_places=2, default=0.0, verbose_name="metros disponible para instalar")
    installed = models.DecimalField(max_digits=10, decimal_places=2, default=0.0,  verbose_name="metros instalados")
    date = models.DateTimeField(verbose_name="Fecha", auto_now=True)
    precio_compra_mtr_lineal = models.DecimalField( max_digits=10, decimal_places=2, default=0.0, verbose_name="Precio Compra Metro Lineal")
    precio_venta_mtr_lineal = models.DecimalField( max_digits=10, decimal_places=2, default=0.0, verbose_name="Precio Venta Metro Lineal")
    def __str__(self):
        return f'{self.sucursal.name}-{self.bobina.window_film_id} '


# class instalador_sucursal(models.Model):
#     sucursal_id = models.ForeignKey(Sucursal, on_delete=models.DO_NOTHING, verbose_name="Sucursal")
#     instalador = models.ForeignKey(User, on_delete=models.DO_NOTHING, verbose_name="Instalador")

class Sale_Header(models.Model):
    helper = Proforma_Helper()
    sales_status = models.CharField(choices=helper.status, default=helper.default_status, verbose_name='Estado')
    sales_type = models.CharField(choices=helper.tipo_venta, default=helper.tipo_venta_instalacion, verbose_name='Tipo Venta')
    date = models.DateTimeField(verbose_name="Fecha")
    client_id = models.ForeignKey(Client, on_delete=models.DO_NOTHING, verbose_name="Cliente")
    name = models.CharField(max_length=400, default=" ", null=False, verbose_name="Nombre Completo")
    sucursal = models.ForeignKey(Sucursal, on_delete=models.DO_NOTHING,blank=True, null=True, verbose_name="Sucursal")
    email = models.CharField(validators=[EmailValidator()], null=True,verbose_name="Email")
    ci_nit = models.CharField(validators=[RegexValidator('\d*')],null=True, verbose_name="CI/NIT")
    codigo_garantia = models.CharField(null=True, blank=True, verbose_name="Codigo Garantia", max_length=12, unique=True)
    car_plate = models.CharField(max_length=10, default="", null=True, verbose_name="Placa Auto")
    phone_number = models.CharField(validators=[RegexValidator('(\+)*\d{7,11}')], default="", verbose_name="Numero Telefónico")
    car_model_id = models.ForeignKey(Car_Model, on_delete=models.DO_NOTHING, verbose_name="Modelo")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Total Pagar")
    is_delete = models.BooleanField(default=False)
    def clean(self):
        if self.sales_status == self.helper.inst and self.codigo_garantia is None:
            raise ValidationError({"codigo_garantia": _("porfavor agregue el codigo de garantia")})
    
    class Meta:
        verbose_name = 'Proforma'

    def __str__(self) -> str:
        return f'Proforma {self.id}'
    
    
class Sale_Detail(models.Model):
    sales_header_id = models.ForeignKey(Sale_Header, related_name='items', on_delete=models.DO_NOTHING, verbose_name="Proforma")
    car_part_id = models.ForeignKey(Car_Part, on_delete=models.DO_NOTHING, blank=True, null=True, verbose_name="Item")
    width = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Ancho" )
    length = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Largo")
    sub_total = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Sub Total")
    installation_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Costo Instalación")
    window_film_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Costo Lámina")
    quantity = models.PositiveIntegerField(default=0, verbose_name="Cantidad")
    window_film_id = models.ForeignKey(Window_Film, on_delete=models.DO_NOTHING, verbose_name="Lámina", null=True)
    
    class Meta:
        verbose_name = 'Detalle Venta'
    
    def __str__(self) -> str:
        return f'Detalle Proforma {self.car_part_id}'

