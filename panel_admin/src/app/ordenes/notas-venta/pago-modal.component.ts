import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { extractApiError } from '../ordenes.errors';
import { AppNotaVentaDetail, PagoPayload, TipoPago } from '../ordenes.model';
import { OrdenesService } from '../ordenes.service';
import { confirmAction } from '../proforma-actions';

/** Modal "Registrar pago". El monto es de solo lectura: lo fija el servidor
 * (total de la nota de venta); aqui solo se elige el tipo de pago y, opcional, el
 * registro contable (formato 1234/26). Se cierra con la nota de venta actualizada. */
@Component({
  selector: 'app-pago-modal',
  standalone: true,
  imports: [ReactiveFormsModule],
  templateUrl: './pago-modal.component.html',
})
export class PagoModalComponent {
  private fb = inject(FormBuilder);
  private ordenesService = inject(OrdenesService);
  activeModal = inject(NgbActiveModal);

  /** Los fija quien abre el modal (`componentInstance`). */
  notaVentaId = 0;
  total = '';

  submitted = false;
  saving = false;
  errorMessage = '';

  readonly tipos: { value: TipoPago; label: string }[] = [
    { value: 'efec', label: 'Efectivo' },
    { value: 'trans', label: 'Tarjeta/QR' },
  ];

  form = this.fb.group({
    tipo_pago: ['efec' as TipoPago, Validators.required],
    registro_contable: ['', Validators.pattern(/^(\d{1,4}\/\d{2})?$/)],
  });

  async submit(): Promise<void> {
    this.submitted = true;
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    if (!(await confirmAction(`¿Registrar el pago de ${this.total} Bs?`, 'La nota de venta quedará pagada.', 'Registrar pago'))) {
      return;
    }
    const value = this.form.value;
    const payload: PagoPayload = {
      tipo_pago: value.tipo_pago as TipoPago,
      registro_contable: (value.registro_contable || '').trim(),
    };
    this.saving = true;
    this.errorMessage = '';
    this.ordenesService.registrarPago(this.notaVentaId, payload).subscribe({
      next: (nota: AppNotaVentaDetail) => {
        this.saving = false;
        this.activeModal.close(nota);
      },
      error: (err) => {
        this.saving = false;
        this.errorMessage = extractApiError(err, 'No se pudo registrar el pago.');
      },
    });
  }
}
