
class Proforma_Helper:

    def __init__(self):
        self.req = 'req'
        self.apr = 'apr'
        self.inst = 'inst'
        self.canc = 'can'
        self.status = [(self.req,'Requerido'), (self.apr,'Aprobado'), (self.inst,'Instalado'), (self.canc,'Cancelado')]
        self.default_status = self.req
        self.tipo_venta_instalacion = 'venta_instalacion'
        self.tipo_venta_metro_lineal = 'venta_metro_lineal'
        self.tipo_venta = [(self.tipo_venta_instalacion, 'Venta con Instalación'), (self.tipo_venta_metro_lineal, 'Venta Metro Lineal')]



        