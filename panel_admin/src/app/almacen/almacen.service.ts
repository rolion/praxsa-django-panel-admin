import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  AppInventario,
  AppSucursal,
  AppWindowFilm,
  AppWindowFilmReel,
  InventarioCreatePayload,
  InventarioUpdatePayload,
} from './almacen.model';

interface ListParams {
  search?: string;
  includeInactive?: boolean;
}

function buildParams(params: ListParams = {}): Record<string, string> {
  const query: Record<string, string> = {};
  if (params.search) {
    query['search'] = params.search;
  }
  if (params.includeInactive) {
    query['include_inactive'] = 'true';
  }
  return query;
}

@Injectable({
  providedIn: 'root',
})
export class AlmacenService {
  private http = inject(HttpClient);
  private base = `${environment.apiUrl}/product/almacen`;

  // Laminas
  listLaminas(params: ListParams = {}): Observable<AppWindowFilm[]> {
    return this.http.get<AppWindowFilm[]>(`${this.base}/laminas`, { params: buildParams(params) });
  }

  getLamina(id: number): Observable<AppWindowFilm> {
    return this.http.get<AppWindowFilm>(`${this.base}/laminas/${id}/`);
  }

  createLamina(
    name: string,
    description: string,
    image?: File | null
  ): Observable<AppWindowFilm> {
    if (!image) {
      return this.http.post<AppWindowFilm>(`${this.base}/laminas`, { name, description });
    }
    const formData = new FormData();
    formData.append('name', name);
    formData.append('description', description);
    formData.append('image', image);
    return this.http.post<AppWindowFilm>(`${this.base}/laminas`, formData);
  }

  updateLamina(
    id: number,
    name: string,
    description: string,
    image?: File | null
  ): Observable<AppWindowFilm> {
    if (image === undefined) {
      return this.http.patch<AppWindowFilm>(`${this.base}/laminas/${id}/`, { name, description });
    }
    const formData = new FormData();
    formData.append('name', name);
    formData.append('description', description);
    formData.append('image', image === null ? '' : image);
    return this.http.patch<AppWindowFilm>(`${this.base}/laminas/${id}/`, formData);
  }

  toggleLaminaActive(id: number, isActive: boolean): Observable<AppWindowFilm> {
    return this.http.patch<AppWindowFilm>(`${this.base}/laminas/${id}/toggle-active/`, {
      is_active: isActive,
    });
  }

  // Bobinas
  listBobinas(params: ListParams = {}): Observable<AppWindowFilmReel[]> {
    return this.http.get<AppWindowFilmReel[]>(`${this.base}/bobinas`, { params: buildParams(params) });
  }

  createBobina(windowFilm: number, width: string, length: string, price: string): Observable<AppWindowFilmReel> {
    return this.http.post<AppWindowFilmReel>(`${this.base}/bobinas`, {
      window_film: windowFilm,
      width,
      length,
      price,
    });
  }

  updateBobina(
    id: number,
    windowFilm: number,
    width: string,
    length: string,
    price: string
  ): Observable<AppWindowFilmReel> {
    return this.http.patch<AppWindowFilmReel>(`${this.base}/bobinas/${id}/`, {
      window_film: windowFilm,
      width,
      length,
      price,
    });
  }

  toggleBobinaActive(id: number, isActive: boolean): Observable<AppWindowFilmReel> {
    return this.http.patch<AppWindowFilmReel>(`${this.base}/bobinas/${id}/toggle-active/`, {
      is_active: isActive,
    });
  }

  // Inventario
  listInventario(params: ListParams = {}): Observable<AppInventario[]> {
    return this.http.get<AppInventario[]>(`${this.base}/inventario`, { params: buildParams(params) });
  }

  getInventario(id: number): Observable<AppInventario> {
    return this.http.get<AppInventario>(`${this.base}/inventario/${id}/`);
  }

  createInventario(payload: InventarioCreatePayload): Observable<AppInventario> {
    return this.http.post<AppInventario>(`${this.base}/inventario`, payload);
  }

  updateInventario(id: number, payload: InventarioUpdatePayload): Observable<AppInventario> {
    return this.http.patch<AppInventario>(`${this.base}/inventario/${id}/`, payload);
  }

  toggleInventarioActive(id: number, isActive: boolean): Observable<AppInventario> {
    return this.http.patch<AppInventario>(`${this.base}/inventario/${id}/toggle-active/`, {
      is_active: isActive,
    });
  }

  // Reutiliza el endpoint ya existente del modulo Usuarios -- no duplica su CRUD.
  listSucursales(): Observable<AppSucursal[]> {
    return this.http.get<AppSucursal[]>(`${environment.apiUrl}/product/sucursales`);
  }
}
