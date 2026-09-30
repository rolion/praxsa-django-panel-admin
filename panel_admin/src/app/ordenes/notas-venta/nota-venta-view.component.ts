import { DatePipe } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { Observable } from 'rxjs';
import { AuthService } from '../../core/service/auth.service';
import { extractApiError } from '../ordenes.errors';
import { AppNotaVentaDetail } from '../ordenes.model';
import { OrdenesService } from '../ordenes.service';
import { statusClass } from '../ordenes.status';
import { confirmAnularOrden, confirmAnularPago, showErrorAlert } from '../proforma-actions';
import { anularBlockReason, payBlockReason } from './nota-venta-rules';
import { PagoModalComponent } from './pago-modal.component';

/** Vista de una Nota de Venta: datos, estado del cobro y del trabajo, pago y
 * acciones (registrar pago, anular pago, anular nota de venta). */
@Component({
  selector: 'app-nota-venta-view',
  standalone: true,
  imports: [RouterLink, DatePipe],
  templateUrl: './nota-venta-view.component.html',
})
export class NotaVentaViewComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private ordenesService = inject(OrdenesService);
  private modalService = inject(NgbModal);
  authService = inject(AuthService);

  nota: AppNotaVentaDetail | null = null;
  loading = true;
  errorMessage = '';
  savedMessage = '';

  badge(status: string): string {
    return 'status-badge ' + statusClass(status);
  }

  get payBlockReason(): string {
    return this.nota ? payBlockReason(this.nota) : '';
  }

  get anularBlockReason(): string {
    return this.nota ? anularBlockReason(this.nota) : '';
  }

  get canPay(): boolean {
    return !!this.nota && this.nota.status === 'por_cobrar' && this.authService.hasPermission('add_pago');
  }

  get canAnularPago(): boolean {
    return (
      !!this.nota &&
      this.nota.status === 'pagada' &&
      !!this.nota.pago &&
      !this.nota.pago.cerrado &&
      this.authService.hasPermission('delete_pago')
    );
  }

  get canAnular(): boolean {
    return !!this.nota && this.nota.status === 'por_cobrar' && this.authService.hasPermission('delete_nota_venta');
  }

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    this.ordenesService.getNotaVenta(id).subscribe({
      next: (nota) => {
        this.nota = nota;
        this.loading = false;
      },
      error: () => {
        this.errorMessage = 'No se pudo cargar la nota de venta.';
        this.loading = false;
      },
    });
  }

  pay(): void {
    if (!this.nota || this.payBlockReason) {
      return;
    }
    const ref = this.modalService.open(PagoModalComponent, { ariaLabelledBy: 'pago-modal-title' });
    ref.componentInstance.notaVentaId = this.nota.id;
    ref.componentInstance.total = this.nota.total_price;
    ref.result.then(
      (nota: AppNotaVentaDetail) => {
        this.nota = nota;
        this.savedMessage = 'Pago registrado.';
      },
      () => undefined
    );
  }

  async anularPago(): Promise<void> {
    if (!this.nota || !(await confirmAnularPago(this.nota.id))) {
      return;
    }
    this.run(this.ordenesService.anularPago(this.nota.id), 'No se pudo anular el pago', 'Pago anulado.');
  }

  async anular(): Promise<void> {
    if (!this.nota || this.anularBlockReason || !(await confirmAnularOrden(this.nota.proforma_id, 'nota de venta'))) {
      return;
    }
    this.run(
      this.ordenesService.anularNotaVenta(this.nota.id),
      'No se pudo anular la nota de venta',
      'Nota de venta anulada; la proforma volvió a estar vigente.'
    );
  }

  private run(request: Observable<AppNotaVentaDetail>, errorTitle: string, okMessage: string): void {
    this.savedMessage = '';
    request.subscribe({
      next: (nota) => {
        this.nota = nota;
        this.savedMessage = okMessage;
      },
      error: (err) => showErrorAlert(errorTitle, extractApiError(err, errorTitle + '.')),
    });
  }
}
