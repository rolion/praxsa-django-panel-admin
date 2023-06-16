from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator, EmailValidator
from django.contrib.auth.models import User


class Car_Brand(models.Model):
    name = models.CharField( max_length=200)
    class Meta:
        ordering = ['name']
        verbose_name = 'Brand'
    def __str__(self):
        return self.name
    
class Car_Model(models.Model):
    car_brand_id = models.ForeignKey(Car_Brand, on_delete=models.DO_NOTHING, verbose_name="Brand")
    name = models.CharField(max_length=200)
    class Meta:
        ordering = ['car_brand_id']
        verbose_name = 'Model'
    def __str__(self):
        return self.name
    
class Car_Part(models.Model):
    name = models.CharField(max_length=200)
    class Meta:
        ordering = ['name']
        verbose_name = 'Car Part'
    def __str__(self):
        return self.name
    
class Car_Model_Part(models.Model):
    car_model_id =  models.ForeignKey(Car_Model, on_delete=models.DO_NOTHING, verbose_name="Model")
    car_part_id =  models.ForeignKey(Car_Part, on_delete=models.DO_NOTHING, null=True, verbose_name="Car Part")
    width = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    length = models.DecimalField(max_digits=10, decimal_places=2,  default=0)
    quantity = models.PositiveIntegerField(default=1)
    installation_price = models.DecimalField(max_digits=10,decimal_places=2, default=0)
    class Meta:
        verbose_name = 'Car Model Part'
        
    def __str__(self):
        return f'{self.car_part_id.name} - {self.car_model_id.name}'
    
class Window_Film(models.Model):
    name = models.CharField(max_length=200)
    description= models.TextField()
    class Meta:
        ordering = ['name']
        verbose_name = 'Window Film'
    def __str__(self):
        return self.name
    
class Window_Film_Reel(models.Model):
    window_film_id = models.ForeignKey(Window_Film, on_delete=models.DO_NOTHING, verbose_name="Window Film")
    width = models.DecimalField(max_digits=10, decimal_places=2)
    length = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    class Meta:
        ordering = ['window_film_id']
        verbose_name = 'Window Film Reel'
        
    def __str__(self):
        return self.window_film_id.name
    
class Window_Film_Reel_Storage(models.Model):
    window_film_reel_id = models.ForeignKey(Window_Film_Reel, on_delete=models.DO_NOTHING, verbose_name="Window Film Reel")
    total_length= models.PositiveIntegerField(verbose_name="Total Length")
    class Meta:
        ordering = ['window_film_reel_id']
        verbose_name = 'Window Film Reel Storage'
    
class Client(models.Model):
    name = models.CharField(max_length=400)
    last_name = models.CharField(max_length=400, verbose_name="lastname")
    phone_number = models.CharField(validators=[RegexValidator('(\+)*\d{7,11}')], verbose_name="Phone Number")
    ci_nit = models.CharField(validators=[RegexValidator('\d*')], verbose_name="CI/NIT")
    user_id = models.ForeignKey(User, on_delete=models.DO_NOTHING, verbose_name='User', null=True)
    def __str__(self):
        return f'{self.name} {self.last_name}'

class Sale_Header(models.Model):
    date = models.DateTimeField(verbose_name="Fecha")
    client_id = models.ForeignKey(Client, on_delete=models.DO_NOTHING, verbose_name="Cliente")
    name = models.CharField(max_length=400, default=" ", null=False, verbose_name="Nombre Completo")
    email = models.CharField(validators=[EmailValidator()], null=True,verbose_name="Email")
    ci_nit = models.CharField(validators=[RegexValidator('\d*')],null=True, verbose_name="CI/NIT")
    car_plate = models.CharField(max_length=10, default="", null=True, verbose_name="Placa Auto")
    phone_number = models.CharField(validators=[RegexValidator('(\+)*\d{7,11}')], default="", verbose_name="Numero Telefónico")
    car_model_id = models.ForeignKey(Car_Model, on_delete=models.DO_NOTHING, verbose_name="Modelo")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Total Pagar")
    class Meta:
        verbose_name = 'Proforma'
    
    
class Sale_Detail(models.Model):
    sales_header_id = models.ForeignKey(Sale_Header, related_name='items', on_delete=models.DO_NOTHING, verbose_name="Proforma")
    car_part_id = models.ForeignKey(Car_Part, on_delete=models.DO_NOTHING, null=True, verbose_name="Parte Auto")
    width = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Ancho" )
    length = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Largo")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Precio")
    installation_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Costo Instalación")
    window_film_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Costo Lámina")
    quantity = models.PositiveIntegerField(default=0, verbose_name="Cantidad")
    window_film_id = models.ForeignKey(Window_Film, on_delete=models.DO_NOTHING, verbose_name="Lámina", null=True)
    class Meta:
        verbose_name = 'Detalle Venta'
    