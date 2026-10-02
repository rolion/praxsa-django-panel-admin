import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { ReporteFiltros, UtilidadReport, VentasDiariasReport } from './reportes.model';

@Injectable({
  providedIn: 'root',
})
export class ReportesService {
  private http = inject(HttpClient);
  private base = `${environment.apiUrl}/product/reportes`;

  getVentasDiarias(filtros: ReporteFiltros): Observable<VentasDiariasReport> {
    return this.http.get<VentasDiariasReport>(`${this.base}/ventas-diarias`, { params: this.params(filtros, true) });
  }

  getUtilidad(filtros: ReporteFiltros): Observable<UtilidadReport> {
    return this.http.get<UtilidadReport>(`${this.base}/utilidad`, { params: this.params(filtros, false) });
  }

  /** Solo se envian los filtros con valor; el tipo de pago aplica solo a Ventas Diarias. */
  private params(filtros: ReporteFiltros, conTipoPago: boolean): HttpParams {
    let params = new HttpParams().set('desde', filtros.desde).set('hasta', filtros.hasta);
    if (filtros.sucursales?.length) {
      params = params.set('sucursales', filtros.sucursales.join(','));
    } else if (filtros.sucursal) {
      params = params.set('sucursal', String(filtros.sucursal));
    }
    if (filtros.salesType) {
      params = params.set('sales_type', filtros.salesType);
    }
    if (conTipoPago && filtros.tipoPago) {
      params = params.set('tipo_pago', filtros.tipoPago);
    }
    return params;
  }
}
