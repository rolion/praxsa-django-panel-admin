from ..models import pago, Proforma_Header, Nota_trabajo
from django.db import IntegrityError, transaction
class Pago_Business:

    @transaction.atomic
    def cerrar_pago(self,paiment: pago):
        try:
            with transaction.atomic():
                paiment.cerrado = True
                paiment.save()
                proforma = paiment.nota_venta.nota_trabajo.proforma
                proforma.is_paid = True
                proforma.save()
                nota_trabajo = proforma.nota_trabajo
                nota_trabajo.cerrada = True
                nota_trabajo.save()
        except Exception as e:
            print(str(e))
            raise Exception('algo salio mal, contacte al administrador')
            pass