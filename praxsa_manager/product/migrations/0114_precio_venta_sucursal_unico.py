from django.db import migrations, models
from django.db.models import Count


def verificar_sin_duplicados(apps, schema_editor):
    """Aborta la migracion, sin modificar datos, si ya hay mas de un precio
    para la misma (sucursal, lamina, ancho). La limpieza es manual y previa
    (ADR-mejora-inventario-bobinas-regla-ancho-y-precio, decision 3)."""
    Precio = apps.get_model('product', 'precio_venta_sucursal')
    duplicados = (
        Precio.objects.values('sucursal_id', 'lamina_id', 'width')
        .annotate(total=Count('id'))
        .filter(total__gt=1)
        .order_by('sucursal_id', 'lamina_id', 'width')
    )
    if duplicados:
        detalle = '\n'.join(
            f"  sucursal={d['sucursal_id']} lamina={d['lamina_id']} ancho={d['width']}: {d['total']} precios"
            for d in duplicados
        )
        raise RuntimeError(
            'No se puede agregar la restriccion de precio unico por sucursal/lamina/ancho: '
            'hay precios duplicados en precio_venta_sucursal. Eliminar o unificar los duplicados y volver a migrar.\n'
            + detalle
        )


class Migration(migrations.Migration):
    """Un solo precio por (sucursal, lamina, ancho). Reversible: el reverso
    elimina la restriccion."""

    dependencies = [
        ('product', '0113_inventario_movimiento'),
    ]

    operations = [
        migrations.RunPython(verificar_sin_duplicados, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='precio_venta_sucursal',
            constraint=models.UniqueConstraint(fields=('sucursal', 'lamina', 'width'), name='unique_precio_sucursal_lamina_width'),
        ),
    ]
