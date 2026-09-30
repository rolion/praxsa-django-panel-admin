import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { NgbProgressbar } from '@ng-bootstrap/ng-bootstrap';
import { NgApexchartsModule } from 'ng-apexcharts';
import { Observable } from 'rxjs';
import { AuthService } from '../../core/service/auth.service';
import { extractApiError } from '../../ordenes/ordenes.errors';
import { AppProforma, OrdenSucursal } from '../../ordenes/ordenes.model';
import { OrdenesService } from '../../ordenes/ordenes.service';
import { confirmGenerateNota, showErrorAlert } from '../../ordenes/proforma-actions';
import { statusClass } from '../../ordenes/ordenes.status';
import { bs, fechaHora, porcentaje } from '../../reportes/reportes.filtros';
import { AxisChartOptions, DonutChartOptions, donutChart, lineChart, stackedBarChart } from '../dashboard.charts';
import {
  ColaFila,
  ColaTaller,
  ConsumoLaminas,
  DashboardKpis,
  DashboardParams,
  ItemsSolicitados,
  ProformasRecientes,
  ProformasVsVentas,
  StockCritico,
  StockEstado,
  StockFila,
} from '../dashboard.model';
import { DashboardService } from '../dashboard.service';

/** Estado independiente de cada widget: carga, error (con "Reintentar") y dato. */
export interface WidgetState<T> {
  loading: boolean;
  error: string;
  data: T | null;
}

function newState<T>(): WidgetState<T> {
  return { loading: false, error: '', data: null };
}

interface EstadoStockInfo {
  label: string;
  icon: string;
  clase: string;
  barra: 'success' | 'warning' | 'danger';
}

const STOCK_INFO: Record<StockEstado, EstadoStockInfo> = {
  ok: { label: 'OK', icon: 'fa-check-circle', clase: 'stock-ok', barra: 'success' },
  bajo: { label: 'Bajo', icon: 'fa-exclamation-triangle', clase: 'stock-bajo', barra: 'warning' },
  critico: { label: 'Crítico', icon: 'fa-times-circle', clase: 'stock-critico', barra: 'danger' },
};

/** Dashboard del taller (ver DDR-dashboard-taller-laminas-pantalla-dashboard). Solo lectura salvo
 * "Convertir a venta", que reutiliza la aprobacion de proformas de Ordenes. Ocultar ventas segun el
 * `null` del servidor es solo UX: la barrera real es el permiso del endpoint. */
@Component({
  selector: 'app-main',
  templateUrl: './main.component.html',
  imports: [RouterLink, FormsModule, NgbProgressbar, NgApexchartsModule],
})
export class MainComponent implements OnInit {
  private dashboard = inject(DashboardService);
  private ordenesService = inject(OrdenesService);
  private destroyRef = inject(DestroyRef);
  authService = inject(AuthService);

  readonly bs = bs;
  readonly fechaHora = fechaHora;
  readonly porcentaje = porcentaje;
  readonly statusClass = statusClass;
  readonly periodos = [12, 6];

  sucursales: OrdenSucursal[] = [];
  sucursal: number | null = null;
  meses = 12;
  stockTodos = false;
  converting: number | null = null;

  kpis = newState<DashboardKpis>();
  serie = newState<ProformasVsVentas>();
  consumo = newState<ConsumoLaminas>();
  items = newState<ItemsSolicitados>();
  stock = newState<StockCritico>();
  cola = newState<ColaTaller>();
  recientes = newState<ProformasRecientes>();

  lineOptions: AxisChartOptions | null = null;
  barOptions: AxisChartOptions | null = null;
  donutOptions: DonutChartOptions | null = null;

  ngOnInit(): void {
    this.ordenesService
      .listSucursales()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (sucursales) => (this.sucursales = sucursales),
        error: () => (this.sucursales = []),
      });
    this.loadAll();
  }

  /** Con mas de una sucursal en alcance se ofrece el selector ("Todas"), como en Reportes. */
  get showSucursalSelector(): boolean {
    return this.sucursales.length > 1;
  }

  private get params(): DashboardParams {
    return { sucursal: this.sucursal, meses: this.meses, todos: this.stockTodos };
  }

  // ------------------------------------------------------------------ carga
  loadAll(): void {
    this.loadKpis();
    this.loadSerie();
    this.loadConsumo();
    this.loadItems();
    this.loadStock();
    this.loadCola();
    this.loadRecientes();
  }

  loadKpis(): void {
    this.run(this.kpis, this.dashboard.getKpis(this.params));
  }

  loadSerie(): void {
    this.run(this.serie, this.dashboard.getProformasVsVentas(this.params), (d) => (this.lineOptions = lineChart(d)));
  }

  loadConsumo(): void {
    this.run(this.consumo, this.dashboard.getConsumoLaminas(this.params), (d) => (this.barOptions = stackedBarChart(d)));
  }

  loadItems(): void {
    this.run(this.items, this.dashboard.getItemsSolicitados(this.params), (d) => (this.donutOptions = donutChart(d)));
  }

  loadStock(): void {
    this.run(this.stock, this.dashboard.getStockCritico(this.params));
  }

  loadCola(): void {
    this.run(this.cola, this.dashboard.getColaTaller(this.params));
  }

  loadRecientes(): void {
    this.run(this.recientes, this.dashboard.getProformasRecientes(this.params));
  }

  private run<T>(state: WidgetState<T>, source: Observable<T>, after?: (data: T) => void): void {
    state.loading = true;
    state.error = '';
    source.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (data) => {
        state.data = data;
        state.loading = false;
        after?.(data);
      },
      error: (err) => {
        state.error = extractApiError(err, 'No se pudo cargar esta sección.');
        state.loading = false;
      },
    });
  }

  setSucursal(value: number | null): void {
    this.sucursal = value;
    this.loadAll();
  }

  setMeses(value: number): void {
    this.meses = Number(value);
    this.loadSerie();
    this.loadConsumo();
    this.loadItems();
  }

  toggleStockTodos(): void {
    this.stockTodos = !this.stockTodos;
    this.loadStock();
  }

  // ------------------------------------------------------------------ presentacion
  /** "Sin datos" de las graficas: se decide con el texto del servidor, sin convertir a numero. */
  get serieVacia(): boolean {
    const s = this.serie.data;
    return !s || (s.cotizado.every(esCero) && (s.vendido === null || s.vendido.every(esCero)));
  }

  resumenSerie(s: ProformasVsVentas): string {
    const ultimo = s.meses.length - 1;
    const vendido = s.vendido ? `, ventas reales ${bs(s.vendido[ultimo])}` : '';
    return `Último mes: cotizado ${bs(s.cotizado[ultimo])}${vendido}.`;
  }

  variacion(value: string | null): { texto: string; icono: string; clase: string } {
    if (value === null) {
      return { texto: 'Sin datos del mes anterior', icono: '', clase: 'delta-flat' };
    }
    const n = Number(value);
    if (n > 0) {
      return { texto: `+${value} %`, icono: '▲', clase: 'delta-up' };
    }
    if (n < 0) {
      return { texto: `${value} %`, icono: '▼', clase: 'delta-down' };
    }
    return { texto: '0.0 %', icono: '=', clase: 'delta-flat' };
  }

  stockInfo(estado: StockEstado): EstadoStockInfo {
    return STOCK_INFO[estado];
  }

  /** Ancho de la barra de nivel: metros respecto del umbral "bajo" (tope 100 %). Solo visual. */
  stockPercent(fila: StockFila, umbralBajo: string): number {
    const tope = Number(umbralBajo);
    return tope > 0 ? Math.max(0, Math.min(100, (Number(fila.metros) / tope) * 100)) : 100;
  }

  laminasTexto(fila: ColaFila): string {
    if (!fila.laminas.length) {
      return '—';
    }
    return fila.laminas.length > 1 ? `${fila.laminas[0]} +${fila.laminas.length - 1}` : fila.laminas[0];
  }

  get showStockSucursal(): boolean {
    return this.sucursales.length > 1 && !this.sucursal;
  }

  canConvert(row: AppProforma): boolean {
    return row.status === 'proforma' && this.authService.hasPermission('add_nota_trabajo');
  }

  // ------------------------------------------------------------------ convertir a venta
  /** Reutiliza la aprobacion de Ordenes ("Aprobar y generar orden"): confirmacion, errores y permiso. */
  async convertir(row: AppProforma): Promise<void> {
    if (this.converting !== null || !(await confirmGenerateNota(row.id))) {
      return;
    }
    this.converting = row.id;
    this.ordenesService.generarNotaTrabajo(row.id).subscribe({
      next: () => {
        this.converting = null;
        this.loadAll();
      },
      error: (err) => {
        this.converting = null;
        showErrorAlert('No se pudo aprobar la proforma', extractApiError(err, 'No se pudo aprobar la proforma.'));
      },
    });
  }
}

function esCero(value: string): boolean {
  return Number(value) === 0;
}
