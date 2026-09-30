import { DatePipe } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { NgxDatatableModule } from '@swimlane/ngx-datatable';
import { AuthService } from '../../core/service/auth.service';
import { AppNotaTrabajoDetail, SALES_TYPE_INSTALACION } from '../ordenes.model';
import { OrdenesService } from '../ordenes.service';

@Component({
  selector: 'app-nota-trabajo-view',
  standalone: true,
  imports: [RouterLink, NgxDatatableModule, DatePipe],
  templateUrl: './nota-trabajo-view.component.html',
  styleUrl: '../orden-view.shared.scss',
})
export class NotaTrabajoViewComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private ordenesService = inject(OrdenesService);
  authService = inject(AuthService);

  nota: AppNotaTrabajoDetail | null = null;
  loading = true;
  errorMessage = '';

  get isInstalacion(): boolean {
    return this.nota?.sales_type === SALES_TYPE_INSTALACION;
  }

  /** Badge de estado: verde = finalizado, ambar = en ejecucion. */
  get statusText(): string {
    return this.nota?.is_finalizada ? 'Finalizado' : 'En ejecución';
  }

  get statusClass(): string {
    return this.nota?.is_finalizada ? 'status-done' : 'status-progress';
  }

  get canEdit(): boolean {
    return (
      !!this.nota &&
      !this.nota.is_finalizada &&
      !this.nota.is_close &&
      this.authService.hasPermission('change_nota_trabajo')
    );
  }

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    this.ordenesService.getNotaTrabajo(id).subscribe({
      next: (nota) => {
        this.nota = nota;
        this.loading = false;
      },
      error: () => {
        this.errorMessage = 'No se pudo cargar la nota de trabajo.';
        this.loading = false;
      },
    });
  }
}
