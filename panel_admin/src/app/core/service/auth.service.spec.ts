import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';

import { environment } from '../../../environments/environment';
import { AuthService } from './auth.service';
import { LocalStorageService } from './storage.service';

describe('AuthService', () => {
  let service: AuthService;
  let httpMock: HttpTestingController;
  let storageService: LocalStorageService;

  beforeEach(() => {
    // AuthService lee localStorage real en su constructor -- limpiarlo antes
    // de cada test evita que una sesion guardada por un test anterior
    // contamine el estado inicial del siguiente.
    localStorage.clear();
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(AuthService);
    httpMock = TestBed.inject(HttpTestingController);
    storageService = TestBed.inject(LocalStorageService);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('successful login stores the token and updates currentUserValue', () => {
    let result: any;
    service.login('admin@test.com', 'secret').subscribe((user) => (result = user));

    const req = httpMock.expectOne(`${environment.apiUrl}/product/admin-token-auth/`);
    expect(req.request.method).toBe('POST');
    req.flush({
      token: 'abc123',
      user_id: 1,
      username: 'admin@test.com',
      email: 'admin@test.com',
      first_name: 'Admin',
      last_name: 'User',
      is_staff: true,
      groups: ['admin'],
    });

    expect(result.token).toBe('abc123');
    expect(service.currentUserValue.token).toBe('abc123');
    expect(service.currentUserValue.isStaff).toBe(true);
    expect(storageService.get('currentUser')).toBeTruthy();
  });

  it('failed login does not store anything and propagates the error', () => {
    let errored = false;
    service.login('admin@test.com', 'wrong').subscribe({
      next: () => fail('should not succeed'),
      error: () => (errored = true),
    });

    const req = httpMock.expectOne(`${environment.apiUrl}/product/admin-token-auth/`);
    req.flush({ detail: 'Invalid credentials' }, { status: 400, statusText: 'Bad Request' });

    expect(errored).toBe(true);
    expect(service.currentUserValue.token).toBeUndefined();
    expect(storageService.get('currentUser')).toBeFalsy();
  });

  it('logout clears the stored session', () => {
    service.login('admin@test.com', 'secret').subscribe();
    httpMock
      .expectOne(`${environment.apiUrl}/product/admin-token-auth/`)
      .flush({
        token: 'abc123',
        user_id: 1,
        username: 'admin@test.com',
        email: 'admin@test.com',
        first_name: 'Admin',
        last_name: 'User',
        is_staff: true,
        groups: [],
      });

    service.logout();

    expect(service.currentUserValue.token).toBeUndefined();
    expect(storageService.get('currentUser')).toBeFalsy();
  });
});
