
class Proforma_Helper:

    def __init__(self):
        self.prof = 'prof' #proforma
        self.nov = 'nove' # nota venta
        self.notra = 'ntra' # nota trabajo 
        self.origin_portal = 'port'
        self.origen_calculadora = 'cal'
        self.status = [(self.prof,'Proforma'), (self.notra,'Nota Trabajo'), (self.nov,'Nota Venta')]
        self.origen = [(self.origen_calculadora, 'Calculadora'), (self.origin_portal, 'Portal')]
        self.default_status = self.prof
        self.tipo_venta_instalacion = 'venta_instalacion'
        self.tipo_venta_metro_lineal = 'venta_metro_lineal'
        self.tipo_venta = [(self.tipo_venta_instalacion, 'Venta con Instalación'), (self.tipo_venta_metro_lineal, 'Venta Metro Lineal')]



        