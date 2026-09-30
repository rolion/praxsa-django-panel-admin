import { Component, OnInit, ViewChild, inject } from '@angular/core';
import { ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { DatatableComponent, NgxDatatableModule } from '@swimlane/ngx-datatable';
import { Observable } from 'rxjs';
import { ReporteBase } from '../reporte-base';
import { hoyIso } from '../reportes.filtros';
import { ReporteFiltros, VentaDiariaRow, VentasDiariasReport } from '../reportes.model';
import { ReportesService } from '../reportes.service';

/** Reporte de Ventas Diarias (Reportes > Ventas Diarias): cobros del periodo con totales, desglose
 * por tipo de venta y de pago. Solo lectura; sin costos ni utilidad. Ver DDR-reportes-utilidad-
 * ventas-diarias-pantallas-reportes. */
@Component({
  selector: 'app-ventas-diarias',
  standalone: true,
  imports: [RouterLink, ReactiveFormsModule, NgxDatatableModule],
  templateUrl: './ventas-diarias.component.html',
})
export class VentasDiariasComponent extends ReporteBase<VentasDiariasReport> implements OnInit {
  @ViewChild(DatatableComponent) table!: DatatableComponent;

  private reportesService = inject(ReportesService);
  protected readonly permission = 'view_proxy_pagos';

  report: VentasDiariasReport | null = null;
  rows: VentaDiariaRow[] = [];

  /** Fila de resumen de la tabla: los totales son los del servidor (todo el periodo), no la
   * suma de la pagina visible. */
  readonly summary: Record<string, () => string> = {
    venta_lamina: () => this.bs(this.report?.totales.venta_lamina),
    instalacion: () => this.bs(this.report?.totales.instalacion),
    bruto: () => this.bs(this.report?.totales.bruto),
    descuento: () => this.bs(this.report?.totales.descuento),
    cobrado: () => this.bs(this.report?.totales.cobrado),
  };
  readonly noSummary = (): string => '';

  ngOnInit(): void {
    this.init();
  }

  protected defaultDesde(): string {
    return hoyIso();
  }

  protected fetch(filtros: ReporteFiltros): Observable<VentasDiariasReport> {
    return this.reportesService.getVentasDiarias(filtros);
  }

  protected loaded(report: VentasDiariasReport): void {
    this.report = report;
    this.rows = report.rows;
    this.withoutSucursal = report.sin_sucursal;
  }

  filterDatatable(event: Event): void {
    const val = (event.target as HTMLInputElement).value.toLowerCase();
    this.rows = (this.report?.rows ?? []).filter(
      (row) =>
        !val ||
        String(row.nota_venta_id).indexOf(val) !== -1 ||
        String(row.proforma_id).indexOf(val) !== -1 ||
        row.cliente.toLowerCase().indexOf(val) !== -1 ||
        (row.registro_contable || '').toLowerCase().indexOf(val) !== -1
    );
    if (this.table) {
      this.table.offset = 0;
    }
  }

  badge(row: VentaDiariaRow): string {
    return 'status-badge ' + (row.sales_type === 'venta_instalacion' ? 'status-proforma' : 'status-cobrar');
  }
}
