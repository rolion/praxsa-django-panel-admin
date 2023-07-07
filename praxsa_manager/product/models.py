from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator, EmailValidator
from django.contrib.auth.models import User


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
    class Meta:
        ordering = ['name']
        verbose_name = 'Lamina'
    def __str__(self):
        return self.name
    
class Window_Film_Reel(models.Model):
    window_film_id = models.ForeignKey(Window_Film, on_delete=models.DO_NOTHING, verbose_name="Lamina")
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

class Sale_Header(models.Model):
    req = 'req'
    apr = 'apr'
    inst = 'ins'
    canc = 'can'
    status = [
        (req,'Requerido'), (apr,'Aprobado'), (inst,'Instalado'), (canc,'Cancelado')]
    sales_status = models.CharField(choices=status, default="Requerido", verbose_name='Estado')
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
    car_part_id = models.ForeignKey(Car_Part, on_delete=models.DO_NOTHING, null=True, verbose_name="Item")
    width = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Ancho" )
    length = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Largo")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Precio")
    installation_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Costo Instalación")
    window_film_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Costo Lámina")
    quantity = models.PositiveIntegerField(default=0, verbose_name="Cantidad")
    window_film_id = models.ForeignKey(Window_Film, on_delete=models.DO_NOTHING, verbose_name="Lámina", null=True)
    sub_total = models.DecimalField(max_digits=10, decimal_places=2, default=0,verbose_name="Sub Total")
    class Meta:
        verbose_name = 'Detalle Venta'
    