class Proforma_Helper:

    
    def __init__(self):
        self.req = 'req'
        self.apr = 'apr'
        self.inst = 'inst'
        self.canc = 'can'
        self.status = [(self.req,'Requerido'), (self.apr,'Aprobado'), (self.inst,'Instalado'), (self.canc,'Cancelado')]
        self.default_status = self.req

        