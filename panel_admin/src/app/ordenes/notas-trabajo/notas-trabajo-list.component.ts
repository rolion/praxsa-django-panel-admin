import { SlicePipe } from '@angular/common';
import { Component, OnInit, ViewChild, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { DatatableComponent, NgxDatatableModule } from '@swimlane/ngx-datatable';
import { AuthService } from '../../core/service/auth.service';
import { AppNotaTrabajo } from '../ordenes.model';
import { OrdenesService } from '../ordenes.service';
import {
  COBRO_NOTA_TRABAJO_OPTIONS, OpcionFiltro, SIN_NOTA_VENTA, TODOS, TRABAJO_OPTIONS, opcionesPorId, opcionesUnicas, valorDeEvento,
} from '../ordenes.filtros';
import { statusClass } from '../ordenes.status';

type FiltroNotaTrabajo = 'sucursal' | 'marca' | 'modelo' | 'instalador' | 'status' | 'cobro';
const FILTROS_VACIOS: Record<FiltroNotaTrabajo, string> = {
  sucursal: TODOS, marca: TODOS, modelo: TODOS, instalador: TODOS, status: TODOS, cobro: TODOS,
};

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
  /** Filtros de la tarjeta "Filtros" ('' = todos); se combinan con el buscador por AND. */
  filtros: Record<FiltroNotaTrabajo, string> = { ...FILTROS_VACIOS };
  readonly estadoOptions = TRABAJO_OPTIONS;
  readonly cobroOptions = COBRO_NOTA_TRABAJO_OPTIONS;
  private searchTerm = '';

  /** Opciones tomadas de las filas cargadas (ya acotadas por el backend a las sucursales del usuario). */
  get sucursalOptions(): OpcionFiltro[] {
    return opcionesPorId(this.data, (r) => r.sucursal_id, (r) => r.sucursal_name);
  }

  get marcaOptions(): string[] {
    return opcionesUnicas(this.data, (r) => r.car_brand_name);
  }

  get modeloOptions(): string[] {
    const marca = this.filtros.marca;
    const rows = marca ? this.data.filter((r) => r.car_brand_name === marca) : this.data;
    return opcionesUnicas(rows, (r) => r.car_model_name);
  }

  get instaladorOptions(): OpcionFiltro[] {
    return opcionesPorId(this.data, (r) => r.instaladar, (r) => r.instalador_name);
  }

  get hasActiveFilters(): boolean {
    return Object.values(this.filtros).some((value) => value !== TODOS);
  }

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
        this.applyFilters();
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
    this.searchTerm = valorDeEvento(event).toLowerCase();
    this.applyFilters();
  }

  setFiltro(campo: FiltroNotaTrabajo, event: Event): void {
    this.filtros[campo] = valorDeEvento(event);
    if (campo === 'marca') {
      this.filtros.modelo = TODOS;
    }
    this.applyFilters();
  }

  limpiarFiltros(): void {
    this.filtros = { ...FILTROS_VACIOS };
    this.applyFilters();
  }

  private applyFilters(): void {
    const val = this.searchTerm;
    const f = this.filtros;
    this.rows = this.data.filter(
      (row) =>
        (!f.sucursal || String(row.sucursal_id) === f.sucursal) &&
        (!f.marca || row.car_brand_name === f.marca) &&
        (!f.modelo || row.car_model_name === f.modelo) &&
        (!f.instalador || String(row.instaladar) === f.instalador) &&
        (!f.status || row.status === f.status) &&
        (!f.cobro || (f.cobro === SIN_NOTA_VENTA ? row.nota_venta === null : row.nota_venta?.status === f.cobro)) &&
        (!val ||
          String(row.proforma_id).indexOf(val) !== -1 ||
          row.name.toLowerCase().indexOf(val) !== -1 ||
          (row.car_plate || '').toLowerCase().indexOf(val) !== -1 ||
          (row.car_model_name || '').toLowerCase().indexOf(val) !== -1 ||
          (row.instalador_name || '').toLowerCase().indexOf(val) !== -1)
    );
    if (this.table) {
      this.table.offset = 0;
    }
  }
}
