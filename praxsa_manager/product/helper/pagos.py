
class Pagos_Helper:

    def __init__(self):
        self.efec = 'efec'
        self.trans = 'trans'
        self.types = [(self.efec,'Efectivo'), (self.trans,'Targeta/QR')]
        self.default_type = self.efec