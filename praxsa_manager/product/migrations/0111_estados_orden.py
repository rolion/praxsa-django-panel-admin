import logging
from decimal import Decimal

from django.db import migrations, models
from django.utils import timezone

logger = logging.getLogger('django_admin')

# Vocabulario duplicado a proposito (como hizo 0106): una migracion no debe
# importar codigo de la app, que puede cambiar despues.
NT_EN_PROCESO, NT_TERMINADO, NT_CANCELADA = 'en_proceso', 'terminado', 'cancelada'
NV_POR_COBRAR, NV_PAGADA, NV_ANULADA = 'por_cobrar', 'pagada', 'anulada'


def _estado_global(nota, nota_venta):
    if nota is None or nota.status == NT_CANCELADA:
        return 'proforma'
    if nota.status == NT_EN_PROCESO:
        return 'en_trabajo'
    if nota_venta is not None and nota_venta.status == NV_PAGADA:
        return 'finalizado'
    return 'por_cobrar'


def _flush_deferred_constraints(schema_editor):
    """Postgres no deja ALTERAR una tabla con eventos de trigger (FK diferidas)
    pendientes de las filas que este mismo RunPython inserto o borro dentro de la
    misma transaccion ("pending trigger events"): se validan ahora."""
    if schema_editor is not None and schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute('SET CONSTRAINTS ALL IMMEDIATE')


def backfill_estados(apps, schema_editor):
    """ADR-estados-...-maquina-de-estados, decision 4.

    - Nota de trabajo con nota de venta -> 'terminado' (en el modelo anterior la
      nota de venta solo se creaba al terminar); la nota de venta queda 'pagada'
      si tiene pago, si no 'por_cobrar'.
    - Nota de trabajo sin nota de venta y con la proforma abierta (is_close=False:
      "abrir proforma" ya devolvio el inventario) -> 'cancelada'.
    - Nota de trabajo sin nota de venta y con la proforma cerrada -> 'en_proceso'
      y se le crea una nota de venta 'por_cobrar'.
    - Nota de trabajo sin proforma: se omite (no hay total que calcular) y se loguea.
    - Se recalcula Proforma_Header.status y los is_close legados."""
    Nota_trabajo = apps.get_model('product', 'Nota_trabajo')
    Nota_Venta = apps.get_model('product', 'Nota_Venta')
    Pago = apps.get_model('product', 'pago')
    Proforma_Header = apps.get_model('product', 'Proforma_Header')

    omitidas = 0
    for nota in Nota_trabajo.objects.all().iterator():
        nota_venta = Nota_Venta.objects.filter(nota_trabajo=nota).first()
        if nota_venta is not None:
            nota.status = NT_TERMINADO
            nota_venta.status = NV_PAGADA if Pago.objects.filter(nota_venta=nota_venta).exists() else NV_POR_COBRAR
        elif nota.proforma_id is None:
            omitidas += 1
            logger.warning(f'0111_estados_orden: Nota_trabajo {nota.pk} sin proforma; se omite (no se crea nota de venta).')
            continue
        else:
            proforma = Proforma_Header.objects.get(pk=nota.proforma_id)
            if not proforma.is_close:
                nota.status = NT_CANCELADA
            else:
                nota.status = NT_EN_PROCESO
                nota_venta = Nota_Venta(
                    nota_trabajo=nota,
                    name=proforma.name,
                    ci_nit=proforma.ci_nit,
                    total_price=Decimal(proforma.total_price) - Decimal(proforma.discount),
                    created_by_id=nota.responsable_id or proforma.created_by_id,
                    created_on=timezone.now(),
                    status=NV_POR_COBRAR,
                )
        nota.is_close = nota.status != NT_EN_PROCESO
        nota.save(update_fields=['status', 'is_close'])
        if nota_venta is not None:
            nota_venta.is_close = nota_venta.status != NV_POR_COBRAR
            nota_venta.save()

    for proforma in Proforma_Header.objects.all().iterator():
        nota = Nota_trabajo.objects.filter(proforma=proforma).first()
        nota_venta = Nota_Venta.objects.filter(nota_trabajo=nota).first() if nota is not None else None
        status = _estado_global(nota, nota_venta)
        proforma.status = status
        proforma.is_close = status != 'proforma'
        proforma.save(update_fields=['status', 'is_close'])
    if omitidas:
        logger.warning(f'0111_estados_orden: {omitidas} nota(s) de trabajo omitida(s) por no tener proforma.')
    _flush_deferred_constraints(schema_editor)


def reverse_estados(apps, schema_editor):
    """Deja los datos como los esperaba el codigo anterior: elimina las notas de
    venta que solo existen en el modelo nuevo (las de una nota de trabajo que no
    esta 'terminado' y no tienen pago) y restaura el vocabulario de
    Proforma_Header.status (proforma / nota_trabajo / por_cobrar / finalizado)."""
    Nota_trabajo = apps.get_model('product', 'Nota_trabajo')
    Nota_Venta = apps.get_model('product', 'Nota_Venta')
    Pago = apps.get_model('product', 'pago')
    Proforma_Header = apps.get_model('product', 'Proforma_Header')

    for nota_venta in Nota_Venta.objects.all().iterator():
        nota = Nota_trabajo.objects.get(pk=nota_venta.nota_trabajo_id)
        if nota.status != NT_TERMINADO and not Pago.objects.filter(nota_venta=nota_venta).exists():
            nota_venta.delete()

    for proforma in Proforma_Header.objects.all().iterator():
        nota = Nota_trabajo.objects.filter(proforma=proforma).first()
        status = 'proforma'
        if nota is not None:
            status = 'nota_trabajo'
            nota_venta = Nota_Venta.objects.filter(nota_trabajo=nota).first()
            if nota_venta is not None:
                status = 'por_cobrar'
                if Pago.objects.filter(nota_venta=nota_venta).exists():
                    status = 'finalizado'
        proforma.status = status
        proforma.save(update_fields=['status'])
    _flush_deferred_constraints(schema_editor)


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0110_inventario_is_active'),
    ]

    operations = [
        migrations.AddField(
            model_name='nota_trabajo',
            name='status',
            field=models.CharField(choices=[('en_proceso', 'En proceso'), ('terminado', 'Terminado'), ('cancelada', 'Cancelada')], default='en_proceso', max_length=20, verbose_name='Estado'),
        ),
        migrations.AddField(
            model_name='nota_venta',
            name='status',
            field=models.CharField(choices=[('por_cobrar', 'Por cobrar'), ('pagada', 'Pagada'), ('anulada', 'Anulada')], default='por_cobrar', max_length=20, verbose_name='Estado'),
        ),
        migrations.AlterField(
            model_name='proforma_header',
            name='status',
            field=models.CharField(choices=[('proforma', 'Proforma'), ('en_trabajo', 'En trabajo'), ('por_cobrar', 'Por Cobrar'), ('finalizado', 'Finalizado'), ('anulada', 'Anulada')], default='proforma', max_length=20, verbose_name='Estado'),
        ),
        migrations.RunPython(backfill_estados, reverse_code=reverse_estados),
    ]
