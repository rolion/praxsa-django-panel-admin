import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { BehaviorSubject, Observable, map } from 'rxjs';
import { environment } from '../../../environments/environment';
import { User } from '../models/user';
import { LocalStorageService } from './storage.service';

interface StaffLoginResponse {
  token: string;
  user_id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  is_staff: boolean;
  groups: string[];
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
      .post<StaffLoginResponse>(`${environment.apiUrl}/product/admin-token-auth/`, {
        username,
        password,
      })
      .pipe(
        map((response) => {
          const user: User = {
            id: response.user_id,
            username: response.username,
            password: '',
            firstName: response.first_name,
            lastName: response.last_name,
            token: response.token,
            email: response.email,
            isStaff: response.is_staff,
            groups: response.groups,
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
  }
}
