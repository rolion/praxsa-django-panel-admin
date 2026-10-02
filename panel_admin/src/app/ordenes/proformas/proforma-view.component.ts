import { DatePipe } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { NgxDatatableModule } from '@swimlane/ngx-datatable';
import { AuthService } from '../../core/service/auth.service';
import { extractApiError } from '../ordenes.errors';
import { AppProformaDetail, SALES_TYPE_INSTALACION } from '../ordenes.model';
import { OrdenesService } from '../ordenes.service';
import { statusClass } from '../ordenes.status';
import { confirmAnularProforma, confirmGenerateNota, saveBlob, showErrorAlert } from '../proforma-actions';

@Component({
  selector: 'app-proforma-view',
  standalone: true,
  imports: [RouterLink, NgxDatatableModule, DatePipe],
  templateUrl: './proforma-view.component.html',
})
export class ProformaViewComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private ordenesService = inject(OrdenesService);
  authService = inject(AuthService);

  proforma: AppProformaDetail | null = null;
  loading = true;
  errorMessage = '';

  /** Las columnas no numericas no llevan resumen (el pie solo muestra totales bajo Subtotal). */
  noSummary = (): string => '';

  /** Estado global de la orden (derivado en el servidor): el texto viene de `status_label`. */
  get statusText(): string {
    return this.proforma?.status_label ?? '';
  }

  get statusClass(): string {
    return statusClass(this.proforma?.status);
  }

  /** La orden existe (nota de trabajo y de venta vigentes) en estos estados. */
  get hasOrder(): boolean {
    const status = this.proforma?.status;
    return status === 'en_trabajo' || status === 'por_cobrar' || status === 'finalizado';
  }

  get isInstalacion(): boolean {
    return this.proforma?.sales_type === SALES_TYPE_INSTALACION;
  }

  /** La sucursal esta inactiva: la proforma se ve pero no se modifica. */
  get sucursalInactiva(): boolean {
    return this.proforma?.sucursal_activa === false;
  }

  get canEdit(): boolean {
    return (
      !!this.proforma && this.proforma.status === 'proforma' && !this.sucursalInactiva &&
      this.authService.hasPermission('change_proforma_header')
    );
  }

  get canGenerateNota(): boolean {
    return (
      !!this.proforma && this.proforma.status === 'proforma' && !this.sucursalInactiva &&
      this.authService.hasPermission('add_nota_trabajo')
    );
  }

  get canAnular(): boolean {
    return (
      !!this.proforma && this.proforma.status === 'proforma' && !this.sucursalInactiva &&
      this.authService.hasPermission('delete_proforma_header')
    );
  }

  ngOnInit(): void {
    this.load();
  }

  private load(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    this.ordenesService.getProforma(id).subscribe({
      next: (proforma) => {
        this.proforma = proforma;
        this.loading = false;
      },
      error: () => {
        this.errorMessage = 'No se pudo cargar la proforma.';
        this.loading = false;
      },
    });
  }

  async generateNota(): Promise<void> {
    if (!this.proforma || !(await confirmGenerateNota(this.proforma.id))) {
      return;
    }
    this.ordenesService.generarNotaTrabajo(this.proforma.id).subscribe({
      next: (proforma) => (this.proforma = proforma),
      error: (err) =>
        showErrorAlert(
          'No se pudo aprobar la proforma',
          extractApiError(err, 'No se pudo aprobar la proforma.')
        ),
    });
  }

  async anular(): Promise<void> {
    if (!this.proforma || !(await confirmAnularProforma(this.proforma.id))) {
      return;
    }
    this.ordenesService.anularProforma(this.proforma.id).subscribe({
      next: (proforma) => (this.proforma = proforma),
      error: (err) =>
        showErrorAlert('No se pudo anular la proforma', extractApiError(err, 'No se pudo anular la proforma.')),
    });
  }

  downloadPdf(): void {
    if (!this.proforma) {
      return;
    }
    const id = this.proforma.id;
    this.ordenesService.downloadProformaPdf(id).subscribe({
      next: (blob) => saveBlob(blob, `proforma-${id}.pdf`),
      error: (err) =>
        showErrorAlert('No se pudo descargar el PDF', extractApiError(err, 'No se pudo descargar el PDF.')),
    });
  }
}
