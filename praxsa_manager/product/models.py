from django.db import models
from django.core.validators import RegexValidator, EmailValidator, MaxValueValidator, DecimalValidator, MinValueValidator
from django.contrib.auth.models import User
from tinymce.models import HTMLField
from django.utils.translation import gettext_lazy as _
from .helper.proforma import Proforma_Helper
from .helper.pagos import Pagos_Helper
import datetime
alphanumeric = RegexValidator(r'^[0-9a-zA-Z]*$', 'Solo se permiten letras y numeros')


class Car_Brand(models.Model):
    name = models.CharField( max_length=200, verbose_name="Nombre", unique=True)
    class Meta:
        ordering = ['name']
        verbose_name = 'Marca'
    def __str__(self):
        return self.name
    
class Car_Model(models.Model):
    car_brand_id = models.ForeignKey(Car_Brand, on_delete=models.DO_NOTHING, verbose_name="Marca")
    name = models.CharField(max_length=200, verbose_name="Nombre", unique=True)
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
        constraints = [
            models.UniqueConstraint(fields=['car_model_id', 'car_part_id'], name='unique_model_item'),
        ]
        
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
    window_film = models.ForeignKey(Window_Film,
                                       related_name="bobina_lamina",
                                       on_delete=models.DO_NOTHING, 
                                       verbose_name="Lamina")
    width = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Ancho")
    length = models.DecimalField(max_digits=10, decimal_places=2,  verbose_name="Largo")
    price = models.DecimalField(max_digits=10, decimal_places=2,  verbose_name="Precio")
    class Meta:
        ordering = ['window_film']
        verbose_name = 'Bobina'  
    
    def __str__(self):
        return f'{self.window_film.name} - {self.width}'
    
# class Window_Film_Reel_Storage(models.Model):
#     window_film_reel_id = models.ForeignKey(Window_Film_Reel, on_delete=models.DO_NOTHING, verbose_name="Bobina")
#     total_length= models.PositiveIntegerField(verbose_name="Largo Total")
#     class Meta:
#         ordering = ['window_film_reel_id']
#         verbose_name = 'Almacen Bobina'
    
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
    address = models.CharField(max_length=400, default=" ", null=False, verbose_name="Dirección")
    enable_to_install_windows_film = models.BooleanField(default=True, verbose_name="Habilitado")
    empleado = models.ManyToManyField(User, verbose_name='Empleados')
    # administrador = models.ManyToManyField(User, verbose_name='Admin Sucursal')
    def __str__(self):
        return f'{self.name}'
    
class instalador(models.Model):
    name = models.CharField(max_length=20, default=" ", null=False, verbose_name="Nombre")
    address = models.CharField(max_length=400, default=" ", null=False, verbose_name="Dirección")
    phonenumber = models.CharField(validators=[RegexValidator('(\+)*\d{7,11}')], verbose_name="Numero Telefónico")
    sucursal = models.ManyToManyField(Sucursal)
    def __str__(self):
        return self.name

class inventario(models.Model):
    sucursal = models.ForeignKey(Sucursal, on_delete=models.DO_NOTHING, verbose_name="Sucursal",related_name="sucursal_inventario")
    bobina = models.ForeignKey(Window_Film_Reel, on_delete=models.DO_NOTHING, verbose_name="Bobina", related_name="bobina_inventario")
    quantity = models.PositiveIntegerField(verbose_name="Cantidad")
    to_install = models.DecimalField(max_digits=10, decimal_places=2, default=0.0, verbose_name="metros disponible para instalar")
    installed = models.DecimalField(max_digits=10, decimal_places=2, default=0.0,  verbose_name="metros instalados")
    original_length = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Longitud Inicial")
    date = models.DateTimeField(verbose_name="Fecha", null=False)
    numero_referencia = models.PositiveIntegerField( verbose_name="Numero Referencia",default=0, validators=[MaxValueValidator(limit_value=9999999999, message='solo se aceptan valores con 10 digitos')])
    precio_compra_mtr_lineal = models.DecimalField( max_digits=10, decimal_places=2, default=0.0, verbose_name="Precio Compra Metro Lineal")
    precio_venta_mtr_lineal = models.DecimalField( max_digits=10, decimal_places=2, default=0.0, verbose_name="Precio Venta Metro Lineal")
    nro_lote = models.CharField(max_length=15,validators=[alphanumeric], null=True, verbose_name='Nro. Lote')
    def __str__(self):
        return f'{self.sucursal.name}-{self.bobina.window_film.name}'

class Proforma_Header(models.Model):
    helper = Proforma_Helper()
    sales_type = models.CharField(choices=helper.tipo_venta, default=helper.tipo_venta_instalacion, verbose_name='Tipo Venta')
    origen = models.CharField(choices=helper.origen, default=helper.origin_portal, verbose_name='Origen')
    proforma_created_on = models.DateTimeField(verbose_name="Fecha Proforma", auto_now=True)

    name = models.CharField(max_length=400, default=" ", null=False, verbose_name="Nombre Completo")
    email = models.CharField(validators=[EmailValidator()], null=True,verbose_name="Email")
    ci_nit = models.CharField(validators=[RegexValidator('\d*')],null=True, verbose_name="CI/NIT")
    car_plate = models.CharField(max_length=10, default="", blank=True, null=True, verbose_name="Placa Auto")
    phone_number = models.CharField(validators=[RegexValidator('(\+)*\d{7,11}')], default="", verbose_name="Numero Telefónico")
    sucursal = models.ForeignKey(Sucursal, on_delete=models.DO_NOTHING,blank=True, null=True, verbose_name="Sucursal")
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[DecimalValidator(max_digits=10, decimal_places=2), MinValueValidator(limit_value=0)],
                                   verbose_name="Descuento")
    discount_reason = models.TextField(verbose_name='Motivo Descuento', blank=True, null=True)
    car_model_id = models.ForeignKey(Car_Model, on_delete=models.DO_NOTHING, verbose_name="Modelo", blank=True, null=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Total Pagar")
    is_delete = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, verbose_name='Creado Por',on_delete=models.DO_NOTHING, null=False,related_name='proforma_created_by')
    is_close = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = 'Proforma'
        ordering = ["-id","-proforma_created_on",]

    def __str__(self) -> str:
        # prefijo = 'Proforma' if self.sales_status == self.helper.prof else 'Nota Venta'
        return f'Proforma {self.id}'
    
class Proxy_Proforma(Proforma_Header):
    class Meta:
        proxy = True
        verbose_name = 'Reporte Proforma'
        ordering = ["-id","-proforma_created_on"]
    
class Nota_trabajo(models.Model):
    proforma = models.OneToOneField(Proforma_Header, on_delete=models.DO_NOTHING, blank=True, null=True, verbose_name="Proforma")
    codigo_garantia = models.CharField(null=True, blank=True, verbose_name="Codigo Garantia", max_length=12, unique=True)
    entrada_vehiculo = models.DateTimeField(verbose_name="Entrada Vehiculo", null=True, blank=True)
    salida_vehiculo = models.DateTimeField(verbose_name="Salida Vehiculo", null=True, blank=True)
    observaciones = models.TextField(verbose_name='Observaciones', blank=True, null=True)
    instaladar = models.ForeignKey(instalador, verbose_name='Instalador',on_delete=models.DO_NOTHING, null=True, related_name='instalador_laminas_nota_trabajo')
    responsable = models.ForeignKey(User, verbose_name='Responsable',on_delete=models.DO_NOTHING, blank=True, null=True, related_name='responsable_proforma_nota_trabajo')
    name = models.CharField(max_length=400, default=" ", null=False, verbose_name="Nombre Completo")
    car_plate = models.CharField(max_length=10, default="", null=True, verbose_name="Placa Auto")
    car_model = models.ForeignKey(Car_Model, on_delete=models.DO_NOTHING, verbose_name="Modelo", null=True, blank=True)
    nota_venta_created_on = models.DateTimeField(verbose_name="Fecha Orden Trabajo",  auto_now_add=True)
    is_close = models.BooleanField(default=False) 
    def __str__(self) -> str:
        return f'Nota Trabajo {self.id }'

    class Meta:
        verbose_name = 'Nota Trabajo'
        ordering = ["-id","-nota_venta_created_on"]
        
class Detalle_Nota_Trabajo(models.Model):
    
    nota_trabajo = models.ForeignKey(Nota_trabajo, on_delete=models.DO_NOTHING, related_name='detalle_trabajo',verbose_name='Nota de trabajo')
    window_film = models.ForeignKey(Window_Film, on_delete=models.DO_NOTHING, related_name='detalle_trabajo',verbose_name="Lámina", null=True)
    # detalle_proforma = models.ForeignKey(Proforma_Detail, on_delete=models.DO_NOTHING, blank=True, null=True, verbose_name="Detalle")
    width = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Ancho" )
    length = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Largo")
    # quantity = models.PositiveIntegerField(default=0, verbose_name="Cantidad")
    
    # car_part = models.ForeignKey(Car_Part, on_delete=models.DO_NOTHING, blank=True, null=True, verbose_name="Item")
    
    class Meta:
        verbose_name = 'Resumen Trabajo'
    
    def __str__(self) -> str:
        return f'Resumen'

class Proxy_Nota_trabajo(Nota_trabajo):
    class Meta:
        proxy = True
        verbose_name = 'Reporte Nota Trabajo'
        ordering = ["-id","-nota_venta_created_on"]
        
    
    
class Proforma_Detail(models.Model):
    helper = Proforma_Helper()
    inventario = models.ForeignKey(inventario, related_name="lamina_inventario",null=True, on_delete=models.DO_NOTHING)
    proforma_header = models.ForeignKey(Proforma_Header, related_name='items', on_delete=models.DO_NOTHING, verbose_name="Proforma")
    window_film = models.ForeignKey(Window_Film, on_delete=models.DO_NOTHING, verbose_name="Lámina", null=True)
    car_part = models.ForeignKey(Car_Part, on_delete=models.DO_NOTHING, blank=True, null=True, verbose_name="Item")
    width = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Ancho" )
    length = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Largo")
    sub_total = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Sub Total")
    installation_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Costo Instalación")
    window_film_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Costo Lámina")
    quantity = models.PositiveIntegerField(default=0, verbose_name="Cantidad")
    
    class Meta:
        verbose_name = 'Detalle Venta'
    
    def __str__(self) -> str:
        return f'Detalle'
    

class Nota_Venta(models.Model):
    nota_trabajo = models.OneToOneField(Nota_trabajo, on_delete=models.DO_NOTHING, verbose_name="Nota de Trabajo")
    name = models.CharField(max_length=400, default=" ", null=False, verbose_name="Nombre Completo")
    ci_nit = models.CharField(validators=[RegexValidator('\d*')],null=True, verbose_name="CI/NIT")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Total Pagar")
    created_by = models.ForeignKey(User, verbose_name='Creado Por',
                                   on_delete=models.DO_NOTHING, 
                                   null=False, 
                                   related_name='nota_venta_created_by')
    created_on = models.DateTimeField(verbose_name="Creado en", null=True, blank=True)
    is_close = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Nota Venta'

    def __str__(self) -> str:
        return f'Nota Venta {self.nota_trabajo.proforma.id}'
    

    
class pago(models.Model):
    helper = Pagos_Helper()
    nota_venta = models.OneToOneField(Nota_Venta, 
                                      on_delete=models.DO_NOTHING, 
                                      verbose_name="Nota de Venta",
                                      blank=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2, default= 0)
    tipo_pago =models.CharField(choices=helper.types, 
                                default=helper.default_type, 
                                verbose_name='Tipo Pago')
    cerrado = models.BooleanField(default=False)
    created_on = models.DateTimeField(verbose_name="Fecha", auto_now_add=True)
    created_by = models.ForeignKey(User, 
                                   on_delete=models.DO_NOTHING, 
                                   verbose_name='Creado por')
    def __str__(self) -> str:
        return f'Pago {self.id}'
    
class Proxy_Pagos(pago):
    class Meta:
        proxy = True
        verbose_name = 'Reporte Ventas Diarias'
        ordering = ["-id","-created_on"]

