"""Asigna a los grupos del negocio los permisos `view` de los reportes de Ventas
Diarias y Utilidad (TASK-reportes-utilidad-ventas-diarias, ADR-...-permisos).
Idempotente: solo agrega lo que falta; no quita permisos ni crea grupos. El
nombre del grupo no distingue mayusculas y se aplica a TODOS los grupos que
coincidan (en algunos ambientes existen tanto `Admin` como `admin`)."""
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

# grupo -> permisos (codename del app `product`). `view_proxy_pagos` es el permiso del
# "Reporte Ventas Diaria"; `view_utilidades`, el del "Reporte Utilidades" (muestra costos).
PERMISOS_POR_GRUPO = {
    'Admin': ['view_proxy_pagos', 'view_utilidades'],
    'Caja': ['view_proxy_pagos'],
}


class Command(BaseCommand):
    help = 'Asigna a Admin (ambos reportes) y Caja (solo Ventas Diarias) los permisos de los reportes.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Muestra lo que se agregaria sin escribir.')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        plan = []
        grupos_faltantes = []
        for nombre, codenames in PERMISOS_POR_GRUPO.items():
            grupos = list(Group.objects.filter(name__iexact=nombre).order_by('name'))
            if not grupos:
                grupos_faltantes.append(nombre)
                continue
            permisos = list(Permission.objects.filter(content_type__app_label='product', codename__in=codenames))
            faltantes = set(codenames) - {p.codename for p in permisos}
            if faltantes:
                raise CommandError(f'Permisos inexistentes en el app product: {sorted(faltantes)} (¿faltan migraciones?).')
            plan.extend((grupo, permisos) for grupo in grupos)
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
