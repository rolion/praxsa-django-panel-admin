import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { ClientProfile, ClientProformaRow, InvoicePayload, RegisterPayload } from './cliente.model';

/** API del cliente final (todas ya existen en el backend, ver
 * ADR-pricing-calculator-screen-registro-y-api-cliente):
 *  - POST product/client/register  (publica, con throttle)
 *  - GET  product/client/me        (perfil propio, Token)
 *  - GET  product/client/proformas (proformas propias, Token)
 *  - POST product/invoice          (guardar proforma; el servidor recalcula el precio) */
@Injectable({ providedIn: 'root' })
export class ClienteService {
  private http = inject(HttpClient);
  private base = `${environment.apiUrl}/product`;

  register(payload: RegisterPayload): Observable<{ username: string }> {
    return this.http.post<{ username: string }>(`${this.base}/client/register`, payload);
  }

  me(): Observable<ClientProfile> {
    return this.http.get<ClientProfile>(`${this.base}/client/me`);
  }

  proformas(): Observable<ClientProformaRow[]> {
    return this.http.get<ClientProformaRow[]>(`${this.base}/client/proformas`);
  }

  createInvoice(payload: InvoicePayload): Observable<{ id: number }> {
    return this.http.post<{ id: number }>(`${this.base}/invoice`, payload);
  }
}
