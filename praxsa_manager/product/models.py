from django.db import models
from django.core.validators import RegexValidator, EmailValidator
from django.contrib.auth.models import User
from tinymce.models import HTMLField
from django.utils.translation import gettext_lazy as _
from .helper.proforma import Proforma_Helper
from .helper.pagos import Pagos_Helper


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
    window_film = models.ForeignKey(Window_Film,
                                       related_name="bobina_lamina",
                                       on_delete=models.DO_NOTHING, 
                                       verbose_name="Lamina")
    width = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Ancho")
    length = models.DecimalField(max_digits=10, decimal_places=2,  verbose_name="Largo")
    price = models.DecimalField(max_digits=10, decimal_places=2,  verbose_name="Precio")
    quantity = models.PositiveIntegerField(verbose_name="Cantidad")
    class Meta:
        ordering = ['window_film']
        verbose_name = 'Bobina'
        
    def __str__(self):
        return f'{self.window_film.name} - {self.width}'
    
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
    date = models.DateTimeField(verbose_name="Fecha", auto_now_add=True)
    precio_compra_mtr_lineal = models.DecimalField( max_digits=10, decimal_places=2, default=0.0, verbose_name="Precio Compra Metro Lineal")
    precio_venta_mtr_lineal = models.DecimalField( max_digits=10, decimal_places=2, default=0.0, verbose_name="Precio Venta Metro Lineal")
    def __str__(self):
        return f'{self.sucursal.name}-{self.bobina.window_film.name}'

class Proforma_Header(models.Model):
    helper = Proforma_Helper()
    sales_status = models.CharField(choices=helper.status, default=helper.default_status, verbose_name='Estado')
    sales_type = models.CharField(choices=helper.tipo_venta, default=helper.tipo_venta_instalacion, verbose_name='Tipo Venta')
    is_paid = models.BooleanField(default=False, verbose_name='Pagado')
    proforma_created_on = models.DateTimeField(verbose_name="Fecha Proforma", auto_now=True)
    nota_venta_created_on = models.DateTimeField(verbose_name="Fecha Nota Venta", null=True, blank=True)
    is_nota_venta_canceled = models.BooleanField(default=False)
    is_nota_venta_refund = models.BooleanField(default=False)
    name = models.CharField(max_length=400, default=" ", null=False, verbose_name="Nombre Completo")
    email = models.CharField(validators=[EmailValidator()], null=True,verbose_name="Email")
    ci_nit = models.CharField(validators=[RegexValidator('\d*')],null=True, verbose_name="CI/NIT")
    car_plate = models.CharField(max_length=10, default="", null=True, verbose_name="Placa Auto")
    phone_number = models.CharField(validators=[RegexValidator('(\+)*\d{7,11}')], default="", verbose_name="Numero Telefónico")
    sucursal = models.ForeignKey(Sucursal, on_delete=models.DO_NOTHING,blank=True, null=True, verbose_name="Sucursal")
    codigo_garantia = models.CharField(null=True, blank=True, verbose_name="Codigo Garantia", max_length=12, unique=True)
    car_model_id = models.ForeignKey(Car_Model, on_delete=models.DO_NOTHING, verbose_name="Modelo")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Total Pagar")
    is_delete = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, verbose_name='Creado Por',on_delete=models.DO_NOTHING, null=False, related_name='usuario_proforma')
    
    class Meta:
        verbose_name = 'Proforma'
        ordering = ["-id","-proforma_created_on","-nota_venta_created_on"]

    def __str__(self) -> str:
        prefijo = 'Proforma' if self.sales_status == self.helper.prof else 'Nota Venta'
        return f'{prefijo} {self.id}'
    
class Nota_trabajo(models.Model):
    proforma = models.OneToOneField(Proforma_Header, on_delete=models.DO_NOTHING, blank=True, null=True, verbose_name="Proforma")
    entrada_vehiculo = models.DateTimeField(verbose_name="Entrada Vehiculo", null=True, blank=True)
    salida_vehiculo = models.DateTimeField(verbose_name="Salida Vehiculo", null=True, blank=True)
    observaciones = models.TextField(verbose_name='Observaciones', blank=True, null=True)
    instaladar = models.ForeignKey(User, verbose_name='Instalador',on_delete=models.DO_NOTHING, null=True, related_name='instalador_laminas_nota_trabajo')
    responsable = models.ForeignKey(User, verbose_name='Responsable',on_delete=models.DO_NOTHING, blank=True, null=True, related_name='responsable_proforma_nota_trabajo')
    name = models.CharField(max_length=400, default=" ", null=False, verbose_name="Nombre Completo")
    car_plate = models.CharField(max_length=10, default="", null=True, verbose_name="Placa Auto")
    car_model = models.ForeignKey(Car_Model, on_delete=models.DO_NOTHING, verbose_name="Modelo", null=True, blank=True)
    nota_venta_created_on = models.DateTimeField(verbose_name="Fecha Orden Trabajo",  auto_now_add=True)
    cerrada = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f'Nota Trabajo {self.id}'

    class Meta:
        verbose_name = 'Nota Trabajo'
        ordering = ["-id","-nota_venta_created_on"]
    
    
class Proforma_Detail(models.Model):
    helper = Proforma_Helper()
    proforma_header = models.ForeignKey(Proforma_Header, related_name='items', on_delete=models.DO_NOTHING, verbose_name="Proforma")
    car_part = models.ForeignKey(Car_Part, on_delete=models.DO_NOTHING, blank=True, null=True, verbose_name="Item")
    width = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Ancho" )
    length = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Largo")
    sub_total = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Sub Total")
    installation_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Costo Instalación")
    window_film_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Costo Lámina")
    quantity = models.PositiveIntegerField(default=0, verbose_name="Cantidad")
    window_film = models.ForeignKey(Window_Film, on_delete=models.DO_NOTHING, verbose_name="Lámina", null=True)
    class Meta:
        verbose_name = 'Detalle Venta'
    
    def __str__(self) -> str:
        return f'Detalle'
    
class Detalle_Nota_Trabajo(models.Model):
    nota_trabajo = models.ForeignKey(Nota_trabajo, on_delete=models.DO_NOTHING, related_name='detalle_trabajo',verbose_name='Nota de trabajo')
    detalle_proforma = models.ForeignKey(Proforma_Detail, on_delete=models.DO_NOTHING, blank=True, null=True, verbose_name="Detalle")
    width = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Ancho" )
    length = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Largo")
    quantity = models.PositiveIntegerField(default=0, verbose_name="Cantidad")
    window_film = models.ForeignKey(Window_Film, on_delete=models.DO_NOTHING, verbose_name="Lámina", null=True)
    car_part = models.ForeignKey(Car_Part, on_delete=models.DO_NOTHING, blank=True, null=True, verbose_name="Item")

    def __str__(self) -> str:
        return f'Detalle'
    
class pago(models.Model):
    helper = Pagos_Helper()
    proforma = models.OneToOneField(Proforma_Header, on_delete=models.DO_NOTHING, verbose_name="Nota de Venta")
    tipo_pago =models.CharField(choices=helper.types, default=helper.default_type, verbose_name='Tipo Pago')
    cerrado = models.BooleanField(default=False)
    created_on = models.DateTimeField(verbose_name="Fecha", auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.DO_NOTHING, verbose_name='Creado por')
    def __str__(self) -> str:
        return f'Pago {self.id}'

