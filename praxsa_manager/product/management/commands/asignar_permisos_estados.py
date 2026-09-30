"""Asigna a los grupos del negocio los permisos que usa el flujo de estados de
la orden (TASK-estados-proforma-nota-trabajo-nota-venta). Idempotente: solo
agrega lo que falta; no quita permisos ni crea grupos."""
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

# grupo -> permisos (codename del app `product`). Ver plan v2, matriz de permisos.
PERMISOS_POR_GRUPO = {
    'Admin': [
        'add_pago', 'delete_pago',
        'add_nota_trabajo', 'change_nota_trabajo', 'delete_nota_trabajo',
        'change_proforma_header', 'delete_proforma_header',
        'delete_nota_venta',
    ],
    'Caja': ['add_pago', 'delete_pago', 'delete_nota_venta'],
    'Vendedor': [
        'add_pago', 'delete_pago',
        'add_nota_trabajo',
        'change_proforma_header', 'delete_proforma_header',
        'delete_nota_venta',
    ],
    'Almacen': ['change_proforma_header', 'change_nota_trabajo', 'delete_nota_trabajo'],
}


class Command(BaseCommand):
    help = 'Asigna a los grupos Admin, Caja, Vendedor y Almacen los permisos del flujo de estados de la orden.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Muestra lo que se agregaria sin escribir.')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        plan = []
        grupos_faltantes = []
        for nombre, codenames in PERMISOS_POR_GRUPO.items():
            grupo = Group.objects.filter(name__iexact=nombre).first()
            if grupo is None:
                grupos_faltantes.append(nombre)
                continue
            permisos = list(Permission.objects.filter(content_type__app_label='product', codename__in=codenames))
            faltantes = set(codenames) - {p.codename for p in permisos}
            if faltantes:
                raise CommandError(f'Permisos inexistentes en el app product: {sorted(faltantes)} (¿faltan migraciones?).')
            plan.append((grupo, permisos))
        if grupos_faltantes:
            existentes = list(Group.objects.order_by('name').values_list('name', flat=True))
            raise CommandError(
                f'No existen los grupos {grupos_faltantes}. Grupos existentes: {existentes}. No se aplicó ningún cambio.'
            )

        with transaction.atomic():
            for grupo, permisos in plan:
                actuales = set(grupo.permissions.values_list('pk', flat=True))
                nuevos = [p for p in permisos if p.pk not in actuales]
                if nuevos and not dry_run:
                    grupo.permissions.add(*nuevos)
                self.stdout.write(
                    f'{grupo.name}: {"se agregarían" if dry_run else "agregados"} {len(nuevos)} '
                    f'({", ".join(p.codename for p in nuevos) or "-"}); ya presentes {len(permisos) - len(nuevos)}.'
                )
