
class Proforma_Helper:

    def __init__(self):
        self.origin_portal = 'port'
        self.origen_calculadora = 'cal'
        # Estados del pipeline proforma->instalacion->venta->pago (TASK-009/ADR-006),
        # calculados por Proforma_Business.refresh_status con la misma logica que
        # ProformaAdmin.get_estado (admin_config/proforma_admin.py).
        self.estado_proforma = 'proforma'
        self.estado_nota_trabajo = 'nota_trabajo'
        self.estado_por_cobrar = 'por_cobrar'
        self.estado_finalizado = 'finalizado'
        self.status = [
            (self.estado_proforma, 'Proforma'),
            (self.estado_nota_trabajo, 'Nota Trabajo'),
            (self.estado_por_cobrar, 'Por Cobrar'),
            (self.estado_finalizado, 'Finalizado'),
        ]
        self.origen = [(self.origen_calculadora, 'Calculadora'), (self.origin_portal, 'Portal')]
        self.default_status = self.estado_proforma
        self.tipo_venta_instalacion = 'venta_instalacion'
        self.tipo_venta_metro_lineal = 'venta_metro_lineal'
        self.tipo_venta = [(self.tipo_venta_instalacion, 'Venta con Instalación'), (self.tipo_venta_metro_lineal, 'Venta Metro Lineal')]



        