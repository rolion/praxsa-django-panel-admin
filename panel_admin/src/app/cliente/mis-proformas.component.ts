import { DatePipe } from '@angular/common';
import { Component, OnDestroy, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { NgxDatatableModule } from '@swimlane/ngx-datatable';
import { formatBs } from '../calculadora/calculadora.helpers';
import { ClientProformaRow } from './cliente.model';
import { ClienteService } from './cliente.service';

/** Mis proformas: lista de solo lectura de las proformas del cliente autenticado
 * (DDR-pricing-calculator-screen-flujo-cliente). Sin acciones ni columna de estado.
 *
 * API real: GET product/client/proformas (solo devuelve las del usuario del token). */
@Component({
  selector: 'app-mis-proformas',
  standalone: true,
  imports: [RouterLink, NgxDatatableModule, DatePipe],
  templateUrl: './mis-proformas.component.html',
})
export class MisProformasComponent implements OnInit, OnDestroy {
  private clienteService = inject(ClienteService);

  readonly formatBs = formatBs;
  rows = signal<ClientProformaRow[]>([]);
  loading = signal(true);
  errorMessage = signal('');
  /** Id de la proforma recien guardada (llega por el estado de navegacion): se resalta unos segundos. */
  highlightedId = signal<number | null>(null);
  private highlightTimer: ReturnType<typeof setTimeout> | null = null;

  ngOnInit(): void {
    const savedId = Number((history.state as { savedId?: number } | null)?.savedId);
    if (Number.isInteger(savedId) && savedId > 0) {
      this.highlightedId.set(savedId);
      this.highlightTimer = setTimeout(() => this.highlightedId.set(null), 5000);
    }
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.errorMessage.set('');
    this.clienteService.proformas().subscribe({
      next: (rows) => {
        // Mas recientes primero (el servidor ya ordena; se asegura por si cambia).
        this.rows.set([...rows].sort((a, b) => b.date.localeCompare(a.date) || b.id - a.id));
        this.loading.set(false);
      },
      error: () => {
        this.errorMessage.set('No se pudieron cargar tus proformas.');
        this.loading.set(false);
      },
    });
  }

  /** Clase de fila para `ngx-datatable` (resalta la proforma recien guardada). */
  rowClass = (row: ClientProformaRow): Record<string, boolean> => ({
    'saved-row': row.id === this.highlightedId(),
  });

  vehicle(row: ClientProformaRow): string {
    return [row.car_brand_name, row.car_model_name].filter(Boolean).join(' ');
  }

  ngOnDestroy(): void {
    if (this.highlightTimer) {
      clearTimeout(this.highlightTimer);
    }
  }
}
