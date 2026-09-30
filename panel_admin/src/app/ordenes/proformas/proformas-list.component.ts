import { SlicePipe } from '@angular/common';
import { Component, OnInit, ViewChild, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { DatatableComponent, NgxDatatableModule } from '@swimlane/ngx-datatable';
import { AuthService } from '../../core/service/auth.service';
import { extractApiError } from '../ordenes.errors';
import { AppProforma } from '../ordenes.model';
import { OrdenesService } from '../ordenes.service';
import { ORDER_STATUS_OPTIONS, statusClass } from '../ordenes.status';
import { confirmAnularProforma, confirmGenerateNota, saveBlob, showErrorAlert } from '../proforma-actions';

/** Listado de proformas (Ordenes > Proforma). Mismo patron de tabla/busqueda/
 * acciones que Almacen. Los botones se ocultan segun estado y permisos, pero
 * solo es UX: cada endpoint valida permiso y alcance por sucursal
 * (ADR-modulo-ordenes-proforma-nota-trabajo-alcance-permisos). */
@Component({
  selector: 'app-proformas-list',
  standalone: true,
  imports: [RouterLink, NgxDatatableModule, SlicePipe],
  templateUrl: './proformas-list.component.html',
})
export class ProformasListComponent implements OnInit {
  @ViewChild(DatatableComponent) table!: DatatableComponent;

  private ordenesService = inject(OrdenesService);
  authService = inject(AuthService);

  data: AppProforma[] = [];
  rows: AppProforma[] = [];
  loadingIndicator = true;
  errorMessage = '';
  /** El usuario no tiene ninguna sucursal asignada: el listado vacio se explica. */
  withoutSucursal = false;
  readonly statusOptions = ORDER_STATUS_OPTIONS;
  statusFilter = '';
  private searchTerm = '';

  badge(status: string): string {
    return 'status-badge ' + statusClass(status);
  }

  get canCreate(): boolean {
    return this.authService.hasPermission('add_proforma_header');
  }

  get canEdit(): boolean {
    return this.authService.hasPermission('change_proforma_header');
  }

  get canGenerateNota(): boolean {
    return this.authService.hasPermission('add_nota_trabajo');
  }

  get canAnular(): boolean {
    return this.authService.hasPermission('delete_proforma_header');
  }

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loadingIndicator = true;
    this.ordenesService.listProformas().subscribe({
      next: (rows) => {
        this.data = rows;
        this.applyFilters();
        this.loadingIndicator = false;
        if (rows.length === 0) {
          this.checkSucursal();
        }
      },
      error: () => {
        this.errorMessage = 'No se pudieron cargar las proformas.';
        this.loadingIndicator = false;
      },
    });
  }

  private checkSucursal(): void {
    this.ordenesService.listSucursales().subscribe({
      next: (sucursales) => (this.withoutSucursal = sucursales.length === 0),
      error: () => (this.withoutSucursal = false),
    });
  }

  filterDatatable(event: Event): void {
    this.searchTerm = (event.target as HTMLInputElement).value.toLowerCase();
    this.applyFilters();
  }

  onStatusChange(event: Event): void {
    this.statusFilter = (event.target as HTMLSelectElement).value;
    this.applyFilters();
  }

  private applyFilters(): void {
    const val = this.searchTerm;
    this.rows = this.data.filter(
      (row) =>
        (!this.statusFilter || row.status === this.statusFilter) &&
        (!val ||
          String(row.id).indexOf(val) !== -1 ||
          row.name.toLowerCase().indexOf(val) !== -1 ||
          (row.car_plate || '').toLowerCase().indexOf(val) !== -1 ||
          (row.car_model_name || '').toLowerCase().indexOf(val) !== -1 ||
          (row.sucursal_name || '').toLowerCase().indexOf(val) !== -1)
    );
    if (this.table) {
      this.table.offset = 0;
    }
  }

  async generateNota(row: AppProforma): Promise<void> {
    if (!(await confirmGenerateNota(row.id))) {
      return;
    }
    this.ordenesService.generarNotaTrabajo(row.id).subscribe({
      next: () => this.load(),
      error: (err) =>
        showErrorAlert(
          'No se pudo aprobar la proforma',
          extractApiError(err, 'No se pudo aprobar la proforma.')
        ),
    });
  }

  async anular(row: AppProforma): Promise<void> {
    if (!(await confirmAnularProforma(row.id))) {
      return;
    }
    this.ordenesService.anularProforma(row.id).subscribe({
      next: () => this.load(),
      error: (err) =>
        showErrorAlert('No se pudo anular la proforma', extractApiError(err, 'No se pudo anular la proforma.')),
    });
  }

  downloadPdf(row: AppProforma): void {
    this.ordenesService.downloadProformaPdf(row.id).subscribe({
      next: (blob) => saveBlob(blob, `proforma-${row.id}.pdf`),
      error: (err) =>
        showErrorAlert('No se pudo descargar el PDF', extractApiError(err, 'No se pudo descargar el PDF.')),
    });
  }
}
