import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, Subject, of } from 'rxjs';
import { map } from 'rxjs/operators';
import { User } from '../models/user';
import { LocalStorageService } from './storage.service';
import { environment } from '../../../environments/environment';

interface PanelAdminLoginResponse {
  token: string;
  user_id: number;
  username: string;
  name: string;
  lastname: string;
  is_staff: boolean;
  groups: string[];
  permissions?: string[];
}

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private http = inject(HttpClient);
  private storageService = inject(LocalStorageService);
  private currentUserSubject: BehaviorSubject<User>;
  public currentUser: Observable<User>;

  constructor() {
    this.currentUserSubject = new BehaviorSubject<User>(
      (this.storageService.get('currentUser') as User) || ({} as User)
    );
    this.currentUser = this.currentUserSubject.asObservable();
  }

  public get currentUserValue(): User {
    return this.currentUserSubject.value;
  }

  private sessionExpiredSubject = new Subject<void>();
  /** Se emite cuando una sesion de CLIENTE vence (401): la pantalla reabre el modal de
   * acceso sin recargar la pagina (ADR-pricing-calculator-screen-sesion-cliente-aislamiento). */
  readonly sessionExpired$ = this.sessionExpiredSubject.asObservable();

  get isLoggedIn(): boolean {
    return !!this.currentUserValue?.token;
  }

  /** Sesion de personal interno. Sesiones guardadas antes de que existiera `isStaff`
   * se tratan como no-staff hasta volver a iniciar sesion. Solo UX: la barrera real
   * es `IsStaffUser` en cada endpoint de administracion. */
  get isStaff(): boolean {
    return this.isLoggedIn && this.currentUserValue.isStaff === true;
  }

  /** Sesion de cliente final (con token y sin `is_staff`). */
  get isClient(): boolean {
    return this.isLoggedIn && !this.isStaff;
  }

  notifySessionExpired(): void {
    this.sessionExpiredSubject.next();
  }

  login(username: string, password: string): Observable<User> {
    return this.http
      .post<PanelAdminLoginResponse>(`${environment.apiUrl}/product/api-panel-admin-token-auth/`, {
        username,
        password,
      })
      .pipe(
        map((res) => {
          const user: User = {
            id: res.user_id,
            username: res.username,
            // Los usuarios creados con createsuperuser no tienen first_name: se
            // muestra el username en vez de un nombre vacío.
            firstName: res.name || res.username,
            lastName: res.lastname,
            token: res.token,
            isStaff: res.is_staff,
            groups: res.groups,
            permissions: res.permissions ?? [],
          };
          this.storageService.set('currentUser', user);
          this.currentUserSubject.next(user);
          return user;
        })
      );
  }

  /** Compara contra los grupos del usuario logueado, igual criterio que
   * `User_Helper.to_lowercase` del backend. Solo capa de UX (ocultar
   * botones) -- la barrera real es el permiso Django del endpoint, ver
   * ADR-modulo-almacen-permisos-rol-frontend. */
  hasGroup(name: string): boolean {
    const groups = this.currentUserValue.groups || [];
    return groups.map((g) => g.toLowerCase()).includes(name.toLowerCase());
  }

  /** Permiso Django efectivo del usuario logueado (`add_proforma_header` o
   * `product.add_proforma_header`). Solo capa de UX (ocultar botones): la
   * barrera real es el permiso de cada endpoint, ver ADR-modulo-ordenes-
   * proforma-nota-trabajo-alcance-permisos. Sesiones antiguas sin
   * `permissions` devuelven false hasta volver a iniciar sesion. */
  hasPermission(codename: string): boolean {
    const permissions = this.currentUserValue.permissions || [];
    const full = codename.includes('.') ? codename : `product.${codename}`;
    return permissions.includes(full);
  }

  logout() {
    // remove user from local storage to log user out
    this.storageService.remove('currentUser');
    this.currentUserSubject.next({} as User);
    return of({ success: false });
  }
}
