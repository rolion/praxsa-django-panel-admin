class ProformaException(Exception):
    def __init__(self, message="Hay un problema con la proforma"):
        self.message = message
        super().__init__(self.message)

class NotaVentaException(Exception):
    def __init__(self, message="Hay un problema con la nota venta"):
        self.message = message
        super().__init__(self.message)

class OrdenTrabajo(Exception):
    def __init__(self, message="Hay un problema con la orden de trabajo"):
        self.message = message
        super().__init__(self.message)