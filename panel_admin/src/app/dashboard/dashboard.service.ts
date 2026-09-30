import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  ColaTaller,
  ConsumoLaminas,
  DashboardKpis,
  DashboardParams,
  ItemsSolicitados,
  ProformasRecientes,
  ProformasVsVentas,
  StockCritico,
} from './dashboard.model';

@Injectable({
  providedIn: 'root',
})
export class DashboardService {
  private http = inject(HttpClient);
  private base = `${environment.apiUrl}/product/dashboard`;

  getKpis(params: DashboardParams = {}): Observable<DashboardKpis> {
    return this.http.get<DashboardKpis>(`${this.base}/kpis`, { params: this.params(params) });
  }

  getProformasVsVentas(params: DashboardParams = {}): Observable<ProformasVsVentas> {
    return this.http.get<ProformasVsVentas>(`${this.base}/proformas-vs-ventas`, {
      params: this.params(params, ['sucursal', 'meses']),
    });
  }

  getConsumoLaminas(params: DashboardParams = {}): Observable<ConsumoLaminas> {
    return this.http.get<ConsumoLaminas>(`${this.base}/consumo-laminas`, {
      params: this.params(params, ['sucursal', 'meses']),
    });
  }

  getItemsSolicitados(params: DashboardParams = {}): Observable<ItemsSolicitados> {
    return this.http.get<ItemsSolicitados>(`${this.base}/items-solicitados`, {
      params: this.params(params, ['sucursal', 'meses']),
    });
  }

  getStockCritico(params: DashboardParams = {}): Observable<StockCritico> {
    return this.http.get<StockCritico>(`${this.base}/stock-critico`, {
      params: this.params(params, ['sucursal', 'todos']),
    });
  }

  getColaTaller(params: DashboardParams = {}): Observable<ColaTaller> {
    return this.http.get<ColaTaller>(`${this.base}/cola-taller`, { params: this.params(params) });
  }

  getProformasRecientes(params: DashboardParams = {}): Observable<ProformasRecientes> {
    return this.http.get<ProformasRecientes>(`${this.base}/proformas-recientes`, { params: this.params(params) });
  }

  /** Solo se envian los parametros con valor y los que el endpoint usa (por defecto, solo la sucursal). */
  private params(params: DashboardParams, allowed: (keyof DashboardParams)[] = ['sucursal']): HttpParams {
    let query = new HttpParams();
    if (allowed.includes('sucursal') && params.sucursal) {
      query = query.set('sucursal', String(params.sucursal));
    }
    if (allowed.includes('meses') && params.meses) {
      query = query.set('meses', String(params.meses));
    }
    if (allowed.includes('todos') && params.todos) {
      query = query.set('todos', 'true');
    }
    return query;
  }
}
