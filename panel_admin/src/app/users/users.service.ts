import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  AppGroup,
  AppPermission,
  AppSucursal,
  AppUser,
  CreateUserPayload,
} from './users.model';

@Injectable({
  providedIn: 'root',
})
export class UsersService {
  private http = inject(HttpClient);
  private base = `${environment.apiUrl}/product`;

  listUsers(includeInactive = false): Observable<AppUser[]> {
    const params: Record<string, string> = includeInactive ? { include_inactive: 'true' } : {};
    return this.http.get<AppUser[]>(`${this.base}/users`, { params });
  }

  getUser(id: number): Observable<AppUser> {
    return this.http.get<AppUser>(`${this.base}/users/${id}/`);
  }

  createUser(payload: CreateUserPayload): Observable<AppUser> {
    return this.http.post<AppUser>(`${this.base}/users`, payload);
  }

  updateUser(id: number, payload: Partial<AppUser>): Observable<AppUser> {
    return this.http.patch<AppUser>(`${this.base}/users/${id}/`, payload);
  }

  setPassword(id: number, password: string, passwordConfirm: string): Observable<void> {
    return this.http.post<void>(`${this.base}/users/${id}/set-password/`, {
      password,
      password_confirm: passwordConfirm,
    });
  }

  toggleActive(id: number, isActive: boolean): Observable<AppUser> {
    return this.http.patch<AppUser>(`${this.base}/users/${id}/toggle-active/`, {
      is_active: isActive,
    });
  }

  listGroups(): Observable<AppGroup[]> {
    return this.http.get<AppGroup[]>(`${this.base}/groups`);
  }

  getGroup(id: number): Observable<AppGroup> {
    return this.http.get<AppGroup>(`${this.base}/groups/${id}/`);
  }

  createGroup(payload: { name: string; permissions: number[] }): Observable<AppGroup> {
    return this.http.post<AppGroup>(`${this.base}/groups`, payload);
  }

  updateGroup(id: number, payload: Partial<AppGroup>): Observable<AppGroup> {
    return this.http.patch<AppGroup>(`${this.base}/groups/${id}/`, payload);
  }

  deleteGroup(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/groups/${id}/`);
  }

  listPermissions(): Observable<AppPermission[]> {
    return this.http.get<AppPermission[]>(`${this.base}/permissions`);
  }

  listSucursales(): Observable<AppSucursal[]> {
    return this.http.get<AppSucursal[]>(`${this.base}/sucursales`);
  }

  getSucursal(id: number): Observable<AppSucursal> {
    return this.http.get<AppSucursal>(`${this.base}/sucursales/${id}/`);
  }

  createSucursal(payload: Partial<AppSucursal>): Observable<AppSucursal> {
    return this.http.post<AppSucursal>(`${this.base}/sucursales`, payload);
  }

  updateSucursal(id: number, payload: Partial<AppSucursal>): Observable<AppSucursal> {
    return this.http.patch<AppSucursal>(`${this.base}/sucursales/${id}/`, payload);
  }

  deleteSucursal(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/sucursales/${id}/`);
  }
}
