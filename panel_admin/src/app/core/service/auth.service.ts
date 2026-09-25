import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, of } from 'rxjs';
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
          };
          this.storageService.set('currentUser', user);
          this.currentUserSubject.next(user);
          return user;
        })
      );
  }

  logout() {
    // remove user from local storage to log user out
    this.storageService.remove('currentUser');
    this.currentUserSubject.next({} as User);
    return of({ success: false });
  }
}
