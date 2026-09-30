import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, from, throwError } from 'rxjs';
import { catchError, switchMap } from 'rxjs/operators';
import { environment } from '../../environments/environment';
import {
  AppNotaTrabajo,
  AppNotaTrabajoDetail,
  AppNotaVenta,
  AppNotaVentaDetail,
  AppProforma,
  AppProformaDetail,
  NotaTrabajoUpdatePayload,
  OrdenInstalador,
  OrdenSucursal,
  PagoPayload,
  ProformaPayload,
  ReelCatalogItem,
} from './ordenes.model';

interface ProformaListParams {
  search?: string;
  salesType?: string;
  status?: string;
}

@Injectable({
  providedIn: 'root',
})
export class OrdenesService {
  private http = inject(HttpClient);
  private base = `${environment.apiUrl}/product/ordenes`;

  // Proformas
  listProformas(params: ProformaListParams = {}): Observable<AppProforma[]> {
    const query: Record<string, string> = {};
    if (params.search) {
      query['search'] = params.search;
    }
    if (params.salesType) {
      query['sales_type'] = params.salesType;
    }
    if (params.status) {
      query['status'] = params.status;
    }
    return this.http.get<AppProforma[]>(`${this.base}/proformas`, { params: query });
  }

  getProforma(id: number): Observable<AppProformaDetail> {
    return this.http.get<AppProformaDetail>(`${this.base}/proformas/${id}/`);
  }

  createProforma(payload: ProformaPayload): Observable<AppProformaDetail> {
    return this.http.post<AppProformaDetail>(`${this.base}/proformas`, payload);
  }

  updateProforma(id: number, payload: Partial<ProformaPayload>): Observable<AppProformaDetail> {
    return this.http.patch<AppProformaDetail>(`${this.base}/proformas/${id}/`, payload);
  }

  generarNotaTrabajo(id: number): Observable<AppProformaDetail> {
    return this.http.post<AppProformaDetail>(`${this.base}/proformas/${id}/generar-nota-trabajo/`, {});
  }

  anularProforma(id: number): Observable<AppProformaDetail> {
    return this.http.post<AppProformaDetail>(`${this.base}/proformas/${id}/anular/`, {});
  }

  /** Descarga el PDF como Blob. Un error llega del servidor como Blob (JSON
   * dentro): se convierte de vuelta a objeto para que `extractApiError` lo lea. */
  downloadProformaPdf(id: number): Observable<Blob> {
    return this.http.get(`${this.base}/proformas/${id}/pdf/`, { responseType: 'blob' }).pipe(
      catchError((err) => {
        if (err?.error instanceof Blob) {
          return from(err.error.text() as Promise<string>).pipe(
            switchMap((text) => {
              let parsed: unknown = null;
              try {
                parsed = JSON.parse(text);
              } catch {
                parsed = null;
              }
              return throwError(() => ({ ...err, error: parsed }));
            })
          );
        }
        return throwError(() => err);
      })
    );
  }

  // Notas de trabajo
  listNotasTrabajo(search?: string): Observable<AppNotaTrabajo[]> {
    const params: Record<string, string> = search ? { search } : {};
    return this.http.get<AppNotaTrabajo[]>(`${this.base}/notas-trabajo`, { params });
  }

  getNotaTrabajo(id: number): Observable<AppNotaTrabajoDetail> {
    return this.http.get<AppNotaTrabajoDetail>(`${this.base}/notas-trabajo/${id}/`);
  }

  updateNotaTrabajo(id: number, payload: NotaTrabajoUpdatePayload): Observable<AppNotaTrabajoDetail> {
    return this.http.patch<AppNotaTrabajoDetail>(`${this.base}/notas-trabajo/${id}/`, payload);
  }

  terminarNotaTrabajo(id: number): Observable<AppNotaTrabajoDetail> {
    return this.http.post<AppNotaTrabajoDetail>(`${this.base}/notas-trabajo/${id}/terminar/`, {});
  }

  corregirNotaTrabajo(id: number): Observable<AppNotaTrabajoDetail> {
    return this.http.post<AppNotaTrabajoDetail>(`${this.base}/notas-trabajo/${id}/corregir/`, {});
  }

  anularNotaTrabajo(id: number): Observable<AppNotaTrabajoDetail> {
    return this.http.post<AppNotaTrabajoDetail>(`${this.base}/notas-trabajo/${id}/anular/`, {});
  }

  // Notas de venta y cobro
  listNotasVenta(params: { search?: string; status?: string } = {}): Observable<AppNotaVenta[]> {
    const query: Record<string, string> = {};
    if (params.search) {
      query['search'] = params.search;
    }
    if (params.status) {
      query['status'] = params.status;
    }
    return this.http.get<AppNotaVenta[]>(`${this.base}/notas-venta`, { params: query });
  }

  getNotaVenta(id: number): Observable<AppNotaVentaDetail> {
    return this.http.get<AppNotaVentaDetail>(`${this.base}/notas-venta/${id}/`);
  }

  registrarPago(id: number, payload: PagoPayload): Observable<AppNotaVentaDetail> {
    return this.http.post<AppNotaVentaDetail>(`${this.base}/notas-venta/${id}/pago/`, payload);
  }

  anularPago(id: number): Observable<AppNotaVentaDetail> {
    return this.http.post<AppNotaVentaDetail>(`${this.base}/notas-venta/${id}/anular-pago/`, {});
  }

  anularNotaVenta(id: number): Observable<AppNotaVentaDetail> {
    return this.http.post<AppNotaVentaDetail>(`${this.base}/notas-venta/${id}/anular/`, {});
  }

  // Catalogos
  listSucursales(): Observable<OrdenSucursal[]> {
    return this.http.get<OrdenSucursal[]>(`${this.base}/catalogo/sucursales`);
  }

  listBobinas(sucursalId: number): Observable<ReelCatalogItem[]> {
    return this.http.get<ReelCatalogItem[]>(`${this.base}/catalogo/bobinas`, {
      params: { sucursal: sucursalId },
    });
  }

  listInstaladores(sucursalId: number): Observable<OrdenInstalador[]> {
    return this.http.get<OrdenInstalador[]>(`${this.base}/catalogo/instaladores`, {
      params: { sucursal: sucursalId },
    });
  }
}
