import { SlicePipe } from '@angular/common';
import { Component, OnInit, ViewChild, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { DatatableComponent, NgxDatatableModule } from '@swimlane/ngx-datatable';
import { AuthService } from '../../core/service/auth.service';
import { AppNotaTrabajo } from '../ordenes.model';
import { OrdenesService } from '../ordenes.service';
import { statusClass } from '../ordenes.status';

/** Listado de Notas de Trabajo (Ordenes > Nota de Trabajo). Solo consulta y
 * edicion operativa: las notas nacen de la proforma, no se crean aqui. */
@Component({
  selector: 'app-notas-trabajo-list',
  standalone: true,
  imports: [RouterLink, NgxDatatableModule, SlicePipe],
  templateUrl: './notas-trabajo-list.component.html',
})
export class NotasTrabajoListComponent implements OnInit {
  @ViewChild(DatatableComponent) table!: DatatableComponent;

  private ordenesService = inject(OrdenesService);
  authService = inject(AuthService);

  data: AppNotaTrabajo[] = [];
  rows: AppNotaTrabajo[] = [];
  loadingIndicator = true;
  errorMessage = '';
  withoutSucursal = false;

  badge(status: string): string {
    return 'status-badge ' + statusClass(status);
  }

  get canEdit(): boolean {
    return this.authService.hasPermission('change_nota_trabajo');
  }

  ngOnInit(): void {
    this.ordenesService.listNotasTrabajo().subscribe({
      next: (rows) => {
        this.data = rows;
        this.rows = rows;
        this.loadingIndicator = false;
        if (rows.length === 0) {
          this.ordenesService.listSucursales().subscribe({
            next: (sucursales) => (this.withoutSucursal = sucursales.length === 0),
            error: () => (this.withoutSucursal = false),
          });
        }
      },
      error: () => {
        this.errorMessage = 'No se pudieron cargar las notas de trabajo.';
        this.loadingIndicator = false;
      },
    });
  }

  filterDatatable(event: Event): void {
    const val = (event.target as HTMLInputElement).value.toLowerCase();
    this.rows = this.data.filter(
      (row) =>
        !val ||
        String(row.proforma_id).indexOf(val) !== -1 ||
        row.name.toLowerCase().indexOf(val) !== -1 ||
        (row.car_plate || '').toLowerCase().indexOf(val) !== -1 ||
        (row.car_model_name || '').toLowerCase().indexOf(val) !== -1 ||
        (row.instalador_name || '').toLowerCase().indexOf(val) !== -1
    );
    if (this.table) {
      this.table.offset = 0;
    }
  }
}
