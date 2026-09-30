"""Estados y tabla de transiciones de la orden (Proforma -> Nota de Trabajo ->
Nota de Venta -> Pago). Ver ADR-estados-proforma-nota-trabajo-nota-venta-maquina-de-estados.

Solo Orden_Estado_Business (business/orden_estado.py) escribe estos estados."""

# Nota de trabajo
NT_EN_PROCESO = 'en_proceso'
NT_TERMINADO = 'terminado'
NT_CANCELADA = 'cancelada'
NT_STATUS_CHOICES = [
    (NT_EN_PROCESO, 'En proceso'),
    (NT_TERMINADO, 'Terminado'),
    (NT_CANCELADA, 'Cancelada'),
]

# Nota de venta
NV_POR_COBRAR = 'por_cobrar'
NV_PAGADA = 'pagada'
NV_ANULADA = 'anulada'
NV_STATUS_CHOICES = [
    (NV_POR_COBRAR, 'Por cobrar'),
    (NV_PAGADA, 'Pagada'),
    (NV_ANULADA, 'Anulada'),
]

DOC_NOTA_TRABAJO = 'nota_trabajo'
DOC_NOTA_VENTA = 'nota_venta'
DOC_PROFORMA = 'proforma'

# (documento, estado actual, estado destino) permitidos. El estado global de
# Proforma_Header.status (proforma/en_trabajo/por_cobrar/finalizado/anulada) se
# deriva, salvo la anulacion de una proforma sin nota de trabajo.
TRANSICIONES = {
    (DOC_NOTA_TRABAJO, NT_EN_PROCESO, NT_TERMINADO),
    (DOC_NOTA_TRABAJO, NT_TERMINADO, NT_EN_PROCESO),
    (DOC_NOTA_TRABAJO, NT_EN_PROCESO, NT_CANCELADA),
    (DOC_NOTA_TRABAJO, NT_CANCELADA, NT_EN_PROCESO),
    (DOC_NOTA_VENTA, NV_POR_COBRAR, NV_PAGADA),
    (DOC_NOTA_VENTA, NV_PAGADA, NV_POR_COBRAR),
    (DOC_NOTA_VENTA, NV_POR_COBRAR, NV_ANULADA),
    (DOC_NOTA_VENTA, NV_ANULADA, NV_POR_COBRAR),
}


def transicion_permitida(documento, desde, hasta):
    return (documento, desde, hasta) in TRANSICIONES
