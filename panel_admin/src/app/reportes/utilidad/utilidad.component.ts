import { Component, OnInit, ViewChild, inject } from '@angular/core';
import { ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { DatatableComponent, NgxDatatableModule } from '@swimlane/ngx-datatable';
import { Observable } from 'rxjs';
import { ReporteBase } from '../reporte-base';
import { inicioMesIso } from '../reportes.filtros';
import { ReporteFiltros, UtilidadReport, UtilidadVentaRow } from '../reportes.model';
import { ReportesService } from '../reportes.service';

/** Reporte de Utilidad (Reportes > Utilidad): venta de lámina menos costo de compra, antes y
 * después de descuento; la instalación se muestra aparte y no entra en la utilidad. Solo lectura.
 * Muestra costos: solo para quien tenga `view_utilidades`. Ver DDR-reportes-utilidad-ventas-
 * diarias-pantallas-reportes (y su Actualización 1) y los ADR del task. */
@Component({
  selector: 'app-utilidad',
  standalone: true,
  imports: [RouterLink, ReactiveFormsModule, NgxDatatableModule],
  templateUrl: './utilidad.component.html',
})
export class UtilidadComponent extends ReporteBase<UtilidadReport> implements OnInit {
  @ViewChild(DatatableComponent) table!: DatatableComponent;

  private reportesService = inject(ReportesService);
  protected readonly permission = 'view_utilidades';

  report: UtilidadReport | null = null;
  rows: UtilidadVentaRow[] = [];

  /** Fila de resumen de la tabla por venta: totales del servidor (todo el periodo). */
  readonly summary: Record<string, () => string> = {
    venta_lamina: () => this.bs(this.report?.totales.venta_lamina),
    instalacion: () => this.bs(this.report?.totales.instalacion),
    descuento: () => this.bs(this.report?.totales.descuento),
    costo_compra: () => this.bs(this.report?.totales.costo_compra),
    utilidad_despues: () => this.bs(this.report?.totales.utilidad_despues),
    margen: () => this.porcentaje(this.report?.totales.margen),
  };
  readonly noSummary = (): string => '';

  ngOnInit(): void {
    this.init();
  }

  protected defaultDesde(): string {
    return inicioMesIso();
  }

  protected fetch(filtros: ReporteFiltros): Observable<UtilidadReport> {
    return this.reportesService.getUtilidad(filtros);
  }

  protected loaded(report: UtilidadReport): void {
    this.report = report;
    this.rows = report.ventas;
    this.withoutSucursal = report.sin_sucursal;
  }

  filterDatatable(event: Event): void {
    const val = (event.target as HTMLInputElement).value.toLowerCase();
    this.rows = (this.report?.ventas ?? []).filter(
      (row) =>
        !val ||
        String(row.nota_venta_id).indexOf(val) !== -1 ||
        String(row.proforma_id).indexOf(val) !== -1 ||
        row.cliente.toLowerCase().indexOf(val) !== -1
    );
    if (this.table) {
      this.table.offset = 0;
    }
  }

  badge(row: UtilidadVentaRow): string {
    return 'status-badge ' + (row.sales_type === 'venta_instalacion' ? 'status-proforma' : 'status-cobrar');
  }
}
