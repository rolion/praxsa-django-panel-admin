"""Servicio unico de transiciones de la orden (Proforma / Nota de Trabajo /
Nota de Venta / Pago). Ver ADR-estados-proforma-nota-trabajo-nota-venta-maquina-de-estados.

Es el UNICO lugar que escribe estados. Cada transicion abre una transaccion,
bloquea la proforma (select_for_update), valida contra la tabla de
helper/estados.py y recalcula el estado global de Proforma_Header. Las
transiciones invalidas lanzan OrdenEstadoException (la API responde 409)."""
import logging
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from ..helper import estados
from ..helper.proforma import Proforma_Helper
from ..models import Nota_trabajo, Nota_Venta, Proforma_Detail, Proforma_Header, pago
from ..utils.exception.nohaylaminas import NoHayLaminasDisponibles
from ..utils.exception.proforma import OrdenEstadoException, ProformaException
from .inventario import Inventario_Business
from .orden_trabajo import Orden_Trabajo_Business

_NT_LABELS = dict(estados.NT_STATUS_CHOICES)
_NV_LABELS = dict(estados.NV_STATUS_CHOICES)


class Orden_Estado_Business:

    def __init__(self) -> None:
        self.helper = Proforma_Helper()
        self.inv_business = Inventario_Business()
        self.orden_trabajo_business = Orden_Trabajo_Business()
        self.log_errors = logging.getLogger('django_admin')

    # ------------------------------------------------------------------ estado global
    def calcular_estado_orden(self, proforma):
        """Estado global de la orden, derivado de los estados de la nota de
        trabajo y de la nota de venta. La anulacion de una proforma sin nota de
        trabajo vigente no se puede derivar: se conserva."""
        if proforma.status == self.helper.estado_anulada:
            return self.helper.estado_anulada
        nota = Nota_trabajo.objects.filter(proforma=proforma).first()
        if nota is None or nota.status == estados.NT_CANCELADA:
            return self.helper.estado_proforma
        if nota.status == estados.NT_EN_PROCESO:
            return self.helper.estado_en_trabajo
        nota_venta = Nota_Venta.objects.filter(nota_trabajo=nota).first()
        if nota_venta is not None and nota_venta.status == estados.NV_PAGADA:
            return self.helper.estado_finalizado
        return self.helper.estado_por_cobrar

    def refrescar(self, proforma):
        """Persiste el estado global (y el is_close legado de la proforma).
        update_fields para no tocar proforma_created_on (auto_now)."""
        proforma.status = self.calcular_estado_orden(proforma)
        proforma.is_close = proforma.status != self.helper.estado_proforma
        proforma.save(update_fields=['status', 'is_close'])
        return proforma

    # ------------------------------------------------------------------ utilidades
    def _bloquear(self, proforma):
        if proforma is None:
            raise OrdenEstadoException('La nota de trabajo no tiene una proforma asociada.')
        Proforma_Header.objects.select_for_update().get(pk=proforma.pk)
        proforma.refresh_from_db()
        return proforma

    def _validar(self, documento, desde, hasta, mensaje=None):
        if not estados.transicion_permitida(documento, desde, hasta):
            labels = _NT_LABELS if documento == estados.DOC_NOTA_TRABAJO else _NV_LABELS
            nombre = 'nota de trabajo' if documento == estados.DOC_NOTA_TRABAJO else 'nota de venta'
            raise OrdenEstadoException(
                mensaje or f'No se puede pasar la {nombre} de "{labels.get(desde, desde)}" a "{labels.get(hasta, hasta)}".'
            )

    def _sincronizar_legado(self, nota=None, nota_venta=None):
        """is_close es un campo legado derivado del estado (ADR, decision 1)."""
        if nota is not None:
            nota.is_close = nota.status != estados.NT_EN_PROCESO
        if nota_venta is not None:
            nota_venta.is_close = nota_venta.status != estados.NV_POR_COBRAR

    # ------------------------------------------------------------------ aprobar
    @transaction.atomic
    def aprobar_proforma(self, proforma, responsable):
        """Proforma -> orden: descuenta inventario, crea (o reutiliza) la nota de
        trabajo 'en_proceso' y la nota de venta 'por_cobrar' con el total congelado."""
        self._bloquear(proforma)
        if proforma.status != self.helper.estado_proforma:
            raise OrdenEstadoException(
                f'La proforma {proforma.id} ya fue aprobada o está anulada; no se puede generar la nota de trabajo.'
            )
        try:
            with transaction.atomic():
                detalles = Proforma_Detail.objects.select_related('proforma_header', 'window_film', 'proforma_header__sucursal')
                detalles = detalles.filter(proforma_header=proforma)
                sumary = []
                if detalles.exists():
                    if proforma.sales_type == self.helper.tipo_venta_instalacion:
                        # Import diferido: proforma.py importa este modulo.
                        from .proforma import Proforma_Business
                        Proforma_Business().validate_proforma_detail(detalles)
                    for detalle in list(detalles):
                        to_reduce = detalle.length
                        to_reduce = to_reduce * Decimal(detalle.quantity) if detalle.quantity > 0 else to_reduce
                        inventario = self.inv_business.reduce_inventory(
                            sucursal=detalle.proforma_header.sucursal,
                            windows_film=detalle.window_film,
                            width=detalle.width,
                            length_to_reduce=to_reduce,
                        )
                        detalle.inventario = inventario
                        detalle.save()
                        item_index = next((i for i, item in enumerate(sumary)
                                           if item['window_film'] == detalle.window_film and item['width'] == inventario.bobina.width),
                                          None)
                        if item_index is not None:
                            sumary[item_index]['length'] = sumary[item_index]['length'] + to_reduce
                        else:
                            sumary.append({'window_film': detalle.window_film, 'width': inventario.bobina.width, 'length': to_reduce})
                nota = self.orden_trabajo_business.create_work_note(proforma=proforma, sumary=sumary, responsable=responsable)
                if nota is None:
                    raise ProformaException('No se pudo generar la nota de trabajo.')
                if nota.status == estados.NT_CANCELADA:
                    self._validar(estados.DOC_NOTA_TRABAJO, nota.status, estados.NT_EN_PROCESO)
                    nota.entrada_vehiculo = timezone.now()
                    nota.salida_vehiculo = None
                nota.status = estados.NT_EN_PROCESO
                nota.is_close = False
                nota.save()
                self._crear_o_reutilizar_nota_venta(nota, proforma, responsable)
                self.refrescar(proforma)
                return nota
        except IntegrityError:
            raise OrdenEstadoException(f'ya existe una nota de trabajo asignada a la Proforma {proforma.id}')
        except NoHayLaminasDisponibles as e:
            raise Exception(str(e))
        except (ProformaException, OrdenEstadoException):
            raise
        except Exception as e:
            self.log_errors.error(f'algo salio mal, contactar administrador {e}')
            raise Exception('algo salio mal, contactar administrador')

    def _crear_o_reutilizar_nota_venta(self, nota, proforma, user):
        total = Decimal(proforma.total_price) - Decimal(proforma.discount)
        nota_venta = Nota_Venta.objects.filter(nota_trabajo=nota).first()
        if nota_venta is None:
            nota_venta = Nota_Venta(nota_trabajo=nota)
        elif nota_venta.status != estados.NV_ANULADA:
            raise OrdenEstadoException(f'La nota de trabajo {nota.id} ya tiene una nota de venta vigente.')
        else:
            self._validar(estados.DOC_NOTA_VENTA, nota_venta.status, estados.NV_POR_COBRAR)
        nota_venta.name = proforma.name
        nota_venta.ci_nit = proforma.ci_nit
        nota_venta.total_price = total
        nota_venta.created_by = user
        nota_venta.created_on = timezone.now()
        nota_venta.status = estados.NV_POR_COBRAR
        self._sincronizar_legado(nota_venta=nota_venta)
        nota_venta.save()
        return nota_venta

    # ------------------------------------------------------------------ trabajo
    @transaction.atomic
    def terminar_trabajo(self, nota_trabajo):
        proforma = self._bloquear(nota_trabajo.proforma)
        nota_trabajo.refresh_from_db()
        self._validar(estados.DOC_NOTA_TRABAJO, nota_trabajo.status, estados.NT_TERMINADO,
                      'Solo se puede terminar una nota de trabajo En proceso.')
        if proforma.sales_type == self.helper.tipo_venta_instalacion:
            if nota_trabajo.codigo_garantia is None:
                raise OrdenEstadoException('Debe agregar el código de Garantía')
            if nota_trabajo.instaladar is None:
                raise OrdenEstadoException('Debe agregar un Instalador')
        nota_trabajo.status = estados.NT_TERMINADO
        if nota_trabajo.salida_vehiculo is None:
            nota_trabajo.salida_vehiculo = timezone.now()
        self._sincronizar_legado(nota=nota_trabajo)
        nota_trabajo.save()
        self.refrescar(proforma)
        return nota_trabajo

    @transaction.atomic
    def corregir_trabajo(self, nota_trabajo):
        proforma = self._bloquear(nota_trabajo.proforma)
        nota_trabajo.refresh_from_db()
        self._validar(estados.DOC_NOTA_TRABAJO, nota_trabajo.status, estados.NT_EN_PROCESO,
                      'Solo se puede corregir una nota de trabajo Terminada.')
        nota_venta = Nota_Venta.objects.filter(nota_trabajo=nota_trabajo).first()
        if nota_venta is not None and nota_venta.status != estados.NV_POR_COBRAR:
            raise OrdenEstadoException('La nota de venta ya está pagada; anule el pago antes de corregir el trabajo.')
        nota_trabajo.status = estados.NT_EN_PROCESO
        self._sincronizar_legado(nota=nota_trabajo)
        nota_trabajo.save()
        self.refrescar(proforma)
        return nota_trabajo

    # ------------------------------------------------------------------ anulaciones de la orden
    def _cancelar_orden(self, nota_trabajo):
        """Anular la nota de trabajo == anular la nota de venta == reabrir la
        proforma: NT 'cancelada', NV 'anulada', inventario devuelto, proforma
        vuelve a 'proforma'. Solo con NT en_proceso y NV por_cobrar."""
        proforma = self._bloquear(nota_trabajo.proforma)
        nota_trabajo.refresh_from_db()
        if nota_trabajo.status == estados.NT_TERMINADO:
            raise OrdenEstadoException('El trabajo ya está terminado; corrija el trabajo antes de anular.')
        self._validar(estados.DOC_NOTA_TRABAJO, nota_trabajo.status, estados.NT_CANCELADA,
                      'Solo se puede anular una nota de trabajo En proceso.')
        nota_venta = Nota_Venta.objects.filter(nota_trabajo=nota_trabajo).first()
        if nota_venta is not None and nota_venta.status != estados.NV_POR_COBRAR:
            raise OrdenEstadoException('La nota de venta ya no está por cobrar; anule el pago primero.')
        for detalle in Proforma_Detail.objects.filter(proforma_header=proforma).select_related('inventario'):
            if detalle.inventario_id is None:
                continue
            to_add = detalle.length
            to_add = to_add * Decimal(detalle.quantity) if detalle.quantity > 0 else to_add
            if self.inv_business.return_to_inventory(detail_inventory=detalle.inventario, length_to_add=to_add) is not True:
                raise OrdenEstadoException('No se pudo devolver el inventario; la orden no se anuló.')
            detalle.inventario = None
            detalle.save(update_fields=['inventario'])
        nota_trabajo.status = estados.NT_CANCELADA
        self._sincronizar_legado(nota=nota_trabajo)
        nota_trabajo.save()
        if nota_venta is not None:
            self._validar(estados.DOC_NOTA_VENTA, nota_venta.status, estados.NV_ANULADA)
            nota_venta.status = estados.NV_ANULADA
            self._sincronizar_legado(nota_venta=nota_venta)
            nota_venta.save()
        self.refrescar(proforma)
        return nota_trabajo

    @transaction.atomic
    def anular_nota_trabajo(self, nota_trabajo):
        return self._cancelar_orden(nota_trabajo)

    @transaction.atomic
    def anular_nota_venta(self, nota_venta):
        nota_venta.refresh_from_db()
        if nota_venta.status == estados.NV_PAGADA:
            raise OrdenEstadoException('La nota de venta está pagada; anule el pago antes de anularla.')
        if nota_venta.status != estados.NV_POR_COBRAR:
            raise OrdenEstadoException('Solo se puede anular una nota de venta Por cobrar.')
        return self._cancelar_orden(nota_venta.nota_trabajo)

    @transaction.atomic
    def anular_proforma(self, proforma):
        self._bloquear(proforma)
        if proforma.status != self.helper.estado_proforma:
            raise OrdenEstadoException('Solo se puede anular una proforma vigente (sin nota de trabajo activa).')
        proforma.status = self.helper.estado_anulada
        proforma.is_close = True
        proforma.save(update_fields=['status', 'is_close'])
        return proforma

    # ------------------------------------------------------------------ cobro
    @transaction.atomic
    def registrar_pago_instancia(self, pago_obj, user):
        """Registra el pago de un objeto `pago` aun sin guardar (lo usa tambien
        Django Admin). El monto lo fija SIEMPRE el servidor."""
        nota_venta = pago_obj.nota_venta
        nota_trabajo = Nota_trabajo.objects.get(pk=nota_venta.nota_trabajo_id)
        self._bloquear(nota_trabajo.proforma)
        nota_venta.refresh_from_db()
        nota_trabajo.refresh_from_db()
        self._validar(estados.DOC_NOTA_VENTA, nota_venta.status, estados.NV_PAGADA,
                      'La nota de venta no está Por cobrar.')
        if nota_trabajo.status != estados.NT_TERMINADO:
            raise OrdenEstadoException('El trabajo aún no está terminado; no se puede registrar el pago.')
        if pago.objects.filter(nota_venta=nota_venta).exists():
            raise OrdenEstadoException('La nota de venta ya tiene un pago registrado.')
        pago_obj.monto = nota_venta.total_price
        pago_obj.cerrado = False
        pago_obj.created_by = user
        try:
            with transaction.atomic():
                pago_obj.save()
        except IntegrityError:
            raise OrdenEstadoException('El registro contable ya está en uso.')
        nota_venta.status = estados.NV_PAGADA
        self._sincronizar_legado(nota_venta=nota_venta)
        nota_venta.save()
        self.refrescar(nota_trabajo.proforma)
        return pago_obj

    def registrar_pago(self, nota_venta, user, tipo_pago, registro_contable=None):
        nuevo = pago(nota_venta=nota_venta, tipo_pago=tipo_pago, registro_contable=registro_contable or None)
        return self.registrar_pago_instancia(nuevo, user)

    @transaction.atomic
    def anular_pago(self, pago_obj):
        nota_venta = pago_obj.nota_venta
        nota_trabajo = Nota_trabajo.objects.get(pk=nota_venta.nota_trabajo_id)
        proforma = self._bloquear(nota_trabajo.proforma)
        pago_obj.refresh_from_db()
        if pago_obj.cerrado:
            raise OrdenEstadoException('El pago está cerrado contablemente y no se puede anular.')
        nota_venta.refresh_from_db()
        self._validar(estados.DOC_NOTA_VENTA, nota_venta.status, estados.NV_POR_COBRAR,
                      'La nota de venta no está pagada.')
        self.log_errors.info(f'anular_pago: pago {pago_obj.pk} de la nota de venta {nota_venta.pk} (monto {pago_obj.monto})')
        pago_obj.delete()
        nota_venta.status = estados.NV_POR_COBRAR
        self._sincronizar_legado(nota_venta=nota_venta)
        nota_venta.save()
        self.refrescar(proforma)
        return nota_venta

    @transaction.atomic
    def cerrar_pago(self, pago_obj):
        """Cierre contable: solo el flag; no cambia ningun estado."""
        pago_obj.cerrado = True
        pago_obj.save(update_fields=['cerrado'])
        return pago_obj
