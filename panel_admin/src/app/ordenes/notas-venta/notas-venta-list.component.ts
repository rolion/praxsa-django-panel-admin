import { SlicePipe } from '@angular/common';
import { Component, OnInit, ViewChild, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { DatatableComponent, NgxDatatableModule } from '@swimlane/ngx-datatable';
import { AuthService } from '../../core/service/auth.service';
import { extractApiError } from '../ordenes.errors';
import { AppNotaVenta } from '../ordenes.model';
import { OrdenesService } from '../ordenes.service';
import { statusClass } from '../ordenes.status';
import { confirmAnularOrden, showErrorAlert } from '../proforma-actions';
import { anularBlockReason, payBlockReason } from './nota-venta-rules';
import { PagoModalComponent } from './pago-modal.component';

/** Listado de Notas de Venta (Ordenes > Nota de Venta). Nacen con la nota de
 * trabajo; aqui se consultan, se cobran y se anulan. Los botones se ocultan por
 * permiso y se deshabilitan (con motivo) por precondicion de negocio; solo es
 * UX: el servidor valida permiso, alcance por sucursal y estado. */
@Component({
  selector: 'app-notas-venta-list',
  standalone: true,
  imports: [RouterLink, NgxDatatableModule, SlicePipe],
  templateUrl: './notas-venta-list.component.html',
})
export class NotasVentaListComponent implements OnInit {
  @ViewChild(DatatableComponent) table!: DatatableComponent;

  private ordenesService = inject(OrdenesService);
  private modalService = inject(NgbModal);
  authService = inject(AuthService);

  data: AppNotaVenta[] = [];
  rows: AppNotaVenta[] = [];
  loadingIndicator = true;
  errorMessage = '';
  withoutSucursal = false;

  readonly payBlockReason = payBlockReason;
  readonly anularBlockReason = anularBlockReason;

  badge(status: string): string {
    return 'status-badge ' + statusClass(status);
  }

  get canPay(): boolean {
    return this.authService.hasPermission('add_pago');
  }

  get canAnular(): boolean {
    return this.authService.hasPermission('delete_nota_venta');
  }

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loadingIndicator = true;
    this.ordenesService.listNotasVenta().subscribe({
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
        this.errorMessage = 'No se pudieron cargar las notas de venta.';
        this.loadingIndicator = false;
      },
    });
  }

  filterDatatable(event: Event): void {
    const val = (event.target as HTMLInputElement).value.toLowerCase();
    this.rows = this.data.filter(
      (row) =>
        !val ||
        String(row.id).indexOf(val) !== -1 ||
        String(row.proforma_id ?? '').indexOf(val) !== -1 ||
        row.name.toLowerCase().indexOf(val) !== -1 ||
        (row.ci_nit || '').toLowerCase().indexOf(val) !== -1 ||
        (row.sucursal_name || '').toLowerCase().indexOf(val) !== -1
    );
    if (this.table) {
      this.table.offset = 0;
    }
  }

  pay(row: AppNotaVenta): void {
    if (payBlockReason(row)) {
      return;
    }
    const ref = this.modalService.open(PagoModalComponent, { ariaLabelledBy: 'pago-modal-title' });
    ref.componentInstance.notaVentaId = row.id;
    ref.componentInstance.total = row.total_price;
    ref.result.then(
      () => this.load(),
      () => undefined
    );
  }

  async anular(row: AppNotaVenta): Promise<void> {
    if (anularBlockReason(row) || !(await confirmAnularOrden(row.proforma_id, 'nota de venta'))) {
      return;
    }
    this.ordenesService.anularNotaVenta(row.id).subscribe({
      next: () => this.load(),
      error: (err) =>
        showErrorAlert('No se pudo anular la nota de venta', extractApiError(err, 'No se pudo anular la nota de venta.')),
    });
  }
}
