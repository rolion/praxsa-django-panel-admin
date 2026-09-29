import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { AuthService } from '../../core/service/auth.service';
import { extractApiError } from '../ordenes.errors';
import { AppProformaDetail, SALES_TYPE_INSTALACION } from '../ordenes.model';
import { OrdenesService } from '../ordenes.service';
import { confirmGenerateNota, saveBlob, showErrorAlert } from '../proforma-actions';

@Component({
  selector: 'app-proforma-view',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './proforma-view.component.html',
})
export class ProformaViewComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private ordenesService = inject(OrdenesService);
  authService = inject(AuthService);

  proforma: AppProformaDetail | null = null;
  loading = true;
  errorMessage = '';

  get isInstalacion(): boolean {
    return this.proforma?.sales_type === SALES_TYPE_INSTALACION;
  }

  get canEdit(): boolean {
    return !!this.proforma && !this.proforma.is_close && this.authService.hasPermission('change_proforma_header');
  }

  get canGenerateNota(): boolean {
    return !!this.proforma && !this.proforma.is_close && this.authService.hasPermission('add_nota_trabajo');
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
          'No se pudo generar la nota de trabajo',
          extractApiError(err, 'No se pudo generar la nota de trabajo.')
        ),
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
