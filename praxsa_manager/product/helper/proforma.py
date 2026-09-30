
class Proforma_Helper:

    def __init__(self):
        self.origin_portal = 'port'
        self.origen_calculadora = 'cal'
        # Estado GLOBAL de la orden (derivado de los estados de la nota de trabajo
        # y de la nota de venta; ver helper/estados.py y
        # Orden_Estado_Business.calcular_estado_orden). 'Finalizado' = trabajo
        # terminado y pagado.
        self.estado_proforma = 'proforma'
        self.estado_en_trabajo = 'en_trabajo'
        self.estado_por_cobrar = 'por_cobrar'
        self.estado_finalizado = 'finalizado'
        self.estado_anulada = 'anulada'
        self.status = [
            (self.estado_proforma, 'Proforma'),
            (self.estado_en_trabajo, 'En trabajo'),
            (self.estado_por_cobrar, 'Por Cobrar'),
            (self.estado_finalizado, 'Finalizado'),
            (self.estado_anulada, 'Anulada'),
        ]
        self.origen = [(self.origen_calculadora, 'Calculadora'), (self.origin_portal, 'Portal')]
        self.default_status = self.estado_proforma
        self.tipo_venta_instalacion = 'venta_instalacion'
        self.tipo_venta_metro_lineal = 'venta_metro_lineal'
        self.tipo_venta = [(self.tipo_venta_instalacion, 'Venta con Instalación'), (self.tipo_venta_metro_lineal, 'Venta Metro Lineal')]



        